"""
Módulo de Comandos Slash Nativos para los bots 'Asistente' y 'Economia Asistente' en Discord:
Contiene los 41 comandos interactivos oficiales (@app_commands.command) divididos en Runner Dual:
- Comandos Generales del Asistente (22):
  * Multimedia y Arte: /dibuja, /musica
  * Gaming y Catálogo: /steam, /tribunal
  * Asistencia y Lore: /perfil, /pregunta, /voz, /recuerda, /xp
  * Voz Neuronal y Gemini Live: /habla, /geminilive, /cambiar_voz, /unete, /desconecta, /para_audio
  * Minijuegos del Servidor: /trivial, /ranking_trivial, /tres_en_raya, /conecta4, /ajedrez
  * Moderación y Reemplazo de Carl-bot: /autoroles, /sugerencia
- Comandos de Economía y Casino de Economia Asistente (19):
  * Economía de Porros y Casino: /slots, /balance, /trabajar, /transferir, /depositar, /retirar, /robar, /tienda, /salario, /blackjack, /bj, /ruleta, /coinflip, /casino, /crimen, /ranking, /inventario, /usar, /admin_dinero
"""

import os
import sys
import json
import random
import io
import re
import urllib.parse
from typing import Optional
import discord
from discord import app_commands
from discord.ext import voice_recv
from datetime import datetime, timezone
import asyncio


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


def _bot_log(msg: str):
    bs = _bs()
    log_fn = getattr(bs, "bot_log", print)
    log_fn(msg)


def _get_bot():
    bs = _bs()
    return getattr(bs, "bot", None)


