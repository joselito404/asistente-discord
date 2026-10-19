"""
Servidor HTTP de salud, estado en tiempo real, visor de logs y reproductor/descarga de grabaciones de voz (Puerto 10000 en Render).
Endpoints:
- GET /status: Estado JSON del bot, conexiones de voz, protocolo DAVE E2EE y hora española.
- GET /logs: Últimas 200 líneas del buffer global de logs.
- GET /audios (o /grabaciones): Panel web reproductor de grabaciones de las últimas 24h.
- GET /audios/zip (o /grabaciones/zip): Descarga en paquete ZIP de todas las grabaciones activas y su metadata.
- GET /audios/file/<fname>: Streaming/descarga segura de un archivo .wav individual (protegido con os.path.basename).
- GET /api/audios: API JSON del registro de intervenciones de voz.
"""

from datetime import datetime
import html
import http.server
import io
import json
import os
import socketserver
import sys
import urllib.parse
import zipfile


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


class ReusableTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_health_check_server():
    port = int(os.getenv("PORT", 10000))

    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            bs = _bs()
            bot = getattr(bs, "bot", None)
            log_buf = getattr(bs, "GLOBAL_LOG_BUFFER", [])
            recordings_dir = getattr(bs, "RECORDINGS_DIR", "recordings")
            metadata_file = getattr(bs, "METADATA_FILE", os.path.join(recordings_dir, "recordings_metadata.json"))
            voice_lock = getattr(bs, "VOICE_TURNS_LOCK", None)
            voice_log = getattr(bs, "VOICE_TURNS_LOG", [])
            spain_now_fn = getattr(bs, "get_spain_now_str", lambda: "")

            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/logs":
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.end_headers()
                content = "\n".join(log_buf) if log_buf else "Sin logs registrados aún."
                self.wfile.write(content.encode("utf-8"))
            elif parsed.path == "/status":
                try:
                    voice_data = []
                    for vc in list(getattr(bot, "voice_clients", [])):
                        conn = getattr(vc, "_connection", None)
                        dave = getattr(conn, "dave_session", None)
                        dave_info = {
                            "protocol_version": getattr(conn, "dave_protocol_version", 0),
                            "ready": getattr(dave, "ready", False) if dave else False,
                            "user_ids": dave.get_user_ids() if dave and hasattr(dave, "get_user_ids") else [],
                        }
                        voice_data.append(
                            {
                                "guild": str(vc.guild.name) if vc.guild else None,
                                "channel": str(getattr(vc.channel, "name", "desconocido")),
                                "is_connected": bool(vc.is_connected()),
                                "is_listening": bool(vc.is_listening()) if hasattr(vc, "is_listening") else False,
                                "is_playing": bool(vc.is_playing()) if hasattr(vc, "is_playing") else False,
                                "dave": dave_info,
                                "members": [m.display_name for m in getattr(vc.channel, "members", []) if not m.bot],
                            }
                        )
                    economy_bot = getattr(bs, "economy_bot", None)
                    payload = {
                        "bot_ready": bot.is_ready() if bot else False,
                        "bot_user": str(bot.user) if (bot and bot.user) else None,
                        "economy_bot_ready": economy_bot.is_ready() if economy_bot else False,
                        "economy_bot_user": str(economy_bot.user) if (economy_bot and economy_bot.user) else None,
                        "voice_clients": voice_data,
                        "server_time": spain_now_fn(),
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
                        if os.path.exists(metadata_file):
                            zf.write(metadata_file, arcname="recordings_metadata.json")
                        if os.path.exists(recordings_dir):
                            for fname in os.listdir(recordings_dir):
                                if fname.endswith(".wav"):
                                    fpath = os.path.join(recordings_dir, fname)
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
                    if voice_lock:
                        with voice_lock:
                            turns = list(reversed(voice_log))
                    else:
                        turns = list(reversed(voice_log))

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

                    body_content = (
                        "\n".join(cards_html)
                        if cards_html
                        else '<div class="empty-state"><h3>Aún no hay grabaciones en esta sesión</h3><p>Cuando alguien hable en la llamada de Discord, sus intervenciones aparecerán aquí con su reproductor de audio y transcripción.</p></div>'
                    )

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
                fpath = os.path.join(recordings_dir, fname)
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
                if voice_lock:
                    with voice_lock:
                        turns = list(reversed(voice_log))
                else:
                    turns = list(reversed(voice_log))
                d_b = json.dumps(turns, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.send_header("Content-length", str(len(d_b)))
                self.end_headers()
                self.wfile.write(d_b)
            else:
                is_rdy = bot.is_ready() if bot else False
                status = (
                    "OK - Asistente Bot Activo (Discord: Conectado)"
                    if is_rdy
                    else "OK - Asistente Bot Activo (Discord: Conectando...)"
                )
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

    log_fn = getattr(_bs(), "bot_log", print)
    try:
        with ReusableTCPServer(("", port), HealthHandler) as httpd:
            log_fn(f"Servidor de salud y logs HTTP activo en puerto {port} para Render")
            httpd.serve_forever()
    except Exception as e:
        log_fn(f"Aviso servidor salud: {e}")
