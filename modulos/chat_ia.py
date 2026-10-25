"""
Módulo de Inteligencia Artificial Conversacional y Generación de Texto para el Bot 'Asistente':
- Clientes y orquestador multi-modelo de Gemini con Circuit Breaker inteligente (fallback automático).
- System Prompt maestro con directrices de personalidad, lore del servidor y políticas estrictas.
- Monitor en tiempo real de niveles reales de Cakey Bot (#bots) con caché segura y calculadora cuadrática de XP.
- Búsqueda web contextual en vivo y lector de páginas web / documentos / adjuntos multimodales.
- Radars de canales de voz, censos en vivo de miembros, fichas técnicas y memoria persistente de usuarios.
- Enrutador conversacional seguro de mensajes (_handle_message_safe) con intercepción de acciones visuales y locución de voz.
"""

import os
import sys
import json
import time
import asyncio
import re
import base64
import html
import urllib.request
import urllib.parse
import urllib.error
import socket
import unicodedata
import io
import discord
from typing import Any, Optional, Union
from datetime import datetime, timezone, timedelta


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


def _bot_log(msg: str):
    bs = _bs()
    log_fn = getattr(bs, "bot_log", print)
    log_fn(msg)


def _get_bot():
    bs = _bs()
    return getattr(bs, "bot", None)


def _get_gemini_key():
    bs = _bs()
    return getattr(bs, "GEMINI_KEY", os.getenv("GEMINI_API_KEY", ""))


def _get_base_dir():
    bs = _bs()
    return getattr(bs, "BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_spain_now_str() -> str:
    """Devuelve la fecha y hora actual en España peninsular formateada en español."""
    now_utc = datetime.now(timezone.utc)
    m = now_utc.month
    # Horario peninsular español (CEST UTC+2 en verano, CET UTC+1 en invierno)
    offset_h = 2 if (4 <= m <= 9 or (m == 3 and now_utc.day >= 25) or (m == 10 and now_utc.day < 25)) else 1
    spain_time = now_utc + timedelta(hours=offset_h)
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    dia_sem = dias[spain_time.weekday()]
    mes = meses[spain_time.month - 1]
    return f"{dia_sem}, {spain_time.day} de {mes} de {spain_time.year} - {spain_time.strftime('%H:%M')} (Hora de España)"


# ==========================================
# GESTIÓN DE MODELOS Y CIRCUIT BREAKER
# ==========================================

MODELS_PRIORITY = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
]
model_cooldowns = {}


def get_available_models():
    """Devuelve los modelos disponibles que no están en cooldown por error 429/503."""
    bs = _bs()
    cooldowns_dict = getattr(bs, "model_cooldowns", model_cooldowns)
    priority_list = getattr(bs, "MODELS_PRIORITY", MODELS_PRIORITY)
    now = time.time()
    available = [m for m in priority_list if now >= cooldowns_dict.get(m, 0)]
    return available if available else priority_list


def mark_model_cooldown(model_name: str, duration_sec: int = 60):
    """Aplica cooldown temporal a un modelo saturado para conmutar sin latencia."""
    bs = _bs()
    cooldowns_dict = getattr(bs, "model_cooldowns", model_cooldowns)
    cooldowns_dict[model_name] = time.time() + duration_sec
    _bot_log(f"⚡ [Circuit Breaker] Modelo '{model_name}' en cooldown por {duration_sec}s.")


# ==========================================
# CATÁLOGO DE EMOJIS DEL SERVIDOR Y CONVERSOR
# ==========================================

# Diccionario canónico de los 124 emojis del servidor (98 estáticos, 26 animados)
SERVER_EMOJIS_DATA = {
    "sigmajawline": {"name": "sigmajawline", "id": 1476986259883950121, "animated": False, "is_safe": True, "rank": 1},
    "dislike": {"name": "Dislike", "id": 1476986782053568604, "animated": False, "is_safe": True, "rank": 2},
    "smash": {"name": "smash", "id": 1476989162715349053, "animated": False, "is_safe": True, "rank": 3},
    "pensando": {"name": "pensando", "id": 1476989472502452255, "animated": False, "is_safe": True, "rank": 4},
    "absolutecinema": {"name": "absolutecinema", "id": 1478115607336714300, "animated": False, "is_safe": True, "rank": 5},
    "67": {"name": "67", "id": 1480177258931949659, "animated": False, "is_safe": True, "rank": 6},
    "sanchez_view": {"name": "sanchez_view", "id": 1484579256758567023, "animated": False, "is_safe": True, "rank": 7},
    "facherita": {"name": "facherita", "id": 1484580141618303021, "animated": False, "is_safe": True, "rank": 8},
    "pepecry": {"name": "pepeCRY", "id": 1530995788182847649, "animated": False, "is_safe": True, "rank": 9},
    "pepecringe": {"name": "pepeCringe", "id": 1530996221810966690, "animated": False, "is_safe": True, "rank": 10},
    "goodgame": {"name": "GoodGame", "id": 1530996598195097640, "animated": False, "is_safe": True, "rank": 11},
    "blob_off": {"name": "blob_off", "id": 1530996740298375410, "animated": False, "is_safe": True, "rank": 12},
    "amongus_ass": {"name": "amongus_ass", "id": 1530996947098271965, "animated": False, "is_safe": True, "rank": 13},
    "diamante": {"name": "Diamante", "id": 1530997108520255753, "animated": False, "is_safe": True, "rank": 14},
    "catpointandlaugh": {"name": "catpointandlaugh", "id": 1530997580350357565, "animated": False, "is_safe": True, "rank": 15},
    "goofy_ah_cat": {"name": "goofy_ah_cat", "id": 1530997748340363399, "animated": False, "is_safe": True, "rank": 16},
    "nerd": {"name": "nerd", "id": 1531000077462540440, "animated": False, "is_safe": True, "rank": 17},
    "patrick": {"name": "patrick", "id": 1531000481776799888, "animated": False, "is_safe": True, "rank": 18},
    "side_eye": {"name": "side_eye", "id": 1531001406733947001, "animated": False, "is_safe": True, "rank": 19},
    "bros": {"name": "bros", "id": 1531001502066413678, "animated": False, "is_safe": True, "rank": 20},
    "dead_stare": {"name": "dead_stare", "id": 1531001721915183244, "animated": False, "is_safe": True, "rank": 21},
    "nazi": {"name": "Nazi", "id": 1531002011682607301, "animated": False, "is_safe": True, "rank": 22},
    "franco": {"name": "franco", "id": 1531002139562872912, "animated": False, "is_safe": True, "rank": 23},
    "spain_empire": {"name": "Spain_empire", "id": 1531002554656358584, "animated": False, "is_safe": True, "rank": 24},
    "gay": {"name": "GAY", "id": 1531003064272814142, "animated": False, "is_safe": True, "rank": 25},
    "sonimcrine": {"name": "sonimcrine", "id": 1535676442636189817, "animated": False, "is_safe": True, "rank": 26},
    "sayswear": {"name": "SaySwear", "id": 1535676796362825839, "animated": False, "is_safe": True, "rank": 27},
    "sybauspeed": {"name": "sybauspeed", "id": 1535677246734598275, "animated": False, "is_safe": True, "rank": 28},
    "sigma_male_bale": {"name": "Sigma_Male_Bale", "id": 1535677801808535702, "animated": False, "is_safe": True, "rank": 29},
    "pepecuerda": {"name": "pepecuerda", "id": 1535680479330701433, "animated": False, "is_safe": True, "rank": 30},
    "95_crythumbsup": {"name": "95_CryThumbsUp", "id": 1535681917473656882, "animated": False, "is_safe": True, "rank": 31},
    "bonk": {"name": "bonk", "id": 1535681979843092620, "animated": False, "is_safe": True, "rank": 32},
    "gigachad": {"name": "gigachad", "id": 1535682070536519730, "animated": False, "is_safe": True, "rank": 33},
    "trolled": {"name": "Trolled", "id": 1535682153818357802, "animated": False, "is_safe": True, "rank": 34},
    "dwayneeyebrow": {"name": "DwayneEyebrow", "id": 1535682237817823362, "animated": False, "is_safe": True, "rank": 35},
    "bruh": {"name": "bruh", "id": 1535682294139060235, "animated": False, "is_safe": True, "rank": 36},
    "emojigg_omg": {"name": "emojigg_OMG", "id": 1535682384450691153, "animated": False, "is_safe": True, "rank": 37},
    "what_in_the_hell": {"name": "what_in_the_hell", "id": 1535682520698585180, "animated": False, "is_safe": True, "rank": 38},
    "uno_reverse": {"name": "uno_reverse", "id": 1535682567968129095, "animated": False, "is_safe": True, "rank": 39},
    "cat_sus": {"name": "Cat_Sus", "id": 1535682639544197212, "animated": False, "is_safe": True, "rank": 40},
    "shrug": {"name": "shrug", "id": 1535682710306029638, "animated": False, "is_safe": True, "rank": 41},
    "cryingman": {"name": "CryingMan", "id": 1535682791755481141, "animated": False, "is_safe": True, "rank": 42},
    "pixel_rip_tombstone": {"name": "pixel_rip_tombstone", "id": 1535682950056906752, "animated": False, "is_safe": True, "rank": 43},
    "knowledge": {"name": "knowledge", "id": 1535683001533337640, "animated": False, "is_safe": True, "rank": 44},
    "doomed": {"name": "doomed", "id": 1535683080294236220, "animated": False, "is_safe": True, "rank": 45},
    "wahhhhh": {"name": "wahhhhh", "id": 1535683162628169760, "animated": False, "is_safe": True, "rank": 46},
    "my_honest_reaction": {"name": "my_honest_reaction", "id": 1535683205879832767, "animated": False, "is_safe": True, "rank": 47},
    "heartache": {"name": "Heartache", "id": 1535683279334805635, "animated": False, "is_safe": True, "rank": 48},
    "mrincredible": {"name": "MrIncredible", "id": 1535683403158921338, "animated": False, "is_safe": True, "rank": 49},
    "yb_angry2": {"name": "yb_angry2", "id": 1535683502937350145, "animated": False, "is_safe": True, "rank": 50},
    "doakes": {"name": "Doakes", "id": 1535683572910784652, "animated": False, "is_safe": False, "rank": 51},
    "im_done": {"name": "Im_done", "id": 1535683692779802664, "animated": False, "is_safe": False, "rank": 52},
    "yb_ayo": {"name": "yb_ayo", "id": 1535683762182955051, "animated": False, "is_safe": False, "rank": 53},
    "monkeythink": {"name": "monkeythink", "id": 1535684318993584219, "animated": False, "is_safe": False, "rank": 54},
    "9999iq": {"name": "9999IQ", "id": 1535684433011540078, "animated": False, "is_safe": False, "rank": 55},
    "pensivebetrayal": {"name": "pensivebetrayal", "id": 1535684508542832690, "animated": False, "is_safe": False, "rank": 56},
    "emojigg_huh": {"name": "emojigg_HUH", "id": 1535684921795026984, "animated": False, "is_safe": False, "rank": 57},
    "porro": {"name": "Porro", "id": 1535685303317172305, "animated": False, "is_safe": False, "rank": 58},
    "cathink": {"name": "cathink", "id": 1535685385424867400, "animated": False, "is_safe": False, "rank": 59},
    "thousandyardstare": {"name": "thousandyardstare", "id": 1535685557525545062, "animated": False, "is_safe": False, "rank": 60},
    "4k_ultra_hd": {"name": "4k_ultra_hd", "id": 1535685617026080911, "animated": False, "is_safe": False, "rank": 61},
    "baldwinhand": {"name": "BaldwinHand", "id": 1535724200013201408, "animated": False, "is_safe": False, "rank": 62},
    "dumbass_stare": {"name": "dumbass_stare", "id": 1535724333756977253, "animated": False, "is_safe": False, "rank": 63},
    "poorhomeless": {"name": "PoorHomeless", "id": 1535724701698228234, "animated": False, "is_safe": False, "rank": 64},
    "patrickleash": {"name": "PatrickLeash", "id": 1535724791644954691, "animated": False, "is_safe": False, "rank": 65},
    "bb_thumbs_up": {"name": "bb_thumbs_up", "id": 1535725204175855726, "animated": False, "is_safe": False, "rank": 66},
    "oh_god": {"name": "oh_god", "id": 1535725370723147939, "animated": False, "is_safe": False, "rank": 67},
    "fruity_sus": {"name": "fruity_sus", "id": 1535725573190455308, "animated": False, "is_safe": False, "rank": 68},
    "florkwhat": {"name": "Florkwhat", "id": 1535725634779619472, "animated": False, "is_safe": False, "rank": 69},
    "tungtungtungsahur": {"name": "Tungtungtungsahur", "id": 1535725729503772813, "animated": False, "is_safe": False, "rank": 70},
    "skeleton": {"name": "skeleton", "id": 1535725933032382556, "animated": False, "is_safe": False, "rank": 71},
    "nobodycares": {"name": "nobodycares", "id": 1535726064293257298, "animated": False, "is_safe": False, "rank": 72},
    "messirve": {"name": "Messirve", "id": 1535726367847743528, "animated": False, "is_safe": False, "rank": 73},
    "mindblown": {"name": "Mindblown", "id": 1535726556318793798, "animated": False, "is_safe": False, "rank": 74},
    "autism": {"name": "Autism", "id": 1535726626049101926, "animated": False, "is_safe": False, "rank": 75},
    "cooked": {"name": "cooked", "id": 1535726716901789726, "animated": False, "is_safe": False, "rank": 76},
    "mortroll": {"name": "mortroll", "id": 1535726810086641795, "animated": False, "is_safe": False, "rank": 77},
    "blue_screen": {"name": "blue_screen", "id": 1535726947831914576, "animated": False, "is_safe": False, "rank": 78},
    "grass": {"name": "grass", "id": 1535727100365901855, "animated": False, "is_safe": False, "rank": 79},
    "skillissue": {"name": "skillissue", "id": 1535727329156931624, "animated": False, "is_safe": False, "rank": 80},
    "emojigg_bot": {"name": "emojigg_bot", "id": 1535727917441744937, "animated": False, "is_safe": False, "rank": 81},
    "serious": {"name": "Serious", "id": 1535728149038366851, "animated": False, "is_safe": False, "rank": 82},
    "point_gay": {"name": "POINT_GAY", "id": 1535728247696789564, "animated": False, "is_safe": False, "rank": 83},
    "emojigg_ban": {"name": "emojigg_BAN", "id": 1535728476181495870, "animated": False, "is_safe": False, "rank": 84},
    "aura": {"name": "aura", "id": 1535728704129466462, "animated": False, "is_safe": False, "rank": 85},
    "ahegao": {"name": "ahegao", "id": 1535728782630191174, "animated": False, "is_safe": False, "rank": 86},
    "take_my_money": {"name": "take_my_money", "id": 1535728830097133751, "animated": False, "is_safe": False, "rank": 87},
    "stfu": {"name": "STFU", "id": 1535728963371147296, "animated": False, "is_safe": False, "rank": 88},
    "true": {"name": "true", "id": 1535729025794838609, "animated": False, "is_safe": False, "rank": 89},
    "same": {"name": "same", "id": 1535729270582943824, "animated": False, "is_safe": False, "rank": 90},
    "false": {"name": "False", "id": 1535729373947109487, "animated": False, "is_safe": False, "rank": 91},
    "thankyou": {"name": "thankyou", "id": 1535730204977406062, "animated": False, "is_safe": False, "rank": 92},
    "ranked_pro": {"name": "Ranked_Pro", "id": 1550129987972104252, "animated": False, "is_safe": False, "rank": 93},
    "ranked_masters": {"name": "Ranked_Masters", "id": 1550129992837496833, "animated": False, "is_safe": False, "rank": 94},
    "ranked_legendary": {"name": "Ranked_Legendary", "id": 1550129997774323732, "animated": False, "is_safe": False, "rank": 95},
    "ranked_mythic": {"name": "Ranked_Mythic", "id": 1550130000852820099, "animated": False, "is_safe": False, "rank": 96},
    "ranked_diamond": {"name": "Ranked_Diamond", "id": 1550130004074041434, "animated": False, "is_safe": False, "rank": 97},
    "ranked_gold": {"name": "Ranked_Gold", "id": 1550130006896812084, "animated": False, "is_safe": False, "rank": 98},
    "hello_wave": {"name": "hello_wave", "id": 1535678953870725121, "animated": True, "is_safe": True, "rank": 1},
    "thisisfine": {"name": "Thisisfine", "id": 1535679070312857672, "animated": True, "is_safe": True, "rank": 2},
    "hulk_gif": {"name": "hulk_gif", "id": 1535679185803018361, "animated": True, "is_safe": True, "rank": 3},
    "pain": {"name": "pain", "id": 1535679465383002192, "animated": True, "is_safe": True, "rank": 4},
    "pepe_simp": {"name": "pepe_simp", "id": 1535679584819875950, "animated": True, "is_safe": True, "rank": 5},
    "donowall": {"name": "Donowall", "id": 1535679683918831676, "animated": True, "is_safe": True, "rank": 6},
    "kekwlaugh": {"name": "KEKWLaugh", "id": 1535679941059018903, "animated": True, "is_safe": True, "rank": 7},
    "galaxybrainmeme": {"name": "GalaxyBrainMeme", "id": 1535680100060766311, "animated": True, "is_safe": True, "rank": 8},
    "cat_bitting": {"name": "cat_bitting", "id": 1535680234207191100, "animated": True, "is_safe": True, "rank": 9},
    "chadgif": {"name": "chadgif", "id": 1535680346199162982, "animated": True, "is_safe": True, "rank": 10},
    "flashbang": {"name": "flashbang", "id": 1535680549660655616, "animated": True, "is_safe": True, "rank": 11},
    "actually_im": {"name": "ACTUALLY_IM", "id": 1535680603179974678, "animated": True, "is_safe": True, "rank": 12},
    "cat_boom": {"name": "cat_boom", "id": 1535725821652770836, "animated": True, "is_safe": True, "rank": 13},
    "dead_spin": {"name": "dead_spin", "id": 1535726486168932353, "animated": True, "is_safe": True, "rank": 14},
    "yummy": {"name": "yummy", "id": 1535726899018338346, "animated": True, "is_safe": True, "rank": 15},
    "scubbacat": {"name": "Scubbacat", "id": 1535727498602618890, "animated": True, "is_safe": True, "rank": 16},
    "ai_baby": {"name": "ai_baby", "id": 1535727719948623872, "animated": True, "is_safe": True, "rank": 17},
    "freaky_lick": {"name": "freaky_lick", "id": 1535727845014241320, "animated": True, "is_safe": True, "rank": 18},
    "reze": {"name": "Reze", "id": 1535727967232069642, "animated": True, "is_safe": True, "rank": 19},
    "panickedno": {"name": "PanickedNo", "id": 1535728525431013437, "animated": True, "is_safe": True, "rank": 20},
    "cornershaking": {"name": "cornershaking", "id": 1535728585665548298, "animated": True, "is_safe": True, "rank": 21},
    "emojigg_67": {"name": "emojigg_67", "id": 1535729079657963661, "animated": True, "is_safe": True, "rank": 22},
    "spinningfish": {"name": "SpinningFish", "id": 1535729132208656395, "animated": True, "is_safe": True, "rank": 23},
    "ononono": {"name": "ononono", "id": 1535729205982269570, "animated": True, "is_safe": True, "rank": 24},
    "think": {"name": "Think", "id": 1535729557469011968, "animated": True, "is_safe": True, "rank": 25},
    "zooom": {"name": "ZOOOM", "id": 1535729987116736554, "animated": True, "is_safe": True, "rank": 26},
}

