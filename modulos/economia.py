"""
Fachada de Reexportación y Compatibilidad de Economía y Casino para 'Asistente':
- Centraliza y reexporta el 100% de símbolos de:
  * modulos.economia_core
  * modulos.economia_tienda
  * modulos.casino_slots
  * modulos.casino_juegos
Garantiza retrocompatibilidad total e inmediata para bot_service.py y suites de tests.
"""

from modulos.economia_core import *
from modulos.economia_tienda import *
from modulos.casino_slots import *
from modulos.casino_juegos import *

# Reexportación explícita de componentes clave
from modulos.economia_core import (
    BASE_DIR,
    ECONOMY_DATA_PATH,
    PORRO_EMOJI,
    DEFAULT_STARTING_CASH,
    DEFAULT_STARTING_BANK,
    DEFAULT_JACKPOT,
    JACKPOT_FEED_PERCENT,
    ECONOMY_LOCK,
    ECONOMY_CATEGORY_ID,
    ALLOWED_ECONOMY_CHANNELS,
    MIN_SLOTS_BET,
    MIN_BLACKJACK_BET,
    MIN_ROULETTE_BET,
    MIN_COINFLIP_BET,
    WORK_MESSAGES,
    CRIME_SUCCESS_MESSAGES,
    CRIME_FAIL_MESSAGES,
    ROLE_SALARIES,
    DEFAULT_BASE_SALARY,
    LEVEL_ROLE_MULTIPLIERS,
    LEVEL_ROLE_MIN_LEVELS,
    _ECONOMY_CACHE,
    _bs,
    _bot_log,
    _get_default_structure,
    safe_write_json,
    load_economy_data,
    save_economy_data,
    ensure_user,
    get_user_economy,
    get_balance,
    modify_balance,
    get_server_jackpot,
    modify_server_jackpot,
    reset_server_jackpot,
    deposit_cash,
    withdraw_cash,
    transfer_funds,
    get_level_role_multiplier,
    can_work,
    execute_work,
    can_crime,
    execute_crime,
    user_has_shield,
    can_rob,
    execute_rob,
    calculate_daily_salary,
    calculate_accumulated_salary,
    can_claim_salary,
    claim_salary,
    get_economy_leaderboard,
    build_ranking_embed,
    RankingCategorySelect,
    RankingView,
    _normalize_target_field,
    admin_modify_money,
    admin_airdrop_role,
)

from modulos.economia_tienda import (
    SHOP_ITEMS,
    USABLE_ITEM_KEYS,
    TRANSFERABLE_ITEM_KEYS,
    get_shop_catalog,
    buy_shop_item,
    build_shop_embed,
    ShopItemSelect,
    ShopInteractiveView,
    use_inventory_item,
    check_and_expire_buffs,
    gift_inventory_item,
    _format_remaining_time,
    build_inventory_embed,
    InventoryView,
)

from modulos.casino_slots import (
    SLOT_SYMBOLS,
    SLOT_PAYLINES,
    SlotEngine,
    slot_engine,
    build_payouts_text,
    handle_slots_spin,
    SlotsPlayAgainButton,
    SlotsPayoutsButton,
    SlotsFreeSpinButton,
    SlotsLayoutView,
    handle_slots_interaction,
)

from modulos.casino_juegos import (
    format_bj_card,
    get_bj_card_value,
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
    ROULETTE_WHEEL_ORDER,
    format_roulette_pocket,
    normalize_roulette_bet_type,
    is_roulette_winner,
    parse_roulette_bet,
    RouletteEngine,
    roulette_engine,
    build_roulette_embed,
    RouletteActionView,
    ACTIVE_COINFLIP_DUELS,
    normalize_coinflip_side,
    parse_coinflip_bet,
    CoinflipEngine,
    coinflip_engine,
    build_coinflip_embed,
    CoinflipActionView,
    CoinflipChallengeView,
    CASINO_GAMES_INFO,
    build_casino_hub_embed,
    CasinoHubSelect,
    CasinoHubView,
)

import sys
import types
import modulos.economia_core as _core
import modulos.economia_tienda as _tienda
import modulos.casino_slots as _slots
import modulos.casino_juegos as _juegos


class _FachadaEconomia(types.ModuleType):
    """Fachada dinámica que propaga mutaciones de variables (como ECONOMY_DATA_PATH en tests) a los submódulos."""

    def __setattr__(self, name, value):
        for sub in (_core, _tienda, _slots, _juegos):
            if hasattr(sub, name):
                setattr(sub, name, value)
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = _FachadaEconomia

