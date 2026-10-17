"""
Servicio 24/7 de IA Multimodal para el Bot 'Asistente' en Discord.
Capacidades:
- Niveles Reales de Cakey Bot en Vivo: Lee en tiempo real el canal #bots para conocer el nivel exacto de cada miembro.
- Búsqueda Web en Vivo: Consulta internet en tiempo real para datos de actualidad, anime, juegos y hardware con memoria conversacional (context-aware search).
- Visión Multimodal: Lee y analiza imágenes, capturas, fotos y memes (OCR + visión).
- Lectura de Enlaces Web: Descarga y lee páginas web y noticias compartidas en el chat.
- Lectura de Archivos: Lee archivos de texto, código de programación y PDFs adjuntos.
- Continuidad Conversacional: Memoria de contexto de los últimos turnos en el canal.
- Mensajes Fijados: Lector dinámico de los pins clave de los canales (channel.pins()).
- Ficha Técnica de Usuarios: Inspección en profundidad de fechas, roles y estado de miembros.
- Calculadora de XP: Motor matemático cuadrático del sistema de niveles de Cakey Bot.
- Guía de Comandos: Diccionario completo de economía (UnbelievaBoat) y niveles (Cakey Bot).
- Seguridad: Cero permisos de roles; actúa como enciclopedia del servidor y colega.
- Motor: Gemini Flash con lista de respaldo automático (100% Free Tier, coste 0€).
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
import discord
from discord import app_commands
import io
import wave
import struct
import math
import threading
import random
import tempfile
import edge_tts
from discord.ext import voice_recv
from datetime import datetime, timezone, timedelta
import collections

GLOBAL_LOG_BUFFER = collections.deque(maxlen=200)

def bot_log(msg: str):
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    GLOBAL_LOG_BUFFER.append(line)

# === PARCHE DAVE (DISCORD E2EE VOICE DECRYPTION) ===
# Permite al bot descifrar el audio encriptado con MLS proveniente de la app de escritorio de Discord
try:
    import davey
    import discord.ext.voice_recv.opus as vo
    if hasattr(vo, "PacketDecoder"):
        _orig_decode_packet = vo.PacketDecoder._decode_packet

        def _patched_decode_packet(self, packet):
            try:
                if packet and getattr(packet, "decrypted_data", None):
                    vc = getattr(self.sink, "voice_client", None) or getattr(self.sink, "vc", None)
                    if vc:
                        conn = getattr(vc, "_connection", None)
                        dave = getattr(conn, "dave_session", None)
                        if dave and getattr(dave, "ready", False):
                            candidates = []
                            if self._cached_id:
                                candidates.append(self._cached_id)
                            u = vc._get_id_from_ssrc(self.ssrc)
                            if u and u not in candidates:
                                candidates.append(u)
                            if not candidates:
                                try:
                                    candidates = dave.get_user_ids()
                                except Exception:
                                    candidates = []

                            for cand_id in candidates:
                                try:
                                    dec = dave.decrypt(cand_id, davey.MediaType.audio, packet.decrypted_data)
                                    if dec:
                                        packet.decrypted_data = dec
                                        self._cached_id = cand_id
                                        if not vc._get_id_from_ssrc(self.ssrc):
                                            vc._add_ssrc(cand_id, self.ssrc)
                                        break
                                except Exception:
                                    pass
                return _orig_decode_packet(self, packet)
            except Exception:
                return packet, b""

        vo.PacketDecoder._decode_packet = _patched_decode_packet
        bot_log("🔒 [DAVE E2EE] Parche de descifrado de voz activo en PacketDecoder.")
except Exception as _patch_err:
    bot_log(f"Aviso inicialización parche DAVE: {_patch_err}")

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def get_spain_now_str() -> str:
    """Devuelve la fecha y hora actual en España peninsular formateada en español."""
    now_utc = datetime.now(timezone.utc)
    m = now_utc.month
    # Horario peninsular español (CEST UTC+2 en verano, CET UTC+1 en invierno)
    offset_h = 2 if (4 <= m <= 9 or (m == 3 and now_utc.day >= 25) or (m == 10 and now_utc.day < 25)) else 1
    spain_time = now_utc + timedelta(hours=offset_h)
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    dia_sem = dias[spain_time.weekday()]
    mes = meses[spain_time.month - 1]
    return f"{dia_sem}, {spain_time.day} de {mes} de {spain_time.year} - {spain_time.strftime('%H:%M')} (Hora de España)"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config_discord.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

cfg = load_config()
TOKEN = os.getenv("DISCORD_TOKEN") or cfg.get("token")
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or cfg.get("gemini_api_key")
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or cfg.get("gemini_model", "gemini-3.6-flash")

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

🛡️ SEGURIDAD:
- No tienes permisos de Discord para modificar roles ni expulsar a nadie. Si te lo piden en broma, responde con humor de colega.

REGLAS DE FORMATO:
- Sé conciso, directo, estructurado y usa negritas.
- OBLIGATORIO: Máximo 1.700 caracteres por respuesta para entrar limpio en un único mensaje de Discord.
"""

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

TRIBUNAL_DATA_PATH = os.path.join(BASE_DIR, "datos", "tribunal_data.json")

def load_tribunal_data() -> dict:
    if os.path.exists(TRIBUNAL_DATA_PATH):
        try:
            with open(TRIBUNAL_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Aviso lectura tribunal_data.json: {e}")
    return {"coop": [], "single": []}

tribunal_data = load_tribunal_data()

USER_MEMORY_PATH = os.path.join(BASE_DIR, "datos", "user_memory.json")
TRIVIA_DATA_PATH = os.path.join(BASE_DIR, "datos", "trivia_data.json")

def load_user_memory() -> dict:
    if os.path.exists(USER_MEMORY_PATH):
        try:
            with open(USER_MEMORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Aviso lectura user_memory.json: {e}")
    return {}

def save_user_memory(data: dict):
    try:
        with open(USER_MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error guardando user_memory.json: {e}")

user_memory = load_user_memory()

def get_user_memory_ctx(user_id: int) -> str:
    """Extrae la memoria persistente del usuario para inyectarla en el contexto del bot."""
    mem = user_memory.get(str(user_id))
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

def load_trivia_data() -> list:
    if os.path.exists(TRIVIA_DATA_PATH):
        try:
            with open(TRIVIA_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Aviso lectura trivia_data.json: {e}")
    return []

def clean_text_for_tts(text: str) -> str:
    """Limpia markdown, URLs, emojis de Discord y caracteres especiales para locución natural."""
    clean = re.sub(r"\[ACTION_DRAW:\s*.*?\]", "", text, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"https?://[^\s<>\"']+", "", clean)
    clean = re.sub(r"<@!?\d+>", "", clean)
    clean = re.sub(r"<@&\d+>", "", clean)
    clean = re.sub(r"<#\d+>", "", clean)
    clean = re.sub(r"<a?:[^:]+:\d+>", "", clean)
    # Convertir saltos de línea en pausas oracionales para locutar párrafos consecutivos con fluidez
    clean = re.sub(r"([^\.\?!])\n+", r"\1. ", clean)
    clean = re.sub(r"[*_~`#>\[\]\(\)\{\}\\\^\$]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

# Catálogo único de voces de /habla: clave -> (etiqueta, motor, voz, tono, velocidad). Discord admite 25 opciones como máximo.
TTS_VOICES = {
    "alvaro":    ("Álvaro (España)", "edge", "es-ES-AlvaroNeural", "+0Hz", "+0%"),
    "elvira":    ("Elvira (España, femenina)", "edge", "es-ES-ElviraNeural", "+0Hz", "+0%"),
    "ximena":    ("Ximena (España, juvenil)", "edge", "es-ES-XimenaNeural", "+0Hz", "+0%"),
    "jorge":     ("Jorge (México)", "edge", "es-MX-JorgeNeural", "+0Hz", "+0%"),
    "dalia":     ("Dalia (México, femenina)", "edge", "es-MX-DaliaNeural", "+0Hz", "+0%"),
    "tomas":     ("Tomás (Argentina)", "edge", "es-AR-TomasNeural", "+0Hz", "+0%"),
    "elena":     ("Elena (Argentina, femenina)", "edge", "es-AR-ElenaNeural", "+0Hz", "+0%"),
    "gonzalo":   ("Gonzalo (Colombia)", "edge", "es-CO-GonzaloNeural", "+0Hz", "+0%"),
    "camila":    ("Camila (Perú, femenina)", "edge", "es-PE-CamilaNeural", "+0Hz", "+0%"),
    "manuel":    ("Manuel (Cuba)", "edge", "es-CU-ManuelNeural", "+0Hz", "+0%"),
    "ardilla":   ("Ardilla (aguda y rápida)", "edge", "es-ES-AlvaroNeural", "+80Hz", "+30%"),
    "demonio":   ("Demonio (grave y lenta)", "edge", "es-ES-AlvaroNeural", "-45Hz", "-20%"),
    "puck":      ("Puck (Gemini, animada)", "gemini", "Puck", None, None),
    "charon":    ("Charon (Gemini, grave)", "gemini", "Charon", None, None),
    "kore":      ("Kore (Gemini, firme femenina)", "gemini", "Kore", None, None),
    "fenrir":    ("Fenrir (Gemini, excitable)", "gemini", "Fenrir", None, None),
    "zephyr":    ("Zephyr (Gemini, brillante femenina)", "gemini", "Zephyr", None, None),
    "leda":      ("Leda (Gemini, juvenil femenina)", "gemini", "Leda", None, None),
    "orus":      ("Orus (Gemini, seria)", "gemini", "Orus", None, None),
    "aoede":     ("Aoede (Gemini, desenfadada femenina)", "gemini", "Aoede", None, None),
    "enceladus": ("Enceladus (Gemini, susurrante)", "gemini", "Enceladus", None, None),
    "algenib":   ("Algenib (Gemini, rasgada)", "gemini", "Algenib", None, None),
    "gacrux":    ("Gacrux (Gemini, madura femenina)", "gemini", "Gacrux", None, None),
    "sadachbia": ("Sadachbia (Gemini, vivaz)", "gemini", "Sadachbia", None, None),
    "sulafat":   ("Sulafat (Gemini, cálida femenina)", "gemini", "Sulafat", None, None),
}
# Alias de claves antiguas
TTS_VOICE_ALIASES = {"abril": "elvira"}

async def generate_speech_audio(text: str, voice_type: str = "alvaro") -> str:
    """Genera archivo de audio temporal con Edge Neural TTS o Gemini Flash TTS con fallback automático."""
    clean = clean_text_for_tts(text)
    if not clean:
        clean = "Hola, aquí estoy."
    clean = clean[:2500]
    
    temp_dir = tempfile.gettempdir()
    voice_type = TTS_VOICE_ALIASES.get(voice_type, voice_type)
    _, engine, vname, pitch, rate = TTS_VOICES.get(voice_type, TTS_VOICES["alvaro"])
    
    if engine == "gemini":
        out_path = os.path.join(temp_dir, f"speech_gemini_{int(time.time()*1000)}.wav")
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-lite-tts:generateContent?key={GEMINI_KEY}"
            payload = {
                "contents": [{"parts": [{"text": clean}]}],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": vname
                            }
                        }
                    }
                }
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            
            def call_gemini_tts():
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode("utf-8"))
                    
            res = await asyncio.to_thread(call_gemini_tts)
            b64 = res['candidates'][0]['content']['parts'][0]['inlineData']['data']
            raw = base64.b64decode(b64)
            with open(out_path, "wb") as f:
                f.write(raw)
            return out_path
        except Exception as e:
            print(f"Aviso: Gemini TTS falló ({e}). Conmutando automáticamente a Edge Neural TTS...")
            _, engine, vname, pitch, rate = TTS_VOICES["alvaro"]
            
    out_path = os.path.join(temp_dir, f"speech_edge_{int(time.time()*1000)}.mp3")
    try:
        comm = edge_tts.Communicate(clean, vname, pitch=pitch, rate=rate)
        await comm.save(out_path)
    except Exception as e:
        if vname == "es-ES-AlvaroNeural" and pitch == "+0Hz":
            raise
        print(f"Aviso: voz Edge '{vname}' falló ({e}). Conmutando a Álvaro...")
        comm = edge_tts.Communicate(clean, "es-ES-AlvaroNeural")
        await comm.save(out_path)
    return out_path

import zipfile

RECORDINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")
os.makedirs(RECORDINGS_DIR, exist_ok=True)
METADATA_FILE = os.path.join(RECORDINGS_DIR, "recordings_metadata.json")
RETENTION_SECONDS = 24 * 3600  # Retención de 24 horas completas (1 día)

# Reentrante: el limpiador de grabaciones llama a save_recordings_metadata() con el candado ya tomado;
# con un Lock normal eso se bloqueaba a sí mismo y congelaba todo el bot
VOICE_TURNS_LOCK = threading.RLock()

def load_recordings_metadata():
    """Carga de disco el historial de grabaciones válidas de las últimas 24 horas."""
    if not os.path.exists(METADATA_FILE):
        return []
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            entries = json.load(f)
        now = time.time()
        valid = []
        for e in entries:
            epoch = e.get("epoch", 0.0)
            if (now - epoch) < RETENTION_SECONDS:
                fpath = os.path.join(RECORDINGS_DIR, e.get("filename", ""))
                if os.path.exists(fpath):
                    valid.append(e)
            else:
                fpath = os.path.join(RECORDINGS_DIR, e.get("filename", ""))
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
        return valid
    except Exception as ex:
        bot_log(f"Aviso carga grabaciones: {ex}")
        return []

def save_recordings_metadata():
    """Persiste de forma atómica el registro de grabaciones en recordings_metadata.json."""
    try:
        with VOICE_TURNS_LOCK:
            data = list(VOICE_TURNS_LOG)
        tmp = METADATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, METADATA_FILE)
    except Exception as ex:
        bot_log(f"Aviso guardado grabaciones metadata: {ex}")

VOICE_TURNS_LOG = load_recordings_metadata()
# Mapeo de guild_id -> tiempo de expiración (para no quedarse bloqueado permanentemente si alguien dice 'salte' o hay desconexión temporal)
VOICE_MANUALLY_DISCONNECTED = {}
# Mapeo de guild_id -> instante de una desconexión iniciada por el propio bot (limpieza interna), que NO debe bloquear la auto-conexión
VOICE_INTERNAL_DISCONNECT = {}

def set_voice_manually_disconnected(guild_id: int, duration_sec: float = None):
    """Bloquea la auto-conexión. Sin duración el bloqueo es indefinido: solo se levanta con /unete, una orden de unirse
    o cuando la sala se queda sin humanos (así un kick no se deshace solo a los 3 minutos)."""
    if guild_id:
        VOICE_MANUALLY_DISCONNECTED[guild_id] = float("inf") if duration_sec is None else time.time() + duration_sec

def mark_internal_voice_disconnect(guild_id: int):
    if guild_id:
        VOICE_INTERNAL_DISCONNECT[guild_id] = time.time()

def consume_internal_voice_disconnect(guild_id: int) -> bool:
    ts = VOICE_INTERNAL_DISCONNECT.pop(guild_id, None)
    return ts is not None and (time.time() - ts) < 15.0

def clear_voice_manually_disconnected(guild_id: int):
    if guild_id:
        VOICE_MANUALLY_DISCONNECTED.pop(guild_id, None)

def is_voice_manually_disconnected(guild_id: int) -> bool:
    if not guild_id or guild_id not in VOICE_MANUALLY_DISCONNECTED:
        return False
    if time.time() >= VOICE_MANUALLY_DISCONNECTED[guild_id]:
        VOICE_MANUALLY_DISCONNECTED.pop(guild_id, None)
        return False
    return True

def pcm_stereo_to_mono_48k(pcm_bytes: bytes) -> bytes:
    """Convierte audio PCM estéreo de 48kHz a mono puro a 48kHz con normalización de volumen para máxima claridad en Gemini."""
    try:
        import audioop
        mono = audioop.tomono(pcm_bytes, 2, 0.5, 0.5)
        max_val = audioop.max(mono, 2)
        if max_val > 80 and max_val < 18000:
            factor = min(18000.0 / max_val, 3.5)
            mono = audioop.mul(mono, 2, factor)
        return mono
    except Exception:
        count = len(pcm_bytes) // 4
        if count == 0:
            return b""
        shorts = struct.unpack(f"<{count * 2}h", pcm_bytes[:count * 4])
        mono_shorts = [(shorts[i*2] + shorts[i*2+1]) // 2 for i in range(count)]
        return struct.pack(f"<{count}h", *mono_shorts)

# Modelos verificados en orden de respuesta (<0.7s) y cuota gratuita amplia
MODELS_PRIORITY = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-flash-latest"
]
model_cooldowns = {}

def get_available_models():
    """Devuelve los modelos disponibles que no están en cooldown por error 429/503."""
    now = time.time()
    available = [m for m in MODELS_PRIORITY if now >= model_cooldowns.get(m, 0)]
    return available if available else MODELS_PRIORITY

def mark_model_cooldown(model_name: str, duration_sec: int = 60):
    """Aplica cooldown temporal a un modelo saturado para conmutar sin latencia."""
    model_cooldowns[model_name] = time.time() + duration_sec
    bot_log(f"⚡ [Circuit Breaker] Modelo '{model_name}' en cooldown por {duration_sec}s.")

