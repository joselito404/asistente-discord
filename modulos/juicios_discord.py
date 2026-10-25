"""
Módulo de Juicios Comunitarios en Discord para 'Los Mongolos del Sanvi':
Minijuego de litigios cómicos, acusaciones y jurado popular (especificación canónica docs/DISENO_JUICIOS_DISCORD.md).

Características principales:
1. Concurrencia controlada: un juicio simultáneo por canal (ACTIVE_TRIALS bajo TRIALS_LOCK).
2. Modo Dual de Fianza:
   - Modo Económico (fianza >= 100 y <= 2500): retención de fianza a ambas partes y tasa judicial
     no reembolsable de COURT_FEE = 50 Porros transferida a server_jackpot bajo ECONOMY_LOCK.
   - Modo Moral (fianza == 0): juicio puramente honorífico y lúdico sin retención de fondos ni tasas.
3. Vista interactiva TrialView:
   - [⚖️ Declarar Culpable] (danger)
   - [🕊️ Declarar Inocente] (success)
   - [📜 Ver Cargos] (secondary, modal/ephemeral con expediente completo)
4. Lógica de votación:
   - 1 voto por ciudadano externo a las partes.
   - Votos conmutables (permite cambiar de Culpable a Inocente y viceversa).
   - Idempotente si repite el mismo voto.
   - Veto estricto a demandante y acusado (incompatibilidad judicial).
   - Escrutinio en tiempo real con barra visual de bloques (🟥 y 🟩) y porcentajes.
5. Deliberación de 120 segundos (2 minutos) con cuenta regresiva.
6. Veredicto y resolución:
   - Quorum mínimo: 2 votos externos ajenos a las partes. Si no hay quorum, desestimado y devolución íntegra de fianzas.
   - Culpable: demandante se lleva el pozo de fianza (+2 * fianza). Sentencia satírica + rol temporal 'Culpable de Skill Issue' (1h).
   - Inocente: acusado se lleva el pozo de fianza (+2 * fianza) como costas indemnizatorias. Sentencia satírica.
   - Empate: In dubio pro reo. Devolución de fianzas a ambas partes.
7. Totalmente desvinculado de El Tribunal Gaming (0 referencias a videojuegos o notas de la web).
"""

import sys
import os
import time
import asyncio
import random
from typing import Optional, Dict, Set

import discord
from discord import app_commands, ui

from modulos.economia import (
    get_balance,
    modify_balance,
    modify_server_jackpot,
    ECONOMY_LOCK,
    PORRO_EMOJI,
)

# Constantes canónicas aprobadas en docs/DISENO_JUICIOS_DISCORD.md
MIN_BAIL: int = 100
MAX_BAIL: int = 2500
DEFAULT_BAIL: int = 300
COURT_FEE: int = 50
TRIAL_DURATION: int = 120  # 120 segundos (2 minutos)
MIN_QUORUM: int = 2
SKILL_ISSUE_ROLE_NAME: str = "Culpable de Skill Issue"
SKILL_ISSUE_DURATION: int = 3600  # 1 hora

# Registro global de juicios activos por canal y cerrojo de concurrencia
ACTIVE_TRIALS: Dict[int, "TrialSession"] = {}
TRIALS_LOCK = asyncio.Lock()


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


def _bot_log(msg: str):
    bs = _bs()
    log_fn = getattr(bs, "bot_log", print)
    log_fn(msg)


# Frases satíricas de sentencia dictadas por Asistente
SATIRICAL_GUILTY_SENTENCES = [
    "Tras una exhaustiva deliberación popular, este honorable tribunal declara al acusado CULPABLE de todos los cargos. Se ordena la entrega inmediata del pozo de fianza al demandante y se le impone la marca de la deshonra por manco acreditado.",
    "El veredicto del pueblo es fulminante: CULPABLE sin atenuantes. Queda demostrado que la acusación tenía más razón que un santo y al acusado no le salva ni invocar lag mental.",
    "El jurado ha hablado y no hay piedad: CULPABLE. La fianza pasa a manos de la acusación como justa recompensa y el acusado queda registrado en el historial de la vergüenza.",
    "Veredicto inapelable: CULPABLE. Los testigos confirman que hubo dolo, alevosía y un nivel de skill issue digno de estudio científico.",
]

