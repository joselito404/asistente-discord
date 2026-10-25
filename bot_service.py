"""
Servicio 24/7 de IA Multimodal y Runner Dual para los Bots 'Asistente' y 'Economia Asistente' en Discord.
Arquitectura Modular (Paquete 'modulos/'):
- modulos.graficos: Motor visual (FLUX.1, LaTeX PNG, gráficos QuickChart, Mermaid, terminal Pillow).
- modulos.juegos: Steam Store, El Tribunal Gaming, Trivial con IA, Tres en Raya, Conecta 4 y Ajedrez.
- modulos.voz: Parche DAVE E2EE, TTS neuronal Edge/Gemini, Gemini Live bidireccional y retención 24h.
- modulos.autoroles: Reemplazo integral 24/7 de Carl-bot (Auto-roles con toggle/personal y sugerencias).
- modulos.chat_ia: Modelos Gemini, System Prompt, búsqueda web, niveles Cakey Bot, XP, memoria y router.
- modulos.comandos: Registro oficial de Comandos Slash (22 Generales + 13 Economía).
- modulos.economia: Motor nativo de economía comunitaria, banca, robos, tienda, salarios, tragaperras 5x3, Blackjack 21, Ruleta Europea y Coinflip Dual.
- modulos.web_server: Servidor HTTP multihilo en puerto 10000 para health-check de Render y audios.

bot_service.py actúa como el conector y orquestador central con Arquitectura de Runner Dual.
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
ECONOMY_TOKEN = os.getenv("ECONOMY_DISCORD_TOKEN") or cfg.get("economy_bot_token")
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

# Clientes Discord y CommandTrees (Arquitectura Dual Runner)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

economy_bot = discord.Client(intents=intents)
economy_tree = app_commands.CommandTree(economy_bot)

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
    MAX_STORAGE_BYTES,
    TARGET_STORAGE_BYTES,
    enforce_storage_quota,
    generate_call_summary,
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
    build_category_personal_embed,
    _resolve_guild_member,
    _apply_role_changes_to_member,
    AutoRoleSelect,
    PersonalCategorySelect,
    SingleCategoryPersonalView,
    PersonalAutoRolesView,
    _handle_category_button,
    _handle_mis_roles_button,
    _handle_limpiar_autoroles_button,
    _handle_refrescar_autoroles_button,
    AutoRolesPersistentView,
    AutoRoleCategoryView,
    is_admin_or_mod,
)

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
    # Símbolos legados para compatibilidad
    SuggestionPersistentView,
    SUGGESTION_VOTES_STATE,
    _extract_votes_from_embed,
    _extract_vote_state_from_embed,
    _update_suggestion_embed_votes,
    _get_next_suggestion_number,
)

from modulos.starboard import (
    handle_starboard_reaction_add,
    handle_starboard_reaction_remove,
)


from modulos.chat_ia import (
    SERVER_EMOJIS_DATA,
    DISABLED_EMOJI_FALLBACK,
    format_server_emojis,
    MODELS_PRIORITY,
    model_cooldowns,
    get_available_models,
    mark_model_cooldown,
    SYSTEM_PROMPT_BODY,
    SYSTEM_PROMPT_A,
    SYSTEM_PROMPT_B,
    BOT_PERSONALITIES,
    ACTIVE_PERSONALITY,
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
    # Nuevos símbolos sociales, Mini-RAG y lurker
    fetch_youtube_info,
    fetch_twitter_info,
    fetch_reddit_info,
    fetch_tiktok_info,
    resolve_social_url,
    get_social_dynamics_ctx,
    record_voice_duo,
    record_duel_interaction,
    search_deep_channel_history,
    search_starboard_moments,
    format_episodic_memory,
    check_lurker_reaction,
    LURKER_ALLOWED_CHANNELS,
)

from modulos.economia import (
    PORRO_EMOJI,
    DEFAULT_JACKPOT,
    DEFAULT_STARTING_CASH,
    DEFAULT_STARTING_BANK,
    SLOT_SYMBOLS,
    SLOT_PAYLINES,
    SlotEngine,
    slot_engine,
    SlotsLayoutView,
    SlotsPlayAgainButton,
    SlotsPayoutsButton,
    get_balance,
    modify_balance,
    get_user_economy,
    ensure_user,
    get_server_jackpot,
    modify_server_jackpot,
    reset_server_jackpot,
    transfer_funds,
    can_work,
    execute_work,
    load_economy_data,
    save_economy_data,
    build_payouts_text,
    handle_slots_spin,
    handle_slots_interaction,
    deposit_cash,
    withdraw_cash,
    execute_rob,
    can_rob,
    user_has_shield,
    buy_shop_item,
    get_shop_catalog,
    build_shop_embed,
    ShopInteractiveView,
    SHOP_ITEMS,
    calculate_daily_salary,
    calculate_accumulated_salary,
    can_claim_salary,
    claim_salary,
    BlackjackHand,
    BlackjackEngine,
    blackjack_engine,
    ACTIVE_BLACKJACK_GAMES,
    parse_blackjack_bet,
    build_blackjack_embed,
    BlackjackView,
    ROULETTE_SEQUENCE,
    ROULETTE_RED,
    ROULETTE_BLACK,
    ROULETTE_GREEN,
    ROULETTE_BET_INFO,
    RouletteEngine,
    roulette_engine,
    RouletteActionView,
    parse_roulette_bet,
    build_roulette_embed,
    format_roulette_pocket,
    normalize_roulette_bet_type,
    is_roulette_winner,
    ACTIVE_COINFLIP_DUELS,
    CoinflipEngine,
    coinflip_engine,
    CoinflipActionView,
    CoinflipChallengeView,
    parse_coinflip_bet,
    normalize_coinflip_side,
    build_coinflip_embed,
    CasinoHubView,
    build_casino_hub_embed,
    get_level_role_multiplier,
    can_crime,
    execute_crime,
    use_inventory_item,
    check_and_expire_buffs,
    build_inventory_embed,
    InventoryView,
    get_economy_leaderboard,
    build_ranking_embed,
    RankingView,
    admin_modify_money,
    admin_airdrop_role,
    gift_inventory_item,
    MIN_SLOTS_BET,
    MIN_BLACKJACK_BET,
    MIN_ROULETTE_BET,
    MIN_COINFLIP_BET,
    ECONOMY_CATEGORY_ID,
    ALLOWED_ECONOMY_CHANNELS,
)

from modulos.comandos import (
    GENERAL_SLASH_COMMANDS,
    ECONOMY_SLASH_COMMANDS,
    ALL_SLASH_COMMANDS,
    register_general_commands,
    register_economy_commands,
    register_slash_commands,
    ensure_economy_channel,
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
    cmd_resumen_llamada,
    cmd_recuerda,
    cmd_trivial,
    cmd_ranking_trivial,
    cmd_tres_en_raya,
    cmd_conecta4,
    cmd_xp,
    cmd_autoroles,
    cmd_sugerencia,
    cmd_ajedrez,
    cmd_juicio,
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
)

from modulos.comandos_bolsa import handle_bolsa_interaction
from modulos.comandos_economia import handle_admin_eco_interaction
from modulos.persistencia_discord import (
    restore_from_discord,
    backup_to_discord,
    setup_persistence,
)

from modulos.cakey_client import (
    get_cakey_leaderboard,
    get_user_cakey_data,
)

# Registrar comandos en sus árboles correspondientes (Dual Runner)
register_general_commands(tree)
register_economy_commands(economy_tree)

# ==========================================
# EVENTOS DEL CICLO DE VIDA DE DISCORD
# ==========================================

@bot.event
async def on_ready():
    bot_log(f"Bot '{bot.user}' conectado y listo en Discord.")
    bot_log(f"Motores de IA con respaldo: {MODELS_PRIORITY}")
    bot_log(f"Ajedrez: python-chess {'OK' if chess else 'NO disponible'} | Stockfish {'OK' if os.path.exists(STOCKFISH_PATH) else 'NO encontrado'} ({STOCKFISH_PATH})")
    bot_log("Capacidades activas: Gemini Live en Voz (/geminilive), Auto-Roles 24/7 (/autoroles), Sugerencias 2.0 (/sugerencia, /panel_sugerencias), Memoria Persistente, Trivial, Niveles Reales, Búsqueda Web, FLUX.1, Steam Store, Tribunal Gaming y 24 Slash Commands Generales.")

    # 1. Hidratación inicial desde Discord (Render Cloud 24/7 - docs/PERSISTENCIA_DATOS.md)
    try:
        restore_res = await restore_from_discord(bot)
        if restore_res.get("restored"):
            bot_log(f"💾 [Persistencia] Hidratación inicial completada desde Discord: {restore_res.get('files')}")
        else:
            bot_log("💾 [Persistencia] Hidratación completada: iniciando con versión local.")
        # Configurar tareas periódicas de respaldo (5 min) e interceptores SIGTERM/SIGINT
        setup_persistence(bot)
    except Exception as e_pers:
        bot_log(f"Aviso en inicialización de persistencia Discord: {e_pers}")

    # Registrar vistas interactivas persistentes 24/7 (sobreviven a reinicios de Render sin expirar jamás)
    try:
        bot.add_view(AutoRolesPersistentView())
        bot.add_view(PersonalAutoRolesView())
        bot.add_view(SuggestionActiveView())
        bot.add_view(SuggestionHubView())
        bot_log("🎭 [Persistent Views] AutoRolesPersistentView, PersonalAutoRolesView, SuggestionActiveView y SuggestionHubView registradas 24/7.")
    except Exception as e_view:
        bot_log(f"Aviso registrando vistas persistentes: {e_view}")

    # Sincronización instantánea de Slash Commands Generales en el servidor
    try:
        GUILD_ID = 1446143936891715616
        guild_obj = discord.Object(id=GUILD_ID)
        tree.copy_global_to(guild=guild_obj)
        await tree.sync(guild=guild_obj)
        bot_log(f"Comandos Slash Generales (24) sincronizados limpiamente en el servidor ID {GUILD_ID} (sin duplicados).")
    except Exception as e:
        bot_log(f"Aviso sincronización comandos slash generales: {e}")

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

    # Tarea periódica de salvaguarda de cuota de grabaciones en disco (Render Cloud)
    async def _recordings_retention_cleaner():
        await asyncio.sleep(60.0)
        while not bot.is_closed():
            try:
                purged = enforce_storage_quota()
                if purged > 0:
                    bot_log(f"🧹 [Grabaciones] Salvaguarda de cuota ejecutada: purgados {purged} audios antiguos.")
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
            ch_name = getattr(vc.channel, "name", "llamada")
            bot_log(f"ℹ️ Canal de voz #{ch_name} vacío. Desconectando Asistente...")

            # Auto-resumen opcional al desconectarse de la sala de voz
            try:
                cutoff = time.time() - 3600.0  # Última hora de la llamada
                with VOICE_TURNS_LOCK:
                    recent_real_turns = [
                        t for t in VOICE_TURNS_LOG
                        if t.get("epoch", 0.0) >= cutoff
                        and t.get("transcription")
                        and t.get("transcription") not in ["(audio procesado)", "[Silencio]", "[Ruido]"]
                        and not str(t.get("transcription", "")).strip().startswith(("[Silencio]", "[Ruido]", "[ininteligible]"))
                    ]
                if len(recent_real_turns) > 3:
                    bot_log(f"📝 [Voice Summary] Generando crónica automática de llamada en #{ch_name} ({len(recent_real_turns)} intervenciones)...")
                    summary_embed = await generate_call_summary(hours=1.0, channel_name=ch_name)
                    target_ch = None
                    if hasattr(vc.channel, "send"):
                        target_ch = vc.channel
                    if not target_ch and getattr(vc.channel, "category", None):
                        for tch in vc.channel.category.text_channels:
                            target_ch = tch
                            break
                    if not target_ch:
                        target_ch = guild.get_channel(1446143938044887052)
                    if not target_ch:
                        for tch in guild.text_channels:
                            if "shit-de-todos-los-dias" in tch.name:
                                target_ch = tch
                                break
                    if not target_ch:
                        target_ch = guild.system_channel
                    if target_ch and hasattr(target_ch, "send"):
                        await target_ch.send(embed=summary_embed)
                        bot_log(f"📢 [Voice Summary] Crónica de voz publicada en #{getattr(target_ch, 'name', 'canal')}")
            except Exception as e_sum:
                bot_log(f"Aviso generando resumen automático de llamada: {e_sum}")

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


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component and not interaction.response.is_done():
        cid = interaction.data.get("custom_id", "")
        if cid.startswith("slots:"):
            await handle_slots_interaction(interaction)
        elif cid.startswith("bolsa:"):
            await handle_bolsa_interaction(interaction)
        elif cid.startswith("admin_eco:"):
            await handle_admin_eco_interaction(interaction)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    try:
        await handle_starboard_reaction_add(payload, bot)
    except Exception as e:
        bot_log(f"Error procesando reaction_add en starboard: {e}")


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    try:
        await handle_starboard_reaction_remove(payload, bot)
    except Exception as e:
        bot_log(f"Error procesando reaction_remove en starboard: {e}")


# ==========================================
# EVENTOS DEL BOT DE ECONOMÍA (ECONOMIA ASISTENTE)
# ==========================================

_XP_WATCHER_STARTED = False


@economy_bot.event
async def on_ready():
    global _XP_WATCHER_STARTED
    GUILD_ID = 1446143936891715616
    guild_obj = discord.Object(id=GUILD_ID)
    try:
        economy_tree.copy_global_to(guild=guild_obj)
        await economy_tree.sync(guild=guild_obj)
        bot_log(f"Bot de Economía '{economy_bot.user}' conectado y listo en Discord.")
        bot_log(f"Comandos de Economía (23) sincronizados limpiamente en el servidor ID {GUILD_ID}.")
    except Exception as e:
        bot_log(f"Aviso sincronización comandos de economía: {e}")

    activity = discord.Activity(type=discord.ActivityType.watching, name="Casino y Porros (/slots)")
    await economy_bot.change_presence(activity=activity)

    async def _xp_passes_expiration_watcher():
        await asyncio.sleep(10.0)
        while not economy_bot.is_closed():
            try:
                expired_buffs = check_and_expire_buffs()
                if expired_buffs:
                    guild = economy_bot.get_guild(GUILD_ID) or bot.get_guild(GUILD_ID)
                    for exp in expired_buffs:
                        uid_str = exp.get("user_id")
                        role_id_str = exp.get("role_id")
                        b_name = exp.get("name", "Pase XP")
                        if not uid_str or not role_id_str or not guild:
                            continue
                        # Comprobar si el usuario sigue teniendo otro buff activo con el mismo role_id
                        udata = get_user_economy(uid_str)
                        still_has_role_buff = any(
                            str(b.get("role_id")) == str(role_id_str)
                            for b in udata.get("active_buffs", [])
                        )
                        if still_has_role_buff:
                            continue
                        role = guild.get_role(int(role_id_str))
                        member = guild.get_member(int(uid_str))
                        if not member:
                            try:
                                member = await guild.fetch_member(int(uid_str))
                            except Exception:
                                member = None
                        if role and member and role in getattr(member, "roles", []):
                            try:
                                await member.remove_roles(
                                    role,
                                    reason=f"Expiración automática del pase temporal '{b_name}'",
                                )
                                bot_log(f"⏳ [XP Watcher] Rol '{role.name}' retirado a {member.display_name} ({uid_str}) por vencimiento.")
                            except Exception as ex_rm:
                                bot_log(f"Aviso retirando rol expirado {role.name} a {uid_str}: {ex_rm}")
            except Exception as e_watch:
                bot_log(f"Aviso en _xp_passes_expiration_watcher: {e_watch}")
            await asyncio.sleep(1800.0)

    if not _XP_WATCHER_STARTED:
        _XP_WATCHER_STARTED = True
        economy_bot.loop.create_task(_xp_passes_expiration_watcher())

    async def _bolsa_lifecycle_watcher():
        await asyncio.sleep(15.0)
        while not economy_bot.is_closed():
            try:
                now_utc = datetime.now(timezone.utc)
                today_str = now_utc.strftime("%Y-%m-%d")
                
                # 1. Snapshot diario de Cakey Bot
                from modulos.bolsa_sanvi import load_cakey_history, save_cakey_history
                from modulos.cakey_client import get_cakey_leaderboard
                history = load_cakey_history()
                if today_str not in history.get("snapshots", {}):
                    lb = await get_cakey_leaderboard()
                    if lb:
                        snap = {}
                        for uid, udata in lb.items():
                            uname = udata.get("username")
                            if uname:
                                snap[uname] = {
                                    "level": udata.get("level", 0),
                                    "xp": udata.get("xp", 0.0),
                                    "messages": udata.get("messages", 0),
                                    "voice_minutes": udata.get("voice_minutes", 0),
                                }
                        history["snapshots"][today_str] = snap
                        save_cakey_history(history)
                        bot_log(f"📈 [Bolsa Sanvi] Snapshot diario de Cakey Bot registrado para {today_str} ({len(snap)} miembros).")

                # 2. Reparto de dividendos semanales los domingos a las 22:00 (Hora Peninsular Española, [Confirmada · Jose · 25/10/2026])
                from zoneinfo import ZoneInfo
                now_es = datetime.now(ZoneInfo("Europe/Madrid"))
                if now_es.weekday() == 6 and now_es.hour == 22 and now_es.minute < 15:
                    from modulos.bolsa_sanvi import distribute_weekly_dividends, load_pool_data, save_pool_data
                    p_data = load_pool_data()
                    last_dist = p_data.get("last_distribution_date")
                    if last_dist != today_str and p_data.get("accumulated_pool", 0) > 0:
                        dist_res = distribute_weekly_dividends()
                        p_data["last_distribution_date"] = today_str
                        save_pool_data(p_data)
                        bot_log(f"🏆 [Bolsa Sanvi] Dividendos dominicales (22:00 ES) repartidos: {dist_res.get('distributed_amount', 0):,.2f} Porros.")
                        # Aviso oficial en #🏪tienda-y-mercado🏪 (ID: 1549512919694442547, [Confirmada · Jose · 25/10/2026])
                        try:
                            ch_eco = economy_bot.get_channel(1549512919694442547)
                            if ch_eco:
                                emb = discord.Embed(
                                    title="🏆 Liquidación Semanal del Yield Pool — Bolsa Sanvi",
                                    description=(
                                        f"Se han repartido **{dist_res.get('distributed_amount', 0):,.2f} Porros** "
                                        f"en dividendos entre **{dist_res.get('recipients_count', 0)} accionistas**, "
                                        "ingresados directamente en sus cuentas bancarias.\n\n"
                                        "¡Gracias por invertir y holdear en la Bolsa Sanvi!"
                                    ),
                                    color=0x00E676
                                )
                                await ch_eco.send(embed=emb)
                        except Exception as e_ch:
                            bot_log(f"Aviso al enviar embed de Yield Pool en tienda-y-mercado: {e_ch}")
            except Exception as e_bolsa_loop:
                bot_log(f"Aviso en _bolsa_lifecycle_watcher: {e_bolsa_loop}")
            await asyncio.sleep(600.0)

    economy_bot.loop.create_task(_bolsa_lifecycle_watcher())


@economy_bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component and not interaction.response.is_done():
        cid = interaction.data.get("custom_id", "")
        if cid.startswith("slots:"):
            await handle_slots_interaction(interaction)
        elif cid.startswith("bolsa:"):
            await handle_bolsa_interaction(interaction)
        elif cid.startswith("admin_eco:"):
            await handle_admin_eco_interaction(interaction)



# ==========================================
# SUPERVISOR PERSISTENTE Y ARRANQUE DUAL
# ==========================================

from modulos.web_server import (
    ReusableTCPServer,
    run_health_check_server,
)


async def run_bots():
    """Ejecuta concurrentemente en el mismo event loop ambos bots de Discord."""
    tasks = [bot.start(TOKEN)]
    if ECONOMY_TOKEN:
        tasks.append(economy_bot.start(ECONOMY_TOKEN))
    await asyncio.gather(*tasks)


def start_bot_persistent():
    """Bucle supervisor persistente para mantener los dos bots conectados 24/7 sin caídas."""
    while True:
        try:
            bot_log("Iniciando conexión dual de bots con Discord (Asistente + Economia)...")
            asyncio.run(run_bots())
        except (KeyboardInterrupt, SystemExit):
            bot_log("Cierre manual solicitado.")
            break
        except Exception as e:
            bot_log(f"Excepción en run_bots(): {e}. Reintentando en 5 segundos...")
            time.sleep(5)
        bot_log("run_bots() finalizó. Reanudando en 5 segundos...")
        time.sleep(5)


if __name__ == "__main__":
    t = threading.Thread(target=run_health_check_server, daemon=True)
    t.start()
    start_bot_persistent()
