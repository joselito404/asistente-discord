"""
Módulo de Juicios Comunitarios de El Tribunal en Discord:
- Gestión del ciclo judicial lúdico en canales comunitarios (especialmente #⚖️el-tribunal-gaming⚖️).
- Retención de fianzas en Porros y tasa judicial de apertura para el server_jackpot.
- Interfaz interactiva de deliberación popular (TrialView) con botones y actualización en tiempo real.
- Sistema de votación con quorum, veto a las partes interesadas y conmutación de voto.
- Resolución automática y sentencias satíricas del Asistente (culpabilidad, inocencia, empate o desestimación).
- Asignación de rol humorístico 'Culpable de Skill Issue'.
- Diferenciación canónica con la web oficial de videojuegos (https://el-tribunal-gaming.vercel.app).
"""

import os
import sys
import asyncio
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple, Set, Any, List

import discord
from discord import app_commands

from modulos.economia_core import (
    ECONOMY_LOCK,
    PORRO_EMOJI,
    get_balance,
    modify_balance,
    modify_server_jackpot,
    is_economy_halted,
    get_economy_halt_reason,
)


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


def _bot_log(msg: str):
    bs = _bs()
    log_fn = getattr(bs, "bot_log", print)
    log_fn(msg)


# ==========================================
# CONSTANTES Y REGLAS JUDICIALES
# ==========================================
MIN_BAIL = 100
MAX_BAIL = 2500
DEFAULT_BAIL = 300
COURT_FEE = 50  # Tasa judicial no reembolsable destinada a las arcas del server_jackpot
MIN_QUORUM = 2  # Quorum mínimo de jurados externos
DEFAULT_DURATION_SECONDS = 180  # 3 minutos de deliberación
CULPABLE_ROLE_NAME = "Culpable de Skill Issue"
WEB_TRIBUNAL_URL = "https://el-tribunal-gaming.vercel.app"

# Mapa de juicios activos por canal: {channel_id: TrialState}
ACTIVE_TRIALS: Dict[int, "TrialState"] = {}
TRIALS_LOCK = threading.RLock()


# ==========================================
# TEXTOS SATÍRICOS JUDICIALES
# ==========================================
SATIRICAL_GUILTY_PHRASES = [
    "¡SENTENCIA DE CULPABILIDAD ABSOLUTA! Tras una deliberación implacable del jurado popular, {defendant} ha sido declarado CULPABLE de todos los cargos. Ese skill issue no lo arregla ni un parche de 40 GB.",
    "¡CULPABLE! La corte ha dictado sentencia. Las pruebas son abrumadoras y las excusas de {defendant} han dado más vergüenza ajena que un tutorial sin saltar. Fianza confiscada y transferida.",
    "¡VEREDICTO CONDENATORIO! El jurado no ha comprado el cuento de {defendant}. La negligencia táctica y la traición al equipo quedan legalmente sancionadas.",
]

SATIRICAL_INNOCENT_PHRASES = [
    "¡SENTENCIA ABSOLUTORIA Y RESTAURACIÓN DE HONOR! El jurado popular ha proclamado la total INOCENCIA de {defendant}. {plaintiff} es condenado en costas por acusación temeraria y lloriqueo procesal.",
    "¡LIBRE DE TODA CULPA! {defendant} sale triunfante de los juzgados con la cabeza alta. {plaintiff} deberá indemnizar al acusado con su fianza por difamación pública.",
    "¡ABSOLUCIÓN HISTÓRICA! El jurado concluye que {defendant} no cometió infracción alguna y que el demandante {plaintiff} simplemente necesita 'aprender a jugar'. Fianza transferida.",
]

SATIRICAL_TIE_PHRASES = [
    "¡EMPATE JUDICIAL! El jurado popular ha quedado dividido exactamente a partes iguales. En estricta aplicación del principio universal 'In dubio pro reo', el acusado queda absuelto sin costas y las fianzas regresan a sus bolsillos.",
    "¡DIVISIÓN TOTAL DE LA CORTE! Ni el tribunal ni el jurado se ponen de acuerdo. Se declara tabla rasa, devolución íntegra de fianzas y cada uno a su trinchera.",
]