SATIRICAL_INNOCENT_SENTENCES = [
    "¡INOCENTE CON TODOS LOS HONORES! El jurado popular desestima la demanda y expone al acusador como un difamador sin pruebas. El acusado se lleva el pozo de fianza como indemnización por daños a su honor.",
    "Absolución inmediata. Las acusaciones de la fiscalía se sostienen menos que un castillo de naipes. El demandante deberá pagar las costas procesales con su fianza por hacerle perder el tiempo a este juzgado.",
    "El tribunal declara al acusado COMPLETAMENTE INOCENTE. El demandante queda públicamente retratado y se procede al embargo de su fianza a favor de la víctima de semejante cacería.",
    "Veredicto unánime de inocencia. Que sirva de lección al acusador: antes de montar un circo judicial, asegúrate de tener pruebas y no solo berrinches.",
]

SATIRICAL_TIE_SENTENCES = [
    "Empate técnico en el jurado popular. Aplicando el principio universal 'In dubio pro reo', el acusado queda absuelto sin costas y las fianzas retenidas son restituidas a ambas partes.",
    "El pueblo se halla dividido al 50%. Ante la duda razonable, este tribunal declara el caso cerrado en tablas. Se devuelven las fianzas íntegras y que cada uno se vaya a su casa.",
]

SATIRICAL_DISMISSED_SENTENCES = [
    "Caso desestimado por falta de quorum y absoluto desinterés ciudadano. Menos de 2 miembros acudieron a deliberar. Se devuelven las fianzas y se archiva el expediente por irrelevante.",
    "Juicio cancelado por incomparecencia popular. A la comunidad le ha dado tanta pereza este litigio que nadie vino a votar. Fianzas devueltas a ambas partes.",
]


def render_vote_bar(guilty_count: int, innocent_count: int, total_blocks: int = 10) -> tuple[str, float, float]:
    """Genera una barra visual de bloques emoji (🟥 y 🟩) y porcentajes de escrutinio."""
    total = guilty_count + innocent_count
    if total == 0:
        bar = "⬜" * total_blocks
        return bar, 0.0, 0.0

    pct_guilty = (guilty_count / total) * 100.0
    pct_innocent = (innocent_count / total) * 100.0

    guilty_blocks = round((guilty_count / total) * total_blocks)
    if guilty_count > 0 and guilty_blocks == 0:
        guilty_blocks = 1
    elif guilty_count < total and guilty_blocks == total_blocks:
        guilty_blocks = total_blocks - 1

    innocent_blocks = total_blocks - guilty_blocks
    bar = ("🟥" * guilty_blocks) + ("🟩" * innocent_blocks)
    return bar, pct_guilty, pct_innocent


class TrialSession:
    """Representa el estado completo de un juicio activo en un canal."""

    def __init__(
        self,
        channel_id: int,
        guild_id: int,
        plaintiff: discord.Member,
        defendant: discord.Member,
        reason: str,
        bail: int,
        fee_paid: int,
        duration: int = TRIAL_DURATION,
        guild: Optional[discord.Guild] = None,
    ):
        self.channel_id: int = channel_id
        self.guild_id: int = guild_id
        self.plaintiff_id: int = plaintiff.id
        self.plaintiff_name: str = plaintiff.display_name
        self.plaintiff_mention: str = plaintiff.mention
        self.defendant_id: int = defendant.id
        self.defendant_name: str = defendant.display_name
        self.defendant_mention: str = defendant.mention
        self.reason: str = reason
        self.bail: int = bail
        self.fee_paid: int = fee_paid
        self.start_time: float = time.time()
        self.duration: int = duration
        self.end_time: int = int(self.start_time + duration)
        self.guild: Optional[discord.Guild] = guild

        self.votes_guilty: Set[int] = set()
        self.votes_innocent: Set[int] = set()

        self.message: Optional[discord.Message] = None
        self.view: Optional["TrialView"] = None
        self.timer_task: Optional[asyncio.Task] = None
        self.resolved: bool = False
        self.lock: asyncio.Lock = asyncio.Lock()


