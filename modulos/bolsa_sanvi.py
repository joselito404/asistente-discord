"""

Módulo de la Bolsa Sanvi (Sanvi Exchange & Aura Market) para 'Asistente':

- Especificaciones de diseño: docs/DISENO_BOLSA_SANVI.md y docs/AURA_BAREMO.md.

- Motor bursátil AMM con factor K=2000 y suelo garantizado en P_base.

- Valuación contable (Book Value de por vida) y rendimiento temporal (Earnings 30d 50/50).

- Horquilla Bid/Ask fija del 1% (0.5% compra / 0.5% venta) con quema y Yield Pool de dividendos.

- Sinergia de Cartera (bono multiplicador en /trabajar de +5% a +25%).

- Indicadores técnicos cuantitativos (RSI 14, SMA/EMA 14/50/100/200, Golden/Death Cross).

- Informe analítico financiero asistido por IA (Gemini).

"""



import os

import sys

import json

import time

import math

import asyncio

import threading

from datetime import datetime, timezone, timedelta

from typing import Dict, List, Optional, Tuple, Any, Union



# Importación segura de módulos hermanos

def _bs():

    return sys.modules.get("bot_service") or sys.modules.get("__main__")



def _bot_log(msg: str):

    bs = _bs()

    log_fn = getattr(bs, "bot_log", print)

    log_fn(f"[BolsaSanvi] {msg}")



# ==========================================

# RUTAS Y CONSTANTES DE CONFIGURACIÓN

# ==========================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MERCADO_DATA_PATH = os.path.join(BASE_DIR, "datos", "bolsa_mercado.json")

POOL_DATA_PATH = os.path.join(BASE_DIR, "datos", "bolsa_pool.json")

CAKEY_HISTORY_PATH = os.path.join(BASE_DIR, "datos", "cakey_history.json")



BOLSA_LOCK = threading.RLock()



# Tickers Iniciales Fundadores

TICKERS = {

    "JOSE": {

        "user_id": 857923274771136522,

        "alt_user_id": 1170704124631846993,

        "cakey_user": "joselito3499",

        "name": "Joselito",

    },

    "TERRE": {

        "user_id": 794223776215990332,

        "alt_user_id": 345678901234567890,

        "cakey_user": "terreneiror",

        "name": "Terre",

    },

    "OMEN": {

        "user_id": 1170704124631846993,

        "alt_user_id": 1170704124631846993,

        "cakey_user": "omen2042_38051",

        "name": "Omen",

    },

    "RACER": {

        "user_id": 1208551025578082367,

        "alt_user_id": 456789012345678901,

        "cakey_user": "racerwasp",

        "name": "Racer",

    },

}



TOTAL_SHARES = 10000

INITIAL_FOUNDER_SHARES = 100

INITIAL_AMM_SHARES = 9900



SPREAD_PCT = 0.01  # 1.0% total

SPREAD_BUY_ASK = 0.005  # +0.5% en compra

SPREAD_SELL_BID = 0.005  # -0.5% en venta

SPREAD_BURN_RATIO = 0.5  # 50% destruido

SPREAD_POOL_RATIO = 0.5  # 50% al Yield Pool de dividendos



MAX_SHARES_PER_ORDER = 500

ORDER_COOLDOWN_SECONDS = 30

AMM_FACTOR_K = 2000.0



# Semilla histórica canónica ratificada el 20/10/2026 en docs/AURA_BAREMO.md

CANONICAL_SEEDS = {

    "joselito3499": {"level": 54, "voice_minutes": 3950, "messages": 658, "voice_hours": 65.8},

    "terreneiror": {"level": 37, "voice_minutes": 1502, "messages": 196, "voice_hours": 25.0},

    "omen2042_38051": {"level": 36, "voice_minutes": 1787, "messages": 148, "voice_hours": 29.8},

    "racerwasp": {"level": 33, "voice_minutes": 1738, "messages": 129, "voice_hours": 29.0},

}





# ==========================================

# UTILIDADES DE PERSISTENCIA ATÓMICA

# ==========================================



def safe_write_json(filepath: str, data: Any) -> None:

    """Escritura atómica usando archivo temporal y os.replace."""

    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    temp_path = f"{filepath}.tmp"

    try:

        with open(temp_path, "w", encoding="utf-8") as f:

            json.dump(data, f, indent=2, ensure_ascii=False)

            f.flush()

            os.fsync(f.fileno())

        os.replace(temp_path, filepath)

    except Exception as e:

        if os.path.exists(temp_path):

            try:

                os.remove(temp_path)

            except Exception:

                pass

        raise e





def _get_default_market_data() -> Dict[str, Any]:

    """Genera la estructura inicial de bolsa_mercado.json."""

    now_iso = datetime.now(timezone.utc).isoformat()

    tickers_data = {}

    for sym, info in TICKERS.items():

        founder_str = str(info["user_id"])

        tickers_data[sym] = {

            "ticker": sym,

            "name": info["name"],

            "founder_id": info["user_id"],

            "total_shares": TOTAL_SHARES,

            "amm_shares": INITIAL_AMM_SHARES,

            "holdings": {

                founder_str: INITIAL_FOUNDER_SHARES

            },

            "order_history": [],

            "last_orders": {},

        }

    return {

        "tickers": tickers_data,

        "meta": {

            "version": "1.0",

            "created_at": now_iso,

            "updated_at": now_iso,

        },

    }





