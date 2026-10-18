"""
Subsistema de Auto-Roles 24/7 y Sugerencias Comunitarias (Reemplazo Integral de Carl-bot):
- Catálogo oficial de 36 autoroles en 3 categorías ('plataformas', 'generos', 'juegos').
- Whitelist estricta de seguridad (ALL_AUTOROLE_IDS) que protege roles de Admin, Staff, Niveles y Economía.
- Menús desplegables públicos persistentes (AutoRolesPersistentView, AutoRoleCategoryView, AutoRoleSelect) con modo Toggle.
- Vista Personal efímera persistente (PersonalAutoRolesView, PersonalCategorySelect) con checks premarcados (default=True).
- Sistema de Sugerencias Comunitarias 24/7 (SuggestionPersistentView, SuggestionDecisionModal) con persistencia de votantes en embed.
"""

from datetime import datetime, timezone
import re
import sys
import discord


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


def _bot_log(msg: str):
    bs = _bs()
    log_fn = getattr(bs, "bot_log", print)
    log_fn(msg)


AUTOROLES_CATALOG = {
    "plataformas": {
        "title": "🎮 PLATAFORMAS, IDIOMAS Y HOBBIES",
        "placeholder": "🎮 Plataformas, Idiomas y Hobbies (elige uno o varios)",
        "description": "Selecciona tus dispositivos, idiomas o aficiones en el menú desplegable para asignarte (✅) o quitarte (❌) los roles al instante:",
        "color": 0x5865F2,
        "roles": [
            ("💻", 1537577523011911772, "PC", "Jugador de PC / Escritorio"),
            ("🎮", 1537593228209950720, "Consola", "PlayStation, Xbox o Nintendo Switch"),
            ("🍿", 1537592958747148368, "Cine", "Películas, series y debate cinéfilo"),
            ("📖", 1537593474721906759, "lectura", "Libros, novelas ligeras y lectura"),
            ("🤝", 1537577153862967366, "Co-op", "Juegos cooperativos (acceso a #juegos-cooperativos)"),
            ("📚", 1537593587670327356, "manga", "Lectores de manga japonés"),
            ("🐉", 1537593562772799498, "anime", "Temporadas de anime y películas"),
            ("🇰🇷", 1537593440303325275, "Manhwa", "Manhwas, webtoons y cultura coreana"),
            ("👥", 1537593280232165396, "Familia de Steam", "Miembros de la Familia de Steam (#familia-steam)"),
            ("⚽", 1537594961837428776, "Deportes", "Fútbol, motor, deporte y eventos"),
            ("🌙", 1537593627105038466, "nocturno", "Búhos nocturnos y charlas de madrugada"),
            ("🇪🇸", 1537594201326489690, "Español", "Hablante de español"),
            ("🇬🇧", 1537594249720242216, "ingles", "Hablante / lector en inglés"),
            ("⚡", 1537593357713412146, "Tryhard", "Competitivo, ranked y sudar la camiseta"),
            ("☕", 1537593381830529104, "Casual", "Jugar de chill y pasar el rato"),
        ],
    },
    "generos": {
        "title": "🎯 GÉNEROS DE JUEGOS Y ALERTAS",
        "placeholder": "🎯 Géneros de Juegos y Alertas (elige uno o varios)",
        "description": "Selecciona los géneros de videojuegos y avisos que te interesen:",
        "color": 0x10B981,
        "roles": [
            ("🎯", 1537591932010766367, "Shooters", "FPS, tácticos y juegos de disparos"),
            ("🌲", 1537592360291008612, "Survival", "Supervivencia, crafteo y mundo abierto"),
            ("🎒", 1537592390142132396, "Extraction", "Extraction shooters y loot de alto riesgo"),
            ("💀", 1537592856380706906, "Roguelike", "Roguelikes, roguelites y runs infinitas"),
            ("🗡️", 1537595229627224124, "RPG", "Juegos de rol, historia y aventura"),
            ("🤼", 1537594274093465683, "Peleas", "Fighting games y combates 1v1"),
            ("🚨", 1537594120078368768, "Falta Uno", "Ping cuando falta hueco en el lobby"),
            ("🃏", 1537595303346053221, "Cartas", "Deckbuilders, TCG y juegos de cartas"),
            ("♟️", 1537595282190237706, "Estrategia", "RTS, 4X, táctica y ajedrez"),
            ("⭐", 1537914650274963598, "recomendaciones de juegos", "Avisos de joyas y análisis en #recomendaciones-gaming"),
            ("🔥", 1537595250695209000, "Soulslike", "FromSoftware, bosses duros y acción desafiante"),
            ("🕹️", 1537592919815360632, "Indie", "Juegos independientes y propuestas originales"),
            ("📈", 1537934178283290664, "incremental", "Idle, clickers y números que suben"),
        ],
    },
    "juegos": {
        "title": "🕹️ JUEGOS ESPECÍFICOS",
        "placeholder": "🕹️ Juegos Específicos (elige uno o varios)",
        "description": "Selecciona los juegos a los que juegas para enterarte cuando se arme partida:",
        "color": 0xF59E0B,
        "roles": [
            ("📱", 1537591875656224820, "Brawl Stars", "Partidas, club y Matcherino de Brawl Stars"),
            ("🤖", 1537914271483297812, "ARC Raiders", "Escuadrones en ARC Raiders"),
            ("🪂", 1537914329167302718, "Fornite", "Battle Royale y modos de Fortnite"),
            ("💥", 1537914381277462719, "The finals", "Torneos y destrucción en THE FINALS"),
            ("📦", 1537914482724970576, "R.E.P.O", "Cooperativo y risas en R.E.P.O."),
            ("🌻", 1537914562823594024, "PVZ GW2", "Plants vs. Zombies: Garden Warfare 2"),
            ("⛰️", 1537914820223828038, "PEAK", "Escalada cooperativa en PEAK"),
            ("🚶", 1548716906213543986, "Big Walk", "Aventuras cooperativas en Big Walk"),
        ],
    },
}