def build_trial_embed(
    session: TrialSession,
    state: str = "active",
    verdict: Optional[str] = None,
    sentence_text: Optional[str] = None,
) -> discord.Embed:
    """Construye el Embed oficial de estado o resolución del juicio popular."""
    guilty_count = len(session.votes_guilty)
    innocent_count = len(session.votes_innocent)
    total_votes = guilty_count + innocent_count
    bar, pct_g, pct_i = render_vote_bar(guilty_count, innocent_count)

    if state == "active":
        title = "⚖️ TRIBUNAL POPULAR DE SANVI — JUICIO EN CURSO"
        color = 0xE67E22  # Naranja judicial
    elif verdict == "culpable":
        title = "⚖️ VEREDICTO FINAL: ¡CULPABLE!"
        color = 0xE74C3C  # Rojo
    elif verdict == "inocente":
        title = "🕊️ VEREDICTO FINAL: ¡INOCENTE!"
        color = 0x2ECC71  # Verde
    elif verdict == "empate":
        title = "⚖️ VEREDICTO FINAL: EMPATE JUDICIAL (IN DUBIO PRO REO)"
        color = 0xF1C40F  # Amarillo
    else:  # dismiss / sin quorum
        title = "📜 CASO DESESTIMADO POR FALTA DE QUORUM"
        color = 0x95A5A6  # Gris

    embed = discord.Embed(title=title, color=color)

    # Litigantes
    embed.add_field(
        name="👤 Acusador (Demandante)",
        value=f"{session.plaintiff_mention} (`{session.plaintiff_name}`)",
        inline=True,
    )
    embed.add_field(
        name="🎯 Acusado (Demandado)",
        value=f"{session.defendant_mention} (`{session.defendant_name}`)",
        inline=True,
    )

    # Modalidad y fianza
    if session.bail > 0:
        mode_str = f"💰 **{session.bail:,}** Porros retenidos por parte\n*(Tasa judicial: **{session.fee_paid}** Porros a jackpot)*"
    else:
        mode_str = "🕊️ **Juicio Moral y Honorífico** *(0 Porros retenidos, sin tasas)*"
    embed.add_field(name="💼 Modalidad del Litigio", value=mode_str, inline=False)

    # Motivo de la acusación
    embed.add_field(
        name="📜 Cargos e Imputación",
        value=f"> *\"{session.reason}\"*",
        inline=False,
    )

    # Escrutinio popular
    votos_info = (
        f"{bar}\n"
        f"🟥 Culpable: **{guilty_count}** ({pct_guilty_fmt(pct_g)})  |  "
        f"🟩 Inocente: **{innocent_count}** ({pct_innocent_fmt(pct_i)})\n"
        f"👥 Total emitidos: **{total_votes}** *(Quorum mínimo: {MIN_QUORUM} votos externos)*"
    )
    embed.add_field(name="🗳️ Escrutinio del Jurado Popular", value=votos_info, inline=False)

    # Estado o sentencia
    if state == "active":
        embed.add_field(
            name="⏳ Tiempo Restante para Votar",
            value=f"<t:{session.end_time}:R> (<t:{session.end_time}:T>)",
            inline=False,
        )
        embed.set_footer(
            text="Los Mongolos del Sanvi · Juicio Comunitario 100% lúdico · 1 voto por miembro externo",
        )
    else:
        if sentence_text:
            embed.add_field(name="📢 Sentencia Judicial de Asistente", value=sentence_text, inline=False)
        embed.set_footer(
            text="Los Mongolos del Sanvi · Causa judicial cerrada e inapelable",
        )

    return embed


def pct_guilty_fmt(val: float) -> str:
    return f"{val:.1f}%"


def pct_innocent_fmt(val: float) -> str:
    return f"{val:.1f}%"