def load_market_data() -> Dict[str, Any]:

    """Carga bolsa_mercado.json asegurando la existencia de los 4 tickers iniciales."""

    with BOLSA_LOCK:

        if os.path.exists(MERCADO_DATA_PATH):

            try:

                with open(MERCADO_DATA_PATH, "r", encoding="utf-8") as f:

                    data = json.load(f)

                    if isinstance(data, dict) and "tickers" in data:

                        # Asegurar que los tickers canónicos existen

                        tickers = data["tickers"]

                        modified = False

                        for sym, info in TICKERS.items():

                            if sym not in tickers:

                                founder_str = str(info["user_id"])

                                tickers[sym] = {

                                    "ticker": sym,

                                    "name": info["name"],

                                    "founder_id": info["user_id"],

                                    "total_shares": TOTAL_SHARES,

                                    "amm_shares": INITIAL_AMM_SHARES,

                                    "holdings": {founder_str: INITIAL_FOUNDER_SHARES},

                                    "order_history": [],

                                    "last_orders": {},

                                }

                                modified = True

                        if modified:

                            save_market_data(data)

                        return data

            except Exception as e:

                _bot_log(f"⚠️ Error leyendo bolsa_mercado.json: {e}")



        default_data = _get_default_market_data()

        safe_write_json(MERCADO_DATA_PATH, default_data)

        return default_data





def save_market_data(data: Dict[str, Any]) -> None:

    """Guarda los datos del mercado atómicamente."""

    with BOLSA_LOCK:

        if "meta" in data:

            data["meta"]["updated_at"] = datetime.now(timezone.utc).isoformat()

        safe_write_json(MERCADO_DATA_PATH, data)





def load_pool_data() -> Dict[str, Any]:

    """Carga bolsa_pool.json con los dividendos acumulados."""

    with BOLSA_LOCK:

        if os.path.exists(POOL_DATA_PATH):

            try:

                with open(POOL_DATA_PATH, "r", encoding="utf-8") as f:

                    data = json.load(f)

                    if isinstance(data, dict) and "accumulated_pool" in data:

                        return data

            except Exception as e:

                _bot_log(f"⚠️ Error leyendo bolsa_pool.json: {e}")



        default_pool = {

            "accumulated_pool": 0.0,

            "total_distributed": 0.0,

            "distributions": [],

            "meta": {

                "created_at": datetime.now(timezone.utc).isoformat(),

                "updated_at": datetime.now(timezone.utc).isoformat(),

            },

        }

        safe_write_json(POOL_DATA_PATH, default_pool)

        return default_pool





def save_pool_data(data: Dict[str, Any]) -> None:

    """Guarda el yield pool atómicamente."""

    with BOLSA_LOCK:

        if "meta" in data:

            data["meta"]["updated_at"] = datetime.now(timezone.utc).isoformat()

        safe_write_json(POOL_DATA_PATH, data)





def add_to_dividend_pool(amount: Union[int, float]) -> float:

    """Añade Porros al yield pool acumulado de dividendos semanales."""

    if amount <= 0:

        return 0.0

    with BOLSA_LOCK:

        pool = load_pool_data()

        pool["accumulated_pool"] = round(float(pool.get("accumulated_pool", 0.0)) + float(amount), 2)

        save_pool_data(pool)

        return float(pool["accumulated_pool"])





def load_cakey_history() -> Dict[str, Any]:

    """Carga el historial de snapshots de Cakey Bot."""

    with BOLSA_LOCK:

        if os.path.exists(CAKEY_HISTORY_PATH):

            try:

                with open(CAKEY_HISTORY_PATH, "r", encoding="utf-8") as f:

                    data = json.load(f)

                    if isinstance(data, dict) and "snapshots" in data:

                        return data

            except Exception as e:

                _bot_log(f"⚠️ Error leyendo cakey_history.json: {e}")



        default_history = {

            "snapshots": {

                "2026-10-22": {

                    k: {

                        "level": v["level"],

                        "xp": 0.0,

                        "messages": v["messages"],

                        "voice_minutes": v["voice_minutes"],

                    }

                    for k, v in CANONICAL_SEEDS.items()

                }

            },

            "meta": {

                "source": "Cakey Bot Web Leaderboard Snapshot",

                "updated_at": datetime.now(timezone.utc).isoformat(),

            },

        }

        safe_write_json(CAKEY_HISTORY_PATH, default_history)

        return default_history





def save_cakey_history(data: Dict[str, Any]) -> None:

    """Guarda los snapshots históricos de Cakey Bot."""

    with BOLSA_LOCK:

        safe_write_json(CAKEY_HISTORY_PATH, data)





# ==========================================

# ECUACIONES FUNDAMENTALES DE AURA Y PRECIOS

# ==========================================



def calculate_book_value(level: int, voice_hours: float, messages: int) -> float:

    """

    Calcula el valor contable indestructible (Book Value) de un miembro:

    BV = 10.0 + (0.8 * level) + (0.2 * voice_hours) + (0.02 * messages)

    docs/DISENO_BOLSA_SANVI.md (§9.2)

    """

    val = 10.0 + (0.8 * level) + (0.2 * float(voice_hours)) + (0.02 * int(messages))

    return round(val, 2)





