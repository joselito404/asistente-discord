"""
Módulo The Sanvi Daily / Starboard Gráfico 2.0 para 'Asistente' en Discord.
Especificación canónica: docs/DISENO_SANVI_DAILY.md

Transforma mensajes célebres con 2 o más reacciones de ⭐ en portadas de periódico
vintage ('The Sanvi Daily') generadas localmente con Pillow a coste cero de tokens.
Reemplazo definitivo de Carl-bot en #⭐muro-de-la-fama⭐ (1548043919827271740).
"""

import os
import io
import json
import asyncio
import threading
import textwrap
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

import discord
from discord.ui import View, Button
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ==========================================
# CONSTANTES Y CONFIGURACIÓN CANÓNICA
# ==========================================

STARBOARD_CHANNEL_ID: int = 1548043919827271740  # #⭐muro-de-la-fama⭐
STAR_EMOJI: str = "⭐"  # \u2b50
MIN_STARS_THRESHOLD: int = 2

# Canales excluidos para evitar bucles o filtraciones de canales privados/staff
EXCLUDED_CHANNEL_IDS: set = {
    1548043919827271740,  # #⭐muro-de-la-fama⭐
    1537575196305653831,  # #🔒backup-datos
    1535676349451341885,  # #🛠️apps-solo-mods🛠️
    1537574896605265970,  # Legacy ID apps-solo-mods
    1549509420550066227,  # #🔒staff-sanvi🔒
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STARBOARD_DATA_PATH = os.path.join(BASE_DIR, "datos", "starboard.json")

STARBOARD_LOCK = asyncio.Lock()
_DISK_LOCK = threading.Lock()

# Paleta cromática vintage para Pillow
BG_COLOR = (245, 238, 219)        # #F5EEDB pergamino claro
INK_MAIN = (28, 25, 23)           # #1C1917 negro carboncillo
INK_MUTED = (85, 75, 65)          # #554B41 sepia intermedio
BORDER_COLOR = (50, 40, 30)       # #32281E marrón oscuro rotativo
STAMP_COLOR = (180, 50, 30)       # #B4321E rojo sello vintage


def _log(msg: str):
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{timestamp}] [Starboard] {msg}")


# ==========================================
# PERSISTENCIA ATÓMICA DE DATOS
# ==========================================

def load_starboard_data() -> Dict[str, Any]:
    """Carga los datos de starboard.json bajo bloqueo de disco."""
    with _DISK_LOCK:
        if not os.path.exists(STARBOARD_DATA_PATH):
            return {"next_edition_number": 1, "entries": {}}
        try:
            with open(STARBOARD_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
                data.setdefault("next_edition_number", 1)
                data.setdefault("entries", {})
                return data
        except Exception as e:
            _log(f"Error leyendo {STARBOARD_DATA_PATH}: {e}")
            return {"next_edition_number": 1, "entries": {}}


def save_starboard_data(data: Dict[str, Any]) -> None:
    """Guarda los datos en starboard.json con escritura atómica (.tmp + os.replace)."""
    with _DISK_LOCK:
        dir_name = os.path.dirname(STARBOARD_DATA_PATH)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        tmp_path = f"{STARBOARD_DATA_PATH}.tmp.{os.getpid()}_{threading.get_ident()}"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, STARBOARD_DATA_PATH)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


# ==========================================
# GESTOR DE FUENTES TIPOGRÁFICAS
# ==========================================

def _get_font(names: List[str], size: int) -> ImageFont.ImageFont:
    """Intenta cargar la primera fuente válida de la lista; hace fallback a default."""
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _get_title_font(size: int = 56) -> ImageFont.ImageFont:
    serif_candidates = [
        "timesbd.ttf", "times.ttf", "georgia.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
        "arialbd.ttf"
    ]
    return _get_font(serif_candidates, size)