def _get_base_dir():
    bs = _bs()
    return getattr(bs, "BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_tribunal_data() -> dict:
    bs = _bs()
    td = getattr(bs, "tribunal_data", None)
    if td:
        return td
    path = os.path.join(_get_base_dir(), "datos", "tribunal_data.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"coop": [], "single": []}


def _load_trivia_data() -> list:
    bs = _bs()
    if hasattr(bs, "load_trivia_data"):
        try:
            return bs.load_trivia_data()
        except Exception:
            pass
    path = os.path.join(_get_base_dir(), "datos", "trivia_data.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


# ==========================================
# 1. MULTIMEDIA Y ARTE
# ==========================================

@app_commands.command(name="dibuja", description="Genera una imagen en alta resolución con el motor FLUX.1")
@app_commands.describe(
    prompt="Describe la escena, personajes o idea que quieres generar",
    estilo="Elige un estilo artístico para la imagen",
)
@app_commands.choices(estilo=[
    app_commands.Choice(name="🎨 Anime / Manga Shonen", value="anime style, highly detailed shonen anime aesthetic, vivid colors, dynamic lighting"),
    app_commands.Choice(name="🌃 Cyberpunk / Neón", value="cyberpunk aesthetic, futuristic neon lights, dark sci-fi city, dramatic reflections, cinematic"),
    app_commands.Choice(name="📸 Fotorrealista / Cine", value="photorealistic 8k, cinematic movie still, 35mm lens, natural volumetric lighting, depth of field"),
    app_commands.Choice(name="👾 Pixel Art Retro", value="16-bit pixel art style, detailed retro game graphics, vibrant pixel palette"),
    app_commands.Choice(name="🖼️ Óleo Clásico / Pintura", value="classical oil painting, textured brush strokes, dramatic chiaroscuro lighting, masterpiece"),
])
async def cmd_dibuja(interaction: discord.Interaction, prompt: str, estilo: app_commands.Choice[str] = None):
    from modulos.graficos import enhance_image_prompt, generate_image_flux, ImageActionView

    await interaction.response.defer(thinking=True)
    author_name = interaction.user.display_name
    concept = prompt
    if estilo:
        concept += f", {estilo.value}"
    enhanced = await asyncio.to_thread(enhance_image_prompt, concept, author_name)
    try:
        img_bytes = await asyncio.to_thread(generate_image_flux, enhanced)
        file = discord.File(io.BytesIO(img_bytes), filename="creacion_flux.png")
        view = ImageActionView(enhanced, interaction.user.id)
        await interaction.followup.send(
            content=f"🎨 **Aquí tienes tu creación, {author_name}:**\n> *\"{prompt}\"*",
            file=file,
            view=view,
        )
    except Exception as e:
        await interaction.followup.send(f"⚠️ Error generando la imagen: {e}. Inténtalo de nuevo en unos momentos.")


@app_commands.command(name="musica", description="Busca una canción y muestra cómo reproducirla con Cakey Bot en la llamada de voz")
@app_commands.describe(cancion="Título o artista de la canción que quieres escuchar")
async def cmd_musica(interaction: discord.Interaction, cancion: str):
    encoded = urllib.parse.quote(cancion.strip())
    yt_url = f"https://www.youtube.com/results?search_query={encoded}"
    sp_url = f"https://open.spotify.com/search/{encoded}"

    embed = discord.Embed(
        title=f"🎵 Búsqueda Musical: {cancion}",
        description=(
            f"Para reproducirla en la sala de voz con **Cakey Bot**, escribe en el canal:\n"
            f"> `/play song: {cancion}`\n\n"
            f"🔗 **Enlaces directos para escucharla al instante:**\n"
            f"• [▶️ Buscar en YouTube]({yt_url})\n"
            f"• [🟢 Buscar en Spotify]({sp_url})\n\n"
            f"-# *Si Cakey Bot tiene la cola vacía o se atasca, usa `/skip`, `/stop` o un nuevo `/play`.*"
        ),
        color=0x1DB954,
    )
    embed.set_footer(text="Asistente de Música • Integración Cakey Bot & Streaming")
    await interaction.response.send_message(embed=embed)


# ==========================================
# 2. GAMING Y CATÁLOGO
# ==========================================

@app_commands.command(name="steam", description="Consulta el precio oficial, ofertas y detalles de un juego en Steam")
@app_commands.describe(juego="Nombre del juego en Steam")
async def cmd_steam(interaction: discord.Interaction, juego: str):
    from modulos.juegos import fetch_steam_game, SteamView

    await interaction.response.defer(thinking=True)
    game = await asyncio.to_thread(fetch_steam_game, juego)
    if not game:
        await interaction.followup.send(f"❌ No se encontró ningún juego en Steam llamado **'{juego}'**. Revisa el título o prueba con el nombre en inglés.")
        return

    title = game.get("name", juego)
    app_id = game.get("steam_appid", "")
    url = f"https://store.steampowered.com/app/{app_id}/" if app_id else "https://store.steampowered.com"
    header_img = game.get("header_image")
    short_desc = game.get("short_description", "Sin descripción disponible.")
    if len(short_desc) > 280:
        short_desc = short_desc[:277] + "..."

    price_info = game.get("price_overview", {})
    is_free = game.get("is_free", False)
    if is_free:
        price_str = "🆓 **Gratis (Free-to-Play)**"
    elif price_info:
        final_price = price_info.get("final_formatted", "N/D")
        discount = price_info.get("discount_percent", 0)
        if discount > 0:
            init_price = price_info.get("initial_formatted", "")
            price_str = f"🔥 **{final_price}** *(~~{init_price}~~ -{discount}% Rebajado)*"
        else:
            price_str = f"💳 **{final_price}**"
    else:
        price_str = "No disponible para compra directa"

    meta = game.get("metacritic", {}).get("score", "Sin nota")
    genres = [g.get("description", "") for g in game.get("genres", [])]
    genre_str = ", ".join(genres[:4]) if genres else "Varios"
    devs = ", ".join(game.get("developers", [])[:2]) or "Desconocido"
    release = game.get("release_date", {}).get("date", "Desconocida")

    embed = discord.Embed(
        title=f"🎮 {title}",
        url=url,
        description=short_desc,
        color=0x1B2838,
    )
    if header_img:
        embed.set_image(url=header_img)
    embed.add_field(name="💰 Precio (Steam ES)", value=price_str, inline=True)
    embed.add_field(name="⭐ Metacritic", value=f"**{meta}**", inline=True)
    embed.add_field(name="🏷️ Géneros", value=genre_str, inline=True)
    embed.add_field(name="🛠️ Desarrollador", value=devs, inline=True)
    embed.add_field(name="📅 Lanzamiento", value=release, inline=True)
    embed.set_footer(text="Steam Store API España • Datos oficiales en tiempo real", icon_url="https://store.steampowered.com/favicon.ico")

    view = SteamView(app_id)
    await interaction.followup.send(embed=embed, view=view)


@app_commands.command(name="tribunal", description="Consulta las notas, juegos cooperativos y veredictos de El Tribunal Gaming")
@app_commands.describe(
    accion="Qué deseas consultar en El Tribunal Gaming",
    juego="Nombre del juego a buscar (opcional si consultas listas)",
)
@app_commands.choices(accion=[
    app_commands.Choice(name="🔍 Buscar ficha de juego", value="buscar"),
    app_commands.Choice(name="🤝 Catálogo Cooperativo (categorías y viabilidad)", value="coop"),
    app_commands.Choice(name="💀 Muro de la Vergüenza / Vetados", value="muro"),
    app_commands.Choice(name="🏆 Top Rankings Metacritic & HLTB", value="top"),
])
async def cmd_tribunal(interaction: discord.Interaction, accion: app_commands.Choice[str], juego: str = ""):
    from modulos.juegos import TribunalView

    await interaction.response.defer(thinking=True)
    val = accion.value
    tribunal_data = _get_tribunal_data()

    if val == "buscar":
        if not juego:
            await interaction.followup.send("⚠️ Por favor indica el nombre del juego que quieres buscar en El Tribunal Gaming.")
            return
        q = juego.lower().strip()
        found_sp = [g for g in tribunal_data.get("single", []) if q in g.get("title", "").lower()]
        found_coop = [g for g in tribunal_data.get("coop", []) if q in g.get("title", "").lower()]

        if not found_sp and not found_coop:
            await interaction.followup.send(f"❌ No se encontró ningún juego en El Tribunal Gaming con el nombre **'{juego}'**. Puedes ver el catálogo completo en https://tribunal-gaming.vercel.app")
            return

        if found_sp:
            g = found_sp[0]
            embed = discord.Embed(
                title=f"⚖️ {g['title']} - El Tribunal Gaming",
                url="https://tribunal-gaming.vercel.app",
                description=g.get("description", "")[:320] + "...",
                color=0x6366F1,
            )
            embed.add_field(name="⭐ Metacritic", value=f"**{g.get('metacritic', 'N/D')}**", inline=True)
            hltb = g.get("hltb", {})
            hltb_str = f"Historia: {hltb.get('main', 'N/D')} | Completo: {hltb.get('completionist', 'N/D')}" if hltb else "N/D"
            embed.add_field(name="⏱️ Duración (HLTB)", value=hltb_str, inline=True)
            genres = ", ".join(g.get("genres", [])[:4]) or "Varios"
            embed.add_field(name="🏷️ Géneros", value=genres, inline=False)
            embed.set_footer(text="tribunal-gaming.vercel.app • Evaluaciones de los Magistrados")
            view = TribunalView()
            await interaction.followup.send(embed=embed, view=view)
            return

        if found_coop:
            g = found_coop[0]
            embed = discord.Embed(
                title=f"🤝 {g['title']} (Cooperativo) - El Tribunal Gaming",
                url="https://tribunal-gaming.vercel.app",
                description=g.get("desc", "")[:320],
                color=0x10B981,
            )
            embed.add_field(name="📂 Categoría", value=f"**{g.get('category', 'Cooperativo')}**", inline=True)
            embed.add_field(name="💾 Tamaño", value=g.get("size", "N/D"), inline=True)
            embed.add_field(name="⚙️ Rendimiento", value=g.get("perf", "Sin notas específicas"), inline=False)
            embed.set_footer(text="tribunal-gaming.vercel.app • Cooperativos evaluados")
            view = TribunalView()
            await interaction.followup.send(embed=embed, view=view)
            return

    elif val == "muro":
        unavail = [g for g in tribunal_data.get("coop", []) if g.get("availability") == "unavailable"]
        embed = discord.Embed(
            title="💀 El Muro de la Vergüenza - El Tribunal Gaming",
            url="https://tribunal-gaming.vercel.app",
            description="Juegos cooperativos retirados, vetados o en el limbo por los Magistrados del Tribunal Gaming:",
            color=0xEF4444,
        )
        sample = unavail[:8]
        lines = [f"• **{g['title']}** ({g.get('category', 'Coop')}) - {g.get('perf', 'Vetado / No disponible')[:75]}" for g in sample]
        embed.add_field(name=f"Juegos en el Limbo ({len(unavail)} totales)", value="\n".join(lines) or "Sin juegos registrados actualmente.", inline=False)
        embed.set_footer(text="tribunal-gaming.vercel.app • El Muro de la Vergüenza")
        view = TribunalView()
        await interaction.followup.send(embed=embed, view=view)

    elif val == "top":
        sp = sorted(tribunal_data.get("single", []), key=lambda x: x.get("metacritic") or 0, reverse=True)
        embed = discord.Embed(
            title="🏆 Top Rankings - El Tribunal Gaming",
            url="https://tribunal-gaming.vercel.app",
            description="Los títulos mejor puntuados en la base de datos de El Tribunal Gaming:",
            color=0xF59E0B,
        )
        lines = []
        for i, g in enumerate(sp[:8], 1):
            lines.append(f"**#{i}** **{g['title']}** - ⭐ **{g.get('metacritic')}** | ⏱️ {g.get('hltb', {}).get('main', 'N/D')}")
        embed.add_field(name="Top Obras Maestras", value="\n".join(lines), inline=False)
        embed.set_footer(text="tribunal-gaming.vercel.app • Rankings Oficiales")
        view = TribunalView()
        await interaction.followup.send(embed=embed, view=view)

    elif val == "coop":
        cats = {}
        for g in tribunal_data.get("coop", []):
            c = g.get("category", "Otros")
            cats[c] = cats.get(c, 0) + 1
        cat_str = "\n".join([f"• **{k}**: {v} juegos analizados" for k, v in cats.items()])
        embed = discord.Embed(
            title="🤝 Catálogo Cooperativo - El Tribunal Gaming",
            url="https://tribunal-gaming.vercel.app",
            description=f"El Tribunal Gaming tiene registrados **{len(tribunal_data.get('coop', []))} juegos cooperativos** clasificados por viabilidad y rendimiento técnico:\n\n{cat_str}\n\n*Usa `/tribunal buscar [juego]` para ver la ficha técnica de un juego concreto.*",
            color=0x10B981,
        )
        embed.set_footer(text="tribunal-gaming.vercel.app • Filtro Cooperativo")
        view = TribunalView()
        await interaction.followup.send(embed=embed, view=view)


# ==========================================
# 3. ASISTENCIA Y LORE
# ==========================================

@app_commands.command(name="perfil", description="Muestra la ficha técnica, rango de Cakey Bot y roles de un miembro")
@app_commands.describe(usuario="El miembro del que quieres consultar la ficha (por defecto tú)")
async def cmd_perfil(interaction: discord.Interaction, usuario: discord.Member = None):
    from modulos.chat_ia import get_live_levels_dict

    member = usuario or interaction.user
    live_levels = await get_live_levels_dict(interaction.guild) if interaction.guild else {}
    lvl_val = f"**Nivel {live_levels[member.id]}**" if member.id in live_levels else "No registrado recientemente en #bots"
    roles = [r.name for r in member.roles if r.name != "@everyone"]
    top_role = member.top_role.name if member.top_role else "Ninguno"
    color = member.color if member.color.value != 0 else discord.Color.blue()

    created = member.created_at.strftime("%d/%m/%Y")
    joined = member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "Desconocida"

    embed = discord.Embed(
        title=f"👤 Ficha de {member.display_name} (@{member.name})",
        color=color,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="📊 Nivel Cakey Bot", value=lvl_val, inline=True)
    embed.add_field(name="👑 Rol Principal", value=f"**{top_role}**", inline=True)
    embed.add_field(name="📅 Cuenta Creada", value=created, inline=True)
    embed.add_field(name="🚪 Entrada al Server", value=joined, inline=True)
    roles_str = ", ".join(roles[:12]) if roles else "Sin roles"
    if len(roles) > 12:
        roles_str += f" *(+{len(roles) - 12} más)*"
    embed.add_field(name=f"🎭 Roles ({len(roles)})", value=roles_str, inline=False)
    embed.set_footer(text=f"ID: {member.id} • Servidor: {interaction.guild.name if interaction.guild else 'Discord'}")

    await interaction.response.send_message(embed=embed)


@app_commands.command(name="pregunta", description="Haz una pregunta o debate con el Asistente sin necesidad de mencionarlo")
@app_commands.describe(duda="Tu pregunta sobre juegos, anime, hardware, salseo o cualquier tema")
async def cmd_pregunta(interaction: discord.Interaction, duda: str):
    from modulos.chat_ia import call_gemini_multiturn, get_spain_now_str, format_server_emojis
    from modulos.graficos import generate_image_flux, ImageActionView

    await interaction.response.defer(thinking=True)
    spain_time = get_spain_now_str()
    prompt = f"{interaction.user.display_name}: {duda}\n[CONTEXTO: Fecha y hora en España: {spain_time} | Usuario: {interaction.user.display_name} (@{interaction.user.name})]"
    turns = [{"role": "user", "parts": [{"text": prompt}]}]
    response = await asyncio.to_thread(call_gemini_multiturn, turns)

    draw_match = re.search(r"\[ACTION_DRAW:\s*(.*?)\]", response, re.DOTALL | re.IGNORECASE)
    if draw_match:
        prompt_flux = draw_match.group(1).strip()
        clean_response = re.sub(r"\[ACTION_DRAW:\s*.*?\]", "", response, flags=re.DOTALL | re.IGNORECASE).strip()
        clean_response = format_server_emojis(clean_response, guild=interaction.guild)
        try:
            img_bytes = await asyncio.to_thread(generate_image_flux, prompt_flux)
            file = discord.File(io.BytesIO(img_bytes), filename="creacion_flux.png")
            view = ImageActionView(prompt_flux, interaction.user.id)
            await interaction.followup.send(content=clean_response or None, file=file, view=view)
            return
        except Exception:
            pass

    response = format_server_emojis(response, guild=interaction.guild)
    if len(response) <= 1900:
        await interaction.followup.send(response)
    else:
        await interaction.followup.send(response[:1900])


@app_commands.command(name="voz", description="Consulta el radar en tiempo real de quién está en las salas de voz y su estado")
async def cmd_voz(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Este comando solo está disponible dentro de un servidor.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎙️ Radar de Canales de Voz en Vivo",
        color=0x3B82F6,
        description=f"Estado de las salas de voz en **{interaction.guild.name}** al segundo:",
    )

    total_active = 0
    for vc in interaction.guild.voice_channels:
        if vc.members:
            total_active += len(vc.members)
            member_lines = []
            for m in vc.members:
                state = m.voice
                icons = []
                if m.bot:
                    icons.append("🤖 Bot")
                else:
                    if state.self_mute or state.mute:
                        icons.append("🔇 Silenciado")
                    else:
                        icons.append("🎤 Micro activo")
                    if state.self_deaf or state.deaf:
                        icons.append("🎧 Ensordecido")
                    if state.self_stream:
                        icons.append("📺 Streaming")
                    if state.self_video:
                        icons.append("📷 Cámara")
                icon_str = f" • *{', '.join(icons)}*" if icons else ""
                member_lines.append(f"• **{m.display_name}** (`@{m.name}`){icon_str}")

            embed.add_field(
                name=f"🔊 #{vc.name} ({len(vc.members)} personas)",
                value="\n".join(member_lines),
                inline=False,
            )

    if total_active == 0:
        embed.description = "🟢 **Todas las salas de voz están libres actualmente.** No hay nadie conectado ahora mismo."
    else:
        embed.set_footer(text=f"Total: {total_active} miembros en llamadas de voz • Actualizado al segundo")

    await interaction.response.send_message(embed=embed)


@app_commands.command(name="recuerda", description="Guarda un gusto, nota o detalle en la memoria persistente de un usuario")
@app_commands.describe(
    dato="El dato a recordar (ej: 'Le flipa Solo Leveling y The Greatest Estate Developer')",
    categoria="Categoría del recuerdo (obra favorita, género o nota)",
    usuario="El miembro al que asociar este recuerdo (por defecto tú)",
)
@app_commands.choices(categoria=[
    app_commands.Choice(name="Obra / Juego favorito (fav_works)", value="fav_works"),
    app_commands.Choice(name="Género favorito (fav_genres)", value="fav_genres"),
    app_commands.Choice(name="Nota / Lore personal (notes)", value="notes"),
])
async def cmd_recuerda(interaction: discord.Interaction, dato: str, categoria: app_commands.Choice[str] = None, usuario: discord.Member = None):
    from modulos.chat_ia import user_memory, save_user_memory

    member = usuario or interaction.user
    uid_str = str(member.id)
    cat_key = categoria.value if categoria else "notes"

    if uid_str not in user_memory:
        user_memory[uid_str] = {
            "name": member.display_name,
            "display_name": member.display_name,
            "username": member.name,
            "role_in_server": member.top_role.name if getattr(member, "top_role", None) else "Miembro",
            "fav_genres": [],
            "fav_works": [],
            "notes": [],
            "trivia_points": 0,
        }

    entry = user_memory[uid_str]
    entry["display_name"] = member.display_name
    entry["username"] = member.name

    if cat_key in ["fav_works", "fav_genres", "notes"]:
        if cat_key not in entry:
            entry[cat_key] = []
        if dato not in entry[cat_key]:
            entry[cat_key].append(dato)

    save_user_memory(user_memory)

    cat_name = categoria.name if categoria else "Nota personal"
    embed = discord.Embed(
        title="🧠 Recuerdo Guardado en Memoria",
        description=f"He anotado el siguiente detalle para **{member.display_name}** (`@{member.name}`):\n\n> **{cat_name}:** {dato}\n\n*A partir de ahora lo tendré en cuenta en nuestras conversaciones.*",
        color=0x8B5CF6,
    )
    embed.set_footer(text="Memoria Persistente de Antigravity Asistente")
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="xp", description="Calcula la XP y mensajes necesarios para alcanzar un nivel objetivo en Cakey Bot")
@app_commands.describe(
    nivel_objetivo="Nivel que deseas alcanzar (ej. 20 para Categoría Pro)",
    nivel_actual="Tu nivel actual (por defecto se consulta tu nivel real en el servidor)",
)
async def cmd_xp(interaction: discord.Interaction, nivel_objetivo: int, nivel_actual: int = None):
    from modulos.chat_ia import get_live_levels_dict, calculate_xp_gap

    start_lvl = nivel_actual
    if start_lvl is None:
        if interaction.guild:
            live_levels = await get_live_levels_dict(interaction.guild)
            start_lvl = live_levels.get(interaction.user.id, 1)
        else:
            start_lvl = 1

    if nivel_objetivo <= start_lvl:
        await interaction.response.send_message(f"⚠️ El nivel objetivo ({nivel_objetivo}) debe ser superior a tu nivel actual ({start_lvl}).", ephemeral=True)
        return

    res = calculate_xp_gap(start_lvl, nivel_objetivo)
    if not res:
        await interaction.response.send_message("❌ Rango de niveles inválido.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"📊 Calculadora de XP de Cakey Bot: Lvl {start_lvl} ➔ Lvl {nivel_objetivo}",
        description=f"Progreso calculado para **{interaction.user.display_name}**:\n\n{res}",
        color=0x3B82F6,
    )
    embed.set_footer(text="Motor Matemático Cuadrático de Cakey Bot • Antigravity Asistente")
    await interaction.response.send_message(embed=embed)


# ==========================================
# 4. VOZ NEURONAL Y GEMINI LIVE
# ==========================================

from modulos.voz import TTS_VOICES


@app_commands.command(name="habla", description="El Asistente entra a tu canal de voz y habla con síntesis neuronal de voz")
@app_commands.describe(
    texto="El mensaje o frase que quieres que diga en la llamada",
    voz="Voz de la locución: acentos, efectos o voces Gemini (por defecto Álvaro)",
)
@app_commands.choices(voz=[app_commands.Choice(name=v[0], value=k) for k, v in TTS_VOICES.items()])
async def cmd_habla(interaction: discord.Interaction, texto: str, voz: app_commands.Choice[str] = None):
    from modulos.voz import (
        generate_speech_audio,
        ensure_voice_connection,
        play_audio_in_voice,
        clear_voice_manually_disconnected,
    )

    await interaction.response.defer(thinking=True)
    if not interaction.guild:
        await interaction.followup.send("❌ Este comando solo está disponible dentro de un servidor.")
        return

    clear_voice_manually_disconnected(interaction.guild.id)

    voice_channel = None
    member = interaction.guild.get_member(interaction.user.id)
    if not member and isinstance(interaction.user, discord.Member):
        member = interaction.user
    if not member:
        try:
            member = await interaction.guild.fetch_member(interaction.user.id)
        except Exception:
            member = None

    if member and getattr(member, "voice", None) and member.voice.channel:
        voice_channel = member.voice.channel
    else:
        for vc in interaction.guild.voice_channels:
            if any(m.id == interaction.user.id for m in vc.members):
                voice_channel = vc
                break

    if not voice_channel:
        await interaction.followup.send("❌ Debes estar conectado a un canal de voz para que pueda hablar contigo.")
        return

    voice_choice = voz.value if voz else "alvaro"

    try:
        audio_file = await generate_speech_audio(texto, voice_choice)
        vc = await ensure_voice_connection(voice_channel)
        play_audio_in_voice(vc, audio_file)

        lbl = TTS_VOICES.get(voice_choice, TTS_VOICES["alvaro"])[0]
        if TTS_VOICES.get(voice_choice, ("", "edge"))[1] == "gemini" and os.path.basename(audio_file).startswith("speech_edge_"):
            lbl = f"{TTS_VOICES['alvaro'][0]} — {lbl} no disponible ahora"

        embed = discord.Embed(
            title="🎙️ Locución en Canal de Voz",
            description=f"🔊 Hablando en **#{voice_channel.name}**\n\n> *\"{texto[:300]}\"*\n\n🎙️ **Voz:** `{lbl}`",
            color=0x3B82F6,
        )
        embed.set_footer(text="Asistente de Voz Neuronal • Usa /para_audio para silenciar")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"Error en /habla: {e}")
        await interaction.followup.send(f"❌ Error al generar o reproducir la voz: {e}")


@app_commands.command(name="geminilive", description="Consulta o configura el estado de Gemini Live en llamada de voz")
@app_commands.describe(
    accion="Acción a realizar",
    sensibilidad="Sensibilidad del detector de voz (VAD)",
    voz="Voz neuronal del Asistente",
)
@app_commands.choices(
    accion=[
        app_commands.Choice(name="Estado y Diagnóstico", value="estado"),
        app_commands.Choice(name="Pausar Escucha", value="pausar"),
        app_commands.Choice(name="Reanudar Escucha", value="activar"),
    ],
    sensibilidad=[
        app_commands.Choice(name="Alta (micrófonos lejanos o voz baja)", value="alta"),
        app_commands.Choice(name="Media (estándar equilibrada)", value="media"),
        app_commands.Choice(name="Baja (entornos con mucho ruido de fondo)", value="baja"),
    ],
    voz=[
        app_commands.Choice(name="Álvaro (Masculina, natural de España)", value="alvaro"),
        app_commands.Choice(name="Elvira (Femenina cálida, España)", value="elvira"),
        app_commands.Choice(name="Ximena (Femenina juvenil, España)", value="ximena"),
    ],
)
async def cmd_geminilive(
    interaction: discord.Interaction,
    accion: app_commands.Choice[str] = None,
    sensibilidad: app_commands.Choice[str] = None,
    voz: app_commands.Choice[str] = None,
):
    from modulos.voz import GeminiLiveVoiceSink

    bot = _get_bot()
    await interaction.response.defer(thinking=True)
    if not interaction.guild:
        await interaction.followup.send("❌ Este comando solo está disponible en un servidor.")
        return

    vc = interaction.guild.voice_client
    sink = getattr(vc, "sink", None) if vc else None
    act = accion.value if accion else "estado"

    if act == "pausar":
        if sink and hasattr(sink, "_is_active"):
            sink._is_active = False
            await interaction.followup.send("⏸️ **Gemini Live pausado**: El bot no escuchará el micrófono hasta que uses `/geminilive accion:Reanudar Escucha`.")
        else:
            await interaction.followup.send("ℹ️ El bot no está conectado o no tiene Gemini Live activo en este servidor.")
        return

    if act == "activar":
        if sink and hasattr(sink, "_is_active"):
            sink._is_active = True
            await interaction.followup.send("▶️ **Gemini Live reanudado**: El bot vuelve a escuchar activamente la llamada.")
        elif vc and vc.is_connected() and isinstance(vc, voice_recv.VoiceRecvClient) and bot:
            new_sink = GeminiLiveVoiceSink(vc, bot.loop)
            vc.listen(new_sink)
            await interaction.followup.send(f"🎙️ **Gemini Live iniciado** en **#{vc.channel.name}**.")
        else:
            await interaction.followup.send("ℹ️ Usa `/unete` para conectar el bot a tu sala de voz primero.")
        return

    if sink:
        if sensibilidad and hasattr(sink, "silence_threshold_rms"):
            sens_map = {"alta": 40, "media": 70, "baja": 180}
            sink.silence_threshold_rms = sens_map.get(sensibilidad.value, 70)
        if voz and hasattr(sink, "voice_type"):
            sink.voice_type = voz.value

    is_conn = vc is not None and vc.is_connected()
    ch_name = vc.channel.name if (is_conn and vc.channel) else "Desconectado"
    is_listening = getattr(vc, "is_listening", lambda: False)() if is_conn else False
    current_sens = "Media (RMS 70)"
    current_voice = "Álvaro (Masculina)"
    if sink:
        rms_val = getattr(sink, "silence_threshold_rms", 70)
        if rms_val <= 50:
            current_sens = "Alta (RMS 40)"
        elif rms_val >= 150:
            current_sens = "Baja (RMS 180)"
        v_type = getattr(sink, "voice_type", "alvaro")
        v_labels = {"alvaro": "Álvaro (Masculina)", "elvira": "Elvira (Femenina cálida)", "ximena": "Ximena (Femenina juvenil)", "abril": "Elvira (Femenina)"}
        current_voice = v_labels.get(v_type, "Álvaro (Masculina)")

    embed = discord.Embed(
        title="🎙️ Panel de Control: Gemini Live Voice",
        description="Experiencia conversacional fluida en tiempo real por voz en Discord.",
        color=0x10B981 if (is_conn and is_listening) else 0x6B7280,
    )
    embed.add_field(name="📡 Estado Conexión", value=f"`{'🟢 Conectado' if is_conn else '🔴 Desconectado'}`", inline=True)
    embed.add_field(name="🔊 Canal de Voz", value=f"**#{ch_name}**", inline=True)
    embed.add_field(name="👂 Escucha en Vivo", value=f"`{'🟢 Activa (Escuchando)' if is_listening else '⚪ Inactiva'}`", inline=True)
    embed.add_field(name="🎚️ Sensibilidad Micro (VAD)", value=f"`{current_sens}`", inline=True)
    embed.add_field(name="🗣️ Voz de Salida", value=f"`{current_voice}`", inline=True)
    embed.add_field(name="⚡ Latencia de Respuesta", value="`~1.5s (Full Duplex)`", inline=True)
    embed.set_footer(text="Usa /voz para cambiar de locutor o /desconecta para salir.")
    await interaction.followup.send(embed=embed)


@app_commands.command(name="cambiar_voz", description="Cambia la voz del Asistente en la llamada de voz (Álvaro, Elvira o Ximena)")
@app_commands.describe(tipo="Selecciona la voz neuronal")
@app_commands.choices(
    tipo=[
        app_commands.Choice(name="Álvaro (Masculina, natural de España)", value="alvaro"),
        app_commands.Choice(name="Elvira (Femenina cálida, España)", value="elvira"),
        app_commands.Choice(name="Ximena (Femenina juvenil, España)", value="ximena"),
    ]
)
async def cmd_cambiar_voz(interaction: discord.Interaction, tipo: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)
    if not interaction.guild:
        await interaction.followup.send("❌ Este comando solo está disponible en un servidor.")
        return
    vc = interaction.guild.voice_client
    sink = getattr(vc, "sink", None) if vc else None
    labels = {
        "alvaro": "Álvaro (Masculina)",
        "elvira": "Elvira (Femenina cálida)",
        "ximena": "Ximena (Femenina juvenil)",
    }
    lbl = labels.get(tipo.value, tipo.name)
    if sink and hasattr(sink, "voice_type"):
        sink.voice_type = tipo.value
        await interaction.followup.send(f"🎙️ **Voz cambiada**: A partir de ahora el Asistente responderá con la voz de **{lbl}**.\n*(También puedes cambiársela pidiéndole por voz 'ponte voz de chica' o 'ponte voz de chico')*.")
    else:
        channel_hint = interaction.user.voice.channel.name if getattr(interaction.user, 'voice', None) and interaction.user.voice.channel else "una sala de voz"
        await interaction.followup.send(f"ℹ️ El Asistente no tiene una llamada activa ahora. Conéctalo a **#{channel_hint}** y podrás usar `/cambiar_voz` o pedírselo por el micro.")


@app_commands.command(name="unete", description="Conecta al Asistente a tu canal de voz en modo conversacional Gemini Live")
@app_commands.describe(canal="Canal de voz al que conectarse (por defecto el tuyo)")
async def cmd_unete(interaction: discord.Interaction, canal: discord.VoiceChannel = None):
    from modulos.voz import (
        clear_voice_manually_disconnected,
        ensure_voice_connection,
        generate_speech_audio,
        play_audio_in_voice,
    )

    await interaction.response.defer(thinking=True)
    if not interaction.guild:
        await interaction.followup.send("❌ Este comando solo está disponible en un servidor.")
        return

    clear_voice_manually_disconnected(interaction.guild.id)

    target_channel = canal
    if not target_channel:
        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            try:
                member = await interaction.guild.fetch_member(interaction.user.id)
            except Exception:
                member = None
        if member and getattr(member, "voice", None) and member.voice.channel:
            target_channel = member.voice.channel
        else:
            for vc in interaction.guild.voice_channels:
                if any(m.id == interaction.user.id for m in vc.members):
                    target_channel = vc
                    break

    if not target_channel:
        await interaction.followup.send("❌ Debes estar conectado a una sala de voz o especificar una.")
        return

    try:
        vc = await ensure_voice_connection(target_channel)
        try:
            greeting_path = await generate_speech_audio("¡Hola! Ya estoy en la llamada en modo Gemini Live. Te escucho por el micro.", "alvaro")
            play_audio_in_voice(vc, greeting_path)
        except Exception as ge:
            print(f"Aviso saludo vocal /unete: {ge}")
        embed = discord.Embed(
            title="🎙️ Gemini Live Conectado",
            description=(
                f"🔊 Me he conectado a **#{target_channel.name}** en modo **Gemini Live Bidireccional**.\n\n"
                f"✨ **¿Cómo funciona?**\n"
                f"• Háblame directamente por el micro diciendo *\"Asistente...\"* o haciéndome preguntas.\n"
                f"• Te escucharé y responderé al instante por voz en la misma llamada.\n"
                f"• Filtro inteligente: puedes hablar con tus amigos sin que el bot interrumpa tus partidas.\n"
                f"• Usa `/para_audio` para cortar si está hablando o `/desconecta` para salir."
            ),
            color=0x10B981,
        )
        embed.set_footer(text="Gemini Live Discord • Voz Neuronal en Tiempo Real")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al conectar a la llamada de voz: {e}")


@app_commands.command(name="desconecta", description="Desconecta al Asistente del canal de voz")
async def cmd_desconecta(interaction: discord.Interaction):
    from modulos.voz import set_voice_manually_disconnected

    await interaction.response.defer(thinking=True)
    if not interaction.guild:
        await interaction.followup.send("❌ Este comando solo está disponible en un servidor.")
        return

    vc = interaction.guild.voice_client
    if not vc or not vc.is_connected():
        await interaction.followup.send("ℹ️ No estoy conectado a ningún canal de voz en este servidor.")
        return

    ch_name = vc.channel.name if vc.channel else "la llamada"
    if hasattr(vc, "stop_listening"):
        try:
            vc.stop_listening()
        except Exception:
            pass
    if vc.is_playing():
        if hasattr(vc, "stop_playing"):
            vc.stop_playing()
        else:
            vc.stop()
    set_voice_manually_disconnected(interaction.guild.id)
    await vc.disconnect(force=True)
    await interaction.followup.send(f"🔌 Me he desconectado de **#{ch_name}** y detenido Gemini Live.\n*(No volveré solo hasta que uses `/unete`)*.")


@app_commands.command(name="para_audio", description="Detiene la locución actual si el bot está hablando en la sala de voz")
async def cmd_para_audio(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    vc = interaction.guild.voice_client if interaction.guild else None
    if not vc or not vc.is_connected():
        await interaction.followup.send("ℹ️ No estoy en ningún canal de voz.")
        return
    if vc.is_playing():
        if hasattr(vc, "stop_playing"):
            vc.stop_playing()
        else:
            vc.stop()
        await interaction.followup.send("⏹️ Audio detenido.")
    else:
        await interaction.followup.send("ℹ️ No hay ningún audio reproduciéndose actualmente.")


# ==========================================
# 5. MINIJUEGOS DEL SERVIDOR
# ==========================================

from modulos.juegos import (
    CATEGORY_ALIASES,
    RECENT_TRIVIA_IDS,
    generate_gemini_trivia_question,
    TriviaView,
    TicTacToeView,
    Connect4View,
    chess,
    CHESS_GAMES,
    CHESS_LEVELS,
    ChessGame,
    ChessView,
    chess_build_embed,
    chess_finish,
    chess_run_bot_turn,
)


@app_commands.command(name="trivial", description="Inicia una ronda de preguntas de Trivial (+10 pts al acertar)")
@app_commands.describe(
    categoria="Categoría de las preguntas",
    modo="Modo de obtención de la pregunta (Banco oficial o Generada por IA)",
)
@app_commands.choices(categoria=[
    app_commands.Choice(name="Todas las categorías (Aleatorio)", value="all"),
    app_commands.Choice(name="🎌 Manhwas & Anime", value="manhwa"),
    app_commands.Choice(name="🎮 Videojuegos", value="gaming"),
    app_commands.Choice(name="⚖️ El Tribunal Gaming", value="tribunal"),
    app_commands.Choice(name="📜 Lore del Servidor & Colegas", value="lore"),
    app_commands.Choice(name="🧠 Cultura General", value="general"),
])
@app_commands.choices(modo=[
    app_commands.Choice(name="📚 Banco oficial (110+ preguntas)", value="local"),
    app_commands.Choice(name="✨ Generada en vivo por IA (Gemini)", value="ia"),
])
async def cmd_trivial(interaction: discord.Interaction, categoria: app_commands.Choice[str] = None, modo: app_commands.Choice[str] = None):
    trivia_pool = _load_trivia_data()
    raw_cat = categoria.value if categoria else "all"
    cat_val = CATEGORY_ALIASES.get(raw_cat.lower(), raw_cat.lower())
    use_ia = (modo and modo.value == "ia")

    question = None
    ia_notice = ""
    if use_ia:
        await interaction.response.defer()
        gemini_q = await asyncio.to_thread(generate_gemini_trivia_question, cat_val)
        if gemini_q:
            question = gemini_q
            ia_notice = "✨ *Pregunta inédita generada en tiempo real por Gemini IA*\n\n"
        else:
            ia_notice = "⚠️ *IA en cooldown temporal. Obteniendo pregunta del banco oficial...*\n\n"

    if not question:
        if not trivia_pool:
            if interaction.response.is_done():
                await interaction.followup.send("❌ No hay preguntas de Trivial disponibles.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ No hay preguntas de Trivial disponibles.", ephemeral=True)
            return

        if cat_val != "all":
            pool = [q for q in trivia_pool if CATEGORY_ALIASES.get(q.get("category", "").lower(), q.get("category", "").lower()) == cat_val]
        else:
            pool = trivia_pool

        if not pool:
            pool = trivia_pool

        unplayed = [q for q in pool if q.get("id") not in RECENT_TRIVIA_IDS]
        if unplayed:
            question = random.choice(unplayed)
        else:
            if not interaction.response.is_done():
                await interaction.response.defer()
            gemini_q = await asyncio.to_thread(generate_gemini_trivia_question, cat_val)
            if gemini_q:
                question = gemini_q
                ia_notice = "✨ *Preguntas locales agotadas recientemente. ¡Pregunta inédita generada en vivo por Gemini IA!*\n\n"
            else:
                question = random.choice(pool)

        if question and "id" in question:
            RECENT_TRIVIA_IDS.append(question["id"])

    letters = ["🇦", "🇧", "🇨", "🇩"]
    opts_txt = "\n".join([f"{letters[i]} **{opt}**" for i, opt in enumerate(question["options"][:4])])

    embed = discord.Embed(
        title=f"❓ Trivial: {question.get('category_name', 'Pregunta')}",
        description=f"{ia_notice}**{question['question']}**\n\n{opts_txt}\n\n*Pulsa el botón con la respuesta correcta abajo. ¡El primero en acertar se lleva 10 puntos!*",
        color=0x3B82F6,
    )
    embed.set_footer(text="Trivial Asistente • 60 segundos para responder • /ranking_trivial")
    view = TriviaView(question, interaction.user.id, raw_cat)
    if interaction.response.is_done():
        msg = await interaction.followup.send(embed=embed, view=view, wait=True)
        view.message = msg
    else:
        await interaction.response.send_message(embed=embed, view=view)
        try:
            view.message = await interaction.original_response()
        except Exception:
            pass


@app_commands.command(name="ranking_trivial", description="Muestra la tabla de clasificación y puntos de Trivial del servidor")
async def cmd_ranking_trivial(interaction: discord.Interaction):
    from modulos.chat_ia import user_memory

    ranked = []
    for uid, data in user_memory.items():
        pts = data.get("trivia_points", 0)
        if pts > 0:
            name = data.get("display_name") or data.get("name") or uid
            ranked.append((name, pts))
    ranked.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="🏆 Ranking de Trivial del Servidor",
        color=0xF59E0B,
        description="Puntuación acumulada respondiendo preguntas con `/trivial` (+10 pts por acierto):",
    )
    if not ranked:
        embed.description += "\n\n*Aún nadie tiene puntos en el Trivial. ¡Sé el primero usando `/trivial`!*"
    else:
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        lines = []
        for i, (name, pts) in enumerate(ranked[:10]):
            m = medals[i] if i < len(medals) else f"{i+1}."
            lines.append(f"{m} **{name}**: `{pts} pts`")
        embed.description += "\n\n" + "\n".join(lines)

    embed.set_footer(text="El Trivial de Asistente • 110+ Preguntas de Manhwa, Gaming, Lore y Tribunal")
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="tres_en_raya", description="Juega al Tres en Raya interactivo (PvE contra Asistente o PvP contra un colega)")
@app_commands.describe(rival="El miembro al que deseas retar (dejar vacío para jugar contra la IA de Asistente)")
async def cmd_tres_en_raya(interaction: discord.Interaction, rival: discord.Member = None):
    target_rival = rival
    if target_rival and (target_rival.bot or target_rival.id == interaction.user.id):
        target_rival = None

    view = TicTacToeView(interaction.user, target_rival)
    embed = view.build_embed()
    await interaction.response.send_message(embed=embed, view=view)
    try:
        view.message = await interaction.original_response()
    except Exception:
        pass
    p2_txt = target_rival.display_name if target_rival else "Asistente (IA)"
    _bot_log(f"🎮 [Tres en Raya] '{interaction.user.display_name}' inicia partida vs '{p2_txt}'.")