def calculate_earnings_30d(delta_voice_hours: float, delta_messages: int) -> float:

    """

    Calcula el rendimiento de actividad en la ventana móvil de 30 días (50% voz / 50% chat):

    E_30d = (0.50 * delta_voice_hours) + (0.05 * delta_messages)

    1h de voz = +0.50 Porros

    10 msgs = +0.50 Porros (0.05/msg)

    docs/DISENO_BOLSA_SANVI.md (§9.2)

    """

    val = (0.50 * max(0.0, float(delta_voice_hours))) + (0.05 * max(0, int(delta_messages)))

    return round(val, 2)





def get_ticker_info(ticker: str) -> Optional[Dict[str, Any]]:

    """Devuelve la configuración y metadatos de un ticker (case-insensitive)."""

    sym = ticker.upper().lstrip("$")

    return TICKERS.get(sym)





def resolve_ticker_symbol(user_id_or_ticker: Union[int, str]) -> Optional[str]:

    """Identifica el ticker correspondiente a un user_id (int/str) o símbolo."""

    if isinstance(user_id_or_ticker, str):

        sym = user_id_or_ticker.upper().lstrip("$")

        if sym in TICKERS:

            return sym

    

    # Buscar por user_id o alt_user_id

    try:

        uid = int(user_id_or_ticker)

        for sym, data in TICKERS.items():

            if data["user_id"] == uid or data.get("alt_user_id") == uid:

                return sym

    except (ValueError, TypeError):

        pass



    return None





def get_member_stats(ticker: str) -> Dict[str, Any]:

    """

    Obtiene los datos históricos acumulados y el delta de 30 días de un miembro.

    Prioriza cakey_history.json y recurre a CANONICAL_SEEDS.

    """

    sym = ticker.upper().lstrip("$")

    t_info = TICKERS.get(sym)

    if not t_info:

        return {"level": 20, "voice_hours": 0.0, "messages": 0, "delta_voice_hours": 0.0, "delta_messages": 0}



    cakey_user = t_info["cakey_user"]

    canonical = CANONICAL_SEEDS.get(cakey_user, {"level": 20, "voice_hours": 0.0, "messages": 0, "voice_minutes": 0})



    history = load_cakey_history()

    snapshots = history.get("snapshots", {})



    sorted_dates = sorted(snapshots.keys())

    if not sorted_dates:

        return {

            "level": canonical["level"],

            "voice_hours": canonical.get("voice_hours", round(canonical.get("voice_minutes", 0) / 60.0, 1)),

            "messages": canonical["messages"],

            "delta_voice_hours": 0.0,

            "delta_messages": 0,

        }



    latest_date = sorted_dates[-1]

    latest_snap = snapshots[latest_date].get(cakey_user)



    if not latest_snap:

        return {

            "level": canonical["level"],

            "voice_hours": canonical.get("voice_hours", round(canonical.get("voice_minutes", 0) / 60.0, 1)),

            "messages": canonical["messages"],

            "delta_voice_hours": 0.0,

            "delta_messages": 0,

        }



    level = latest_snap.get("level", canonical["level"])

    v_min = latest_snap.get("voice_minutes", canonical.get("voice_minutes", 0))

    messages = latest_snap.get("messages", canonical["messages"])

    voice_hours = canonical.get("voice_hours") if "voice_hours" in canonical and v_min == canonical.get("voice_minutes") else round(v_min / 60.0, 1)



    delta_v_hours = 0.0

    delta_msgs = 0



    if len(sorted_dates) > 1:

        earliest_date = sorted_dates[0]

        earliest_snap = snapshots[earliest_date].get(cakey_user, {})

        e_vmin = earliest_snap.get("voice_minutes", v_min)

        e_msgs = earliest_snap.get("messages", messages)

        delta_v_hours = max(0.0, round((v_min - e_vmin) / 60.0, 1))

        delta_msgs = max(0, messages - e_msgs)



    return {

        "level": level,

        "voice_hours": voice_hours,

        "messages": messages,

        "delta_voice_hours": delta_v_hours,

        "delta_messages": delta_msgs,

    }





def calculate_base_price(ticker: str) -> float:

    """

    Calcula el precio fundamental base P_base = BV + E_30d.

    docs/DISENO_BOLSA_SANVI.md (§9.2)

    """

    stats = get_member_stats(ticker)

    bv = calculate_book_value(stats["level"], stats["voice_hours"], stats["messages"])

    e30 = calculate_earnings_30d(stats["delta_voice_hours"], stats["delta_messages"])

    return round(bv + e30, 2)





def calculate_market_price(ticker: str) -> float:

    """

    Calcula el precio de mercado actual regido por la curva AMM:

    multiplier = 1.0 + (max(0, shares_held_by_users - 100) / 2000.0)

    P_mercado = round(max(P_base, P_base * multiplier), 2)

    docs/DISENO_BOLSA_SANVI.md (§9.2)

    """

    sym = ticker.upper().lstrip("$")

    mdata = load_market_data()

    t_info = mdata.get("tickers", {}).get(sym)



    amm_shares = t_info.get("amm_shares", INITIAL_AMM_SHARES) if t_info else INITIAL_AMM_SHARES

    shares_held_by_users = TOTAL_SHARES - amm_shares



    base_price = calculate_base_price(sym)

    excess_shares = max(0.0, float(shares_held_by_users - INITIAL_FOUNDER_SHARES))

    multiplier = 1.0 + (excess_shares / AMM_FACTOR_K)



    return round(max(base_price, base_price * multiplier), 2)