# Fallbacks limpios cuando un emoji queda deshabilitado en Discord por expiración del Server Boost (slots 51-98)
DISABLED_EMOJI_FALLBACK = {
    "doakes": "🤨",
    "im_done": "🤦‍♂️",
    "yb_ayo": "😳",
    "monkeythink": "🐵🤔",
    "9999iq": "<:gigachad:1535682070536519730>",
    "pensivebetrayal": "😔🗡️",
    "emojigg_huh": "🤨",
    "porro": "🚬",
    "cathink": "🐱🤔",
    "thousandyardstare": "😳",
    "4k_ultra_hd": "📸",
    "baldwinhand": "✋",
    "dumbass_stare": "😐",
    "poorhomeless": "🏚️",
    "patrickleash": "🪢",
    "bb_thumbs_up": "👍",
    "oh_god": "😱",
    "fruity_sus": "🤨",
    "florkwhat": "🥢",
    "tungtungtungsahur": "🥁",
    "skeleton": "💀",
    "nobodycares": "🤷‍♂️",
    "messirve": "<:facherita:1484580141618303021>",
    "mindblown": "🤯",
    "autism": "🎉",
    "cooked": "💀",
    "mortroll": "🃏",
    "blue_screen": "💻💥",
    "grass": "🌱",
    "skillissue": "<:pepeCringe:1530996221810966690>",
    "emojigg_bot": "🤖",
    "serious": "😐",
    "point_gay": "👉",
    "emojigg_ban": "🔨",
    "aura": "<:gigachad:1535682070536519730>",
    "ahegao": "😵",
    "take_my_money": "💸",
    "stfu": "🤫",
    "true": "✅",
    "same": "🤝",
    "false": "❌",
    "thankyou": "🙏",
    "ranked_pro": "🏆",
    "ranked_masters": "👑",
    "ranked_legendary": "🌟",
    "ranked_mythic": "🟣",
    "ranked_diamond": "💎",
    "ranked_gold": "🥇",
}

REACTION_SINGLE_UNICODE_FALLBACK = {
    "monkeythink": "🤔",
    "pensivebetrayal": "😔",
    "cathink": "🤔",
    "blue_screen": "💥",
    "9999iq": "🧠",
    "messirve": "👍",
    "skillissue": "💀",
    "aura": "🗿",
}

RAW_DISCORD_EMOJI_PATTERN = re.compile(r"<(?P<anim>a)?:(?P<name>[a-zA-Z0-9_]+):(?P<id>\d+)>")
EMOJI_PATTERN = re.compile(r"(?<!<)(?<!<a):([a-zA-Z0-9_]+):(?!\d+>)")
ID_LEAK_PATTERN = re.compile(
    r"([\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50]|<a?:[a-zA-Z0-9_]+:\d+>)(?:\s*)(\d{15,21})"
)


def format_server_emojis(text: str, guild: discord.Guild = None) -> str:
    """
    Convierte automáticamente patrones ':nombre_emoji:' en menciones nativas de Discord:
      <:nombre_emoji:ID> (estáticos) o <a:nombre_emoji:ID> (animados).

    Resiliencia de Server Boosts, compatibilidad y blindaje:
    - Soporte para menciones <:name:ID> y <a:name:ID> ya presentes o generadas por Gemini:
      Si el emoji en guild.emojis tiene available == False (o no existe en el servidor),
      se sustituye por su fallback limpio de DISABLED_EMOJI_FALLBACK (o Unicode).
    - Limpieza de fugas de ID crudo:
      Si un emoji queda seguido de un ID numérico (ej: 💸1535726716901789726.), se purga
      el remanente para dejar únicamente el emoji limpio.
    - Puntuación adyacente:
      Procesa de forma infalible casos con puntuaciones pegadas (:bruh:.., :grass:,, :KEKWLaugh:., (:Porro:), ¡:aura:!).
    - Protege bloques de código (```...```) y código inline (`...`) para no alterar fragmentos técnicos.
    """
    if not text or not isinstance(text, str):
        return text

    code_blocks = []

    def _save_code(m):
        code_blocks.append(m.group(0))
        return f"___CODE_BLOCK_{len(code_blocks)-1}___"

    text_protected = re.sub(r"(```[\s\S]*?```|`[^`\n]+`)", _save_code, text)

    live_map = {}
    live_id_map = {}
    if guild and hasattr(guild, "emojis") and guild.emojis:
        for e in guild.emojis:
            live_map[e.name.lower()] = e
            try:
                live_id_map[int(e.id)] = e
            except (ValueError, TypeError):
                pass

    # Paso 1: Sanitizar menciones crudas ya formateadas (<:name:id> o <a:name:id>)
    # Si el servidor reporta que el emoji está deshabilitado o no existe, aplicar fallback limpio
    def _replace_raw_mention(match):
        raw_name = match.group("name")
        lower_name = raw_name.lower()
        try:
            raw_id = int(match.group("id"))
        except (ValueError, TypeError):
            raw_id = None

        if live_map or live_id_map:
            e = live_id_map.get(raw_id) or live_map.get(lower_name)
            if e:
                is_available = getattr(e, "available", True)
                if is_available:
                    prefix = "a" if e.animated else ""
                    return f"<{prefix}:{e.name}:{e.id}>"
                else:
                    if lower_name in DISABLED_EMOJI_FALLBACK:
                        return DISABLED_EMOJI_FALLBACK[lower_name]
                    return match.group(0)
            else:
                # No existe en el servidor activo
                if lower_name in DISABLED_EMOJI_FALLBACK:
                    return DISABLED_EMOJI_FALLBACK[lower_name]
                return match.group(0)

        return match.group(0)

    text_protected = RAW_DISCORD_EMOJI_PATTERN.sub(_replace_raw_mention, text_protected)

    # Paso 2: Convertir patrones :nombre_emoji:
    def _replace(match):
        raw_name = match.group(1)
        lower_name = raw_name.lower()

        # 1. Consulta en tiempo real en discord.py si guild está disponible
        if live_map or live_id_map:
            if lower_name in live_map:
                e = live_map[lower_name]
                is_available = getattr(e, "available", True)
                if is_available:
                    prefix = "a" if e.animated else ""
                    return f"<{prefix}:{e.name}:{e.id}>"
                else:
                    if lower_name in DISABLED_EMOJI_FALLBACK:
                        return DISABLED_EMOJI_FALLBACK[lower_name]
                    return match.group(0)
            elif lower_name in DISABLED_EMOJI_FALLBACK:
                return DISABLED_EMOJI_FALLBACK[lower_name]

        # 2. Fallback de catálogo canónico base (para tests, DMs o bot headless)
        if lower_name in SERVER_EMOJIS_DATA:
            info = SERVER_EMOJIS_DATA[lower_name]
            prefix = "a" if info["animated"] else ""
            return f"<{prefix}:{info['name']}:{info['id']}>"

        return match.group(0)

    converted = EMOJI_PATTERN.sub(_replace, text_protected)

    # Paso 3: Limpieza de fugas de ID crudo (ej: 💸1535726716901789726. -> 💸.)
    converted = ID_LEAK_PATTERN.sub(r"\1", converted)
    converted = re.sub(r"<([\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50]):?\d{15,21}>", r"\1", converted)

    # Paso 4: Restaurar bloques de código markdown
    for idx, block in enumerate(code_blocks):
        converted = converted.replace(f"___CODE_BLOCK_{idx}___", block)

    return converted


SINGLE_UNICODE_EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50\u2764\u203c\u2049\u2122\u2139\u2194-\u2199\u21a9-\u21aa]"
    r"(?:\ufe0f)?(?:\u200d[\U00010000-\U0010ffff\u2600-\u27bf\u2640\u2642\u2695\u2696\u2708\u2764](?:\ufe0f)?)*"
)


def _extract_first_unicode_emoji(s: str) -> Optional[str]:
    if not s:
        return None
    m = SINGLE_UNICODE_EMOJI_PATTERN.search(s)
    if m:
        return m.group(0)
    return None


def resolve_reaction_emoji(raw_emoji: str, guild: discord.Guild = None) -> Optional[Union[discord.Emoji, str]]:
    """
    Resuelve cualquier formato de emoji emitido por Gemini en [ACTION_REACT: ...]
    a un objeto discord.Emoji activo, una cadena <:name:id> segura o un único emoji Unicode válido
    para message.add_reaction.
    """
    if not raw_emoji or not isinstance(raw_emoji, str):
        return None

    cleaned = raw_emoji.strip()
    if not cleaned:
        return None

    live_map = {}
    live_id_map = {}
    has_live_emojis = False
    if guild and hasattr(guild, "emojis") and guild.emojis:
        has_live_emojis = True
        for e in guild.emojis:
            live_map[e.name.lower()] = e
            try:
                live_id_map[int(e.id)] = e
            except (ValueError, TypeError):
                pass

    target_name = None
    target_id = None

    m_raw = RAW_DISCORD_EMOJI_PATTERN.fullmatch(cleaned) or RAW_DISCORD_EMOJI_PATTERN.search(cleaned)
    if m_raw:
        target_name = m_raw.group("name").lower()
        try:
            target_id = int(m_raw.group("id"))
        except (ValueError, TypeError):
            target_id = None
    else:
        m_colon = re.fullmatch(r":([a-zA-Z0-9_]+):", cleaned)
        if m_colon:
            target_name = m_colon.group(1).lower()
        elif re.fullmatch(r"[a-zA-Z0-9_]+", cleaned):
            cand = cleaned.lower()
            if (
                cand in SERVER_EMOJIS_DATA
                or cand in DISABLED_EMOJI_FALLBACK
                or cand in REACTION_SINGLE_UNICODE_FALLBACK
                or cand in live_map
            ):
                target_name = cand
            else:
                return None

    if target_name is not None or target_id is not None:
        if has_live_emojis:
            e = (live_id_map.get(target_id) if target_id is not None else None) or (
                live_map.get(target_name) if target_name else None
            )
            if e and getattr(e, "available", True):
                return e

            # Emoji deshabilitado o no presente en guild.emojis
            lower_name = target_name or (e.name.lower() if e else "")
            if lower_name in DISABLED_EMOJI_FALLBACK:
                fb_val = DISABLED_EMOJI_FALLBACK[lower_name]
                fb_match = RAW_DISCORD_EMOJI_PATTERN.search(fb_val)
                if fb_match:
                    other_name = fb_match.group("name").lower()
                    try:
                        other_id = int(fb_match.group("id"))
                    except (ValueError, TypeError):
                        other_id = None
                    other_e = (live_id_map.get(other_id) if other_id else None) or live_map.get(other_name)
                    if other_e and getattr(other_e, "available", True):
                        return other_e
                    if lower_name in REACTION_SINGLE_UNICODE_FALLBACK:
                        return REACTION_SINGLE_UNICODE_FALLBACK[lower_name]
                    return "👍"
                if lower_name in REACTION_SINGLE_UNICODE_FALLBACK:
                    return REACTION_SINGLE_UNICODE_FALLBACK[lower_name]
                uni = _extract_first_unicode_emoji(fb_val)
                return uni if uni else "🤔"

            if lower_name in REACTION_SINGLE_UNICODE_FALLBACK:
                return REACTION_SINGLE_UNICODE_FALLBACK[lower_name]
            return "🤔"
        else:
            # Sin guild o sin guild.emojis (ej. DMs o tests sin guild)
            lower_name = target_name or ""
            if lower_name in SERVER_EMOJIS_DATA:
                info = SERVER_EMOJIS_DATA[lower_name]
                if info.get("is_safe", True):
                    prefix = "a" if info.get("animated") else ""
                    return f"<{prefix}:{info['name']}:{info['id']}>"
                if lower_name in REACTION_SINGLE_UNICODE_FALLBACK:
                    return REACTION_SINGLE_UNICODE_FALLBACK[lower_name]
                if lower_name in DISABLED_EMOJI_FALLBACK:
                    fb_val = DISABLED_EMOJI_FALLBACK[lower_name]
                    if RAW_DISCORD_EMOJI_PATTERN.search(fb_val):
                        return fb_val
                    uni = _extract_first_unicode_emoji(fb_val)
                    return uni if uni else "🤔"
                return "🤔"
            if lower_name in REACTION_SINGLE_UNICODE_FALLBACK:
                return REACTION_SINGLE_UNICODE_FALLBACK[lower_name]
            if lower_name in DISABLED_EMOJI_FALLBACK:
                fb_val = DISABLED_EMOJI_FALLBACK[lower_name]
                uni = _extract_first_unicode_emoji(fb_val)
                return uni if uni else "🤔"
            return None

    # Emoji Unicode directo
    first_uni = _extract_first_unicode_emoji(cleaned)
    if first_uni:
        return first_uni

    return None


