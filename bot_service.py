"""
Servicio 24/7 de IA Multimodal para el Bot 'Asistente' en Discord.
Arquitectura Modular (Paquete 'modulos/'):
- modulos.graficos: Motor visual (FLUX.1, LaTeX PNG, gráficos QuickChart, Mermaid, terminal Pillow).
- modulos.juegos: Steam Store, El Tribunal Gaming, Trivial con IA, Tres en Raya, Conecta 4 y Ajedrez.
- modulos.voz: Parche DAVE E2EE, TTS neuronal Edge/Gemini, Gemini Live bidireccional y retención 24h.
- modulos.autoroles: Reemplazo integral 24/7 de Carl-bot (Auto-roles con toggle/personal y sugerencias).
- modulos.chat_ia: Modelos Gemini, System Prompt, búsqueda web, niveles Cakey Bot, XP, memoria y router.
- modulos.comandos: Registro oficial de los 22 Comandos Slash (@app_commands.command).
- modulos.web_server: Servidor HTTP multihilo en puerto 10000 para health-check de Render y audios.

bot_service.py actúa como el conector y orquestador central ligero (~180 líneas).
"""

import os
import sys
import json
import time
import asyncio
import threading
import collections
from datetime import datetime, timezone
import discord
from discord import app_commands

# Registrar bot_service en sys.modules para imports dinámicos y compatibilidad total con tests
sys.modules.setdefault("bot_service", sys.modules[__name__])

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Buffer de logs en memoria
GLOBAL_LOG_BUFFER = collections.deque(maxlen=200)


def bot_log(msg: str):
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    GLOBAL_LOG_BUFFER.append(line)


# Aplicar parche DAVE E2EE antes de inicializar clientes de voz
from modulos.voz import apply_dave_patch
apply_dave_patch()

# Configuración y credenciales
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

# Datos del servidor
TRIBUNAL_DATA_PATH = os.path.join(BASE_DIR, "datos", "tribunal_data.json")
TRIVIA_DATA_PATH = os.path.join(BASE_DIR, "datos", "trivia_data.json")