class GeminiLiveVoiceSink(voice_recv.AudioSink):
    """
    Sink de audio bidireccional en tiempo real (estilo Gemini Live) para llamadas de Discord.
    - Captura tramas PCM de 48kHz estéreo de los usuarios en la llamada.
    - Detección de actividad vocal (VAD) y segmentación por silencios.
    - Convierte a 48kHz mono con ganancia normalizada y guarda el clip de audio en disco para auditoría.
    - Filtra inteligentemente si los usuarios hablan entre ellos jugando o se dirigen al Asistente.
    - Responde al vuelo con voz neuronal fluida (Edge Neural TTS) directamente en la llamada.
    """
    def __init__(self, voice_client: voice_recv.VoiceRecvClient, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.vc = voice_client
        self.loop = loop
        self.user_buffers = {}
        self._lock = threading.Lock()
        self._is_active = True
        self.silence_threshold_rms = 45  # Sensibilidad excelente para captar voces suaves con Krisp
        self.silence_timeout = 0.85      # Ventana de 850ms para evitar cortar palabras a mitad de frase
        self.min_speech_frames = 16      # ~0.32s mínimo para filtrar micro-chasquidos y pops de micrófono
        self.max_speech_frames = 450     # ~9.0s máximo por turno
        self.recent_turns = []
        self.last_bot_reply_time = 0.0
        self.voice_type = "alvaro"
        self.playback_lock = asyncio.Lock()
        self.watchdog_task = self.loop.create_task(self._watchdog())
        ch_name = getattr(getattr(voice_client, "channel", None), "name", "llamada")
        bot_log(f"🎙️ [Gemini Live] Sink activado y escuchando en #{ch_name}")

    def wants_opus(self) -> bool:
        return False

    def write(self, user: discord.User, data: voice_recv.VoiceData) -> None:
        try:
            if not self._is_active:
                return
            if user is not None and getattr(user, "bot", False):
                return
            client = self.vc or getattr(self, "voice_client", None)
            pcm = data.pcm
            if not pcm:
                return

            packet = getattr(data, "packet", None)
            ssrc = getattr(packet, "ssrc", None) if packet else None

            # Resolver user a través del SSRC en tiempo real si el gateway no lo incluyó
            if user is None and client and ssrc:
                uid = getattr(client, "_get_id_from_ssrc", lambda s: None)(ssrc)
                if uid and getattr(client, "guild", None):
                    user = client.guild.get_member(uid)

            count = len(pcm) // 2
            if count == 0:
                return
            shorts = struct.unpack(f"<{count}h", pcm)
            rms = int(math.sqrt(sum(s * s for s in shorts) / count))

            # Buffer aislado por usuario o por SSRC para que nunca se mezclen las voces de distintas personas
            user_key = user.id if user else (f"ssrc_{ssrc}" if ssrc else "speaker")

            now = time.time()
            with self._lock:
                state = self.user_buffers.setdefault(user_key, {
                    "frames": [],
                    "last_speech_time": 0.0,
                    "in_speech": False,
                    "user": user,
                    "ssrc": ssrc
                })
                if user and not state.get("user"):
                    state["user"] = user

                if rms >= self.silence_threshold_rms:
                    state["frames"].append(pcm)
                    state["last_speech_time"] = now
                    if not state["in_speech"]:
                        state["in_speech"] = True
                        u_name = getattr(user, "display_name", None) or getattr(user, "name", f"Usuario_{ssrc or 'voz'}")
                        bot_log(f"🎙️ [Gemini Live VAD] Voz detectada de '{u_name}' (RMS: {rms})")
                    if len(state["frames"]) >= self.max_speech_frames:
                        frames = state["frames"][:]
                        state["frames"].clear()
                        state["in_speech"] = False
                        asyncio.run_coroutine_threadsafe(self.process_speech_turn(state["user"], frames, ssrc=state.get("ssrc")), self.loop)
                elif state["in_speech"]:
                    if len(state["frames"]) < self.max_speech_frames:
                        state["frames"].append(pcm)
                    if (now - state["last_speech_time"]) >= self.silence_timeout:
                        frames = state["frames"][:]
                        state["frames"].clear()
                        state["in_speech"] = False
                        if len(frames) >= self.min_speech_frames:
                            asyncio.run_coroutine_threadsafe(self.process_speech_turn(state["user"], frames, ssrc=state.get("ssrc")), self.loop)
        except Exception as e:
            bot_log(f"Aviso en GeminiLiveVoiceSink.write: {e}")

    async def _watchdog(self):
        """Vigila pausas de voz cuando Discord suspende el envío de paquetes (voice gate) y auto-resucita el listener si se cae."""
        while self._is_active:
            try:
                await asyncio.sleep(0.15)
                client = self.vc or getattr(self, "voice_client", None)
                if not client or not client.is_connected() or not getattr(client, "channel", None):
                    continue
                guild_id = getattr(getattr(client, "guild", None), "id", None)
                if guild_id and is_voice_manually_disconnected(guild_id):
                    self.cleanup()
                    break
                if hasattr(client, "is_listening") and not client.is_listening():
                    bot_log("⚠️ [Gemini Live Watchdog] AudioReader detenido. Reactivando escucha automáticamente...")
                    try:
                        client.listen(self)
                        bot_log("✅ [Gemini Live Watchdog] Escucha reactivada con éxito.")
                    except Exception as ex:
                        bot_log(f"Error reactivando listener de voz: {ex}")

                now = time.time()
                turns = []
                with self._lock:
                    for uid, state in list(self.user_buffers.items()):
                        if state["in_speech"] and (now - state["last_speech_time"]) >= self.silence_timeout:
                            frames = state["frames"][:]
                            state["frames"].clear()
                            state["in_speech"] = False
                            user = state["user"]
                            ssrc = state.get("ssrc")
                            if len(frames) >= self.min_speech_frames:
                                turns.append((user, frames, ssrc))
                                u_name = getattr(user, "display_name", None) or getattr(user, "name", f"Usuario_{ssrc or 'voz'}")
                                bot_log(f"🎙️ [VAD Fin Silencio] Turno completado para '{u_name}' ({len(frames)} tramas). Procesando...")
                for u, f, s in turns:
                    asyncio.create_task(self.process_speech_turn(u, f, ssrc=s))
            except asyncio.CancelledError:
                break
            except Exception as e:
                bot_log(f"Aviso en watchdog de voz: {e}")

    async def send_dictation_to_channel(self, client, user: discord.Member, text: str, user_spoken: str = "") -> bool:
        """Envía un mensaje dictado por voz desde Gemini Live al chat de texto correspondiente."""
        try:
            guild = getattr(client, "guild", None)
            target_ch = None

            # Si el usuario nombró un canal de texto existente por su nombre (ej: "en el chat general", "en el canal torneos")
            if guild and user_spoken:
                u_spoken_lower = user_spoken.lower()
                for tch in getattr(guild, "text_channels", []):
                    c_clean = re.sub(r'[^a-zA-Z0-9]', '', tch.name.lower())
                    if len(c_clean) >= 4 and re.search(r'\b(?:canal|chat)\s+(?:de\s+)?' + re.escape(c_clean) + r'\b', u_spoken_lower):
                        target_ch = tch
                        break

            # Si no especificó otro canal, el destino por defecto es el canal de la llamada actual
            if not target_ch:
                target_ch = getattr(client, "channel", None)

            u_name = getattr(user, "display_name", None) or getattr(user, "name", "Usuario")
            msg_content = f"🎙️ **{u_name}** *(vía Gemini Live)*: {text}"

            sent = False
            if target_ch and hasattr(target_ch, "send"):
                try:
                    await target_ch.send(msg_content)
                    sent = True
                    bot_log(f"💬 [Gemini Live Chat] Dictado de '{u_name}' enviado a #{target_ch.name}: \"{text}\"")
                except Exception as ex_send:
                    bot_log(f"Aviso enviando dictado a #{getattr(target_ch, 'name', '')}: {ex_send}")

            # Fallback si el canal de voz no acepta mensajes o dio error
            if not sent and guild:
                fallback_ch = None
                v_ch = getattr(client, "channel", None)
                if v_ch and getattr(v_ch, "category", None):
                    for tch in v_ch.category.text_channels:
                        fallback_ch = tch
                        break
                if not fallback_ch:
                    fallback_ch = guild.system_channel or (guild.text_channels[0] if guild.text_channels else None)

                if fallback_ch and hasattr(fallback_ch, "send"):
                    await fallback_ch.send(msg_content)
                    bot_log(f"💬 [Gemini Live Chat Fallback] Dictado de '{u_name}' enviado a #{fallback_ch.name}: \"{text}\"")
                    sent = True

            return sent
        except Exception as e:
            bot_log(f"Error enviando dictado a chat: {e}")
            return False

    async def process_speech_turn(self, user: discord.Member, frames: list, ssrc: int = None):
        if not self._is_active:
            return
        try:
            client = self.vc or getattr(self, "voice_client", None)
            if not client or not (client.is_connected() or getattr(client, "is_listening", lambda: False)() or getattr(client, "channel", None)):
                return
            if hasattr(client, "_connection") and not client.is_connected():
                try:
                    from discord.voice_state import ConnectionFlowState
                    client._connection.state = ConnectionFlowState.connected
                except Exception:
                    pass

            if user is None and client and ssrc:
                uid = getattr(client, "_get_id_from_ssrc", lambda s: None)(ssrc)
                if uid and getattr(client, "guild", None):
                    user = client.guild.get_member(uid)

            if user is None and getattr(client, "channel", None):
                humans = [m for m in client.channel.members if not m.bot]
                if len(humans) == 1:
                    user = humans[0]

            raw_pcm = b"".join(frames)
            mono_pcm = pcm_stereo_to_mono_48k(raw_pcm)
            if not mono_pcm:
                return

            duration_s = round(len(mono_pcm) / (48000 * 2), 2)
            if duration_s < 0.35:
                return

            count_m = len(mono_pcm) // 2
            shorts_m = struct.unpack(f"<{count_m}h", mono_pcm)
            max_amp = max(abs(s) for s in shorts_m) if count_m > 0 else 0
            if max_amp < 350 and duration_s < 0.8:
                return

            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(mono_pcm)
            wav_bytes = wav_io.getvalue()
            b64_audio = base64.b64encode(wav_bytes).decode("utf-8")

            user_name = getattr(user, "display_name", None) or getattr(user, "name", None) or f"Usuario_{ssrc or 'voz'}"
            user_id = getattr(user, "id", None)
            user_mem = get_user_memory_ctx(user_id) if user_id else ""
            channel_name = getattr(getattr(client, "channel", None), "name", "llamada")
            guild_name = getattr(getattr(client, "guild", None), "name", "Servidor")
            channel_members = getattr(getattr(client, "channel", None), "members", [])
            members_str = ", ".join([m.display_name for m in channel_members if not m.bot]) or user_name
            bot_log(f"🎙️ [Gemini Live Turno] Procesando audio de '{user_name}' ({len(frames)} tramas, {duration_s}s, {len(wav_bytes)} B)...")

            # Guardar el audio en disco para que el usuario y el agente puedan escucharlo/auditarlo
            clean_uname = re.sub(r'[^a-zA-Z0-9_\-]', '', user_name)[:20] or "Usuario"
            turn_timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{turn_timestamp_str}_{clean_uname}_{int(time.time()*1000)%100000}.wav"
            file_path = os.path.join(RECORDINGS_DIR, filename)
            try:
                with open(file_path, "wb") as f_wav:
                    f_wav.write(wav_bytes)
            except Exception as e_w:
                bot_log(f"Aviso guardando archivo audio: {e_w}")

            now = time.time()
            record_entry = {
                "id": filename.replace(".wav", ""),
                "timestamp": get_spain_now_str(),
                "epoch": now,
                "user": user_name,
                "user_id": str(user_id) if user_id else None,
                "duration_s": duration_s,
                "filename": filename,
                "audio_url": f"/audios/file/{filename}",
                "transcription": "",
                "bot_reply": "",
                "status": "procesando"
            }
            with VOICE_TURNS_LOCK:
                VOICE_TURNS_LOG.append(record_entry)
            save_recordings_metadata()

            time_since_last_reply = now - getattr(self, "last_bot_reply_time", 0.0)
            is_dialogue_active = time_since_last_reply < 25.0

            history_lines = []
            for item in self.recent_turns[-3:]:
                if len(item) == 3:
                    u_n, u_t, b_txt = item
                    history_lines.append(f"- {u_n}: \"{u_t}\" -> Asistente: \"{b_txt}\"")
                elif len(item) == 2:
                    spk, b_txt = item
                    history_lines.append(f"- Asistente (con {spk}): {b_txt}")
            hist_ctx = "\n".join(history_lines) if history_lines else "Sin intervenciones previas recientes."

            spain_now_str = get_spain_now_str()
            prompt = (
                f"Eres el transcriptor acústico y asistente de voz en tiempo real del canal '{channel_name}' en Discord (España).\n"
                f"Tu nombre es estrictamente 'Asistente' (también respondes si dicen 'bot').\n"
                f"Gente en la sala de voz: {members_str}.\n"
                f"Usuario en este turno de voz: '{user_name}'.\n\n"
                f"ÚLTIMAS INTERVENCIONES EN LA LLAMADA:\n{hist_ctx}\n\n"
                f"INSTRUCCIONES CLAVE:\n"
                f"1. PASO 1 - TRANSCRIBE EL AUDIO DEL USUARIO CON MÁXIMA FIDELIDAD ACÚSTICA:\n"
                f"   - Escucha de forma estrictamente literal lo que suena en el archivo de audio.\n"
                f"   - Transcribe únicamente las palabras reales pronunciadas por '{user_name}'.\n"
                f"   - ESTRICTAMENTE PROHIBIDO inventar palabras, completar frases inexistentes o asumir preguntas habituales (como la hora o saludos) si no se oyen con total claridad fonética en el audio.\n"
                f"   - Si es un chasquido, respiración, ruido de fondo, golpe de micro, teclado o silencio, transcribe exactamente: [Ruido] o [Silencio].\n"
                f"   - Si solo son risas o carcajadas sin palabras, escribe: [Risas]\n\n"
                f"2. PASO 2 - REGLA OBLIGATORIA DE INTERVENCIÓN:\n"
                f"   - Los miembros del canal suelen estar jugando o hablando entre ellos.\n"
                f"   - REGLA DE ORO: Si en la frase transcrita el usuario NO menciona explícitamente la palabra 'asistente' o 'bot', tu Respuesta DEBE ser estrictamente: [IGNORAR].\n"
                f"   - Si dicen 'asistente' o 'bot', responde de forma concisa, útil y directa a lo que soliciten (1-2 frases).\n"
                f"   - Si te piden callar explícitamente ('cállate asistente', 'silencio asistente', 'shh'): pon Respuesta: [SILENCIO]\n"
                f"   - Si te piden salir de la llamada ('asistente sal de la llamada', 'asistente vete', 'bot desconéctate'): pon Respuesta: [DESCONECTAR]\n"
                f"   - Si te piden buscar algo en internet ('asistente busca...', 'asistente qué tiempo hace'): pon Respuesta: [BUSCAR: <términos>]\n"
                f"   - Si te piden escribir o enviar un mensaje al chat ('asistente pon en el chat...', 'asistente escribe en el chat...', 'bot manda al chat...'): pon Respuesta: [CHAT: <mensaje exacto a enviar>] acompañado de una confirmación hablada breve (ej: [CHAT: voy en 5 minutos] Ya lo he puesto en el chat).\n\n"
                f"3. FORMATO DE SALIDA ESTRICTO:\n"
                f"Oído: <texto transcrito, o [Risas], o [Ruido], o [Silencio]>\n"
                f"Respuesta: <respuesta para locutar, o [IGNORAR], o [SILENCIO], o [DESCONECTAR], o [BUSCAR: <términos>], o [CHAT: <mensaje>]>\n\n"
                f"[DATOS DE REFERENCIA SI PREGUNTAN]: Hora peninsular de España actual: {spain_now_str}."
            )

            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "audio/wav", "data": b64_audio}}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.15,
                    "maxOutputTokens": 600
                }
            }
            data = json.dumps(payload).encode("utf-8")
            response_text = ""
            # Modelos multimodales verificados con cuota disponible inmediata (respetando Circuit Breaker)
            for model_name in get_available_models():
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
                try:
                    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                    def call_api(r=req):
                        with urllib.request.urlopen(r, timeout=7) as resp:
                            return json.loads(resp.read().decode("utf-8"))
                    res = await asyncio.to_thread(call_api)
                    candidates = res.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        response_text = candidates[0]["content"]["parts"][0]["text"].strip()
                        if response_text:
                            break
                except urllib.error.HTTPError as e:
                    if e.code in (429, 500, 503):
                        mark_model_cooldown(model_name, 60)
                    else:
                        bot_log(f"Aviso HTTP {e.code} API Gemini Live ({model_name}): {e}")
                    continue
                except Exception as e:
                    bot_log(f"Aviso API Gemini Live ({model_name}): {e}")
                    continue

            if not response_text:
                bot_log("⚠️ [Gemini Live] Ningún modelo respondió satisfactoriamente para la intervención de voz.")

            user_spoken = ""
            bot_reply = response_text
            if "Respuesta:" in response_text:
                parts = response_text.split("Respuesta:", 1)
                bot_reply = parts[1].strip()
                if "Oído:" in parts[0]:
                    user_spoken = parts[0].replace("Oído:", "").strip()
            elif "Oído:" in response_text:
                parts = response_text.split("Oído:", 1)
                bot_reply = parts[0].strip()
                user_spoken = parts[1].strip()

            record_entry["transcription"] = user_spoken or "(audio procesado)"

            # Detección estricta de orden de desconexión por voz mediante patrones regex (evitar falsos positivos como 'salte de ahí' o 'vete al punto')
            # Se quitan las etiquetas del transcriptor ([Silencio], [Ruido], [Risas]): no son palabras del usuario y
            # '[Silencio]' casaba con el patrón de orden de silencio, cortando el audio del bot en cada turno sin voz
            u_clean = re.sub(r"\[[^\]]*\]", " ", user_spoken).lower().strip()
            disconnect_patterns = [
                r"\b(vete|sal|salte|descon[eé]ctate|m[aá]rchate|l[aá]rgate)\s+(de\s+la\s+llamada|del\s+canal|de\s+voz|de\s+aqu[ií])\b",
                r"\b(asistente|bot)\s+(salte|vete|descon[eé]ctate|l[aá]rgate)\b",
                r"\b(abandona\s+la\s+llamada)\b",
                r"\b(a\s+la\s+(puta\s+)?calle\s+bot)\b"
            ]
            explicit_disconnect_intent = any(re.search(pat, u_clean) for pat in disconnect_patterns)
            is_disconnect_cmd = (
                "[DESCONECTAR]" in response_text or 
                "[DESCONECTAR]" in bot_reply or 
                explicit_disconnect_intent
            )

            if is_disconnect_cmd:
                record_entry["status"] = "desconectado"
                record_entry["bot_reply"] = "[DESCONECTAR]"
                save_recordings_metadata()
                guild_id = client.guild.id if hasattr(client, "guild") and client.guild else None
                if guild_id:
                    set_voice_manually_disconnected(guild_id)
                bot_log(f"🔌 [Gemini Live Desconectar] '{user_name}' pidió desconectar ('{user_spoken}'). Saliendo de la sala.")
                if client.is_playing():
                    client.stop()
                try:
                    await client.disconnect(force=True)
                except Exception as ex_dc:
                    bot_log(f"Aviso al desconectar por voz: {ex_dc}")
                return

            # Detección estricta de silencio (evitar falsos positivos con 'dispara', 'bastante', 'callao', etc.)
            silence_patterns = [
                r"\b(c[aá]llate|silencio|shh+|calla|para\s+ya|para\s+de\s+hablar|cierra\s+el\s+pico|cierra\s+la\s+boca)\b",
                r"\b(asistente|bot)\s+(c[aá]llate|silencio|calla|para)\b",
                r"\b(otra\s+m[aá]s\s+y\s+te\s+vas)\b"
            ]
            explicit_silence_intent = any(re.search(pat, u_clean) for pat in silence_patterns)
            is_silence_cmd = (
                "[SILENCIO]" in response_text or 
                "[SILENCIO]" in bot_reply or 
                explicit_silence_intent
            )

            if is_silence_cmd:
                record_entry["status"] = "silenciado"
                record_entry["bot_reply"] = "[SILENCIO]"
                save_recordings_metadata()
                bot_log(f"🤫 [Gemini Live Silencio] Orden de silencio de '{user_name}'. Cortando audio.")
                if client.is_playing():
                    client.stop()
                return

            # REGLA ESTRICTA SOLICITADA POR EL USUARIO:
            # Ignorar cualquier mensaje que no tenga la palabra 'asistente' o 'bot' en la frase transcrita
            has_wake_word = bool(re.search(r"\b(asistente|bot)\b", u_clean))
            is_ignored_sound = any(tag in user_spoken for tag in ["[ININTELIGIBLE]", "[Risas]", "[Ruido]", "[Silencio]"])
            if not has_wake_word or not bot_reply or "[IGNORAR]" in bot_reply or bot_reply.strip() == "IGNORAR" or is_ignored_sound:
                record_entry["status"] = "ignorado"
                record_entry["bot_reply"] = "[IGNORAR]"
                save_recordings_metadata()
                bot_log(f"🎙️ [Gemini Live Filtro Asistente] '{user_name}' ('{user_spoken}') -> [IGNORAR] (Wake word: {has_wake_word})")
                return

            # Manejo de búsqueda web en tiempo real por voz
            if "[BUSCAR:" in bot_reply:
                m_search = re.search(r"\[BUSCAR:\s*([^\]]+)\]", bot_reply, re.IGNORECASE)
                if m_search:
                    search_q = m_search.group(1).strip()
                    bot_log(f"🔍 [Gemini Live Web Search] Buscando en internet para voz: '{search_q}'")
                    web_ctx = await asyncio.to_thread(search_web_lite, search_q, 3)
                    if web_ctx:
                        search_summary_prompt = (
                            f"Estás en vivo por voz en Discord con '{user_name}'.\n"
                            f"El usuario preguntó: '{user_spoken}'.\n"
                            f"Resultados de internet:\n{web_ctx}\n\n"
                            f"Resume la respuesta en 2 frases claras, amables y directas para locutar por voz en español de España (sin markdown ni emojis):"
                        )
                        sum_payload = {
                            "contents": [{"parts": [{"text": search_summary_prompt}]}],
                            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 300}
                        }
                        s_data = json.dumps(sum_payload).encode("utf-8")
                        search_summary_done = False
                        for s_model in get_available_models():
                            s_url = f"https://generativelanguage.googleapis.com/v1beta/models/{s_model}:generateContent?key={GEMINI_KEY}"
                            s_req = urllib.request.Request(s_url, data=s_data, headers={"Content-Type": "application/json"})
                            try:
                                def _call_s(r=s_req):
                                    with urllib.request.urlopen(r, timeout=8) as r_resp:
                                        return json.loads(r_resp.read().decode("utf-8"))
                                s_res = await asyncio.to_thread(_call_s)
                                if s_res.get("candidates") and "content" in s_res["candidates"][0]:
                                    bot_reply = s_res["candidates"][0]["content"]["parts"][0]["text"].strip()
                                    if bot_reply:
                                        search_summary_done = True
                                        break
                            except urllib.error.HTTPError as e_http:
                                if e_http.code in (429, 500, 503):
                                    mark_model_cooldown(s_model, 60)
                                else:
                                    bot_log(f"Aviso HTTP {e_http.code} resumen búsqueda voz ({s_model}): {e_http}")
                                continue
                            except Exception as e_sum:
                                bot_log(f"Aviso resumen búsqueda voz ({s_model}): {e_sum}")
                                continue
                        if not search_summary_done:
                            bot_reply = f"He buscado sobre {search_q}, pero no he podido sintetizar los resultados en este instante."
                    else:
                        bot_reply = f"He buscado en internet sobre {search_q}, pero no he encontrado datos claros ahora mismo."

            if "[VOZ:" in bot_reply:
                m_v = re.search(r"\[VOZ:\s*([a-zA-Z0-9_-]+)\]", bot_reply, re.IGNORECASE)
                if m_v:
                    target_v = m_v.group(1).lower()
                    if target_v in ["alvaro", "elvira", "ximena", "abril"]:
                        self.voice_type = target_v
                        bot_log(f"🎙️ [Gemini Live Voz] Voz cambiada en llamada a '{self.voice_type}' por orden de '{user_name}'")
                bot_reply = re.sub(r"\[VOZ:\s*([a-zA-Z0-9_-]+)\]", "", bot_reply).strip()

            # Manejo de dictado a chat de texto por voz ("asistente pon en el chat...", "escribe en el chat...")
            chat_patterns = [
                r"\b(?:pon|escribe|manda|env[ií]a|di|dile)\s+(?:en\s+el|al|por\s+el)\s+chat\b",
                r"\b(?:pon|escribe|manda|env[ií]a)\s+(?:un\s+mensaje|esto)\s+(?:en\s+el|al)\s+chat\b",
                r"\b(?:escribe|manda|env[ií]a)\s+al\s+canal\b",
            ]
            has_chat_pattern = any(re.search(pat, u_clean) for pat in chat_patterns)
            if "[CHAT:" in bot_reply or has_chat_pattern:
                chat_msg_to_send = ""
                m_chat = re.search(r"\[CHAT:\s*([^\]]+)\]", bot_reply, re.IGNORECASE)
                if m_chat:
                    chat_msg_to_send = m_chat.group(1).strip()
                    bot_reply = re.sub(r"\[CHAT:\s*([^\]]+)\]", "", bot_reply).strip()
                elif has_chat_pattern:
                    m_ext = re.search(r"(?:chat|canal)\s*(?:que\s+|:\s*|\s+)?(.*)", u_clean, re.IGNORECASE)
                    if m_ext and m_ext.group(1).strip():
                        chat_msg_to_send = m_ext.group(1).strip()

                if chat_msg_to_send:
                    chat_msg_to_send = chat_msg_to_send.strip(' "\'')
                    await self.send_dictation_to_channel(client, user, chat_msg_to_send, user_spoken=user_spoken)
                    if not bot_reply or bot_reply.strip() == "":
                        bot_reply = "Listo, ya lo he puesto en el chat."

            clean_resp = clean_text_for_tts(bot_reply)
            if not clean_resp:
                record_entry["status"] = "vacio"
                save_recordings_metadata()
                return

            # Protección contra auto-interrupción: si ya está reproduciendo y el audio entrante fue muy breve, no cortar
            if client.is_playing():
                if len(frames) < 22 and any(greeting in clean_resp.lower() for greeting in ["qué pasa", "dime", "hola"]):
                    bot_log("🎙️ [Gemini Live Overlap] Ignorando interrupción menor para no cortar audio en curso.")
                    return
                client.stop()

            record_entry["status"] = "respondido"
            record_entry["bot_reply"] = clean_resp
            save_recordings_metadata()
            bot_log(f"🎙️ [Gemini Live] '{user_name}' dijo: \"{user_spoken}\" -> Asistente: \"{clean_resp}\"")
            self.last_bot_reply_time = time.time()
            self.recent_turns.append((user_name, user_spoken, clean_resp))
            if len(self.recent_turns) > 8:
                self.recent_turns.pop(0)

            try:
                audio_file = await generate_speech_audio(clean_resp, voice_type=self.voice_type)
                async with self.playback_lock:
                    play_audio_in_voice(client, audio_file)
                bot_log(f"🔊 [Gemini Live] Audio enviado a #{channel_name}")
            except Exception as ex:
                bot_log(f"Error reproduciendo voz Gemini Live: {ex}")
        except Exception as ex_turn:
            bot_log(f"Aviso procesando turno de voz: {ex_turn}")

    def cleanup(self):
        self._is_active = False
        if self.watchdog_task and not self.watchdog_task.done():
            self.watchdog_task.cancel()
        with self._lock:
            self.user_buffers.clear()

