"""
Subsistema de Voz, DAVE E2EE, TTS Neuronal y Gemini Live Bidireccional:
- Parche de descifrado de voz MLS (DAVE E2EE) para PacketDecoder.
- Síntesis de voz neuronal con 25 voces (Edge TTS con acentos y efectos + Gemini TTS) y limpieza de texto.
- Gestión de grabaciones de las últimas 24h con lock reentrante (VOICE_TURNS_LOCK).
- Control de estado de desconexión manual y automática.
- Sink bidireccional en tiempo real (GeminiLiveVoiceSink) con VAD, anti-alucinación, dictado a chat ([CHAT:]) y búsqueda web en vivo.
"""

import asyncio
import base64
from datetime import datetime, timezone
import io
import json
import math
import os
import re
import struct
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import wave
import discord
from discord.ext import voice_recv
import edge_tts


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


def _bot_log(msg: str):
    bs = _bs()
    log_fn = getattr(bs, "bot_log", print)
    log_fn(msg)


def apply_dave_patch():
    """Permite al bot descifrar el audio encriptado con MLS proveniente de la app de escritorio de Discord."""
    try:
        import davey
        import discord.ext.voice_recv.opus as vo

        if hasattr(vo, "PacketDecoder"):
            if getattr(vo.PacketDecoder, "_dave_patched", False):
                return
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
            vo.PacketDecoder._dave_patched = True
            _bot_log("🔒 [DAVE E2EE] Parche de descifrado de voz activo en PacketDecoder.")
    except Exception as _patch_err:
        _bot_log(f"Aviso inicialización parche DAVE: {_patch_err}")


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
    gemini_key = getattr(_bs(), "GEMINI_KEY", "")

    if engine == "gemini":
        out_path = os.path.join(temp_dir, f"speech_gemini_{int(time.time()*1000)}.wav")
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-lite-tts:generateContent?key={gemini_key}"
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
                    },
                },
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

            def call_gemini_tts():
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode("utf-8"))

            res = await asyncio.to_thread(call_gemini_tts)
            b64 = res["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
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


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDINGS_DIR = os.path.join(ROOT_DIR, "recordings")
os.makedirs(RECORDINGS_DIR, exist_ok=True)
METADATA_FILE = os.path.join(RECORDINGS_DIR, "recordings_metadata.json")
RETENTION_SECONDS = 24 * 3600  # Retención de 24 horas completas (1 día)

# Reentrante: el limpiador de grabaciones llama a save_recordings_metadata() con el candado ya tomado
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
        _bot_log(f"Aviso carga grabaciones: {ex}")
        return []


VOICE_TURNS_LOG = load_recordings_metadata()
VOICE_MANUALLY_DISCONNECTED = {}
VOICE_INTERNAL_DISCONNECT = {}


def save_recordings_metadata():
    """Persiste de forma atómica el registro de grabaciones en recordings_metadata.json."""
    try:
        bs = _bs()
        lock = getattr(bs, "VOICE_TURNS_LOCK", VOICE_TURNS_LOCK)
        turns_log = getattr(bs, "VOICE_TURNS_LOG", VOICE_TURNS_LOG)
        meta_file = getattr(bs, "METADATA_FILE", METADATA_FILE)
        with lock:
            data = list(turns_log)
        tmp = meta_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, meta_file)
    except Exception as ex:
        _bot_log(f"Aviso guardado grabaciones metadata: {ex}")


def set_voice_manually_disconnected(guild_id: int, duration_sec: float = None):
    """Bloquea la auto-conexión. Sin duración el bloqueo es indefinido."""
    if guild_id:
        dc_dict = getattr(_bs(), "VOICE_MANUALLY_DISCONNECTED", VOICE_MANUALLY_DISCONNECTED)
        dc_dict[guild_id] = float("inf") if duration_sec is None else time.time() + duration_sec


def mark_internal_voice_disconnect(guild_id: int):
    if guild_id:
        int_dict = getattr(_bs(), "VOICE_INTERNAL_DISCONNECT", VOICE_INTERNAL_DISCONNECT)
        int_dict[guild_id] = time.time()


