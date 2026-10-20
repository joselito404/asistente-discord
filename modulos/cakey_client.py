"""
Cliente del Leaderboard Web de Cakey Bot para 'Asistente' en Discord.
Fuente de Verdad canónica de niveles, XP acumulada, mensajes y minutos de voz:
https://cakey.bot/leaderboard/id/1446143936891715616?tab=leveling
Especificación: docs/AURA_BAREMO.md (§3.1)
"""

import re
import sys
import time
import asyncio
from typing import Dict, Any, Optional, Union
import aiohttp
import discord

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

GUILD_ID: int = 1446143936891715616
CAKEY_LEADERBOARD_URL: str = f"https://cakey.bot/leaderboard/id/{GUILD_ID}?tab=leveling"

_CACHE: Dict[int, Dict[str, Any]] = {}
_CACHE_TIME: float = 0.0
TTL: float = 300.0  # 5 minutos de retención en memoria
_LOCK = asyncio.Lock()


def _log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] [CakeyClient] {msg}")


def parse_xp_value(xp_raw: str) -> float:
    """Convierte cadenas como '340.6k XP', '1.2M XP' o '2000' en valor numérico flotante."""
    if not xp_raw:
        return 0.0
    clean = xp_raw.replace("XP", "").strip().replace(",", "")
    match = re.match(r"^([\d\.]+)\s*([kKmM]?)$", clean)
    if not match:
        # Intentar extraer dígitos
        digits = re.findall(r"[\d\.]+", clean)
        return float(digits[0]) if digits else 0.0
    val_str, unit = match.groups()
    try:
        val = float(val_str)
        unit = unit.lower()
        if unit == "k":
            return val * 1000.0
        elif unit == "m":
            return val * 1000000.0
        return val
    except ValueError:
        return 0.0


def parse_cakey_leaderboard_html(html: str) -> Dict[int, Dict[str, Any]]:
    """
    Parsea el HTML del leaderboard de Cakey Bot extrayendo los miembros.
    Retorna un diccionario indexado por user_id (int) con la estructura:
    {
        user_id: {
            "rank": int,
            "username": str,
            "user_id": int,
            "messages": int,
            "voice_minutes": int,
            "level": int,
            "xp": float,
            "xp_str": str
        }
    }
    """
    if not html:
        return {}

    results: Dict[int, Dict[str, Any]] = {}
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
    
    fallback_rank = 1
    for row in rows:
        # Ignorar filas de encabezado <th>
        if "<th" in row.lower():
            continue

        # 1. Rango / Posición (#)
        rank = fallback_rank
        # Posición 1, 2, 3 suele venir como <img src="/assets/images/1.svg" alt="Star" ...>
        svg_match = re.search(r"/assets/images/(\d+)\.svg", row, re.IGNORECASE)
        h4_match = re.search(r"<h4[^>]*>\s*(\d+)\s*</h4>", row, re.IGNORECASE)
        if svg_match:
            try:
                rank = int(svg_match.group(1))
            except ValueError:
                rank = fallback_rank
        elif h4_match:
            try:
                rank = int(h4_match.group(1))
            except ValueError:
                rank = fallback_rank

        # 2. User ID y Avatar
        # Discord CDN pattern: https://cdn.discordapp.com/avatars/<user_id>/<hash>.png
        uid_match = re.search(r"avatars/(\d+)/[a-zA-Z0-9_\-]+", row)
        user_id = int(uid_match.group(1)) if uid_match else 0

        # 3. Username
        name_match = re.search(r'<span class=[\'"][^\'"]*text-theme\s+font-medium[^\'"]*[\'"]>([^<]+)</span>', row)
        if not name_match:
            name_match = re.search(r'alt=[\'"]([^\'"]+)[\'"]\s+class=[\'"][^\'"]*rounded-full', row)
        username = name_match.group(1).strip() if name_match else ""

        # 4. Celdas de columnas (td)
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
        # Columnas estándar: [0: Rank, 1: User, 2: XP Messages, 3: XP Voice Minutes, 4: Progress]
        messages = 0
        voice_minutes = 0
        if len(tds) >= 4:
            # XP Messages (columna 2)
            msg_digits = re.sub(r"[^\d]", "", tds[2])
            messages = int(msg_digits) if msg_digits else 0
            # XP Voice Minutes (columna 3)
            voice_digits = re.sub(r"[^\d]", "", tds[3])
            voice_minutes = int(voice_digits) if voice_digits else 0

        # 5. Nivel (Level <span ...>54</span>)
        level = 0
        lvl_match = re.search(r"Level\s*<span[^>]*>\s*(\d+)\s*</span>", row, re.IGNORECASE)
        if lvl_match:
            try:
                level = int(lvl_match.group(1))
            except ValueError:
                level = 0

        # 6. XP Total (<span ...>340.6k XP</span>)
        xp_str = ""
        xp_val = 0.0
        xp_match = re.search(r"([\d\.]+\s*[kKmM]?\s*XP)", row, re.IGNORECASE)
        if xp_match:
            xp_str = xp_match.group(1).strip()
            xp_val = parse_xp_value(xp_str)

        # Si tenemos al menos un user_id o username
        if user_id > 0:
            results[user_id] = {
                "rank": rank,
                "username": username,
                "user_id": user_id,
                "messages": messages,
                "voice_minutes": voice_minutes,
                "level": level,
                "xp": xp_val,
                "xp_str": xp_str,
            }
        elif username:
            # Clave sintética si no hay ID extraíble
            results[hash(username)] = {
                "rank": rank,
                "username": username,
                "user_id": 0,
                "messages": messages,
                "voice_minutes": voice_minutes,
                "level": level,
                "xp": xp_val,
                "xp_str": xp_str,
            }

        fallback_rank += 1

    return results


