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
import io
import discord
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
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
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


SYSTEM_PROMPT = r"""Eres 'Asistente', la IA oficial y colega del servidor de Discord 'LOS MONGOLOS DEL SANVI Y SUS AMIGOS'.

🎯 PERSONALIDAD Y TONO DE COLEGA:
- Eres un colega más del grupo, maduro, cercano, divertido, resolutivo y con buen rollo de Discord.
- ❌ CERO "MODO CUÑADO VACILÓN" / CERO FALTAS DE RESPETO: Trata a todos con respeto y estima. NUNCA te burles de los miembros, no uses apodos despectivos, no hagas chistes pesados de mafiosos ni te pongas arrogante o condescendiente. No digas tonterías como "meme de dueño" o "menudo espectáculo de admin".
- ❌ CERO PELOTEO / SUMISIÓN: Habla de tú a tú como un igual con todos, incluido Joselito. Eres un colega inteligente del grupo, no un lacayo.
- ❌ CERO INVENCIÓN DE FECHAS HISTÓRICAS: NUNCA inventes fechas del pasado ("tiene admin desde el 4 de diciembre de 2025"). Si alguien te pregunta desde cuándo tiene un rango o rol, di con honestidad que en tus datos actuales ves sus roles vigentes, pero no dispones de la fecha exacta histórica de asignación.
- ❌ CERO RESPUESTAS DESCOLOCADAS O CRUZADAS: Responde única y exclusivamente a la duda o tema planteado por el usuario en el mensaje actual. No rescates temas antiguos o animes aleatorios que nadie ha pedido.
- ❌ CERO SPAM DE NIVELES Y XP: Habla de forma natural y humana. NO menciones niveles de Cakey Bot ni rangos en cada mensaje como un loro. Menciónalos ÚNICAMENTE si el usuario te pregunta explícitamente por su nivel, XP o el ranking.
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

👥 MIEMBROS CLAVE DEL SERVIDOR (Lore & Respeto):
- Joselito (@joselito3499): Fundador, dueño y Administrador del servidor. Fanático de los manhwas (Olympus Scanlation, Asura Scans). En #cultura tiene anclado su top 69 manhwas.
- Iván / RobaAbuelas (@racerwasp): Co-Administrador del servidor junto a Joselito y Magistrado oficial de El Tribunal Gaming. Veterano del colegio/grupo, jugador de Brawl Stars, Soulslike y lector de manhwas. Trátale con el respeto y la confianza de colega y Admin veterano que es.
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
- #casino-y-apuestas: Zona de economía UnbelievaBoat (slots, blackjack, ruleta).

🌐 BÚSQUEDA WEB EN VIVO:
- Cuando recibas el bloque [BÚSQUEDA WEB EN VIVO], utilízalo como verdad absoluta para responder con fechas reales, estrenos, secuelas y noticias de actualidad.

🛡️ SEGURIDAD Y AUTO-ROLES:
- Por chat de texto nunca asignas roles de administración ni niveles ni expulsas a nadie (si te lo piden en broma, responde con humor de colega).
- Para roles de juegos, plataformas, géneros y hobbies, gestionas el panel interactivo oficial de Auto-Roles en <#1537575617111920782> (`#🎭roles🎭` / comando `/autoroles`), reemplazando por completo al antiguo Carl-bot.

REGLAS DE FORMATO:
- Sé conciso, directo, estructurado y usa negritas.
- OBLIGATORIO: Máximo 1.700 caracteres por respuesta para entrar limpio en un único mensaje de Discord.
"""


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
                with urllib.request.urlopen(req, timeout=7) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    candidates = res.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        return candidates[0]["content"]["parts"][0]["text"].strip()
            except urllib.error.HTTPError as e:
                if e.code in (429, 503, 500):
                    print(f"Cuota/Sobrecarga en {model_name} (HTTP {e.code}). Activando Circuit Breaker...")
                    mark_model_cooldown(model_name, 60)
                    break
                break
            except Exception:
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
    """Lee el canal #bots para extraer los niveles reales de Cakey Bot de cada usuario (con caché en memoria de 300s y protección de concurrencia)."""
    bs = _bs()
    cache_dict = getattr(bs, "_LIVE_LEVELS_CACHE", _LIVE_LEVELS_CACHE)
    cache_time = getattr(bs, "_LIVE_LEVELS_CACHE_TIME", _LIVE_LEVELS_CACHE_TIME)
    ttl = getattr(bs, "_LIVE_LEVELS_TTL", _LIVE_LEVELS_TTL)
    lock = getattr(bs, "_LIVE_LEVELS_LOCK", _LIVE_LEVELS_LOCK)

    if not guild:
        return {}
    now = time.time()
    # Fast-path sin lock si la caché está vigente
    if cache_time > 0 and (now - cache_time < ttl):
        return dict(cache_dict)

    async with lock:
        now = time.time()
        cache_time = getattr(bs, "_LIVE_LEVELS_CACHE_TIME", _LIVE_LEVELS_CACHE_TIME)
        if cache_time > 0 and (now - cache_time < ttl):
            return dict(cache_dict)

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