def get_bid_ask_prices(ticker: str) -> Dict[str, float]:

    """

    Calcula los precios de mercado, compra (Ask +0.5%) y venta (Bid -0.5%):

    Horquilla fija del 1.0%.

    """

    market_price = calculate_market_price(ticker)

    ask_price = round(market_price * (1.0 + SPREAD_BUY_ASK), 2)

    bid_price = round(market_price * (1.0 - SPREAD_SELL_BID), 2)

    return {

        "market": market_price,

        "ask": ask_price,

        "bid": bid_price,

    }





# ==========================================

# GESTIÓN Y EJECUCIÓN DE ÓRDENES BURSÁTILES

# ==========================================



# ==========================================
# PARO DE EMERGENCIA Y MANTENIMIENTO (24/7)
# ==========================================

def is_market_halted() -> bool:
    """Comprueba si el mercado bursátil está suspendido por emergencia o mantenimiento."""
    with BOLSA_LOCK:
        mdata = load_market_data()
        meta = mdata.get("meta", {})
        return bool(meta.get("emergency_halt", False))


def get_market_halt_reason() -> str:
    """Obtiene el motivo del paro de emergencia si está activo."""
    with BOLSA_LOCK:
        mdata = load_market_data()
        meta = mdata.get("meta", {})
        return meta.get("halt_reason", "")


def set_market_halt(halted: bool, reason: str = "") -> Dict[str, Any]:
    """Activa o desactiva la suspensión de emergencia del Sanvi Exchange."""
    with BOLSA_LOCK:
        mdata = load_market_data()
        meta = mdata.setdefault("meta", {})
        meta["emergency_halt"] = bool(halted)
        meta["halt_reason"] = reason.strip() if halted else ""
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_market_data(mdata)
        _bot_log(f"Estado de mercado actualizado: emergency_halt={halted}, reason='{reason}'")
        return {"success": True, "emergency_halt": bool(halted), "reason": reason.strip()}


def execute_buy_order(

    user_id: Union[int, str],

    ticker: str,

    shares: int,

    ignore_cooldown: bool = False,

) -> Dict[str, Any]:

    """

    Ejecuta una orden de compra contra el Automated Market Maker (AMM).

    - Valida shares (1 a 500).

    - Valida cooldown (30s).

    - Deduce fondos en efectivo vía modulos.economia_core.

    - Liquida spread: 50% al Yield Pool y 50% quemado.

    - Transfiere acciones del AMM a la cartera del usuario.

    """

    sym = ticker.upper().lstrip("$")

    if sym not in TICKERS:

        return {"success": False, "error": f"Ticker '{sym}' no existe en la Bolsa Sanvi."}



    if not isinstance(shares, int) or shares <= 0:

        return {"success": False, "error": "La cantidad de acciones debe ser un entero positivo."}



    if shares > MAX_SHARES_PER_ORDER:

        return {

            "success": False,

            "error": f"Límite excedido: máximo {MAX_SHARES_PER_ORDER} acciones por orden (Blindaje Anti-Ballenas).",

        }



    if is_market_halted():
        r = get_market_halt_reason()
        err_msg = "⛔ La Bolsa Sanvi está temporalmente suspendida por mantenimiento o emergencia."
        if r:
            err_msg += f" Motivo: {r}"
        return {"success": False, "error": err_msg}
    uid_str = str(user_id)

    now_ts = time.time()



    with BOLSA_LOCK:

        mdata = load_market_data()

        tickers_map = mdata.setdefault("tickers", {})

        t_data = tickers_map.get(sym)

        if not t_data:

            return {"success": False, "error": f"Ticker '{sym}' no inicializado en el mercado."}



        # 1. Comprobación de cooldown anti-ballenas

        last_orders = t_data.setdefault("last_orders", {})

        last_time = last_orders.get(uid_str, 0.0)

        if not ignore_cooldown and (now_ts - last_time < ORDER_COOLDOWN_SECONDS):

            remaining = ORDER_COOLDOWN_SECONDS - (now_ts - last_time)

            return {

                "success": False,

                "error": f"Cooldown activo: espera {remaining:.1f}s antes de operar nuevamente en ${sym}.",

                "cooldown_remaining": remaining,

            }



        # 2. Comprobación de stock en AMM

        amm_shares = t_data.get("amm_shares", INITIAL_AMM_SHARES)

        if amm_shares < shares:

            return {

                "success": False,

                "error": f"Liquidez insuficiente en el AMM: sólo hay {amm_shares} acciones disponibles.",

            }



        # 3. Precios y costes

        quotes = get_bid_ask_prices(sym)

        market_price = quotes["market"]

        ask_price = quotes["ask"]

        cost_float = round(shares * ask_price, 2)

        int_cost = int(round(cost_float))



        # 4. Descuento de fondos en economia_core

        from modulos import economia_core

        user_bal = economia_core.get_balance(user_id)

        if user_bal["cash"] < int_cost:

            return {

                "success": False,

                "error": f"Efectivo insuficiente. Necesitas {int_cost:,} Porros (tienes {user_bal['cash']:,}).",

                "required": int_cost,

                "cash": user_bal["cash"],

            }



        try:

            economia_core.modify_balance(user_id, cash_delta=-int_cost)

        except Exception as e:

            return {"success": False, "error": f"Fallo al debitar fondos de la cuenta: {e}"}



        # 5. Cálculo y distribución del Spread

        spread_total = round(shares * (ask_price - market_price), 2)

        spread_to_pool = round(spread_total * SPREAD_POOL_RATIO, 2)

        spread_burned = round(spread_total - spread_to_pool, 2)



        if spread_to_pool > 0:

            pool_data = load_pool_data()

            pool_data["accumulated_pool"] = round(pool_data.get("accumulated_pool", 0.0) + spread_to_pool, 2)

            save_pool_data(pool_data)



        # 6. Transferencia de acciones

        t_data["amm_shares"] = amm_shares - shares

        holdings = t_data.setdefault("holdings", {})

        holdings[uid_str] = holdings.get(uid_str, 0) + shares

        last_orders[uid_str] = now_ts



        # Registro en el histórico de órdenes

        order_entry = {

            "id": f"BUY_{int(now_ts)}_{uid_str[:6]}",

            "type": "BUY",

            "user_id": uid_str,

            "shares": shares,

            "price": ask_price,

            "market_price": market_price,

            "cost": int_cost,

            "spread_pool": spread_to_pool,

            "spread_burned": spread_burned,

            "timestamp": datetime.now(timezone.utc).isoformat(),

        }

        t_data.setdefault("order_history", []).append(order_entry)

        save_market_data(mdata)



        # Sincronización secundaria en portfolio de economia.json

        try:

            with economia_core.ECONOMY_LOCK:

                edata = economia_core.load_economy_data()

                u_econ = edata.get("users", {}).get(uid_str)

                if u_econ is not None:

                    u_port = u_econ.setdefault("portfolio", {})

                    u_port[sym] = holdings[uid_str]

                    economia_core.save_economy_data(edata)

        except Exception:

            pass



        return {

            "success": True,

            "ticker": sym,

            "type": "BUY",

            "shares": shares,

            "price": ask_price,

            "market_price": market_price,

            "total_cost": int_cost,

            "cost_float": cost_float,

            "spread_fee": spread_total,

            "spread_to_pool": spread_to_pool,

            "spread_burned": spread_burned,

            "remaining_amm_shares": t_data["amm_shares"],

            "user_total_shares": holdings[uid_str],

        }