async def ensure_voice_connection(channel: discord.VoiceChannel, auto: bool = False) -> voice_recv.VoiceRecvClient:
    """Asegura la conexión del bot a una sala de voz con Gemini Live bidireccional activo.
    auto=True para las uniones automáticas (watchdog, auto-join): respetan el bloqueo y no lo levantan."""
    if channel and channel.guild and not auto:
        clear_voice_manually_disconnected(channel.guild.id)
    if not discord.opus.is_loaded():
        for opus_lib in ["libopus.so.0", "libopus.so", "opus", "libopus-0.x86_64.so"]:
            try:
                discord.opus.load_opus(opus_lib)
                if discord.opus.is_loaded():
                    break
            except Exception:
                pass

    vc = channel.guild.voice_client
    if vc is not None:
        if isinstance(vc, voice_recv.VoiceRecvClient) and (vc.is_connected() or getattr(vc, "is_listening", lambda: False)()):
            if hasattr(vc, "_connection") and not vc.is_connected():
                try:
                    from discord.voice_state import ConnectionFlowState
                    vc._connection.state = ConnectionFlowState.connected
                except Exception:
                    pass
            if vc.channel.id != channel.id:
                bot_log(f"🎙️ [Voice Move] Moviendo Asistente de #{vc.channel.name} a #{channel.name}...")
                await vc.move_to(channel)
            if not vc.is_listening():
                sink = GeminiLiveVoiceSink(vc, bot.loop)
                vc.listen(sink)
            return vc
        else:
            try:
                if hasattr(vc, "stop_listening"):
                    vc.stop_listening()
                if vc.is_playing():
                    if hasattr(vc, "stop_playing"):
                        vc.stop_playing()
                    else:
                        vc.stop()
                mark_internal_voice_disconnect(channel.guild.id)
                await vc.disconnect(force=True)
            except Exception:
                pass
            await asyncio.sleep(0.5)

    bot_log(f"🎙️ [Voice Connect] Conectando Asistente a #{channel.name} (ID: {channel.id})...")
    vc = await channel.connect(cls=voice_recv.VoiceRecvClient, timeout=15.0, reconnect=True, self_deaf=False)
    if hasattr(vc, "_connection") and not vc.is_connected():
        try:
            from discord.voice_state import ConnectionFlowState
            vc._connection.state = ConnectionFlowState.connected
        except Exception:
            pass
    sink = GeminiLiveVoiceSink(vc, bot.loop)
    vc.listen(sink)
    bot_log(f"🎙️ [Voice Connected] Conexión establecida y escuchando en #{channel.name}")
    return vc

def play_audio_in_voice(voice_client: discord.VoiceClient, audio_path: str):
    """Reproduce el audio en el canal de voz usando FFmpegPCMAudio y elimina el archivo al terminar."""
    if hasattr(voice_client, "_connection") and not voice_client.is_connected():
        try:
            from discord.voice_state import ConnectionFlowState
            voice_client._connection.state = ConnectionFlowState.connected
        except Exception:
            pass

    if hasattr(voice_client, "stop_playing"):
        voice_client.stop_playing()
    elif voice_client.is_playing():
        voice_client.stop()
        
    def after_play(err):
        if err:
            print(f"Aviso reproducción de voz: {err}")
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

    audio_source = discord.FFmpegPCMAudio(audio_path)
    voice_client.play(audio_source, after=after_play)

def fetch_steam_game(query: str) -> dict:
    """Busca en Steam Store y devuelve ficha completa con precios en EUR, descuento y detalles."""
    try:
        encoded = urllib.parse.quote(query.strip())
        search_url = f"https://store.steampowered.com/api/storesearch/?term={encoded}&l=spanish&cc=ES"
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("items", [])
            if not items:
                return None
            app_id = items[0]["id"]
        
        detail_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=es&l=spanish"
        req2 = urllib.request.Request(detail_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req2, timeout=6) as resp2:
            d = json.loads(resp2.read().decode("utf-8"))
            game_data = d.get(str(app_id), {}).get("data", {})
            return game_data
    except Exception as e:
        print(f"Error consultando Steam Store: {e}")
        return None

def get_tribunal_query_ctx(text: str) -> str:
    """Busca menciones a juegos de El Tribunal Gaming y devuelve su ficha resumida."""
    low = text.lower()
    if not any(k in low for k in ["tribunal", "nota", "veredicto", "muro", "vergüenza", "cooperativo", "salvavidas", "guerreros", "pesados"]):
        return ""
    for g in tribunal_data.get("single", []):
        t = g.get("title", "")
        if len(t) > 3 and t.lower() in low:
            hltb = g.get("hltb", {})
            return f"\n[FICHA EN EL TRIBUNAL GAMING: '{t}']:\n  * Metacritic: {g.get('metacritic', 'N/D')}\n  * HLTB: Historia {hltb.get('main', 'N/D')}, Completo {hltb.get('completionist', 'N/D')}\n  * Géneros: {', '.join(g.get('genres', [])[:3])}\n  * Web oficial: https://tribunal-gaming.vercel.app"
    for g in tribunal_data.get("coop", []):
        t = g.get("title", "")
        if len(t) > 3 and t.lower() in low:
            return f"\n[FICHA COOPERATIVO EN EL TRIBUNAL GAMING: '{t}']:\n  * Categoría: {g.get('category', 'Coop')}\n  * Estado: {g.get('availability')}\n  * Rendimiento: {g.get('perf', 'N/D')}\n  * Web oficial: https://tribunal-gaming.vercel.app"
    return ""

def get_steam_query_ctx(text: str) -> str:
    """Detecta si se pregunta por el precio o ficha de Steam de un juego y aporta datos frescos."""
    low = text.lower()
    if not any(k in low for k in ["steam", "precio", "cuanto vale", "cuánto vale", "cuanto cuesta", "cuánto cuesta", "oferta", "descuento"]):
        return ""
    clean = re.sub(r"\b(steam|precio|de|cuanto|cuánto|vale|cuesta|oferta|descuento|en|el|juego|porfa|asistente)\b", "", low).strip()
    if len(clean) >= 3:
        game = fetch_steam_game(clean)
        if game:
            p = game.get("price_overview", {})
            price_str = f"{p.get('final_formatted', 'N/D')}" + (f" (-{p.get('discount_percent')}% oferta)" if p.get("discount_percent", 0) > 0 else "") if p else ("Gratis" if game.get("is_free") else "Precio no disponible")
            meta = game.get("metacritic", {}).get("score", "Sin nota")
            return f"\n[FICHA STEAM STORE EN VIVO: '{game.get('name')}']:\n  * Precio actual: {price_str}\n  * Metacritic: {meta}\n  * URL: https://store.steampowered.com/app/{game.get('steam_appid')}/"
    return ""

user_cooldowns = {}
COOLDOWN_SECONDS = 3

TEXT_EXTENSIONS = {
    ".txt", ".py", ".js", ".ts", ".json", ".csv", ".md", ".cpp", ".c", ".h",
    ".java", ".html", ".css", ".xml", ".yaml", ".yml", ".sh", ".bat", ".ps1", ".log"
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

_LIVE_LEVELS_CACHE = {}
_LIVE_LEVELS_CACHE_TIME = 0.0
_LIVE_LEVELS_TTL = 300.0
_LIVE_LEVELS_LOCK = asyncio.Lock()

async def get_live_levels_dict(guild: discord.Guild) -> dict:
    """Lee el canal #bots para extraer los niveles reales de Cakey Bot de cada usuario (con caché en memoria de 300s y protección de concurrencia)."""
    global _LIVE_LEVELS_CACHE, _LIVE_LEVELS_CACHE_TIME
    if not guild:
        return {}
    now = time.time()
    # Fast-path sin lock si la caché está vigente
    if _LIVE_LEVELS_CACHE_TIME > 0 and (now - _LIVE_LEVELS_CACHE_TIME < _LIVE_LEVELS_TTL):
        return dict(_LIVE_LEVELS_CACHE)

    async with _LIVE_LEVELS_LOCK:
        now = time.time()
        # Doble verificación dentro del lock por si otra corrutina ya actualizó la caché
        if _LIVE_LEVELS_CACHE_TIME > 0 and (now - _LIVE_LEVELS_CACHE_TIME < _LIVE_LEVELS_TTL):
            return dict(_LIVE_LEVELS_CACHE)

        bots_channel = discord.utils.find(lambda c: "bots" in c.name.lower(), guild.text_channels)
        if not bots_channel:
            return dict(_LIVE_LEVELS_CACHE)
        levels = {}
        try:
            async for m in bots_channel.history(limit=120):
                if m.author.bot and m.content:
                    # Patrón: ¡Enhorabuena <@ID>! Has alcanzado el nivel X o ¡Ascenso para <@ID>! Ya estás en nivel X
                    match = re.search(r"<@!?(\d+)>.*?nivel\s*(\d+)", m.content, re.IGNORECASE)
                    if match:
                        uid = int(match.group(1))
                        lvl = int(match.group(2))
                        if uid not in levels or lvl > levels[uid]:
                            levels[uid] = lvl
            # Fusión acumulativa: no borrar usuarios conocidos de turnos previos
            for uid, lvl in levels.items():
                if uid not in _LIVE_LEVELS_CACHE or lvl > _LIVE_LEVELS_CACHE[uid]:
                    _LIVE_LEVELS_CACHE[uid] = lvl
            # Registrar marca temporal aunque el canal estuviera silencioso para no martillear la API
            _LIVE_LEVELS_CACHE_TIME = now
        except Exception as e:
            bot_log(f"Aviso lectura niveles #bots: {e}")
            if _LIVE_LEVELS_CACHE:
                return dict(_LIVE_LEVELS_CACHE)
        return dict(_LIVE_LEVELS_CACHE)

def search_web_lite(query: str, max_results: int = 5) -> str:
    """Busca en internet en tiempo real y devuelve los mejores resultados con título y snippet."""
    if not query or len(query.strip()) < 3:
        return ""
    url = "https://html.duckduckgo.com/html/"
    data = urllib.parse.urlencode({"q": query}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}
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
            if prev.author != bot.user and len(prev_content) > 3:
                return f"{prev_content} {clean_no_punct}".strip()
                
    return clean_no_punct

def calculate_xp_gap(start_lvl: int, target_lvl: int) -> str:
    """Calcula matemáticamente el XP exacto necesario entre dos niveles y desglosa por canales estándar y con boost."""
    if start_lvl < 0 or start_lvl >= target_lvl or target_lvl > 100:
        return ""
    total = sum(5 * (lvl ** 2) + 50 * lvl + 100 for lvl in range(start_lvl, target_lvl))
    msgs_base = round(total / 225)
    hours_voice_base = round(total / 1500, 1)

    # Canales con Boost de XP según INFO_SERVIDOR.md
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

def fetch_url_content(url: str) -> str:
    """Descarga y limpia el texto legible de una página web."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            }
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
                        "data": b64
                    }
                })
            elif ctype == "application/pdf" or ext == ".pdf":
                b64 = base64.b64encode(raw_bytes).decode("utf-8")
                parts.append({
                    "inlineData": {
                        "mimeType": "application/pdf",
                        "data": b64
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

def extract_action_block(text: str, tag_name: str):
    """
    Extrae bloques de acción [TAG_NAME: ...] soportando corchetes anidados
    (como arr[0] en código o [a, b] en fórmulas LaTeX y Mermaid) sin truncamientos accidentales.
    Delimita la búsqueda antes de cualquier acción posterior para evitar contaminación cruzada.
    Devuelve (full_match_str, content_str) o None si no existe la etiqueta.
    """
    prefix = f"[{tag_name.upper()}:"
    lower_text = text.lower()
    lower_prefix = prefix.lower()
    start_pos = lower_text.find(lower_prefix)
    if start_pos == -1:
        return None
    
    content_start = start_pos + len(prefix)
    
    # Buscar el inicio de cualquier acción posterior para no rebasarla nunca
    next_action_match = re.search(r"\[ACTION_[A-Z_]+:", text[content_start:], re.IGNORECASE)
    search_limit = content_start + next_action_match.start() if next_action_match else len(text)
    search_text = text[:search_limit]

    depth = 1
    end_pos = -1
    in_quote = None
    in_comment = False
    escaped = False
    is_code = tag_name.upper() in ("ACTION_CODE", "ACTION_CHART")
    
    idx = content_start
    while idx < search_limit:
        ch = search_text[idx]
        if escaped:
            escaped = False
            idx += 1
            continue
        if ch == '\\':
            escaped = True
            idx += 1
            continue

        if is_code:
            # Comentarios de código: ignorar caracteres y comillas hasta el fin de línea
            if in_comment:
                if ch == '\n':
                    in_comment = False
                idx += 1
                continue
            elif ch == '#' and in_quote is None:
                in_comment = True
                idx += 1
                continue

            # Strings literales en código
            if in_quote is not None:
                if len(in_quote) == 3:
                    if search_text.startswith(in_quote, idx):
                        idx += 3
                        in_quote = None
                        continue
                else:
                    if ch == in_quote:
                        in_quote = None
                    elif ch == '\n':
                        in_quote = None
                idx += 1
                continue
            else:
                if search_text.startswith('"""', idx):
                    in_quote = '"""'
                    idx += 3
                    continue
                elif search_text.startswith("'''", idx):
                    in_quote = "'''"
                    idx += 3
                    continue
                elif ch in ('"', "'"):
                    in_quote = ch
                    idx += 1
                    continue

        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                end_pos = idx
                break
        idx += 1
                
    if end_pos != -1:
        return text[start_pos : end_pos + 1], text[content_start : end_pos]
    else:
        # Fallback acotado estrictamente antes de la siguiente acción
        last_bracket = text.rfind(']', content_start, search_limit)
        if last_bracket != -1:
            return text[start_pos : last_bracket + 1], text[content_start : last_bracket]
        else:
            return text[start_pos : search_limit], text[content_start : search_limit]

def generate_image_flux(prompt: str, width: int = 1024, height: int = 1024) -> bytes:
    """Genera una imagen en alta resolución usando el clúster libre de FLUX.1 / Stable Diffusion."""
    encoded_prompt = urllib.parse.quote(prompt.strip())
    seed = int(time.time() * 1000) % 1000000
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true&seed={seed}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=35) as resp:
        return resp.read()

