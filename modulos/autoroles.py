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
        "description": "Pulsa los botones de abajo para ver tus roles activos y elegir tus dispositivos o aficiones (con ✅ en los que ya tienes):",
        "color": 0x5865F2,
        "roles": [
            ("💻", 1537577523011911772, "PC", None),
            ("🎮", 1537593228209950720, "Consola", None),
            ("🍿", 1537592958747148368, "Cine", "Películas y series"),
            ("📖", 1537593474721906759, "lectura", "Libros y novelas"),
            ("🤝", 1537577153862967366, "Co-op", "Juegos cooperativos"),
            ("📚", 1537593587670327356, "manga", None),
            ("🐉", 1537593562772799498, "anime", None),
            ("🇰🇷", 1537593440303325275, "Manhwa", None),
            ("👥", 1537593280232165396, "Familia de Steam", None),
            ("⚽", 1537594961837428776, "Deportes", None),
            ("🌙", 1537593627105038466, "nocturno", "Charlas de noche"),
            ("🇪🇸", 1537594201326489690, "Español", None),
            ("🇬🇧", 1537594249720242216, "ingles", None),
            ("⚡", 1537593357713412146, "Tryhard", "Juego competitivo"),
            ("☕", 1537593381830529104, "Casual", "Jugar de chill"),
        ],
    },
    "generos": {
        "title": "🎯 GÉNEROS DE JUEGOS Y ALERTAS",
        "placeholder": "🎯 Géneros de Juegos y Alertas (elige uno o varios)",
        "description": "Pulsa los botones de abajo para seleccionar los géneros de videojuegos y avisos que te interesen:",
        "color": 0x10B981,
        "roles": [
            ("🎯", 1537591932010766367, "Shooters", None),
            ("🌲", 1537592360291008612, "Survival", None),
            ("🎒", 1537592390142132396, "Extraction", None),
            ("💀", 1537592856380706906, "Roguelike", None),
            ("🗡️", 1537595229627224124, "RPG", None),
            ("🤼", 1537594274093465683, "Peleas", None),
            ("🚨", 1537594120078368768, "Falta Uno", "Avisos para completar partida"),
            ("🃏", 1537595303346053221, "Cartas", None),
            ("♟️", 1537595282190237706, "Estrategia", None),
            ("⭐", 1537914650274963598, "recomendaciones de juegos", None),
            ("🔥", 1537595250695209000, "Soulslike", None),
            ("🕹️", 1537592919815360632, "Indie", None),
            ("📈", 1537934178283290664, "incremental", None),
        ],
    },
    "juegos": {
        "title": "🕹️ JUEGOS ESPECÍFICOS",
        "placeholder": "🕹️ Juegos Específicos (elige uno o varios)",
        "description": "Pulsa los botones de abajo para seleccionar los juegos a los que juegas y enterarte cuando se arme partida:",
        "color": 0xF59E0B,
        "roles": [
            ("📱", 1537591875656224820, "Brawl Stars", None),
            ("🤖", 1537914271483297812, "ARC Raiders", None),
            ("🪂", 1537914329167302718, "Fornite", None),
            ("💥", 1537914381277462719, "The finals", None),
            ("📦", 1537914482724970576, "R.E.P.O", None),
            ("🌻", 1537914562823594024, "PVZ GW2", "Plants vs. Zombies GW2"),
            ("⛰️", 1537914820223828038, "PEAK", None),
            ("🚶", 1548716906213543986, "Big Walk", None),
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


def build_autoroles_category_embed(cat_key: str, guild: discord.Guild = None, include_footer: bool = False) -> discord.Embed:
    """Construye el embed visual de una categoría de Auto-Roles con menciones nativas <@&ID> y contadores de miembros en tiempo real."""
    cat = AUTOROLES_CATALOG[cat_key]
    lines = []
    for emoji, rid, _name, desc in cat["roles"]:
        count_str = ""
        if guild:
            role = guild.get_role(rid)
            count = len(role.members) if (role and hasattr(role, "members")) else 0
            count_str = f" • 👥 **{count}**"
        desc_str = f" — *{desc}*" if desc else ""
        lines.append(f"{emoji} <@&{rid}>{count_str}{desc_str}")

    embed = discord.Embed(
        title=cat["title"],
        description=f"{cat['description']}\n\n" + "\n".join(lines),
        color=cat["color"],
    )
    if include_footer:
        member_cnt = f" • 👥 {len(guild.members)} miembros en el servidor" if (guild and hasattr(guild, "members")) else ""
        embed.set_footer(
            text=f"⚡ Auto-Roles 24/7 de Asistente{member_cnt} • Pulsa los botones para abrir tu menú personal con tus roles premarcados (✅)"
        )
    return embed


def build_autoroles_all_embeds(guild: discord.Guild = None) -> list:
    """Construye los 3 embeds oficiales de Auto-Roles para el panel unificado con contadores en tiempo real."""
    keys = list(AUTOROLES_CATALOG.keys())
    return [build_autoroles_category_embed(k, guild=guild, include_footer=(i == len(keys) - 1)) for i, k in enumerate(keys)]


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


def build_category_personal_embed(cat_key: str, member_display_name: str, current_role_ids: set, changes_summary: str = "") -> discord.Embed:
    """Construye el embed efímero para una sola categoría con los roles activos del usuario."""
    cat = AUTOROLES_CATALOG[cat_key]
    active_in_cat = [
        f"{emoji} <@&{rid}>"
        for emoji, rid, _name, _desc in cat["roles"]
        if rid in current_role_ids
    ]
    desc_parts = []
    if changes_summary:
        desc_parts.append(changes_summary)
    desc_parts.append(
        f"Selecciona tus roles para **{cat['title']}** en el menú desplegable de abajo.\n"
        f"Los roles que ya tienes equipados aparecen **marcados con ✅** en el menú: marca o desmarca los que quieras."
    )
    embed = discord.Embed(
        title=f"🎭 {cat['title']} — {member_display_name}",
        description="\n\n".join(desc_parts),
        color=cat.get("color", 0x8B5CF6),
    )
    val = " · ".join(active_in_cat) if active_in_cat else "*Ninguno seleccionado en esta categoría*"
    embed.add_field(name="Tus roles activos en esta categoría", value=val, inline=False)
    embed.set_footer(text="Vista personal efímera • Solo tú puedes ver y modificar estos roles")
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

    def __init__(self, cat_key: str, row: int = 0, guild: discord.Guild = None):
        self.cat_key = cat_key
        self.guild = guild
        cat = AUTOROLES_CATALOG[cat_key]
        options = []
        for emoji, rid, name, desc in cat["roles"]:
            count_text = ""
            if guild:
                role = guild.get_role(rid)
                count = len(role.members) if (role and hasattr(role, "members")) else 0
                count_text = f"{count} {'miembro' if count == 1 else 'miembros'}"
            full_desc = f"{count_text} • {desc}" if (count_text and desc) else (count_text or desc or None)
            options.append(
                discord.SelectOption(
                    label=name,
                    value=str(rid),
                    emoji=emoji,
                    description=full_desc[:100] if full_desc else None,
                )
            )
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

        # Refrescar el View y los embeds del mensaje público para limpiar la selección visual en el cliente y actualizar contadores
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
                    fresh_embed = build_autoroles_category_embed(self.cat_key, guild=interaction.guild, include_footer=has_buttons)
                    fresh_view = AutoRoleCategoryView(self.cat_key, include_buttons=has_buttons, guild=interaction.guild)
                    await interaction.message.edit(embed=fresh_embed, view=fresh_view)
                else:
                    fresh_embeds = build_autoroles_all_embeds(guild=interaction.guild)
                    fresh_view = AutoRolesPersistentView(guild=interaction.guild)
                    await interaction.message.edit(embeds=fresh_embeds, view=fresh_view)
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

    def __init__(
        self,
        cat_key: str,
        current_role_ids: set,
        row: int = 0,
        guild: discord.Guild = None,
        public_message_id: int = None,
        channel_id: int = None,
    ):
        self.cat_key = cat_key
        self.guild = guild
        self.public_message_id = public_message_id
        self.channel_id = channel_id
        cat = AUTOROLES_CATALOG[cat_key]
        options = []
        for emoji, rid, name, desc in cat["roles"]:
            count_text = ""
            if guild:
                role = guild.get_role(rid)
                count = len(role.members) if (role and hasattr(role, "members")) else 0
                count_text = f"{count} {'miembro' if count == 1 else 'miembros'}"
            full_desc = f"{count_text} • {desc}" if (count_text and desc) else (count_text or desc or None)
            options.append(
                discord.SelectOption(
                    label=name,
                    value=str(rid),
                    emoji=emoji,
                    description=full_desc[:100] if full_desc else None,
                    default=(rid in current_role_ids),
                )
            )
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

        # Refrescar mensaje público en el canal para actualizar contadores en tiempo real
        if self.public_message_id:
            try:
                ch = interaction.guild.get_channel(self.channel_id) or interaction.channel
                if ch:
                    pub_msg = await ch.fetch_message(self.public_message_id)
                    if pub_msg:
                        fresh_embeds = build_autoroles_all_embeds(guild=interaction.guild)
                        fresh_view = AutoRolesPersistentView(guild=interaction.guild)
                        await pub_msg.edit(embeds=fresh_embeds, view=fresh_view)
            except Exception:
                pass

        summary_lines = []
        if added_ok:
            summary_lines.append("✅ **Añadidos:** " + ", ".join(f"<@&{rid}>" for rid in added_ok))
        if removed_ok:
            summary_lines.append("❌ **Retirados:** " + ", ".join(f"<@&{rid}>" for rid in removed_ok))
        if errors:
            summary_lines.append("⚠️ " + " | ".join(errors))
        if not summary_lines:
            summary_lines.append("ℹ️ *Sin cambios en esta categoría.*")

        is_single_category = bool(self.view and len(self.view.children) <= 2)
        if is_single_category:
            new_embed = build_category_personal_embed(self.cat_key, member.display_name, updated_ids, "\n".join(summary_lines))
            new_view = SingleCategoryPersonalView(
                self.cat_key,
                updated_ids,
                guild=interaction.guild,
                public_message_id=self.public_message_id,
                channel_id=self.channel_id,
            )
        else:
            new_embed = build_personal_autoroles_embed(member.display_name, updated_ids, "\n".join(summary_lines))
            new_view = PersonalAutoRolesView(
                updated_ids,
                guild=interaction.guild,
                public_message_id=self.public_message_id,
                channel_id=self.channel_id,
            )
        _bot_log(f"🎭 [Auto-Roles Personal] {member.display_name} ({self.cat_key}): +{len(added_ok)} / -{len(removed_ok)}")
        await interaction.edit_original_response(embed=new_embed, view=new_view)


class SingleCategoryPersonalView(discord.ui.View):
    """Vista efímera para editar una categoría específica con checks premarcados (default=True)."""

    def __init__(
        self,
        cat_key: str,
        current_role_ids: set = None,
        guild: discord.Guild = None,
        public_message_id: int = None,
        channel_id: int = None,
    ):
        super().__init__(timeout=None)
        self.cat_key = cat_key
        self.guild = guild
        self.public_message_id = public_message_id
        self.channel_id = channel_id
        role_ids_set = set(current_role_ids) if current_role_ids else set()
        self.add_item(
            PersonalCategorySelect(
                cat_key,
                role_ids_set,
                row=0,
                guild=guild,
                public_message_id=public_message_id,
                channel_id=channel_id,
            )
        )

        btn_todas = discord.ui.Button(
            label="Ver Todas las Categorías",
            style=discord.ButtonStyle.secondary,
            emoji="📋",
            row=1,
        )

        async def _on_todas(btn_inter: discord.Interaction):
            mem = await _resolve_guild_member(btn_inter)
            c_ids = {r.id for r in getattr(mem, "roles", [])} if mem else role_ids_set
            all_emb = build_personal_autoroles_embed(mem.display_name if mem else "Usuario", c_ids)
            all_view = PersonalAutoRolesView(
                c_ids,
                guild=guild or btn_inter.guild,
                public_message_id=public_message_id,
                channel_id=channel_id,
            )
            await btn_inter.response.edit_message(embed=all_emb, view=all_view)

        btn_todas.callback = _on_todas
        self.add_item(btn_todas)


class PersonalAutoRolesView(discord.ui.View):
    """Vista efímera personalizada persistente donde el usuario ve sus roles premarcados con ✅ y puede editarlos."""

    def __init__(
        self,
        current_role_ids: set = None,
        guild: discord.Guild = None,
        public_message_id: int = None,
        channel_id: int = None,
    ):
        super().__init__(timeout=None)
        self.public_message_id = public_message_id
        self.channel_id = channel_id
        role_ids_set = set(current_role_ids) if current_role_ids else set()
        for idx, cat_key in enumerate(AUTOROLES_CATALOG.keys()):
            self.add_item(
                PersonalCategorySelect(
                    cat_key,
                    role_ids_set,
                    row=idx,
                    guild=guild,
                    public_message_id=public_message_id,
                    channel_id=channel_id,
                )
            )


async def _handle_category_button(interaction: discord.Interaction):
    """Abre el menú efímero personal de una categoría concreta con checks premarcados (default=True)."""
    if not interaction.guild:
        await interaction.response.send_message("❌ Solo disponible en el servidor.", ephemeral=True)
        return
    cat_key = interaction.data.get("custom_id", "").split(":")[-1]
    if cat_key not in AUTOROLES_CATALOG:
        await interaction.response.send_message("❌ Categoría no encontrada.", ephemeral=True)
        return

    member = await _resolve_guild_member(interaction)
    if not member:
        await interaction.response.send_message("❌ No se pudo cargar tu perfil de miembro.", ephemeral=True)
        return

    current_ids = {r.id for r in getattr(member, "roles", [])}
    embed = build_category_personal_embed(cat_key, member.display_name, current_ids)
    view = SingleCategoryPersonalView(
        cat_key,
        current_ids,
        guild=interaction.guild,
        public_message_id=interaction.message.id if interaction.message else None,
        channel_id=interaction.channel_id,
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


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
    view = PersonalAutoRolesView(
        current_ids,
        guild=interaction.guild,
        public_message_id=interaction.message.id if interaction.message else None,
        channel_id=interaction.channel_id,
    )
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

    if interaction.message:
        try:
            fresh_embeds = build_autoroles_all_embeds(guild=interaction.guild)
            fresh_view = AutoRolesPersistentView(guild=interaction.guild)
            await interaction.message.edit(embeds=fresh_embeds, view=fresh_view)
        except Exception:
            pass

    mentions = ", ".join(f"<@&{rid}>" for rid in removed_ok)
    desc = f"🗑️ Se han retirado **{len(removed_ok)}** autoroles de tu perfil:\n{mentions}\n\n*(Tus roles de nivel, economía y administración no se tocan nunca)*."
    if errors:
        desc += "\n⚠️ " + " | ".join(errors)
    embed = discord.Embed(title="🧹 Auto-Roles Limpiados", description=desc, color=0xEF4444)
    _bot_log(f"🧹 [Auto-Roles] {member.display_name} limpió todos sus autoroles ({len(removed_ok)} retirados).")
    await interaction.followup.send(embed=embed, ephemeral=True)


async def _handle_refrescar_autoroles_button(interaction: discord.Interaction):
    """Refresca manualmente los contadores de miembros en los embeds públicos."""
    if not interaction.guild:
        await interaction.response.send_message("❌ Solo disponible en el servidor.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    if interaction.message:
        try:
            cat_found = None
            has_other_cats = False
            for row_comp in getattr(interaction.message, "components", []):
                for child in getattr(row_comp, "children", []):
                    cid = getattr(child, "custom_id", "") or ""
                    if cid.startswith("autoroles:btn:cat:"):
                        k = cid.split(":")[-1]
                        if cat_found and cat_found != k:
                            has_other_cats = True
                        cat_found = k

            if cat_found and not has_other_cats:
                fresh_embed = build_autoroles_category_embed(cat_found, guild=interaction.guild, include_footer=True)
                fresh_view = AutoRoleCategoryView(cat_found, include_buttons=True, guild=interaction.guild)
                await interaction.message.edit(embed=fresh_embed, view=fresh_view)
            else:
                fresh_embeds = build_autoroles_all_embeds(guild=interaction.guild)
                fresh_view = AutoRolesPersistentView(guild=interaction.guild)
                await interaction.message.edit(embeds=fresh_embeds, view=fresh_view)
            _bot_log(f"🔄 [Auto-Roles] Contadores de roles actualizados por {interaction.user.display_name}.")
            await interaction.followup.send("✅ **Contadores actualizados:** los números de miembros reflejan el censo en tiempo real.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"⚠️ Error actualizando los contadores: {e}", ephemeral=True)
            return
    await interaction.followup.send("ℹ️ No se pudo detectar el mensaje a refrescar.", ephemeral=True)


class AutoRolesPersistentView(discord.ui.View):
    """Panel maestro persistente 24/7 con botones por categoría y de gestión (flujo personal efímero con checks)."""

    def __init__(self, guild: discord.Guild = None):
        super().__init__(timeout=None)
        # Fila 0: Botones de acceso por categoría
        btn_plat = discord.ui.Button(
            label="Plataformas y Hobbies",
            style=discord.ButtonStyle.primary,
            emoji="🎮",
            custom_id="autoroles:btn:cat:plataformas",
            row=0,
        )
        btn_plat.callback = _handle_category_button
        self.add_item(btn_plat)

        btn_gen = discord.ui.Button(
            label="Géneros y Alertas",
            style=discord.ButtonStyle.primary,
            emoji="🎯",
            custom_id="autoroles:btn:cat:generos",
            row=0,
        )
        btn_gen.callback = _handle_category_button
        self.add_item(btn_gen)

        btn_jue = discord.ui.Button(
            label="Juegos Específicos",
            style=discord.ButtonStyle.primary,
            emoji="🕹️",
            custom_id="autoroles:btn:cat:juegos",
            row=0,
        )
        btn_jue.callback = _handle_category_button
        self.add_item(btn_jue)

        # Fila 1: Botones de gestión global
        btn_mis_roles = discord.ui.Button(
            label="Mis Roles / Ver Todos (✅)",
            style=discord.ButtonStyle.success,
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

        btn_refrescar = discord.ui.Button(
            label="Actualizar Contadores",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            custom_id="autoroles:btn:refrescar",
            row=1,
        )
        btn_refrescar.callback = _handle_refrescar_autoroles_button
        self.add_item(btn_refrescar)


class AutoRoleCategoryView(discord.ui.View):
    """Vista persistente para un mensaje individual de una sola categoría (modo separado)."""

    def __init__(self, cat_key: str, include_buttons: bool = False, guild: discord.Guild = None):
        super().__init__(timeout=None)
        cat_info = AUTOROLES_CATALOG.get(cat_key, {})
        raw_title = cat_info.get("title", "Roles")
        title_word = raw_title.split(" ")[1].capitalize() if " " in raw_title else "Roles"
        cat_emoji = cat_info.get("roles", [("🎮",)])[0][0]
        btn_cat = discord.ui.Button(
            label=f"Elegir {title_word}",
            style=discord.ButtonStyle.primary,
            emoji=cat_emoji,
            custom_id=f"autoroles:btn:cat:{cat_key}",
            row=0,
        )
        btn_cat.callback = _handle_category_button
        self.add_item(btn_cat)

        if include_buttons:
            btn_mis_roles = discord.ui.Button(
                label="Mis Roles / Ver Todos (✅)",
                style=discord.ButtonStyle.success,
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

            btn_refrescar = discord.ui.Button(
                label="Actualizar Contadores",
                style=discord.ButtonStyle.secondary,
                emoji="🔄",
                custom_id="autoroles:btn:refrescar",
                row=1,
            )
            btn_refrescar.callback = _handle_refrescar_autoroles_button
            self.add_item(btn_refrescar)


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


# --- REEXPORTACIÓN SUBSISTEMA DE SUGERENCIAS 2.0 (MODULOS.SUGERENCIAS) ---
# Extraído de autoroles.py hacia modulos/sugerencias.py cumpliendo docs/DISENO_SUGERENCIAS_2.md.
# Se mantienen los símbolos públicos para retrocompatibilidad 100%.

from modulos.sugerencias import (
    SUGGESTIONS_CHANNEL_ID,
    SUGGESTIONS_DATA_PATH,
    SUGGESTIONS_LOCK,
    format_progress_bar,
    build_suggestion_embed,
    build_suggestions_hub_embed,
    publish_suggestions_hub,
    get_or_generate_ai_verdict,
    SuggestionSubmitModal,
    SuggestionDecisionModal,
    SuggestionActiveView,
    SuggestionClosedView,
    SuggestionHubView,
    handle_direct_suggestion,
    # Símbolos legados
    SuggestionPersistentView,
    SUGGESTION_VOTES_STATE,
    _extract_votes_from_embed,
    _extract_vote_state_from_embed,
    _update_suggestion_embed_votes,
    _get_next_suggestion_number,
)

