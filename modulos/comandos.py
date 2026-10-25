"""
Fachada de Reexportación y Compatibilidad de Comandos Slash para 'Asistente':
- Reexporta los 23 comandos de modulos.comandos_generales (Bot Asistente).
- Reexporta los 20 comandos de modulos.comandos_economia (Bot Economia Asistente).
- Proporciona ALL_SLASH_COMMANDS y register_slash_commands para retrocompatibilidad total.
"""

from discord import app_commands

from modulos.comandos_generales import (
    GENERAL_SLASH_COMMANDS,
    register_general_commands,
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
    cmd_resumen_llamada,
    cmd_trivial,
    cmd_ranking_trivial,
    cmd_tres_en_raya,
    cmd_conecta4,
    cmd_ajedrez,
    cmd_autoroles,
    cmd_sugerencia,
    cmd_panel_sugerencias,
    # Componentes y helpers generales reexportados
    _bs,
    _bot_log,
    _get_bot,
    _get_base_dir,
    _get_tribunal_data,
    _load_trivia_data,
    _resolve_guild_member,
    _get_next_suggestion_number,
    is_admin_or_mod,
    generate_gemini_trivia_question,
    AUTOROLES_CATALOG,
    AutoRoleCategoryView,
    AutoRolesPersistentView,
    CATEGORY_ALIASES,
    CHESS_GAMES,
    CHESS_LEVELS,
    ChessGame,
    ChessView,
    chess_build_embed,
    chess_finish,
    chess_run_bot_turn,
    Connect4View,
    RECENT_TRIVIA_IDS,
    SUGGESTIONS_CHANNEL_ID,
    SUGGESTION_VOTES_STATE,
    SuggestionPersistentView,
    TTS_VOICES,
    TicTacToeView,
    TriviaView,
    build_autoroles_all_embeds,
    build_autoroles_category_embed,
)

from modulos.comandos_economia import (
    ECONOMY_SLASH_COMMANDS,
    register_economy_commands,
    ECONOMY_CATEGORY_ID,
    ALLOWED_ECONOMY_CHANNELS,
    ensure_economy_channel,
    _handle_blackjack_command,
    _handle_roulette_command,
    _handle_coinflip_command,
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

# Total de 43 comandos para retrocompatibilidad total
ALL_SLASH_COMMANDS = GENERAL_SLASH_COMMANDS + ECONOMY_SLASH_COMMANDS


def register_slash_commands(tree: app_commands.CommandTree):
    """Registra de forma segura todos los comandos slash (generales y economía) en el árbol de comandos."""
    register_general_commands(tree)
    register_economy_commands(tree)


import sys
import types
import modulos.comandos_generales as _cmd_gen
import modulos.comandos_economia as _cmd_eco


class _FachadaComandos(types.ModuleType):
    """Fachada dinámica que propaga mutaciones de variables a los submódulos de comandos."""

    def __setattr__(self, name, value):
        for sub in (_cmd_gen, _cmd_eco):
            if hasattr(sub, name):
                setattr(sub, name, value)
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _FachadaComandos

