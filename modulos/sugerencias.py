"""
Subsistema de Sugerencias Comunitarias 2.0 (Reemplazo Definitivo de Carl-bot en #💡sugerencias💡).
Especificación técnica: docs/DISENO_SUGERENCIAS_2.md

Características principales:
- Interfaz interactiva Discord V2 con modales estructurados (Título, Categoría, Explicación).
- Tarjetas vivas con barra de progreso emoji dinámica (10 bloques 🟩/🟥 y porcentajes).
- Debate ordenado mediante creación automática de hilos de discusión por propuesta.
- Veredicto satírico, honesto y ácido con IA (Gemini) en el hilo con cacheo persistente.
- Moderación administrativa directa (Aprobar/Descartar con modal de motivo y cierre de hilo).
- Persistencia atómica 24/7 en datos/sugerencias.json bajo cerrojo asíncrono SUGGESTIONS_LOCK.
"""

import os
import sys
import json
import re
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

import discord
from discord import app_commands, TextStyle, ButtonStyle

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==========================================
# CONSTANTES Y CONFIGURACIÓN
# ==========================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUGGESTIONS_DATA_PATH = os.path.join(BASE_DIR, "datos", "sugerencias.json")
SUGGESTIONS_CHANNEL_ID = 1537582722812481696

# Cerrojo para concurrencia asíncrona y de disco
SUGGESTIONS_LOCK = asyncio.Lock()
_DISK_LOCK = threading.Lock()

# Buffer de logs interno
def _sug_log(msg: str):
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{timestamp}] [Sugerencias 2.0] {msg}")


def is_admin_or_mod(member_or_user) -> bool:
    """Verifica si el usuario es Administrador o Moderador en el servidor."""
    if not member_or_user:
        return False
    perms = getattr(member_or_user, "guild_permissions", None)
    if perms and (perms.administrator or perms.manage_roles or perms.manage_guild):
        return True
    roles = getattr(member_or_user, "roles", [])
    # IDs de roles autorizados: Pendejo Supremo (Admin), Pendejo Veterano (Mod/Staff), etc.
    return any(getattr(r, "id", 0) in (1446145987335950549, 1536783626199633940, 1446145803432235120) for r in roles)


# ==========================================
# PERSISTENCIA ATÓMICA DE DATOS
# ==========================================

def _load_data_sync() -> Dict[str, Any]:
    """Carga sincrónica del archivo JSON de sugerencias."""
    with _DISK_LOCK:
        if os.path.exists(SUGGESTIONS_DATA_PATH):
            try:
                with open(SUGGESTIONS_DATA_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        data.setdefault("next_suggestion_id", 9)
                        data.setdefault("suggestions", {})
                        return data
            except Exception as e:
                _sug_log(f"Aviso lectura sugerencias.json: {e}")
        return {"next_suggestion_id": 9, "suggestions": {}}


def _save_data_sync(data: Dict[str, Any]) -> None:
    """Guarda sincrónicamente y de forma atómica el archivo JSON."""
    with _DISK_LOCK:
        os.makedirs(os.path.dirname(SUGGESTIONS_DATA_PATH), exist_ok=True)
        tmp_path = f"{SUGGESTIONS_DATA_PATH}.tmp.{os.getpid()}_{threading.get_ident()}"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, SUGGESTIONS_DATA_PATH)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


async def load_suggestions_data() -> Dict[str, Any]:
    """Carga de datos de sugerencias bajo cerrojo asíncrono."""
    async with SUGGESTIONS_LOCK:
        return _load_data_sync()


async def save_suggestions_data(data: Dict[str, Any]) -> None:
    """Guardado de datos de sugerencias bajo cerrojo asíncrono."""
    async with SUGGESTIONS_LOCK:
        _save_data_sync(data)


def find_suggestion_by_id(data: Dict[str, Any], sug_id: int) -> Optional[Dict[str, Any]]:
    """Localiza una sugerencia por su ID correlativo."""
    for s in data.get("suggestions", {}).values():
        if int(s.get("id", 0)) == int(sug_id):
            return s
    return None


def find_suggestion_by_message_id(data: Dict[str, Any], message_id: int) -> Optional[Dict[str, Any]]:
    """Localiza una sugerencia por el ID del mensaje original."""
    for s in data.get("suggestions", {}).values():
        if int(s.get("message_id", 0) or 0) == int(message_id):
            return s
    return None


# ==========================================
# MOTOR VISUAL Y BARRA DE PROGRESO
# ==========================================