def consume_internal_voice_disconnect(guild_id: int) -> bool:
    int_dict = getattr(_bs(), "VOICE_INTERNAL_DISCONNECT", VOICE_INTERNAL_DISCONNECT)
    ts = int_dict.pop(guild_id, None)
    return ts is not None and (time.time() - ts) < 15.0


def clear_voice_manually_disconnected(guild_id: int):
    if guild_id:
        dc_dict = getattr(_bs(), "VOICE_MANUALLY_DISCONNECTED", VOICE_MANUALLY_DISCONNECTED)
        dc_dict.pop(guild_id, None)


def is_voice_manually_disconnected(guild_id: int) -> bool:
    dc_dict = getattr(_bs(), "VOICE_MANUALLY_DISCONNECTED", VOICE_MANUALLY_DISCONNECTED)
    if not guild_id or guild_id not in dc_dict:
        return False
    if time.time() >= dc_dict[guild_id]:
        dc_dict.pop(guild_id, None)
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
        shorts = struct.unpack(f"<{count * 2}h", pcm_bytes[: count * 4])
        mono_shorts = [(shorts[i * 2] + shorts[i * 2 + 1]) // 2 for i in range(count)]
        return struct.pack(f"<{count}h", *mono_shorts)


class GeminiLiveVoiceSink(voice_recv.AudioSink):
    """
    Sink de audio bidireccional en tiempo real (estilo Gemini Live) para llamadas de Discord.
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
        _bot_log(f"🎙️ [Gemini Live] Sink activado y escuchando en #{ch_name}")

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

            if user is None and client and ssrc:
                uid = getattr(client, "_get_id_from_ssrc", lambda s: None)(ssrc)
                if uid and getattr(client, "guild", None):
                    user = client.guild.get_member(uid)

            count = len(pcm) // 2
            if count == 0:
                return
            shorts = struct.unpack(f"<{count}h", pcm)
            rms = int(math.sqrt(sum(s * s for s in shorts) / count))

            user_key = user.id if user else (f"ssrc_{ssrc}" if ssrc else "speaker")

            now = time.time()
            with self._lock:
                state = self.user_buffers.setdefault(
                    user_key,
                    {
                        "frames": [],
                        "last_speech_time": 0.0,
                        "in_speech": False,
                        "user": user,
                        "ssrc": ssrc,
                    },
                )
                if user and not state.get("user"):
                    state["user"] = user

                if rms >= self.silence_threshold_rms:
                    state["frames"].append(pcm)
                    state["last_speech_time"] = now
                    if not state["in_speech"]:
                        state["in_speech"] = True
                        u_name = getattr(user, "display_name", None) or getattr(user, "name", f"Usuario_{ssrc or 'voz'}")
                        _bot_log(f"🎙️ [Gemini Live VAD] Voz detectada de '{u_name}' (RMS: {rms})")
                    if len(state["frames"]) >= self.max_speech_frames:
                        frames = state["frames"][:]
                        state["frames"].clear()
                        state["in_speech"] = False
                        asyncio.run_coroutine_threadsafe(
                            self.process_speech_turn(state["user"], frames, ssrc=state.get("ssrc")),
                            self.loop,
                        )
                elif state["in_speech"]:
                    if len(state["frames"]) < self.max_speech_frames:
                        state["frames"].append(pcm)
                    if (now - state["last_speech_time"]) >= self.silence_timeout:
                        frames = state["frames"][:]
                        state["frames"].clear()
                        state["in_speech"] = False
                        if len(frames) >= self.min_speech_frames:
                            asyncio.run_coroutine_threadsafe(
                                self.process_speech_turn(state["user"], frames, ssrc=state.get("ssrc")),
                                self.loop,
                            )
        except Exception as e:
            _bot_log(f"Aviso en GeminiLiveVoiceSink.write: {e}")

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
                    _bot_log("⚠️ [Gemini Live Watchdog] AudioReader detenido. Reactivando escucha automáticamente...")
                    try:
                        client.listen(self)
                        _bot_log("✅ [Gemini Live Watchdog] Escucha reactivada con éxito.")
                    except Exception as ex:
                        _bot_log(f"Error reactivando listener de voz: {ex}")

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
                                _bot_log(f"🎙️ [VAD Fin Silencio] Turno completado para '{u_name}' ({len(frames)} tramas). Procesando...")
                for u, f, s in turns:
                    asyncio.create_task(self.process_speech_turn(u, f, ssrc=s))
            except asyncio.CancelledError:
                break
            except Exception as e:
                _bot_log(f"Aviso en watchdog de voz: {e}")

    async def send_dictation_to_channel(self, client, user: discord.Member, text: str, user_spoken: str = "") -> tuple[bool, str]:
        """Envía un mensaje dictado por voz desde Gemini Live al chat de texto correspondiente."""
        try:
            guild = getattr(client, "guild", None)
            target_ch = None

            if guild and user_spoken:
                u_spoken_lower = user_spoken.lower()
                for tch in getattr(guild, "text_channels", []):
                    c_clean = re.sub(r"[^a-zA-Z0-9]", "", tch.name.lower())
                    if len(c_clean) >= 4 and re.search(r"\b(?:canal|chat)\s+(?:de\s+)?" + re.escape(c_clean) + r"\b", u_spoken_lower):
                        target_ch = tch
                        break

            if not target_ch:
                target_ch = getattr(client, "channel", None)

            u_name = getattr(user, "display_name", None) or getattr(user, "name", "Usuario")
            msg_content = f"🎙️ **{u_name}** *(vía Gemini Live)*: {text}"

            sent = False
            sent_ch_name = ""
            if target_ch and hasattr(target_ch, "send"):
                try:
                    await target_ch.send(msg_content)
                    sent = True
                    sent_ch_name = getattr(target_ch, "name", "")
                    _bot_log(f"💬 [Gemini Live Chat] Dictado de '{u_name}' enviado a #{sent_ch_name}: \"{text}\"")
                except Exception as ex_send:
                    _bot_log(f"Aviso enviando dictado a #{getattr(target_ch, 'name', '')}: {ex_send}")

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
                    sent_ch_name = getattr(fallback_ch, "name", "")
                    _bot_log(f"💬 [Gemini Live Chat Fallback] Dictado de '{u_name}' enviado a #{sent_ch_name}: \"{text}\"")
                    sent = True

            return sent, sent_ch_name
        except Exception as e:
            _bot_log(f"Error enviando dictado a chat: {e}")
            return False, ""

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

            bs = _bs()
            get_mem_fn = getattr(bs, "get_user_memory_ctx", lambda uid: "")
            spain_now_fn = getattr(bs, "get_spain_now_str", lambda: "")
            avail_fn = getattr(bs, "get_available_models", lambda: [])
            cooldown_fn = getattr(bs, "mark_model_cooldown", lambda m, s=60: None)
            search_fn = getattr(bs, "search_web_lite", lambda q, n=3: "")
            gemini_key = getattr(bs, "GEMINI_KEY", "")
            rec_dir = getattr(bs, "RECORDINGS_DIR", RECORDINGS_DIR)
            v_lock = getattr(bs, "VOICE_TURNS_LOCK", VOICE_TURNS_LOCK)
            v_log = getattr(bs, "VOICE_TURNS_LOG", VOICE_TURNS_LOG)

            user_name = getattr(user, "display_name", None) or getattr(user, "name", None) or f"Usuario_{ssrc or 'voz'}"
            user_id = getattr(user, "id", None)
            user_mem = get_mem_fn(user_id) if user_id else ""
            channel_name = getattr(getattr(client, "channel", None), "name", "llamada")
            channel_members = getattr(getattr(client, "channel", None), "members", [])
            members_str = ", ".join([m.display_name for m in channel_members if not m.bot]) or user_name
            _bot_log(f"🎙️ [Gemini Live Turno] Procesando audio de '{user_name}' ({len(frames)} tramas, {duration_s}s, {len(wav_bytes)} B)...")

            clean_uname = re.sub(r"[^a-zA-Z0-9_\-]", "", user_name)[:20] or "Usuario"
            turn_timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"{turn_timestamp_str}_{clean_uname}_{int(time.time()*1000)%100000}.wav"
            file_path = os.path.join(rec_dir, filename)
            try:
                with open(file_path, "wb") as f_wav:
                    f_wav.write(wav_bytes)
            except Exception as e_w:
                _bot_log(f"Aviso guardando archivo audio: {e_w}")

            now = time.time()
            record_entry = {
                "id": filename.replace(".wav", ""),
                "timestamp": spain_now_fn(),
                "epoch": now,
                "user": user_name,
                "user_id": str(user_id) if user_id else None,
                "duration_s": duration_s,
                "filename": filename,
                "audio_url": f"/audios/file/{filename}",
                "transcription": "",
                "bot_reply": "",
                "status": "procesando",
            }
            with v_lock:
                v_log.append(record_entry)
            save_recordings_metadata()

            time_since_last_reply = now - getattr(self, "last_bot_reply_time", 0.0)
            is_dialogue_active = time_since_last_reply < 35.0

            history_lines = []
            if is_dialogue_active:
                for item in self.recent_turns[-3:]:
                    if len(item) == 3:
                        u_n, u_t, b_txt = item
                        history_lines.append(f"- {u_n}: \"{u_t}\" -> Asistente: \"{b_txt}\"")
                    elif len(item) == 2:
                        spk, b_txt = item
                        history_lines.append(f"- Asistente (con {spk}): {b_txt}")
            hist_ctx = "\n".join(history_lines) if history_lines else "Sin intervenciones previas recientes."

            spain_now_str = spain_now_fn()
            prompt = (
                f"Eres el transcriptor acústico y asistente de voz en tiempo real del canal '{channel_name}' en Discord (España).\n"
                f"Tu nombre es estrictamente 'Asistente' (también respondes si dicen 'bot').\n"
                f"Gente en la sala de voz: {members_str}.\n"
                f"Usuario en este turno de voz: '{user_name}'.{user_mem}\n\n"
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
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "audio/wav", "data": b64_audio}},
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0.15, "maxOutputTokens": 600},
            }
            data = json.dumps(payload).encode("utf-8")
            response_text = ""
            for model_name in avail_fn():
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
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
                        cooldown_fn(model_name, 60)
                    else:
                        _bot_log(f"Aviso HTTP {e.code} API Gemini Live ({model_name}): {e}")
                    continue
                except Exception as e:
                    _bot_log(f"Aviso API Gemini Live ({model_name}): {e}")
                    continue

            if not response_text:
                _bot_log("⚠️ [Gemini Live] Ningún modelo respondió satisfactoriamente para la intervención de voz.")

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

            u_clean = re.sub(r"\[[^\]]*\]", " ", user_spoken).lower().strip()
            has_wake_word = bool(re.search(r"\b(asistente|bot)\b", u_clean))
            is_ignored_sound = any(tag in user_spoken for tag in ["[ININTELIGIBLE]", "[Risas]", "[Ruido]", "[Silencio]"])

            disconnect_patterns = [
                r"\b(vete|sal|salte|descon[eé]ctate|m[aá]rchate|l[aá]rgate)\s+(de\s+la\s+llamada|del\s+canal|de\s+voz|de\s+aqu[ií])\b",
                r"\b(asistente|bot)\s+(salte|vete|descon[eé]ctate|l[aá]rgate)\b",
                r"\b(abandona\s+la\s+llamada)\b",
                r"\b(a\s+la\s+(puta\s+)?calle\s+bot)\b",
            ]
            explicit_disconnect_intent = any(re.search(pat, u_clean) for pat in disconnect_patterns)
            is_disconnect_cmd = "[DESCONECTAR]" in bot_reply or (has_wake_word and explicit_disconnect_intent)

            if is_disconnect_cmd:
                record_entry["status"] = "desconectado"
                record_entry["bot_reply"] = "[DESCONECTAR]"
                save_recordings_metadata()
                guild_id = client.guild.id if hasattr(client, "guild") and client.guild else None
                if guild_id:
                    set_voice_manually_disconnected(guild_id)
                _bot_log(f"🔌 [Gemini Live Desconectar] '{user_name}' pidió desconectar ('{user_spoken}'). Saliendo de la sala.")
                if client.is_playing():
                    client.stop()
                try:
                    await client.disconnect(force=True)
                except Exception as ex_dc:
                    _bot_log(f"Aviso al desconectar por voz: {ex_dc}")
                return

            silence_patterns = [
                r"\b(c[aá]llate|silencio|shh+|calla|para\s+ya|para\s+de\s+hablar|cierra\s+el\s+pico|cierra\s+la\s+boca)\b",
                r"\b(asistente|bot)\s+(c[aá]llate|silencio|calla|para)\b",
                r"\b(otra\s+m[aá]s\s+y\s+te\s+vas)\b",
            ]
            explicit_silence_intent = any(re.search(pat, u_clean) for pat in silence_patterns)
            is_silence_cmd = (
                "[SILENCIO]" in bot_reply
                or (has_wake_word and explicit_silence_intent)
                or (client.is_playing() and explicit_silence_intent)
            )

            if is_silence_cmd:
                record_entry["status"] = "silenciado"
                record_entry["bot_reply"] = "[SILENCIO]"
                save_recordings_metadata()
                _bot_log(f"🤫 [Gemini Live Silencio] Orden de silencio de '{user_name}'. Cortando audio.")
                if client.is_playing():
                    client.stop()
                return

            chat_patterns = [
                r"\b(?:pon|escribe|manda|env[ií]a|di|dile)\s+(?:en\s+el|al|por\s+el)\s+chat\b",
                r"\b(?:pon|escribe|manda|env[ií]a)\s+(?:un\s+mensaje|esto)\s+(?:en\s+el|al)\s+chat\b",
                r"\b(?:escribe|manda|env[ií]a)\s+al\s+canal\b",
            ]
            has_chat_pattern = any(re.search(pat, u_clean) for pat in chat_patterns)
            is_dictation = has_wake_word and ("[CHAT:" in bot_reply or has_chat_pattern)

            if not is_dictation:
                if not has_wake_word or not bot_reply or "[IGNORAR]" in bot_reply or bot_reply.strip() == "IGNORAR" or is_ignored_sound:
                    record_entry["status"] = "ignorado"
                    record_entry["bot_reply"] = "[IGNORAR]"
                    save_recordings_metadata()
                    _bot_log(f"🎙️ [Gemini Live Filtro Asistente] '{user_name}' ('{user_spoken}') -> [IGNORAR] (Wake word: {has_wake_word})")
                    return

            if is_dictation:
                chat_msg_to_send = ""
                m_chat = re.search(r"\[CHAT:\s*([^\]]+)\]", bot_reply, re.IGNORECASE)
                if m_chat:
                    chat_msg_to_send = m_chat.group(1).strip()
                    bot_reply = re.sub(r"\[CHAT:\s*([^\]]+)\]", "", bot_reply).strip()
                elif has_chat_pattern:
                    guild = getattr(client, "guild", None)
                    known_channels = [tch.name.lower() for tch in getattr(guild, "text_channels", [])] if guild else []
                    target_ch_name = None
                    for ch in known_channels:
                        if len(ch) >= 4 and re.search(r"\b(?:canal|chat)\s+(?:de\s+)?" + re.escape(ch) + r"\b", u_clean):
                            target_ch_name = ch
                            break
                    ch_spec = r"(?:\s+(?:de\s+)?" + re.escape(target_ch_name) + r")?" if target_ch_name else r"(?:\s+de\s+(?:texto|voz))?"
                    pat = (
                        r"^(?:asistente|bot)?.*?\b(?:pon|escribe|manda|env[ií]a|di|dile)\s+(?:un\s+mensaje\s+)?(?:en\s+el|al|por\s+el)\s+(?:chat|canal)"
                        + ch_spec
                        + r"\s*(?:que\s+|:\s*|\s+)?(.*)$"
                    )
                    m_ext = re.search(pat, u_clean, re.I)
                    if m_ext and m_ext.group(1).strip():
                        chat_msg_to_send = m_ext.group(1).strip()

                if chat_msg_to_send:
                    chat_msg_to_send = chat_msg_to_send.strip(" \"'")
                    if chat_msg_to_send.lower().startswith("que "):
                        chat_msg_to_send = chat_msg_to_send[4:].strip()
                    sent_ok, ch_name = await self.send_dictation_to_channel(client, user, chat_msg_to_send, user_spoken=user_spoken)
                    if sent_ok:
                        if not bot_reply or bot_reply.strip() in ("", "[IGNORAR]"):
                            target_ref = f"#{ch_name}" if ch_name else "el chat"
                            bot_reply = f"Listo, ya lo he puesto en {target_ref}."
                    else:
                        bot_reply = "No he podido enviar el mensaje al chat, comprueba los permisos del canal."

            if "[BUSCAR:" in bot_reply:
                m_search = re.search(r"\[BUSCAR:\s*([^\]]+)\]", bot_reply, re.IGNORECASE)
                if m_search:
                    search_q = m_search.group(1).strip()
                    _bot_log(f"🔍 [Gemini Live Web Search] Buscando en internet para voz: '{search_q}'")
                    web_ctx = await asyncio.to_thread(search_fn, search_q, 3)
                    if web_ctx:
                        search_summary_prompt = (
                            f"Estás en vivo por voz en Discord con '{user_name}'.\n"
                            f"El usuario preguntó: '{user_spoken}'.\n"
                            f"Resultados de internet:\n{web_ctx}\n\n"
                            f"Resume la respuesta en 2 frases claras, amables y directas para locutar por voz en español de España (sin markdown ni emojis):"
                        )
                        sum_payload = {
                            "contents": [{"parts": [{"text": search_summary_prompt}]}],
                            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 300},
                        }
                        s_data = json.dumps(sum_payload).encode("utf-8")
                        search_summary_done = False
                        for s_model in avail_fn():
                            s_url = f"https://generativelanguage.googleapis.com/v1beta/models/{s_model}:generateContent?key={gemini_key}"
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
                                    cooldown_fn(s_model, 60)
                                else:
                                    _bot_log(f"Aviso HTTP {e_http.code} resumen búsqueda voz ({s_model}): {e_http}")
                                continue
                            except Exception as e_sum:
                                _bot_log(f"Aviso resumen búsqueda voz ({s_model}): {e_sum}")
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
                        _bot_log(f"🎙️ [Gemini Live Voz] Voz cambiada en llamada a '{self.voice_type}' por orden de '{user_name}'")
                bot_reply = re.sub(r"\[VOZ:\s*([a-zA-Z0-9_-]+)\]", "", bot_reply).strip()

            clean_resp = clean_text_for_tts(bot_reply)
            if not clean_resp:
                record_entry["status"] = "vacio"
                save_recordings_metadata()
                return

            if client.is_playing():
                if len(frames) < 22 and any(greeting in clean_resp.lower() for greeting in ["qué pasa", "dime", "hola"]):
                    _bot_log("🎙️ [Gemini Live Overlap] Ignorando interrupción menor para no cortar audio en curso.")
                    return
                client.stop()

            record_entry["status"] = "respondido"
            record_entry["bot_reply"] = clean_resp
            save_recordings_metadata()
            _bot_log(f"🎙️ [Gemini Live] '{user_name}' dijo: \"{user_spoken}\" -> Asistente: \"{clean_resp}\"")
            self.last_bot_reply_time = time.time()
            self.recent_turns.append((user_name, user_spoken, clean_resp))
            if len(self.recent_turns) > 8:
                self.recent_turns.pop(0)

            try:
                audio_file = await generate_speech_audio(clean_resp, voice_type=self.voice_type)
                async with self.playback_lock:
                    play_audio_in_voice(client, audio_file)
                _bot_log(f"🔊 [Gemini Live] Audio enviado a #{channel_name}")
            except Exception as ex:
                _bot_log(f"Error reproduciendo voz Gemini Live: {ex}")
        except Exception as ex_turn:
            _bot_log(f"Aviso procesando turno de voz: {ex_turn}")

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

    bot = getattr(_bs(), "bot", None)
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
                _bot_log(f"🎙️ [Voice Move] Moviendo Asistente de #{vc.channel.name} a #{channel.name}...")
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

    _bot_log(f"🎙️ [Voice Connect] Conectando Asistente a #{channel.name} (ID: {channel.id})...")
    vc = await channel.connect(cls=voice_recv.VoiceRecvClient, timeout=15.0, reconnect=True, self_deaf=False)
    if hasattr(vc, "_connection") and not vc.is_connected():
        try:
            from discord.voice_state import ConnectionFlowState

            vc._connection.state = ConnectionFlowState.connected
        except Exception:
            pass
    sink = GeminiLiveVoiceSink(vc, bot.loop)
    vc.listen(sink)
    _bot_log(f"🎙️ [Voice Connected] Conexión establecida y escuchando en #{channel.name}")
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