AUTOROLE_INFO_BY_ID = {}
for _cat_key, _cat_data in AUTOROLES_CATALOG.items():
    for _emoji, _rid, _name, _desc in _cat_data["roles"]:
        AUTOROLE_INFO_BY_ID[_rid] = {
            "category": _cat_key,
            "emoji": _emoji,
            "id": _rid,
            "name": _name,
            "description": _desc,
        }

ALL_AUTOROLE_IDS = frozenset(AUTOROLE_INFO_BY_ID.keys())


def compute_autorole_toggle(current_role_ids: set, selected_role_ids: list, allowed_role_ids: set = ALL_AUTOROLE_IDS) -> tuple:
    """Calcula qué autoroles añadir y cuáles retirar en modo interruptor (Toggle).
    Ignora estrictamente cualquier ID que no pertenezca a allowed_role_ids."""
    to_add = []
    to_remove = []
    seen = set()
    for raw_id in selected_role_ids:
        try:
            rid = int(raw_id)
        except (ValueError, TypeError):
            continue
        if rid not in allowed_role_ids or rid in seen:
            continue
        seen.add(rid)
        if rid in current_role_ids:
            to_remove.append(rid)
        else:
            to_add.append(rid)
    return to_add, to_remove


def compute_autorole_category_sync(current_role_ids: set, selected_role_ids: list, category_role_ids: list) -> tuple:
    """Calcula la sincronización exacta de una categoría en la vista personal (con checks premarcados).
    Añade los marcados que no tenía y retira los desmarcados de esa categoría."""
    cat_set = set(category_role_ids) & ALL_AUTOROLE_IDS
    selected_set = set()
    for raw_id in selected_role_ids:
        try:
            rid = int(raw_id)
            if rid in cat_set:
                selected_set.add(rid)
        except (ValueError, TypeError):
            continue
    to_add = [rid for rid in category_role_ids if rid in selected_set and rid not in current_role_ids]
    to_remove = [rid for rid in category_role_ids if rid in cat_set and rid in current_role_ids and rid not in selected_set]
    return to_add, to_remove


def build_autoroles_category_embed(cat_key: str, include_footer: bool = False) -> discord.Embed:
    """Construye el embed visual de una categoría de Auto-Roles con menciones nativas <@&ID>."""
    cat = AUTOROLES_CATALOG[cat_key]
    lines = [f"{emoji} <@&{rid}> — *{desc}*" for emoji, rid, _name, desc in cat["roles"]]
    embed = discord.Embed(
        title=cat["title"],
        description=f"{cat['description']}\n\n" + "\n".join(lines),
        color=cat["color"],
    )
    if include_footer:
        embed.set_footer(
            text="⚡ Auto-Roles 24/7 de Asistente • Elige roles en los menús para activarlos (✅) o quitarlos (❌) • Pulsa 'Mis Roles' para tu vista personal"
        )
    return embed