SATIRICAL_DISMISS_PHRASES = [
    "El Tribunal desestima la causa por falta de pruebas y absoluto desinterés ciudadano (quorum insuficiente: {votes}/{min_votes} votos). Se devuelven las fianzas retenidas a ambas partes. La tasa de 50 Porros queda requisada para el bote por hacerle perder el tiempo a la corte.",
]


# ==========================================
# MODELO DE ESTADO DEL JUICIO
# ==========================================
class TrialState:
    def __init__(
        self,
        channel_id: int,
        guild_id: int,
        plaintiff_id: int,
        plaintiff_name: str,
        plaintiff_mention: str,
        defendant_id: int,
        defendant_name: str,
        defendant_mention: str,
        reason: str,
        bail: int = DEFAULT_BAIL,
        duration: int = DEFAULT_DURATION_SECONDS,
    ):
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.plaintiff_id = plaintiff_id
        self.plaintiff_name = plaintiff_name
        self.plaintiff_mention = plaintiff_mention
        self.defendant_id = defendant_id
        self.defendant_name = defendant_name
        self.defendant_mention = defendant_mention
        self.reason = reason.strip()[:250]
        self.bail = bail
        self.fee = COURT_FEE
        self.duration = duration
        self.created_at = datetime.now(timezone.utc)
        self.ends_at = self.created_at + timedelta(seconds=duration)
        self.votes_culpable: Set[int] = set()
        self.votes_inocente: Set[int] = set()
        self.status: str = "deliberation"  # "deliberation", "culpable", "inocente", "tie", "dismissed"
        self.message: Optional[discord.Message] = None
        self.view: Optional["TrialView"] = None
        self.timer_task: Optional[asyncio.Task] = None
        self._resolved: bool = False

    @property
    def total_votes(self) -> int:
        return len(self.votes_culpable) + len(self.votes_inocente)

    def vote(self, user_id: int, choice: str) -> Tuple[bool, str]:
        """Registra o cambia el voto de un jurado. Prohíbe a las partes votar."""
        if self.status != "deliberation":
            return False, "⚠️ La fase de deliberación de este juicio ya ha finalizado."

        if user_id in (self.plaintiff_id, self.defendant_id):
            return (
                False,
                "❌ Como parte interesada en el juicio (demandante o demandado), no puedes formar parte del jurado popular ni votar en tu propia causa.",
            )

        choice_clean = choice.lower().strip()
        if choice_clean == "culpable":
            if user_id in self.votes_culpable:
                return True, "ℹ️ Ya habías votado **CULPABLE** anteriormente."
            if user_id in self.votes_inocente:
                self.votes_inocente.remove(user_id)
            self.votes_culpable.add(user_id)
            return True, "⚖️ Has emitido tu voto: **CULPABLE**."

        elif choice_clean == "inocente":
            if user_id in self.votes_inocente:
                return True, "ℹ️ Ya habías votado **INOCENTE** anteriormente."
            if user_id in self.votes_culpable:
                self.votes_culpable.remove(user_id)
            self.votes_inocente.add(user_id)
            return True, "🕊️ Has emitido tu voto: **INOCENTE**."

        return False, "Opción de voto no válida."

    def build_progress_bar(self) -> str:
        """Construye la barra visual de veredicto con bloques 🟥 y 🟩."""
        total = self.total_votes
        if total == 0:
            return "`[ ⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛ ]` 50% / 50%"
        pct_culpable = len(self.votes_culpable) / total
        blocks_culpable = round(pct_culpable * 10)
        blocks_inocente = 10 - blocks_culpable
        bar = "🟥" * blocks_culpable + "🟩" * blocks_inocente
        pct_c_str = f"{int(pct_culpable * 100)}%"
        pct_i_str = f"{int((1 - pct_culpable) * 100)}%"
        return f"`[{bar}]` ⚖️ {pct_c_str} | 🕊️ {pct_i_str}"

    def build_embed(self) -> discord.Embed:
        """Construye el Embed interactivo del juicio durante la deliberación."""
        embed = discord.Embed(
            title="⚖️ SALA DE AUDIENCIAS: JUICIO DE EL TRIBUNAL",
            description=(
                f"La fiscalía ciudadana abre proceso contra el acusado por supuesta falta grave en el servidor.\n\n"
                f"**📜 Causa Judicial:**\n> *\"{self.reason}\"*\n\n"
                f"El jurado popular dispone de tiempo reglamentario para examinar las pruebas y emitir su veredicto."
            ),
            color=0x9B59B6,
        )
        embed.add_field(name="👤 Acusador", value=self.plaintiff_mention, inline=True)
        embed.add_field(name="🎯 Acusado", value=self.defendant_mention, inline=True)
        embed.add_field(
            name="💰 Fianza en Disputa",
            value=f"{PORRO_EMOJI} **{self.bail:,}** Porros c/u\n*(+50 tasa al bote)*",
            inline=True,
        )

        ends_unix = int(self.ends_at.timestamp())
        embed.add_field(
            name="⏳ Cierre del Jurado",
            value=f"<t:{ends_unix}:R> (<t:{ends_unix}:T>)",
            inline=True,
        )
        embed.add_field(
            name="🗳️ Escrutinio Actual",
            value=(
                f"⚖️ Culpable: **{len(self.votes_culpable)}**  |  🕊️ Inocente: **{len(self.votes_inocente)}**\n"
                f"{self.build_progress_bar()}\n"
                f"*Quorum: {self.total_votes}/{MIN_QUORUM} votos mínimos requeridos*"
            ),
            inline=False,
        )

        embed.set_footer(
            text="El Tribunal Gaming • https://el-tribunal-gaming.vercel.app • Juicio Comunitario en Discord",
            icon_url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/2696.png",
        )
        return embed