def format_progress_bar(up: int, down: int) -> str:
    """
    Genera una barra de progreso visual de 10 bloques de emojis (🟩 y 🟥).
    Si no hay votos: '⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0% (0 votos)'
    Si hay votos: '🟩🟩🟩🟩🟩🟩🟥🟥🟥🟥 **60%** A favor (6 👍 · 4 👎)'
    """
    total = up + down
    if total <= 0:
        return "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0% (0 votos)"
    pct = round((up / total) * 100)
    verdes = round(pct / 10)
    verdes = max(0, min(10, verdes))
    rojos = 10 - verdes
    bloques = ("🟩" * verdes) + ("🟥" * rojos)
    return f"{bloques} **{pct}%** A favor ({up} 👍 · {down} 👎)"


def build_suggestion_embed(sug: Dict[str, Any]) -> discord.Embed:
    """
    Construye el Embed de Discord V2 para una sugerencia.
    Colores:
    - 0x3B82F6 (Azul): En votación comunitaria
    - 0x22C55E (Verde): Aprobada por Administración
    - 0xEF4444 (Rojo): Descartada por Administración
    """
    sug_id = sug.get("id", "?")
    title = sug.get("title", "Sin título")
    desc = sug.get("description", "Sin descripción")
    category = sug.get("category", "General")
    status = sug.get("status", "voting")
    up_votes = sug.get("up_votes", [])
    down_votes = sug.get("down_votes", [])
    author_name = sug.get("author_name", "Miembro")
    author_avatar = sug.get("author_avatar")

    if status == "approved":
        color = 0x22C55E
        status_text = "✅ Aprobada por Administración"
    elif status == "rejected":
        color = 0xEF4444
        status_text = "❌ Descartada por Administración"
    else:
        color = 0x3B82F6
        status_text = "⏳ En votación comunitaria"

    embed = discord.Embed(
        title=f"💡 Sugerencia #{sug_id}: {title}",
        description=desc,
        color=color,
    )

    if author_avatar:
        embed.set_author(name=f"Propuesta por {author_name}", icon_url=author_avatar)
    else:
        embed.set_author(name=f"Propuesta por {author_name}")

    embed.add_field(name="📁 Categoría", value=category, inline=True)
    embed.add_field(name="📊 Estado", value=status_text, inline=True)

    # Barra dinámica de votos
    bar_str = format_progress_bar(len(up_votes), len(down_votes))
    embed.add_field(name="🗳️ Votos", value=bar_str, inline=False)

    # Lista compacta de votantes
    up_mentions = ", ".join(f"<@{uid}>" for uid in sorted(up_votes)[:15]) or "*Sin votos*"
    if len(up_votes) > 15:
        up_mentions += f" *(+{len(up_votes)-15} más)*"
    down_mentions = ", ".join(f"<@{uid}>" for uid in sorted(down_votes)[:15]) or "*Sin votos*"
    if len(down_votes) > 15:
        down_mentions += f" *(+{len(down_votes)-15} más)*"

    embed.add_field(
        name="👥 Votantes",
        value=f"👍: {up_mentions}\n👎: {down_mentions}",
        inline=False,
    )

    # Si está resuelta, campo de resolución del staff
    if status != "voting":
        res_by = sug.get("resolved_by_name", "Staff")
        res_reason = sug.get("resolution_reason", "Sin motivo especificado")
        res_date = sug.get("resolved_at", "")
        date_str = f" • *{res_date[:10]}*" if res_date else ""
        embed.add_field(
            name="⚖️ Resolución del Staff",
            value=f"**Por:** {res_by}{date_str}\n**Motivo:** {res_reason}",
            inline=False,
        )

    embed.set_footer(text=f"ID Sugerencia: {sug_id} • Propuesta por {author_name}")

    created_at = sug.get("created_at")
    if created_at:
        try:
            embed.timestamp = datetime.fromisoformat(created_at)
        except Exception:
            pass

    return embed