def _parse_latex_braces(s: str, start: int):
    """Parsea llaves anidadas en LaTeX para extraer de forma segura numeradores y denominadores."""
    if start >= len(s) or s[start] != '{':
        return None, start
    depth = 0
    content = []
    i = start
    while i < len(s):
        if s[i] == '{':
            depth += 1
            if depth > 1:
                content.append('{')
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return "".join(content), i + 1
            else:
                content.append('}')
        else:
            content.append(s[i])
        i += 1
    return None, start

def replace_frac(text: str) -> str:
    """Convierte comandos \\frac{num}{den} en expresiones legibles (num)/(den)."""
    idx = 0
    while True:
        pos = text.find(r"\frac", idx)
        if pos == -1:
            break
        first_brace = text.find('{', pos)
        if first_brace == -1 or text[pos+5:first_brace].strip() != "":
            idx = pos + 5
            continue
        num, next_pos = _parse_latex_braces(text, first_brace)
        if num is None:
            idx = pos + 5
            continue
        while next_pos < len(text) and text[next_pos].isspace():
            next_pos += 1
        den, end_pos = _parse_latex_braces(text, next_pos)
        if den is None:
            idx = pos + 5
            continue
        replacement = f"({num.strip()})/({den.strip()})"
        text = text[:pos] + replacement + text[end_pos:]
        idx = pos + len(replacement)
    return text

def sanitize_discord_math_text(text: str) -> str:
    """Sustituye código LaTeX residual por símbolos legibles en Discord para evitar aspecto de 'chino'.
    Protege bloques de código (```...``` y `...`) para que el código fuente nunca sea alterado."""
    if not text:
        return text

    placeholders = []
    def repl_code(match):
        idx = len(placeholders)
        placeholders.append(match.group(0))
        return f"\x00CODE_BLOCK_{idx}\x00"

    protected_text = re.sub(r"```[\s\S]*?```|`[^`\n]+`", repl_code, text)

    replacements = [
        (r"\\cdot", "·"),
        (r"\\times", "×"),
        (r"\\div", "÷"),
        (r"\\pm", "±"),
        (r"\\mp", "∓"),
        (r"\\infty", "∞"),
        (r"\\neq", "≠"),
        (r"\\leq", "≤"),
        (r"\\geq", "≥"),
        (r"\\approx", "≈"),
        (r"\\in", "∈"),
        (r"\\notin", "∉"),
        (r"\\forall", "∀"),
        (r"\\exists", "∃"),
        (r"\\to", "→"),
        (r"\\rightarrow", "→"),
        (r"\\leftarrow", "←"),
        (r"\\Rightarrow", "⇒"),
        (r"\\Leftarrow", "⇐"),
        (r"\\iff", "⇔"),
        (r"\\alpha", "α"),
        (r"\\beta", "β"),
        (r"\\gamma", "γ"),
        (r"\\theta", "θ"),
        (r"\\pi", "π"),
        (r"\\sigma", "σ"),
        (r"\\lambda", "λ"),
        (r"\\Delta", "Δ"),
        (r"\\Omega", "Ω"),
    ]
    res = protected_text
    for pat, rep in replacements:
        res = re.sub(pat, rep, res)
    res = replace_frac(res)
    res = re.sub(r"\\sqrt\{([^{}]+)\}", r"√(\1)", res)
    res = re.sub(r"\\lim_\{([^{}]+)\}", r"lím(\1)", res)
    res = re.sub(r"\\text\{([^{}]+)\}", r"\1", res)
    res = re.sub(r"\{([^{}]+)\}", r"\1", res)
    res = re.sub(r"\$\$([^\$]+)\$\$", r"\1", res)
    res = re.sub(r"(?<!\w)\$([^\$\n]+)\$(?!\w)", r"\1", res)

    for idx, block in enumerate(placeholders):
        res = res.replace(f"\x00CODE_BLOCK_{idx}\x00", block)

    return res


def render_math_image(latex_code: str) -> bytes:
    """Convierte una fórmula LaTeX en una tarjeta gráfica PNG de alta resolución con fondo oscuro para Discord."""
    clean_latex = latex_code.strip().strip("$")
    encoded = urllib.parse.quote(clean_latex)
    # Renderizado 200 DPI con fondo Discord #1e1f22 y texto blanco nítido
    url = f"https://latex.codecogs.com/png.image?\\dpi{{200}}\\bg{{1e1f22}}\\color{{white}}{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()

def render_chart_image(chart_json_str: str) -> bytes:
    """Genera un gráfico estadístico o función matemática (líneas, barras, tarta) mediante QuickChart."""
    config = json.loads(chart_json_str) if isinstance(chart_json_str, str) else chart_json_str
    # Añadir estilo oscuro por defecto si no lo tiene
    if "options" not in config:
        config["options"] = {}
    config["options"]["legend"] = config["options"].get("legend", {})
    config["options"]["legend"]["labels"] = {"fontColor": "#ffffff"}
    
    url = "https://quickchart.io/chart"
    payload = {"chart": config, "backgroundColor": "#1e1f22", "width": 800, "height": 450}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()

def render_diagram_image(mermaid_code: str) -> bytes:
    """Genera un diagrama de flujo o esquema a partir de código Mermaid."""
    clean_code = mermaid_code.strip().replace("```mermaid", "").replace("```", "").strip()
    code_b64 = base64.b64encode(clean_code.encode("utf-8")).decode("ascii")
    url = f"https://mermaid.ink/img/{code_b64}?bgColor=1e1f22"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()

def render_code_card_image(code_str: str) -> bytes:
    """Renderiza una tarjeta gráfica de código limpia estilo ventana terminal con Pillow."""
    from PIL import Image, ImageDraw
    lines = code_str.strip().replace("```", "").strip().split("\n")[:25]
    max_len = max(len(l) for l in lines) if lines else 20
    w = max(550, min(1000, 40 + max_len * 9))
    h = 45 + len(lines) * 22
    img = Image.new("RGB", (w, h), color="#1e1f22")
    draw = ImageDraw.Draw(img)
    # Botones terminal estilo macOS
    draw.ellipse((14, 12, 24, 22), fill="#ed6a5e")
    draw.ellipse((30, 12, 40, 22), fill="#f5bf4f")
    draw.ellipse((46, 12, 56, 22), fill="#62c554")
    draw.line([(0, 32), (w, 32)], fill="#2b2d31", width=1)
    
    y = 40
    for l in lines:
        draw.text((20, y), l, fill="#e0e0e0")
        y += 22
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def enhance_image_prompt(user_text: str, author_name: str = "") -> str:
    """Traduce y optimiza el prompt del usuario al inglés con detalles visuales cinematográficos."""
    clean = re.sub(r"\b(crea|genera|hazme|haz|dibuja|dibújame|dibujame|puedes|una|un|imagen|foto|dibujo|de|porfa|oye|asistente)\b", "", user_text, flags=re.IGNORECASE).strip()
    if not clean:
        clean = "cyberpunk anime warrior"
    
    if author_name:
        clean = re.sub(r"\b(yo|mí|mi)\b", author_name, clean, flags=re.IGNORECASE)
    
    prompt_enhancer = (
        f"You are an expert prompt engineer for FLUX.1 and Stable Diffusion image generation. "
        f"Convert this concept into a single, detailed, visually stunning English prompt (maximum 35 words). "
        f"Include art style, lighting, atmosphere, characters, actions and composition. "
        f"Return ONLY the final prompt text without quotes or explanations.\n"
        f"Concept: {clean}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt_enhancer}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 100}
    }
    data = json.dumps(payload).encode("utf-8")
    for model_name in get_available_models():
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                candidates = res.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    enhanced = candidates[0]["content"]["parts"][0]["text"].strip()
                    if enhanced and len(enhanced) > 5:
                        return enhanced
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                mark_model_cooldown(model_name, 60)
            continue
        except Exception:
            continue
            
    if "vs" in clean.lower() or "contra" in clean.lower():
        return f"An epic 1v1 battle, {clean}, intense clash, glowing energy aura, dynamic action angle, detailed digital art, cinematic lighting"
    return f"{clean}, high quality digital art, detailed, dramatic lighting, cinematic 8k wallpaper"

def call_gemini_multiturn(turns: list) -> str:
    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": turns,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }
    
    data = json.dumps(payload).encode("utf-8")
    models_to_try = get_available_models()
    
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
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
            except Exception as ex:
                mark_model_cooldown(model_name, 45)
                break
                
    return "Cuota de IA temporalmente saturada. Se restablece en unos momentos automáticamente."

# ==========================================
# COMPONENTES INTERACTIVOS (discord.ui)
# ==========================================

class ImageActionView(discord.ui.View):
    """Botonera interactiva para creaciones de imágenes con FLUX.1."""
    def __init__(self, prompt: str, author_id: int):
        super().__init__(timeout=300)
        self.prompt = prompt
        self.author_id = author_id

    @discord.ui.button(label="Re-roll", style=discord.ButtonStyle.primary, emoji="🔄")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        try:
            img_bytes = await asyncio.to_thread(generate_image_flux, self.prompt)
            file = discord.File(io.BytesIO(img_bytes), filename="reroll_flux.png")
            new_view = ImageActionView(self.prompt, self.author_id)
            await interaction.followup.send(
                content=f"🔄 **Nueva versión (Re-roll) para {interaction.user.display_name}:**\n> *\"{self.prompt[:120]}\"*",
                file=file,
                view=new_view
            )
        except Exception as e:
            await interaction.followup.send(f"⚠️ Error generando re-roll: {e}", ephemeral=True)

class SteamView(discord.ui.View):
    """Botones oficiales de acceso directo a Steam Store y Comunidad."""
    def __init__(self, app_id: int or str):
        super().__init__(timeout=None)
        if app_id:
            self.add_item(discord.ui.Button(label="Abrir en Steam", url=f"https://store.steampowered.com/app/{app_id}/", emoji="🛒"))
            self.add_item(discord.ui.Button(label="Comunidad & Guías", url=f"https://steamcommunity.com/app/{app_id}/", emoji="👥"))

class TribunalView(discord.ui.View):
    """Botones interactivos para El Tribunal Gaming."""
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(discord.ui.Button(label="Ver en Web", url="https://tribunal-gaming.vercel.app", emoji="🌐"))

    @discord.ui.button(label="Juego Aleatorio", style=discord.ButtonStyle.secondary, emoji="🎲")
    async def random_game_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        pool = tribunal_data.get("single", []) + tribunal_data.get("coop", [])
        if not pool:
            await interaction.response.send_message("No hay juegos en la base de datos.", ephemeral=True)
            return
        g = random.choice(pool)
        title = g.get("title", "Juego")
        if "metacritic" in g:
            meta = g.get("metacritic", "N/D")
            desc = g.get("description", "")[:180]
            hltb = g.get("hltb", {}).get("main", "N/D")
            msg = f"🎲 **Recomendación Aleatoria:** **{title}**\n⭐ Metacritic: **{meta}** | ⏱️ Historia: **{hltb}**\n_{desc}..._"
        else:
            cat = g.get("category", "Coop")
            perf = g.get("perf", "Sin notas")
            msg = f"🎲 **Cooperativo Aleatorio:** **{title}** ({cat})\n⚙️ Rendimiento: {perf}"
        await interaction.response.send_message(msg, ephemeral=False)

RECENT_TRIVIA_IDS = collections.deque(maxlen=40)

CATEGORY_ALIASES = {
    "all": "all",
    "manhwa": "manhwa",
    "manhwas": "manhwa",
    "anime": "manhwa",
    "gaming": "gaming",
    "videojuegos": "gaming",
    "juegos": "gaming",
    "tribunal": "tribunal",
    "lore": "lore",
    "servidor": "lore",
    "general": "general",
    "cultura": "general"
}

TRIVIA_CATEGORIES_INFO = {
    "all": ("todas las categorías de cultura pop, videojuegos, anime, manhwas y curiosidades generales", "🎲 Trivial General"),
    "manhwa": ("manhwas coreanos (Solo Leveling, The Greatest Estate Developer, Omniscient Reader, Tower of God, Lookism) y series icónicas de anime", "🎌 Manhwas & Anime"),
    "gaming": ("videojuegos célebres, FromSoftware (Elden Ring, Dark Souls), Hollow Knight, Brawl Stars, Nintendo, RPGs y clásicos", "🎮 Videojuegos"),
    "tribunal": ("El Tribunal Gaming (juegos cooperativos, Muro de la Vergüenza, rendimiento técnico, Iván racerwasp y Jose)", "⚖️ El Tribunal Gaming"),
    "lore": ("lore y anécdotas del servidor de Discord 'LOS MONGOLOS DEL SANVI', Terreneiror (Lázaro) y la tragaperras, Joselito, Iván, Cakey Bot y UnbelievaBoat", "📜 Lore del Servidor & Colegas"),
    "general": ("cultura general, ciencia, astronomía, historia, tecnología y geografía mundial", "🧠 Cultura General"),
}

def generate_gemini_trivia_question(category_key: str = "all") -> dict | None:
    """Genera dinámicamente con IA de Gemini una pregunta inédita de opción múltiple estructurada en JSON."""
    cat_key_clean = CATEGORY_ALIASES.get(category_key.lower(), category_key.lower())
    cat_desc, cat_name = TRIVIA_CATEGORIES_INFO.get(cat_key_clean, TRIVIA_CATEGORIES_INFO["all"])

    prompt = (
        f"Eres el creador de preguntas de trivial para el servidor de Discord 'LOS MONGOLOS DEL SANVI'.\n"
        f"Genera exactamente UNA pregunta inédita, entretenida y de dificultad media/alta sobre la temática: {cat_desc}.\n"
        f"Requisitos obligatorios:\n"
        f"1. La pregunta debe ser clara y en español.\n"
        f"2. Debe tener exactamente 4 opciones de respuesta verosímiles en una lista de texto (ninguna repetida).\n"
        f"3. Solo una opción es la correcta.\n"
        f"4. Proporciona una explicación breve (1-2 frases) del porqué de la respuesta correcta.\n"
        f"5. Devuelve EXCLUSIVAMENTE un objeto JSON válido con los campos:\n"
        f"   {{\n"
        f"     \"category\": \"{cat_key_clean if cat_key_clean != 'all' else 'general'}\",\n"
        f"     \"category_name\": \"{cat_name}\",\n"
        f"     \"question\": \"¿Texto de la pregunta?\",\n"
        f"     \"options\": [\"Opción A\", \"Opción B\", \"Opción C\", \"Opción D\"],\n"
        f"     \"correct\": 0,\n"
        f"     \"explanation\": \"Explicación concisa.\"\n"
        f"   }}\n"
        f"NO incluyas bloques de código markdown, comillas de inicio ni texto adicional fuera del JSON."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 600,
            "responseMimeType": "application/json"
        }
    }
    data = json.dumps(payload).encode("utf-8")

    if not GEMINI_KEY:
        return None

    for model_name in get_available_models():
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode("utf-8"))
            text = res.get("candidates", [])[0]["content"]["parts"][0]["text"].strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
                text = re.sub(r"\s*```$", "", text)
            q_data = json.loads(text)
            if (
                isinstance(q_data, dict)
                and "question" in q_data
                and isinstance(q_data.get("options"), list)
                and len(q_data["options"]) == 4
                and isinstance(q_data.get("correct"), int)
                and 0 <= q_data["correct"] <= 3
                and "explanation" in q_data
            ):
                q_data["category_name"] = cat_name
                q_data["category"] = cat_key_clean if cat_key_clean != "all" else "general"
                return q_data
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503):
                mark_model_cooldown(model_name, 60)
        except Exception:
            pass

    return None