class TrialView(ui.View):
    """Vista interactiva con botones de voto popular y consulta de expediente."""

    def __init__(self, session: TrialSession):
        super().__init__(timeout=None)
        self.session = session

    @ui.button(
        label="Declarar Culpable",
        style=discord.ButtonStyle.danger,
        emoji="⚖️",
        custom_id="trial_vote_guilty",
    )
    async def btn_guilty(self, interaction: discord.Interaction, button: ui.Button):
        await self._handle_vote(interaction, vote_type="culpable")

    @ui.button(
        label="Declarar Inocente",
        style=discord.ButtonStyle.success,
        emoji="🕊️",
        custom_id="trial_vote_innocent",
    )
    async def btn_innocent(self, interaction: discord.Interaction, button: ui.Button):
        await self._handle_vote(interaction, vote_type="inocente")

    @ui.button(
        label="Ver Cargos",
        style=discord.ButtonStyle.secondary,
        emoji="📜",
        custom_id="trial_view_charges",
    )
    async def btn_charges(self, interaction: discord.Interaction, button: ui.Button):
        expediente = (
            f"📋 **EXPEDIENTE JUDICIAL DE LA CAUSA**\n\n"
            f"• **Demandante:** {self.session.plaintiff_mention} (`{self.session.plaintiff_name}`)\n"
            f"• **Acusado:** {self.session.defendant_mention} (`{self.session.defendant_name}`)\n"
            f"• **Cargos formulados:** *\"{self.session.reason}\"*\n"
            f"• **Modalidad:** {'Económica con fianza de ' + str(self.session.bail) + ' Porros' if self.session.bail > 0 else 'Honorífica y moral (0 Porros)'}\n"
            f"• **Reglamento del Tribunal:**\n"
            f"  1. Ni el acusador ni el acusado pueden votar en su propio juicio.\n"
            f"  2. Cada miembro del servidor tiene **1 voto**, pero puede conmutarlo libremente durante la deliberación.\n"
            f"  3. Se exige un quorum mínimo de **{MIN_QUORUM} votos externos** para dictar sentencia válida.\n"
            f"  4. La deliberación dura **{TRIAL_DURATION} segundos** (2 minutos)."
        )
        await interaction.response.send_message(expediente, ephemeral=True)

    async def _handle_vote(self, interaction: discord.Interaction, vote_type: str):
        user_id = interaction.user.id

        # Veto estricto a demandante y acusado
        if user_id in (self.session.plaintiff_id, self.session.defendant_id):
            await interaction.response.send_message(
                "❌ **Incompatibilidad Judicial:** Como parte directamente implicada en este litigio (acusador o acusado), no puedes votar en tu propio juicio.",
                ephemeral=True,
            )
            return

        if self.session.resolved:
            await interaction.response.send_message(
                "⚖️ Este juicio ya ha finalizado y el veredicto ha sido dictado.",
                ephemeral=True,
            )
            return

        async with self.session.lock:
            if vote_type == "culpable":
                if user_id in self.session.votes_guilty:
                    await interaction.response.send_message(
                        "ℹ️ Ya has votado **Culpable** en este juicio. Tu voto ya se encuentra registrado.",
                        ephemeral=True,
                    )
                    return
                was_innocent = user_id in self.session.votes_innocent
                if was_innocent:
                    self.session.votes_innocent.remove(user_id)
                self.session.votes_guilty.add(user_id)
                resp_text = (
                    "🔄 Has conmutado tu voto a **Culpable** ⚖️."
                    if was_innocent
                    else "🗳️ Has votado **Culpable** ⚖️."
                )
            else:
                if user_id in self.session.votes_innocent:
                    await interaction.response.send_message(
                        "ℹ️ Ya has votado **Inocente** en este juicio. Tu voto ya se encuentra registrado.",
                        ephemeral=True,
                    )
                    return
                was_guilty = user_id in self.session.votes_guilty
                if was_guilty:
                    self.session.votes_guilty.remove(user_id)
                self.session.votes_innocent.add(user_id)
                resp_text = (
                    "🔄 Has conmutado tu voto a **Inocente** 🕊️."
                    if was_guilty
                    else "🗳️ Has votado **Inocente** 🕊️."
                )

        await interaction.response.send_message(resp_text, ephemeral=True)

        # Actualizar el embed principal con el escrutinio en tiempo real
        try:
            if self.session.message:
                embed = build_trial_embed(self.session, state="active")
                await self.session.message.edit(embed=embed)
        except Exception as e:
            _bot_log(f"Aviso actualizando embed de juicio {self.session.channel_id}: {e}")