def _get_body_font(size: int = 20, bold: bool = False) -> ImageFont.ImageFont:
    candidates = (
        ["timesbd.ttf", "georgiab.ttf", "arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]
        if bold else
        ["times.ttf", "georgia.ttf", "arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"]
    )
    return _get_font(candidates, size)


def _get_header_font(size: int = 15) -> ImageFont.ImageFont:
    candidates = [
        "arialbd.ttf", "arial.ttf", "timesbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    return _get_font(candidates, size)


def _draw_star_polygon(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    r_out: float,
    r_in: float,
    fill: Tuple[int, int, int],
    outline: Optional[Tuple[int, int, int]] = None,
) -> None:
    """Dibuja una estrella geométrica vectorial de 5 puntas perfecta en Pillow."""
    import math
    points = []
    angle_offset = -math.pi / 2
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        angle = angle_offset + i * (math.pi / 5)
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=fill, outline=outline)


def _draw_diamond_polygon(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    size: float,
    fill: Tuple[int, int, int],
) -> None:
    """Dibuja un rombo vectorial clásico sin depender de fuentes tipográficas."""
    draw.polygon([(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)], fill=fill)


def _clean_discord_text(text: str) -> str:
    """
    Limpia el texto de formato interno de Discord para maquetación tipográfica de prensa vintage:
    - Retira bloques de código y código inline.
    - Retira encabezados markdown (#, ##, ###, -#) y citas (>).
    - Retira emojis personalizados <:nombre:123456> para que no ensucien la cita de prensa.
    - Limpia menciones de usuarios, canales y roles.
    - Retira negritas/cursivas (**texto**, __texto__).
    - Normaliza espacios en blanco.
    """
    if not text:
        return ""
    import re
    # 1. Retirar bloques de código y código inline
    clean = re.sub(r"```[a-zA-Z]*\n?([\s\S]*?)```", r"\1", text)
    clean = re.sub(r"`([^`]+)`", r"\1", clean)
    # 2. Retirar encabezados markdown y subtextos
    clean = re.sub(r"(?m)^#{1,3}\s*", "", clean)
    clean = re.sub(r"(?m)^-#\s*", "", clean)
    clean = re.sub(r"#{1,3}\s+", "", clean)
    # 3. Retirar blockquotes markdown
    clean = re.sub(r"(?m)^>+\s*", "", clean)
    # 4. Retirar emojis personalizados de Discord (<:nombre:id> o <a:nombre:id>)
    clean = re.sub(r"<a?:\w+:\d+>", "", clean)
    # 5. Reemplazar menciones numéricas de usuarios por @usuario
    clean = re.sub(r"<@!?\d+>", "@usuario", clean)
    # 6. Reemplazar menciones de canales <#id> por #canal
    clean = re.sub(r"<#\d+>", "#canal", clean)
    # 7. Reemplazar menciones de roles <@&id> por @rol
    clean = re.sub(r"<@&\d+>", "@rol", clean)
    # 8. Retirar negritas y cursivas excesivas (**texto**, __texto__)
    clean = re.sub(r"\*\*(.*?)\*\*", r"\1", clean)
    clean = re.sub(r"__(.*?)__", r"\1", clean)
    clean = clean.replace("**", "").replace("__", "")
    # 9. Colapsar espacios múltiples y limpiar extremos
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _iter_all_components(components: Any):
    """
    Recorre recursivamente cualquier jerarquía de componentes de Discord,
    soportando tanto instancias de discord.py (ActionRow, Container, etc.)
    como diccionarios JSON raw de Discord Components V2.
    """
    if not components:
        return
    for item in components:
        yield item
        sub_items = None
        if isinstance(item, dict):
            raw_sub = item.get("components") or item.get("children")
            if isinstance(raw_sub, (list, tuple)):
                sub_items = raw_sub
        else:
            for attr in ("components", "children"):
                val = getattr(item, attr, None)
                if isinstance(val, (list, tuple)):
                    sub_items = val
                    break
        if sub_items:
            yield from _iter_all_components(sub_items)


def _resolve_message_author(message: Any) -> Any:
    """
    Examina el mensaje para resolver su autor humano real.
    Si message.author es un bot (ej. Economia Asistente al responder a /slots):
    1. Si hasattr(message, 'interaction') y message.interaction tiene atributo 'user':
       el autor real es message.interaction.user.
    2. Si en los embeds o contenido se identifica un usuario iniciador (por mención o guild), lo retorna.
    3. Si en los custom_ids de componentes se identifica un user_id, lo busca en el servidor.
    4. En caso contrario, hace fallback a message.author.
    Si message.author no es bot, retorna message.author directamente.
    """
    author = getattr(message, "author", None)
    if not author:
        return author

    # Comprobar si el autor es un bot
    is_bot = (getattr(author, "bot", False) is True)
    if not is_bot:
        return author

    # 1. Interacción directa de Discord Slash Command / Context Menu
    interaction = getattr(message, "interaction", None)
    if interaction and hasattr(interaction, "user") and interaction.user:
        return interaction.user

    # 2. Búsqueda en embeds (mención en título, descripción o campos)
    embeds = getattr(message, "embeds", []) or []
    import re
    for emb in embeds:
        text_chunks = [getattr(emb, "title", "") or "", getattr(emb, "description", "") or ""]
        for f in getattr(emb, "fields", []) or []:
            text_chunks.append(getattr(f, "name", "") or "")
            text_chunks.append(getattr(f, "value", "") or "")
        combined = " ".join(text_chunks)
        m = re.search(r"<@!?(\d+)>", combined)
        if m:
            uid = int(m.group(1))
            guild = getattr(message, "guild", None)
            if guild and hasattr(guild, "get_member"):
                member = guild.get_member(uid)
                if member:
                    return member

    # 3. Búsqueda en custom_ids de componentes (ej: slots:play-again:100:USER_ID)
    components = getattr(message, "components", []) or []
    for comp in _iter_all_components(components):
        custom_id = getattr(comp, "custom_id", None) or (comp.get("custom_id") if isinstance(comp, dict) else None)
        if custom_id and isinstance(custom_id, str):
            parts = custom_id.split(":")
            if len(parts) >= 4 and parts[0] == "slots" and parts[-1].isdigit():
                uid = int(parts[-1])
                guild = getattr(message, "guild", None)
                if guild and hasattr(guild, "get_member"):
                    member = guild.get_member(uid)
                    if member:
                        return member

    # Fallback canónico
    return author


def _extract_message_text(message: Any) -> str:
    """
    Extrae el texto representativo de un mensaje con soporte exhaustivo para:
    1. message.content si no está vacío.
    2. message.components (Components V2, Containers y TextDisplays).
    3. message.embeds (título, descripción y campos).
    4. Fallbacks contextuales para adjuntos o interactivos sin texto.
    """
    # 1. Contenido textual estándar
    content = getattr(message, "content", None)
    if content and isinstance(content, str) and content.strip():
        return content.strip()

    # 2. Inspección profunda de componentes V2 (TextDisplay / Container)
    components = getattr(message, "components", []) or []
    comp_texts: List[str] = []
    for comp in _iter_all_components(components):
        comp_type = getattr(comp, "type", None)
        if comp_type is None and isinstance(comp, dict):
            comp_type = comp.get("type")
        comp_type_val = getattr(comp_type, "value", comp_type)

        # TextDisplay es tipo 10 o componente con atributo 'content'
        if comp_type_val == 10 or hasattr(comp, "content") or (isinstance(comp, dict) and "content" in comp):
            c = getattr(comp, "content", None)
            if c is None and isinstance(comp, dict):
                c = comp.get("content")
            if isinstance(c, str) and c.strip():
                comp_texts.append(c.strip())

    if comp_texts:
        return "\n\n".join(comp_texts)

    # 3. Inspección de embeds
    embeds = getattr(message, "embeds", []) or []
    embed_texts: List[str] = []
    for emb in embeds:
        title = getattr(emb, "title", None) or (emb.get("title") if isinstance(emb, dict) else None)
        desc = getattr(emb, "description", None) or (emb.get("description") if isinstance(emb, dict) else None)
        if title and isinstance(title, str) and title.strip():
            embed_texts.append(title.strip())
        if desc and isinstance(desc, str) and desc.strip():
            embed_texts.append(desc.strip())
        fields = getattr(emb, "fields", None) or (emb.get("fields") if isinstance(emb, dict) else None)
        if fields:
            for f in fields:
                fname = getattr(f, "name", None) or (f.get("name") if isinstance(f, dict) else None)
                fval = getattr(f, "value", None) or (f.get("value") if isinstance(f, dict) else None)
                if fname and fval:
                    embed_texts.append(f"{fname}: {fval}")
                elif fname:
                    embed_texts.append(str(fname))
                elif fval:
                    embed_texts.append(str(fval))

    if embed_texts:
        return "\n\n".join(embed_texts)

    # 4. Fallback para adjuntos multimedia
    attachments = getattr(message, "attachments", []) or []
    if attachments and len(attachments) > 0:
        return "“(Contenido multimedia o imagen adjunta)”"

    # 5. Fallback final interactivo
    return "“(Mensaje interactivo sin texto)”"


# ==========================================
# MOTOR DE RENDERIZADO PILLOW (THE SANVI DAILY)
# ==========================================

def render_sanvi_daily_cover(
    author_name: str,
    author_avatar_bytes: Optional[bytes],
    content: str,
    created_at_str: str,
    edition_num: int,
    stars_count: int,
    attachment_bytes: Optional[bytes] = None,
) -> bytes:
    """
    Renderiza la portada estilo periódico vintage 'The Sanvi Daily' (800 x 1000 px).
    Devuelve los bytes en formato PNG.
    """
    WIDTH = 800
    HEIGHT = 1000

    img = Image.new("RGB", (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 1. Marco exterior doble de estilo rotativo vintage
    draw.rectangle([14, 14, WIDTH - 14, HEIGHT - 14], outline=BORDER_COLOR, width=3)
    draw.rectangle([19, 19, WIDTH - 19, HEIGHT - 19], outline=BORDER_COLOR, width=1)

    # 2. Cintillo superior con metadatos
    font_top = _get_header_font(13)
    cintillo_left = f"EDICIÓN Nº {edition_num} • ARCHIVO HISTÓRICO COMUNITARIO"
    cintillo_right_prefix = f"FECHA: {created_at_str} • PRECIO: 2 "
    draw.text((28, 25), cintillo_left, fill=INK_MUTED, font=font_top)

    try:
        prefix_w = font_top.getlength(cintillo_right_prefix)
    except Exception:
        prefix_w = 230
    total_right_w = prefix_w + 16
    start_rx = WIDTH - 28 - total_right_w
    draw.text((start_rx, 25), cintillo_right_prefix, fill=INK_MUTED, font=font_top)
    # Estrella vectorial limpia (sin glifos tofu de fuentes)
    _draw_star_polygon(draw, start_rx + prefix_w + 7, 31, r_out=6, r_in=2.6, fill=INK_MUTED)

    # Filete separador superior
    draw.line([(24, 44), (WIDTH - 24, 44)], fill=BORDER_COLOR, width=2)

    # 3. Gran Cabecera: THE SANVI DAILY
    font_title = _get_title_font(60)
    title_text = "THE SANVI DAILY"
    try:
        title_w = font_title.getlength(title_text)
    except Exception:
        title_w = 480
    draw.text(((WIDTH - title_w) / 2, 48), title_text, fill=INK_MAIN, font=font_title)

    # 4. Lema y filetes dobles de cabecera
    font_motto = _get_body_font(15, bold=False)
    motto_text = "«La verdad duele, pero las capturas duelen más» — Edición Histórica Comunitaria"
    try:
        motto_w = font_motto.getlength(motto_text)
    except Exception:
        motto_w = 420

    draw.line([(24, 118), (WIDTH - 24, 118)], fill=BORDER_COLOR, width=1)
    draw.text(((WIDTH - motto_w) / 2, 122), motto_text, fill=INK_MUTED, font=font_motto)
    draw.line([(24, 142), (WIDTH - 24, 142)], fill=BORDER_COLOR, width=3)
    draw.line([(24, 147), (WIDTH - 24, 147)], fill=BORDER_COLOR, width=1)

    # 5. Sección Titular y Avatar
    current_y = 158

    # Avatar del autor
    avatar_size = 96
    avatar_x = 32
    avatar_y = current_y

    if author_avatar_bytes:
        try:
            av_img = Image.open(io.BytesIO(author_avatar_bytes)).convert("RGBA")
            av_img = av_img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            # Máscara circular con borde sepia
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            img.paste(av_img, (avatar_x, avatar_y), mask)
            # Borde circular
            draw.ellipse(
                (avatar_x - 2, avatar_y - 2, avatar_x + avatar_size + 2, avatar_y + avatar_size + 2),
                outline=BORDER_COLOR,
                width=2,
            )
        except Exception as e:
            _log(f"Aviso procesando avatar: {e}")
            draw.rectangle(
                [avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size],
                outline=BORDER_COLOR,
                width=2,
            )
    else:
        draw.rectangle(
            [avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size],
            outline=BORDER_COLOR,
            width=2,
        )

    # Titular principal
    header_x = avatar_x + avatar_size + 20

    font_headline = _get_body_font(26, bold=True)
    headline_clean = f"DECLARACIÓN CÉLEBRE DE {author_name.upper()}"
    headline_lines = textwrap.wrap(headline_clean, width=30)
    
    h_y = avatar_y + 4
    for hline in headline_lines[:2]:
        draw.text((header_x, h_y), hline, fill=INK_MAIN, font=font_headline)
        h_y += 32

    font_subhead = _get_body_font(16, bold=False)
    subhead_text = "Testimonio verificado en directo por los ciudadanos del servidor"
    draw.text((header_x, h_y + 4), subhead_text, fill=INK_MUTED, font=font_subhead)

    # Separador horizontal del titular
    current_y = max(avatar_y + avatar_size + 16, h_y + 36)
    draw.line([(28, current_y), (WIDTH - 28, current_y)], fill=BORDER_COLOR, width=1)
    current_y += 18

    # 6. Cuerpo de la Noticia (Caja de Texto con comillas y ajuste)
    raw_cleaned = _clean_discord_text(content)
    clean_content = raw_cleaned if raw_cleaned else "(Mensaje sin texto adjunto o exclusivamente multimedia)"
    
    # Adaptación tipográfica: frases cortas reciben fuente más destacada
    is_short = len(clean_content) < 220 and not attachment_bytes
    quote_font_size = 26 if is_short else 22
    font_quote = _get_body_font(quote_font_size, bold=False)
    line_spacing = 36 if is_short else 28
    char_width = 46 if is_short else 54

    max_quote_lines = 7 if attachment_bytes else 16
    wrapped_lines = textwrap.wrap(clean_content, width=char_width)

    # Añadir comillas tipográficas
    if wrapped_lines:
        if not wrapped_lines[0].startswith("“"):
            wrapped_lines[0] = f"“ {wrapped_lines[0]}"
        if not wrapped_lines[-1].endswith("”"):
            if len(wrapped_lines) <= max_quote_lines:
                wrapped_lines[-1] = f"{wrapped_lines[-1]} ”"
            else:
                wrapped_lines = wrapped_lines[:max_quote_lines]
                wrapped_lines[-1] = f"{wrapped_lines[-1]}... ”"
    else:
        wrapped_lines = ["“ (Sin texto) ”"]

    for line in wrapped_lines:
        draw.text((44, current_y), line, fill=INK_MAIN, font=font_quote)
        current_y += line_spacing

    current_y += 20

    # 7. Imagen Adjunta (si existe) procesada en estilo sepia vintage
    if attachment_bytes:
        try:
            att_img = Image.open(io.BytesIO(attachment_bytes))
            att_img = att_img.convert("RGB")
            
            # Espacio disponible para la foto
            max_img_w = WIDTH - 64  # 736 px
            max_img_h = max(200, (HEIGHT - 120) - current_y - 80)
            
            # Escalar manteniendo aspect ratio
            att_img.thumbnail((max_img_w, max_img_h), Image.Resampling.LANCZOS)
            
            # Filtro sepia suave
            gray = ImageOps.grayscale(att_img)
            sepia_img = ImageOps.colorize(gray, black="#2C1D11", white="#FFF3D6")
            
            # Centrar imagen
            img_x = (WIDTH - sepia_img.width) // 2
            img_y = current_y
            
            # Marco doble alrededor de la foto
            draw.rectangle(
                [img_x - 4, img_y - 4, img_x + sepia_img.width + 3, img_y + sepia_img.height + 3],
                outline=BORDER_COLOR,
                width=2,
            )
            img.paste(sepia_img, (img_x, img_y))
            
            # Pie de foto
            font_caption = _get_body_font(14, bold=False)
            caption_text = "[ Fotografía exclusiva adjunta al testimonio original ]"
            try:
                cap_w = font_caption.getlength(caption_text)
            except Exception:
                cap_w = 260
            draw.text(((WIDTH - cap_w) / 2, img_y + sepia_img.height + 8), caption_text, fill=INK_MUTED, font=font_caption)
            
            current_y = img_y + sepia_img.height + 32
        except Exception as e:
            _log(f"Aviso incrustando imagen adjunta: {e}")
    else:
        # Ornamento gráfico vintage decorativo si el texto es corto para equilibrar la composición
        if is_short:
            ornament_y = (current_y + (HEIGHT - 110)) // 2
            draw.line([(WIDTH // 4, ornament_y), (3 * WIDTH // 4, ornament_y)], fill=BORDER_COLOR, width=1)
            # Dibujar 3 rombos vectoriales perfectos en el centro
            cx = WIDTH // 2
            spacing = 24
            # Rectángulo para limpiar la línea central
            draw.rectangle([cx - spacing - 14, ornament_y - 8, cx + spacing + 14, ornament_y + 8], fill=BG_COLOR)
            _draw_diamond_polygon(draw, cx - spacing, ornament_y, size=5, fill=INK_MUTED)
            _draw_diamond_polygon(draw, cx, ornament_y, size=7, fill=INK_MUTED)
            _draw_diamond_polygon(draw, cx + spacing, ornament_y, size=5, fill=INK_MUTED)

    # 8. Pie de Rotativo y Sello de Autenticidad
    footer_y = HEIGHT - 80
    draw.line([(24, footer_y), (WIDTH - 24, footer_y)], fill=BORDER_COLOR, width=2)

    # Texto legal / de archivo
    font_footer = _get_header_font(13)
    draw.text((32, footer_y + 12), "ARCHIVO OFICIAL DE LOS MONGOLOS DEL SANVI", fill=INK_MAIN, font=font_footer)
    draw.text((32, footer_y + 32), "Inmortalizado de forma permanente por votación popular comunitaria.", fill=INK_MUTED, font=_get_header_font(12))

    # Sello de cera / tampón vintage a la derecha
    stamp_w, stamp_h = 220, 48
    stamp_x = WIDTH - stamp_w - 32
    stamp_y = footer_y + 10
    draw.rectangle([stamp_x, stamp_y, stamp_x + stamp_w, stamp_y + stamp_h], outline=STAMP_COLOR, width=2)
    draw.rectangle([stamp_x + 3, stamp_y + 3, stamp_x + stamp_w - 3, stamp_y + stamp_h - 3], outline=STAMP_COLOR, width=1)

    stamp_font_top = _get_header_font(14)
    stamp_text_stars = f"{stars_count} ESTRELLAS"
    stamp_text_2 = "APROBADO POR EL PUEBLO"
    try:
        s1_w = stamp_font_top.getlength(stamp_text_stars)
        s2_w = stamp_font_top.getlength(stamp_text_2)
    except Exception:
        s1_w, s2_w = 90, 160

    # Estrella roja vectorial integrada en el sello
    star_spacing = 20
    total_stamp_w = s1_w + star_spacing
    s1_start_x = stamp_x + (stamp_w - total_stamp_w) / 2

    _draw_star_polygon(draw, s1_start_x + 6, stamp_y + 15, r_out=7, r_in=3, fill=STAMP_COLOR)
    draw.text((s1_start_x + star_spacing, stamp_y + 6), stamp_text_stars, fill=STAMP_COLOR, font=stamp_font_top)
    draw.text((stamp_x + (stamp_w - s2_w) / 2, stamp_y + 26), stamp_text_2, fill=STAMP_COLOR, font=_get_header_font(11))

    # Guardar en buffer de memoria PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ==========================================
# MANEJADORES DE EVENTOS REACTIVOS (DISCORD)
# ==========================================

async def handle_starboard_reaction_add(payload: discord.RawReactionActionEvent, bot: discord.Client) -> None:
    """
    Procesa la adición de una reacción. Si es ⭐ y el mensaje no pertenece a un canal
    excluido, computa las estrellas de usuarios (excluyendo al autor) y publica o actualiza
    la portada en #⭐muro-de-la-fama⭐.
    """
    # 1. Validar emoji y exclusión de canales
    if str(payload.emoji) != STAR_EMOJI:
        return

    if payload.channel_id in EXCLUDED_CHANNEL_IDS:
        return

    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(payload.channel_id)
        except Exception as e:
            _log(f"No se pudo obtener el canal {payload.channel_id}: {e}")
            return

    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception as e:
        _log(f"No se pudo obtener el mensaje {payload.message_id} en #{getattr(channel, 'name', payload.channel_id)}: {e}")
        return

    # 2. Cómputo estricto anti-autobombo: excluir al autor del mensaje
    star_reaction = None
    for r in message.reactions:
        if str(r.emoji) == STAR_EMOJI:
            star_reaction = r
            break

    if not star_reaction:
        return

    try:
        reaction_users = [u async for u in star_reaction.users()]
    except Exception as e:
        _log(f"Error leyendo usuarios de la reacción ⭐: {e}")
        return

    real_author = _resolve_message_author(message)
    excluded_author_ids = {message.author.id}
    if real_author and hasattr(real_author, "id"):
        excluded_author_ids.add(real_author.id)

    valid_stargazers = [u for u in reaction_users if u.id not in excluded_author_ids]
    stars_count = len(valid_stargazers)

    entry_key = f"{message.channel.id}_{message.id}"

    async with STARBOARD_LOCK:
        data = load_starboard_data()
        entries = data.get("entries", {})
        existing_entry = entries.get(entry_key)

        # Caso A: Ya existe en el muro -> Editar mensaje existente si cambiaron las estrellas
        if existing_entry:
            old_count = existing_entry.get("stars_count", 0)
            if old_count != stars_count:
                existing_entry["stars_count"] = stars_count
                existing_entry["stargazers"] = [u.id for u in valid_stargazers]
                save_starboard_data(data)

                # Intentar editar el mensaje publicado en el Starboard
                sb_channel = bot.get_channel(STARBOARD_CHANNEL_ID)
                if not sb_channel:
                    try:
                        sb_channel = await bot.fetch_channel(STARBOARD_CHANNEL_ID)
                    except Exception:
                        sb_channel = None

                if sb_channel:
                    try:
                        sb_msg = await sb_channel.fetch_message(existing_entry["starboard_message_id"])
                        if sb_msg and sb_msg.embeds:
                            embed = sb_msg.embeds[0]
                            edition = existing_entry.get("edition_number", 1)
                            embed.set_footer(text=f"Edición Nº {edition} • Inmortalizado con {stars_count} ⭐")
                            await sb_msg.edit(embed=embed)
                            _log(f"Contador de estrellas actualizado a {stars_count} ⭐ en edición #{edition}.")
                    except Exception as e_edit:
                        _log(f"Aviso actualizando mensaje de Starboard: {e_edit}")
            return

        # Caso B: No existe aún -> Comprobar si alcanza el umbral mínimo (>= 2 estrellas)
        if stars_count < MIN_STARS_THRESHOLD:
            return

        # Alcanzó el umbral de publicación: Imprimir nueva edición de The Sanvi Daily
        edition = data.get("next_edition_number", 1)
        data["next_edition_number"] = edition + 1

        _log(f"🌟 ¡Mensaje {message.id} alcanzó {stars_count} ⭐! Imprimiendo Edición Nº {edition}...")

        # Descargar avatar del autor real
        target_author = real_author or message.author
        author_avatar_bytes: Optional[bytes] = None
        try:
            if hasattr(target_author, "display_avatar") and target_author.display_avatar:
                author_avatar_bytes = await target_author.display_avatar.read()
        except Exception as e_av:
            _log(f"Aviso descargando avatar del autor: {e_av}")

        # Comprobar si el mensaje original contenía un archivo adjunto de imagen
        attachment_bytes: Optional[bytes] = None
        for att in message.attachments:
            c_type = (att.content_type or "").lower()
            fname = att.filename.lower()
            if c_type.startswith("image/") or fname.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                try:
                    attachment_bytes = await att.read()
                    break
                except Exception as e_att:
                    _log(f"Aviso descargando adjunto {att.filename}: {e_att}")

        # Extraer texto representativo del mensaje (content, components V2, embeds o fallbacks)
        extracted_content = _extract_message_text(message)

        # Renderizar la portada con Pillow
        created_at_str = message.created_at.strftime("%d/%m/%Y %H:%M UTC")
        author_name = getattr(target_author, "display_name", getattr(target_author, "name", "Ciudadano"))
        img_bytes = render_sanvi_daily_cover(
            author_name=author_name,
            author_avatar_bytes=author_avatar_bytes,
            content=extracted_content,
            created_at_str=created_at_str,
            edition_num=edition,
            stars_count=stars_count,
            attachment_bytes=attachment_bytes,
        )

        # Construir Embed Dorado Canónico (0xF59E0B)
        embed = discord.Embed(
            title=f"⭐ #{edition} | The Sanvi Daily",
            description=f"Mensaje célebre de <@{target_author.id}> en <#{message.channel.id}>",
            color=0xF59E0B,
            timestamp=message.created_at,
        )
        embed.set_footer(text=f"Edición Nº {edition} • Inmortalizado con {stars_count} ⭐")

        # Botón de salto interactivo
        view = View()
        view.add_item(Button(label="Ir al Mensaje", url=message.jump_url, emoji="🔗"))

        # Adjuntar la portada renderizada
        filename = f"sanvi_daily_{edition}.png"
        file = discord.File(io.BytesIO(img_bytes), filename=filename)
        embed.set_image(url=f"attachment://{filename}")

        # Enviar al canal oficial #⭐muro-de-la-fama⭐
        sb_channel = bot.get_channel(STARBOARD_CHANNEL_ID)
        if not sb_channel:
            try:
                sb_channel = await bot.fetch_channel(STARBOARD_CHANNEL_ID)
            except Exception as e_ch:
                _log(f"Error obteniendo canal de Starboard {STARBOARD_CHANNEL_ID}: {e_ch}")
                return

        try:
            sent_msg = await sb_channel.send(embed=embed, file=file, view=view)
            
            # Registrar en persistencia
            entries[entry_key] = {
                "edition_number": edition,
                "orig_channel_id": message.channel.id,
                "orig_message_id": message.id,
                "starboard_message_id": sent_msg.id,
                "author_id": target_author.id,
                "author_name": getattr(target_author, "name", str(target_author)),
                "stars_count": stars_count,
                "stargazers": [u.id for u in valid_stargazers],
                "created_at": message.created_at.isoformat(),
                "has_image": attachment_bytes is not None,
            }
            save_starboard_data(data)
            _log(f"✅ Edición Nº {edition} publicada en #{sb_channel.name} ({sent_msg.id}).")
        except Exception as e_send:
            _log(f"Error enviando mensaje al Starboard: {e_send}")


async def handle_starboard_reaction_remove(payload: discord.RawReactionActionEvent, bot: discord.Client) -> None:
    """
    Procesa la retirada de una reacción ⭐.
    PERMANENCIA IRREVOCABLE CANÓNICA: La portada jamás se elimina aunque el mensaje baje de 2 estrellas.
    Solo se actualiza el contador de estrellas si procede.
    """
    if str(payload.emoji) != STAR_EMOJI:
        return

    if payload.channel_id in EXCLUDED_CHANNEL_IDS:
        return

    entry_key = f"{payload.channel_id}_{payload.message_id}"

    async with STARBOARD_LOCK:
        data = load_starboard_data()
        entries = data.get("entries", {})
        existing_entry = entries.get(entry_key)

        # Si el mensaje nunca llegó al starboard, nada que hacer
        if not existing_entry:
            return

        channel = bot.get_channel(payload.channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(payload.channel_id)
            except Exception:
                return

        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return

        # Recalcular estrellas válidas excluyendo al autor
        star_reaction = None
        for r in message.reactions:
            if str(r.emoji) == STAR_EMOJI:
                star_reaction = r
                break

        real_author = _resolve_message_author(message)
        excluded_author_ids = {message.author.id}
        if real_author and hasattr(real_author, "id"):
            excluded_author_ids.add(real_author.id)

        valid_stargazers = []
        if star_reaction:
            try:
                reaction_users = [u async for u in star_reaction.users()]
                valid_stargazers = [u for u in reaction_users if u.id not in excluded_author_ids]
            except Exception:
                pass

        new_count = len(valid_stargazers)
        old_count = existing_entry.get("stars_count", 0)

        if new_count != old_count:
            existing_entry["stars_count"] = new_count
            existing_entry["stargazers"] = [u.id for u in valid_stargazers]
            save_starboard_data(data)

            # Actualizar embed en Discord manteniendo la portada
            sb_channel = bot.get_channel(STARBOARD_CHANNEL_ID)
            if not sb_channel:
                try:
                    sb_channel = await bot.fetch_channel(STARBOARD_CHANNEL_ID)
                except Exception:
                    sb_channel = None

            if sb_channel:
                try:
                    sb_msg = await sb_channel.fetch_message(existing_entry["starboard_message_id"])
                    if sb_msg and sb_msg.embeds:
                        embed = sb_msg.embeds[0]
                        edition = existing_entry.get("edition_number", 1)
                        embed.set_footer(text=f"Edición Nº {edition} • Inmortalizado con {new_count} ⭐")
                        await sb_msg.edit(embed=embed)
                        _log(f"Contador actualizado tras retirada de estrella: {new_count} ⭐ en edición #{edition}.")
                except Exception as e_edit:
                    _log(f"Aviso actualizando tras retirada de estrella: {e_edit}")