async def handle_next_trivia(interaction: discord.Interaction, category_key: str = "all"):
    """Lanza la siguiente pregunta de trivial con soporte dinámico de IA si se agota el banco local."""
    await interaction.response.defer()
    trivia_pool = load_trivia_data()
    cat_val = CATEGORY_ALIASES.get(category_key.lower(), category_key.lower())
    
    question = None
    ia_notice = ""

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
        # Fallback dinámico a Gemini al agotarse las preguntas inéditas locales
        gemini_q = await asyncio.to_thread(generate_gemini_trivia_question, cat_val)
        if gemini_q:
            question = gemini_q
            ia_notice = "✨ *Preguntas locales agotadas recientemente. ¡Pregunta inédita generada en vivo por Gemini IA!*\n\n"
        elif pool:
            question = random.choice(pool)

    if not question:
        await interaction.followup.send("❌ No se pudo cargar una nueva pregunta de Trivial.", ephemeral=True)
        return

    if "id" in question:
        RECENT_TRIVIA_IDS.append(question["id"])

    letters = ["🇦", "🇧", "🇨", "🇩"]
    opts_txt = "\n".join([f"{letters[i]} **{opt}**" for i, opt in enumerate(question["options"][:4])])

    embed = discord.Embed(
        title=f"❓ Trivial: {question.get('category_name', 'Pregunta')}",
        description=f"{ia_notice}**{question['question']}**\n\n{opts_txt}\n\n*Pulsa el botón con la respuesta correcta abajo. ¡El primero en acertar se lleva 10 puntos!*",
        color=0x3b82f6
    )
    embed.set_footer(text="Trivial Asistente • 60 segundos para responder • /ranking_trivial")
    new_view = TriviaView(question, interaction.user.id, category_key)
    msg = await interaction.followup.send(embed=embed, view=new_view, wait=True)
    new_view.message = msg

class TriviaView(discord.ui.View):
    """Botonera interactiva para rondas de preguntas de Trivial."""
    def __init__(self, question_data: dict, author_id: int, category_key: str = "all"):
        super().__init__(timeout=60)
        self.question_data = question_data
        self.author_id = author_id
        self.category_key = category_key
        self.answered = False
        self.message: discord.Message = None

        letters = ["A", "B", "C", "D"]
        for i, opt in enumerate(question_data.get("options", [])[:4]):
            btn = discord.ui.Button(
                label=f"{letters[i]}: {opt[:70]}",
                style=discord.ButtonStyle.primary
            )
            btn.callback = self.make_callback(i)
            self.add_item(btn)

    def make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            if not self.message and interaction.message:
                self.message = interaction.message
            if self.answered:
                await interaction.response.send_message("⚠️ Esta pregunta ya ha sido respondida.", ephemeral=True)
                return
            self.answered = True

            for item in self.children:
                item.disabled = True

            correct_idx = self.question_data.get("correct", 0)
            is_correct = (index == correct_idx)
            user = interaction.user
            uid_str = str(user.id)

            if uid_str not in user_memory:
                user_memory[uid_str] = {
                    "name": user.display_name,
                    "display_name": user.display_name,
                    "username": user.name,
                    "role_in_server": user.top_role.name if getattr(user, "top_role", None) else "Miembro",
                    "fav_genres": [],
                    "fav_works": [],
                    "notes": [],
                    "trivia_points": 0
                }
            else:
                user_memory[uid_str]["display_name"] = user.display_name
                user_memory[uid_str]["name"] = user.display_name

            if correct_idx < len(self.children):
                self.children[correct_idx].style = discord.ButtonStyle.success
            if not is_correct and index < len(self.children):
                self.children[index].style = discord.ButtonStyle.danger

            pts_gain = 10 if is_correct else 0
            user_memory[uid_str]["trivia_points"] = user_memory[uid_str].get("trivia_points", 0) + pts_gain
            save_user_memory(user_memory)
            total_pts = user_memory[uid_str]["trivia_points"]

            color = 0x22c55e if is_correct else 0xef4444
            title = "🎉 ¡RESPUESTA CORRECTA! (+10 pts)" if is_correct else "❌ ¡RESPUESTA INCORRECTA!"
            status_desc = (
                f"**{user.display_name}** acertó: **{self.question_data['options'][correct_idx]}**"
                if is_correct
                else f"**{user.display_name}** eligió '{self.question_data['options'][index]}', pero la correcta era: **{self.question_data['options'][correct_idx]}**"
            )

            # Botón interactivo para continuar jugando con la siguiente pregunta
            next_btn = discord.ui.Button(label="🔄 Siguiente Pregunta", style=discord.ButtonStyle.secondary, row=2)
            async def next_callback(next_interaction: discord.Interaction):
                next_btn.disabled = True
                try:
                    await next_interaction.message.edit(view=self)
                except Exception:
                    pass
                await handle_next_trivia(next_interaction, self.category_key)
            next_btn.callback = next_callback
            self.add_item(next_btn)

            embed = discord.Embed(
                title=title,
                description=f"{status_desc}\n\n💡 **Explicación:** {self.question_data.get('explanation', '')}\n\n🏆 Puntos acumulados de {user.display_name}: **{total_pts} pts**",
                color=color
            )
            embed.set_footer(text=f"Categoría: {self.question_data.get('category_name', 'Trivial')} • Usa /ranking_trivial o pulsa Siguiente Pregunta")
            await interaction.response.edit_message(embed=embed, view=self)

        return callback

    async def on_timeout(self):
        if not self.answered:
            self.answered = True
            for item in self.children:
                item.disabled = True
            correct_idx = self.question_data.get("correct", 0)
            if correct_idx < len(self.children):
                self.children[correct_idx].style = discord.ButtonStyle.success

            next_btn = discord.ui.Button(label="🔄 Siguiente Pregunta", style=discord.ButtonStyle.secondary, row=2)
            async def next_callback(next_interaction: discord.Interaction):
                next_btn.disabled = True
                try:
                    await next_interaction.message.edit(view=self)
                except Exception:
                    pass
                await handle_next_trivia(next_interaction, self.category_key)
            next_btn.callback = next_callback
            self.add_item(next_btn)

            if self.message:
                try:
                    embed = discord.Embed(
                        title="⌛ Tiempo Agotado",
                        description=f"Se acabaron los 60 segundos.\n\nLa respuesta correcta era: **{self.question_data['options'][correct_idx]}**\n\n💡 **Explicación:** {self.question_data.get('explanation', '')}",
                        color=0x6b7280
                    )
                    embed.set_footer(text=f"Categoría: {self.question_data.get('category_name', 'Trivial')} • Usa /ranking_trivial o pulsa Siguiente Pregunta")
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    pass

# ==========================================
# MOTOR INTERACTIVO DE TRES EN RAYA (TIC-TAC-TOE)
# ==========================================

def check_ttt_winner_and_line(board: list) -> tuple:
    """Comprueba si hay 3 en raya en el tablero y devuelve (ganador, tupla_linea)."""
    lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Filas
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Columnas
        (0, 4, 8), (2, 4, 6)              # Diagonales
    ]
    for a, b, c in lines:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a], (a, b, c)
    return None, None

def tictactoe_minimax(board: list, is_maximizing: bool, depth: int = 0) -> int:
    """Evaluación Minimax exhaustiva para IA de Tres en Raya con ponderación de profundidad."""
    winner, _ = check_ttt_winner_and_line(board)
    if winner == "O":
        return 10 - depth
    elif winner == "X":
        return depth - 10
    elif "" not in board:
        return 0

    if is_maximizing:
        best = -1000
        for i in range(9):
            if board[i] == "":
                board[i] = "O"
                val = tictactoe_minimax(board, False, depth + 1)
                board[i] = ""
                best = max(best, val)
        return best
    else:
        best = 1000
        for i in range(9):
            if board[i] == "":
                board[i] = "X"
                val = tictactoe_minimax(board, True, depth + 1)
                board[i] = ""
                best = min(best, val)
        return best

def get_tictactoe_bot_move(board: list) -> int:
    """Devuelve la mejor casilla para el bot (O) usando victoria inmediata, bloqueo y Minimax."""
    # 1. Comprobar victoria inmediata del bot
    for i in range(9):
        if board[i] == "":
            board[i] = "O"
            if check_ttt_winner_and_line(board)[0] == "O":
                board[i] = ""
                return i
            board[i] = ""

    # 2. Bloquear victoria inmediata del rival (X)
    for i in range(9):
        if board[i] == "":
            board[i] = "X"
            if check_ttt_winner_and_line(board)[0] == "X":
                board[i] = ""
                return i
            board[i] = ""

    # 3. Minimax
    best_score = -1000
    best_move = -1
    for i in range(9):
        if board[i] == "":
            board[i] = "O"
            score = tictactoe_minimax(board, False, depth=1)
            board[i] = ""
            if score > best_score:
                best_score = score
                best_move = i
    return best_move if best_move != -1 else board.index("")

class TicTacToeButton(discord.ui.Button):
    def __init__(self, index: int, row: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=row)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view
        await view.process_click(interaction, self.index)

class TicTacToeView(discord.ui.View):
    """Botonera interactiva en cuadrícula 3x3 para Tres en Raya."""
    def __init__(self, player_x: discord.User | discord.Member, player_o: discord.User | discord.Member | None):
        super().__init__(timeout=120)
        self.player_x = player_x
        self.player_o = player_o
        self.is_pve = (player_o is None)
        self.board = [""] * 9
        self.current_turn = "X"
        self.finished = False
        self.winner = None
        self.winning_line = None
        self.message: discord.Message = None

        for i in range(9):
            row = i // 3
            self.add_item(TicTacToeButton(i, row))

    def build_embed(self) -> discord.Embed:
        if self.is_pve:
            rival_desc = f"❌ **{self.player_x.display_name}** vs ⭕ **Asistente (IA)**"
        else:
            rival_desc = f"❌ **{self.player_x.display_name}** vs ⭕ **{self.player_o.display_name}**"

        if self.finished:
            if self.winner == "X":
                title = f"🏆 ¡Victoria de {self.player_x.display_name}!"
                desc = f"{rival_desc}\n\n🎉 ¡**{self.player_x.display_name}** (❌) ha ganado la partida formando 3 en raya!"
                color = 0x22c55e
            elif self.winner == "O":
                winner_name = "Asistente" if self.is_pve else self.player_o.display_name
                title = f"🏆 ¡Victoria de {winner_name}!"
                desc = f"{rival_desc}\n\n🎉 ¡**{winner_name}** (⭕) ha ganado la partida formando 3 en raya!"
                color = 0x3b82f6
            elif self.winner == "tie":
                title = "🤝 ¡Empate!"
                desc = f"{rival_desc}\n\nTablero completo sin ganador. ¡Tablas bien disputadas!"
                color = 0xf59e0b
            else:
                title = "⌛ Partida finalizada"
                desc = f"{rival_desc}\n\nLa partida ha finalizado."
                color = 0x6b7280
        else:
            turn_name = self.player_x.display_name if self.current_turn == "X" else ("Asistente" if self.is_pve else self.player_o.display_name)
            symbol = "❌" if self.current_turn == "X" else "⭕"
            title = f"🎮 Tres en Raya — Turno de {symbol} {turn_name}"
            desc = f"{rival_desc}\n\nEs el turno de **{turn_name}** ({symbol}). Pulsa una casilla vacía para mover."
            color = 0x8b5cf6

        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text="Tres en Raya interactivo • /tres_en_raya • 120s de inactividad")
        return embed

    def update_buttons(self):
        for item in self.children:
            if isinstance(item, TicTacToeButton):
                val = self.board[item.index]
                if val == "X":
                    item.label = "❌"
                    item.style = discord.ButtonStyle.danger
                    item.disabled = True
                elif val == "O":
                    item.label = "⭕"
                    item.style = discord.ButtonStyle.primary
                    item.disabled = True
                else:
                    item.label = "\u200b"
                    item.style = discord.ButtonStyle.secondary
                    item.disabled = self.finished

        if self.winning_line:
            for idx in self.winning_line:
                self.children[idx].style = discord.ButtonStyle.success

    async def process_click(self, interaction: discord.Interaction, index: int):
        if not self.message and interaction.message:
            self.message = interaction.message
        if self.finished:
            await interaction.response.send_message("⚠️ Esta partida ya ha concluido.", ephemeral=True)
            return

        if self.current_turn == "X":
            if interaction.user.id != self.player_x.id:
                await interaction.response.send_message(f"❌ No es tu turno. Le toca a {self.player_x.display_name} (❌).", ephemeral=True)
                return
        else:
            if self.is_pve:
                await interaction.response.send_message("❌ Es el turno del bot Asistente.", ephemeral=True)
                return
            if interaction.user.id != self.player_o.id:
                await interaction.response.send_message(f"❌ No es tu turno. Le toca a {self.player_o.display_name} (⭕).", ephemeral=True)
                return

        if self.board[index] != "":
            await interaction.response.send_message("❌ Esa casilla ya está ocupada.", ephemeral=True)
            return

        self.board[index] = self.current_turn
        win, line = check_ttt_winner_and_line(self.board)
        if win:
            self.finished = True
            self.winner = win
            self.winning_line = line
        elif "" not in self.board:
            self.finished = True
            self.winner = "tie"
        else:
            if self.current_turn == "X":
                self.current_turn = "O"
                if self.is_pve:
                    bot_move = get_tictactoe_bot_move(self.board)
                    if bot_move is not None:
                        self.board[bot_move] = "O"
                        bot_win, bot_line = check_ttt_winner_and_line(self.board)
                        if bot_win:
                            self.finished = True
                            self.winner = bot_win
                            self.winning_line = bot_line
                        elif "" not in self.board:
                            self.finished = True
                            self.winner = "tie"
                        else:
                            self.current_turn = "X"
            else:
                self.current_turn = "X"

        self.update_buttons()
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if not self.finished:
            self.finished = True
            self.winner = "timeout"
            for item in self.children:
                item.disabled = True
            embed = self.build_embed()
            embed.title = "⌛ Partida Cancelada por Inactividad"
            embed.description += "\n\n*Han transcurrido 2 minutos sin jugadas.*"
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    pass

# ==========================================
# MOTOR INTERACTIVO DE CONECTA 4
# ==========================================

def check_connect4_winner(board: list) -> tuple:
    """Comprueba 4 en raya (horizontal, vertical, diagonal) y devuelve (ganador, celdas_ganadoras)."""
    # Horizontal
    for r in range(6):
        for c in range(4):
            if board[r][c] != 0 and board[r][c] == board[r][c+1] == board[r][c+2] == board[r][c+3]:
                return board[r][c], [(r, c), (r, c+1), (r, c+2), (r, c+3)]
    # Vertical
    for r in range(3):
        for c in range(7):
            if board[r][c] != 0 and board[r][c] == board[r+1][c] == board[r+2][c] == board[r+3][c]:
                return board[r][c], [(r, c), (r+1, c), (r+2, c), (r+3, c)]
    # Diagonal \
    for r in range(3):
        for c in range(4):
            if board[r][c] != 0 and board[r][c] == board[r+1][c+1] == board[r+2][c+2] == board[r+3][c+3]:
                return board[r][c], [(r, c), (r+1, c+1), (r+2, c+2), (r+3, c+3)]
    # Diagonal /
    for r in range(3, 6):
        for c in range(4):
            if board[r][c] != 0 and board[r][c] == board[r-1][c+1] == board[r-2][c+2] == board[r-3][c+3]:
                return board[r][c], [(r, c), (r-1, c+1), (r-2, c+2), (r-3, c+3)]
    return 0, None

def drop_connect4_piece(board: list, col: int, player: int) -> int:
    """Deja caer una ficha en la columna indicada. Devuelve la fila ocupada o -1 si está llena."""
    if col < 0 or col >= 7 or board[0][col] != 0:
        return -1
    for r in range(5, -1, -1):
        if board[r][col] == 0:
            board[r][col] = player
            return r
    return -1

def get_connect4_bot_move(board: list, bot_player: int = 2, human_player: int = 1) -> int:
    """IA heurística estratégica para Conecta 4: victoria inmediata, bloqueo y ponderación central."""
    valid_cols = [c for c in range(7) if board[0][c] == 0]
    if not valid_cols:
        return -1

    # 1. Comprobar victoria inmediata del bot
    for c in valid_cols:
        r = drop_connect4_piece(board, c, bot_player)
        win, _ = check_connect4_winner(board)
        board[r][c] = 0
        if win == bot_player:
            return c

    # 2. Bloquear victoria inmediata del rival humano
    for c in valid_cols:
        r = drop_connect4_piece(board, c, human_player)
        win, _ = check_connect4_winner(board)
        board[r][c] = 0
        if win == human_player:
            return c

    # 3. Filtrar columnas donde poner ficha permita al rival ganar justo encima en su siguiente turno
    safe_cols = []
    for c in valid_cols:
        r = drop_connect4_piece(board, c, bot_player)
        rival_wins_above = False
        if r > 0:
            board[r-1][c] = human_player
            w, _ = check_connect4_winner(board)
            if w == human_player:
                rival_wins_above = True
            board[r-1][c] = 0
        board[r][c] = 0
        if not rival_wins_above:
            safe_cols.append(c)

    candidates = safe_cols if safe_cols else valid_cols

    # 4. Ponderación posicional y evaluación táctica de amenazas futuras
    col_weights = {3: 8, 2: 5, 4: 5, 1: 3, 5: 3, 0: 1, 6: 1}
    best_score = -1000
    best_c = candidates[0]
    for c in candidates:
        r = drop_connect4_piece(board, c, bot_player)
        score = col_weights.get(c, 0)
        # Bonificación si esta jugada crea una amenaza de 4 en raya para el bot en su siguiente turno
        threats = 0
        for next_c in [nc for nc in range(7) if board[0][nc] == 0]:
            nr = drop_connect4_piece(board, next_c, bot_player)
            w, _ = check_connect4_winner(board)
            board[nr][next_c] = 0
            if w == bot_player:
                threats += 1
        score += threats * 15
        board[r][c] = 0
        if score > best_score:
            best_score = score
            best_c = c
    return best_c

class Connect4Button(discord.ui.Button):
    def __init__(self, col: int, row_pos: int):
        super().__init__(style=discord.ButtonStyle.primary, label=f"{col+1}", row=row_pos)
        self.col = col

    async def callback(self, interaction: discord.Interaction):
        view: Connect4View = self.view
        await view.process_drop(interaction, self.col)