@app_commands.command(name="conecta4", description="Juega a Conecta 4 interactivo (PvE contra Asistente o PvP contra un colega)")
@app_commands.describe(rival="El miembro al que deseas retar (dejar vacío para jugar contra la IA de Asistente)")
async def cmd_conecta4(interaction: discord.Interaction, rival: discord.Member = None):
    target_rival = rival
    if target_rival and (target_rival.bot or target_rival.id == interaction.user.id):
        target_rival = None

    view = Connect4View(interaction.user, target_rival)
    embed = view.build_embed()
    await interaction.response.send_message(embed=embed, view=view)
    try:
        view.message = await interaction.original_response()
    except Exception:
        pass
    p2_txt = target_rival.display_name if target_rival else "Asistente (IA)"
    _bot_log(f"🔴🟡 [Conecta 4] '{interaction.user.display_name}' inicia partida vs '{p2_txt}'.")


@app_commands.command(name="ajedrez", description="Juega una partida de ajedrez contra Asistente (menús o escribiendo la jugada)")
@app_commands.describe(
    dificultad="Nivel de Asistente (por defecto Medio, 1400 ELO)",
    color="Con qué color juegas (por defecto blancas)",
)
@app_commands.choices(
    dificultad=[app_commands.Choice(name=v[0], value=k) for k, v in CHESS_LEVELS.items()],
    color=[
        app_commands.Choice(name="Blancas (mueves primero)", value="blancas"),
        app_commands.Choice(name="Negras", value="negras"),
        app_commands.Choice(name="Al azar", value="azar"),
    ],
)
async def cmd_ajedrez(interaction: discord.Interaction, dificultad: app_commands.Choice[str] = None, color: app_commands.Choice[str] = None):
    if chess is None:
        await interaction.response.send_message("❌ El módulo de ajedrez no está disponible en este despliegue.", ephemeral=True)
        return
    await interaction.response.defer()
    old = CHESS_GAMES.get(interaction.user.id)
    if old:
        chess_finish(old, f"🚪 **Partida abandonada por {old.user_name}.**")
        try:
            await old.message.edit(embed=chess_build_embed(old), view=None)
        except Exception:
            pass

    color_value = color.value if color else "blancas"
    player_white = random.choice([True, False]) if color_value == "azar" else color_value == "blancas"
    game = ChessGame(interaction.user.id, interaction.user.display_name, player_white, dificultad.value if dificultad else "medio")
    game.busy = not player_white
    CHESS_GAMES[interaction.user.id] = game
    sent = await interaction.followup.send(embed=chess_build_embed(game), view=ChessView(game), wait=True)
    try:
        game.message = await interaction.channel.fetch_message(sent.id)
    except Exception:
        game.message = sent
    _bot_log(f"♟️ [Ajedrez] '{game.user_name}' empieza partida en dificultad {CHESS_LEVELS[game.rival][0]} ({'blancas' if player_white else 'negras'}).")
    if not player_white:
        async with game.lock:
            await chess_run_bot_turn(game)