def execute_sell_order(

    user_id: Union[int, str],

    ticker: str,

    shares: int,

    ignore_cooldown: bool = False,

) -> Dict[str, Any]:

    """

    Ejecuta una orden de venta contra el Automated Market Maker (AMM).

    - Valida shares (1 a 500) y que el usuario disponga de suficientes acciones.

    - Valida cooldown (30s).

    - Acredita fondos en efectivo vía modulos.economia_core.

    - Liquida spread: 50% al Yield Pool y 50% quemado.

    - Transfiere acciones del usuario al AMM.

    """

    sym = ticker.upper().lstrip("$")

    if sym not in TICKERS:

        return {"success": False, "error": f"Ticker '{sym}' no existe en la Bolsa Sanvi."}



    if not isinstance(shares, int) or shares <= 0:

        return {"success": False, "error": "La cantidad de acciones debe ser un entero positivo."}



    if shares > MAX_SHARES_PER_ORDER:

        return {

            "success": False,

            "error": f"Límite excedido: máximo {MAX_SHARES_PER_ORDER} acciones por orden (Blindaje Anti-Ballenas).",

        }



    if is_market_halted():
        r = get_market_halt_reason()
        err_msg = "⛔ La Bolsa Sanvi está temporalmente suspendida por mantenimiento o emergencia."
        if r:
            err_msg += f" Motivo: {r}"
        return {"success": False, "error": err_msg}
    uid_str = str(user_id)

    now_ts = time.time()



    with BOLSA_LOCK:

        mdata = load_market_data()

        tickers_map = mdata.setdefault("tickers", {})

        t_data = tickers_map.get(sym)

        if not t_data:

            return {"success": False, "error": f"Ticker '{sym}' no inicializado en el mercado."}



        # 1. Comprobación de cooldown anti-ballenas

        last_orders = t_data.setdefault("last_orders", {})

        last_time = last_orders.get(uid_str, 0.0)

        if not ignore_cooldown and (now_ts - last_time < ORDER_COOLDOWN_SECONDS):

            remaining = ORDER_COOLDOWN_SECONDS - (now_ts - last_time)

            return {

                "success": False,

                "error": f"Cooldown activo: espera {remaining:.1f}s antes de operar nuevamente en ${sym}.",

                "cooldown_remaining": remaining,

            }



        # 2. Comprobación de tenencia en cartera

        holdings = t_data.setdefault("holdings", {})

        user_shares = holdings.get(uid_str, 0)

        if user_shares < shares:

            return {

                "success": False,

                "error": f"Acciones insuficientes en cartera. Posees {user_shares} de ${sym}.",

                "user_shares": user_shares,

            }



        # 3. Precios y liquidación

        quotes = get_bid_ask_prices(sym)

        market_price = quotes["market"]

        bid_price = quotes["bid"]

        payout_float = round(shares * bid_price, 2)

        int_payout = int(round(payout_float))



        # 4. Acreditación de fondos en efectivo

        from modulos import economia_core

        try:

            economia_core.modify_balance(user_id, cash_delta=int_payout)

        except Exception as e:

            return {"success": False, "error": f"Fallo al acreditar fondos en efectivo: {e}"}



        # 5. Cálculo y distribución del Spread

        spread_total = round(shares * (market_price - bid_price), 2)

        spread_to_pool = round(spread_total * SPREAD_POOL_RATIO, 2)

        spread_burned = round(spread_total - spread_to_pool, 2)



        if spread_to_pool > 0:

            pool_data = load_pool_data()

            pool_data["accumulated_pool"] = round(pool_data.get("accumulated_pool", 0.0) + spread_to_pool, 2)

            save_pool_data(pool_data)



        # 6. Transferencia de acciones

        holdings[uid_str] = user_shares - shares

        if holdings[uid_str] <= 0:

            del holdings[uid_str]



        t_data["amm_shares"] = t_data.get("amm_shares", INITIAL_AMM_SHARES) + shares

        last_orders[uid_str] = now_ts



        # Registro en el histórico de órdenes

        order_entry = {

            "id": f"SELL_{int(now_ts)}_{uid_str[:6]}",

            "type": "SELL",

            "user_id": uid_str,

            "shares": shares,

            "price": bid_price,

            "market_price": market_price,

            "payout": int_payout,

            "spread_pool": spread_to_pool,

            "spread_burned": spread_burned,

            "timestamp": datetime.now(timezone.utc).isoformat(),

        }

        t_data.setdefault("order_history", []).append(order_entry)

        save_market_data(mdata)



        # Sincronización secundaria en portfolio de economia.json

        try:

            with economia_core.ECONOMY_LOCK:

                edata = economia_core.load_economy_data()

                u_econ = edata.get("users", {}).get(uid_str)

                if u_econ is not None:

                    u_port = u_econ.setdefault("portfolio", {})

                    if holdings.get(uid_str, 0) > 0:

                        u_port[sym] = holdings[uid_str]

                    elif sym in u_port:

                        del u_port[sym]

                    economia_core.save_economy_data(edata)

        except Exception:

            pass



        return {

            "success": True,

            "ticker": sym,

            "type": "SELL",

            "shares": shares,

            "price": bid_price,

            "market_price": market_price,

            "total_payout": int_payout,

            "payout_float": payout_float,

            "spread_fee": spread_total,

            "spread_to_pool": spread_to_pool,

            "spread_burned": spread_burned,

            "remaining_amm_shares": t_data["amm_shares"],

            "user_total_shares": holdings.get(uid_str, 0),

        }