def build_autoroles_all_embeds() -> list:
    """Construye los 3 embeds oficiales de Auto-Roles para el panel unificado."""
    keys = list(AUTOROLES_CATALOG.keys())
    return [build_autoroles_category_embed(k, include_footer=(i == len(keys) - 1)) for i, k in enumerate(keys)]


def build_personal_autoroles_embed(member_display_name: str, current_role_ids: set, changes_summary: str = "") -> discord.Embed:
    """Construye el embed efímero con el resumen de autoroles activos del usuario."""
    total_active = len(current_role_ids & ALL_AUTOROLE_IDS)
    desc_parts = []
    if changes_summary:
        desc_parts.append(changes_summary)
    desc_parts.append(
        f"Aquí tienes tus autoroles equipados actualmente (**{total_active} / {len(ALL_AUTOROLE_IDS)}** activos).\n"
        f"En los menús de abajo ya aparecen **marcados con ✅** los que tienes: marca o desmarca los que quieras para sincronizarlos al vuelo."
    )
    embed = discord.Embed(
        title=f"🎭 Vista Personal de Auto-Roles — {member_display_name}",
        description="\n\n".join(desc_parts),
        color=0x8B5CF6,
    )
    for cat_key, cat_data in AUTOROLES_CATALOG.items():
        active_mentions = [
            f"{emoji} <@&{rid}>"
            for emoji, rid, _name, _desc in cat_data["roles"]
            if rid in current_role_ids
        ]
        val = " · ".join(active_mentions) if active_mentions else "*Ninguno seleccionado*"
        embed.add_field(name=cat_data["title"], value=val, inline=False)
    embed.set_footer(text="Vista personal efímera • Solo tú puedes ver y usar estos menús")
    return embed


async def _resolve_guild_member(interaction: discord.Interaction):
    """Obtiene el objeto discord.Member actualizado del usuario que interactúa."""
    if not interaction.guild:
        return None
    if isinstance(interaction.user, discord.Member):
        return interaction.user
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        try:
            member = await interaction.guild.fetch_member(interaction.user.id)
        except Exception:
            member = None
    return member


async def _apply_role_changes_to_member(guild: discord.Guild, member: discord.Member, to_add_ids: list, to_remove_ids: list, reason: str) -> tuple:
    """Aplica las altas y bajas de roles al miembro en Discord de forma segura.
    Devuelve (added_ids_ok, removed_ids_ok, errors)."""
    added_ok = []
    removed_ok = []
    errors = []

    add_objs = []
    for rid in to_add_ids:
        if rid not in ALL_AUTOROLE_IDS:
            continue
        r_obj = guild.get_role(rid) or discord.Object(id=rid)
        add_objs.append((rid, r_obj))

    rem_objs = []
    for rid in to_remove_ids:
        if rid not in ALL_AUTOROLE_IDS:
            continue
        r_obj = guild.get_role(rid) or discord.Object(id=rid)
        rem_objs.append((rid, r_obj))

    if add_objs:
        try:
            await member.add_roles(*[o for _, o in add_objs], reason=reason)
            added_ok.extend([rid for rid, _ in add_objs])
        except Exception as e:
            if len(add_objs) > 1:
                for rid, r_obj in add_objs:
                    try:
                        await member.add_roles(r_obj, reason=reason)
                        added_ok.append(rid)
                    except Exception as e_single:
                        errors.append(f"Error añadiendo <@&{rid}>: {e_single}")
            else:
                errors.append(f"Error añadiendo roles: {e}")

    if rem_objs:
        try:
            await member.remove_roles(*[o for _, o in rem_objs], reason=reason)
            removed_ok.extend([rid for rid, _ in rem_objs])
        except Exception as e:
            if len(rem_objs) > 1:
                for rid, r_obj in rem_objs:
                    try:
                        await member.remove_roles(r_obj, reason=reason)
                        removed_ok.append(rid)
                    except Exception as e_single:
                        errors.append(f"Error retirando <@&{rid}>: {e_single}")
            else:
                errors.append(f"Error retirando roles: {e}")

    return added_ok, removed_ok, errors