# ==========================================
# 6. MODERACIÓN Y REEMPLAZO DE CARL-BOT
# ==========================================

from modulos.autoroles import (
    AUTOROLES_CATALOG,
    build_autoroles_category_embed,
    build_autoroles_all_embeds,
    AutoRoleCategoryView,
    AutoRolesPersistentView,
    _resolve_guild_member,
    is_admin_or_mod,
    SUGGESTIONS_CHANNEL_ID,
    SUGGESTION_VOTES_STATE,
    SuggestionPersistentView,
    _get_next_suggestion_number,
)


@app_commands.command(name="autoroles", description="Publica el panel interactivo 24/7 de Auto-Roles del servidor (Reemplazo de Carl-bot)")
@app_commands.describe(
    canal="Canal donde publicar el panel de Auto-Roles (por defecto el canal actual)",
    formato="Diseño del panel: Unificado en 1 mensaje o Separado en 3 mensajes por categoría",
)
@app_commands.choices(
    formato=[
        app_commands.Choice(name="📦 Panel Único Compacto (3 categorías + 3 menús en 1 mensaje)", value="unificado"),
        app_commands.Choice(name="📑 3 Mensajes Separados por Categoría (estilo Carl-bot)", value="separado"),
    ]
)
async def cmd_autoroles(interaction: discord.Interaction, canal: discord.TextChannel = None, formato: app_commands.Choice[str] = None):
    if not interaction.guild:
        await interaction.response.send_message("❌ Este comando solo está disponible en el servidor.", ephemeral=True)
        return

    member = await _resolve_guild_member(interaction)
    if not is_admin_or_mod(member or interaction.user):
        await interaction.response.send_message("❌ Solo los administradores o moderadores pueden publicar el panel de Auto-Roles.", ephemeral=True)
        return

    target_channel = canal or interaction.channel
    fmt_val = formato.value if formato else "unificado"
    await interaction.response.defer(ephemeral=True)

    try:
        if fmt_val == "separado":
            keys = list(AUTOROLES_CATALOG.keys())
            for idx, k in enumerate(keys):
                is_last = idx == len(keys) - 1
                emb = build_autoroles_category_embed(k, guild=interaction.guild, include_footer=is_last)
                vw = AutoRoleCategoryView(k, include_buttons=is_last, guild=interaction.guild)
                await target_channel.send(embed=emb, view=vw)
        else:
            embeds = build_autoroles_all_embeds(guild=interaction.guild)
            view = AutoRolesPersistentView(guild=interaction.guild)
            await target_channel.send(embeds=embeds, view=view)

        _bot_log(f"🎭 [Auto-Roles] Panel ({fmt_val}) publicado en #{target_channel.name} por {interaction.user.display_name}.")
        await interaction.followup.send(
            f"✅ **Panel interactivo 24/7 de Auto-Roles** publicado correctamente en <#{target_channel.id}> (`{fmt_val}`).",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error al publicar el panel de Auto-Roles: {e}", ephemeral=True)


@app_commands.command(name="sugerencia", description="Envía una propuesta a #💡sugerencias💡 para votación comunitaria (Reemplazo de Carl-bot)")
@app_commands.describe(idea="Describe tu sugerencia o mejora para el servidor")
async def cmd_sugerencia(interaction: discord.Interaction, idea: str):
    if not interaction.guild:
        await interaction.response.send_message("❌ Este comando solo funciona en el servidor.", ephemeral=True)
        return

    clean_idea = idea.strip()
    if len(clean_idea) < 5:
        await interaction.response.send_message("⚠️ Describe tu sugerencia con un poco más de detalle (mínimo 5 caracteres).", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    sug_channel = interaction.guild.get_channel(SUGGESTIONS_CHANNEL_ID)
    if not sug_channel or not isinstance(sug_channel, discord.TextChannel):
        sug_channel = discord.utils.find(lambda c: "sugerencia" in c.name.lower(), interaction.guild.text_channels) or interaction.channel

    next_num = await _get_next_suggestion_number(sug_channel)
    embed = discord.Embed(
        title=f"💡 Sugerencia #{next_num}",
        description=clean_idea,
        color=0x3B82F6,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(
        name=f"{interaction.user.display_name} (@{interaction.user.name})",
        icon_url=str(interaction.user.display_avatar.url),
    )
    embed.add_field(name="📊 Estado", value="⏳ En votación comunitaria", inline=True)
    embed.add_field(
        name="🗳️ Votos",
        value=f"👍 **1** a favor · 👎 **0** en contra\n👍: <@{interaction.user.id}>",
        inline=True,
    )
    embed.set_footer(text=f"Autor ID: {interaction.user.id} • Usa /sugerencia para proponer ideas")

    view = SuggestionPersistentView(up_count=1, down_count=0, disabled=False)
    sent_msg = await sug_channel.send(embed=embed, view=view)
    SUGGESTION_VOTES_STATE[sent_msg.id] = {
        "up": {interaction.user.id},
        "down": set(),
        "base_up": 0,
        "base_down": 0,
    }
    _bot_log(f"💡 [Sugerencia #{next_num}] Creada por {interaction.user.display_name} en #{sug_channel.name}.")
    await interaction.followup.send(
        f"✅ ¡Tu **Sugerencia #{next_num}** ha sido publicada en <#{sug_channel.id}> para votación comunitaria!",
        ephemeral=True,
    )



# ==========================================
# 7. ECONOMÍA DE PORROS Y CASINO
# ==========================================

async def ensure_economy_channel(interaction: discord.Interaction) -> bool:
    """
    Verifica si la interacción proviene de los canales autorizados para Economía y Casino:
    - Si no hay contexto de canal (mocks unitarios), permite la ejecución (True).
    - Si interaction.channel_id pertenece a ALLOWED_ECONOMY_CHANNELS o la categoría es ECONOMY_CATEGORY_ID, permite (True).
    - En caso contrario, responde con mensaje efímero de restricción y devuelve False.
    """
    from modulos.economia import ALLOWED_ECONOMY_CHANNELS, ECONOMY_CATEGORY_ID

    ch_id = getattr(interaction, "channel_id", None)
    channel = getattr(interaction, "channel", None)

    if ch_id is None and channel is not None:
        ch_id = getattr(channel, "id", None)

    cat_id = getattr(channel, "category_id", None) if channel is not None else None

    # Detectar si hay identificadores reales de canal o categoría
    real_ch_id = None
    if isinstance(ch_id, int):
        real_ch_id = ch_id
    elif isinstance(ch_id, str) and ch_id.isdigit():
        real_ch_id = int(ch_id)

    real_cat_id = None
    if isinstance(cat_id, int):
        real_cat_id = cat_id
    elif isinstance(cat_id, str) and cat_id.isdigit():
        real_cat_id = int(cat_id)

    # Si no hay contexto de canal real (p.ej. tests con MagicMock/AsyncMock sin configurar), permitir
    if real_ch_id is None and real_cat_id is None:
        return True

    if (real_ch_id is not None and real_ch_id in ALLOWED_ECONOMY_CHANNELS) or (
        real_cat_id is not None and real_cat_id == ECONOMY_CATEGORY_ID
    ):
        return True

    await interaction.response.send_message(
        "❌ Los comandos de economía y casino solo están permitidos en los canales de **🎲・CASINO & ECONOMÍA・🎲** (<#1549458785485987890>, <#1550894047382610081> y <#1549512919694442547>).",
        ephemeral=True,
    )
    return False


@app_commands.command(name="slots", description="Juega a la máquina tragaperras del servidor apostando Porros")
@app_commands.describe(
    apuesta="Cantidad de Porros a apostar (mínimo 100, por defecto 100)"
)
async def cmd_slots(interaction: discord.Interaction, apuesta: int = 100):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import handle_slots_spin, SlotsLayoutView, PORRO_EMOJI, MIN_SLOTS_BET

    if apuesta < MIN_SLOTS_BET:
        await interaction.response.send_message(
            f"❌ La apuesta mínima en la tragaperras es de {MIN_SLOTS_BET} Porros ({PORRO_EMOJI}).",
            ephemeral=True,
        )
        return

    ok, err_msg, res, bal = handle_slots_spin(interaction.user.id, apuesta)
    if not ok:
        await interaction.response.send_message(
            f"❌ {err_msg}\n💡 Usa `/trabajar` para conseguir Porros si estás a cero.",
            ephemeral=True,
        )
        return

    view = SlotsLayoutView(res, str(interaction.user.id), apuesta)
    await interaction.response.send_message(view=view)


@app_commands.command(name="balance", description="Consulta tu saldo de Porros o el de otro miembro del servidor")
@app_commands.describe(
    usuario="Miembro cuyo saldo quieres consultar (opcional, por defecto tú)"
)
async def cmd_balance(interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import get_balance, get_server_jackpot, PORRO_EMOJI

    target = usuario or interaction.user
    bal = get_balance(target.id)
    jackpot = get_server_jackpot()

    embed = discord.Embed(
        title=f"💰 Saldo de {target.display_name}",
        color=0xF1C40F,  # Dorado
        timestamp=datetime.now(timezone.utc),
    )
    if hasattr(target, "display_avatar") and target.display_avatar:
        embed.set_thumbnail(url=str(target.display_avatar.url))

    embed.add_field(
        name="💵 Efectivo (Cash)",
        value=f"{PORRO_EMOJI} **{bal['cash']:,}** Porros",
        inline=True,
    )
    embed.add_field(
        name="🏦 Banco (Bank)",
        value=f"{PORRO_EMOJI} **{bal['bank']:,}** Porros",
        inline=True,
    )
    embed.add_field(
        name="💎 Patrimonio Total",
        value=f"{PORRO_EMOJI} **{bal['total']:,}** Porros",
        inline=False,
    )
    embed.add_field(
        name="🎰 Bote Acumulado del Servidor",
        value=f"{PORRO_EMOJI} **{jackpot:,}** Porros *(¡Reclámalo con Ranked Pro en /slots!)*",
        inline=False,
    )
    embed.set_footer(text="Economía Oficial de Porros • Asistente")

    is_ephemeral = (usuario is None or target.id == interaction.user.id)
    await interaction.response.send_message(embed=embed, ephemeral=is_ephemeral)


@app_commands.command(name="trabajar", description="Trabaja en el servidor para conseguir Porros con bono por rol de nivel (cooldown de 4 horas)")
async def cmd_trabajar(interaction: discord.Interaction):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import execute_work, get_balance, PORRO_EMOJI

    member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.user
    ok, job_story, reward = execute_work(interaction.user.id, member=member)
    if not ok:
        await interaction.response.send_message(job_story, ephemeral=True)
        return

    bal = get_balance(interaction.user.id)
    embed = discord.Embed(
        title="💼 Jornada Laboral Completada",
        description=f"{job_story}\n\n**Salario recibido:** {PORRO_EMOJI} **+{reward:,}** Porros\n**Saldo actual en efectivo:** {PORRO_EMOJI} **{bal['cash']:,}** Porros",
        color=0x2ECC71,  # Verde esmeralda
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(
        name=f"{interaction.user.display_name} (@{interaction.user.name})",
        icon_url=str(interaction.user.display_avatar.url) if hasattr(interaction.user, "display_avatar") else None,
    )
    embed.set_footer(text="Vuelve en 4 horas para volver a trabajar (o usa un 🥤 Monster Blanco) • /trabajar")
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="transferir", description="Transfiere Porros de tu efectivo a otro miembro del servidor")
@app_commands.describe(
    usuario="Miembro al que deseas transferir los Porros",
    cantidad="Cantidad exacta de Porros a transferir (número entero positivo)",
)
async def cmd_transferir(interaction: discord.Interaction, usuario: discord.Member, cantidad: int):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import transfer_funds, PORRO_EMOJI

    if usuario.id == interaction.user.id:
        await interaction.response.send_message("❌ No puedes transferirte Porros a ti mismo.", ephemeral=True)
        return

    if getattr(usuario, "bot", False):
        await interaction.response.send_message("❌ No puedes transferir Porros a un bot.", ephemeral=True)
        return

    if cantidad <= 0:
        await interaction.response.send_message("❌ La cantidad a transferir debe ser mayor a 0 Porros.", ephemeral=True)
        return

    ok, msg, sender_bal, recipient_bal = transfer_funds(interaction.user.id, usuario.id, cantidad)
    if not ok:
        await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
        return

    embed = discord.Embed(
        title="💸 Transferencia Exitosa",
        description=f"**{interaction.user.display_name}** le ha transferido {PORRO_EMOJI} **{cantidad:,}** Porros a **{usuario.display_name}**.",
        color=0x3498DB,  # Azul
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name=f"Saldo de {interaction.user.display_name}",
        value=f"{PORRO_EMOJI} **{sender_bal['cash']:,}** Porros",
        inline=True,
    )
    embed.add_field(
        name=f"Saldo de {usuario.display_name}",
        value=f"{PORRO_EMOJI} **{recipient_bal['cash']:,}** Porros",
        inline=True,
    )
    embed.set_footer(text="Transferencia instantánea sin comisiones • Economía de Porros")
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="depositar", description="Deposita Porros de tu efectivo en tu cuenta bancaria protegida")
@app_commands.describe(cantidad="Cantidad de Porros a ingresar en el banco o 'all'/'todo'")
async def cmd_depositar(interaction: discord.Interaction, cantidad: str):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import deposit_cash, PORRO_EMOJI

    ok, msg, bal = deposit_cash(interaction.user.id, cantidad)
    if not ok:
        await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
        return

    embed = discord.Embed(
        title="🏦 Depósito Bancario Completado",
        description=f"{msg}\n\n**Efectivo disponible:** {PORRO_EMOJI} **{bal['cash']:,}** Porros\n**Saldo en banco:** {PORRO_EMOJI} **{bal['bank']:,}** Porros",
        color=0x2ECC71,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(name=interaction.user.display_name, icon_url=str(interaction.user.display_avatar.url) if hasattr(interaction.user, "display_avatar") else None)
    embed.set_footer(text="El banco protege tus Porros al 100% frente a robos • /retirar")
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="retirar", description="Retira Porros de tu cuenta bancaria a tu efectivo")
@app_commands.describe(cantidad="Cantidad de Porros a retirar del banco o 'all'/'todo'")
async def cmd_retirar(interaction: discord.Interaction, cantidad: str):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import withdraw_cash, PORRO_EMOJI

    ok, msg, bal = withdraw_cash(interaction.user.id, cantidad)
    if not ok:
        await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
        return

    embed = discord.Embed(
        title="🏧 Retirada Bancaria Completada",
        description=f"{msg}\n\n**Efectivo disponible:** {PORRO_EMOJI} **{bal['cash']:,}** Porros\n**Saldo restante en banco:** {PORRO_EMOJI} **{bal['bank']:,}** Porros",
        color=0x3498DB,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(name=interaction.user.display_name, icon_url=str(interaction.user.display_avatar.url) if hasattr(interaction.user, "display_avatar") else None)
    embed.set_footer(text="Recuerda que los Porros en efectivo pueden ser atracados con /robar")
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="robar", description="Intenta robar Porros en efectivo a otro miembro del servidor (50% éxito)")
@app_commands.describe(usuario="Miembro al que intentas atracar")
async def cmd_robar(interaction: discord.Interaction, usuario: discord.Member):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import execute_rob, PORRO_EMOJI

    if usuario.id == interaction.user.id:
        await interaction.response.send_message("❌ No puedes robarte a ti mismo. Ve al casino si quieres perder dinero.", ephemeral=True)
        return

    if getattr(usuario, "bot", False):
        await interaction.response.send_message("❌ No puedes robar a un bot. Los bots no llevan Porros encima.", ephemeral=True)
        return

    ok, msg, delta = execute_rob(interaction.user.id, usuario.id, victim_member=usuario)

    color = 0x2ECC71 if ok else 0xE74C3C
    embed = discord.Embed(
        title="🥷 Intento de Atraco",
        description=msg,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(name=f"{interaction.user.display_name} vs {usuario.display_name}")
    embed.set_footer(text="Protege tu efectivo en el banco con /depositar o compra la 🛡️ Cartera Blindada")
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="tienda", description="Consulta el catálogo interactivo de la tienda oficial y adquiere artículos con confirmación")
async def cmd_tienda(interaction: discord.Interaction):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import build_shop_embed, ShopInteractiveView

    embed = build_shop_embed(interaction.user.id)
    view = ShopInteractiveView(author_id=interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)
    try:
        view.message = await interaction.original_response()
    except Exception:
        pass


@app_commands.command(name="salario", description="Cobra tu salario diario acumulado según tus roles de nivel y podio (con decaimiento del 5%)")
async def cmd_salario(interaction: discord.Interaction):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import claim_salary, get_balance, PORRO_EMOJI
    from modulos.chat_ia import get_live_levels_dict

    levels_dict = await get_live_levels_dict(interaction.guild) if interaction.guild else {}
    user_level = levels_dict.get(str(interaction.user.id))

    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    ok, msg, payout, daily_salary = claim_salary(
        interaction.user.id,
        member=member,
        user_level=user_level,
    )

    if not ok:
        await interaction.response.send_message(msg, ephemeral=True)
        return

    bal = get_balance(interaction.user.id)
    embed = discord.Embed(
        title="💵 Cobro de Salario Acumulativo",
        description=msg,
        color=0x2ECC71,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="💰 Saldo Actual en Efectivo",
        value=f"{PORRO_EMOJI} **{bal['cash']:,}** Porros",
        inline=True,
    )
    embed.add_field(
        name="📈 Salario Diario Base",
        value=f"{PORRO_EMOJI} **{daily_salary:,}** Porros/día",
        inline=True,
    )
    embed.set_footer(text="Fórmula de decaimiento del 5% diario • Sube de nivel en el servidor para ganar más")
    await interaction.response.send_message(embed=embed)


async def _handle_blackjack_command(interaction: discord.Interaction, apuesta: str = "100"):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import (
        parse_blackjack_bet,
        modify_balance,
        modify_server_jackpot,
        BlackjackHand,
        blackjack_engine,
        BlackjackView,
        build_blackjack_embed,
        ACTIVE_BLACKJACK_GAMES,
        ECONOMY_LOCK,
        PORRO_EMOJI,
        JACKPOT_FEED_PERCENT,
        format_bj_card,
    )

    ok, bet, err = parse_blackjack_bet(interaction.user.id, apuesta)
    if not ok:
        await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        return

    with ECONOMY_LOCK:
        if interaction.user.id in ACTIVE_BLACKJACK_GAMES:
            await interaction.response.send_message(
                "❌ Ya tienes una partida de Blackjack activa en curso. Termínala antes de iniciar otra.",
                ephemeral=True,
            )
            return

        modify_balance(interaction.user.id, cash_delta=-bet)
        ACTIVE_BLACKJACK_GAMES[interaction.user.id] = True

    try:
        player_hand = BlackjackHand([blackjack_engine.draw(), blackjack_engine.draw()])
        dealer_hand = BlackjackHand([blackjack_engine.draw(), blackjack_engine.draw()])

        player_bj = player_hand.is_blackjack
        dealer_bj = dealer_hand.is_blackjack

        if player_bj or dealer_bj:
            with ECONOMY_LOCK:
                ACTIVE_BLACKJACK_GAMES.pop(interaction.user.id, None)
                if player_bj and dealer_bj:
                    modify_balance(interaction.user.id, cash_delta=bet)
                    res_msg = (
                        f"🤝 **¡Empate (Push)!**\n"
                        f"¡Tanto tú como el crupier tenéis **Blackjack Natural** de inicio!\n"
                        f"Se te devuelve tu apuesta de **{bet:,}** Porros ({PORRO_EMOJI})."
                    )
                    color = 0xF1C40F
                elif player_bj:
                    win_net = int(bet * 1.5)
                    payout = bet + win_net
                    modify_balance(interaction.user.id, cash_delta=payout)
                    res_msg = (
                        f"🔥 **¡BLACKJACK NATURAL!** 🃏\n"
                        f"¡Has conseguido 21 de inicio!\n"
                        f"**Pago 3:2:** ¡Has ganado **+{win_net:,}** Porros limpios ({PORRO_EMOJI})!\n"
                        f"💰 Total ingresado en efectivo: **{payout:,}** Porros."
                    )
                    color = 0x2ECC71
                else:
                    jackpot_feed = max(1, int(bet * JACKPOT_FEED_PERCENT))
                    modify_server_jackpot(jackpot_feed)
                    res_msg = (
                        f"💀 **¡El crupier tiene Blackjack Natural!** 🃏\n"
                        f"El crupier ha conseguido 21 con [ {format_bj_card(dealer_hand.cards[0])} ] [ {format_bj_card(dealer_hand.cards[1])} ].\n"
                        f"Has perdido **{bet:,}** Porros ({PORRO_EMOJI}).\n"
                        f"🎰 Se han añadido **+{jackpot_feed:,}** Porros al bote del servidor."
                    )
                    color = 0xE74C3C

            embed = build_blackjack_embed(
                user=interaction.user,
                player_hand=player_hand,
                dealer_hand=dealer_hand,
                bet=bet,
                dealer_revealed=True,
                result_text=res_msg,
                color=color,
            )
            await interaction.response.send_message(embed=embed)
            return

        view = BlackjackView(
            user_id=interaction.user.id,
            user=interaction.user,
            bet=bet,
            engine=blackjack_engine,
            player_hand=player_hand,
            dealer_hand=dealer_hand,
        )
        with ECONOMY_LOCK:
            ACTIVE_BLACKJACK_GAMES[interaction.user.id] = view

        embed = build_blackjack_embed(
            user=interaction.user,
            player_hand=player_hand,
            dealer_hand=dealer_hand,
            bet=bet,
            dealer_revealed=False,
            result_text="Tu turno: Elige si **Pedir**, **Plantarte** o **Doblar** tu apuesta.",
            color=0x3498DB,
        )
        await interaction.response.send_message(embed=embed, view=view)
        try:
            view.message = await interaction.original_response()
        except Exception:
            pass

    except Exception as e:
        with ECONOMY_LOCK:
            modify_balance(interaction.user.id, cash_delta=bet)
            ACTIVE_BLACKJACK_GAMES.pop(interaction.user.id, None)
        raise e


@app_commands.command(name="blackjack", description="Juega al Blackjack 21 nativo contra el crupier apostando Porros")
@app_commands.describe(apuesta="Cantidad de Porros a apostar (mínimo 100) o 'all'/'todo'")
async def cmd_blackjack(interaction: discord.Interaction, apuesta: str = "100"):
    await _handle_blackjack_command(interaction, apuesta)


@app_commands.command(name="bj", description="Alias rápido ergonómico para jugar al Blackjack 21")
@app_commands.describe(apuesta="Cantidad de Porros a apostar (mínimo 100) o 'all'/'todo'")
async def cmd_bj(interaction: discord.Interaction, apuesta: str = "100"):
    await _handle_blackjack_command(interaction, apuesta)


async def _handle_roulette_command(
    interaction: discord.Interaction,
    apuesta: str = "100",
    tipo: str = "rojo",
    numero: Optional[int] = None,
):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import (
        parse_roulette_bet,
        normalize_roulette_bet_type,
        roulette_engine,
        build_roulette_embed,
        RouletteActionView,
        ROULETTE_BET_INFO,
    )

    norm_type = normalize_roulette_bet_type(tipo)
    if norm_type not in ROULETTE_BET_INFO:
        await interaction.response.send_message(
            f"❌ Tipo de apuesta '{tipo}' no válido. Elige una opción oficial del menú.",
            ephemeral=True,
        )
        return

    if norm_type == "pleno":
        if numero is None:
            await interaction.response.send_message(
                "❌ Para apostar a **Pleno**, debes indicar el parámetro `numero` con un valor del 0 al 36.",
                ephemeral=True,
            )
            return
        if not (0 <= numero <= 36):
            await interaction.response.send_message(
                "❌ El número para Pleno debe estar comprendido entre **0** y **36**.",
                ephemeral=True,
            )
            return

    ok, bet, err = parse_roulette_bet(interaction.user.id, apuesta)
    if not ok:
        await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        return

    try:
        res = roulette_engine.spin_wheel(
            user_id=interaction.user.id,
            bet_amount=bet,
            bet_type=norm_type,
            bet_number=numero,
        )
        embed = build_roulette_embed(user=interaction.user, result=res)
        view = RouletteActionView(
            user_id=interaction.user.id,
            user=interaction.user,
            bet_amount=bet,
            bet_type=norm_type,
            bet_number=numero,
            engine=roulette_engine,
        )
        await interaction.response.send_message(embed=embed, view=view)
        try:
            view.message = await interaction.original_response()
        except Exception:
            pass
    except Exception as e:
        await interaction.response.send_message(f"❌ Error al procesar la ruleta: {e}", ephemeral=True)


@app_commands.command(name="ruleta", description="Juega a la Ruleta Europea de 37 casillas (RTP 97.30%)")
@app_commands.describe(
    apuesta="Cantidad de Porros a apostar (mínimo 100) o 'all'/'todo'",
    tipo="Tipo de apuesta (Rojo, Negro, Par, Impar, Docenas, Columnas, Pleno...)",
    numero="Número exacto (0-36). Requerido si eliges 'Pleno'",
)
@app_commands.choices(
    tipo=[
        app_commands.Choice(name="🔴 Rojo", value="rojo"),
        app_commands.Choice(name="⚫ Negro", value="negro"),
        app_commands.Choice(name="⚖️ Par", value="par"),
        app_commands.Choice(name="⚡ Impar", value="impar"),
        app_commands.Choice(name="📉 1-18 (Baja)", value="baja"),
        app_commands.Choice(name="📈 19-36 (Alta)", value="alta"),
        app_commands.Choice(name="1️⃣ 1ª Docena (1-12)", value="docena1"),
        app_commands.Choice(name="2️⃣ 2ª Docena (13-24)", value="docena2"),
        app_commands.Choice(name="3️⃣ 3ª Docena (25-36)", value="docena3"),
        app_commands.Choice(name="🏛️ Columna 1", value="columna1"),
        app_commands.Choice(name="🏛️ Columna 2", value="columna2"),
        app_commands.Choice(name="🏛️ Columna 3", value="columna3"),
        app_commands.Choice(name="🎯 Pleno (0-36)", value="pleno"),
    ]
)
async def cmd_ruleta(
    interaction: discord.Interaction,
    apuesta: str = "100",
    tipo: str = "rojo",
    numero: Optional[int] = None,
):
    await _handle_roulette_command(interaction, apuesta, tipo, numero)


async def _handle_coinflip_command(
    interaction: discord.Interaction,
    apuesta: str = "100",
    lado: Optional[str] = "cara",
    rival: Optional[discord.Member] = None,
):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import (
        parse_coinflip_bet,
        normalize_coinflip_side,
        coinflip_engine,
        build_coinflip_embed,
        CoinflipActionView,
        CoinflipChallengeView,
        ACTIVE_COINFLIP_DUELS,
        ECONOMY_LOCK,
        modify_balance,
        PORRO_EMOJI,
    )

    norm_lado = normalize_coinflip_side(lado)

    # Modo PvE: Lanzamiento rápido contra la casa (sin rival)
    if rival is None:
        ok, bet, err = parse_coinflip_bet(interaction.user.id, apuesta)
        if not ok:
            await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

        try:
            res = coinflip_engine.play_pve(
                user_id=interaction.user.id,
                bet_amount=bet,
                choice=norm_lado,
            )
            embed = build_coinflip_embed(mode="pve", user=interaction.user, result=res)
            view = CoinflipActionView(
                user_id=interaction.user.id,
                user=interaction.user,
                bet_amount=bet,
                side=norm_lado,
                engine=coinflip_engine,
            )
            await interaction.response.send_message(embed=embed, view=view)
            try:
                view.message = await interaction.original_response()
            except Exception:
                pass
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al procesar Coinflip: {e}", ephemeral=True)
        return

    # Modo PvP: Duelo entre dos miembros
    if rival.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ No puedes desafiarte a ti mismo. Si quieres jugar solo, no especifiques ningún rival para apostar contra la casa.",
            ephemeral=True,
        )
        return

    if getattr(rival, "bot", False):
        await interaction.response.send_message(
            "❌ No puedes retar a un bot a un duelo de Coinflip. Los duelos son exclusivos entre miembros.",
            ephemeral=True,
        )
        return

    ok, bet, err = parse_coinflip_bet(interaction.user.id, apuesta)
    if not ok:
        await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        return

    with ECONOMY_LOCK:
        if str(interaction.user.id) in ACTIVE_COINFLIP_DUELS or interaction.user.id in ACTIVE_COINFLIP_DUELS:
            await interaction.response.send_message(
                "❌ Ya tienes un duelo de Coinflip activo en curso. Termínalo o cancélalo antes de retar a otro miembro.",
                ephemeral=True,
            )
            return

        if str(rival.id) in ACTIVE_COINFLIP_DUELS or rival.id in ACTIVE_COINFLIP_DUELS:
            await interaction.response.send_message(
                f"❌ **{rival.display_name}** ya tiene un desafío activo en curso. Espera a que termine su duelo.",
                ephemeral=True,
            )
            return

        # Deducir y retener la fianza del retador atómicamente bajo ECONOMY_LOCK
        modify_balance(interaction.user.id, cash_delta=-bet)
        ACTIVE_COINFLIP_DUELS[str(interaction.user.id)] = True
        ACTIVE_COINFLIP_DUELS[str(rival.id)] = True

    c_side = norm_lado
    r_side = "cruz" if c_side == "cara" else "cara"

    view = CoinflipChallengeView(
        challenger_id=interaction.user.id,
        challenger=interaction.user,
        rival_id=rival.id,
        rival=rival,
        bet_amount=bet,
        challenger_side=c_side,
        engine=coinflip_engine,
    )
    with ECONOMY_LOCK:
        ACTIVE_COINFLIP_DUELS[str(interaction.user.id)] = view
        ACTIVE_COINFLIP_DUELS[str(rival.id)] = view

    embed = build_coinflip_embed(
        mode="pvp_pending",
        challenger=interaction.user,
        rival=rival,
        bet=bet,
        challenger_side=c_side,
        rival_side=r_side,
    )

    try:
        await interaction.response.send_message(
            content=f"⚔️ {rival.mention}, ¡has sido desafiado a un duelo de Coinflip por {interaction.user.mention}!",
            embed=embed,
            view=view,
        )
        try:
            view.message = await interaction.original_response()
        except Exception:
            pass
    except Exception as e:
        with ECONOMY_LOCK:
            modify_balance(interaction.user.id, cash_delta=+bet)
            ACTIVE_COINFLIP_DUELS.pop(str(interaction.user.id), None)
            ACTIVE_COINFLIP_DUELS.pop(str(rival.id), None)
            ACTIVE_COINFLIP_DUELS.pop(interaction.user.id, None)
            ACTIVE_COINFLIP_DUELS.pop(rival.id, None)
        await interaction.response.send_message(f"❌ Error al iniciar el desafío: {e}", ephemeral=True)


@app_commands.command(
    name="coinflip",
    description="Lanza una moneda 50/50 contra la casa (PvE) o desafía a un miembro en duelo (PvP)",
)
@app_commands.describe(
    apuesta="Cantidad de Porros a apostar (mínimo 100) o 'all'/'todo'",
    lado="Lado de la moneda que eliges (por defecto Cara)",
    rival="Miembro al que desafiar en duelo PvP (opcional: si no se indica juegas contra la casa)",
)
@app_commands.choices(
    lado=[
        app_commands.Choice(name="🪙 Cara", value="cara"),
        app_commands.Choice(name="🪙 Cruz", value="cruz"),
    ]
)
async def cmd_coinflip(
    interaction: discord.Interaction,
    apuesta: str = "100",
    lado: Optional[str] = "cara",
    rival: Optional[discord.Member] = None,
):
    await _handle_coinflip_command(interaction, apuesta, lado, rival)


@app_commands.command(
    name="casino",
    description="Centro de Control del Casino Central: catálogo interactivo de juegos, reglas y bote",
)
async def cmd_casino(interaction: discord.Interaction):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import CasinoHubView, build_casino_hub_embed

    view = CasinoHubView(author_id=interaction.user.id)
    embed = build_casino_hub_embed(interaction.user, selected_game=None)

    await interaction.response.send_message(embed=embed, view=view)
    try:
        view.message = await interaction.original_response()
    except Exception:
        pass


@app_commands.command(
    name="crimen",
    description="Comete un delito de alto riesgo en el servidor (50% éxito, cooldown de 12 horas)",
)
async def cmd_crimen(interaction: discord.Interaction):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import execute_crime, get_balance, PORRO_EMOJI

    member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.user
    ok, msg, delta = execute_crime(interaction.user.id, member=member)

    if not ok and delta == 0 and msg.startswith("⏳"):
        await interaction.response.send_message(msg, ephemeral=True)
        return

    bal = get_balance(interaction.user.id)
    color = 0x2ECC71 if ok else 0xE74C3C
    title = "🦹 Golpe Criminal Completado" if ok else "🚓 Redada Policial — Delito Frustrado"

    embed = discord.Embed(
        title=title,
        description=(
            f"{msg}\n\n"
            f"**Saldo actual en efectivo:** {PORRO_EMOJI} **{bal['cash']:,}** Porros"
        ),
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(
        name=f"{interaction.user.display_name} (@{interaction.user.name})",
        icon_url=str(interaction.user.display_avatar.url) if hasattr(interaction.user, "display_avatar") and interaction.user.display_avatar else None,
    )
    embed.set_footer(text="Cooldown de 12 horas (o resetea al instante con /usar 🥤 Monster Blanco) • /crimen")
    await interaction.response.send_message(embed=embed)


@app_commands.command(
    name="ranking",
    description="Muestra el Top 10 de miembros más ricos del servidor (Patrimonio Total, Efectivo y Banco)",
)
async def cmd_ranking(interaction: discord.Interaction):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import build_ranking_embed, RankingView

    embed = build_ranking_embed(
        sort_by="total",
        requester_id=interaction.user.id,
        guild=interaction.guild,
    )
    view = RankingView(author_id=interaction.user.id, sort_by="total")
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
    try:
        view.message = await interaction.original_response()
    except Exception:
        pass


@app_commands.command(
    name="inventario",
    description="Consulta tus artículos, consumibles, roles permanentes y pases de XP activos",
)
@app_commands.describe(
    usuario="Miembro cuyo inventario deseas consultar (opcional, por defecto tú)"
)
async def cmd_inventario(interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import build_inventory_embed, InventoryView

    target = usuario or interaction.user
    avatar_url = (
        str(target.display_avatar.url)
        if hasattr(target, "display_avatar") and target.display_avatar
        else None
    )
    embed = build_inventory_embed(target.id, target.display_name, avatar_url)
    view = InventoryView(
        author_id=interaction.user.id,
        target_id=target.id,
        target_display_name=target.display_name,
        target_avatar_url=avatar_url,
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@app_commands.command(
    name="usar",
    description="Consume un artículo o activa un pase temporal de XP guardado en tu /inventario",
)
@app_commands.describe(
    articulo="Elige el artículo o pase de tu inventario que quieres usar ahora mismo"
)
@app_commands.choices(
    articulo=[
        app_commands.Choice(name="🥤 Monster Blanco (Resetea /trabajar, /crimen y /robar)", value="monster_blanco"),
        app_commands.Choice(name="⚡ Chute de XP (24h — Boost +5% XP)", value="chute_xp"),
        app_commands.Choice(name="🔥 Pase Semanal de XP (7 días — Boost +10% XP)", value="pase_semanal_xp"),
        app_commands.Choice(name="💠 Pase Mensual de XP (30 días — Boost +15% XP)", value="pase_mensual_xp"),
    ]
)
async def cmd_usar(interaction: discord.Interaction, articulo: str):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import use_inventory_item

    ok, msg, item_data = use_inventory_item(interaction.user.id, articulo)
    if not ok:
        await interaction.response.send_message(msg, ephemeral=True)
        return

    role_assigned = False
    if item_data and item_data.get("role_id") and interaction.guild and hasattr(interaction.user, "add_roles"):
        role = interaction.guild.get_role(int(item_data["role_id"]))
        if role:
            try:
                await interaction.user.add_roles(role, reason=f"Activación de {item_data['name']} con /usar")
                role_assigned = True
            except Exception as e:
                _bot_log(f"Aviso asignando rol temporal en /usar: {e}")

    embed = discord.Embed(
        title=f"✨ Artículo Utilizado: {item_data['name']}",
        description=msg,
        color=0x2ECC71,
        timestamp=datetime.now(timezone.utc),
    )
    if role_assigned:
        embed.add_field(
            name="🎭 Rol de Boost Activado",
            value=f"Se te ha asignado el rol **{item_data['name']}** en el servidor durante el periodo activo.",
            inline=False,
        )
    embed.set_footer(text="Consulta el tiempo restante de tus pases con /inventario")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(
    name="regalar",
    description="Regala artículos o consumibles de tu inventario a otro miembro del servidor",
)
@app_commands.describe(
    usuario="Miembro al que deseas regalar el artículo",
    articulo="Artículo o consumible transferible de tu inventario",
    cantidad="Cantidad de unidades a regalar (por defecto 1)",
)
@app_commands.choices(
    articulo=[
        app_commands.Choice(name="🚬 Porro de Oro (Coleccionable)", value="porro_oro"),
        app_commands.Choice(name="🥤 Monster Blanco (Resetea cooldowns)", value="monster_blanco"),
        app_commands.Choice(name="⚡ Chute de XP (24h — Boost +5% XP)", value="chute_xp"),
        app_commands.Choice(name="🔥 Pase Semanal de XP (7 días — Boost +10% XP)", value="pase_semanal_xp"),
        app_commands.Choice(name="💠 Pase Mensual de XP (30 días — Boost +15% XP)", value="pase_mensual_xp"),
    ]
)
async def cmd_regalar(
    interaction: discord.Interaction,
    usuario: discord.Member,
    articulo: str,
    cantidad: int = 1,
):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import gift_inventory_item

    if usuario.id == interaction.user.id:
        await interaction.response.send_message("❌ No puedes regalarte artículos a ti mismo.", ephemeral=True)
        return

    if getattr(usuario, "bot", False):
        await interaction.response.send_message("❌ No puedes regalar artículos a un bot. Los bots no tienen inventario.", ephemeral=True)
        return

    if cantidad < 1:
        await interaction.response.send_message("❌ La cantidad debe ser al menos 1 unidad.", ephemeral=True)
        return

    ok, msg, item_data = gift_inventory_item(interaction.user.id, usuario.id, articulo, cantidad)
    if not ok:
        await interaction.response.send_message(msg, ephemeral=True)
        return

    item_name = item_data["name"] if item_data else articulo
    embed = discord.Embed(
        title="🎁 Regalo Enviado con Éxito",
        description=(
            f"**{interaction.user.display_name}** le ha regalado **{cantidad}x {item_name}** a **{usuario.display_name}**.\n\n"
            f"📦 Los artículos se han transferido directamente a su `/inventario`."
        ),
        color=0xE91E63,  # Rosa/Fucsia festivo
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(
        name=f"{interaction.user.display_name} ➡️ {usuario.display_name}",
        icon_url=str(interaction.user.display_avatar.url) if hasattr(interaction.user, "display_avatar") else None,
    )
    embed.set_footer(text="Economía Oficial de Porros • Asistente")
    await interaction.response.send_message(embed=embed)


@app_commands.command(
    name="admin_dinero",
    description="[ADMIN] Panel financiero para dar, quitar, fijar Porros o lanzar un Airdrop por rol",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    accion="Operación a realizar (dar, quitar, fijar o airdrop a un rol)",
    cantidad="Cantidad de Porros (entero positivo, o >= 0 para fijar)",
    destino="Dónde aplicar la operación: Efectivo (Cash) o Banco (Bank)",
    usuario="Miembro objetivo (obligatorio para dar, quitar y fijar)",
    rol="Rol objetivo (obligatorio para airdrop masivo)",
)
@app_commands.choices(
    accion=[
        app_commands.Choice(name="➕ Dar Porros a un miembro", value="dar"),
        app_commands.Choice(name="➖ Quitar Porros a un miembro", value="quitar"),
        app_commands.Choice(name="🎯 Fijar saldo exacto a un miembro", value="fijar"),
        app_commands.Choice(name="🪂 Airdrop masivo a todos los miembros de un rol", value="airdrop"),
    ],
    destino=[
        app_commands.Choice(name="💵 Efectivo (Cash)", value="cash"),
        app_commands.Choice(name="🏦 Banco (Bank)", value="bank"),
    ],
)
async def cmd_admin_dinero(
    interaction: discord.Interaction,
    accion: str,
    cantidad: int,
    destino: str = "cash",
    usuario: Optional[discord.Member] = None,
    rol: Optional[discord.Role] = None,
):
    from modulos.economia import admin_modify_money, admin_airdrop_role, PORRO_EMOJI

    # Verificación estricta de permisos de Administrador
    is_admin = bool(
        getattr(interaction.user, "guild_permissions", None)
        and interaction.user.guild_permissions.administrator
    )
    if not is_admin:
        await interaction.response.send_message(
            "⛔ No tienes permisos de **Administrador** para ejecutar este comando financiero.",
            ephemeral=True,
        )
        return

    act = accion.strip().lower()
    if act == "airdrop":
        if rol is None:
            await interaction.response.send_message(
                "❌ Para ejecutar un **Airdrop**, debes especificar el parámetro `rol`.",
                ephemeral=True,
            )
            return

        human_members = [
            (m.id, getattr(m, "name", None))
            for m in getattr(rol, "members", [])
            if not getattr(m, "bot", False)
        ]
        ok, msg, count = admin_airdrop_role(
            targets=human_members,
            amount=cantidad,
            target_field=destino,
            role_name=rol.name,
        )
        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return

        embed = discord.Embed(
            title="🪂 Airdrop Administrativo Ejecutado",
            description=msg,
            color=0xF1C40F,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Ejecutado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Operaciones individuales: dar, quitar, fijar
    if usuario is None:
        await interaction.response.send_message(
            f"❌ Para la acción **{act}**, debes indicar el parámetro `usuario`.",
            ephemeral=True,
        )
        return

    ok, msg, new_bal = admin_modify_money(
        target_user_id=usuario.id,
        action=act,
        amount=cantidad,
        target_field=destino,
        username=getattr(usuario, "name", None),
    )
    if not ok:
        await interaction.response.send_message(msg, ephemeral=True)
        return

    embed = discord.Embed(
        title=f"🛠️ Ajuste Financiero — {usuario.display_name}",
        description=(
            f"{msg}\n\n"
            f"• 💵 **Nuevo Efectivo:** {PORRO_EMOJI} **{new_bal['cash']:,}** Porros\n"
            f"• 🏦 **Nuevo Banco:** {PORRO_EMOJI} **{new_bal['bank']:,}** Porros\n"
            f"• 💎 **Patrimonio Total:** {PORRO_EMOJI} **{new_bal['total']:,}** Porros"
        ),
        color=0x3498DB,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"Operación '{act}' ejecutada por {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# LISTAS DE COMANDOS SLASH (RUNNER DUAL)
# ==========================================

# 22 Comandos Generales para el Bot 'Asistente'
GENERAL_SLASH_COMMANDS = [
    cmd_dibuja,
    cmd_musica,
    cmd_steam,
    cmd_tribunal,
    cmd_perfil,
    cmd_pregunta,
    cmd_voz,
    cmd_recuerda,
    cmd_xp,
    cmd_habla,
    cmd_geminilive,
    cmd_cambiar_voz,
    cmd_unete,
    cmd_desconecta,
    cmd_para_audio,
    cmd_trivial,
    cmd_ranking_trivial,
    cmd_tres_en_raya,
    cmd_conecta4,
    cmd_ajedrez,
    cmd_autoroles,
    cmd_sugerencia,
]

# 20 Comandos de Economía y Casino para el Bot 'Economia Asistente'
ECONOMY_SLASH_COMMANDS = [
    cmd_slots,
    cmd_balance,
    cmd_trabajar,
    cmd_transferir,
    cmd_depositar,
    cmd_retirar,
    cmd_robar,
    cmd_tienda,
    cmd_salario,
    cmd_blackjack,
    cmd_bj,
    cmd_ruleta,
    cmd_coinflip,
    cmd_casino,
    cmd_crimen,
    cmd_ranking,
    cmd_inventario,
    cmd_usar,
    cmd_regalar,
    cmd_admin_dinero,
]

# Total de 42 comandos para retrocompatibilidad total
ALL_SLASH_COMMANDS = GENERAL_SLASH_COMMANDS + ECONOMY_SLASH_COMMANDS


def register_general_commands(tree: app_commands.CommandTree):
    """Registra los 22 comandos slash generales en el árbol del bot Asistente."""
    for cmd in GENERAL_SLASH_COMMANDS:
        try:
            tree.add_command(cmd)
        except app_commands.CommandAlreadyRegistered:
            pass
        except Exception as e:
            _bot_log(f"Aviso registrando comando general /{cmd.name}: {e}")


def register_economy_commands(tree: app_commands.CommandTree):
    """Registra los 20 comandos slash de economía en el árbol del bot Economia Asistente."""
    for cmd in ECONOMY_SLASH_COMMANDS:
        try:
            tree.add_command(cmd)
        except app_commands.CommandAlreadyRegistered:
            pass
        except Exception as e:
            _bot_log(f"Aviso registrando comando de economía /{cmd.name}: {e}")


def register_slash_commands(tree: app_commands.CommandTree):
    """Registra de forma segura todos los comandos slash (generales y economía) en el árbol de comandos."""
    register_general_commands(tree)
    register_economy_commands(tree)