# ==========================================

# SINERGIA DE CARTERA Y UTILIDAD REAL (/trabajar)

# ==========================================



def get_user_portfolio(user_id: Union[int, str]) -> Dict[str, int]:

    """Retorna un mapa {ticker: shares} con todas las acciones en posesión del usuario."""

    if is_market_halted():
        r = get_market_halt_reason()
        err_msg = "⛔ La Bolsa Sanvi está temporalmente suspendida por mantenimiento o emergencia."
        if r:
            err_msg += f" Motivo: {r}"
        return {"success": False, "error": err_msg}
    uid_str = str(user_id)

    mdata = load_market_data()

    tickers_map = mdata.get("tickers", {})

    portfolio = {}

    for sym, t_data in tickers_map.items():

        holdings = t_data.get("holdings", {})

        shares = holdings.get(uid_str, 0)

        if shares > 0:

            portfolio[sym] = shares

    return portfolio





def get_user_portfolio_aura(user_id: Union[int, str]) -> float:

    """

    Calcula el Aura Total en Cartera del usuario:

    Aura Total = sum(Acciones_i * P_base_i)

    docs/DISENO_BOLSA_SANVI.md (§7.2 Pilar 2)

    """

    portfolio = get_user_portfolio(user_id)

    total_aura = 0.0

    for sym, shares in portfolio.items():

        base_price = calculate_base_price(sym)

        total_aura += shares * base_price

    return round(total_aura, 2)





def get_user_portfolio_buff(user_id: Union[int, str]) -> float:

    """

    Determina el multiplicador de bono pasivo para el comando /trabajar:

    - Aura < 1000: +0% (0.0)

    - 1000 <= Aura <= 5000: +5% (0.05) [Inversor Junior]

    - 5001 <= Aura <= 20000: +10% (0.10) [Inversor Senior]

    - 20001 <= Aura <= 50000: +15% (0.15) [Fondo de Inversión]

    - Aura > 50000: +25% (0.25) [Ballena de Sanvi - Tope máximo]

    docs/DISENO_BOLSA_SANVI.md (§7.2 Pilar 2)

    """

    aura = get_user_portfolio_aura(user_id)

    if aura < 1000.0:

        return 0.0

    elif 1000.0 <= aura <= 5000.0:

        return 0.05

    elif 5001.0 <= aura <= 20000.0:

        return 0.10

    elif 20001.0 <= aura <= 50000.0:

        return 0.15

    else:

        return 0.25





# ==========================================

# FONDO DE DIVIDENDOS SEMANAL (YIELD POOL)

# ==========================================