def extract_reaction_tag(text: str) -> tuple[str, Optional[str]]:
    """
    Extrae todas las etiquetas [ACTION_REACT: ...] del texto usando extract_action_block
    y limpieza por regex de respaldo.
    Devuelve (clean_text, first_raw_emoji) conservando únicamente la primera reacción válida.
    """
    if not text or not isinstance(text, str):
        return text, None

    from modulos.graficos import extract_action_block

    first_raw_emoji: Optional[str] = None
    cleaned = text

    while True:
        block = extract_action_block(cleaned, "ACTION_REACT")
        if not block:
            break
        full_tag, content = block
        cand = content.strip()
        if cand and first_raw_emoji is None:
            first_raw_emoji = cand
        cleaned = cleaned.replace(full_tag, "", 1)

    if first_raw_emoji is None:
        m = re.search(r"\[ACTION_REACT:\s*([^\]]*)\]", cleaned, flags=re.IGNORECASE)
        if m and m.group(1).strip():
            first_raw_emoji = m.group(1).strip()

    cleaned = re.sub(r"\[ACTION_REACT:\s*[^\]]*\]", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned, first_raw_emoji


SYSTEM_PROMPT_BODY = r"""
- ❌ CERO "MODO CUÑADO VACILÓN" / CERO FALTAS DE RESPETO: Trata a todos con respeto y estima. NUNCA te burles de los miembros, no uses apodos despectivos, no hagas chistes pesados de mafiosos ni te pongas arrogante o condescendiente. No digas tonterías como "meme de dueño" o "menudo espectáculo de admin".
- ❌ CERO PELOTEO / SUMISIÓN: Habla de tú a tú como un igual con todos, incluido Joselito. Eres un colega inteligente del grupo, no un lacayo.
- ❌ CERO INVENCIÓN DE FECHAS HISTÓRICAS: NUNCA inventes fechas del pasado ("tiene admin desde el 4 de diciembre de 2025"). Si alguien te pregunta desde cuándo tiene un rango o rol, di con honestidad que en tus datos actuales ves sus roles vigentes, pero no dispones de la fecha exacta histórica de asignación.
- ❌ CERO RESPUESTAS DESCOLOCADAS O CRUZADAS: Responde única y exclusivamente a la duda o tema planteado por el usuario en el mensaje actual. No rescates temas antiguos o animes aleatorios que nadie ha pedido.
- ❌ CERO SPAM DE NIVELES Y XP: Habla de forma natural y humana. NO menciones niveles de Cakey Bot ni rangos en cada mensaje como un loro. Menciónalos ÚNICAMENTE si el usuario te pregunta explícitamente por su nivel, XP o el ranking.
- 7. 🚫 VETO ABSOLUTO A INVENTAR CONTENIDO DE DOCUMENTOS O ENLACES: Si el usuario te pregunta por el contenido, posiciones, tiers, recomendaciones o datos de un documento de Google Docs, enlace web o mensaje de otro canal, y NO dispones del texto real extraído en tu contexto (o el enlace falló / era privado): Queda TERMINANTEMENTE PROHIBIDO inventar obras, puestos, tiers o información verosímil (ej: decir que Solo Leveling, Omniscient Reader's Viewpoint o cualquier otra obra está en el top si no aparece literalmente en el texto extraído). Debes responder con sinceridad y con tu personalidad, diciendo que no pudiste leer el documento (o que no tienes el enlace/texto a la vista) y pidiéndole que verifique si el enlace es público o que te copie y pegue el fragmento directamente.
- PUEDES Y DEBES RESPONDER A CUALQUIER TIPO DE PREGUNTA: anime, manhwas, videojuegos, hardware, programación, ciencia, dilemas, bromas, actualidad, cine o salseo.

🎙️ PROTOCOLO ESTRICTO DE ESTADO DE VOZ Y LLAMADAS (AUDIO & TTS EN VIVO):
- Consulta OBLIGATORIAMENTE el bloque [RADAR EN VIVO DE CANALES DE VOZ]. Es la verdad absoluta y en tiempo real del servidor.
- Si un usuario aparece en el radar conectado a una sala, ESTÁ DENTRO. Revisa sus flags ([Micro activo/Hablando], [Silenciado/Mute], [Ensordecido], [Compartiendo pantalla]).
- Si un usuario NO aparece en el radar de esa sala o figura como [FUERA DE LLAMADA], ESTÁ FUERA. NUNCA contradigas a quien te está hablando diciendo que alguien está dentro si no figura en el radar.
- Si te preguntan si Joselito o cualquier otra persona está en la llamada, mira si su nombre aparece en la sala. Si no está, confirma claramente que no está en la llamada.
- 🗣️ LOCUCIÓN Y VOZ EN DIRECTO: Tienes la capacidad de unirte a canales de voz y hablar en vivo con síntesis neuronal de voz en español mediante el comando `/habla [texto] [voz]`. También puedes unirte con `/unete`, salir con `/desconecta` o parar el audio con `/para_audio`. Si te piden en el chat "di en la llamada: ..." o "únete a la llamada", sabrás que puedes hablar directamente por voz.

🧠 MEMORIA PERSISTENTE DE USUARIOS:
- Cuentas con un sistema de memoria de largo plazo que recuerda los gustos, obras favoritas (manhwas, series, juegos), notas y puntos de trivial de cada usuario.
- Cuando recibas el bloque [MEMORIA PERSISTENTE DE ESTE USUARIO], úsalo de forma natural para personalizar tus respuestas según sus gustos.
- Puedes sugerir o usar `/recuerda` para guardar datos clave de cualquier colega.

🎲 TRIVIAL Y MINIJUEGOS DEL SERVIDOR:
- Dispones del comando interactivo `/trivial [categoria]` con botones dinámicos para competir en preguntas de Manhwas, Videojuegos, El Tribunal Gaming, Lore del Servidor y Cultura General (+10 pts por acierto).
- Puedes consultar el podio del servidor con `/ranking_trivial`.

🎵 MÚSICA Y REPRODUCCIÓN EN CANALES DE VOZ:
- El bot oficial para poner música en el servidor es Cakey Bot.
- Si alguien pide escuchar una canción (ej: "escuchar projection (de yoshimasa terui)", "pon música", "/play"):
  1. Reconoce y comenta brevemente el tema solicitado con buen rollo.
  2. Explica con claridad cómo reproducirla en la sala con Cakey Bot mediante el comando slash: `/play song: <nombre de la canción>` o `/play search: <nombre>`.
  3. Si Cakey Bot está atascado con spam de 'queue empty' o la cola está vacía, indica que se desatasca con `/skip`, `/stop` o lanzando una nueva canción con `/play`.
  4. Facilita siempre el enlace directo de búsqueda de YouTube para que puedan escucharla al instante con un clic.

🎨 MOTOR GRÁFICO MULTIMODAL & GENERACIÓN VISUAL:
1. 🖼️ DIBUJO ARTÍSTICO (FLUX.1):
   - Si te piden dibujar o pintar una escena, incluye la etiqueta:
     [ACTION_DRAW: <detailed English visual prompt for FLUX.1 (max 40 words, subject, art style, lighting, cinematic)>]
2. 📐 FÓRMULAS MATEMÁTICAS EN IMAGEN (LaTeX Render):
   - ❌ NUNCA escribas fórmulas matemáticas en texto plano con código LaTeX (`$...$`, `$$...$$`, `\frac`, `\lim`, etc.): Discord no renderiza LaTeX y a los usuarios les aparece como código ilegible ("chino").
   - SIEMPRE que una explicación requiera una o varias fórmulas matemáticas formales (límites, derivadas, integrales, matrices, teoremas), explica el concepto con palabras en español llano y emite la etiqueta especial:
     [ACTION_MATH: <fórmula matemática pura en LaTeX limpia sin dólares, ej: \lim_{n \to \infty} \frac{a_n - a_{n-1}}{b_n - b_{n-1}}>]
     El sistema renderizará la fórmula automáticamente como una tarjeta gráfica PNG oscura y nítida de alta resolución y la adjuntará a tu respuesta.
3. 📊 GRÁFICAS ESTADÍSTICAS Y FUNCIONES:
   - Si piden graficar una función f(x), comparar datos numéricos o mostrar estadísticas, emite la etiqueta:
     [ACTION_CHART: {"type": "line|bar|pie", "data": {"labels": [...], "datasets": [{"label": "...", "data": [...]}]}}]
4. 🗺️ DIAGRAMAS DE FLUJO Y ESQUEMAS:
   - Para mapas conceptuales, algoritmos o flujos paso a paso, emite la etiqueta:
     [ACTION_DIAGRAM: <código mermaid, ej: graph TD; A[Inicio] --> B{Decisión}; B -->|Sí| C[Fin]>]
5. 💻 TARJETAS DE CÓDIGO ESTILIZADAS:
   - Si piden código de programación destacado, además de tu explicación puedes emitir:
     [ACTION_CODE: <código limpio sin backticks>]
6. 😄 REACCIÓN CON EMOJI AL MENSAJE DEL USUARIO (OPCIONAL):
   - Cuando el mensaje del usuario sea gracioso, irónico, picante, surrealista o tenga carga emocional clara (vaciles, quejas del casino, opiniones de cine/manhwas, preguntas cómplices), puedes añadir UNA reacción debajo de su mensaje incluyendo al final de tu respuesta:
     [ACTION_REACT: :nombre_emoji:] o [ACTION_REACT: 🤔]
   - Combina con naturalidad emojis del servidor (:pensando:, :bruh:, :KEKWLaugh:, :gigachad:, :absolutecinema:, :Porro:, :cooked:, :skillissue:, :pepeCRY:, :cat_sus:) y emojis Unicode clásicos (🤔, 💀, 😂, ❤️, 👀, 🔥).
   - Regla: Pon máximo 1 reacción y SOLO cuando aporte gracia o complicidad real (no reacciones en consultas técnicas o serias).

⚖️ EL TRIBUNAL GAMING (tribunal-gaming.vercel.app):
- Conoces al dedillo la base de datos oficial de El Tribunal Gaming (113 juegos cooperativos catalogados por categorías como Salvavidas o Guerreros con notas de rendimiento, 151 títulos evaluados con Metacritic y HowLongToBeat, y el Muro de la Vergüenza).
- Puedes responder sobre notas, horas de juego y viabilidad cooperativa si te lo preguntan en el chat o remitiéndoles al comando `/tribunal`.

🕹️ STEAM STORE EN VIVO:
- Puedes consultar precios en tiempo real en euros, ofertas actuales, porcentaje de descuento y compatibilidad de juegos en Steam mediante el comando `/steam` o en el chat general.

💻 COMANDOS SLASH ACTIVOS:
- Dispones de comandos nativos de Discord con interfaz y autocompletado:
  * `/habla [texto] [voz]`: Entra al canal de voz y habla con voz neuronal (25 voces: acentos de España, México, Argentina, Colombia, Perú y Cuba, efectos Ardilla/Demonio y 13 voces Gemini).
  * `/unete` y `/desconecta`: Control de conexión a salas de voz.
  * `/ajedrez [dificultad] [color]`: Partida de ajedrez contra ti en 4 niveles (Fácil ~800, Medio 1400, Difícil 1900, Máximo 3000+ ELO); se juega con menús o escribiendo la jugada en el canal.
  * `/para_audio`: Silencia el audio actual en la llamada.
  * `/trivial [categoria]` y `/ranking_trivial`: Minijuego de preguntas del server con clasificación.
  * `/recuerda [dato] [categoria] [usuario]`: Guarda memoria persistente de gustos y detalles.
  * `/voz`: Radar en vivo de llamadas y quién está dentro.
  * `/musica [cancion]`: Guía y enlace rápido para escuchar temas con Cakey Bot o YouTube.
  * `/dibuja [prompt] [estilo]`: Generación de imágenes FLUX.1.
  * `/steam [juego]`: Consulta precios, descuentos y notas de Steam.
  * `/tribunal [accion] [juego]`: Catálogo de El Tribunal Gaming.
  * `/perfil [usuario]`: Ficha de miembros con roles y niveles.
  * `/pregunta [duda]`: Preguntas directas a la IA.
  * `/autoroles [canal] [formato]`: Publica el panel interactivo 24/7 de Auto-Roles (menús desplegables y vista personal, reemplazando a Carl-bot).
  * `/sugerencia [idea]`: Envía una sugerencia a `#💡sugerencias💡` con botones de votación en vivo y moderación para admins.

💰 ECONOMÍA OFICIAL DE PORROS, CASINO Y BOLSA SANVI (BOT: ECONOMIA ASISTENTE):
- 👑 BOT SOBERANO Y JUBILACIÓN DE UNBELIEVABOAT:
  * El bot oficial, soberano y único de economía en el servidor es **Economia Asistente** (`Economia Asistente#5317`), un bot hermano nativo en Discord.
  * ❌ UnbelievaBoat HA SIDO RETIRADO Y JUBILADO DEFINITIVAMENTE del servidor. Ya no existe ni gestiona saldo alguno.
  * ❌ CERO COMANDOS CON PREFIJOS DE TEXTO: Todos los comandos de economía son estricta y obligatoriamente **Comandos Slash (`/`)**. NUNCA existen comandos con `!` (`!roulette`, `!rob`, `!work`, `!bj`, `!dep`, `!with` son del pasado y no funcionan). Si algún usuario intenta usar prefijo `!` o pregunta por ellos, corrígelo con humor y vacile sano de colega: recuérdale que UnbelievaBoat está criando malvas y que ahora todo se ejecuta con la barra `/` de `Economia Asistente`.
  * 🌿 MONEDA OFICIAL: `<:Porro:1535685303317172305>` **Porros** (saldo inicial al registrarse: 1.000 porros).
- 👀 VISIÓN TOTAL DE EMBEDS, COMPONENTES Y MENSAJES DE BOTS:
  * Tienes visión completa de los Embeds, componentes interactivos y mensajes de otros bots (especialmente 'Economia Asistente', Cakey Bot, etc.) tanto en la conversación reciente como cuando un usuario responde directamente citando uno de sus mensajes ([RESPONDIENDO DIRECTAMENTE AL MENSAJE DEL BOT ...]).
  * Si un usuario responde a o cita un saldo (/balance), transferencia, premio de ruleta/slots, atraco o estado bursátil, VES PERFECTAMENTE las cifras, porros en mano, porros en banco, total y detalles.
  * ❌ CERO CEGUERA: NUNCA digas que "no ves nada", que "está vacío" o que el usuario "no enseña nada". Comenta las cifras exactas, felicítale por estar forrado, vacílale amistosamente por arruinarse o flipa con sus números con total naturalidad y complicidad de colega.

🎰 MECÁNICA CANÓNICA DEL BOTE PROGRESIVO (JACKPOT DEL SERVIDOR) Y RULETA:
- **¿Cómo funciona el bote en la ruleta?**: En la Ruleta Europea (`/ruleta`), las pérdidas netas de los jugadores alimentan continuamente el bote progresivo del servidor (`server_jackpot`) aportando un 3% directo de cada tirada perdida. Cada vez que alguien palma porros en la ruleta, ¡está engordando el bote del servidor para la gloria de quien lo gane!
- **¿Cómo se saca/revienta el bote?**: El bote progresivo acumulado se gana principalmente en las **Tragaperras 5x3** (`/slots`) al alinear una combinación ganadora de Jackpot de 5 símbolos mayores. ¡En la ruleta lo alimentas y aumentas con tus desgracias, pero el pozo gordo se revienta en las slots!
- **Pagos de la Ruleta Europea (`/ruleta`)**: Cilindro europeo de 37 casillas (del 0 al 36):
  * 1:1 en suertes sencillas: Rojo / Negro, Par / Impar, Pasa / Falta (Baja 1-18 / Alta 19-36).
  * 2:1 en Docenas (1ª, 2ª, 3ª) y Columnas.
  * 35:1 en Pleno directo al número exacto (0-36).

📋 CATÁLOGO CANÓNICO DE COMANDOS SLASH DE ECONOMIA ASISTENTE:
- 🎲 Casino y Apuestas:
  * `/slots [apuesta]`: Tragaperras 5x3 con carretes animados (7 líneas de pago, RTP 110.03%, tiradas gratis Free Spins y donde se revienta el Jackpot acumulado).
  * `/ruleta [apuesta] [tipo] [numero]`: Ruleta Europea clásica de 37 casillas (Rojo, Negro, Par, Impar, Docenas, Columnas, Pleno 0-36). Cada tirada perdida alimenta el bote en un 3%.
  * `/blackjack` o `/bj [apuesta]`: Blackjack 21 contra el crupier con baraja interactiva, doblar apuesta y pago 3:2.
  * `/coinflip [apuesta] [lado] [rival]`: Cara o cruz (PvE contra la banca o duelos de honor PvP 1v1 con aceptación interactiva).
  * `/casino`: Hub central del casino con reglas completas, saldo personal y estado en vivo del Bote Acumulado.
- 💼 Finanzas y Progresión:
  * `/balance [usuario]`: Consulta de porros en mano (efectivo), cuenta bancaria y patrimonio total.
  * `/trabajar`: Jornada laboral cada 2 horas (1.000-2.500 Porros + bonus de nivel del servidor y multiplicador de Aura bursátil).
  * `/salario`: Sueldo diario acumulativo según roles y nivel del servidor.
  * `/crimen` y `/robar [usuario]`: Hurtos callejeros y atracos a otros usuarios (con riesgo de multa policial o calabozo).
  * `/depositar [monto]` y `/retirar [monto]`: Blindar porros en el banco ante robos callejeros.
  * `/transferir [usuario] [monto]`: Enviar porros limpios a un colega sin comisiones.
  * `/ranking`: Tabla de clasificación de los usuarios más forrados del servidor.
- 📈 Bolsa Sanvi & Reputación:
  * `/bolsa [ticker]`: Cotizaciones bursátiles en tiempo real de miembros del servidor con gráficas financieras Pillow (estilo Trading 212).
  * `/cartera`: Portafolio bursátil con acciones adquiridas y balance de ganancias/pérdidas no realizadas.
  * `/aura [usuario]`: Reputación comunitaria de miembros que genera dividendos pasivos y prestigio.
- 🏪 Tienda y Artículos:
  * `/tienda`: Catálogo de objetos útiles (`🛡️ Cartera Blindada`, `⚡ Monster Blanco`, etc.).
  * `/inventario`: Mochila personal con artículos adquiridos.
  * `/usar [item]`: Consumir o activar un objeto del inventario.
  * `/regalar [item] [usuario]`: Transferir artículos a otro colega.

👥 MIEMBROS CLAVE DEL SERVIDOR (Lore & Respeto):
- Joselito (@joselito3499): Administrador principal y Desarrollador del servidor y de sus bots (creador y artífice del 95% de todo el servidor, sistemas, canales, economía y bots). Fanático de los manhwas (Olympus Scanlation, Asura Scans). En #cultura tiene anclado su top 69 manhwas.
- Iván / RobaAbuelas (@racerwasp): Administrador y Dueño del servidor (en nombre/corona, aunque el 95% del servidor lo ha construido y desarrollado Joselito) y Magistrado oficial de El Tribunal Gaming. Veterano del colegio/grupo, jugador de Brawl Stars, Soulslike y lector de manhwas. Trátale con el respeto y la confianza de colega y Admin veterano que es.
- Lázaro (@terreneiror): Miembro veterano, colega de la vieja guardia. Aficionado a videojuegos, RPGs y anime.
- Omen2042 (@omen2042_38051): Organizador de torneos y eventos de la comunidad.
- Carlitosmf (@carlitosmf__): Miembro habitual del chat y del casino.
- Vexus, Carmen, Alejandro, Sanix, Danielo, Maikel, Rafa: Miembros y colegas habituales del servidor.

🗺️ MAPA DE CANALES PRINCIPALES:
- #cultura: El santuario de mangas, manhwas, anime, cine, novelas ligeras y charlas de madrugada.
- #el-tribunal-gaming: Sede oficial del Tribunal Gaming (tribunal-gaming.vercel.app). Los magistrados juzgan videojuegos (0-100), gestionan la Escala de Ganas y el Muro de la Vergüenza.
- #la-shit-de-todos-los-dias: El canal de charla general del día a día.
- #violencia: Debates intensos, piques deportivos y salseo.
- #muro-de-la-fama: Starboard oficial del servidor.
- #casino-y-apuestas: Zona oficial de casino y vicio de Economia Asistente (/slots, /ruleta, /blackjack, /coinflip, /casino).
- #tienda-y-mercado: Mercado oficial de Sanvi (/tienda, /inventario, compras e ítems de protección).

🌐 BÚSQUEDA WEB EN VIVO:
- Cuando recibas el bloque [BÚSQUEDA WEB EN VIVO], utilízalo como verdad absoluta para responder con fechas reales, estrenos, secuelas y noticias de actualidad.

🛡️ SEGURIDAD Y AUTO-ROLES:
- Por chat de texto nunca asignas roles de administración ni niveles ni expulsas a nadie (si te lo piden en broma, responde con humor de colega).
- Para roles de juegos, plataformas, géneros y hobbies, gestionas el panel interactivo oficial de Auto-Roles en <#1537575617111920782> (`#🎭roles🎭` / comando `/autoroles`), reemplazando por completo al antiguo Carl-bot.

🎭 USO DE EMOJIS DEL SERVIDOR Y LORE HUMORÍSTICO:
- Tienes a tu disposición los 124 emojis del servidor. Úsalos con soltura, gracia y naturalidad en tus respuestas como un colega más:
  * ⚠️ DIRECTRIZ ESTRICTA DE FORMATO: Escribe los emojis ÚNICAMENTE con el formato simple `:nombre_emoji:` (ejemplo: `:Porro:`, `:bruh:`, `:grass:`). NUNCA inventes ni escribas IDs numéricos ni la sintaxis `<:nombre:ID>`. El sistema los convierte automáticamente a formato de Discord.
  * `:aura:` / `:gigachad:` / `:chadgif:` / `:sigmajawline:` / `:Sigma_Male_Bale:`: Para momentos de máximo respeto, jugadas maestras (+1.000 aura), respuestas legendarias o actitud sigma imperturbable.
  * `:Porro:`: Para situaciones surrealistas, momentos de "qué me estás contando", teorías imposibles, relajación o fumadas sanas.
  * `:absolutecinema:`: Imprescindible para elogiar manhwas sublimes (como los del Top 69 de Joselito en #cultura), animes top o momentos de cine puro.
  * `:Messirve:`: Para dar el visto bueno, aceptar un trato con agrado o confirmar que algo es útil ("me sirve").
  * `:cooked:`: Cuando alguien la ha liado a lo grande, está suspendido, no tiene escapatoria o está en la ruina ("estás cocinado").
  * `:skillissue:`: Para vacilar amistosamente cuando alguien pierde en un juego, falla tiradas o pone excusas ("skill issue colega").
  * `:KEKWLaugh:` / `:ononono:` / `:catpointandlaugh:`: Para reírte a carcajadas de anécdotas o situaciones cómicas del grupo.
  * `:Thisisfine:`: Cuando todo se va a la mierda pero fingimos que el caos está controlado ("todo bajo control").
  * `:bruh:` / `:dead_stare:` / `:DwayneEyebrow:` / `:side_eye:`: Para miradas de sospecha, incredulidad o momentos "no me lo creo".
  * `:pepeCRY:` / `:pepeCringe:` / `:pepecuerda:` / `:pain:`: Para tristeza dramática, vergüenza ajena o desesperación cómica.
  * `:Ranked_Pro:` / `:Ranked_Masters:` / `:Ranked_Legendary:` / `:Ranked_Mythic:` / `:Ranked_Diamond:` / `:Ranked_Gold:`: Para hablar del competitivo de Brawl Stars (juego estrella de Iván y Joselito) o catalogar el nivel de alguien.
  * `:grass:`: Para mandar a alguien a tocar césped tras viciar 10 horas seguidas.
  * `:take_my_money:`: Para el hype ante compras de Steam, ofertas o apuestas del casino.
- Directriz: No satures con ristras excesivas de emojis. Pon 1 o 2 en el remate de tu mensaje donde den fuerza, humor o complicidad real de colega.

REGLAS DE FORMATO:
- Sé conciso, directo, estructurado y usa negritas.
- OBLIGATORIO: Máximo 1.700 caracteres por respuesta para entrar limpio en un único mensaje de Discord.
"""

SYSTEM_PROMPT_A = (
    r"""Eres 'Asistente', la IA oficial y colega del servidor de Discord 'LOS MONGOLOS DEL SANVI Y SUS AMIGOS'.

🎯 PERSONALIDAD Y TONO DE COLEGA (PERSONALIDAD A):
- Eres un colega más del grupo, maduro, cercano, divertido, resolutivo y con buen rollo de Discord."""
    + SYSTEM_PROMPT_BODY
)

SYSTEM_PROMPT_B = (
    r"""Eres 'Asistenta', la IA oficial y colega del servidor de Discord 'LOS MONGOLOS DEL SANVI Y SUS AMIGOS'.

🎯 PERSONALIDAD Y TONO DE COLEGA (PERSONALIDAD B):
- Eres una colega más del grupo, madura, cercana, divertida. Te llamas Asistenta y hablas en femenino ("estoy lista", "encantada", "una colega más"), resolutiva y con buen rollo de Discord."""
    + SYSTEM_PROMPT_BODY
)

BOT_PERSONALITIES = {
    "A": {
        "id": "A",
        "name": "Asistente",
        "avatar_path": "docs/imagenes_contexto/avatar_asistente_original.png",
        "system_prompt": SYSTEM_PROMPT_A,
    },
    "B": {
        "id": "B",
        "name": "Asistenta",
        "avatar_path": "docs/imagenes_contexto/media_1792796615874.jpg",
        "system_prompt": SYSTEM_PROMPT_B,
    },
}

ACTIVE_PERSONALITY = "A"
SYSTEM_PROMPT = SYSTEM_PROMPT_A


def call_gemini_multiturn(turns: list) -> str:
    gemini_key = _get_gemini_key()
    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": turns,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    models_to_try = get_available_models()

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        for attempt in range(2):
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    candidates = res.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        return candidates[0]["content"]["parts"][0]["text"].strip()
            except urllib.error.HTTPError as e:
                if e.code in (429, 503, 500):
                    print(f"Cuota/Sobrecarga en {model_name} (HTTP {e.code}). Activando Circuit Breaker...")
                    mark_model_cooldown(model_name, 60)
                    break
                elif e.code in (404, 400):
                    print(f"Modelo no disponible o no encontrado: {model_name} (HTTP {e.code}). Descartando...")
                    mark_model_cooldown(model_name, 3600)  # Descarte por 1 hora sin tumbar la cascada
                    break
                else:
                    print(f"Error HTTP {e.code} en {model_name}.")
                    break
            except (socket.timeout, TimeoutError, urllib.error.URLError) as e:
                # Si es timeout de red, no aplicar cooldown agresivo de 45s, solo intentar con el siguiente modelo
                is_timeout = isinstance(e, (socket.timeout, TimeoutError)) or (isinstance(e, urllib.error.URLError) and isinstance(getattr(e, "reason", None), (socket.timeout, TimeoutError))) or "timed out" in str(e).lower()
                if is_timeout:
                    print(f"⏱️ Timeout de red en {model_name} (12s). Intentando siguiente modelo sin cooldown agresivo...")
                    break
                else:
                    print(f"Excepción de red en {model_name}: {e}. Activando cooldown temporal...")
                    mark_model_cooldown(model_name, 45)
                    break
            except Exception as e:
                print(f"Excepción en {model_name}: {e}. Activando cooldown temporal...")
                mark_model_cooldown(model_name, 45)
                break

    return "Cuota de IA temporalmente saturada. Se restablece en unos momentos automáticamente."


# ==========================================
# MEMORIA PERSISTENTE DE USUARIOS
# ==========================================

USER_MEMORY_PATH = os.path.join(_get_base_dir(), "datos", "user_memory.json")


def load_user_memory() -> dict:
    base = _get_base_dir()
    path = os.path.join(base, "datos", "user_memory.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Aviso lectura user_memory.json: {e}")
    return {}


def save_user_memory(data: dict):
    base = _get_base_dir()
    path = os.path.join(base, "datos", "user_memory.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error guardando user_memory.json: {e}")


user_memory = load_user_memory()


def get_user_memory_ctx(user_id: int) -> str:
    """Extrae la memoria persistente del usuario para inyectarla en el contexto del bot."""
    bs = _bs()
    mem_dict = getattr(bs, "user_memory", user_memory)
    mem = mem_dict.get(str(user_id))
    if not mem:
        return ""
    lines = []
    if mem.get("name"):
        lines.append(f"  * Nombre/Apodo conocido: {mem.get('name')}")
    if mem.get("role_in_server"):
        lines.append(f"  * Rol/Estatus: {mem.get('role_in_server')}")
    if mem.get("fav_genres"):
        lines.append(f"  * Gustos/Géneros favoritos: {', '.join(mem.get('fav_genres'))}")
    if mem.get("fav_works"):
        lines.append(f"  * Obras/Juegos favoritos: {', '.join(mem.get('fav_works'))}")
    if mem.get("notes"):
        lines.append(f"  * Notas clave: {'; '.join(mem.get('notes'))}")
    pts = mem.get("trivia_points", 0)
    if pts > 0:
        lines.append(f"  * Puntuación en Trivial: {pts} pts")
    if lines:
        return "\n[MEMORIA PERSISTENTE DE ESTE USUARIO]:\n" + "\n".join(lines)
    return ""


# ==========================================
# NIVELES DE CAKEY BOT Y CÁLCULO DE XP
# ==========================================

_LIVE_LEVELS_CACHE = {}
_LIVE_LEVELS_CACHE_TIME = 0.0
_LIVE_LEVELS_TTL = 300.0
_LIVE_LEVELS_LOCK = asyncio.Lock()


async def get_live_levels_dict(guild: discord.Guild) -> dict:
    """Obtiene los niveles reales de Cakey Bot de cada usuario, consumiendo prioritariamente el Leaderboard Web oficial y manteniendo fallback a regex en #bots."""
    bs = _bs()
    cache_dict = getattr(bs, "_LIVE_LEVELS_CACHE", _LIVE_LEVELS_CACHE)
    cache_time = getattr(bs, "_LIVE_LEVELS_CACHE_TIME", _LIVE_LEVELS_CACHE_TIME)
    ttl = getattr(bs, "_LIVE_LEVELS_TTL", _LIVE_LEVELS_TTL)
    lock = getattr(bs, "_LIVE_LEVELS_LOCK", _LIVE_LEVELS_LOCK)

    if not guild:
        return {}
    now = time.time()
    # Fast-path sin lock si la caché está vigente
    if cache_time > 0 and (now - cache_time < ttl) and cache_dict:
        return dict(cache_dict)

    async with lock:
        now = time.time()
        cache_time = getattr(bs, "_LIVE_LEVELS_CACHE_TIME", _LIVE_LEVELS_CACHE_TIME)
        if cache_time > 0 and (now - cache_time < ttl) and cache_dict:
            return dict(cache_dict)

        # 1. Consumo prioritario: Leaderboard Web de Cakey Bot
        try:
            from modulos.cakey_client import get_cakey_leaderboard
            cakey_data = await get_cakey_leaderboard()
            if cakey_data:
                for uid, info in cakey_data.items():
                    lvl = info.get("level", 0)
                    if uid > 0 and lvl > 0:
                        cache_dict[uid] = lvl
                if hasattr(bs, "_LIVE_LEVELS_CACHE_TIME"):
                    bs._LIVE_LEVELS_CACHE_TIME = now
                else:
                    globals()["_LIVE_LEVELS_CACHE_TIME"] = now
                return dict(cache_dict)
        except Exception as e_cakey:
            _bot_log(f"Aviso lectura Cakey Web Leaderboard: {e_cakey}")

        # 2. Fallback: Escaneo del historial de #bots con regex
        bots_channel = discord.utils.find(lambda c: "bots" in c.name.lower(), guild.text_channels)
        if not bots_channel:
            return dict(cache_dict)
        levels = {}
        try:
            async for m in bots_channel.history(limit=120):
                if m.author.bot and m.content:
                    match = re.search(r"<@!?(\d+)>.*?nivel\s*(\d+)", m.content, re.IGNORECASE)
                    if match:
                        uid = int(match.group(1))
                        lvl = int(match.group(2))
                        if uid not in levels or lvl > levels[uid]:
                            levels[uid] = lvl
            for uid, lvl in levels.items():
                if uid not in cache_dict or lvl > cache_dict[uid]:
                    cache_dict[uid] = lvl
            if hasattr(bs, "_LIVE_LEVELS_CACHE_TIME"):
                bs._LIVE_LEVELS_CACHE_TIME = now
            else:
                globals()["_LIVE_LEVELS_CACHE_TIME"] = now
        except Exception as e:
            _bot_log(f"Aviso lectura niveles #bots: {e}")
            if cache_dict:
                return dict(cache_dict)
        return dict(cache_dict)


def calculate_xp_gap(start_lvl: int, target_lvl: int) -> str:
    """Calcula matemáticamente el XP exacto necesario entre dos niveles y desglosa por canales estándar y con boost."""
    if start_lvl < 0 or start_lvl >= target_lvl or target_lvl > 100:
        return ""
    total = sum(5 * (lvl ** 2) + 50 * lvl + 100 for lvl in range(start_lvl, target_lvl))
    msgs_base = round(total / 225)
    hours_voice_base = round(total / 1500, 1)

    msgs_boost_15 = round(total / (225 * 1.15))         # #recomendaciones-gaming (+15%)
    msgs_boost_10 = round(total / (225 * 1.10))         # #la-shit-de-todos-los-dias (+10%)
    hours_voice_boost = round(total / (1500 * 1.05), 1) # 🔊games🔊 (+5%)

    return (
        f"\n[CÁLCULO EXACTO DE XP]:\n"
        f"  * Subir de Nivel {start_lvl} a Nivel {target_lvl} requiere: **{total:,} XP**.\n"
        f"  * Tasa estándar (canales base):\n"
        f"    - Texto (~225 XP/msg): ~{msgs_base} mensajes activos (1 msg/min cooldown).\n"
        f"    - Voz (~1.500 XP/h): ~{hours_voice_base} horas en llamada.\n"
        f"  * Con Boost de servidor (canales bonificados):\n"
        f"    - En #recomendaciones-gaming (+15% XP): ~{msgs_boost_15} mensajes.\n"
        f"    - En #la-shit-de-todos-los-dias (+10% XP): ~{msgs_boost_10} mensajes.\n"
        f"    - En canal de voz 🔊games🔊 (+5% XP): ~{hours_voice_boost} horas."
    )


# ==========================================
# BÚSQUEDA WEB Y LECTURA DE CONTENIDOS
# ==========================================

TEXT_EXTENSIONS = {
    ".txt", ".py", ".js", ".ts", ".json", ".csv", ".md", ".cpp", ".c", ".h",
    ".java", ".html", ".css", ".xml", ".yaml", ".yml", ".sh", ".bat", ".ps1", ".log"
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def search_web_lite(query: str, max_results: int = 5) -> str:
    """Busca en internet en tiempo real y devuelve los mejores resultados con título y snippet."""
    if not query or len(query.strip()) < 3:
        return ""
    url = "https://html.duckduckgo.com/html/"
    data = urllib.parse.urlencode({"q": query}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"},
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            raw = r.read().decode("utf-8", errors="ignore")
            titles = re.findall(r'<h2 class="result__title">.*?<a[^>]*>(.*?)</a>', raw, re.DOTALL)
            snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', raw, re.DOTALL)
            results = []
            for i in range(min(max_results, len(titles))):
                t = html.unescape(re.sub(r'<[^>]+>', '', titles[i])).strip()
                s = html.unescape(re.sub(r'<[^>]+>', '', snippets[i])).strip() if i < len(snippets) else ""
                if t and s:
                    results.append(f"  * **{t}**: {s}")
            if results:
                return f"\n[BÚSQUEDA WEB EN VIVO PARA '{query}']:\n" + "\n".join(results)
    except Exception as e:
        print(f"Aviso búsqueda web: {e}")
    return ""


def build_search_query(current_text: str, raw_msgs: list) -> str:
    """Construye una query de búsqueda precisa usando el texto actual y el contexto conversacional si es breve."""
    bot = _get_bot()
    clean = re.sub(r"<@&?\d+>", "", current_text).strip()
    clean_no_punct = re.sub(r"[¿?¡!#]", "", clean).strip()
    clean_no_punct = re.sub(r"\b(busca|googlea|dime|sabes|asistente|porfa|oye)\b", "", clean_no_punct, flags=re.IGNORECASE).strip()
    words = clean_no_punct.split()

    if len(words) <= 7 and raw_msgs:
        for prev in reversed(raw_msgs):
            prev_content = re.sub(r"<@&?\d+>", "", prev.content).strip()
            title_match = re.search(r"\b([A-Z][a-zA-Z0-9_\-\s]{2,20})\b", prev_content)
            if title_match:
                topic = title_match.group(1).strip()
                if topic.lower() not in ["hola", "buenos", "gracias", "admin", "asistente"]:
                    return f"{topic} {clean_no_punct}".strip()
            if bot and prev.author != bot.user and len(prev_content) > 3:
                return f"{prev_content} {clean_no_punct}".strip()

    return clean_no_punct


# ==========================================
# LECTOR NATIVO DE GOOGLE DOCS / SHEETS Y WEB CON CACHÉ
# ==========================================

_URL_CONTENT_CACHE = {}  # {url: {"content": str, "expires_at": float}}
_URL_CACHE_TTL = 15 * 60  # 15 minutos en segundos


class GoogleDocInfo(dict):
    """Estructura enriquecida para metadatos de Google Docs/Sheets que se comporta como dict y como string."""
    def __str__(self):
        return self.get("export_url", "")

    def __eq__(self, other):
        if isinstance(other, str):
            return self.get("export_url") == other
        return super().__eq__(other)


def extract_google_docs_url(url: str) -> Optional[GoogleDocInfo]:
    """
    Detecta si una URL corresponde a Google Docs o Google Sheets y extrae metadatos y export URLs:
    - type: 'docs' o 'sheets'
    - id: identificador único del documento o spreadsheet
    - tab: id de pestaña/tab si existe en el query string
    - export_url: URL transformada para exportación directa (txt para docs, csv para sheets)
    - fallback_export_url: URL de exportación sin tab si la primera fallara
    """
    if not url or not isinstance(url, str) or "docs.google.com" not in url:
        return None

    # Google Docs
    doc_match = re.search(r"https?://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)", url)
    if doc_match:
        doc_id = doc_match.group(1)
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        tab = qs.get("tab", [None])[0]
        if tab:
            export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt&tab={tab}"
            fallback_export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        else:
            export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
            fallback_export_url = None
        return GoogleDocInfo({
            "type": "docs",
            "id": doc_id,
            "tab": tab,
            "export_url": export_url,
            "fallback_export_url": fallback_export_url,
        })

    # Google Sheets
    sheet_match = re.search(r"https?://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if sheet_match:
        sheet_id = sheet_match.group(1)
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        return GoogleDocInfo({
            "type": "sheets",
            "id": sheet_id,
            "tab": None,
            "export_url": export_url,
            "fallback_export_url": None,
        })

    return None


def fetch_url_content(url: str) -> str:
    """Descarga y limpia el texto legible de una página web, Google Docs o Google Sheets con caché en memoria."""
    now = time.time()
    # 1. Comprobar caché en memoria
    if url in _URL_CONTENT_CACHE:
        cached = _URL_CONTENT_CACHE[url]
        if now < cached.get("expires_at", 0):
            return cached.get("content", "")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }

    # 2. Si es Google Docs o Google Sheets
    gmeta = extract_google_docs_url(url)
    if gmeta:
        export_url = gmeta["export_url"]
        res_text = None

        # Intento 1: export_url (con tab si existe)
        try:
            req = urllib.request.Request(export_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_text = resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404):
                content = f"\n[AVISO GOOGLE DOCS: No se pudo leer el documento ({url}) porque es privado o no tiene permisos de lectura pública. NO inventes su contenido.]\n"
                _URL_CONTENT_CACHE[url] = {"content": content, "expires_at": now + _URL_CACHE_TTL}
                return content
            elif gmeta.get("fallback_export_url"):
                try:
                    req_fb = urllib.request.Request(gmeta["fallback_export_url"], headers=headers)
                    with urllib.request.urlopen(req_fb, timeout=10) as resp_fb:
                        res_text = resp_fb.read().decode("utf-8", errors="ignore")
                except urllib.error.HTTPError as e_fb:
                    if e_fb.code in (401, 403, 404):
                        content = f"\n[AVISO GOOGLE DOCS: No se pudo leer el documento ({url}) porque es privado o no tiene permisos de lectura pública. NO inventes su contenido.]\n"
                        _URL_CONTENT_CACHE[url] = {"content": content, "expires_at": now + _URL_CACHE_TTL}
                        return content
                except Exception:
                    pass
        except Exception:
            if gmeta.get("fallback_export_url"):
                try:
                    req_fb = urllib.request.Request(gmeta["fallback_export_url"], headers=headers)
                    with urllib.request.urlopen(req_fb, timeout=10) as resp_fb:
                        res_text = resp_fb.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass

        if res_text is not None:
            clean_text = res_text.strip()
            if len(clean_text) > 12000:
                clean_text = clean_text[:12000] + "\n... [Contenido truncado a 12.000 caracteres]"

            title_id = f"Google {'Docs' if gmeta['type'] == 'docs' else 'Sheets'} {gmeta['id']}"
            content = f"\n[DOCUMENTO DE GOOGLE DOCS LEÍDO CON ÉXITO: '{title_id}' ({url})]:\n{clean_text}\n"
            _URL_CONTENT_CACHE[url] = {"content": content, "expires_at": now + _URL_CACHE_TTL}
            return content
        else:
            content = f"\n[AVISO GOOGLE DOCS: No se pudo leer el documento ({url}) porque es privado o no tiene permisos de lectura pública. NO inventes su contenido.]\n"
            _URL_CONTENT_CACHE[url] = {"content": content, "expires_at": now + _URL_CACHE_TTL}
            return content

    # 3. Páginas web estándar
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            ctype = resp.headers.get_content_type()
            if "html" not in ctype and "text" not in ctype:
                res = f"[Recurso binario: {ctype}]"
                _URL_CONTENT_CACHE[url] = {"content": res, "expires_at": now + _URL_CACHE_TTL}
                return res
            raw = resp.read().decode("utf-8", errors="ignore")
            title_match = re.search(r"<title>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else "Sin título"
            clean = re.sub(r"<(script|style|svg|noscript).*?>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r"<[^>]+>", " ", clean)
            clean = html.unescape(clean)
            clean = re.sub(r"\s+", " ", clean).strip()
            res = f"\n[Página Web leída: '{title}' ({url})]:\n{clean[:3000]}"
            _URL_CONTENT_CACHE[url] = {"content": res, "expires_at": now + _URL_CACHE_TTL}
            return res
    except Exception as e:
        return f"\n[No se pudo acceder a {url}: {e}]"


async def extract_attachments_parts(msg: discord.Message) -> list:
    """Extrae imágenes, PDFs y archivos de texto convirtiéndolos en piezas para Gemini."""
    parts = []
    attachments = list(msg.attachments)
    if msg.reference and getattr(msg.reference.resolved, "attachments", None):
        attachments.extend(msg.reference.resolved.attachments)

    for att in attachments[:3]:
        filename = att.filename.lower()
        ctype = att.content_type or ""
        ext = os.path.splitext(filename)[1]

        try:
            raw_bytes = await att.read()
            if any(ctype.startswith(x) for x in ["image/png", "image/jpeg", "image/webp", "image/gif"]) or ext in IMAGE_EXTENSIONS:
                mime = ctype if ctype.startswith("image/") else ("image/png" if ext == ".png" else "image/jpeg")
                b64 = base64.b64encode(raw_bytes).decode("utf-8")
                parts.append({
                    "inlineData": {
                        "mimeType": mime,
                        "data": b64,
                    }
                })
            elif ctype == "application/pdf" or ext == ".pdf":
                b64 = base64.b64encode(raw_bytes).decode("utf-8")
                parts.append({
                    "inlineData": {
                        "mimeType": "application/pdf",
                        "data": b64,
                    }
                })
            elif ext in TEXT_EXTENSIONS or ctype.startswith("text/"):
                text_content = raw_bytes.decode("utf-8", errors="replace")[:8000]
                parts.append({
                    "text": f"\n[Archivo adjunto '{att.filename}']:\n```\n{text_content}\n```"
                })
        except Exception as e:
            print(f"Error procesando adjunto {att.filename}: {e}")

    return parts


# ==========================================
# CONTEXTO DEL SERVIDOR Y DOSSIERS
# ==========================================

def get_live_voice_radar(guild: discord.Guild, author: discord.Member = None) -> str:
    """Extrae un radar en tiempo real de todos los canales de voz del servidor con detalles de miembros y estados."""
    if not guild:
        return ""
    lines = []
    total_in_voice = 0
    connected_member_ids = set()

    for vc in guild.voice_channels:
        if vc.members:
            total_in_voice += len(vc.members)
            member_details = []
            for m in vc.members:
                connected_member_ids.add(m.id)
                state = m.voice
                flags = []
                if m.bot:
                    flags.append("Bot")
                if state:
                    if state.self_mute or state.mute:
                        flags.append("Silenciado/Mute")
                    else:
                        flags.append("Micro activo/Hablando")
                    if state.self_deaf or state.deaf:
                        flags.append("Ensordecido")
                    if state.self_stream:
                        flags.append("Compartiendo pantalla")
                    if state.self_video:
                        flags.append("Cámara encendida")
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                tag = f"@{m.name}"
                member_details.append(f"    - {m.display_name} ({tag}){flag_str}")

            lines.append(f"  * #{vc.name} ({len(vc.members)} personas en sala):\n" + "\n".join(member_details))

    key_members_status = []
    joselito_member = guild.get_member(857923274771136522)
    if joselito_member and joselito_member.id not in connected_member_ids:
        key_members_status.append("    - Joselito (@joselito3499): FUERA DE LLAMADA (Desconectado de salas de voz)")

    ivan_member = guild.get_member(1208551025578082367)
    if ivan_member and ivan_member.id not in connected_member_ids:
        key_members_status.append("    - Iván (@racerwasp): FUERA DE LLAMADA (Desconectado de salas de voz)")

    author_status = ""
    if author:
        if getattr(author, "voice", None) and author.voice.channel:
            vc = author.voice.channel
            author_status = f"\n  * Autor del mensaje ({author.display_name}): CONECTADO en la sala de voz #{vc.name}"
        else:
            author_status = f"\n  * Autor del mensaje ({author.display_name}): FUERA DE LLAMADA (No está en ningún canal de voz)"

    out = f"\n[RADAR EN VIVO DE CANALES DE VOZ ({total_in_voice} conectados)]:\n"
    if lines:
        out += "\n".join(lines)
    else:
        out += "  * No hay nadie conectado a ninguna sala de voz actualmente."

    if key_members_status:
        out += "\n  * Estado de miembros destacados ausentes:\n" + "\n".join(key_members_status)
    out += author_status
    return out


def get_live_members_ctx(guild: discord.Guild, levels: dict) -> str:
    """Genera un snapshot en tiempo real de los miembros del servidor con sus roles y niveles reales."""
    if not guild:
        return ""
    lines = []
    try:
        for member in guild.members:
            if member.bot:
                continue
            roles = [r.name for r in member.roles if r.name != "@everyone"]
            nick = member.nick or member.display_name
            username = member.name
            lvl_str = f" [Nivel {levels[member.id]}]" if member.id in levels else ""
            role_str = ", ".join(roles) if roles else "Sin roles"
            lines.append(f"  - {nick} (@{username}){lvl_str} | Roles: {role_str}")
        if lines:
            return "\n[MIEMBROS ACTUALES DEL SERVIDOR (datos en vivo con niveles de Cakey Bot)]:\n" + "\n".join(lines[:35])
    except Exception as e:
        return f"\n[Error obteniendo miembros: {e}]"
    return ""


def get_member_dossier(member: discord.Member, levels: dict) -> str:
    """Genera la ficha técnica en profundidad de un miembro."""
    created = member.created_at.strftime("%d/%m/%Y")
    joined = member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "Desconocida"
    top_role = member.top_role.name if member.top_role else "Ninguno"
    roles = [r.name for r in member.roles if r.name != "@everyone"]
    voice = f"Conectado en voz en #{member.voice.channel.name}" if getattr(member, "voice", None) and member.voice.channel else "Fuera de llamada"
    lvl_val = f"Nivel {levels[member.id]} (Cakey Bot)" if member.id in levels else "No registrado recientemente en #bots"
    avatar_url = str(member.display_avatar.url)
    return (
        f"\n[FICHA TÉCNICA DE {member.display_name} (@{member.name})]:\n"
        f"  * Nick: {member.display_name} | Usuario: @{member.name}\n"
        f"  * Foto de perfil / Avatar URL: {avatar_url}\n"
        f"  * Nivel Cakey Bot: {lvl_val}\n"
        f"  * Cuenta creada en Discord: {created}\n"
        f"  * Fecha de unión al servidor: {joined}\n"
        f"  * Rol más alto: {top_role}\n"
        f"  * Roles totales ({len(roles)}): {', '.join(roles) or 'Sin roles'}\n"
        f"  * Estado actual: {voice}"
    )


def normalize_channel_name(name: str) -> str:
    """Normaliza el nombre de un canal eliminando emojis, tildes, caracteres especiales y pasando a minúsculas."""
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    no_accents = "".join([c for c in nfkd if not unicodedata.combining(c)])
    cleaned = re.sub(r"[\s]+", "-", no_accents.lower())
    cleaned = re.sub(r"[^\w\-]", "", cleaned)
    return re.sub(r"-+", "-", cleaned).strip("-_")


def find_channel_by_name(guild: Any, query: str) -> Optional[Any]:
    """Busca un canal de texto en el servidor normalizando nombres sin emojis ni símbolos."""
    if not guild or not query:
        return None
    q_norm = normalize_channel_name(query)
    if not q_norm:
        return None

    text_channels = getattr(guild, "text_channels", [])

    # 1. Coincidencia exacta normalizada
    for ch in text_channels:
        if normalize_channel_name(ch.name) == q_norm:
            return ch

    # 2. Coincidencia si q_norm contiene el nombre normalizado del canal (ej: "fijado en cultura" contiene "cultura")
    sorted_channels = sorted(text_channels, key=lambda c: len(normalize_channel_name(c.name)), reverse=True)
    for ch in sorted_channels:
        c_norm = normalize_channel_name(ch.name)
        if len(c_norm) >= 3 and c_norm in q_norm:
            return ch

    # 3. Coincidencia si el nombre del canal contiene q_norm (ej: query="tribunal" -> "el-tribunal-gaming")
    for ch in sorted_channels:
        c_norm = normalize_channel_name(ch.name)
        if len(q_norm) >= 3 and q_norm in c_norm:
            return ch

    return None


async def get_pins_context(channel: discord.TextChannel, query: str = "", guild: Optional[discord.Guild] = None) -> str:
    """Extrae los mensajes anclados del canal (o del canal referenciado en la consulta) para consultas clave."""
    try:
        target_channel = channel
        g = guild or getattr(channel, "guild", None)
        if g and query:
            # Si el usuario en cualquier canal pregunta por pins de otro canal (ej: "fijado en cultura", "tier list de cultura", "normas fijadas")
            found = find_channel_by_name(g, query)
            if found:
                target_channel = found

        if not target_channel:
            return ""

        pins = await target_channel.pins()
        if not pins:
            return ""

        lines = []
        doc_extra_ctx = ""
        user_asks_content = any(w in query.lower() for w in [
            "top", "tier", "manhwa", "manga", "lista", "que pone", "qué pone",
            "resumen", "link", "doc", "documento", "recomienda", "recomendacion",
            "recomendación", "norma", "regla"
        ])

        for p in pins[:4]:
            content = p.clean_content.replace("\n", " ")
            lines.append(f"  * [{p.author.display_name}]: {content[:300]}")

            # Si un pin contiene un enlace a Google Docs o URL externa y el usuario pide esa lista/tier list
            if user_asks_content or "docs.google.com" in p.clean_content:
                urls = re.findall(r"https?://[^\s<>\"']+", p.clean_content)
                for u in urls[:2]:
                    fetched = await asyncio.to_thread(fetch_url_content, u)
                    if fetched and "No se pudo acceder" not in fetched:
                        doc_extra_ctx += f"\n[DOCUMENTO/ENLACE VINCULADO AL PIN EN #{target_channel.name} ({u})]:\n{fetched}\n"

        base_pins = f"\n[MENSAJES FIJADOS/PINNED EN #{target_channel.name}]:\n" + "\n".join(lines)
        return f"{base_pins}{doc_extra_ctx}"
    except Exception as e:
        print(f"Aviso obteniendo pins context: {e}")
        return ""


# ==========================================
# EXTRACCIÓN UNIVERSAL DE TEXTO, EMBEDS Y COMPONENTES
# ==========================================

def _extract_components_text(comps: Any) -> list:
    """Extrae texto recursivamente de componentes de Discord (ActionRows, Buttons, TextDisplay, Containers, etc.)."""
    parts = []
    if not comps:
        return parts
    if isinstance(comps, (list, tuple)):
        for c in comps:
            parts.extend(_extract_components_text(c))
        return parts

    if isinstance(comps, dict):
        for k in ("content", "label", "placeholder", "description", "value", "title"):
            val = comps.get(k)
            if val and isinstance(val, str) and val.strip():
                parts.append(val.strip())
        if "components" in comps:
            parts.extend(_extract_components_text(comps["components"]))
        if "children" in comps:
            parts.extend(_extract_components_text(comps["children"]))
        return parts

    for attr in ("content", "label", "placeholder", "description", "value", "title"):
        val = getattr(comps, attr, None)
        if val and isinstance(val, str) and val.strip():
            parts.append(val.strip())

    for child_attr in ("children", "components"):
        sub = getattr(comps, child_attr, None)
        if sub:
            parts.extend(_extract_components_text(sub))

    return parts


def _extract_embed_text(e: Any) -> str:
    """Extrae y formatea en una cadena compacta el contenido de un Discord Embed."""
    if not e:
        return ""

    if isinstance(e, dict):
        title = (e.get("title") or "").strip()
        desc = (e.get("description") or "").strip()
        author_info = e.get("author") or {}
        author = author_info.get("name", "").strip() if isinstance(author_info, dict) else ""
        fields = []
        for f in (e.get("fields") or []):
            if isinstance(f, dict):
                fn = (f.get("name") or "").strip()
                fv = (f.get("value") or "").strip()
                if fn or fv:
                    fields.append(f"{fn}: {fv}" if fn else fv)
        footer_info = e.get("footer") or {}
        footer = footer_info.get("text", "").strip() if isinstance(footer_info, dict) else ""
    else:
        title = (getattr(e, "title", "") or "").strip()
        desc = (getattr(e, "description", "") or "").strip()
        author = ""
        e_author = getattr(e, "author", None)
        if e_author:
            author = (getattr(e_author, "name", "") or "").strip()
        fields = []
        e_fields = getattr(e, "fields", []) or []
        for f in e_fields:
            if isinstance(f, dict):
                fn = (f.get("name") or "").strip()
                fv = (f.get("value") or "").strip()
            else:
                fn = (getattr(f, "name", "") or "").strip()
                fv = (getattr(f, "value", "") or "").strip()
            if fn or fv:
                fields.append(f"{fn}: {fv}" if fn else fv)
        footer = ""
        e_footer = getattr(e, "footer", None)
        if e_footer:
            footer = (getattr(e_footer, "text", "") or "").strip()

    items = []
    if author:
        items.append(f"Autor: {author}")
    if title:
        items.append(title)
    if desc:
        items.append(desc)
    if fields:
        items.append(" | ".join(fields))
    if footer:
        items.append(footer)

    if not items:
        return ""
    return "[Embed: " + " | ".join(items) + "]"


def extract_discord_message_text(msg: Any, max_len: int = 500) -> str:
    """
    Extrae todo el contenido textual legible de un mensaje de Discord:
    texto principal, componentes interactivos (TextDisplay, Container, Botones),
    Embeds formateados ([Embed: ...]) y nombres de archivos adjuntos.
    Soporta objetos discord.Message y diccionarios o stubs de test.
    """
    if not msg:
        return ""

    # 1. Contenido base
    text_content = ""
    if isinstance(msg, dict):
        text_content = msg.get("clean_content") or msg.get("content") or ""
    else:
        text_content = getattr(msg, "clean_content", None) or getattr(msg, "content", "") or ""
    text_content = str(text_content).strip()

    # 2. Componentes (ActionRows, Containers, TextDisplay, Botones)
    comps = msg.get("components", []) if isinstance(msg, dict) else getattr(msg, "components", [])
    comp_parts = _extract_components_text(comps)
    comp_text = " ".join([p for p in comp_parts if p]).strip()

    # 3. Embeds
    embeds = msg.get("embeds", []) if isinstance(msg, dict) else getattr(msg, "embeds", [])
    embed_parts = []
    for emb in (embeds or []):
        emb_txt = _extract_embed_text(emb)
        if emb_txt:
            embed_parts.append(emb_txt)
    embeds_text = " ".join(embed_parts).strip()

    # 4. Attachments
    attachments = msg.get("attachments", []) if isinstance(msg, dict) else getattr(msg, "attachments", [])
    att_parts = []
    for a in (attachments or []):
        fn = a.get("filename", "") if isinstance(a, dict) else getattr(a, "filename", "")
        if fn:
            att_parts.append(f"[Archivo adjunto: {fn}]")
    att_text = " ".join(att_parts).strip()

    # Combinación de fragmentos
    pieces = []
    if text_content:
        pieces.append(text_content)
    if comp_text:
        pieces.append(f"[Componentes: {comp_text}]")
    if embeds_text:
        pieces.append(embeds_text)
    if att_text:
        pieces.append(att_text)

    combined = " ".join(pieces).replace("\n", " ").strip()
    import re
    combined = re.sub(r"\s+", " ", combined)
    if max_len and len(combined) > max_len:
        combined = combined[:max_len].rstrip() + "..."
    return combined


# ==========================================
# PIPELINE CONVERSACIONAL Y ENRUTADOR SEGURO
# ==========================================

user_cooldowns = {}
COOLDOWN_SECONDS = 3


async def _handle_message_safe(message: discord.Message):
    bs = _bs()
    bot = _get_bot()
    if not bot or not bot.user:
        return

    from modulos.voz import (
        ensure_voice_connection,
        is_voice_manually_disconnected,
        set_voice_manually_disconnected,
        play_audio_in_voice,
        generate_speech_audio,
        clean_text_for_tts,
    )
    from modulos.graficos import (
        extract_action_block,
        generate_image_flux,
        render_math_image,
        render_chart_image,
        render_diagram_image,
        render_code_card_image,
        enhance_image_prompt,
        sanitize_discord_math_text,
        ImageActionView,
    )
    from modulos.juegos import (
        get_tribunal_query_ctx,
        get_steam_query_ctx,
    )

    is_mentioned = (
        bot.user in message.mentions
        or any(r.id == 1549789822191935561 or r.name.lower() == "asistente" for r in message.role_mentions)
        or (message.reference and getattr(message.reference.resolved, "author", None) == bot.user)
    )

    if not is_mentioned:
        return

    now = time.time()
    uid = message.author.id

    # Anti-spam cooldown
    last_time = user_cooldowns.get(uid, 0)
    if now - last_time < COOLDOWN_SECONDS:
        await message.add_reaction("\u23f3")
        return
    user_cooldowns[uid] = now

    async with message.channel.typing():
        # 1. Resolver menciones de otros miembros a sus nombres reales antes de limpiar
        resolved_text = message.content
        for m in message.mentions:
            if m != bot.user:
                resolved_text = re.sub(f"<@!?{m.id}>", m.display_name, resolved_text)
        for r in message.role_mentions:
            if r.id != 1549789822191935561 and r.name.lower() != "asistente":
                resolved_text = re.sub(f"<@&{r.id}>", f"@{r.name}", resolved_text)

        # Limpiar mención al bot o al rol asistente
        clean_text = re.sub(f"<@!?{bot.user.id}>", "", resolved_text)
        clean_text = re.sub(r"<@&1549789822191935561>", "", clean_text).strip()
        clean_text = re.sub(r"<@&?\d+>", "", clean_text).strip()
        lowered = clean_text.lower()

        # Detección de acciones conversacionales directas en llamadas de voz
        join_voice_phrases = [
            "únete a la llamada", "unete a la llamada", "entra a la llamada", "entra en la llamada",
            "entra a llamada", "entra en llamada", "ven a la llamada", "ven a llamada",
            "conéctate a la llamada", "conectate a la llamada", "conéctate a llamada", "conectate a llamada",
            "conéctate a voz", "conectate a voz", "conéctate al canal de voz", "conectate al canal de voz",
            "únete al canal de voz", "unete al canal de voz", "entra al canal de voz", "entra en el canal de voz",
            "métete al canal de voz", "metete al canal de voz", "métete en el canal de voz", "metete en el canal de voz",
            "únete a la sala de voz", "unete a la sala de voz", "entra a la sala de voz", "entra en la sala de voz",
            "únete a la sala", "unete a la sala", "entra a la sala", "entra en la sala",
            "métete a la sala", "metete a la sala", "métete en la sala", "metete en la sala",
            "ven a voz", "entra a voz", "ven al canal de voz", "métete a la llamada", "metete a la llamada",
            "métete en la llamada", "metete en la llamada", "únete a voz", "unete a voz"
        ]
        if any(p in lowered for p in join_voice_phrases):
            vch = getattr(message.author, "voice", None) and message.author.voice.channel
            if not vch and message.guild:
                for c in message.guild.voice_channels:
                    if any(m.id == message.author.id for m in c.members):
                        vch = c
                        break

            if vch:
                try:
                    await ensure_voice_connection(vch)
                    await message.reply(f"🎙️ ¡Me he conectado a **#{vch.name}** en modo **Gemini Live**! Háblame directamente por el micro diciendo *'Asistente...'*, te responderé por voz en tiempo real.")
                    return
                except Exception as e:
                    await message.reply(f"❌ No pude conectarme a la sala de voz: {e}")
                    return
            else:
                await message.reply("❌ Debes estar conectado a una sala de voz para que me una a tu llamada.")
                return

        disconnect_phrases = [
            "sal de la llamada", "desconéctate de la llamada", "desconectate de la llamada",
            "salte de la llamada", "abandona la llamada", "sal de voz", "salte de voz",
            "sal del canal", "salte del canal", "vete de la llamada", "vete de voz",
            "vete del canal", "desconéctate de voz", "desconectate de voz",
            "desconéctate del canal", "desconectate del canal"
        ]
        if any(p in lowered for p in disconnect_phrases):
            vc = message.guild.voice_client if message.guild else None
            if vc and vc.is_connected():
                v_name = vc.channel.name if vc.channel else "la sala"
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
                set_voice_manually_disconnected(message.guild.id)
                await vc.disconnect(force=True)
                await message.reply(f"🔌 Me he desconectado de **#{v_name}** y detenido Gemini Live. *(No volveré solo hasta que me pidas unirme.)*")
                return
            else:
                await message.reply("ℹ️ No estoy en ninguna llamada de voz ahora mismo.")
                return

        if any(p in lowered for p in ["para el audio", "para la voz", "para de hablar", "cállate en la llamada", "callate en la llamada", "silencio en la llamada"]):
            vc = message.guild.voice_client if message.guild else None
            if vc and vc.is_connected() and vc.is_playing():
                if hasattr(vc, "stop_playing"):
                    vc.stop_playing()
                else:
                    vc.stop()
                await message.reply("⏹️ Audio detenido.")
                return

        say_match = re.search(r"(?:di en la llamada|di por voz|habla en la llamada|di en voz|suelta por voz)\s*[:,\-]?\s*(.+)", clean_text, re.IGNORECASE)
        if say_match:
            phrase = say_match.group(1).strip()
            vch = getattr(message.author, "voice", None) and message.author.voice.channel
            if not vch and message.guild:
                for c in message.guild.voice_channels:
                    if any(m.id == message.author.id for m in c.members):
                        vch = c
                        break

            if not vch:
                await message.reply("❌ Para que hable en la llamada tienes que estar conectado a una sala de voz.")
                return
            try:
                audio_file = await generate_speech_audio(phrase, "alvaro")
                vc = await ensure_voice_connection(vch)
                play_audio_in_voice(vc, audio_file)
                await message.reply(f"🎙️ Dicho en **#{vch.name}**:\n> *\"{phrase[:250]}\"*")
                return
            except Exception as e:
                await message.reply(f"❌ Error al reproducir audio: {e}")
                return

        # 1. Historial amplio del canal (últimos 35 mensajes para contexto completo)
        raw_msgs = []
        try:
            async for prev_msg in message.channel.history(limit=35, before=message):
                if prev_msg.author.bot and prev_msg.author != bot.user:
                    if any("queue" in str(getattr(e, "to_dict", lambda: e)()).lower() for e in getattr(prev_msg, "embeds", [])):
                        continue
                msg_txt = extract_discord_message_text(prev_msg, max_len=400)
                if msg_txt:
                    raw_msgs.append(prev_msg)
        except Exception as e:
            print(f"Aviso lectura historial canal: {e}")

        raw_msgs.reverse()

        # Transcripción estructurada reciente del canal
        recent_lines = []
        for m in raw_msgs[-20:]:
            m_author = getattr(m.author, "display_name", "Usuario")
            m_tag = f"@{getattr(m.author, 'name', 'usuario')}"
            is_bot_author = getattr(m.author, "bot", False)
            bot_tag = " [BOT]" if (is_bot_author and m.author != bot.user) else ""
            m_text = extract_discord_message_text(m, max_len=300)
            if not m_text:
                continue
            if m.author == bot.user:
                bot_self_name = BOT_PERSONALITIES.get(ACTIVE_PERSONALITY, {}).get("name", "Asistente")
                recent_lines.append(f"  * [{bot_self_name} (Tú)]: {m_text[:250]}")
            else:
                recent_lines.append(f"  * [{m_author}{bot_tag} ({m_tag})]: {m_text[:250]}")
        recent_channel_ctx = ""
        if recent_lines:
            recent_channel_ctx = f"\n[CONVERSACIÓN RECIENTE EN #{message.channel.name} (últimos mensajes del grupo)]:\n" + "\n".join(recent_lines)

        # 2. Extraer niveles reales en directo desde el canal #bots
        live_levels = {}
        if message.guild:
            live_levels = await get_live_levels_dict(message.guild)

        # 3. Detectar si hay URLs directas para leer en el mensaje actual
        urls = re.findall(r"https?://[^\s<>\"']+", clean_text)
        url_context = ""
        if urls:
            for u in urls[:2]:
                fetched = await asyncio.to_thread(fetch_url_content, u)
                url_context += fetched

        # Persistencia de enlaces en historial reciente (multi-turno)
        recent_urls = []
        for rm in raw_msgs[-8:]:
            rm_text = getattr(rm, "content", "") or ""
            for emb in getattr(rm, "embeds", []):
                if getattr(emb, "url", None):
                    rm_text += f" {emb.url}"
                if getattr(emb, "description", None):
                    rm_text += f" {emb.description}"
            for found_u in re.findall(r"https?://[^\s<>\"']+", rm_text):
                if found_u not in urls and found_u not in recent_urls:
                    recent_urls.append(found_u)

        referential_keywords = [
            "top", "tier", "manhwa", "manga", "lista", "qué pone", "que pone",
            "resumen", "link", "doc", "documento", "opinas", "analiza", "enlace",
            "hoja", "sheet", "drive", "primero", "puesto", "ranking", "orden",
            "lee", "leído", "leido", "visto", "pasa", "mira"
        ]
        is_referential = any(k in lowered for k in referential_keywords) or "?" in clean_text or "¿" in clean_text

        if recent_urls and (is_referential or not url_context):
            sorted_recent = sorted(recent_urls, key=lambda x: 0 if "docs.google.com" in x else 1)
            for u in sorted_recent[:2]:
                content = await asyncio.to_thread(fetch_url_content, u)
                if content and "No se pudo acceder" not in content:
                    url_context += f"\n[DOCUMENTO/ENLACE COMPARTIDO RECIENTEMENTE EN LA CONVERSACIÓN ({u})]:\n{content}\n"

        # 4. Búsqueda Web en Vivo (Context-Aware)
        web_search_context = ""
        server_internal_kw = ["rol", "roles", "casino", "porros", "pendejo", "norma", "tribunal", "admin", "quien esta en voz", "llamada", "nivel", "xp"]
        is_internal_query = any(k in lowered for k in server_internal_kw) and not any(k in lowered for k in ["peli", "anime", "manga", "juego", "noticia", "precio", "estreno", "temporada"])

        search_intent_keywords = [
            "peli", "pelicula", "película", "anime", "manga", "manhwa", "serie", "juego", "temporada",
            "season", "estreno", "lanzamiento", "precio", "noticia", "novedad", "parche", "actualización",
            "cuando sale", "cuándo sale", "donde ver", "dónde ver", "quien gano", "quién ganó", "historia",
            "lore", "capitulo", "capítulo", "t1", "t2", "t3", "t4", "segunda", "tercera", "movie", "beyond", "shadow"
        ]
        should_search = (
            any(kw in lowered for kw in search_intent_keywords)
            or (not is_internal_query and ("?" in clean_text or "¿" in clean_text or "busca" in lowered or "googlea" in lowered))
            or (not is_internal_query and len(clean_text.split()) >= 3 and not url_context and not any(kw in lowered for kw in ["dibuja", "imagen", "foto", "crea"]))
        )

        if should_search:
            search_query = build_search_query(clean_text, raw_msgs)
            if len(search_query) >= 3:
                web_search_context = await asyncio.to_thread(search_web_lite, search_query)

        # 5. Lector de mensajes fijados (pins) - Selectivo para ahorrar tokens (local o transversal)
        pins_context = ""
        pins_keywords = ["fijado", "pinned", "pins", "anclado", "destacado", "top", "tier", "lista", "normas", "reglas"]
        user_asks_channel_pins = any(w in lowered for w in pins_keywords) or (
            message.guild and any(normalize_channel_name(c.name) in lowered for c in getattr(message.guild, "text_channels", []) if len(normalize_channel_name(c.name)) >= 4 and any(w in lowered for w in ["top", "tier", "manhwa", "manga", "lista", "norma", "fijado", "pin"]))
        )
        if user_asks_channel_pins or (message.channel and "cultura" in normalize_channel_name(message.channel.name) and any(w in lowered for w in ["top", "recomendacion", "recomendación", "recomienda", "manhwa", "manga", "lista", "que leo", "qué leo"])):
            pins_context = await get_pins_context(message.channel, query=clean_text, guild=message.guild)

        # 6. Ficha técnica de miembros si se menciona a alguien
        dossier_context = ""
        target_members = [m for m in message.mentions if m != bot.user]
        if target_members:
            for tm in target_members[:2]:
                dossier_context += get_member_dossier(tm, live_levels)
        else:
            if message.guild:
                for m in message.guild.members:
                    if not m.bot and (m.name.lower() in lowered or (m.nick and m.nick.lower() in lowered)):
                        if len(m.name) > 3 or (m.nick and len(m.nick) > 3):
                            dossier_context += get_member_dossier(m, live_levels)
                            break

        # 7. Calculadora matemática de XP
        xp_calc_context = ""
        author_lvl = live_levels.get(message.author.id, 1)
        xp_match = re.search(r"nivel\s+(\d+)\s+(?:al?|hasta)\s+(?:nivel\s+)?(\d+)", lowered)
        if xp_match:
            s_lvl = int(xp_match.group(1))
            t_lvl = int(xp_match.group(2))
            xp_calc_context = calculate_xp_gap(s_lvl, t_lvl)
        elif any(p in lowered for p in ["cuanto me falta", "cuánto me falta", "cuanta xp", "cuánta xp", "cuanta experiencia", "cuánta experiencia", "cuanto me queda", "cuánto me queda", "cuanto necesito", "cuánto necesito", "xp para", "experiencia para"]):
            target_match = re.search(r"(?:para|al?)\s+(?:nivel\s+)?(\d+)", lowered)
            if target_match:
                t_lvl = int(target_match.group(1))
                if t_lvl > author_lvl:
                    xp_calc_context = calculate_xp_gap(author_lvl, t_lvl)

        # Extraer imágenes, PDFs o archivos de código adjuntos
        attachment_parts = await extract_attachments_parts(message)

        # Montar turnos cronológicos para Gemini
        turns = []
        for m in raw_msgs[-12:]:
            raw_extracted = extract_discord_message_text(m, max_len=400)
            m_text = re.sub(r"<@&?\d+>", "", raw_extracted).strip()
            if not m_text:
                continue
            is_bot = (m.author == bot.user)
            role = "model" if is_bot else "user"
            author_label = getattr(m.author, "display_name", "Usuario")
            if getattr(m.author, "bot", False) and not is_bot:
                author_label += " [BOT]"
            prefix = "" if is_bot else f"{author_label}: "
            formatted = f"{prefix}{m_text}"

            if turns and turns[-1]["role"] == role:
                turns[-1]["parts"][0]["text"] += f"\n{formatted}"
            else:
                turns.append({
                    "role": role,
                    "parts": [{"text": formatted}]
                })

        # Datos en tiempo real del autor
        author_roles = [r.name for r in getattr(message.author, "roles", []) if r.name != "@everyone"]
        author_voice = ""
        if getattr(message.author, "voice", None) and message.author.voice.channel:
            author_voice = f" (en llamada de voz en #{message.author.voice.channel.name})"
        author_avatar = str(message.author.display_avatar.url)
        author_lvl_info = f" | Nivel Cakey Bot: Nivel {author_lvl}" if message.author.id in live_levels else ""
        user_live_ctx = f"\n[DATOS DEL USUARIO ACTUAL]: {message.author.display_name} (@{message.author.name}){author_lvl_info} | Avatar: {author_avatar} | Roles: {', '.join(author_roles) or 'Sin roles'}{author_voice}"

        # Estado en vivo del servidor y Fecha/Hora exacta en España
        spain_time_str = get_spain_now_str()
        server_live_ctx = ""
        voice_radar_ctx = ""
        if message.guild:
            server_live_ctx = f"\n[ESTADO EN VIVO DEL SERVIDOR]: Fecha y hora actual: {spain_time_str} | Servidor: {message.guild.name} ({message.guild.member_count} miembros) | Canal: #{message.channel.name}"
            voice_radar_ctx = get_live_voice_radar(message.guild, message.author)

        # Detección de peticiones de música en chats de voz o texto
        music_ctx = ""
        music_triggers = ["escuchar ", "pon la canción", "pon música", "ponte la de", "reproduce ", "toca la de", "play ", "cancion", "canción"]
        is_voice_chat = getattr(message.channel, "type", None) == discord.ChannelType.voice
        if any(t in lowered for t in music_triggers) or (is_voice_chat and any(w in lowered for w in ["musica", "música", "cakey", "tema", "escuchar"])):
            clean_song = re.sub(r"\b(asistente|escuchar|pon|la|cancion|canción|musica|música|de|porfa|oye|reproduce|toca|play)\b", "", lowered).strip()
            yt_link = ""
            if len(clean_song) >= 3:
                encoded_song = urllib.parse.quote(clean_song)
                yt_link = f"https://www.youtube.com/results?search_query={encoded_song}"
            music_ctx = (
                f"\n[ASISTENCIA MUSICAL EN SALA DE VOZ]:\n"
                f"  * Bot de música oficial en el servidor: Cakey Bot.\n"
                f"  * Comando para reproducir música con Cakey Bot en la llamada de voz: `/play song: <nombre>` o `/play search: <nombre>`.\n"
                f"  * Si Cakey Bot está atascado con spam de 'queue empty' o cola vacía, se desatasca usando `/skip`, `/stop` o metiendo un nuevo `/play`.\n"
                + (f"  * Enlace directo a YouTube para el usuario: {yt_link}\n" if yt_link else "")
            )

        # Snapshot de miembros reales del servidor (con roles y niveles)
        members_ctx = ""
        members_keywords = ["quien", "quién", "miembros", "roles", "rol", "staff", "admin", "gente", "usuarios", "lista de", "cuantos somos", "cuántos somos", "quienes estan", "quiénes están"]
        if any(k in lowered for k in members_keywords):
            members_ctx = get_live_members_ctx(message.guild, live_levels)

        # Lectura dinámica de canales si se mencionan
        channel_lookup_ctx = ""
        if message.guild:
            mentioned_cids = re.findall(r"<#(\d+)>", message.content)
            channel_keywords = {
                "anuncio": "anuncios",
                "norma": "normas",
                "cultura": "cultura",
                "casino": "casino-y-apuestas",
                "tienda": "tienda-y-mercado",
                "regla": "normas",
                "comandos": "comandos"
            }
            target_channels = []
            for cid in mentioned_cids:
                ch = message.guild.get_channel(int(cid))
                if ch and ch != message.channel and isinstance(ch, discord.TextChannel):
                    target_channels.append(ch)
            for kw, target_name in channel_keywords.items():
                if kw in clean_text.lower():
                    ch = find_channel_by_name(message.guild, target_name)
                    if ch and ch != message.channel and ch not in target_channels and isinstance(ch, discord.TextChannel):
                        target_channels.append(ch)
            # Buscar también canales directamente con find_channel_by_name si se mencionan como "#canal"
            channel_mentions = re.findall(r"#([\w\-]+)", clean_text)
            for cname in channel_mentions:
                ch = find_channel_by_name(message.guild, cname)
                if ch and ch != message.channel and ch not in target_channels and isinstance(ch, discord.TextChannel):
                    target_channels.append(ch)

            for ch in target_channels[:2]:
                try:
                    recent_msgs = []
                    async for rm in ch.history(limit=3):
                        rm_txt = extract_discord_message_text(rm, max_len=200)
                        if rm_txt:
                            recent_msgs.append(f"[{rm.author.display_name}]: {rm_txt}")
                    if recent_msgs:
                        recent_msgs.reverse()
                        channel_lookup_ctx += f"\n[ÚLTIMOS MENSAJES LEÍDOS EN VIVO DE #{ch.name}]:\n" + "\n".join(recent_msgs)
                except Exception:
                    pass

        # Contexto si el mensaje es una respuesta citada a otro mensaje
        reply_ref_ctx = ""
        if getattr(message, "reference", None):
            ref_m = getattr(message.reference, "resolved", None)
            if ref_m is None or not isinstance(ref_m, discord.Message):
                ref_mid = getattr(message.reference, "message_id", None)
                ch = getattr(message, "channel", None)
                if ref_mid and ch and hasattr(ch, "fetch_message"):
                    try:
                        ref_m = await ch.fetch_message(ref_mid)
                    except Exception:
                        ref_m = None

            if ref_m:
                ref_txt = extract_discord_message_text(ref_m, max_len=400)
                if ref_txt:
                    author_name = getattr(ref_m.author, "display_name", "Usuario")
                    if getattr(ref_m.author, "bot", False):
                        reply_ref_ctx = f"\n[RESPONDIENDO DIRECTAMENTE AL MENSAJE DEL BOT {author_name}]: \"{ref_txt}\""
                    else:
                        reply_ref_ctx = f"\n[RESPONDIENDO DIRECTAMENTE AL MENSAJE DE {author_name}]: \"{ref_txt}\""

        # Contexto de El Tribunal Gaming y Steam Store si se consultan en el chat
        tribunal_ctx = get_tribunal_query_ctx(clean_text)
        steam_ctx = get_steam_query_ctx(clean_text)

        # Turno actual del usuario
        current_prompt_text = f"{message.author.display_name}: {clean_text}"
        if reply_ref_ctx:
            current_prompt_text = f"{reply_ref_ctx}\n{current_prompt_text}"
        if url_context:
            current_prompt_text += url_context
        if not clean_text and not url_context and attachment_parts:
            current_prompt_text = f"{message.author.display_name}: Analiza este archivo/imagen adjunta y dime qué contiene."
        elif not clean_text and not url_context and not attachment_parts:
            current_prompt_text = f"{message.author.display_name}: Hola"

        # Inyectar todo el paquete de contexto enriquecido
        user_memory_ctx = get_user_memory_ctx(message.author.id)
        current_prompt_text += f"{user_memory_ctx}{server_live_ctx}{voice_radar_ctx}{user_live_ctx}{recent_channel_ctx}{music_ctx}{members_ctx}{dossier_context}{pins_context}{xp_calc_context}{web_search_context}{channel_lookup_ctx}{tribunal_ctx}{steam_ctx}"

        current_turn_parts = [{"text": current_prompt_text}] + attachment_parts

        if turns and turns[-1]["role"] == "user":
            turns[-1]["parts"][0]["text"] += f"\n{current_prompt_text}"
            if attachment_parts:
                turns[-1]["parts"].extend(attachment_parts)
        else:
            turns.append({
                "role": "user",
                "parts": current_turn_parts
            })

        while turns and turns[0]["role"] != "user":
            turns.pop(0)

        response_text = await asyncio.to_thread(call_gemini_multiturn, turns)

        # Extraer y aplicar reacción dinámica opcional al mensaje del usuario (máximo 1)
        response_text, reaction_raw = extract_reaction_tag(response_text)
        if reaction_raw is not None:
            resolved_react = resolve_reaction_emoji(reaction_raw, guild=message.guild)
            if resolved_react:
                try:
                    await message.add_reaction(resolved_react)
                except Exception as react_err:
                    print(f"Aviso añadiendo reacción '{resolved_react}': {react_err}")
                    try:
                        await message.add_reaction("🤔")
                    except Exception:
                        pass

        # 8. Interceptar acciones visuales y gráficas generadas por IA
        files_to_send = []

        # A. Acción de dibujo FLUX.1
        draw_block = extract_action_block(response_text, "ACTION_DRAW")
        if draw_block:
            full_draw, prompt_flux = draw_block
            prompt_flux = prompt_flux.strip()
            clean_response = response_text.replace(full_draw, "").strip()
            try:
                print(f"[FLUX.1] Generando imagen para prompt: '{prompt_flux}'")
                img_bytes = await asyncio.to_thread(generate_image_flux, prompt_flux)
                file = discord.File(io.BytesIO(img_bytes), filename="creacion_asistente.png")
                view = ImageActionView(prompt_flux, message.author.id)
                if clean_response:
                    clean_response = format_server_emojis(clean_response, guild=message.guild)
                    await message.reply(content=clean_response, file=file, view=view)
                else:
                    await message.reply(file=file, view=view)
                return
            except Exception as img_err:
                print(f"Error generando imagen FLUX: {img_err}")
                err_msg = (clean_response + "\n\n⚠️ *(Hubo un problema temporal con el motor de dibujo FLUX.1. Prueba a pedírmelo de nuevo en unos momentos)*") if clean_response else "⚠️ Ha ocurrido un problema con el motor de dibujo FLUX.1. Prueba a pedírmelo de nuevo en unos momentos."
                err_msg = format_server_emojis(err_msg, guild=message.guild)
                await message.reply(err_msg.strip())
                return

        # B. Acción de renderizado matemático (LaTeX PNG)
        while True:
            math_block = extract_action_block(response_text, "ACTION_MATH")
            if not math_block:
                break
            full_math, raw_latex = math_block
            raw_latex = raw_latex.strip()
            try:
                img_bytes = await asyncio.to_thread(render_math_image, raw_latex)
                files_to_send.append(discord.File(io.BytesIO(img_bytes), filename=f"formula_{len(files_to_send)+1}.png"))
                response_text = response_text.replace(full_math, "", 1).strip()
            except Exception as e:
                print(f"Error generando fórmula matemática: {e}")
                clean_formula = sanitize_discord_math_text(raw_latex)
                response_text = response_text.replace(full_math, f"**{clean_formula}**", 1).strip()

        if "$$" in response_text:
            block_match = re.search(r"\$\$([^\$]+)\$\$", response_text)
            if block_match:
                formula = block_match.group(1).strip()
                try:
                    img_bytes = await asyncio.to_thread(render_math_image, formula)
                    files_to_send.append(discord.File(io.BytesIO(img_bytes), filename=f"formula_{len(files_to_send)+1}.png"))
                    response_text = re.sub(r"\$\$[^\$]+\$\$", "", response_text, count=1).strip()
                except Exception as e:
                    print(f"Error generando fórmula matemática automática: {e}")

        # C. Acción de gráfico estadístico o función (QuickChart)
        while True:
            chart_block = extract_action_block(response_text, "ACTION_CHART")
            if not chart_block:
                break
            full_chart, chart_json = chart_block
            chart_json = chart_json.strip()
            try:
                img_bytes = await asyncio.to_thread(render_chart_image, chart_json)
                files_to_send.append(discord.File(io.BytesIO(img_bytes), filename=f"grafico_{len(files_to_send)+1}.png"))
                response_text = response_text.replace(full_chart, "", 1).strip()
            except Exception as e:
                print(f"Error generando gráfico estadístico: {e}")
                response_text = response_text.replace(full_chart, "", 1).strip()

        # D. Acción de diagrama conceptual / flujo (Mermaid)
        while True:
            diagram_block = extract_action_block(response_text, "ACTION_DIAGRAM")
            if not diagram_block:
                break
            full_diag, mermaid_code = diagram_block
            mermaid_code = mermaid_code.strip()
            try:
                img_bytes = await asyncio.to_thread(render_diagram_image, mermaid_code)
                files_to_send.append(discord.File(io.BytesIO(img_bytes), filename=f"diagrama_{len(files_to_send)+1}.png"))
                response_text = response_text.replace(full_diag, "", 1).strip()
            except Exception as e:
                print(f"Error generando diagrama Mermaid: {e}")
                clean_diag = mermaid_code.strip().replace("```mermaid", "").replace("```", "").strip()
                response_text = response_text.replace(full_diag, f"```mermaid\n{clean_diag}\n```", 1).strip()

        # E. Acción de tarjeta de código destacada (Pillow Terminal Card)
        while True:
            code_block = extract_action_block(response_text, "ACTION_CODE")
            if not code_block:
                break
            full_code, code_content = code_block
            code_content = code_content.strip()
            try:
                img_bytes = await asyncio.to_thread(render_code_card_image, code_content)
                files_to_send.append(discord.File(io.BytesIO(img_bytes), filename=f"tarjeta_codigo_{len(files_to_send)+1}.png"))
                response_text = response_text.replace(full_code, "", 1).strip()
            except Exception as e:
                print(f"Error generando tarjeta de código: {e}")
                clean_code = code_content.strip()
                if clean_code.startswith("```"):
                    fallback_code = clean_code
                else:
                    fallback_code = f"```python\n{clean_code}\n```"
                response_text = response_text.replace(full_code, fallback_code, 1).strip()

        # Fallback de seguridad para dibujo directo
        direct_draw_prefix = ("dibuja ", "dibújame ", "dibujame ", "crea una imagen de ", "genera una imagen de ", "haz un dibujo de ", "hazme un dibujo de ")
        if any(lowered.startswith(p) for p in direct_draw_prefix) and not files_to_send:
            try:
                enhanced = await asyncio.to_thread(enhance_image_prompt, clean_text, message.author.display_name)
                print(f"[FLUX.1 Fallback] Generando imagen para: '{enhanced}'")
                img_bytes = await asyncio.to_thread(generate_image_flux, enhanced)
                file = discord.File(io.BytesIO(img_bytes), filename="creacion_asistente.png")
                view = ImageActionView(enhanced, message.author.id)
                reply_txt = response_text if response_text and not any(bad in response_text.lower() for bad in ["aquí tienes", "aqui tienes", "he creado", "la imagen"]) else f"🎨 **Aquí tienes tu creación, {message.author.display_name}:**"
                reply_txt = format_server_emojis(reply_txt, guild=message.guild)
                await message.reply(content=reply_txt, file=file, view=view)
                return
            except Exception as e:
                print(f"Error en fallback directo de dibujo: {e}")

        # Sanitizar cualquier resto de código LaTeX
        response_text = sanitize_discord_math_text(response_text)
        # Formatear y convertir emojis del servidor (:nombre_emoji: -> <:nombre:ID> o fallback seguro)
        response_text = format_server_emojis(response_text, guild=message.guild)
        if not response_text and files_to_send:
            response_text = "Aquí tienes la representación visual:"

        # Enviar respuesta respetando límite de 2.000 caracteres de Discord
        if len(response_text) <= 1900:
            if files_to_send:
                await message.reply(content=response_text, files=files_to_send[:10])
                for extra_idx in range(10, len(files_to_send), 10):
                    await message.reply(files=files_to_send[extra_idx : extra_idx + 10])
            else:
                await message.reply(response_text)
        else:
            chunks = []
            remaining = response_text
            while len(remaining) > 1900:
                split_at = remaining.rfind("\n", 0, 1900)
                if split_at == -1:
                    split_at = remaining.rfind(" ", 0, 1900)
                if split_at == -1:
                    split_at = 1900
                chunks.append(remaining[:split_at].strip())
                remaining = remaining[split_at:].strip()
            if remaining:
                chunks.append(remaining)
            file_idx = 0
            for i, chunk in enumerate(chunks):
                chunk_files = files_to_send[file_idx : file_idx + 10] if file_idx < len(files_to_send) else []
                file_idx += len(chunk_files)
                if chunk_files:
                    await message.reply(content=chunk, files=chunk_files)
                else:
                    await message.reply(chunk)
            while file_idx < len(files_to_send):
                chunk_files = files_to_send[file_idx : file_idx + 10]
                file_idx += len(chunk_files)
                await message.reply(files=chunk_files)

        # Chat-to-Voice: Solo locutar si se pide explícitamente en el texto
        vch = None
        if message.author and hasattr(message.author, "voice") and message.author.voice and message.author.voice.channel:
            vch = message.author.voice.channel

        vc = message.guild.voice_client if message.guild else None
        guild_id = message.guild.id if message.guild else 0
        manually_dc = is_voice_manually_disconnected(guild_id)

        voice_triggers = [
            "di en la llamada", "habla en la llamada", "únete a la llamada", "unete a la llamada",
            "habla por voz", "respóndeme por voz", "respondeme por voz", "dilo en la llamada",
            "dilo por voz", "dilo en voz alta", "cuéntamelo por voz", "cuentamelo por voz",
            "entra a la llamada", "entra en la llamada", "entra a llamada",
            "conéctate a la llamada", "conectate a la llamada", "conéctate al canal de voz", "conectate al canal de voz",
            "ven a la llamada", "ven al canal de voz", "métete a la llamada", "metete a la llamada",
            "métete en la llamada", "metete en la llamada", "habla en llamada", "dilo en llamada",
            "lee en voz alta", "léelo en voz alta"
        ]
        explicit_voice_request = any(p in lowered for p in voice_triggers)

        should_speak_in_voice = bool(
            explicit_voice_request and vc and vc.is_connected() and vch and vc.channel == vch and not manually_dc
        )

        if should_speak_in_voice and vc and vc.is_connected():
            try:
                clean_for_speech = re.sub(r"\[ACTION_[A-Z]+:\s*.*?\]", "", response_text, flags=re.DOTALL | re.IGNORECASE).strip()
                clean_for_speech = re.sub(r"```.*?```", "", clean_for_speech, flags=re.DOTALL).strip()
                clean_for_speech = re.sub(r"`.*?`", "", clean_for_speech).strip()
                tts_text = clean_text_for_tts(clean_for_speech[:2500])
                if tts_text and len(tts_text) >= 2:
                    _bot_log(f"🎙️ [TTS Locución] Reproduciendo respuesta ({len(tts_text)} chars) en #{vc.channel.name}...")
                    audio_path = await generate_speech_audio(tts_text, "alvaro")
                    play_audio_in_voice(vc, audio_path)
            except Exception as e:
                _bot_log(f"Aviso locución de respuesta en llamada: {e}")