async def _apply_skill_issue_role(session: TrialSession):
    """Intenta asignar temporalmente (1 hora) el rol 'Culpable de Skill Issue' al acusado."""
    if not session.guild:
        return

    try:
        role = discord.utils.get(session.guild.roles, name=SKILL_ISSUE_ROLE_NAME)
        if not role:
            _bot_log(f"[Juicios] Rol '{SKILL_ISSUE_ROLE_NAME}' no existe en {session.guild.name}. Se omite sanción de rol.")
            return

        member = session.guild.get_member(session.defendant_id)
        if not member:
            try:
                member = await session.guild.fetch_member(session.defendant_id)
            except Exception:
                member = None

        if not member:
            return

        await member.add_roles(role, reason="Declarado CULPABLE en Juicio Popular de Discord")
        _bot_log(f"[Juicios] Rol '{SKILL_ISSUE_ROLE_NAME}' asignado temporalmente a {member.display_name}.")

        # Esperar 1 hora y remover rol
        await asyncio.sleep(SKILL_ISSUE_DURATION)
        try:
            await member.remove_roles(role, reason="Expiración de condena de 1 hora de Juicio Popular")
            _bot_log(f"[Juicios] Rol '{SKILL_ISSUE_ROLE_NAME}' retirado tras condena de 1h a {member.display_name}.")
        except Exception as e:
            _bot_log(f"[Juicios] Error retirando rol '{SKILL_ISSUE_ROLE_NAME}': {e}")
    except Exception as e:
        _bot_log(f"[Juicios] No se pudo asignar rol temporal '{SKILL_ISSUE_ROLE_NAME}': {e}")


async def resolve_trial(session: TrialSession):
    """Calcula el veredicto, liquida fondos bajo ECONOMY_LOCK y publica la sentencia final."""
    async with session.lock:
        if session.resolved:
            return
        session.resolved = True

    # Liberar el canal bajo TRIALS_LOCK
    async with TRIALS_LOCK:
        if ACTIVE_TRIALS.get(session.channel_id) is session:
            del ACTIVE_TRIALS[session.channel_id]

    # Deshabilitar botones de la vista
    if session.view:
        for item in session.view.children:
            if isinstance(item, ui.Button):
                item.disabled = True

    guilty_count = len(session.votes_guilty)
    innocent_count = len(session.votes_innocent)
    total_votes = guilty_count + innocent_count

    # 1. Quorum insuficiente (< MIN_QUORUM)
    if total_votes < MIN_QUORUM:
        verdict = "desestimado"
        sentence = random.choice(SATIRICAL_DISMISSED_SENTENCES)
        if session.bail > 0:
            with ECONOMY_LOCK:
                modify_balance(session.plaintiff_id, cash_delta=+session.bail)
                modify_balance(session.defendant_id, cash_delta=+session.bail)
            sentence += f"\n\n💰 **Devolución de fianzas:** Se han restituido **{session.bail:,}** Porros a {session.plaintiff_mention} y **{session.bail:,}** Porros a {session.defendant_mention}."

    # 2. Culpable (Culpable > Inocente)
    elif guilty_count > innocent_count:
        verdict = "culpable"
        sentence = random.choice(SATIRICAL_GUILTY_SENTENCES)
        if session.bail > 0:
            pot = session.bail * 2
            with ECONOMY_LOCK:
                modify_balance(session.plaintiff_id, cash_delta=+pot)
            sentence += f"\n\n💰 **Liquidación de fianza:** {session.plaintiff_mention} se embolsa el pozo total de **{pot:,}** Porros (su fianza + la del acusado)."

        # Sanción de rol temporal en segundo plano
        if session.guild:
            session.role_task = asyncio.create_task(_apply_skill_issue_role(session))
            sentence += f"\n🏷️ **Sanción adicional:** Se ha impuesto la condena de 1 hora con el rol humorístico `\"{SKILL_ISSUE_ROLE_NAME}\"` al acusado."

    # 3. Inocente (Inocente > Culpable)
    elif innocent_count > guilty_count:
        verdict = "inocente"
        sentence = random.choice(SATIRICAL_INNOCENT_SENTENCES)
        if session.bail > 0:
            pot = session.bail * 2
            with ECONOMY_LOCK:
                modify_balance(session.defendant_id, cash_delta=+pot)
            sentence += f"\n\n💰 **Costas procesales:** {session.defendant_mention} se lleva **{pot:,}** Porros íntegros (su fianza + la fianza del acusador) como compensación por falsa acusación."

    # 4. Empate judicial (Culpable == Inocente)
    else:
        verdict = "empate"
        sentence = random.choice(SATIRICAL_TIE_SENTENCES)
        if session.bail > 0:
            with ECONOMY_LOCK:
                modify_balance(session.plaintiff_id, cash_delta=+session.bail)
                modify_balance(session.defendant_id, cash_delta=+session.bail)
            sentence += f"\n\n💰 **Restitución:** Se devuelven íntegramente las fianzas retenidas de **{session.bail:,}** Porros a ambas partes."

    final_embed = build_trial_embed(
        session,
        state="resolved",
        verdict=verdict,
        sentence_text=sentence,
    )

    try:
        if session.message:
            await session.message.edit(embed=final_embed, view=session.view)
    except Exception as e:
        _bot_log(f"Aviso actualizando mensaje final de juicio {session.channel_id}: {e}")