# ==========================================
# INTERFAZ INTERACTIVA (TrialView)
# ==========================================
class TrialView(discord.ui.View):
    def __init__(self, trial: TrialState):
        super().__init__(timeout=trial.duration)
        self.trial = trial

    @discord.ui.button(
        label="Declarar Culpable",
        style=discord.ButtonStyle.danger,
        emoji="⚖️",
        custom_id="trial_vote_culpable",
    )
    async def btn_culpable(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, msg = self.trial.vote(interaction.user.id, "culpable")
        if not success:
            await interaction.response.send_message(msg, ephemeral=True)
            return

        await interaction.response.send_message(msg, ephemeral=True)
        await self._refresh_message()

    @discord.ui.button(
        label="Declarar Inocente",
        style=discord.ButtonStyle.success,
        emoji="🕊️",
        custom_id="trial_vote_inocente",
    )
    async def btn_inocente(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, msg = self.trial.vote(interaction.user.id, "inocente")
        if not success:
            await interaction.response.send_message(msg, ephemeral=True)
            return

        await interaction.response.send_message(msg, ephemeral=True)
        await self._refresh_message()

    @discord.ui.button(
        label="Ver Cargos",
        style=discord.ButtonStyle.secondary,
        emoji="📜",
        custom_id="trial_view_charges",
    )
    async def btn_cargos(self, interaction: discord.Interaction, button: discord.ui.Button):
        detail_embed = discord.Embed(
            title="📜 Expediente Judicial y Cargos",
            description=f"**Causa formulada por {self.trial.plaintiff_name}:**\n> *\"{self.trial.reason}\"*",
            color=0x2B2D31,
        )
        detail_embed.add_field(name="Demandante", value=self.trial.plaintiff_mention, inline=True)
        detail_embed.add_field(name="Demandado", value=self.trial.defendant_mention, inline=True)
        detail_embed.add_field(
            name="Condiciones Económicas",
            value=(
                f"• Fianza en custodia: **{self.trial.bail:,}** Porros de cada parte.\n"
                f"• Tasa judicial no reembolsable: **{self.trial.fee}** Porros destinada al bote del servidor.\n"
                f"• Si el acusado es **Culpable**: el demandante se embolsa la fianza del demandado.\n"
                f"• Si es **Inocente**: el demandante indemniza al acusado con su fianza.\n"
                f"• Si hay **Empate**: se devuelven las fianzas sin costas."
            ),
            inline=False,
        )
        detail_embed.add_field(
            name="Reglas del Jurado Popular",
            value=(
                f"• Quorum mínimo: **{MIN_QUORUM}** votos ajenos a los implicados.\n"
                f"• Ni el demandante ni el demandado pueden votar.\n"
                f"• Los jurados pueden rectificar su voto pulsando la opción contraria."
            ),
            inline=False,
        )
        detail_embed.set_footer(
            text="El Tribunal Gaming Oficial: https://el-tribunal-gaming.vercel.app (Magistrados Jose e Iván)",
        )
        await interaction.response.send_message(embed=detail_embed, ephemeral=True)

    async def _refresh_message(self):
        """Actualiza el embed principal con los votos en tiempo real de forma segura."""
        if self.trial.message and self.trial.status == "deliberation":
            try:
                await self.trial.message.edit(embed=self.trial.build_embed(), view=self)
            except discord.NotFound:
                pass
            except Exception as e:
                _bot_log(f"⚠️ Error refrescando embed de juicio {self.trial.channel_id}: {e}")

    async def on_timeout(self):
        """Al expirar el tiempo reglamentario, resuelve el juicio si no fue resuelto."""
        await resolve_trial(self.trial.channel_id)


# ==========================================
# GESTIÓN Y RESOLUCIÓN DEL JUICIO
# ==========================================
def get_active_trial(channel_id: int) -> Optional[TrialState]:
    """Devuelve el juicio activo en el canal si existe."""
    with TRIALS_LOCK:
        return ACTIVE_TRIALS.get(channel_id)


async def start_trial(
    interaction: discord.Interaction,
    defendant: discord.Member,
    reason: str,
    bail: int = DEFAULT_BAIL,
    duration: int = DEFAULT_DURATION_SECONDS,
) -> Tuple[bool, str, Optional[TrialState]]:
    """Valida, descuenta fondos atómicamente e inicia un juicio comunitario."""
    channel_id = interaction.channel_id
    if not channel_id:
        return False, "❌ Este comando solo puede ejecutarse en un canal de texto del servidor.", None

    if is_economy_halted():
        r = get_economy_halt_reason()
        reason_str = f" Motivo: {r}" if r else ""
        return False, f"⛔ Los juicios y operaciones de Porros están pausados temporalmente.{reason_str}", None

    # Validaciones previas
    plaintiff = interaction.user
    if defendant.bot:
        return False, "❌ No puedes llevar a juicio a un bot del servidor. Los bots carecen de fondos procesales y de alma.", None

    if defendant.id == plaintiff.id:
        return False, "❌ No puedes demandarte a ti mismo. Si tienes un conflicto existencial, coméntalo en #general.", None

    bail = max(MIN_BAIL, min(MAX_BAIL, int(bail)))
    reason_clean = str(reason).strip()
    if not reason_clean:
        return False, "❌ Debes especificar un motivo o cargo judicial válido.", None
    if len(reason_clean) > 250:
        reason_clean = reason_clean[:247] + "..."

    with TRIALS_LOCK:
        if channel_id in ACTIVE_TRIALS:
            active = ACTIVE_TRIALS[channel_id]
            return False, f"⚠️ Ya hay un juicio activo en este canal ({active.plaintiff_name} vs {active.defendant_name}). Espera a que concluya.", None

        # Comprobación de saldo bajo ECONOMY_LOCK
        with ECONOMY_LOCK:
            plaintiff_bal = get_balance(plaintiff.id)
            defendant_bal = get_balance(defendant.id)

            required_plaintiff = bail + COURT_FEE
            if plaintiff_bal["cash"] < required_plaintiff:
                return (
                    False,
                    f"❌ Saldo insuficiente en efectivo. Necesitas al menos {PORRO_EMOJI} **{required_plaintiff:,}** Porros ({bail:,} de fianza + {COURT_FEE} de tasa judicial no reembolsable). Tu saldo: {plaintiff_bal['cash']:,} Porros.",
                    None,
                )

            if defendant_bal["cash"] < bail:
                return (
                    False,
                    f"❌ El acusado {defendant.mention} no tiene suficientes Porros en efectivo para responder de la fianza ({bail:,} Porros requeridos). Saldo del acusado: {defendant_bal['cash']:,} Porros.",
                    None,
                )

            # Deducción atómica
            modify_balance(plaintiff.id, cash_delta=-required_plaintiff)
            modify_server_jackpot(+COURT_FEE)
            modify_balance(defendant.id, cash_delta=-bail)

        # Crear y registrar estado
        trial = TrialState(
            channel_id=channel_id,
            guild_id=interaction.guild_id or 0,
            plaintiff_id=plaintiff.id,
            plaintiff_name=plaintiff.display_name,
            plaintiff_mention=plaintiff.mention,
            defendant_id=defendant.id,
            defendant_name=defendant.display_name,
            defendant_mention=defendant.mention,
            reason=reason_clean,
            bail=bail,
            duration=duration,
        )
        ACTIVE_TRIALS[channel_id] = trial

    view = TrialView(trial)
    trial.view = view

    # Programar temporizador de resolución
    async def _timer_worker():
        try:
            await asyncio.sleep(duration)
            await resolve_trial(channel_id)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            _bot_log(f"⚠️ Error en temporizador de juicio {channel_id}: {e}")

    trial.timer_task = asyncio.create_task(_timer_worker())
    _bot_log(
        f"⚖️ [Tribunal Discord] Juicio iniciado en canal {channel_id}: {trial.plaintiff_name} contra {trial.defendant_name}. Fianza: {bail} Porros. Duración: {duration}s."
    )
    return True, "Juicio iniciado correctamente.", trial


async def resolve_trial(channel_id: int) -> Optional[TrialState]:
    """Resuelve de forma atómica y definitiva un juicio comunitario."""
    with TRIALS_LOCK:
        trial = ACTIVE_TRIALS.get(channel_id)
        if not trial or trial._resolved:
            return None
        trial._resolved = True
        ACTIVE_TRIALS.pop(channel_id, None)

    # Cancelar tarea de temporizador si sigue corriendo
    if trial.timer_task and not trial.timer_task.done():
        trial.timer_task.cancel()

    # Deshabilitar botones de la view
    if trial.view:
        for child in trial.view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    total_votes = trial.total_votes
    culpable_votes = len(trial.votes_culpable)
    inocente_votes = len(trial.votes_inocente)

    bs = _bs()
    bot = getattr(bs, "bot", None)
    guild = None
    if bot and trial.guild_id:
        guild = bot.get_guild(trial.guild_id)

    # 1. Falta de Quorum (< MIN_QUORUM votos ajenos)
    if total_votes < MIN_QUORUM:
        trial.status = "dismissed"
        # Devolución íntegra de fianzas (la tasa de 50 no se devuelve)
        with ECONOMY_LOCK:
            modify_balance(trial.plaintiff_id, cash_delta=+trial.bail)
            modify_balance(trial.defendant_id, cash_delta=+trial.bail)

        verdict_text = (
            f"🏛️ **CASO DESESTIMADO POR FALTA DE QUORUM Y DESINTERÉS CIUDADANO**\n\n"
            f"Solo se registraron **{total_votes}** de los **{MIN_QUORUM}** votos populares mínimos requeridos. "
            f"El Asistente y los Magistrados consideran que la acusación carece de relevancia pública.\n\n"
            f"💸 **Resolución Económica:** Se devuelven íntegramente las fianzas de {PORRO_EMOJI} **{trial.bail:,}** Porros a ambas partes. "
            f"La tasa judicial de apertura ({COURT_FEE} Porros) queda requisada para el bote del servidor por el trámite administrativo."
        )
        embed = discord.Embed(
            title="⚖️ VEREDICTO DE EL TRIBUNAL: CASO DESESTIMADO",
            description=verdict_text,
            color=0x95A5A6,
        )

    # 2. Sentencia CULPABLE (Culpable > Inocente)
    elif culpable_votes > inocente_votes:
        trial.status = "culpable"
        # El demandante recupera su fianza y se lleva la fianza del acusado (+2 * bail)
        with ECONOMY_LOCK:
            modify_balance(trial.plaintiff_id, cash_delta=trial.bail * 2)

        phrase = SATIRICAL_GUILTY_PHRASES[hash(f"{trial.plaintiff_id}_{trial.defendant_id}_{trial.bail}") % len(SATIRICAL_GUILTY_PHRASES)]
        satirical_msg = phrase.format(
            plaintiff=trial.plaintiff_mention,
            defendant=trial.defendant_mention,
        )

        role_assigned = False
        if guild:
            try:
                role = discord.utils.get(guild.roles, name=CULPABLE_ROLE_NAME)
                member = guild.get_member(trial.defendant_id)
                if role and member:
                    await member.add_roles(role, reason="Declarado Culpable en Juicio de El Tribunal")
                    role_assigned = True
            except Exception as e:
                _bot_log(f"⚠️ No se pudo asignar el rol '{CULPABLE_ROLE_NAME}': {e}")

        role_note = f"\n🏷️ **Sanción Moral:** Se ha impuesto al acusado el rol penitenciario **'{CULPABLE_ROLE_NAME}'**." if role_assigned else ""

        verdict_text = (
            f"🔨 **¡SENTENCIA DE CULPABILIDAD!**\n\n"
            f"{satirical_msg}\n\n"
            f"📊 **Resultado:** ⚖️ Culpable: **{culpable_votes}** vs 🕊️ Inocente: **{inocente_votes}**\n\n"
            f"💰 **Condena Económica:** El acusado {trial.defendant_mention} pierde su fianza. "
            f"{trial.plaintiff_mention} recibe {PORRO_EMOJI} **{trial.bail * 2:,}** Porros (su fianza devuelta + fianza confiscada)."
            f"{role_note}"
        )
        embed = discord.Embed(
            title="⚖️ VEREDICTO FINAL: CULPABLE",
            description=verdict_text,
            color=0xED4245,
        )

    # 3. Sentencia INOCENTE (Inocente > Culpable)
    elif inocente_votes > culpable_votes:
        trial.status = "inocente"
        # El acusado recupera su fianza y se lleva la del demandante por costas (+2 * bail)
        with ECONOMY_LOCK:
            modify_balance(trial.defendant_id, cash_delta=trial.bail * 2)

        phrase = SATIRICAL_INNOCENT_PHRASES[hash(f"{trial.plaintiff_id}_{trial.defendant_id}_{trial.bail}") % len(SATIRICAL_INNOCENT_PHRASES)]
        satirical_msg = phrase.format(
            plaintiff=trial.plaintiff_mention,
            defendant=trial.defendant_mention,
        )

        verdict_text = (
            f"🕊️ **¡SENTENCIA ABSOLUTORIA Y RESTAURACIÓN DE HONOR!**\n\n"
            f"{satirical_msg}\n\n"
            f"📊 **Resultado:** 🕊️ Inocente: **{inocente_votes}** vs ⚖️ Culpable: **{culpable_votes}**\n\n"
            f"💰 **Indemnización por Costas:** El demandante {trial.plaintiff_mention} pierde su fianza por acusación infundada. "
            f"{trial.defendant_mention} recibe {PORRO_EMOJI} **{trial.bail * 2:,}** Porros (su fianza devuelta + indemnización)."
        )
        embed = discord.Embed(
            title="⚖️ VEREDICTO FINAL: INOCENTE",
            description=verdict_text,
            color=0x57F287,
        )

    # 4. Empate Judicial (Culpable == Inocente)
    else:
        trial.status = "tie"
        # Devolución íntegra de fianzas
        with ECONOMY_LOCK:
            modify_balance(trial.plaintiff_id, cash_delta=+trial.bail)
            modify_balance(trial.defendant_id, cash_delta=+trial.bail)

        phrase = SATIRICAL_TIE_PHRASES[hash(f"{trial.plaintiff_id}_{trial.defendant_id}_{trial.bail}") % len(SATIRICAL_TIE_PHRASES)]
        satirical_msg = phrase.format(
            plaintiff=trial.plaintiff_mention,
            defendant=trial.defendant_mention,
        )

        verdict_text = (
            f"⚖️ **¡EMPATE JUDICIAL - IN DUBIO PRO REO!**\n\n"
            f"{satirical_msg}\n\n"
            f"📊 **Resultado:** ⚖️ {culpable_votes} votos vs 🕊️ {inocente_votes} votos.\n\n"
            f"💰 **Resolución Económica:** Se devuelven íntegramente las fianzas de {PORRO_EMOJI} **{trial.bail:,}** Porros a ambas partes. "
            f"La tasa de apertura de {COURT_FEE} Porros permanece en el bote del servidor."
        )
        embed = discord.Embed(
            title="⚖️ VEREDICTO FINAL: EMPATE (IN DUBIO PRO REO)",
            description=verdict_text,
            color=0xFEE75C,
        )

    embed.set_footer(
        text="El Tribunal Gaming Oficial: https://el-tribunal-gaming.vercel.app • Veredicto Comunitario",
        icon_url="https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/2696.png",
    )

    # Editar mensaje público si existe
    if trial.message:
        try:
            await trial.message.edit(embed=embed, view=trial.view)
        except Exception as e:
            _bot_log(f"⚠️ Error actualizando mensaje final de juicio {channel_id}: {e}")

    _bot_log(f"⚖️ [Tribunal Discord] Juicio {channel_id} finalizado con estado '{trial.status}'.")
    return trial