async def fetch_cakey_leaderboard_html(url: str = CAKEY_LEADERBOARD_URL, timeout_sec: float = 10.0) -> str:
    """Descarga el HTML crudo del leaderboard público de Cakey Bot."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }
    timeout = aiohttp.ClientTimeout(total=timeout_sec)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status} en {url}")
            return await response.text()


async def get_cakey_leaderboard(force_refresh: bool = False) -> Dict[int, Dict[str, Any]]:
    """
    Obtiene el leaderboard completo de Cakey Bot con caché en memoria y concurrencia protegida.
    Fallback a la última caché válida si la petición remota falla.
    """
    global _CACHE, _CACHE_TIME
    now = time.time()

    # Fast-path sin lock si la caché sigue vigente
    if not force_refresh and _CACHE_TIME > 0 and (now - _CACHE_TIME < TTL) and _CACHE:
        return dict(_CACHE)

    async with _LOCK:
        now = time.time()
        if not force_refresh and _CACHE_TIME > 0 and (now - _CACHE_TIME < TTL) and _CACHE:
            return dict(_CACHE)

        try:
            html = await fetch_cakey_leaderboard_html(CAKEY_LEADERBOARD_URL)
            parsed = parse_cakey_leaderboard_html(html)
            if parsed:
                _CACHE = parsed
                _CACHE_TIME = now
                _log(f"Leaderboard actualizado con éxito ({len(parsed)} miembros extraídos).")
                return dict(_CACHE)
            else:
                _log("Aviso: el HTML de Cakey no contenía filas de miembros válidas.")
        except Exception as e:
            _log(f"Error consultando leaderboard de Cakey Bot: {e}")

        # Fallback a caché previa si existe
        if _CACHE:
            return dict(_CACHE)
        return {}


async def get_user_cakey_data(guild: Optional[discord.Guild], user: Union[discord.Member, discord.User, int, str]) -> Dict[str, Any]:
    """
    Busca los datos de Cakey de un miembro por ID numérico, mención, username o global_name.
    Retorna un diccionario con rank, level, xp, messages, voice_minutes, etc., o {} si no existe.
    """
    leaderboard = await get_cakey_leaderboard()
    if not leaderboard:
        return {}

    # 1. Búsqueda directa por ID
    target_id: Optional[int] = None
    if isinstance(user, int):
        target_id = user
    elif isinstance(user, (discord.Member, discord.User)):
        target_id = user.id
    elif isinstance(user, str) and user.isdigit():
        target_id = int(user)

    if target_id and target_id in leaderboard:
        return dict(leaderboard[target_id])

    # 2. Búsqueda por nombres (username, global_name, display_name)
    names_to_check = []
    if isinstance(user, (discord.Member, discord.User)):
        names_to_check.append(user.name.lower())
        if getattr(user, "global_name", None):
            names_to_check.append(user.global_name.lower())
        if getattr(user, "display_name", None):
            names_to_check.append(user.display_name.lower())
    elif isinstance(user, str):
        cleaned = user.lstrip("@").lower().strip()
        names_to_check.append(cleaned)

    for item in leaderboard.values():
        u_name = item.get("username", "").lower()
        if u_name in names_to_check:
            return dict(item)

    return {}