def load_tribunal_data() -> dict:
    if os.path.exists(TRIBUNAL_DATA_PATH):
        try:
            with open(TRIBUNAL_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Aviso lectura tribunal_data.json: {e}")
    return {"coop": [], "single": []}


def load_trivia_data() -> list:
    if os.path.exists(TRIVIA_DATA_PATH):
        try:
            with open(TRIVIA_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Aviso lectura trivia_data.json: {e}")
    return []


tribunal_data = load_tribunal_data()

# Cliente Discord y CommandTree
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ==========================================
# REEXPORTACIÓN DE MÓDULOS (COMPATIBILIDAD 100%)
# ==========================================

from modulos.graficos import (
    extract_action_block,
    generate_image_flux,
    _parse_latex_braces,
    replace_frac,
    sanitize_discord_math_text,
    render_math_image,
    render_chart_image,
    render_diagram_image,
    render_code_card_image,
    enhance_image_prompt,
    ImageActionView,
)

from modulos.voz import (
    clean_text_for_tts,
    TTS_VOICES,
    TTS_VOICE_ALIASES,
    generate_speech_audio,
    RECORDINGS_DIR,
    METADATA_FILE,
    RETENTION_SECONDS,
    VOICE_TURNS_LOCK,
    load_recordings_metadata,
    save_recordings_metadata,
    VOICE_TURNS_LOG,
    VOICE_MANUALLY_DISCONNECTED,
    VOICE_INTERNAL_DISCONNECT,
    set_voice_manually_disconnected,
    mark_internal_voice_disconnect,
    consume_internal_voice_disconnect,
    clear_voice_manually_disconnected,
    is_voice_manually_disconnected,
    pcm_stereo_to_mono_48k,
    GeminiLiveVoiceSink,
    ensure_voice_connection,
    play_audio_in_voice,
)

from modulos.juegos import (
    fetch_steam_game,
    get_tribunal_query_ctx,
    get_steam_query_ctx,
    SteamView,
    TribunalView,
    RECENT_TRIVIA_IDS,
    CATEGORY_ALIASES,
    TRIVIA_CATEGORIES_INFO,
    generate_gemini_trivia_question,
    handle_next_trivia,
    TriviaView,
    check_ttt_winner_and_line,
    tictactoe_minimax,
    get_tictactoe_bot_move,
    TicTacToeButton,
    TicTacToeView,
    check_connect4_winner,
    drop_connect4_piece,
    get_connect4_bot_move,
    Connect4Button,
    Connect4View,
    chess,
    STOCKFISH_PATH,
    CHESS_GAMES,
    CHESS_PIECE_NAMES,
    CHESS_ICONS_WHITE,
    CHESS_ICONS_BLACK,
    CHESS_LEVELS,
    CHESS_TYPED_MOVE_RE,
    CHESS_SPANISH_PIECES,
    chess_icon,
    chess_board_url,
    chess_parse_typed,
    chess_piece_options,
    chess_dest_options,
    chess_moves_text,
    chess_result_text,
    ChessGame,
    chess_build_embed,
    ChessView,
    chess_finish,
    chess_gemini_pick,
    chess_stockfish_move,
    chess_bot_move,
    chess_run_bot_turn,
    chess_play_player_move,
    chess_try_typed_move,
)

from modulos.autoroles import (
    AUTOROLES_CATALOG,
    AUTOROLE_INFO_BY_ID,
    ALL_AUTOROLE_IDS,
    compute_autorole_toggle,
    compute_autorole_category_sync,
    build_autoroles_category_embed,
    build_autoroles_all_embeds,
    build_personal_autoroles_embed,
    _resolve_guild_member,
    _apply_role_changes_to_member,
    AutoRoleSelect,
    PersonalCategorySelect,
    PersonalAutoRolesView,
    _handle_mis_roles_button,
    _handle_limpiar_autoroles_button,
    AutoRolesPersistentView,
    AutoRoleCategoryView,
    is_admin_or_mod,
    SUGGESTIONS_CHANNEL_ID,
    SUGGESTION_VOTES_STATE,
    _extract_votes_from_embed,
    _extract_vote_state_from_embed,
    _update_suggestion_embed_votes,
    SuggestionDecisionModal,
    SuggestionPersistentView,
    _get_next_suggestion_number,
)

from modulos.chat_ia import (
    MODELS_PRIORITY,
    model_cooldowns,
    get_available_models,
    mark_model_cooldown,
    SYSTEM_PROMPT,
    call_gemini_multiturn,
    get_spain_now_str,
    USER_MEMORY_PATH,
    user_memory,
    load_user_memory,
    save_user_memory,
    get_user_memory_ctx,
    _LIVE_LEVELS_CACHE,
    _LIVE_LEVELS_CACHE_TIME,
    _LIVE_LEVELS_TTL,
    _LIVE_LEVELS_LOCK,
    get_live_levels_dict,
    calculate_xp_gap,
    TEXT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    search_web_lite,
    build_search_query,
    fetch_url_content,
    extract_attachments_parts,
    get_live_voice_radar,
    get_live_members_ctx,
    get_member_dossier,
    get_pins_context,
    user_cooldowns,
    COOLDOWN_SECONDS,
    _handle_message_safe,
)

from modulos.comandos import (
    register_slash_commands,
    cmd_dibuja,
    cmd_steam,
    cmd_tribunal,
    cmd_perfil,
    cmd_pregunta,
    cmd_voz,
    cmd_musica,
    cmd_habla,
    cmd_geminilive,
    cmd_cambiar_voz,
    cmd_unete,
    cmd_desconecta,
    cmd_para_audio,
    cmd_recuerda,
    cmd_trivial,
    cmd_ranking_trivial,
    cmd_tres_en_raya,
    cmd_conecta4,
    cmd_xp,
    cmd_autoroles,
    cmd_sugerencia,
    cmd_ajedrez,
)

# Registrar los 22 comandos slash en el CommandTree
register_slash_commands(tree)

# ==========================================
# EVENTOS DEL CICLO DE VIDA DE DISCORD
# ==========================================

@bot.event
async def on_ready():
    bot_log(f"Bot '{bot.user}' conectado y listo en Discord.")
    bot_log(f"Motores de IA con respaldo: {MODELS_PRIORITY}")
    bot_log(f"Ajedrez: python-chess {'OK' if chess else 'NO disponible'} | Stockfish {'OK' if os.path.exists(STOCKFISH_PATH) else 'NO encontrado'} ({STOCKFISH_PATH})")
    bot_log("Capacidades activas: Gemini Live en Voz (/geminilive), Auto-Roles 24/7 (/autoroles), Sugerencias (/sugerencia), Memoria Persistente, Trivial, Niveles Reales, Búsqueda Web, FLUX.1, Steam Store, Tribunal Gaming y 22 Slash Commands.")

    # Registrar vistas interactivas persistentes 24/7 (sobreviven a reinicios de Render sin expirar jamás)
    try:
        bot.add_view(AutoRolesPersistentView())
        bot.add_view(PersonalAutoRolesView())
        bot.add_view(SuggestionPersistentView())
        bot_log("🎭 [Persistent Views] AutoRolesPersistentView, PersonalAutoRolesView y SuggestionPersistentView registradas 24/7.")
    except Exception as e_view:
        bot_log(f"Aviso registrando vistas persistentes: {e_view}")

    # Sincronización instantánea de Slash Commands en el servidor
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

    # Tarea de vigilancia para canales de voz
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

    # Tarea periódica de limpieza de grabaciones con más de 24 horas
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


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    guild = member.guild
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
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    try:
        if chess is not None and await chess_try_typed_move(message):
            return
        await _handle_message_safe(message)
    except Exception as e:
        print(f"Error procesando mensaje: {e}")


# ==========================================
# SUPERVISOR PERSISTENTE Y ARRANQUE
# ==========================================

from modulos.web_server import (
    ReusableTCPServer,
    run_health_check_server,
)


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