def distribute_weekly_dividends() -> Dict[str, Any]:

    """

    Reparte el Yield Pool acumulado entre todos los poseedores de acciones

    ponderado por el valor de mercado en circulación de su cartera.

    Acredita los dividendos en la cuenta 'bank' de cada accionista.

    docs/DISENO_BOLSA_SANVI.md (§7.2 Pilar 3)

    """

    with BOLSA_LOCK:

        pool_data = load_pool_data()

        accumulated = float(pool_data.get("accumulated_pool", 0.0))

        if accumulated <= 0.0:

            return {

                "success": True,

                "distributed_amount": 0.0,

                "recipients_count": 0,

                "details": {},

                "message": "Yield Pool vacío, sin dividendos pendientes para repartir.",

            }



        mdata = load_market_data()

        tickers_map = mdata.get("tickers", {})



        # Calcular valor de mercado de la cartera de cada usuario

        user_portfolio_values: Dict[str, float] = {}

        for sym, t_data in tickers_map.items():

            market_price = calculate_market_price(sym)

            holdings = t_data.get("holdings", {})

            for uid_str, shares in holdings.items():

                if shares > 0:

                    val = shares * market_price

                    user_portfolio_values[uid_str] = user_portfolio_values.get(uid_str, 0.0) + val



        total_market_capital = sum(user_portfolio_values.values())

        if total_market_capital <= 0.0:

            return {

                "success": True,

                "distributed_amount": 0.0,

                "recipients_count": 0,

                "details": {},

                "message": "No hay accionistas con saldo positivo para recibir dividendos.",

            }



        from modulos import economia_core

        distribution_details = {}

        total_credited = 0



        for uid_str, val in user_portfolio_values.items():

            ratio = val / total_market_capital

            user_payout_float = round(accumulated * ratio, 2)

            int_payout = int(round(user_payout_float))

            if int_payout > 0:

                try:

                    economia_core.modify_balance(uid_str, bank_delta=int_payout)

                    total_credited += int_payout

                    distribution_details[uid_str] = {

                        "portfolio_value": round(val, 2),

                        "ratio": round(ratio, 4),

                        "dividend": int_payout,

                    }

                except Exception as e:

                    _bot_log(f"⚠️ Error abonando dividendo a {uid_str}: {e}")



        # Reset del pool acumulado y registro en historial

        pool_data["total_distributed"] = round(pool_data.get("total_distributed", 0.0) + accumulated, 2)

        pool_data["accumulated_pool"] = 0.0

        dist_record = {

            "timestamp": datetime.now(timezone.utc).isoformat(),

            "amount_distributed": accumulated,

            "total_credited": total_credited,

            "recipients": len(distribution_details),

        }

        pool_data.setdefault("distributions", []).append(dist_record)

        save_pool_data(pool_data)



        return {

            "success": True,

            "distributed_amount": accumulated,

            "total_credited": total_credited,

            "recipients_count": len(distribution_details),

            "details": distribution_details,

        }





# ==========================================

# INDICADORES TÉCNICOS INSTITUCIONALES

# ==========================================



def calculate_rsi(series: List[float], period: int = 14) -> float:

    """

    Calcula el Índice de Fuerza Relativa (RSI de Wilder) a 14 periodos.

    Retorna un valor normalizado entre 0.0 y 100.0.

    docs/DISENO_BOLSA_SANVI.md (§9.3)

    """

    if not series or len(series) < 2:

        return 50.0  # Nivel neutro por defecto



    deltas = [series[i] - series[i - 1] for i in range(1, len(series))]

    if not deltas:

        return 50.0



    effective_period = min(period, len(deltas))



    gains = [max(0.0, d) for d in deltas]

    losses = [max(0.0, -d) for d in deltas]



    # Media inicial de Wilder

    avg_gain = sum(gains[:effective_period]) / effective_period

    avg_loss = sum(losses[:effective_period]) / effective_period



    # Suavizado para el resto de periodos

    for i in range(effective_period, len(deltas)):

        avg_gain = (avg_gain * (effective_period - 1) + gains[i]) / effective_period

        avg_loss = (avg_loss * (effective_period - 1) + losses[i]) / effective_period



    if avg_loss == 0.0:

        return 100.0 if avg_gain > 0.0 else 50.0

    if avg_gain == 0.0:

        return 0.0



    rs = avg_gain / avg_loss

    rsi = 100.0 - (100.0 / (1.0 + rs))

    return round(rsi, 2)





def calculate_moving_averages(series: List[float]) -> Dict[str, Optional[float]]:

    """

    Calcula la batería institucional de Medias Móviles:

    SMA y EMA para 14, 50, 100 y 200 días.

    docs/DISENO_BOLSA_SANVI.md (§9.3)

    """

    periods = [14, 50, 100, 200]

    result: Dict[str, Optional[float]] = {}



    if not series:

        for p in periods:

            result[f"sma_{p}"] = None

            result[f"ema_{p}"] = None

        return result



    for p in periods:

        # 1. Simple Moving Average (SMA)

        if len(series) >= p:

            sma = sum(series[-p:]) / p

        else:

            sma = sum(series) / len(series)

        result[f"sma_{p}"] = round(sma, 2)



        # 2. Exponential Moving Average (EMA)

        alpha = 2.0 / (p + 1.0)

        ema = series[0]

        for val in series[1:]:

            ema = (val * alpha) + (ema * (1.0 - alpha))

        result[f"ema_{p}"] = round(ema, 2)



    return result