class Connect4View(discord.ui.View):
    """Botonera y tablero interactivo de Conecta 4 (6 filas x 7 columnas)."""
    def __init__(self, player_1: discord.User | discord.Member, player_2: discord.User | discord.Member | None):
        super().__init__(timeout=120)
        self.player_1 = player_1  # 🔴
        self.player_2 = player_2  # 🟡
        self.is_pve = (player_2 is None)
        self.board = [[0 for _ in range(7)] for _ in range(6)]
        self.current_turn = 1
        self.finished = False
        self.winner = 0
        self.winning_cells = None
        self.message: discord.Message = None

        for c in range(7):
            row_pos = 0 if c < 4 else 1
            self.add_item(Connect4Button(c, row_pos))

    def render_board_str(self) -> str:
        header = "1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣\n"
        symbols = {0: "⬛", 1: "🔴", 2: "🟡"}
        lines = []
        for r in range(6):
            row_str = ""
            for c in range(7):
                if self.winning_cells and (r, c) in self.winning_cells:
                    row_str += "⭐ "
                else:
                    row_str += f"{symbols[self.board[r][c]]} "
            lines.append(row_str.strip())
        return header + "\n".join(lines)

    def build_embed(self) -> discord.Embed:
        p2_name = "Asistente (IA)" if self.is_pve else self.player_2.display_name
        players_header = f"🔴 **{self.player_1.display_name}** vs 🟡 **{p2_name}**"

        if self.finished:
            if self.winner == 1:
                title = f"🏆 ¡Victoria de {self.player_1.display_name}!"
                desc = f"{players_header}\n\n{self.render_board_str()}\n\n🎉 ¡**{self.player_1.display_name}** (🔴) ha conectado 4 en raya!"
                color = 0xef4444
            elif self.winner == 2:
                title = f"🏆 ¡Victoria de {p2_name}!"
                desc = f"{players_header}\n\n{self.render_board_str()}\n\n🎉 ¡**{p2_name}** (🟡) ha conectado 4 en raya!"
                color = 0xf59e0b
            elif self.winner == -1:
                title = "🤝 ¡Empate en Conecta 4!"
                desc = f"{players_header}\n\n{self.render_board_str()}\n\nTablero completamente lleno sin 4 en raya. ¡Partida muy reñida!"
                color = 0x3b82f6
            else:
                title = "⌛ Partida Finalizada"
                desc = f"{players_header}\n\n{self.render_board_str()}\n\nPartida terminada."
                color = 0x6b7280
        else:
            turn_name = self.player_1.display_name if self.current_turn == 1 else p2_name
            turn_sym = "🔴" if self.current_turn == 1 else "🟡"
            title = f"🔴🟡 Conecta 4 — Turno de {turn_sym} {turn_name}"
            desc = f"{players_header}\n\n{self.render_board_str()}\n\nTurno de **{turn_name}** ({turn_sym}). Pulsa el número de la columna para soltar la ficha."
            color = 0x8b5cf6

        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text="Conecta 4 interactivo • /conecta4 • 120s de inactividad")
        return embed

    def update_buttons(self):
        for item in self.children:
            if isinstance(item, Connect4Button):
                is_full = (self.board[0][item.col] != 0)
                item.disabled = (self.finished or is_full)

    async def process_drop(self, interaction: discord.Interaction, col: int):
        if not self.message and interaction.message:
            self.message = interaction.message
        if self.finished:
            await interaction.response.send_message("⚠️ Esta partida ya ha finalizado.", ephemeral=True)
            return

        if self.current_turn == 1:
            if interaction.user.id != self.player_1.id:
                await interaction.response.send_message(f"❌ No es tu turno. Le toca a {self.player_1.display_name} (🔴).", ephemeral=True)
                return
        else:
            if self.is_pve:
                await interaction.response.send_message("❌ Es el turno del bot Asistente.", ephemeral=True)
                return
            if interaction.user.id != self.player_2.id:
                await interaction.response.send_message(f"❌ No es tu turno. Le toca a {self.player_2.display_name} (🟡).", ephemeral=True)
                return

        r = drop_connect4_piece(self.board, col, self.current_turn)
        if r == -1:
            await interaction.response.send_message("❌ Esa columna ya está completa. Elige otra.", ephemeral=True)
            return

        winner, winning_cells = check_connect4_winner(self.board)
        if winner != 0:
            self.finished = True
            self.winner = winner
            self.winning_cells = winning_cells
        elif all(self.board[0][c] != 0 for c in range(7)):
            self.finished = True
            self.winner = -1
        else:
            if self.current_turn == 1:
                self.current_turn = 2
                if self.is_pve:
                    bot_col = get_connect4_bot_move(self.board, bot_player=2, human_player=1)
                    if bot_col != -1:
                        drop_connect4_piece(self.board, bot_col, 2)
                        b_winner, b_cells = check_connect4_winner(self.board)
                        if b_winner != 0:
                            self.finished = True
                            self.winner = b_winner
                            self.winning_cells = b_cells
                        elif all(self.board[0][c] != 0 for c in range(7)):
                            self.finished = True
                            self.winner = -1
                        else:
                            self.current_turn = 1
            else:
                self.current_turn = 1

        self.update_buttons()
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if not self.finished:
            self.finished = True
            self.winner = 0
            for item in self.children:
                item.disabled = True
            embed = self.build_embed()
            embed.title = "⌛ Partida Cancelada por Inactividad"
            embed.description += "\n\n*Han transcurrido 2 minutos sin jugadas.*"
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    pass

# ==========================================
# COMANDOS SLASH NATIVOS (discord.app_commands)
# ==========================================

@tree.command(name="dibuja", description="Genera una imagen en alta resolución con el motor FLUX.1")
@app_commands.describe(
    prompt="Describe la escena, personajes o idea que quieres generar",
    estilo="Elige un estilo artístico para la imagen"
)
@app_commands.choices(estilo=[
    app_commands.Choice(name="🎨 Anime / Manga Shonen", value="anime style, highly detailed shonen anime aesthetic, vivid colors, dynamic lighting"),
    app_commands.Choice(name="🌃 Cyberpunk / Neón", value="cyberpunk aesthetic, futuristic neon lights, dark sci-fi city, dramatic reflections, cinematic"),
    app_commands.Choice(name="📸 Fotorrealista / Cine", value="photorealistic 8k, cinematic movie still, 35mm lens, natural volumetric lighting, depth of field"),
    app_commands.Choice(name="👾 Pixel Art Retro", value="16-bit pixel art style, detailed retro game graphics, vibrant pixel palette"),
    app_commands.Choice(name="🖼️ Óleo Clásico / Pintura", value="classical oil painting, textured brush strokes, dramatic chiaroscuro lighting, masterpiece")
])
async def cmd_dibuja(interaction: discord.Interaction, prompt: str, estilo: app_commands.Choice[str] = None):
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
            view=view
        )
    except Exception as e:
        await interaction.followup.send(f"⚠️ Error generando la imagen: {e}. Inténtalo de nuevo en unos momentos.")

@tree.command(name="steam", description="Consulta el precio oficial, ofertas y detalles de un juego en Steam")
@app_commands.describe(juego="Nombre del juego en Steam")
async def cmd_steam(interaction: discord.Interaction, juego: str):
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
        color=0x1b2838
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

@tree.command(name="tribunal", description="Consulta las notas, juegos cooperativos y veredictos de El Tribunal Gaming")
@app_commands.describe(
    accion="Qué deseas consultar en El Tribunal Gaming",
    juego="Nombre del juego a buscar (opcional si consultas listas)"
)
@app_commands.choices(accion=[
    app_commands.Choice(name="🔍 Buscar ficha de juego", value="buscar"),
    app_commands.Choice(name="🤝 Catálogo Cooperativo (categorías y viabilidad)", value="coop"),
    app_commands.Choice(name="💀 Muro de la Vergüenza / Vetados", value="muro"),
    app_commands.Choice(name="🏆 Top Rankings Metacritic & HLTB", value="top")
])
async def cmd_tribunal(interaction: discord.Interaction, accion: app_commands.Choice[str], juego: str = ""):
    await interaction.response.defer(thinking=True)
    val = accion.value
    
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
                color=0x6366f1
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
                color=0x10b981
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
            color=0xef4444
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
            color=0xf59e0b
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
            color=0x10b981
        )
        embed.set_footer(text="tribunal-gaming.vercel.app • Filtro Cooperativo")
        view = TribunalView()
        await interaction.followup.send(embed=embed, view=view)

@tree.command(name="perfil", description="Muestra la ficha técnica, rango de Cakey Bot y roles de un miembro")
@app_commands.describe(usuario="El miembro del que quieres consultar la ficha (por defecto tú)")
async def cmd_perfil(interaction: discord.Interaction, usuario: discord.Member = None):
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
        color=color
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

@tree.command(name="pregunta", description="Haz una pregunta o debate con el Asistente sin necesidad de mencionarlo")
@app_commands.describe(duda="Tu pregunta sobre juegos, anime, hardware, salseo o cualquier tema")
async def cmd_pregunta(interaction: discord.Interaction, duda: str):
    await interaction.response.defer(thinking=True)
    spain_time = get_spain_now_str()
    prompt = f"{interaction.user.display_name}: {duda}\n[CONTEXTO: Fecha y hora en España: {spain_time} | Usuario: {interaction.user.display_name} (@{interaction.user.name})]"
    turns = [{"role": "user", "parts": [{"text": prompt}]}]
    response = await asyncio.to_thread(call_gemini_multiturn, turns)
    
    draw_match = re.search(r"\[ACTION_DRAW:\s*(.*?)\]", response, re.DOTALL | re.IGNORECASE)
    if draw_match:
        prompt_flux = draw_match.group(1).strip()
        clean_response = re.sub(r"\[ACTION_DRAW:\s*.*?\]", "", response, flags=re.DOTALL | re.IGNORECASE).strip()
        try:
            img_bytes = await asyncio.to_thread(generate_image_flux, prompt_flux)
            file = discord.File(io.BytesIO(img_bytes), filename="creacion_flux.png")
            view = ImageActionView(prompt_flux, interaction.user.id)
            await interaction.followup.send(content=clean_response or None, file=file, view=view)
            return
        except Exception:
            pass
            
    if len(response) <= 1900:
        await interaction.followup.send(response)
    else:
        await interaction.followup.send(response[:1900])

@tree.command(name="voz", description="Consulta el radar en tiempo real de quién está en las salas de voz y su estado")
async def cmd_voz(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Este comando solo está disponible dentro de un servidor.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🎙️ Radar de Canales de Voz en Vivo",
        color=0x3b82f6,
        description=f"Estado de las salas de voz en **{interaction.guild.name}** al segundo:"
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
                inline=False
            )
            
    if total_active == 0:
        embed.description = "🟢 **Todas las salas de voz están libres actualmente.** No hay nadie conectado ahora mismo."
    else:
        embed.set_footer(text=f"Total: {total_active} miembros en llamadas de voz • Actualizado al segundo")
        
    await interaction.response.send_message(embed=embed)

@tree.command(name="musica", description="Busca una canción y muestra cómo reproducirla con Cakey Bot en la llamada de voz")
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
        color=0x1db954
    )
    embed.set_footer(text="Asistente de Música • Integración Cakey Bot & Streaming")
    await interaction.response.send_message(embed=embed)

@tree.command(name="habla", description="El Asistente entra a tu canal de voz y habla con síntesis neuronal de voz")
@app_commands.describe(
    texto="El mensaje o frase que quieres que diga en la llamada",
    voz="Voz de la locución: acentos, efectos o voces Gemini (por defecto Álvaro)"
)
@app_commands.choices(voz=[app_commands.Choice(name=v[0], value=k) for k, v in TTS_VOICES.items()])
async def cmd_habla(interaction: discord.Interaction, texto: str, voz: app_commands.Choice[str] = None):
    # Defer inmediato para evitar cualquier timeout de 3 segundos en Discord
    await interaction.response.defer(thinking=True)
    
    if not interaction.guild:
        await interaction.followup.send("❌ Este comando solo está disponible dentro de un servidor.")
        return
    
    clear_voice_manually_disconnected(interaction.guild.id)
    
    # 1. Resolver el canal de voz del usuario con múltiples fallbacks robustos
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
        # Fallback de radar: buscar en qué canal de voz figura el usuario
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
        # Si Gemini TTS falló (cuota), el audio salió con la voz de respaldo: no anunciar la voz pedida
        if TTS_VOICES.get(voice_choice, ("", "edge"))[1] == "gemini" and os.path.basename(audio_file).startswith("speech_edge_"):
            lbl = f"{TTS_VOICES['alvaro'][0]} — {lbl} no disponible ahora"
        
        embed = discord.Embed(
            title="🎙️ Locución en Canal de Voz",
            description=f"🔊 Hablando en **#{voice_channel.name}**\n\n> *\"{texto[:300]}\"*\n\n🎙️ **Voz:** `{lbl}`",
            color=0x3b82f6
        )
        embed.set_footer(text="Asistente de Voz Neuronal • Usa /para_audio para silenciar")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"Error en /habla: {e}")
        await interaction.followup.send(f"❌ Error al generar o reproducir la voz: {e}")

@tree.command(name="geminilive", description="Consulta o configura el estado de Gemini Live en llamada de voz")
@app_commands.describe(
    accion="Acción a realizar",
    sensibilidad="Sensibilidad del detector de voz (VAD)",
    voz="Voz neuronal del Asistente"
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
    ]
)
async def cmd_geminilive(
    interaction: discord.Interaction,
    accion: app_commands.Choice[str] = None,
    sensibilidad: app_commands.Choice[str] = None,
    voz: app_commands.Choice[str] = None
):
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
        elif vc and vc.is_connected() and isinstance(vc, voice_recv.VoiceRecvClient):
            new_sink = GeminiLiveVoiceSink(vc, bot.loop)
            vc.listen(new_sink)
            await interaction.followup.send(f"🎙️ **Gemini Live iniciado** en **#{vc.channel.name}**.")
        else:
            await interaction.followup.send("ℹ️ Usa `/unete` para conectar el bot a tu sala de voz primero.")
        return

    # Ajustes de sensibilidad o voz si se han especificado
    if sink:
        if sensibilidad and hasattr(sink, "silence_threshold_rms"):
            sens_map = {"alta": 40, "media": 70, "baja": 180}
            sink.silence_threshold_rms = sens_map.get(sensibilidad.value, 70)
        if voz and hasattr(sink, "voice_type"):
            sink.voice_type = voz.value

    # Mostrar estado detallado
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
        color=0x10b981 if (is_conn and is_listening) else 0x6b7280
    )
    embed.add_field(name="📡 Estado Conexión", value=f"`{'🟢 Conectado' if is_conn else '🔴 Desconectado'}`", inline=True)
    embed.add_field(name="🔊 Canal de Voz", value=f"**#{ch_name}**", inline=True)
    embed.add_field(name="👂 Escucha en Vivo", value=f"`{'🟢 Activa (Escuchando)' if is_listening else '⚪ Inactiva'}`", inline=True)
    embed.add_field(name="🎚️ Sensibilidad Micro (VAD)", value=f"`{current_sens}`", inline=True)
    embed.add_field(name="🗣️ Voz de Salida", value=f"`{current_voice}`", inline=True)
    embed.add_field(name="⚡ Latencia de Respuesta", value="`~1.5s (Full Duplex)`", inline=True)
    embed.set_footer(text="Usa /voz para cambiar de locutor o /desconecta para salir.")
    await interaction.followup.send(embed=embed)

@tree.command(name="cambiar_voz", description="Cambia la voz del Asistente en la llamada de voz (Álvaro, Elvira o Ximena)")
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
        "ximena": "Ximena (Femenina juvenil)"
    }
    lbl = labels.get(tipo.value, tipo.name)
    if sink and hasattr(sink, "voice_type"):
        sink.voice_type = tipo.value
        await interaction.followup.send(f"🎙️ **Voz cambiada**: A partir de ahora el Asistente responderá con la voz de **{lbl}**.\n*(También puedes cambiársela pidiéndole por voz 'ponte voz de chica' o 'ponte voz de chico')*.")
    else:
        channel_hint = interaction.user.voice.channel.name if getattr(interaction.user, 'voice', None) and interaction.user.voice.channel else "una sala de voz"
        await interaction.followup.send(f"ℹ️ El Asistente no tiene una llamada activa ahora. Conéctalo a **#{channel_hint}** y podrás usar `/cambiar_voz` o pedírselo por el micro.")

@tree.command(name="unete", description="Conecta al Asistente a tu canal de voz en modo conversacional Gemini Live")
@app_commands.describe(canal="Canal de voz al que conectarse (por defecto el tuyo)")
async def cmd_unete(interaction: discord.Interaction, canal: discord.VoiceChannel = None):
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
        # Saludo vocal inmediato para inicializar la conexión y confirmar que el audio bidireccional está activo
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
            color=0x10b981
        )
        embed.set_footer(text="Gemini Live Discord • Voz Neuronal en Tiempo Real")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al conectar a la llamada de voz: {e}")

@tree.command(name="desconecta", description="Desconecta al Asistente del canal de voz")
async def cmd_desconecta(interaction: discord.Interaction):
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

@tree.command(name="para_audio", description="Detiene la locución actual si el bot está hablando en la sala de voz")
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

@tree.command(name="recuerda", description="Guarda un gusto, nota o detalle en la memoria persistente de un usuario")
@app_commands.describe(
    dato="El dato a recordar (ej: 'Le flipa Solo Leveling y The Greatest Estate Developer')",
    categoria="Categoría del recuerdo (obra favorita, género o nota)",
    usuario="El miembro al que asociar este recuerdo (por defecto tú)"
)
@app_commands.choices(categoria=[
    app_commands.Choice(name="Obra / Juego favorito (fav_works)", value="fav_works"),
    app_commands.Choice(name="Género favorito (fav_genres)", value="fav_genres"),
    app_commands.Choice(name="Nota / Lore personal (notes)", value="notes"),
])
async def cmd_recuerda(interaction: discord.Interaction, dato: str, categoria: app_commands.Choice[str] = None, usuario: discord.Member = None):
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
            "trivia_points": 0
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
        color=0x8b5cf6
    )
    embed.set_footer(text="Memoria Persistente de Antigravity Asistente")
    await interaction.response.send_message(embed=embed)

@tree.command(name="trivial", description="Inicia una ronda de preguntas de Trivial (+10 pts al acertar)")
@app_commands.describe(
    categoria="Categoría de las preguntas",
    modo="Modo de obtención de la pregunta (Banco oficial o Generada por IA)"
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
    trivia_pool = load_trivia_data()
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
        color=0x3b82f6
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

@tree.command(name="ranking_trivial", description="Muestra la tabla de clasificación y puntos de Trivial del servidor")
async def cmd_ranking_trivial(interaction: discord.Interaction):
    ranked = []
    for uid, data in user_memory.items():
        pts = data.get("trivia_points", 0)
        if pts > 0:
            name = data.get("display_name") or data.get("name") or uid
            ranked.append((name, pts))
    ranked.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="🏆 Ranking de Trivial del Servidor",
        color=0xf59e0b,
        description="Puntuación acumulada respondiendo preguntas con `/trivial` (+10 pts por acierto):"
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

@tree.command(name="tres_en_raya", description="Juega al Tres en Raya interactivo (PvE contra Asistente o PvP contra un colega)")
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
    bot_log(f"🎮 [Tres en Raya] '{interaction.user.display_name}' inicia partida vs '{p2_txt}'.")

@tree.command(name="conecta4", description="Juega a Conecta 4 interactivo (PvE contra Asistente o PvP contra un colega)")
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
    bot_log(f"🔴🟡 [Conecta 4] '{interaction.user.display_name}' inicia partida vs '{p2_txt}'.")

@tree.command(name="xp", description="Calcula la XP y mensajes necesarios para alcanzar un nivel objetivo en Cakey Bot")
@app_commands.describe(
    nivel_objetivo="Nivel que deseas alcanzar (ej. 20 para Categoría Pro)",
    nivel_actual="Tu nivel actual (por defecto se consulta tu nivel real en el servidor)"
)
async def cmd_xp(interaction: discord.Interaction, nivel_objetivo: int, nivel_actual: int = None):
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
        color=0x3b82f6
    )
    embed.set_footer(text="Motor Matemático Cuadrático de Cakey Bot • Antigravity Asistente")
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    guild = member.guild
    # Si el propio bot fue desconectado de una sala de voz (desconexión manual por usuario en Discord o kick)
    if bot.user and member.id == bot.user.id:
        if before.channel is not None and after.channel is None:
            if consume_internal_voice_disconnect(guild.id):
                return
            set_voice_manually_disconnected(guild.id)
            vc = guild.voice_client
            if vc:
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
            bot_log(f"🔌 [Voice] Asistente fue desconectado de #{before.channel.name}. Auto-conexión bloqueada hasta orden explícita (/unete).")
        return

    if member.bot:
        return

    vc = guild.voice_client

    # Si un usuario se va y el canal del bot se queda sin humanos, desconectar para no consumir recursos
    if vc and vc.is_connected() and vc.channel:
        human_members = [m for m in vc.channel.members if m and not getattr(m, "bot", False)]
        if len(human_members) == 0:
            bot_log(f"ℹ️ Canal de voz #{vc.channel.name} vacío. Desconectando Asistente...")
            mark_internal_voice_disconnect(guild.id)
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
            try:
                await vc.disconnect(force=True)
            except Exception:
                pass