def build_suggestions_hub_embed() -> discord.Embed:
    """Construye el embed maestro de bienvenida para fijar en #💡sugerencias💡."""
    embed = discord.Embed(
        title="💡 Buzón Comunitario de Sugerencias — Los Mongolos del Sanvi",
        description=(
            "¡Bienvenido al canal oficial de propuestas de la comunidad!\n"
            "Aquí puedes proponer mejoras, nuevos canales, minijuegos, cambios en la economía "
            "o ideas para eventos y roles del servidor."
        ),
        color=0x3B82F6,
    )
    embed.add_field(
        name="📌 ¿Cómo funciona?",
        value=(
            "1. Pulsa el botón **`[💡 Proponer Idea]`** de abajo o usa `/sugerencia`.\n"
            "2. Rellena el título, la categoría y explica los beneficios de tu propuesta.\n"
            "3. Tu idea se publicará automáticamente con **votación en vivo** y se creará "
            "un **hilo de debate dedicado** para comentarla sin saturar el canal."
        ),
        inline=False,
    )
    embed.add_field(
        name="🧠 Veredicto de Asistente (IA)",
        value=(
            "Cualquier miembro puede pulsar **`[🧠 Veredicto de Asistente]`** en una propuesta "
            "para que Asistente analice con sarcasmo, humor negro y realismo si la idea es factible o una fumada."
        ),
        inline=False,
    )
    embed.add_field(
        name="⚖️ Moderación y Resolución",
        value=(
            "El Staff revisa periódicamente las sugerencias más votadas y las marca como "
            "**✅ Aprobadas** o **❌ Descartadas** fundamentando el motivo."
        ),
        inline=False,
    )
    embed.set_footer(text="💡 Sugerencias 2.0 • Sistema 24/7 de Asistente")
    return embed


async def publish_suggestions_hub(channel: discord.TextChannel) -> discord.Message:
    """Publica el embed maestro del buzón de sugerencias en el canal especificado."""
    embed = build_suggestions_hub_embed()
    view = SuggestionHubView()
    return await channel.send(embed=embed, view=view)


# ==========================================
# VEREDICTO DE ASISTENTE CON IA (GEMINI)
# ==========================================

async def get_or_generate_ai_verdict(sug: Dict[str, Any]) -> str:
    """
    Obtiene el veredicto satírico de Asistente para una sugerencia.
    Si ya fue generado y cacheado en el JSON, lo rescata sin gastar cuota.
    Si no, lo genera con Gemini y lo persiste.
    """
    cached = sug.get("ai_verdict")
    if cached and isinstance(cached, str) and cached.strip():
        return cached.strip()

    title = sug.get("title", "")
    category = sug.get("category", "")
    desc = sug.get("description", "")
    author = sug.get("author_name", "un miembro")

    prompt = (
        f"Actúa como 'Asistente', el bot oficial con personalidad de colega madrileño y sarcástico "
        f"de la comunidad 'Los Mongolos del Sanvi'.\n"
        f"Emite un veredicto satírico, honesto y ácido sobre la siguiente propuesta comunitaria:\n\n"
        f"• Título: {title}\n"
        f"• Categoría: {category}\n"
        f"• Explicación: {desc}\n"
        f"• Autor: {author}\n\n"
        f"Instrucciones:\n"
        f"- Analiza con humor negro, ironía fina y realismo si esto aporta valor o es una fumada inviable.\n"
        f"- Si es buena, reconócelo pero vacilando un poco.\n"
        f"- Concluye obligatoriamente con una línea: 'VEREDICTO: [APROBABLE / INVIABLE / FUMADA HISTÓRICA / OBRA MAESTRA] (Puntuación: X/10)' y una frase lapidaria.\n"
        f"- Máximo 500 caracteres, sé conciso y directo."
    )

    verdict_text = ""
    try:
        from modulos.chat_ia import call_gemini_multiturn
        turns = [{"role": "user", "parts": [{"text": prompt}]}]
        verdict_text = await asyncio.to_thread(call_gemini_multiturn, turns)
    except Exception as e:
        _sug_log(f"Error invocando Gemini para veredicto: {e}")

    if not verdict_text or "Cuota de IA" in verdict_text:
        verdict_text = (
            f"🧠 **Veredicto de Asistente:**\n"
            f"He intentado procesar la idea de {author} pero mis neuronas de silicio han cortocircuitado. "
            f"La propuesta suena a fumada de madrugada, pero si la peña la vota, Jose tendrá que mirárselo.\n"
            f"**VEREDICTO: INCLASIFICABLE (5/10)** — *Votad a favor si tenéis huevos.*"
        )

    # Cachear veredicto en el dict y persistir
    sug["ai_verdict"] = verdict_text
    data = await load_suggestions_data()
    # Actualizar en la colección
    for k, v in data.get("suggestions", {}).items():
        if v.get("id") == sug.get("id"):
            v["ai_verdict"] = verdict_text
            break
    await save_suggestions_data(data)
    return verdict_text


# ==========================================
# MODALES DE DISCORD V2
# ==========================================