class AutoRoleSelect(discord.ui.Select):
    """Menú desplegable público persistente para una categoría de Auto-Roles (Modo Interruptor / Toggle)."""

    def __init__(self, cat_key: str, row: int = 0):
        self.cat_key = cat_key
        cat = AUTOROLES_CATALOG[cat_key]
        options = [
            discord.SelectOption(
                label=name,
                value=str(rid),
                emoji=emoji,
                description=desc[:100],
            )
            for emoji, rid, name, desc in cat["roles"]
        ]
        super().__init__(
            custom_id=f"autoroles:select:{cat_key}",
            placeholder=cat["placeholder"],
            min_values=1,
            max_values=len(options),
            options=options,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Este menú solo funciona dentro del servidor.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        member = await _resolve_guild_member(interaction)
        if not member:
            await interaction.followup.send("❌ No se pudo encontrar tu perfil de miembro en el servidor.", ephemeral=True)
            return

        current_ids = {r.id for r in getattr(member, "roles", [])}
        to_add_ids, to_remove_ids = compute_autorole_toggle(current_ids, list(self.values), ALL_AUTOROLE_IDS)

        added_ok, removed_ok, errors = await _apply_role_changes_to_member(
            interaction.guild,
            member,
            to_add_ids,
            to_remove_ids,
            reason=f"Auto-Roles Asistente ({self.cat_key})",
        )

        # Actualizar conjunto de roles tras la operación
        updated_ids = (current_ids | set(added_ok)) - set(removed_ok)

        # Refrescar el View del mensaje público para limpiar la selección visual en el cliente de Discord
        if interaction.message:
            try:
                select_count = 0
                has_buttons = False
                for row_comp in getattr(interaction.message, "components", []):
                    for child in getattr(row_comp, "children", []):
                        cid = getattr(child, "custom_id", "") or ""
                        if cid.startswith("autoroles:select:"):
                            select_count += 1
                        elif cid.startswith("autoroles:btn:"):
                            has_buttons = True
                if select_count == 1:
                    fresh_view = AutoRoleCategoryView(self.cat_key, include_buttons=has_buttons)
                else:
                    fresh_view = AutoRolesPersistentView()
                await interaction.message.edit(view=fresh_view)
            except Exception:
                pass

        cat = AUTOROLES_CATALOG[self.cat_key]
        lines = []
        if added_ok:
            mentions = ", ".join(f"{AUTOROLE_INFO_BY_ID[rid]['emoji']} <@&{rid}>" for rid in added_ok)
            lines.append(f"✅ **Roles añadidos:** {mentions}")
        if removed_ok:
            mentions = ", ".join(f"{AUTOROLE_INFO_BY_ID[rid]['emoji']} <@&{rid}>" for rid in removed_ok)
            lines.append(f"❌ **Roles retirados:** {mentions}")
        if errors:
            lines.append("⚠️ " + " | ".join(errors))
        if not lines:
            lines.append("ℹ️ No se realizaron cambios de roles.")

        cat_active = [
            f"{emoji} <@&{rid}>"
            for emoji, rid, _name, _desc in cat["roles"]
            if rid in updated_ids
        ]
        lines.append(
            f"\n🎭 **Tus roles actuales en {cat['title']}:**\n"
            + (" · ".join(cat_active) if cat_active else "*Ninguno activo en esta categoría*")
        )

        embed = discord.Embed(
            title="⚡ Auto-Roles Actualizados",
            description="\n".join(lines),
            color=0x10B981 if added_ok and not removed_ok else (0xF59E0B if removed_ok else 0x3B82F6),
        )
        embed.set_footer(text="💡 Tip: Vuelve a elegir un rol si quieres quitártelo, o pulsa '📋 Mis Roles' para ver tu lista marcada.")
        _bot_log(f"🎭 [Auto-Roles] {member.display_name} ({self.cat_key}): +{len(added_ok)} / -{len(removed_ok)}")
        await interaction.followup.send(embed=embed, ephemeral=True)


class PersonalCategorySelect(discord.ui.Select):
    """Menú desplegable efímero personalizado con las opciones actuales del usuario premarcadas (default=True)."""

    def __init__(self, cat_key: str, current_role_ids: set, row: int = 0):
        self.cat_key = cat_key
        cat = AUTOROLES_CATALOG[cat_key]
        options = [
            discord.SelectOption(
                label=name,
                value=str(rid),
                emoji=emoji,
                description=desc[:100],
                default=(rid in current_role_ids),
            )
            for emoji, rid, name, desc in cat["roles"]
        ]
        super().__init__(
            custom_id=f"autoroles:personal:{cat_key}",
            placeholder=f"✏️ Editar {cat['title']} (marca/desmarca)",
            min_values=0,
            max_values=len(options),
            options=options,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Este menú solo funciona en un servidor.", ephemeral=True)
            return

        await interaction.response.defer()
        member = await _resolve_guild_member(interaction)
        if not member:
            await interaction.followup.send("❌ No se pudo encontrar tu perfil de miembro.", ephemeral=True)
            return

        current_ids = {r.id for r in getattr(member, "roles", [])}
        cat_role_ids = [rid for _emoji, rid, _name, _desc in AUTOROLES_CATALOG[self.cat_key]["roles"]]
        to_add_ids, to_remove_ids = compute_autorole_category_sync(current_ids, list(self.values), cat_role_ids)

        added_ok, removed_ok, errors = await _apply_role_changes_to_member(
            interaction.guild,
            member,
            to_add_ids,
            to_remove_ids,
            reason=f"Auto-Roles Vista Personal ({self.cat_key})",
        )

        updated_ids = (current_ids | set(added_ok)) - set(removed_ok)
        summary_lines = []
        if added_ok:
            summary_lines.append("✅ **Añadidos:** " + ", ".join(f"<@&{rid}>" for rid in added_ok))
        if removed_ok:
            summary_lines.append("❌ **Retirados:** " + ", ".join(f"<@&{rid}>" for rid in removed_ok))
        if errors:
            summary_lines.append("⚠️ " + " | ".join(errors))
        if not summary_lines:
            summary_lines.append("ℹ️ *Sin cambios en esta categoría.*")

        new_embed = build_personal_autoroles_embed(member.display_name, updated_ids, "\n".join(summary_lines))
        new_view = PersonalAutoRolesView(updated_ids)
        _bot_log(f"🎭 [Auto-Roles Personal] {member.display_name} ({self.cat_key}): +{len(added_ok)} / -{len(removed_ok)}")
        await interaction.edit_original_response(embed=new_embed, view=new_view)


class PersonalAutoRolesView(discord.ui.View):
    """Vista efímera personalizada persistente donde el usuario ve sus roles premarcados con ✅ y puede editarlos."""

    def __init__(self, current_role_ids: set = None):
        super().__init__(timeout=None)
        role_ids_set = set(current_role_ids) if current_role_ids else set()
        for idx, cat_key in enumerate(AUTOROLES_CATALOG.keys()):
            self.add_item(PersonalCategorySelect(cat_key, role_ids_set, row=idx))


async def _handle_mis_roles_button(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("❌ Solo disponible en el servidor.", ephemeral=True)
        return
    member = await _resolve_guild_member(interaction)
    if not member:
        await interaction.response.send_message("❌ No se pudo cargar tu perfil de miembro.", ephemeral=True)
        return
    current_ids = {r.id for r in getattr(member, "roles", [])}
    embed = build_personal_autoroles_embed(member.display_name, current_ids)
    view = PersonalAutoRolesView(current_ids)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def _handle_limpiar_autoroles_button(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("❌ Solo disponible en el servidor.", ephemeral=True)
        return
    member = await _resolve_guild_member(interaction)
    if not member:
        await interaction.response.send_message("❌ No se pudo cargar tu perfil de miembro.", ephemeral=True)
        return

    current_ids = {r.id for r in getattr(member, "roles", [])}
    active_autoroles = [rid for rid in ALL_AUTOROLE_IDS if rid in current_ids]
    if not active_autoroles:
        await interaction.response.send_message(
            "ℹ️ No tienes ningún autorol de juegos, géneros o hobbies equipado ahora mismo.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)
    _, removed_ok, errors = await _apply_role_changes_to_member(
        interaction.guild,
        member,
        [],
        active_autoroles,
        reason="Auto-Roles: Limpieza total solicitada por el usuario",
    )
    mentions = ", ".join(f"<@&{rid}>" for rid in removed_ok)
    desc = f"🗑️ Se han retirado **{len(removed_ok)}** autoroles de tu perfil:\n{mentions}\n\n*(Tus roles de nivel, economía y administración no se tocan nunca)*."
    if errors:
        desc += "\n⚠️ " + " | ".join(errors)
    embed = discord.Embed(title="🧹 Auto-Roles Limpiados", description=desc, color=0xEF4444)
    _bot_log(f"🧹 [Auto-Roles] {member.display_name} limpió todos sus autoroles ({len(removed_ok)} retirados).")
    await interaction.followup.send(embed=embed, ephemeral=True)


class AutoRolesPersistentView(discord.ui.View):
    """Panel maestro persistente 24/7 con los 3 menús desplegables de categorías y botones de gestión."""

    def __init__(self):
        super().__init__(timeout=None)
        for idx, cat_key in enumerate(AUTOROLES_CATALOG.keys()):
            self.add_item(AutoRoleSelect(cat_key, row=idx))

        btn_mis_roles = discord.ui.Button(
            label="Mis Roles / Vista Personal (✅)",
            style=discord.ButtonStyle.primary,
            emoji="📋",
            custom_id="autoroles:btn:mis_roles",
            row=3,
        )
        btn_mis_roles.callback = _handle_mis_roles_button
        self.add_item(btn_mis_roles)

        btn_limpiar = discord.ui.Button(
            label="Quitar Todos Mis Autoroles",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id="autoroles:btn:limpiar",
            row=3,
        )
        btn_limpiar.callback = _handle_limpiar_autoroles_button
        self.add_item(btn_limpiar)


class AutoRoleCategoryView(discord.ui.View):
    """Vista persistente para un mensaje individual de una sola categoría (modo separado)."""

    def __init__(self, cat_key: str, include_buttons: bool = False):
        super().__init__(timeout=None)
        self.add_item(AutoRoleSelect(cat_key, row=0))
        if include_buttons:
            btn_mis_roles = discord.ui.Button(
                label="Mis Roles / Vista Personal (✅)",
                style=discord.ButtonStyle.primary,
                emoji="📋",
                custom_id="autoroles:btn:mis_roles",
                row=1,
            )
            btn_mis_roles.callback = _handle_mis_roles_button
            self.add_item(btn_mis_roles)

            btn_limpiar = discord.ui.Button(
                label="Quitar Todos Mis Autoroles",
                style=discord.ButtonStyle.danger,
                emoji="🗑️",
                custom_id="autoroles:btn:limpiar",
                row=1,
            )
            btn_limpiar.callback = _handle_limpiar_autoroles_button
            self.add_item(btn_limpiar)


def is_admin_or_mod(member_or_user) -> bool:
    """Verifica si el usuario es Administrador, Moderador con gestión de roles/servidor, Joselito o Iván."""
    uid = getattr(member_or_user, "id", 0)
    if uid in (857923274771136522, 1208551025578082367):
        return True
    perms = getattr(member_or_user, "guild_permissions", None)
    if perms and (perms.administrator or perms.manage_roles or perms.manage_guild):
        return True
    roles = getattr(member_or_user, "roles", [])
    return any(getattr(r, "id", 0) in (1446145987335950549, 1536783626199633940, 1446145803432235120) for r in roles)


# --- SISTEMA DE SUGERENCIAS COMUNITARIAS 24/7 (REEMPLAZO DE CARL-BOT EN #💡sugerencias💡) ---
SUGGESTIONS_CHANNEL_ID = 1537582722812481696
# Estado de votos en memoria por message_id: {msg_id: {"up": set(user_ids), "down": set(user_ids), "base_up": int, "base_down": int}}
SUGGESTION_VOTES_STATE = {}


def _get_votes_state_dict() -> dict:
    bs = _bs()
    return getattr(bs, "SUGGESTION_VOTES_STATE", SUGGESTION_VOTES_STATE)


def _extract_votes_from_embed(embed: discord.Embed) -> tuple:
    """Extrae los contadores (up, down) actuales desde el campo Votos del embed como respaldo tras reinicios."""
    if not embed or not getattr(embed, "fields", None):
        return 0, 0
    for f in embed.fields:
        if "Votos" in (f.name or ""):
            m = re.search(r"👍\s*\*\*(\d+)\*\*.*?👎\s*\*\*(\d+)\*\*", f.value or "")
            if m:
                return int(m.group(1)), int(m.group(2))
    return 0, 0


def _extract_vote_state_from_embed(embed: discord.Embed) -> dict:
    """Reconstruye el estado completo de votantes (sets 'up' y 'down' + base_up/base_down) directamente
    desde el embed de la sugerencia para que ni siquiera un reinicio o redespliegue de Render permita votos duplicados."""
    b_up, b_down = _extract_votes_from_embed(embed)
    up_ids = set()
    down_ids = set()
    if embed and getattr(embed, "fields", None):
        for f in embed.fields:
            if "Votos" in (f.name or ""):
                for line in (f.value or "").splitlines()[1:]:
                    line_s = line.strip()
                    if line_s.startswith("👍:"):
                        up_ids.update(int(x) for x in re.findall(r"<@!?(\d+)>", line_s))
                    elif line_s.startswith("👎:"):
                        down_ids.update(int(x) for x in re.findall(r"<@!?(\d+)>", line_s))

    # Si no había línea explícita de votantes pero el footer tiene Autor ID y hay al menos 1 voto a favor, atribuir al autor
    if not up_ids and not down_ids and b_up >= 1 and embed:
        footer_txt = getattr(getattr(embed, "footer", None), "text", "") or ""
        m_auth = re.search(r"Autor ID:\s*(\d+)", footer_txt)
        if m_auth:
            up_ids.add(int(m_auth.group(1)))

    base_up = max(0, b_up - len(up_ids))
    base_down = max(0, b_down - len(down_ids))
    return {"up": up_ids, "down": down_ids, "base_up": base_up, "base_down": base_down}


def _update_suggestion_embed_votes(embed: discord.Embed, up_count: int, down_count: int, up_ids: set = None, down_ids: set = None) -> discord.Embed:
    """Actualiza el campo de votos y el registro de votantes en el embed de una sugerencia."""
    d = embed.to_dict()
    fields = d.get("fields", [])
    lines = [f"👍 **{up_count}** a favor · 👎 **{down_count}** en contra"]
    if up_ids:
        lines.append("👍: " + ", ".join(f"<@{uid}>" for uid in sorted(up_ids)[:25]))
    if down_ids:
        lines.append("👎: " + ", ".join(f"<@{uid}>" for uid in sorted(down_ids)[:25]))
    vote_str = "\n".join(lines)
    updated = False
    for f in fields:
        if "Votos" in f.get("name", ""):
            f["value"] = vote_str
            updated = True
            break
    if not updated:
        fields.append({"name": "🗳️ Votos", "value": vote_str, "inline": True})
    d["fields"] = fields
    return discord.Embed.from_dict(d)


class SuggestionDecisionModal(discord.ui.Modal):
    """Modal para que un administrador apruebe o rechace una sugerencia indicando el motivo."""

    def __init__(self, action: str, suggestion_message: discord.Message):
        title = "✅ Aprobar Sugerencia" if action == "approve" else "❌ Rechazar Sugerencia"
        super().__init__(title=title)
        self.action = action
        self.suggestion_message = suggestion_message
        self.reason_input = discord.ui.TextInput(
            label="Motivo o comentario de la administración",
            style=discord.TextStyle.paragraph,
            placeholder="Ej: Todos los @🔮Pendejo Veterano🔮 votaron a favor / Inviable técnicamente...",
            required=False,
            max_length=500,
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        target_msg = getattr(interaction, "message", None) or self.suggestion_message
        if not target_msg or not getattr(target_msg, "embeds", None):
            await interaction.response.send_message("❌ No se encontró el embed de la sugerencia.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        old_embed = target_msg.embeds[0]
        d = old_embed.to_dict()
        num_match = re.search(r"#(\d+)", d.get("title", ""))
        sug_num = num_match.group(1) if num_match else "?"
        reason_text = (self.reason_input.value or "").strip() or "Sin motivo especificado"
        admin_name = interaction.user.display_name

        if self.action == "approve":
            d["title"] = f"✅ Sugerencia #{sug_num} Aprobada"
            d["color"] = 0x10B981
            status_val = f"✅ Aprobada por **{admin_name}**"
        else:
            d["title"] = f"❌ Sugerencia #{sug_num} Rechazada"
            d["color"] = 0xEF4444
            status_val = f"❌ Rechazada por **{admin_name}**"

        fields = d.get("fields", [])
        new_fields = []
        for f in fields:
            if "Estado" in f.get("name", ""):
                new_fields.append({"name": "📊 Estado", "value": status_val, "inline": True})
            elif not f.get("name", "").startswith("⚖️ Motivo de"):
                new_fields.append(f)
        new_fields.append({"name": f"⚖️ Motivo de {admin_name}", "value": reason_text, "inline": False})
        d["fields"] = new_fields

        up_c, down_c = _extract_votes_from_embed(old_embed)
        closed_view = SuggestionPersistentView(up_count=up_c, down_count=down_c, disabled=True)
        await target_msg.edit(embed=discord.Embed.from_dict(d), view=closed_view)
        _bot_log(f"💡 [Sugerencia #{sug_num}] {'Aprobada' if self.action == 'approve' else 'Rechazada'} por {admin_name}: {reason_text}")
        await interaction.followup.send(
            f"✅ Has marcado la **Sugerencia #{sug_num}** como **{'Aprobada' if self.action == 'approve' else 'Rechazada'}**.",
            ephemeral=True,
        )


class SuggestionPersistentView(discord.ui.View):
    """Vista interactiva persistente 24/7 para votar y moderar sugerencias de la comunidad."""

    def __init__(self, up_count: int = 0, down_count: int = 0, disabled: bool = False):
        super().__init__(timeout=None)
        btn_up = discord.ui.Button(
            label=f"A favor ({up_count})",
            style=discord.ButtonStyle.success,
            emoji="👍",
            custom_id="sugerencia:vote:up",
            disabled=disabled,
            row=0,
        )
        btn_up.callback = self.on_vote_up
        self.add_item(btn_up)

        btn_down = discord.ui.Button(
            label=f"En contra ({down_count})",
            style=discord.ButtonStyle.secondary,
            emoji="👎",
            custom_id="sugerencia:vote:down",
            disabled=disabled,
            row=0,
        )
        btn_down.callback = self.on_vote_down
        self.add_item(btn_down)

        btn_approve = discord.ui.Button(
            label="Aprobar",
            style=discord.ButtonStyle.primary,
            emoji="✅",
            custom_id="sugerencia:mod:approve",
            disabled=disabled,
            row=0,
        )
        btn_approve.callback = self.on_approve
        self.add_item(btn_approve)

        btn_reject = discord.ui.Button(
            label="Rechazar",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            custom_id="sugerencia:mod:reject",
            disabled=disabled,
            row=0,
        )
        btn_reject.callback = self.on_reject
        self.add_item(btn_reject)

    async def _handle_vote(self, interaction: discord.Interaction, direction: str):
        msg = interaction.message
        if not msg or not msg.embeds:
            await interaction.response.send_message("❌ No se pudo leer la sugerencia.", ephemeral=True)
            return

        emb = msg.embeds[0]
        votes_dict = _get_votes_state_dict()
        state = votes_dict.get(msg.id)
        if state is None:
            state = _extract_vote_state_from_embed(emb)
            votes_dict[msg.id] = state

        uid = interaction.user.id
        if direction == "up":
            if uid in state["up"]:
                state["up"].remove(uid)
                notice = "ℹ️ Has retirado tu voto a favor."
            else:
                state["down"].discard(uid)
                state["up"].add(uid)
                notice = "👍 ¡Voto a favor registrado!"
        else:
            if uid in state["down"]:
                state["down"].remove(uid)
                notice = "ℹ️ Has retirado tu voto en contra."
            else:
                state["up"].discard(uid)
                state["down"].add(uid)
                notice = "👎 Voto en contra registrado."

        up_total = state["base_up"] + len(state["up"])
        down_total = state["base_down"] + len(state["down"])
        new_emb = _update_suggestion_embed_votes(emb, up_total, down_total, state["up"], state["down"])
        new_view = SuggestionPersistentView(up_count=up_total, down_count=down_total, disabled=False)
        await interaction.response.edit_message(embed=new_emb, view=new_view)
        await interaction.followup.send(notice, ephemeral=True)

    async def on_vote_up(self, interaction: discord.Interaction):
        await self._handle_vote(interaction, "up")

    async def on_vote_down(self, interaction: discord.Interaction):
        await self._handle_vote(interaction, "down")

    async def on_approve(self, interaction: discord.Interaction):
        member = await _resolve_guild_member(interaction)
        if not is_admin_or_mod(member or interaction.user):
            await interaction.response.send_message("❌ Solo los administradores pueden aprobar o rechazar sugerencias.", ephemeral=True)
            return
        await interaction.response.send_modal(SuggestionDecisionModal("approve", interaction.message))

    async def on_reject(self, interaction: discord.Interaction):
        member = await _resolve_guild_member(interaction)
        if not is_admin_or_mod(member or interaction.user):
            await interaction.response.send_message("❌ Solo los administradores pueden aprobar o rechazar sugerencias.", ephemeral=True)
            return
        await interaction.response.send_modal(SuggestionDecisionModal("reject", interaction.message))


async def _get_next_suggestion_number(channel: discord.TextChannel) -> int:
    """Obtiene el siguiente número correlativo de sugerencia leyendo el historial de #sugerencias."""
    highest = 8  # Carl-bot llegó hasta Suggestion #8
    try:
        async for m in channel.history(limit=35):
            for emb in getattr(m, "embeds", []):
                t = getattr(emb, "title", "") or ""
                match = re.search(r"(?:Suggestion|Sugerencia)\s*#(\d+)", t, re.IGNORECASE)
                if match:
                    num = int(match.group(1))
                    if num > highest:
                        highest = num
    except Exception:
        pass
    return highest + 1