@bot.event
async def on_ready():
    bot_log(f"Bot '{bot.user}' conectado y listo en Discord.")
    bot_log(f"Motores de IA con respaldo: {MODELS_PRIORITY}")
    bot_log(f"Ajedrez: python-chess {'OK' if chess else 'NO disponible'} | Stockfish {'OK' if os.path.exists(STOCKFISH_PATH) else 'NO encontrado'} ({STOCKFISH_PATH})")
    bot_log("Capacidades activas: Gemini Live en Voz (/geminilive), Memoria Persistente, Trivial, Niveles Reales, Búsqueda Web, FLUX.1, Steam Store, Tribunal Gaming y Slash Commands.")
    
    # Sincronización instantánea de Slash Commands en el servidor (sin duplicados globales)
    try:
        GUILD_ID = 1446143936891715616
        guild_obj = discord.Object(id=GUILD_ID)
        tree.copy_global_to(guild=guild_obj)
        await tree.sync(guild=guild_obj)
        bot_log(f"Comandos Slash sincronizados limpiamente en el servidor ID {GUILD_ID} (sin duplicados).")
    except Exception as e:
        bot_log(f"Aviso sincronización comandos slash: {e}")

    activity = discord.Activity(type=discord.ActivityType.listening, name="Gemini Live en voz (/unete)")
    await bot.change_presence(activity=activity)

    # Tarea de vigilancia para canales de voz: solo supervisa llamadas donde el bot YA fue conectado explícitamente
    async def _voice_channel_watchdog():
        await asyncio.sleep(5.0)
        while not bot.is_closed():
            try:
                for g in bot.guilds:
                    if is_voice_manually_disconnected(g.id):
                        vc = g.voice_client
                        if vc and (vc.is_connected() or getattr(vc, "is_listening", lambda: False)()):
                            try:
                                await vc.disconnect(force=True)
                            except Exception:
                                pass
                        continue
                    vc = g.voice_client
                    if vc and vc.is_connected() and vc.channel:
                        humans = [m for m in vc.channel.members if m and not getattr(m, "bot", False)]
                        if not humans:
                            bot_log(f"ℹ️ [Voice Watchdog] Canal #{vc.channel.name} sin humanos. Desconectando Asistente...")
                            mark_internal_voice_disconnect(g.id)
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
                            try:
                                await vc.disconnect(force=True)
                            except Exception:
                                pass
                        else:
                            is_active_listening = getattr(vc, "is_listening", lambda: False)()
                            if not is_active_listening:
                                bot_log(f"🎙️ [Voice Watchdog] Reactivando escucha en #{vc.channel.name}...")
                                try:
                                    sink = GeminiLiveVoiceSink(vc, bot.loop)
                                    vc.listen(sink)
                                except Exception as ex_sink:
                                    bot_log(f"Aviso reactivando sink en watchdog: {ex_sink}")
            except Exception as e:
                bot_log(f"Aviso en _voice_channel_watchdog: {e}")
            await asyncio.sleep(15.0)

    bot.loop.create_task(_voice_channel_watchdog())

    # Tarea periódica de limpieza de grabaciones con más de 24 horas de antigüedad
    async def _recordings_retention_cleaner():
        await asyncio.sleep(60.0)
        while not bot.is_closed():
            try:
                now = time.time()
                with VOICE_TURNS_LOCK:
                    valid = []
                    for t in VOICE_TURNS_LOG:
                        epoch = t.get("epoch", 0.0)
                        if (now - epoch) < RETENTION_SECONDS:
                            valid.append(t)
                        else:
                            fname = t.get("filename")
                            if fname:
                                fpath = os.path.join(RECORDINGS_DIR, fname)
                                if os.path.exists(fpath):
                                    try:
                                        os.remove(fpath)
                                    except Exception:
                                        pass
                    if len(valid) != len(VOICE_TURNS_LOG):
                        VOICE_TURNS_LOG[:] = valid
                        save_recordings_metadata()
                        bot_log(f"🧹 [Grabaciones] Limpieza 24h completada. {len(valid)} grabaciones activas.")
            except Exception as e:
                bot_log(f"Aviso limpiador grabaciones: {e}")
            await asyncio.sleep(600.0)

    bot.loop.create_task(_recordings_retention_cleaner())

# ==========================================
# AJEDREZ CONTRA ASISTENTE (python-chess + Stockfish)
# ==========================================
try:
    import chess
    import chess.engine
except Exception as _chess_import_err:
    chess = None
    print(f"Aviso: python-chess no disponible ({_chess_import_err}). /ajedrez desactivado.")

import shutil

STOCKFISH_PATH = shutil.which("stockfish") or "/usr/games/stockfish"
# Partidas en memoria: user_id -> ChessGame (un reinicio del servicio las borra)
CHESS_GAMES = {}
CHESS_PIECE_NAMES = {1: "Peón", 2: "Caballo", 3: "Alfil", 4: "Torre", 5: "Dama", 6: "Rey"}
CHESS_ICONS_WHITE = {1: "♙", 2: "♘", 3: "♗", 4: "♖", 5: "♕", 6: "♔"}
CHESS_ICONS_BLACK = {1: "♟", 2: "♞", 3: "♝", 4: "♜", 5: "♛", 6: "♚"}
# Dificultades de Asistente: clave -> (etiqueta, ELO de Stockfish, segundos por jugada).
# ELO None en fácil: la jugada la elige Gemini sola (sin motor), así que su nivel es orientativo.
# ELO 0 en máximo: Stockfish sin límite de fuerza. En todos los niveles Gemini pone el comentario.
CHESS_LEVELS = {
    "facil": ("Fácil (~800 ELO, Gemini juega sola)", None, 0),
    "medio": ("Medio (1400 ELO)", 1400, 0.3),
    "dificil": ("Difícil (1900 ELO)", 1900, 0.5),
    "maximo": ("Máximo (3000+ ELO)", 0, 1.0),
}
CHESS_TYPED_MOVE_RE = re.compile(r"^[a-hRNBQKDTACOo0x=+#\-1-8]{2,7}$")
CHESS_SPANISH_PIECES = {"R": "K", "D": "Q", "T": "R", "A": "B", "C": "N"}

def chess_icon(piece) -> str:
    return (CHESS_ICONS_WHITE if piece.color else CHESS_ICONS_BLACK)[piece.piece_type]

def chess_board_url(board, player_white: bool) -> str:
    """Imagen del tablero servida por Lichess, orientada hacia el jugador y con la última jugada resaltada."""
    params = {"fen": board.fen(), "color": "white" if player_white else "black"}
    if board.move_stack:
        params["lastMove"] = board.move_stack[-1].uci()[:4]
    if board.is_check():
        params["check"] = chess.square_name(board.king(board.turn))
    return "https://lichess1.org/export/fen.gif?" + urllib.parse.urlencode(params)

def chess_parse_typed(board, text: str):
    """Interpreta una jugada escrita en el chat: notación algebraica (inglesa o española) o coordenadas (e2e4)."""
    txt = text.strip()
    if not CHESS_TYPED_MOVE_RE.match(txt):
        return None
    txt = txt.replace("0", "O").replace("o", "O")
    # Variante española: inicial de la pieza (Cf3) y pieza de coronación (a8=D)
    spanish = re.sub(r"=([DTAC])", lambda m: "=" + CHESS_SPANISH_PIECES[m.group(1)], txt)
    if spanish[0] in CHESS_SPANISH_PIECES:
        spanish = CHESS_SPANISH_PIECES[spanish[0]] + spanish[1:]
    candidates = [txt] if spanish == txt else [txt, spanish]
    for cand in candidates:
        try:
            return board.parse_san(cand)
        except Exception:
            pass
    try:
        low = text.strip().lower()
        move = chess.Move.from_uci(low)
        if move in board.legal_moves:
            return move
        # Coronación sin indicar pieza: dama por defecto
        queen = chess.Move.from_uci(low + "q")
        if queen in board.legal_moves:
            return queen
    except Exception:
        pass
    return None

def chess_piece_options(board) -> list:
    """Piezas del bando que mueve con alguna jugada legal: [(etiqueta, descripción, casilla)]."""
    counts = collections.OrderedDict()
    for mv in board.legal_moves:
        counts[mv.from_square] = counts.get(mv.from_square, 0) + 1
    opts = []
    for sq in sorted(counts, key=lambda s: (-board.piece_at(s).piece_type, s)):
        piece = board.piece_at(sq)
        n = counts[sq]
        opts.append((f"{chess_icon(piece)} {CHESS_PIECE_NAMES[piece.piece_type]} {chess.square_name(sq)}",
                     f"{n} jugada{'s' if n != 1 else ''}", chess.square_name(sq)))
    return opts

def chess_dest_options(board, from_square: int) -> list:
    """Destinos legales de una pieza: [(etiqueta, uci)]."""
    opts = []
    piece = board.piece_at(from_square)
    for mv in board.legal_moves:
        if mv.from_square != from_square:
            continue
        if board.is_castling(mv):
            label = "Enroque corto" if board.is_kingside_castling(mv) else "Enroque largo"
        else:
            label = f"{chess_icon(piece)} → {chess.square_name(mv.to_square)}"
            if board.is_en_passant(mv):
                label += " ✕ Peón (al paso)"
            elif board.is_capture(mv):
                label += f" ✕ {CHESS_PIECE_NAMES[board.piece_at(mv.to_square).piece_type]}"
            if mv.promotion:
                label += f" = {CHESS_PIECE_NAMES[mv.promotion]}"
        if board.gives_check(mv):
            label += " (jaque)"
        opts.append((label, mv.uci()))
    return opts

def chess_moves_text(board, max_chars: int = 220) -> str:
    """Lista numerada de la partida, recortada a las últimas jugadas."""
    if not board.move_stack:
        return ""
    txt = chess.Board().variation_san(board.move_stack)
    if len(txt) > max_chars:
        txt = "… " + txt[-max_chars:].split(" ", 1)[-1]
    return txt

def chess_result_text(board, player_white: bool, player_name: str):
    """Texto de final de partida, o None si sigue en juego."""
    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        return None
    if outcome.winner is None:
        reasons = {
            chess.Termination.STALEMATE: "rey ahogado",
            chess.Termination.INSUFFICIENT_MATERIAL: "material insuficiente",
            chess.Termination.THREEFOLD_REPETITION: "triple repetición",
            chess.Termination.FIVEFOLD_REPETITION: "repetición",
            chess.Termination.FIFTY_MOVES: "regla de los 50 movimientos",
            chess.Termination.SEVENTYFIVE_MOVES: "regla de los 75 movimientos",
        }
        return f"🤝 **Tablas** por {reasons.get(outcome.termination, 'acuerdo')}."
    if outcome.winner == player_white:
        return f"🏆 **Jaque mate. Gana {player_name}.**"
    return "💀 **Jaque mate. Gana Asistente.**"

class ChessGame:
    def __init__(self, user_id: int, user_name: str, player_white: bool, rival: str):
        self.user_id = user_id
        self.user_name = user_name
        self.player_white = player_white
        self.rival = rival
        self.board = chess.Board()
        self.message = None
        self.comment = ""
        self.selected = None  # casilla de la pieza elegida en el menú
        self.busy = False
        self.finished = False
        self.result = ""
        self.lock = asyncio.Lock()

def chess_build_embed(game: "ChessGame") -> discord.Embed:
    board = game.board
    rival_label = "Asistente · " + CHESS_LEVELS[game.rival][0].split(" (")[0]
    lines = []
    if game.finished:
        lines.append(game.result)
    elif game.busy:
        lines.append("⏳ **Asistente está pensando...**")
    else:
        color = "blancas" if game.player_white else "negras"
        lines.append(f"🎯 **Te toca, {game.user_name}** (juegas con {color})" + (" — **estás en jaque**" if board.is_check() else ""))
    if game.comment:
        lines.append(f"💬 *{game.comment[:300]}*")
    moves = chess_moves_text(board)
    if moves:
        lines.append(f"`{moves}`")
    embed = discord.Embed(
        title=f"♟️ Ajedrez — {game.user_name} vs {rival_label}",
        description="\n\n".join(lines),
        color=0x57f287 if game.finished else 0x3b82f6
    )
    embed.set_image(url=chess_board_url(board, game.player_white))
    if not game.finished:
        embed.set_footer(text="Elige pieza y destino en los menús, o escribe la jugada en este canal (e4, Cf3, e2e4)")
    return embed

class ChessView(discord.ui.View):
    """Menús de la partida: primero la pieza, después su destino."""
    def __init__(self, game: "ChessGame"):
        super().__init__(timeout=None)
        self.game = game
        board = game.board
        if game.busy:
            self.add_item(discord.ui.Button(label="Asistente está pensando...", style=discord.ButtonStyle.secondary, disabled=True))
            return
        if game.selected is None:
            select = discord.ui.Select(
                placeholder="1. Elige la pieza que quieres mover",
                options=[discord.SelectOption(label=l, description=d, value=v) for l, d, v in chess_piece_options(board)][:25]
            )
            select.callback = self.on_piece
            self.add_item(select)
        else:
            piece = board.piece_at(game.selected)
            dests = chess_dest_options(board, game.selected)
            # Discord admite 25 opciones por menú; una dama puede tener hasta 27 destinos
            for i in range(0, len(dests), 25):
                chunk = dests[i:i + 25]
                select = discord.ui.Select(
                    placeholder=f"2. ¿A dónde va {CHESS_PIECE_NAMES[piece.piece_type]} {chess.square_name(game.selected)}?" + (" (más)" if i else ""),
                    options=[discord.SelectOption(label=l, value=v) for l, v in chunk]
                )
                select.callback = self.on_dest
                self.add_item(select)
            back = discord.ui.Button(label="Cambiar pieza", style=discord.ButtonStyle.secondary, emoji="↩️")
            back.callback = self.on_back
            self.add_item(back)
        resign = discord.ui.Button(label="Rendirse", style=discord.ButtonStyle.danger, emoji="🏳️")
        resign.callback = self.on_resign
        self.add_item(resign)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message("⚠️ Esta partida no es tuya. Empieza la tuya con `/ajedrez`.", ephemeral=True)
            return False
        if self.game.finished or CHESS_GAMES.get(self.game.user_id) is not self.game:
            await interaction.response.send_message("ℹ️ Esta partida ya ha terminado.", ephemeral=True)
            return False
        return True

    async def on_piece(self, interaction: discord.Interaction):
        self.game.selected = chess.parse_square(interaction.data["values"][0])
        await interaction.response.edit_message(embed=chess_build_embed(self.game), view=ChessView(self.game))

    async def on_back(self, interaction: discord.Interaction):
        self.game.selected = None
        await interaction.response.edit_message(embed=chess_build_embed(self.game), view=ChessView(self.game))

    async def on_dest(self, interaction: discord.Interaction):
        move = chess.Move.from_uci(interaction.data["values"][0])
        if not await chess_play_player_move(self.game, move, interaction):
            if not interaction.response.is_done():
                self.game.selected = None
                await interaction.response.edit_message(embed=chess_build_embed(self.game), view=ChessView(self.game))

    async def on_resign(self, interaction: discord.Interaction):
        chess_finish(self.game, f"🏳️ **{self.game.user_name} se rinde. Gana Asistente.**")
        await interaction.response.edit_message(embed=chess_build_embed(self.game), view=None)

def chess_finish(game: "ChessGame", result: str):
    game.finished = True
    game.busy = False
    game.selected = None
    game.result = result
    if CHESS_GAMES.get(game.user_id) is game:
        CHESS_GAMES.pop(game.user_id, None)

def chess_gemini_pick(fen: str, bot_color: str, legal_sans: list, history: str, user_name: str, played_san: str = None):
    """Pide a Gemini una jugada de la lista de legales y un comentario. Devuelve (san, comentario) o (None, '').
    Con played_san la jugada ya la eligió el motor y Gemini solo la comenta."""
    if played_san:
        task = f"Acabas de jugar {played_san}. Repite esa jugada y añade un comentario breve "
    else:
        task = (
            f"Jugadas legales: {', '.join(legal_sans)}\n\n"
            f"Elige la mejor jugada, copiada EXACTAMENTE de la lista de jugadas legales, y añade un comentario breve "
        )
    prompt = (
        f"Eres 'Asistente', el bot colega de un servidor de Discord, jugando al ajedrez con {bot_color} contra {user_name}.\n"
        f"Posición (FEN): {fen}\n"
        f"Partida hasta ahora: {history or 'acaba de empezar'}\n"
        f"{task}"
        f"en español de España con pique sano de colegas (sin insultos, máximo 20 palabras).\n"
        f"Formato de salida estricto:\nJugada: <jugada>\nComentario: <comentario>"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 120}
    }
    data = json.dumps(payload).encode("utf-8")
    for model_name in get_available_models()[:3]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode("utf-8"))
            text = res["candidates"][0]["content"]["parts"][0]["text"]
            m_move = re.search(r"Jugada:\s*([^\s]+)", text)
            m_comment = re.search(r"Comentario:\s*(.+)", text)
            if m_move:
                return m_move.group(1).strip().strip("*`."), (m_comment.group(1).strip() if m_comment else "")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                mark_model_cooldown(model_name, 60)
        except Exception as e:
            print(f"Aviso Gemini ajedrez ({model_name}): {e}")
    return None, ""