class SuggestionSubmitModal(discord.ui.Modal):
    """Modal nativo estructurado para enviar una nueva propuesta comunitaria."""

    def __init__(self):
        super().__init__(title="💡 Proponer Nueva Sugerencia")
        self.title_input = discord.ui.TextInput(
            label="Título o Resumen",
            placeholder="Ej: Nuevo canal de clips / Minijuego de pesca",
            max_length=80,
            required=True,
        )
        self.category_input = discord.ui.TextInput(
            label="Categoría",
            placeholder="Servidor / Juegos / Bots / Ocio / Economía",
            max_length=30,
            required=True,
        )
        self.description_input = discord.ui.TextInput(
            label="Explicación detallada",
            style=TextStyle.paragraph,
            placeholder="Explica tu propuesta, por qué beneficia a la comunidad y cómo debería funcionar...",
            max_length=1000,
            required=True,
        )
        self.add_item(self.title_input)
        self.add_item(self.category_input)
        self.add_item(self.description_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Este comando solo funciona en el servidor.", ephemeral=True)
            return

        title_val = self.title_input.value.strip()
        cat_val = self.category_input.value.strip()
        desc_val = self.description_input.value.strip()

        if len(desc_val) < 10:
            await interaction.response.send_message(
                "⚠️ La explicación debe tener al menos 10 caracteres para que la comunidad pueda evaluarla.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        # Localizar canal #💡sugerencias💡
        sug_channel = interaction.guild.get_channel(SUGGESTIONS_CHANNEL_ID)
        if not sug_channel or not isinstance(sug_channel, discord.TextChannel):
            sug_channel = (
                discord.utils.find(lambda c: "sugerencia" in c.name.lower(), interaction.guild.text_channels)
                or interaction.channel
            )

        # Generar nuevo ID bajo SUGGESTIONS_LOCK
        data = await load_suggestions_data()
        next_id = data.get("next_suggestion_id", 9)
        data["next_suggestion_id"] = next_id + 1

        avatar_url = str(interaction.user.display_avatar.url) if interaction.user.display_avatar else None

        sug_entry: Dict[str, Any] = {
            "id": next_id,
            "message_id": None,
            "channel_id": sug_channel.id,
            "thread_id": None,
            "author_id": interaction.user.id,
            "author_name": interaction.user.display_name,
            "author_avatar": avatar_url,
            "title": title_val,
            "category": cat_val,
            "description": desc_val,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "voting",
            "up_votes": [interaction.user.id],  # El autor vota automáticamente a favor
            "down_votes": [],
            "ai_verdict": None,
            "resolved_by_id": None,
            "resolved_by_name": None,
            "resolution_reason": None,
            "resolved_at": None,
        }

        embed = build_suggestion_embed(sug_entry)
        view = SuggestionActiveView(sug_id=next_id, up_count=1, down_count=0)

        # Publicar en el canal
        sent_msg = await sug_channel.send(embed=embed, view=view)
        sug_entry["message_id"] = sent_msg.id

        # Apertura de hilo de debate
        thread_id = None
        try:
            thread_title = f"💡 Sugerencia #{next_id} - {title_val[:30]}"
            thread = await sent_msg.create_thread(name=thread_title, auto_archive_duration=1440)
            await thread.send(
                f"💬 Hilo de debate abierto para la **Sugerencia #{next_id}** de <@{interaction.user.id}>.\n"
                f"¡Comentad aquí vuestras opiniones, matices y mejoras!"
            )
            thread_id = thread.id
            sug_entry["thread_id"] = thread_id
        except Exception as e_thread:
            _sug_log(f"Aviso creando hilo para Sugerencia #{next_id}: {e_thread}")

        # Guardar en persistencia
        dict_key = f"{sug_channel.id}_{sent_msg.id}"
        data.setdefault("suggestions", {})[dict_key] = sug_entry
        await save_suggestions_data(data)

        _sug_log(f"💡 [Sugerencia #{next_id}] Creada por {interaction.user.display_name} en #{sug_channel.name}")

        await interaction.followup.send(
            f"✅ ¡Tu **Sugerencia #{next_id}** ha sido publicada con éxito en <#{sug_channel.id}>!",
            ephemeral=True,
        )


class SuggestionDecisionModal(discord.ui.Modal):
    """Modal administrativo para resolver (aprobar o rechazar) una propuesta con motivo."""

    def __init__(self, action: str, sug_id: int, suggestion_message: discord.Message):
        title = "✅ Aprobar Sugerencia" if action == "approve" else "❌ Descartar Sugerencia"
        super().__init__(title=title)
        self.action = action
        self.sug_id = sug_id
        self.suggestion_message = suggestion_message

        placeholder_txt = (
            "Ej: Gran propuesta, añadiremos el canal la próxima semana..."
            if action == "approve"
            else "Ej: Inviable técnicamente / No encaja con las normas del servidor..."
        )
        self.reason_input = discord.ui.TextInput(
            label="Motivo o comentario del Staff",
            style=TextStyle.paragraph,
            placeholder=placeholder_txt,
            required=False,
            max_length=500,
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        reason_text = self.reason_input.value.strip() or "Sin motivo especificado"
        admin_name = interaction.user.display_name
        admin_id = interaction.user.id

        data = await load_suggestions_data()
        sug = find_suggestion_by_id(data, self.sug_id)
        if not sug and self.suggestion_message:
            sug = find_suggestion_by_message_id(data, self.suggestion_message.id)

        if not sug:
            await interaction.followup.send("❌ No se encontró el registro de la sugerencia en la base de datos.", ephemeral=True)
            return

        # Actualizar datos de resolución
        sug["status"] = "approved" if self.action == "approve" else "rejected"
        sug["resolved_by_id"] = admin_id
        sug["resolved_by_name"] = admin_name
        sug["resolution_reason"] = reason_text
        sug["resolved_at"] = datetime.now(timezone.utc).isoformat()
        await save_suggestions_data(data)

        # Regenerar embed y vista cerrada
        new_embed = build_suggestion_embed(sug)
        up_count = len(sug.get("up_votes", []))
        down_count = len(sug.get("down_votes", []))
        closed_view = SuggestionClosedView(up_count=up_count, down_count=down_count)

        target_msg = getattr(interaction, "message", None) or self.suggestion_message
        if target_msg:
            try:
                await target_msg.edit(embed=new_embed, view=closed_view)
            except Exception as e_edit:
                _sug_log(f"Aviso actualizando mensaje de sugerencia: {e_edit}")

        # Gestionar hilo si existe
        thread_id = sug.get("thread_id")
        if thread_id and interaction.guild:
            try:
                thread = interaction.guild.get_thread(thread_id)
                if not thread:
                    thread = await interaction.guild.fetch_channel(thread_id)
                if thread and isinstance(thread, discord.Thread):
                    status_verb = "aprobada" if self.action == "approve" else "descartada"
                    emoji_verb = "✅" if self.action == "approve" else "❌"
                    await thread.send(
                        f"{emoji_verb} **Esta sugerencia ha sido {status_verb} por la administración.**\n"
                        f"**Staff:** {admin_name}\n"
                        f"**Motivo:** {reason_text}\n\n"
                        f"🔒 *El hilo de debate queda cerrado y archivado.*"
                    )
                    await thread.edit(archived=True, locked=True)
            except Exception as e_th:
                _sug_log(f"Aviso archivando hilo {thread_id}: {e_th}")

        action_label = "Aprobada" if self.action == "approve" else "Descartada"
        _sug_log(f"💡 [Sugerencia #{self.sug_id}] {action_label} por {admin_name}: {reason_text}")
        await interaction.followup.send(
            f"✅ Has marcado la **Sugerencia #{self.sug_id}** como **{action_label}**.",
            ephemeral=True,
        )


# ==========================================
# VISTAS INTERACTIVAS DISCORD V2
# ==========================================

class SuggestionActiveView(discord.ui.View):
    """
    Vista interactiva persistente 24/7 para votar y moderar sugerencias comunitarias.
    Botones:
    - [👍 Me mola (X)] (custom_id="sug2:up", ButtonStyle.success)
    - [👎 Ni de coña (Y)] (custom_id="sug2:down", ButtonStyle.danger)
    - [🧠 Veredicto de Asistente] (custom_id="sug2:verdict", ButtonStyle.secondary)
    - [✅ Aprobar] (custom_id="sug2:approve", ButtonStyle.success)
    - [❌ Descartar] (custom_id="sug2:reject", ButtonStyle.danger)
    """

    def __init__(self, sug_id: Optional[int] = None, up_count: int = 0, down_count: int = 0):
        super().__init__(timeout=None)
        self.sug_id = sug_id

        # 1. Botón Voto A Favor
        self.btn_up = discord.ui.Button(
            label=f"Me mola ({up_count})",
            style=ButtonStyle.success,
            emoji="👍",
            custom_id="sug2:up",
            row=0,
        )
        self.btn_up.callback = self.on_vote_up
        self.add_item(self.btn_up)

        # 2. Botón Voto En Contra
        self.btn_down = discord.ui.Button(
            label=f"Ni de coña ({down_count})",
            style=ButtonStyle.danger,
            emoji="👎",
            custom_id="sug2:down",
            row=0,
        )
        self.btn_down.callback = self.on_vote_down
        self.add_item(self.btn_down)

        # 3. Botón Veredicto de Asistente (IA)
        self.btn_verdict = discord.ui.Button(
            label="Veredicto de Asistente",
            style=ButtonStyle.secondary,
            emoji="🧠",
            custom_id="sug2:verdict",
            row=0,
        )
        self.btn_verdict.callback = self.on_verdict
        self.add_item(self.btn_verdict)

        # 4. Botón Staff: Aprobar
        self.btn_approve = discord.ui.Button(
            label="Aprobar",
            style=ButtonStyle.success,
            emoji="✅",
            custom_id="sug2:approve",
            row=1,
        )
        self.btn_approve.callback = self.on_approve
        self.add_item(self.btn_approve)

        # 5. Botón Staff: Descartar
        self.btn_reject = discord.ui.Button(
            label="Descartar",
            style=ButtonStyle.danger,
            emoji="❌",
            custom_id="sug2:reject",
            row=1,
        )
        self.btn_reject.callback = self.on_reject
        self.add_item(self.btn_reject)

    async def _resolve_sug_data(self, interaction: discord.Interaction) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """Recupera la sugerencia y el dataset completo desde el mensaje o embeds."""
        data = await load_suggestions_data()
        msg = interaction.message
        if not msg:
            return None, data

        sug = find_suggestion_by_message_id(data, msg.id)
        if sug:
            return sug, data

        # Intento de extracción por título de embed: "💡 Sugerencia #(\d+)"
        if msg.embeds:
            t = msg.embeds[0].title or ""
            m = re.search(r"Sugerencia\s*#(\d+)", t)
            if m:
                s_id = int(m.group(1))
                sug = find_suggestion_by_id(data, s_id)
                if sug:
                    # Enlazar message_id si no estaba
                    sug["message_id"] = msg.id
                    return sug, data
                else:
                    # Fallback de inicialización automática desde embed para mocks/legados
                    b_up, b_down = _extract_votes_from_embed(msg.embeds[0])
                    up_voters = []
                    down_voters = []
                    for fld in msg.embeds[0].fields:
                        for line in (fld.value or "").split("\n"):
                            if "👍" in line:
                                up_voters.extend([int(x) for x in re.findall(r"<@!?(\d+)>", line)])
                            if "👎" in line:
                                down_voters.extend([int(x) for x in re.findall(r"<@!?(\d+)>", line)])
                    while len(up_voters) < b_up:
                        up_voters.append(999000000 + len(up_voters))
                    while len(down_voters) < b_down:
                        down_voters.append(888000000 + len(down_voters))
                    sug = {
                        "id": s_id,
                        "message_id": msg.id,
                        "title": t,
                        "category": "Comunidad",
                        "description": msg.embeds[0].description or "",
                        "status": "voting",
                        "up_votes": up_voters,
                        "down_votes": down_voters,
                    }
                    data["suggestions"][str(msg.id)] = sug
                    return sug, data

        return None, data

    async def _handle_vote_toggle(self, interaction: discord.Interaction, is_up: bool):
        sug, data = await self._resolve_sug_data(interaction)
        if not sug:
            await interaction.response.send_message("❌ No se encontró la sugerencia en la base de datos.", ephemeral=True)
            return

        if sug.get("status") != "voting":
            await interaction.response.send_message("🔒 Esta sugerencia ya ha sido resuelta y las votaciones están cerradas.", ephemeral=True)
            return

        uid = interaction.user.id
        up_list: List[int] = sug.setdefault("up_votes", [])
        down_list: List[int] = sug.setdefault("down_votes", [])

        notice = ""
        if is_up:
            if uid in up_list:
                up_list.remove(uid)
                notice = "ℹ️ Has retirado tu voto a favor."
            else:
                if uid in down_list:
                    down_list.remove(uid)
                up_list.append(uid)
                notice = "👍 ¡Voto a favor registrado!"
        else:
            if uid in down_list:
                down_list.remove(uid)
                notice = "ℹ️ Has retirado tu voto en contra."
            else:
                if uid in up_list:
                    up_list.remove(uid)
                down_list.append(uid)
                notice = "👎 Voto en contra registrado."

        await save_suggestions_data(data)

        # Regenerar Embed y View
        new_embed = build_suggestion_embed(sug)
        new_view = SuggestionActiveView(
            sug_id=sug.get("id"),
            up_count=len(up_list),
            down_count=len(down_list),
        )

        await interaction.response.edit_message(embed=new_embed, view=new_view)
        await interaction.followup.send(notice, ephemeral=True)

    async def on_vote_up(self, interaction: discord.Interaction):
        await self._handle_vote_toggle(interaction, is_up=True)

    async def on_vote_down(self, interaction: discord.Interaction):
        await self._handle_vote_toggle(interaction, is_up=False)

    async def on_verdict(self, interaction: discord.Interaction):
        sug, data = await self._resolve_sug_data(interaction)
        if not sug:
            await interaction.response.send_message("❌ No se encontró la sugerencia para analizar.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        verdict = await get_or_generate_ai_verdict(sug)

        sug_id = sug.get("id", "?")
        thread_id = sug.get("thread_id")
        posted = False

        if thread_id and interaction.guild:
            try:
                thread = interaction.guild.get_thread(thread_id)
                if not thread:
                    thread = await interaction.guild.fetch_channel(thread_id)
                if thread and isinstance(thread, discord.Thread):
                    await thread.send(f"🧠 **Veredicto de Asistente (Sugerencia #{sug_id}):**\n\n{verdict}")
                    posted = True
            except Exception as e:
                _sug_log(f"Aviso enviando veredicto a hilo {thread_id}: {e}")

        if not posted:
            # Fallback en el canal respondiendo al mensaje
            try:
                await interaction.channel.send(
                    f"🧠 **Veredicto de Asistente sobre la Sugerencia #{sug_id}:**\n\n{verdict}",
                    reference=interaction.message,
                )
            except Exception:
                pass

        await interaction.followup.send(
            "🧠 ¡He emitido mi veredicto! Puedes leerlo en el hilo de debate.",
            ephemeral=True,
        )

    async def on_approve(self, interaction: discord.Interaction):
        if not is_admin_or_mod(interaction.user):
            await interaction.response.send_message(
                "❌ Solo los administradores y moderadores pueden aprobar sugerencias.",
                ephemeral=True,
            )
            return

        sug, _ = await self._resolve_sug_data(interaction)
        sug_id = sug.get("id", 0) if sug else 0
        await interaction.response.send_modal(
            SuggestionDecisionModal("approve", sug_id, interaction.message)
        )

    async def on_reject(self, interaction: discord.Interaction):
        if not is_admin_or_mod(interaction.user):
            await interaction.response.send_message(
                "❌ Solo los administradores y moderadores pueden descartar sugerencias.",
                ephemeral=True,
            )
            return

        sug, _ = await self._resolve_sug_data(interaction)
        sug_id = sug.get("id", 0) if sug else 0
        await interaction.response.send_modal(
            SuggestionDecisionModal("reject", sug_id, interaction.message)
        )


class SuggestionClosedView(discord.ui.View):
    """Vista de botones congelados para sugerencias resueltas."""

    def __init__(self, up_count: int = 0, down_count: int = 0):
        super().__init__(timeout=None)
        btn_up = discord.ui.Button(
            label=f"Me mola ({up_count})",
            style=ButtonStyle.secondary,
            emoji="👍",
            disabled=True,
            row=0,
        )
        self.add_item(btn_up)

        btn_down = discord.ui.Button(
            label=f"Ni de coña ({down_count})",
            style=ButtonStyle.secondary,
            emoji="👎",
            disabled=True,
            row=0,
        )
        self.add_item(btn_down)

        btn_status = discord.ui.Button(
            label="Sugerencia Cerrada",
            style=ButtonStyle.secondary,
            emoji="🔒",
            disabled=True,
            row=0,
        )
        self.add_item(btn_status)


class SuggestionHubView(discord.ui.View):
    """Vista persistente del panel maestro de bienvenida para proponer sugerencias."""

    def __init__(self):
        super().__init__(timeout=None)
        self.btn_create = discord.ui.Button(
            label="Proponer Idea",
            style=ButtonStyle.primary,
            emoji="💡",
            custom_id="sug2:create",
            row=0,
        )
        self.btn_create.callback = self.on_propose_idea
        self.add_item(self.btn_create)

    async def on_propose_idea(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SuggestionSubmitModal())


# ==========================================
# HELPER DE CREACIÓN DIRECTA (PARA /sugerencia con texto)
# ==========================================

async def handle_direct_suggestion(interaction: discord.Interaction, idea_text: str):
    """Procesa una sugerencia enviada con texto directo vía comando slash."""
    clean_idea = idea_text.strip()
    if len(clean_idea) < 10:
        await interaction.response.send_message(
            "⚠️ Por favor detalla un poco más tu propuesta (mínimo 10 caracteres) para que la comunidad pueda evaluarla.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    sug_channel = interaction.guild.get_channel(SUGGESTIONS_CHANNEL_ID)
    if not sug_channel or not isinstance(sug_channel, discord.TextChannel):
        sug_channel = (
            discord.utils.find(lambda c: "sugerencia" in c.name.lower(), interaction.guild.text_channels)
            or interaction.channel
        )

    data = await load_suggestions_data()
    next_id = data.get("next_suggestion_id", 9)
    data["next_suggestion_id"] = next_id + 1

    avatar_url = str(interaction.user.display_avatar.url) if interaction.user.display_avatar else None

    # Título resumido a partir de la primera frase o primeros 50 caracteres
    first_line = clean_idea.split("\n")[0].strip()
    title_val = first_line[:60] if len(first_line) > 5 else clean_idea[:50]

    sug_entry: Dict[str, Any] = {
        "id": next_id,
        "message_id": None,
        "channel_id": sug_channel.id,
        "thread_id": None,
        "author_id": interaction.user.id,
        "author_name": interaction.user.display_name,
        "author_avatar": avatar_url,
        "title": title_val,
        "category": "Comunidad / Servidor",
        "description": clean_idea,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "voting",
        "up_votes": [interaction.user.id],
        "down_votes": [],
        "ai_verdict": None,
        "resolved_by_id": None,
        "resolved_by_name": None,
        "resolution_reason": None,
        "resolved_at": None,
    }

    embed = build_suggestion_embed(sug_entry)
    view = SuggestionActiveView(sug_id=next_id, up_count=1, down_count=0)

    sent_msg = await sug_channel.send(embed=embed, view=view)
    sug_entry["message_id"] = sent_msg.id

    try:
        thread_title = f"💡 Sugerencia #{next_id} - {title_val[:30]}"
        thread = await sent_msg.create_thread(name=thread_title, auto_archive_duration=1440)
        await thread.send(
            f"💬 Hilo de debate abierto para la **Sugerencia #{next_id}** de <@{interaction.user.id}>.\n"
            f"¡Comentad aquí vuestras opiniones, matices y mejoras!"
        )
        sug_entry["thread_id"] = thread.id
    except Exception as e_thread:
        _sug_log(f"Aviso creando hilo: {e_thread}")

    dict_key = f"{sug_channel.id}_{sent_msg.id}"
    data.setdefault("suggestions", {})[dict_key] = sug_entry
    await save_suggestions_data(data)

    await interaction.followup.send(
        f"✅ ¡Tu **Sugerencia #{next_id}** ha sido publicada en <#{sug_channel.id}>!",
        ephemeral=True,
    )


# ==========================================
# RETROCOMPATIBILIDAD (ALIAS ANTIGUOS)
# ==========================================

# Vista compatible con el nombre anterior
class SuggestionPersistentView(SuggestionActiveView):
    """Subclase alias para retrocompatibilidad con imports anteriores."""
    def __init__(self, up_count: int = 0, down_count: int = 0, disabled: bool = False):
        if disabled:
            # Recrear con vista cerrada
            super().__init__(up_count=up_count, down_count=down_count)
            for item in self.children:
                item.disabled = True
        else:
            super().__init__(up_count=up_count, down_count=down_count)


SUGGESTION_VOTES_STATE: Dict[int, Any] = {}

def _extract_votes_from_embed(embed: discord.Embed) -> Tuple[int, int]:
    if not embed or not getattr(embed, "fields", None):
        return 0, 0
    for f in embed.fields:
        if "Votos" in (f.name or ""):
            val = f.value or ""
            # Nuevo formato de barra: (3 👍 · 1 👎)
            m_new = re.search(r"(\d+)\s*👍.*?(\d+)\s*👎", val)
            if m_new:
                return int(m_new.group(1)), int(m_new.group(2))
            # Formato clásico de Carl-bot: 👍 **3** a favor · 👎 **1** en contra
            m_old = re.search(r"👍[^\d]*(\d+)[^👎]*👎[^\d]*(\d+)", val)
            if m_old:
                return int(m_old.group(1)), int(m_old.group(2))
            # Fallback genérico a los 2 primeros números
            nums = re.findall(r"\d+", val)
            if len(nums) >= 2:
                return int(nums[0]), int(nums[1])
    return 0, 0


def _extract_vote_state_from_embed(embed: discord.Embed) -> Dict[str, Any]:
    b_up, b_down = _extract_votes_from_embed(embed)
    return {"up": set(), "down": set(), "base_up": b_up, "base_down": b_down}


def _update_suggestion_embed_votes(embed: discord.Embed, up_count: int, down_count: int, up_ids: set = None, down_ids: set = None) -> discord.Embed:
    d = embed.to_dict()
    fields = d.get("fields", [])
    bar_str = format_progress_bar(up_count, down_count)
    for f in fields:
        if "Votos" in f.get("name", ""):
            f["value"] = bar_str
            break
    d["fields"] = fields
    return discord.Embed.from_dict(d)


async def _get_next_suggestion_number(channel: discord.TextChannel) -> int:
    data = await load_suggestions_data()
    return data.get("next_suggestion_id", 9)