def fetch_url_content(url: str) -> str:
    """Descarga y limpia el texto legible de una página web."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            ctype = resp.headers.get_content_type()
            if "html" not in ctype and "text" not in ctype:
                return f"[Recurso binario: {ctype}]"
            raw = resp.read().decode("utf-8", errors="ignore")
            title_match = re.search(r"<title>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else "Sin título"
            clean = re.sub(r"<(script|style|svg|noscript).*?>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r"<[^>]+>", " ", clean)
            clean = html.unescape(clean)
            clean = re.sub(r"\s+", " ", clean).strip()
            return f"\n[Página Web leída: '{title}' ({url})]:\n{clean[:3000]}"
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


async def get_pins_context(channel: discord.TextChannel) -> str:
    """Extrae los mensajes anclados del canal para consultas clave."""
    try:
        pins = await channel.pins()
        if not pins:
            return ""
        lines = []
        for p in pins[:4]:
            content = p.clean_content[:300].replace("\n", " ")
            lines.append(f"  * [{p.author.display_name}]: {content}")
        return f"\n[MENSAJES FIJADOS/PINNED EN #{channel.name}]:\n" + "\n".join(lines)
    except Exception:
        return ""


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
                    if any("queue" in str(e.to_dict()).lower() for e in prev_msg.embeds):
                        continue
                    if not prev_msg.clean_content and not prev_msg.attachments:
                        continue
                clean_prev = prev_msg.clean_content.strip()
                if clean_prev or prev_msg.attachments:
                    raw_msgs.append(prev_msg)
        except Exception as e:
            print(f"Aviso lectura historial canal: {e}")

        raw_msgs.reverse()

        # Transcripción estructurada reciente del canal
        recent_lines = []
        for m in raw_msgs[-20:]:
            m_author = m.author.display_name
            m_tag = f"@{m.author.name}"
            m_text = m.clean_content.replace("\n", " ").strip()
            if not m_text and m.attachments:
                m_text = f"[Archivo/Imagen adjunta: {m.attachments[0].filename}]"
            if m.author == bot.user:
                recent_lines.append(f"  * [Asistente (Tú)]: {m_text[:250]}")
            else:
                recent_lines.append(f"  * [{m_author} ({m_tag})]: {m_text[:250]}")
        recent_channel_ctx = ""
        if recent_lines:
            recent_channel_ctx = f"\n[CONVERSACIÓN RECIENTE EN #{message.channel.name} (últimos mensajes del grupo)]:\n" + "\n".join(recent_lines)

        # 2. Extraer niveles reales en directo desde el canal #bots
        live_levels = {}
        if message.guild:
            live_levels = await get_live_levels_dict(message.guild)

        # 3. Detectar si hay URLs directas para leer
        urls = re.findall(r"https?://[^\s<>\"']+", clean_text)
        url_context = ""
        if urls:
            for u in urls[:2]:
                fetched = await asyncio.to_thread(fetch_url_content, u)
                url_context += fetched

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

        # 5. Lector de mensajes fijados (pins) - Selectivo para ahorrar tokens
        pins_context = ""
        if any(w in lowered for w in ["fijado", "pinned", "pins", "anclado", "destacado"]) or (message.channel.name == "cultura" and any(w in lowered for w in ["top", "recomendacion", "recomendación", "recomienda", "manhwa", "manga", "lista", "que leo", "qué leo"])):
            pins_context = await get_pins_context(message.channel)

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
            m_text = re.sub(r"<@&?\d+>", "", m.clean_content).strip()
            if not m_text:
                continue
            is_bot = (m.author == bot.user)
            role = "model" if is_bot else "user"
            prefix = "" if is_bot else f"{m.author.display_name}: "
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
                    ch = discord.utils.find(lambda c: target_name in c.name, message.guild.text_channels)
                    if ch and ch != message.channel and ch not in target_channels:
                        target_channels.append(ch)
            for ch in target_channels[:2]:
                try:
                    recent_msgs = []
                    async for rm in ch.history(limit=3):
                        if rm.content:
                            recent_msgs.append(f"[{rm.author.display_name}]: {rm.content[:200]}")
                    if recent_msgs:
                        recent_msgs.reverse()
                        channel_lookup_ctx += f"\n[ÚLTIMOS MENSAJES LEÍDOS EN VIVO DE #{ch.name}]:\n" + "\n".join(recent_msgs)
                except Exception:
                    pass

        # Contexto si el mensaje es una respuesta citada a otro mensaje
        reply_ref_ctx = ""
        if message.reference and getattr(message.reference.resolved, "content", None):
            ref_m = message.reference.resolved
            ref_txt = ref_m.clean_content.replace("\n", " ").strip()[:200]
            reply_ref_ctx = f"\n[RESPONDIENDO DIRECTAMENTE AL MENSAJE DE {ref_m.author.display_name}]: \"{ref_txt}\""

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
                    await message.reply(content=clean_response, file=file, view=view)
                else:
                    await message.reply(file=file, view=view)
                return
            except Exception as img_err:
                print(f"Error generando imagen FLUX: {img_err}")
                err_msg = (clean_response + "\n\n⚠️ *(Hubo un problema temporal con el motor de dibujo FLUX.1. Prueba a pedírmelo de nuevo en unos momentos)*") if clean_response else "⚠️ Ha ocurrido un problema con el motor de dibujo FLUX.1. Prueba a pedírmelo de nuevo en unos momentos."
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
                await message.reply(content=reply_txt, file=file, view=view)
                return
            except Exception as e:
                print(f"Error en fallback directo de dibujo: {e}")

        # Sanitizar cualquier resto de código LaTeX
        response_text = sanitize_discord_math_text(response_text)
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