async def chess_stockfish_move(board, elo: int, seconds: float):
    """Jugada de Stockfish limitado al ELO indicado (0 = fuerza completa)."""
    transport, engine = await chess.engine.popen_uci(STOCKFISH_PATH)
    try:
        options = {"Threads": 1, "Hash": 16}
        if elo and "UCI_Elo" in engine.options:
            # El rango admitido depende de la versión instalada (mínimo en torno a 1320)
            opt = engine.options["UCI_Elo"]
            options["UCI_LimitStrength"] = True
            options["UCI_Elo"] = max(opt.min, min(opt.max, elo))
        await engine.configure(options)
        result = await asyncio.wait_for(engine.play(board, chess.engine.Limit(time=seconds)), timeout=20)
        return result.move
    finally:
        try:
            await asyncio.wait_for(engine.quit(), timeout=5)
        except Exception:
            pass

async def chess_bot_move(game: "ChessGame"):
    """Devuelve (jugada, comentario) del rival configurado. Siempre devuelve una jugada legal."""
    board = game.board
    legal = list(board.legal_moves)
    _, elo, seconds = CHESS_LEVELS[game.rival]
    bot_color = "blancas" if board.turn else "negras"
    if elo is not None:
        try:
            move = await chess_stockfish_move(board, elo, seconds)
            if move in legal:
                _, comment = await asyncio.to_thread(
                    chess_gemini_pick, board.fen(), bot_color, [], chess_moves_text(board, 600), game.user_name, board.san(move)
                )
                return move, comment
        except Exception as e:
            bot_log(f"Aviso Stockfish no disponible ({e}). Jugando con Gemini.")
    legal_sans = [board.san(m) for m in legal]
    san, comment = await asyncio.to_thread(
        chess_gemini_pick, board.fen(), bot_color, legal_sans, chess_moves_text(board, 600), game.user_name
    )
    if san:
        try:
            return board.parse_san(san), comment
        except Exception:
            pass
    return random.choice(legal), ""

async def chess_run_bot_turn(game: "ChessGame"):
    """Turno del rival: muestra 'pensando', juega y refresca el mensaje de la partida."""
    try:
        move, comment = await chess_bot_move(game)
        if game.finished:
            return
        game.board.push(move)
        game.comment = comment
    finally:
        game.busy = False
    result = chess_result_text(game.board, game.player_white, game.user_name)
    if result:
        chess_finish(game, result)
    await game.message.edit(embed=chess_build_embed(game), view=None if game.finished else ChessView(game))

async def chess_play_player_move(game: "ChessGame", move, interaction: discord.Interaction = None) -> bool:
    """Aplica la jugada del jugador (desde menú o escrita) y lanza la respuesta del rival."""
    async with game.lock:
        board = game.board
        if game.finished or game.busy or board.turn != game.player_white or move not in board.legal_moves:
            return False
        board.push(move)
        game.selected = None
        game.comment = ""
        result = chess_result_text(board, game.player_white, game.user_name)
        if result:
            chess_finish(game, result)
        else:
            game.busy = True
        embed = chess_build_embed(game)
        view = None if game.finished else ChessView(game)
        if interaction is not None:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await game.message.edit(embed=embed, view=view)
        if not game.finished:
            await chess_run_bot_turn(game)
        return True

async def chess_try_typed_move(message: discord.Message) -> bool:
    """Si el autor tiene partida en este canal y el mensaje es una jugada legal, la juega. Devuelve True si lo era."""
    game = CHESS_GAMES.get(message.author.id)
    if not game or game.finished or game.busy or not game.message or game.message.channel.id != message.channel.id:
        return False
    if game.board.turn != game.player_white:
        return False
    move = chess_parse_typed(game.board, message.content)
    if move is None:
        return False
    try:
        await message.delete()
    except Exception:
        pass
    return await chess_play_player_move(game, move)

@tree.command(name="ajedrez", description="Juega una partida de ajedrez contra Asistente (menús o escribiendo la jugada)")
@app_commands.describe(
    dificultad="Nivel de Asistente (por defecto Medio, 1400 ELO)",
    color="Con qué color juegas (por defecto blancas)"
)
@app_commands.choices(
    dificultad=[app_commands.Choice(name=v[0], value=k) for k, v in CHESS_LEVELS.items()],
    color=[
        app_commands.Choice(name="Blancas (mueves primero)", value="blancas"),
        app_commands.Choice(name="Negras", value="negras"),
        app_commands.Choice(name="Al azar", value="azar"),
    ]
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
    # El mensaje de la interacción solo se puede editar 15 minutos; se recupera como mensaje normal para toda la partida
    try:
        game.message = await interaction.channel.fetch_message(sent.id)
    except Exception:
        game.message = sent
    bot_log(f"♟️ [Ajedrez] '{game.user_name}' empieza partida en dificultad {CHESS_LEVELS[game.rival][0]} ({'blancas' if player_white else 'negras'}).")
    if not player_white:
        async with game.lock:
            await chess_run_bot_turn(game)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    try:
        if chess is not None and await chess_try_typed_move(message):
            return
        await _handle_message_safe(message)
    except Exception as e:
        print(f"Error procesando mensaje: {e}")

async def _handle_message_safe(message: discord.Message):
    is_mentioned = (
        bot.user in message.mentions
        or any(r.id == 1549789822191935561 or r.name.lower() == "asistente" for r in message.role_mentions)
        or (message.reference and getattr(message.reference.resolved, "author", None) == bot.user)
    )
    
    if is_mentioned:
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
                    # Omitir spam de bots pero mantener mensajes del propio Asistente y todos los humanos
                    if prev_msg.author.bot and prev_msg.author != bot.user:
                        # Si es spam de cola vacía de Cakey Bot, ignorarlo
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

            # Snapshot de miembros reales del servidor (con roles y niveles) - Inyección selectiva para ahorrar tokens
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
                # Fallback automático: detectar fórmulas en bloque $$...$$ si no emitió la etiqueta explícita
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
                    # Fallback crítico: si falla Pillow o el renderizado, NUNCA perder el código
                    clean_code = code_content.strip()
                    if clean_code.startswith("```"):
                        fallback_code = clean_code
                    else:
                        fallback_code = f"```python\n{clean_code}\n```"
                    response_text = response_text.replace(full_code, fallback_code, 1).strip()

            # Fallback de seguridad para dibujo directo si el usuario dijo "dibuja..." y la IA no emitió ACTION_DRAW
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

            # Sanitizar cualquier resto de código LaTeX en el texto plano para evitar "chino" en Discord
            response_text = sanitize_discord_math_text(response_text)
            if not response_text and files_to_send:
                response_text = "Aquí tienes la representación visual:"
        
        # Enviar respuesta respetando límite de 2.000 caracteres de Discord y adjuntando archivos acumulados
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
        # Y si el bot YA está conectado a esa misma sala de voz y no fue desconectado manualmente.
        # NUNCA iniciar conexión a voz desde este bloque de chat general.
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

        # Regla estricta: NUNCA auto-unirse a llamadas desde texto en este bloque.
        # Solo locutar si el bot YA está conectado a la misma sala del usuario, no ha sido desconectado manualmente,
        # Y el usuario pidió explícitamente locución por voz en este mensaje.
        should_speak_in_voice = bool(
            explicit_voice_request and vc and vc.is_connected() and vch and vc.channel == vch and not manually_dc
        )

        if should_speak_in_voice and vc and vc.is_connected():
            try:
                clean_for_speech = re.sub(r"\[ACTION_[A-Z]+:\s*.*?\]", "", response_text, flags=re.DOTALL | re.IGNORECASE).strip()
                clean_for_speech = re.sub(r"```.*?```", "", clean_for_speech, flags=re.DOTALL).strip()
                clean_for_speech = re.sub(r"`.*?`", "", clean_for_speech).strip()
                # Permitir hasta 2500 caracteres para leer todos los párrafos de forma completa y natural
                tts_text = clean_text_for_tts(clean_for_speech[:2500])
                if tts_text and len(tts_text) >= 2:
                    bot_log(f"🎙️ [TTS Locución] Reproduciendo respuesta ({len(tts_text)} chars) en #{vc.channel.name}...")
                    audio_path = await generate_speech_audio(tts_text, "alvaro")
                    play_audio_in_voice(vc, audio_path)
            except Exception as e:
                bot_log(f"Aviso locución de respuesta en llamada: {e}")

import http.server
import socketserver
import threading

class ReusableTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

def run_health_check_server():
    port = int(os.getenv("PORT", 10000))
    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/logs":
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.end_headers()
                content = "\n".join(GLOBAL_LOG_BUFFER) if GLOBAL_LOG_BUFFER else "Sin logs registrados aún."
                self.wfile.write(content.encode("utf-8"))
            elif parsed.path == "/status":
                try:
                    voice_data = []
                    for vc in list(bot.voice_clients):
                        conn = getattr(vc, "_connection", None)
                        dave = getattr(conn, "dave_session", None)
                        dave_info = {
                            "protocol_version": getattr(conn, "dave_protocol_version", 0),
                            "ready": getattr(dave, "ready", False) if dave else False,
                            "user_ids": dave.get_user_ids() if dave and hasattr(dave, "get_user_ids") else []
                        }
                        voice_data.append({
                            "guild": str(vc.guild.name) if vc.guild else None,
                            "channel": str(getattr(vc.channel, "name", "desconocido")),
                            "is_connected": bool(vc.is_connected()),
                            "is_listening": bool(vc.is_listening()) if hasattr(vc, "is_listening") else False,
                            "is_playing": bool(vc.is_playing()) if hasattr(vc, "is_playing") else False,
                            "dave": dave_info,
                            "members": [m.display_name for m in getattr(vc.channel, "members", []) if not m.bot]
                        })
                    payload = {
                        "bot_ready": bot.is_ready(),
                        "bot_user": str(bot.user) if bot.user else None,
                        "voice_clients": voice_data,
                        "server_time": get_spain_now_str()
                    }
                    data_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-type", "application/json; charset=utf-8")
                    self.send_header("Content-length", str(len(data_bytes)))
                    self.end_headers()
                    self.wfile.write(data_bytes)
                except Exception as ex:
                    err_bytes = json.dumps({"error": str(ex)}).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-type", "application/json; charset=utf-8")
                    self.send_header("Content-length", str(len(err_bytes)))
                    self.end_headers()
                    self.wfile.write(err_bytes)
            elif parsed.path in ["/audios/zip", "/grabaciones/zip"]:
                try:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                        if os.path.exists(METADATA_FILE):
                            zf.write(METADATA_FILE, arcname="recordings_metadata.json")
                        if os.path.exists(RECORDINGS_DIR):
                            for fname in os.listdir(RECORDINGS_DIR):
                                if fname.endswith(".wav"):
                                    fpath = os.path.join(RECORDINGS_DIR, fname)
                                    if os.path.isfile(fpath):
                                        zf.write(fpath, arcname=fname)
                    zip_data = zip_buffer.getvalue()
                    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    zip_filename = f"grabaciones_24h_{now_str}.zip"
                    self.send_response(200)
                    self.send_header("Content-type", "application/zip")
                    self.send_header("Content-Disposition", f'attachment; filename="{zip_filename}"')
                    self.send_header("Content-length", str(len(zip_data)))
                    self.end_headers()
                    self.wfile.write(zip_data)
                except Exception as ex_zip:
                    err_b = f"Error generando ZIP: {ex_zip}".encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(err_b)
            elif parsed.path in ["/audios", "/grabaciones"]:
                try:
                    with VOICE_TURNS_LOCK:
                        turns = list(reversed(VOICE_TURNS_LOG))

                    cards_html = []
                    for t in turns:
                        status_cls = t.get("status", "procesando")
                        u_name = html.escape(str(t.get("user", "Usuario")))
                        t_time = html.escape(str(t.get("timestamp", "")))
                        dur = t.get("duration_s", 0.0)
                        fname = html.escape(str(t.get("filename", "")))
                        trans = html.escape(str(t.get("transcription", "")))
                        reply = html.escape(str(t.get("bot_reply", "")))
                        file_url = f"/audios/file/{fname}"

                        card = f"""
                        <div class="card {status_cls}">
                          <div class="card-header">
                            <span class="user-badge">{u_name}</span>
                            <span class="time-tag">⏱️ {dur}s &nbsp;|&nbsp; 🕒 {t_time}</span>
                          </div>
                          <div class="speech-bubble user">
                            <div class="bubble-label">👤 Usuario ({u_name}):</div>
                            <div>"{trans or '(audio procesado)'}"</div>
                          </div>
                        """
                        if reply and reply not in ["[IGNORAR]", "IGNORAR"]:
                            card += f"""
                          <div class="speech-bubble bot">
                            <div class="bubble-label">🤖 Asistente:</div>
                            <div>"{reply}"</div>
                          </div>
                        """
                        card += f"""
                          <div class="player-container">
                            <audio controls preload="none" src="{file_url}"></audio>
                            <a href="{file_url}" download="{fname}" class="btn btn-secondary">📥 Descargar WAV</a>
                          </div>
                        </div>
                        """
                        cards_html.append(card)

                    body_content = "\n".join(cards_html) if cards_html else '<div class="empty-state"><h3>Aún no hay grabaciones en esta sesión</h3><p>Cuando alguien hable en la llamada de Discord, sus intervenciones aparecerán aquí con su reproductor de audio y transcripción.</p></div>'

                    html_page = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Grabaciones en Vivo - Asistente Discord</title>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #1e1f22; color: #dbdee1; margin: 0; padding: 20px; }}
.container {{ max-width: 920px; margin: 0 auto; }}
header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #3f4147; padding-bottom: 16px; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }}
.title-group h1 {{ margin: 0; font-size: 22px; color: #fff; }}
.title-group p {{ margin: 4px 0 0 0; color: #949ba4; font-size: 13px; }}
.actions {{ display: flex; gap: 8px; align-items: center; }}
.btn {{ background: #5865f2; color: #fff; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }}
.btn:hover {{ background: #4752c4; }}
.btn-secondary {{ background: #35373c; color: #dbdee1; font-size: 12px; padding: 6px 12px; }}
.btn-secondary:hover {{ background: #3b3e45; color: #fff; }}
.card {{ background: #2b2d31; border-radius: 8px; padding: 16px; margin-bottom: 14px; border-left: 4px solid #5865f2; box-shadow: 0 2px 6px rgba(0,0,0,0.25); }}
.card.respondido {{ border-left-color: #57f287; }}
.card.ignorado {{ border-left-color: #80848e; opacity: 0.85; }}
.card.silenciado {{ border-left-color: #f23f43; }}
.card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px; }}
.user-badge {{ font-weight: 700; color: #fff; background: #5865f2; padding: 3px 10px; border-radius: 12px; font-size: 13px; }}
.time-tag {{ color: #949ba4; font-size: 12px; }}
.speech-bubble {{ background: #313338; border-radius: 6px; padding: 10px 14px; margin: 8px 0; font-size: 14px; }}
.speech-bubble.user {{ border-left: 3px solid #5865f2; color: #f2f3f5; }}
.speech-bubble.bot {{ border-left: 3px solid #57f287; background: #232428; color: #57f287; }}
.bubble-label {{ font-size: 11px; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 4px; color: #949ba4; }}
.player-container {{ display: flex; align-items: center; gap: 10px; margin-top: 10px; background: #1e1f22; padding: 8px 12px; border-radius: 6px; flex-wrap: wrap; }}
audio {{ flex: 1; height: 36px; min-width: 220px; }}
.empty-state {{ text-align: center; padding: 60px 20px; background: #2b2d31; border-radius: 8px; color: #949ba4; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="title-group">
      <h1>🎙️ Grabaciones de Voz - Asistente Discord</h1>
      <p>Escucha las intervenciones de los usuarios y las respuestas del Asistente en tiempo real. <span style="background: rgba(87, 242, 135, 0.15); color: #57f287; border: 1px solid rgba(87, 242, 135, 0.3); border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 11px; margin-left: 6px;">🕒 Retención: Últimas 24 Horas</span></p>
    </div>
    <div class="actions">
      <a href="/audios/zip" class="btn" style="background:#23a55a;">📦 Descargar Todo (ZIP)</a>
      <a href="/audios" class="btn">🔄 Refrescar</a>
      <a href="/status" class="btn btn-secondary">📊 Estado</a>
      <a href="/logs" class="btn btn-secondary">📜 Logs</a>
    </div>
  </header>
  <div class="content">
    {body_content}
  </div>
</div>
</body>
</html>"""
                    out_bytes = html_page.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.send_header("Content-length", str(len(out_bytes)))
                    self.end_headers()
                    self.wfile.write(out_bytes)
                except Exception as e_page:
                    err_b = f"Error generando página: {e_page}".encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(err_b)
            elif parsed.path.startswith("/audios/file/"):
                fname = os.path.basename(parsed.path)
                fpath = os.path.join(RECORDINGS_DIR, fname)
                if os.path.exists(fpath):
                    try:
                        with open(fpath, "rb") as f_a:
                            audio_b = f_a.read()
                        self.send_response(200)
                        self.send_header("Content-type", "audio/wav")
                        self.send_header("Content-length", str(len(audio_b)))
                        self.send_header("Content-Disposition", f'inline; filename="{fname}"')
                        self.end_headers()
                        self.wfile.write(audio_b)
                    except Exception:
                        self.send_response(500)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
            elif parsed.path == "/api/audios":
                with VOICE_TURNS_LOCK:
                    turns = list(reversed(VOICE_TURNS_LOG))
                d_b = json.dumps(turns, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.send_header("Content-length", str(len(d_b)))
                self.end_headers()
                self.wfile.write(d_b)
            else:
                status = "OK - Asistente Bot Activo (Discord: Conectado)" if bot.is_ready() else "OK - Asistente Bot Activo (Discord: Conectando...)"
                status_bytes = status.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.send_header("Connection", "close")
                self.send_header("Content-length", str(len(status_bytes)))
                self.end_headers()
                self.wfile.write(status_bytes)

        def do_HEAD(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.send_header("Connection", "close")
            self.end_headers()

        def log_message(self, format, *args):
            pass

    try:
        with ReusableTCPServer(("", port), HealthHandler) as httpd:
            bot_log(f"Servidor de salud y logs HTTP activo en puerto {port} para Render")
            httpd.serve_forever()
    except Exception as e:
        bot_log(f"Aviso servidor salud: {e}")

def start_bot_persistent():
    """Bucle supervisor persistente para mantener el bot conectado 24/7 sin caídas."""
    while True:
        try:
            print("Iniciando conexión del bot con Discord...")
            bot.run(TOKEN)
        except (KeyboardInterrupt, SystemExit):
            print("Cierre manual solicitado.")
            break
        except Exception as e:
            print(f"Excepción en bot.run(): {e}. Reintentando en 5 segundos...")
            time.sleep(5)
        print("bot.run() finalizó. Reanudando en 5 segundos...")
        time.sleep(5)

if __name__ == "__main__":
    t = threading.Thread(target=run_health_check_server, daemon=True)
    t.start()
    start_bot_persistent()