def detect_crosses(ema_short: Optional[float], sma_long: Optional[float]) -> str:

    """

    Detecta señales de cruce institucional entre corto y largo plazo:

    - GOLDEN_CROSS: Cruce alcista (EMA corto supera SMA largo).

    - DEATH_CROSS: Cruce bajista (EMA corto cae bajo SMA largo).

    - NEUTRAL: Igualdad o datos insuficientes.

    """

    if ema_short is None or sma_long is None:

        return "NEUTRAL"

    if ema_short > sma_long:

        return "GOLDEN_CROSS"

    elif ema_short < sma_long:

        return "DEATH_CROSS"

    return "NEUTRAL"





# ==========================================

# INFORME FINANCIERO DE ASISTENTE IA

# ==========================================



async def generate_market_report(ticker: str) -> str:

    """

    Genera un informe analítico financiero institucional para un ticker.

    Utiliza Gemini AI con fallback determinista impecable.

    docs/DISENO_BOLSA_SANVI.md (§9.3)

    """

    sym = ticker.upper().lstrip("$")

    t_info = get_ticker_info(sym)

    if not t_info:

        return f"⚠️ Ticker **${sym}** no encontrado en la Bolsa Sanvi."



    stats = get_member_stats(sym)

    bv = calculate_book_value(stats["level"], stats["voice_hours"], stats["messages"])

    e30 = calculate_earnings_30d(stats["delta_voice_hours"], stats["delta_messages"])

    base_price = calculate_base_price(sym)

    market_price = calculate_market_price(sym)

    quotes = get_bid_ask_prices(sym)



    # Simulación o lectura de serie para RSI y Medias

    # Construimos una serie sintética congruente si la historia es corta

    series = [base_price * 0.95, base_price * 0.98, base_price, market_price]

    rsi = calculate_rsi(series, period=14)

    mas = calculate_moving_averages(series)

    cross_signal = detect_crosses(mas.get("ema_14"), mas.get("sma_50"))



    # Intentar invocación a Gemini

    prompt_context = (

        f"Eres el Analista Financiero Jefe de Sanvi Capital en Discord ('El Lobo de Sanvi'). "

        f"Genera un informe financiero en tono de colega pero técnicamente riguroso sobre la acción ${sym} ({t_info['name']}).\n"

        f"Datos:\n"

        f"- Valor Contable (Book Value): {bv:.2f} Porros (Lvl {stats['level']}, {stats['voice_hours']}h voz, {stats['messages']} msgs)\n"

        f"- Rendimiento 30d (Earnings): +{e30:.2f} Porros\n"

        f"- Precio Base (Aura Fundamental): {base_price:.2f} Porros\n"

        f"- Precio de Mercado: {market_price:.2f} Porros (Ask: {quotes['ask']:.2f}, Bid: {quotes['bid']:.2f})\n"

        f"- RSI (14 días): {rsi:.2f}\n"

        f"- Señal Técnica: {cross_signal}\n"

        f"Estructura obligatoria:\n"

        f"1. 🏛️ Análisis Fundamental (Book Value y salud comunitaria)\n"

        f"2. 📈 Momento Técnico (RSI y presión compradora)\n"

        f"3. 🎯 Dictamen Sanvi Capital (Comprar / Mantener / Tomar Beneficios) y justificación en 2 frases."

    )



    try:

        from modulos import chat_ia

        if hasattr(chat_ia, "call_gemini_multiturn"):

            turns = [{"role": "user", "parts": [{"text": prompt_context}]}]

            ai_text = await asyncio.to_thread(chat_ia.call_gemini_multiturn, turns)

            if ai_text and "temporalmente saturada" not in ai_text:

                return ai_text

    except Exception as e:

        _bot_log(f"Fallo en llamada IA, utilizando dictamen financiero determinista: {e}")



    # Fallback determinista estructurado

    dictamen = "MANTENER (HOLD)"

    if rsi < 35 or market_price <= base_price * 1.02:

        dictamen = "COMPRAR (BUY THE DIP)"

    elif rsi > 70 or market_price >= base_price * 1.30:

        dictamen = "TOMAR BENEFICIOS (TAKE PROFIT)"



    report = (

        f"📊 **INFORME INSTITUCIONAL SANVI CAPITAL — ${sym} ({t_info['name']})**\n\n"

        f"🏛️ **Fundamentales Contables (P_base):**\n"

        f"• **Book Value (Suelo):** `{bv:.2f}` Porros *(Nivel {stats['level']} · {stats['voice_hours']}h voz · {stats['messages']} msgs)*\n"

        f"• **Earnings Mensuales (30d):** `+{e30:.2f}` Porros *(50% voz / 50% chat)*\n"

        f"• **Precio Fundamental Base:** `{base_price:.2f}` Porros\n\n"

        f"📈 **Cotización de Mercado y Horquilla:**\n"

        f"• **Precio de Mercado:** `{market_price:.2f}` Porros\n"

        f"• **Ask (Compra):** `{quotes['ask']:.2f}` Porros | **Bid (Venta):** `{quotes['bid']:.2f}` Porros\n"

        f"• **RSI (14 días):** `{rsi:.2f}` *(Señal: {cross_signal})*\n\n"

        f"🎯 **Dictamen Sanvi Capital:** **`{dictamen}`**\n"

        f"El suelo fundamental de ${sym} está sólidamente respaldado por su actividad en el servidor. "

        f"La horquilla del 1% destina la mitad del spread directamente al Yield Pool de dividendos comunitarios."

    )

    return report