async def run_trial_timer(session: TrialSession):
    """Bucle temporizador de 120 segundos que concluye el juicio automáticamente."""
    try:
        await asyncio.sleep(session.duration)
    except asyncio.CancelledError:
        return
    except Exception as e:
        _bot_log(f"Error en temporizador de juicio {session.channel_id}: {e}")

    await resolve_trial(session)


# ==========================================
# COMANDO SLASH: /juicio (demandar, estado)
# ==========================================

cmd_juicio = app_commands.Group(
    name="juicio",
    description="Minijuego de Juicios Comunitarios en Discord (litigios cómicos y jurado popular)",
)


@cmd_juicio.command(
    name="demandar",
    description="Abre un juicio popular contra otro miembro del servidor por faltas o piques",
)
@app_commands.describe(
    acusado="Miembro del servidor al que deseas llevar a juicio",
    motivo="Causa o imputación concreta de la demanda (máximo 250 caracteres)",
    fianza="Fianza en Porros (0 para modo moral honorífico, o entre 100 y 2500; defecto: 300)",
)
async def cmd_juicio_demandar(
    interaction: discord.Interaction,
    acusado: discord.Member,
    motivo: str,
    fianza: int = DEFAULT_BAIL,
):
    if not interaction.guild or not interaction.channel:
        await interaction.response.send_message(
            "❌ Este comando solo puede utilizarse dentro de un canal del servidor.",
            ephemeral=True,
        )
        return

    # Validaciones sobre el acusado
    if getattr(acusado, "bot", False):
        await interaction.response.send_message(
            "❌ No puedes demandar a un bot. Los juicios comunitarios son exclusivos entre miembros humanos.",
            ephemeral=True,
        )
        return

    if acusado.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ No puedes demandarte a ti mismo. Si tienes un dilema existencial, habla con el psicólogo del servidor.",
            ephemeral=True,
        )
        return

    # Validación del motivo
    clean_reason = motivo.strip()
    if not clean_reason:
        await interaction.response.send_message(
            "❌ Debes especificar un motivo o cargo válido para la acusación.",
            ephemeral=True,
        )
        return

    if len(clean_reason) > 250:
        await interaction.response.send_message(
            f"❌ El motivo de la acusación no puede superar los 250 caracteres (longitud actual: {len(clean_reason)}).",
            ephemeral=True,
        )
        return

    # Validación de fianza
    if fianza < 0:
        await interaction.response.send_message(
            "❌ La fianza no puede ser negativa. Usa `0` para el modo moral honorífico o entre `100` y `2500` Porros.",
            ephemeral=True,
        )
        return

    if fianza != 0 and (fianza < MIN_BAIL or fianza > MAX_BAIL):
        await interaction.response.send_message(
            f"❌ La fianza debe ser exactamente `0` (modo moral) o estar comprendida entre **{MIN_BAIL:,}** y **{MAX_BAIL:,}** Porros.",
            ephemeral=True,
        )
        return

    # Verificación de concurrencia por canal
    async with TRIALS_LOCK:
        if interaction.channel_id in ACTIVE_TRIALS:
            await interaction.response.send_message(
                "❌ Ya existe un juicio popular activo en este canal. Espera a que concluya el veredicto antes de abrir una nueva causa.",
                ephemeral=True,
            )
            return

        fee_to_pay = COURT_FEE if fianza > 0 else 0

        # Verificación y retención económica bajo ECONOMY_LOCK
        if fianza > 0:
            with ECONOMY_LOCK:
                p_bal = get_balance(interaction.user.id)
                p_cash = int(p_bal.get("cash", 0))
                needed_p = fianza + fee_to_pay
                if p_cash < needed_p:
                    await interaction.response.send_message(
                        f"❌ No tienes suficiente efectivo para abrir el juicio. Necesitas **{needed_p:,}** Porros (**{fianza:,}** de fianza + **{fee_to_pay}** de tasa judicial no reembolsable). Tu efectivo actual es **{p_cash:,}** {PORRO_EMOJI}.",
                        ephemeral=True,
                    )
                    return

                d_bal = get_balance(acusado.id)
                d_cash = int(d_bal.get("cash", 0))
                if d_cash < fianza:
                    await interaction.response.send_message(
                        f"❌ El acusado **{acusado.display_name}** no dispone de suficiente efectivo para cubrir la fianza requerida de **{fianza:,}** {PORRO_EMOJI} (saldo actual del acusado: **{d_cash:,}**). Podéis disputar el litigio en modo moral con `fianza: 0`.",
                        ephemeral=True,
                    )
                    return

                # Deducir fondos atómicamente
                modify_balance(interaction.user.id, cash_delta=-needed_p)
                modify_balance(acusado.id, cash_delta=-fianza)
                modify_server_jackpot(fee_to_pay)

        # Crear sesión de juicio
        session = TrialSession(
            channel_id=interaction.channel_id,
            guild_id=interaction.guild_id,
            plaintiff=interaction.user,
            defendant=acusado,
            reason=clean_reason,
            bail=fianza,
            fee_paid=fee_to_pay,
            duration=TRIAL_DURATION,
            guild=interaction.guild,
        )
        ACTIVE_TRIALS[interaction.channel_id] = session

    view = TrialView(session)
    session.view = view
    embed = build_trial_embed(session, state="active")

    await interaction.response.send_message(
        content=f"🔔 {acusado.mention}, has sido sentado en el banquillo de los acusados por {interaction.user.mention}.",
        embed=embed,
        view=view,
    )

    try:
        session.message = await interaction.original_response()
    except Exception:
        pass

    session.timer_task = asyncio.create_task(run_trial_timer(session))
    _bot_log(f"⚖️ [Juicios] Juicio iniciado en canal {interaction.channel_id}: {interaction.user.display_name} contra {acusado.display_name} (Fianza: {fianza}).")


@cmd_juicio.command(
    name="estado",
    description="Consulta el estado y escrutinio del juicio popular en este canal",
)
async def cmd_juicio_estado(interaction: discord.Interaction):
    if not interaction.channel_id:
        await interaction.response.send_message("❌ Comando no disponible aquí.", ephemeral=True)
        return

    session = ACTIVE_TRIALS.get(interaction.channel_id)
    if not session:
        await interaction.response.send_message(
            "ℹ️ No hay ningún juicio activo en este canal actualmente. Puedes abrir una nueva causa con `/juicio demandar`.",
            ephemeral=True,
        )
        return

    embed = build_trial_embed(session, state="active")
    await interaction.response.send_message(embed=embed, ephemeral=True)
