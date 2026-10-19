"""
Módulo de Economía Nativa y Minijuego de Tragaperras 5x3 de Alta Tensión para 'Asistente':
- Moneda oficial: Porros (<:Porro:1535685303317172305>).
- Almacenamiento seguro y atómico en 'datos/economia.json' con thread-safety (RLock).
- Gestión de saldos: get_balance, modify_balance, transfer_funds.
- Sistema de Banca: deposit_cash, withdraw_cash (con soporte para cantidades numéricas o "all").
- Sistema de Robo: execute_rob (50% éxito, 20-50% robo, chequeo de '🛡️ Cartera Blindada' y multas).
- Catálogo de Tienda V2: 9 artículos con compra y auto-asignación de roles en Discord.
- Salario Acumulativo: claim_salary con decaimiento diario del 5% (fórmula P = S * (1 - (1-d)^n)/d, asíntota 20*S).
- Sistema de trabajo (/trabajar): retribución balanceada y textos cómicos del servidor con cooldown de 2 horas.
- Máquina tragaperras 5x3 (/slots):
  * Matriz 5x3 (15 casilleros) y 8 símbolos: 6 Brawl Stars Ranked, WILD (<:absolutecinema:1478115607336714300>) y SCATTER (<:Porro:1535685303317172305>).
  * 7 Líneas de Pago Limpias evaluadas con Opción B (consecutivos en cualquier posición: 3, 4 y 5 aciertos).
  * Pantalla Completa (15 casilleros a x500.0).
  * Ronda de Free Spins escalonada (3/4/5 Scatters -> 5/8/12 giros a x2 con re-triggers).
  * Bote Progresivo Escalonado: Grand Jackpot (100% bote) y Mini Jackpot (25% bote) en L1.
  * Calibración Monte Carlo a RTP 110.0% (+/- 0.5%) y Hit Rate ~73.8%.
  * Componentes Discord V2: Container (tipo 17), Separator (tipo 14), TextDisplay (tipo 10) y ActionRow (tipo 1).
"""

import os
import sys
import json
import math
import random
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Union

import discord
from discord.enums import SeparatorSpacing
from discord.ui import LayoutView, Container, Separator, TextDisplay, ActionRow, Button


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


def _bot_log(msg: str):
    bs = _bs()
    log_fn = getattr(bs, "bot_log", print)
    log_fn(msg)


# ==========================================
# RUTAS Y CONSTANTES DE CONFIGURACIÓN
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECONOMY_DATA_PATH = os.path.join(BASE_DIR, "datos", "economia.json")

PORRO_EMOJI = "<:Porro:1535685303317172305>"
DEFAULT_STARTING_CASH = 1000
DEFAULT_STARTING_BANK = 0
DEFAULT_JACKPOT = 25000
JACKPOT_FEED_PERCENT = 0.03  # 3% de pérdidas netas alimenta el bote del servidor

ECONOMY_LOCK = threading.RLock()

# Símbolos oficiales de Tragaperras 5x3: 6 Brawl Stars Ranked + WILD + SCATTER
# Suma de pesos = 38 + 24 + 15 + 9 + 5 + 3 + 2 + 4 = 100
# Calibrado a RTP 110.0% (+/- 0.5%) y Hit Rate ~73.8% con Opción B (3 y 4 consecutivos en cualquier posición)
SLOT_SYMBOLS = {
    "Gold": {
        "id": "1550130006896812084",
        "emoji": "<:Ranked_Gold:1550130006896812084>",
        "name": "Ranked_Gold",
        "mults": {3: 0.19, 4: 0.58, 5: 1.95},
        "weight": 38,
    },
    "Diamond": {
        "id": "1550130004074041434",
        "emoji": "<:Ranked_Diamond:1550130004074041434>",
        "name": "Ranked_Diamond",
        "mults": {3: 0.37, 4: 1.20, 5: 3.80},
        "weight": 24,
    },
    "Mythic": {
        "id": "1550130000852820099",
        "emoji": "<:Ranked_Mythic:1550130000852820099>",
        "name": "Ranked_Mythic",
        "mults": {3: 0.78, 4: 2.70, 5: 8.90},
        "weight": 15,
    },
    "Legendary": {
        "id": "1550129997774323732",
        "emoji": "<:Ranked_Legendary:1550129997774323732>",
        "name": "Ranked_Legendary",
        "mults": {3: 1.65, 4: 5.80, 5: 18.80},
        "weight": 9,
    },
    "Masters": {
        "id": "1550129992837496833",
        "emoji": "<:Ranked_Masters:1550129992837496833>",
        "name": "Ranked_Masters",
        "mults": {3: 4.70, 4: 15.0, 5: 46.50},
        "weight": 5,
    },
    "Pro": {
        "id": "1550129987972104252",
        "emoji": "<:Ranked_Pro:1550129987972104252>",
        "name": "Ranked_Pro",
        "mults": {3: 11.60, 4: 37.5, 5: 122.0},
        "weight": 3,
    },
    "Wild": {
        "id": "1478115607336714300",
        "emoji": "<:absolutecinema:1478115607336714300>",
        "name": "WILD",
        "mults": {3: 15.0, 4: 49.0, 5: 152.0},
        "weight": 2,
    },
    "Scatter": {
        "id": "1535685303317172305",
        "emoji": "<:Porro:1535685303317172305>",
        "name": "SCATTER",
        "mults": {3: 4.0, 4: 13.0, 5: 48.0},
        "weight": 4,
    },
}

# Las 7 Líneas de pago definitivas aprobadas por Jose en matriz 5x3 (evaluadas de izquierda a derecha)
SLOT_PAYLINES = [
    ("L1: Centro", [(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)]),
    ("L2: Arriba", [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]),
    ("L3: Abajo", [(2, 0), (2, 1), (2, 2), (2, 3), (2, 4)]),
    ("L4: V Suave", [(0, 0), (1, 1), (2, 2), (1, 3), (0, 4)]),
    ("L5: V Invertida", [(2, 0), (1, 1), (0, 2), (1, 3), (2, 4)]),
    ("L6: Diagonal Descendente", [(0, 0), (0, 1), (1, 2), (2, 3), (2, 4)]),
    ("L7: Diagonal Ascendente", [(2, 0), (2, 1), (1, 2), (0, 3), (0, 4)]),
]

# Textos cómicos y temáticos de trabajo vinculados a la vida y lore del servidor
WORK_MESSAGES = [
    "Ayudaste a Iván a redactar una sentencia absolutoria en El Tribunal Gaming por falta de pruebas y contradicción de testigos.",
    "Le explicaste a Joselito por qué el último capítulo de su manhwa favorito es cine absoluto y merecía un 10 rotundo.",
    "Hiciste de árbitro en una partida competitiva de Brawl Stars y lograste que nadie estampara el móvil contra la pared.",
    "Organizaste el cableado de una torre AM5 sin doblar ni un solo pin del Ryzen 7600X ni romper el cristal templado.",
    "Convenciste a la peña de no quemar todos sus Porros en la tragaperras (aunque luego fuiste tú de cabeza).",
    "Filtreaste las ofertas de las rebajas de Steam y salvaste a un colega de comprar un juego multijugador abandonado en 2021.",
    "Soltaste un meme en #risas-y-memes tan oportuno que te otorgó +1.000 de aura instantáneo en la comunidad.",
    "Aguantaste de guardia en el canal de voz hasta las 4 AM debatiendo si una GPU de 8GB sigue teniendo futuro.",
    "Cubriste la retaguardia de la escuadra en Helldivers 2 y conseguisteis extraer con todas las muestras intactas.",
    "Jugaste contra Stockfish en nivel 1, ganaste por la mínima y te hiciste pasar por Gran Maestro internacional.",
    "Encontraste un bug en un script de Python antes de subirlo a producción en Render y te ganaste el respeto del clúster.",
    "Moderaste una discusión sobre si el doblaje de anime en japonés es superior y saliste ileso sin ningún baneo.",
    "Hiciste de copiloto en un simulador de carreras y avisaste de una curva cerrada 0.2 segundos antes de la tragedia.",
    "Revisaste los logs del servidor a medianoche y confirmaste que todos los contenedores seguían en verde.",
    "Compartiste tu playlist secreta en el canal de música y la peña admitió con resignación que tenías buen gusto.",
]

# Catálogo Oficial de la Tienda (9 Ítems)
SHOP_ITEMS: Dict[str, Dict[str, Any]] = {
    "cartera_blindada": {
        "id": "cartera_blindada",
        "name": "🛡️ Cartera Blindada",
        "price": 50000,
        "type": "role",
        "role_id": "1549520453926912062",
        "role_name": "🛡️ Cartera Blindada",
        "description": "Otorga inmunidad total contra el comando /robar. Si alguien intenta robarte, el atraco falla al 100% y te paga una multa del 15%.",
        "unique": True,
    },
    "porro_oro": {
        "id": "porro_oro",
        "name": "🚬 Porro de Oro",
        "price": 75000,
        "type": "item",
        "description": "Coleccionable de inventario de máximo prestigio y flexeo. Demuestra quién manda en la economía.",
        "unique": False,
    },
    "camello_barrio": {
        "id": "camello_barrio",
        "name": "🚬 Camello del Barrio",
        "price": 85000,
        "type": "role",
        "role_id": "1549805021153984617",
        "role_name": "🚬 Camello del Barrio",
        "description": "Rol cosmético exclusivo de Discord en verde porro (#2ECC71).",
        "unique": True,
    },
    "ludopata_rehabilitado": {
        "id": "ludopata_rehabilitado",
        "name": "🎰 Ludópata Rehabilitado",
        "price": 40000,
        "type": "role",
        "role_id": "1549805313920864429",
        "role_name": "🎰 Ludópata Rehabilitado",
        "description": "Rol cosmético exclusivo de Discord en rojo casino (#E74C3C).",
        "unique": True,
    },
    "pollo_pelea": {
        "id": "pollo_pelea",
        "name": "🍗 Pollo de Pelea Dopado",
        "price": 25000,
        "type": "item",
        "description": "Ítem de inventario de combate para duelos de cockfight y apuestas clandestinas.",
        "unique": False,
    },
    "chute_xp": {
        "id": "chute_xp",
        "name": "⚡ Chute de XP (24h)",
        "price": 15000,
        "type": "role",
        "role_id": "1549880939205623972",
        "role_name": "⚡ Chute de XP (24h)",
        "duration_hours": 24,
        "description": "Pase temporal con boost de +5% de XP en Cakey Bot durante 24 horas.",
        "unique": True,
    },
    "pase_semanal_xp": {
        "id": "pase_semanal_xp",
        "name": "🔥 Pase Semanal de XP",
        "price": 75000,
        "type": "role",
        "role_id": "1549880941466357940",
        "role_name": "🔥 Pase Semanal de XP",
        "duration_hours": 168,
        "description": "Pase temporal con boost de +10% de XP en Cakey Bot durante 7 días.",
        "unique": True,
    },
    "pase_mensual_xp": {
        "id": "pase_mensual_xp",
        "name": "💠 Pase Mensual de XP",
        "price": 250000,
        "type": "role",
        "role_id": "1549880942909329539",
        "role_name": "💠 Pase Mensual de XP",
        "duration_hours": 720,
        "description": "Pase temporal con boost de +15% de XP en Cakey Bot durante 30 días.",
        "unique": True,
    },
    "aura_xp": {
        "id": "aura_xp",
        "name": "👑 Aura de XP Permanente",
        "price": 1000000,
        "type": "role",
        "role_id": "1549880944490582106",
        "role_name": "👑 Aura de XP Permanente",
        "description": "Pase perpetuo de máxima élite con boost de +10% de XP permanente e inmarchitable.",
        "unique": True,
    },
}

# Tabla de Salarios Diarios Base por Rol de Nivel y Podio (UnbelievaBoat Role Income)
ROLE_SALARIES = {
    # Niveles
    "10": {"name": "Pendejo de Rango Medio", "daily": 2000, "kw": ["rango medio"]},
    "20": {"name": "Pendejo Veterano", "daily": 2000, "kw": ["veterano"]},
    "30": {"name": "Pendejo Experimentado", "daily": 3000, "kw": ["experimentado"]},
    "40": {"name": "Pendejo de Alto Rango", "daily": 4500, "kw": ["alto rango"]},
    "50": {"name": "Pendejo de Élite", "daily": 6500, "kw": ["élite", "elite"]},
    "60": {"name": "Pendejo Maestro", "daily": 10000, "kw": ["maestro"]},
    "70": {"name": "Pendejo Legendario", "daily": 14000, "kw": ["legendario"]},
    "80": {"name": "Pendejo Mítico", "daily": 20000, "kw": ["mítico", "mitico"]},
    "90": {"name": "Pendejo Ancestral", "daily": 28000, "kw": ["ancestral"]},
    "100": {"name": "Pendejo Supremo", "daily": 40000, "kw": ["supremo"]},
    # Podio
    "top3": {"name": "Top 3", "daily": 3000, "kw": ["top 3", "top3"]},
    "top2": {"name": "Top 2", "daily": 5000, "kw": ["top 2", "top2"]},
    "top1": {"name": "Top 1", "daily": 8000, "kw": ["top 1", "top1"]},
}
DEFAULT_BASE_SALARY = 1000  # Salario diario base para novatos sin rol


# ==========================================
# PERSISTENCIA Y ESCRITURA ATÓMICA
# ==========================================

_ECONOMY_CACHE: Optional[Dict[str, Any]] = None


def _get_default_structure() -> Dict[str, Any]:
    return {
        "users": {},
        "server_jackpot": DEFAULT_JACKPOT,
        "meta": {
            "currency_name": "Porro",
            "currency_emoji": PORRO_EMOJI,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "version": "2.0",
        },
    }


def safe_write_json(file_path: str, data: Dict[str, Any]) -> None:
    """Escribe a un archivo temporal y reemplaza atómicamente para prevenir corrupción."""
    dir_name = os.path.dirname(file_path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    tmp_path = f"{file_path}.tmp.{os.getpid()}_{threading.get_ident()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def load_economy_data(force_reload: bool = False) -> Dict[str, Any]:
    """Carga los datos de economía desde disco con caché y fallback a estructura por defecto."""
    global _ECONOMY_CACHE
    with ECONOMY_LOCK:
        if _ECONOMY_CACHE is not None and not force_reload:
            return _ECONOMY_CACHE

        if os.path.exists(ECONOMY_DATA_PATH):
            try:
                with open(ECONOMY_DATA_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "users" in data:
                        if "server_jackpot" not in data:
                            data["server_jackpot"] = DEFAULT_JACKPOT
                        _ECONOMY_CACHE = data
                        return _ECONOMY_CACHE
            except Exception as e:
                _bot_log(f"⚠️ Error cargando economia.json: {e}. Creando estructura fresca.")

        default_data = _get_default_structure()
        safe_write_json(ECONOMY_DATA_PATH, default_data)
        _ECONOMY_CACHE = default_data
        return _ECONOMY_CACHE


def save_economy_data(data: Optional[Dict[str, Any]] = None) -> None:
    """Guarda los datos en caché atómicamente a disco."""
    global _ECONOMY_CACHE
    with ECONOMY_LOCK:
        if data is not None:
            _ECONOMY_CACHE = data
        if _ECONOMY_CACHE is None:
            _ECONOMY_CACHE = load_economy_data()
        safe_write_json(ECONOMY_DATA_PATH, _ECONOMY_CACHE)


def ensure_user(user_id: Any, default_cash: int = DEFAULT_STARTING_CASH) -> Dict[str, Any]:
    """Garantiza que un usuario exista en la base de datos de economía con campos completos."""
    uid = str(user_id)
    with ECONOMY_LOCK:
        data = load_economy_data()
        users = data.setdefault("users", {})
        if uid not in users:
            users[uid] = {
                "cash": default_cash,
                "bank": DEFAULT_STARTING_BANK,
                "last_work": None,
                "last_rob": None,
                "last_salary": None,
                "inventory": [],
                "portfolio": {},
            }
            save_economy_data(data)
        else:
            user = users[uid]
            modified = False
            for field, def_val in [
                ("cash", default_cash),
                ("bank", DEFAULT_STARTING_BANK),
                ("last_work", None),
                ("last_rob", None),
                ("last_salary", None),
                ("inventory", []),
                ("portfolio", {}),
            ]:
                if field not in user:
                    user[field] = def_val
                    modified = True
            if modified:
                save_economy_data(data)
        return users[uid]


def get_user_economy(user_id: Any) -> Dict[str, Any]:
    """Devuelve el objeto completo de economía de un usuario."""
    return ensure_user(user_id)


def get_balance(user_id: Any) -> Dict[str, int]:
    """Devuelve el balance {'cash': int, 'bank': int, 'total': int} de un usuario."""
    user = ensure_user(user_id)
    cash = int(user.get("cash", 0))
    bank = int(user.get("bank", 0))
    return {
        "cash": cash,
        "bank": bank,
        "total": cash + bank,
    }


def modify_balance(
    user_id: Any,
    cash_delta: int = 0,
    bank_delta: int = 0,
    allow_negative: bool = False,
) -> Dict[str, int]:
    """Modifica el saldo en efectivo o banco de un usuario de forma atómica y segura."""
    uid = str(user_id)
    with ECONOMY_LOCK:
        data = load_economy_data()
        users = data.setdefault("users", {})
        if uid not in users:
            users[uid] = {
                "cash": DEFAULT_STARTING_CASH,
                "bank": DEFAULT_STARTING_BANK,
                "last_work": None,
                "last_rob": None,
                "last_salary": None,
                "inventory": [],
                "portfolio": {},
            }
        user = users[uid]
        current_cash = int(user.get("cash", 0))
        current_bank = int(user.get("bank", 0))

        new_cash = current_cash + cash_delta
        new_bank = current_bank + bank_delta

        if not allow_negative and (new_cash < 0 or new_bank < 0):
            raise ValueError(
                f"Fondos insuficientes para el usuario {uid}. "
                f"Efectivo: {current_cash} (delta: {cash_delta}), Banco: {current_bank} (delta: {bank_delta})"
            )

        user["cash"] = new_cash
        user["bank"] = new_bank
        save_economy_data(data)

        return {
            "cash": new_cash,
            "bank": new_bank,
            "total": new_cash + new_bank,
        }


# ==========================================
# BOTE PROGRESIVO DEL SERVIDOR (JACKPOT)
# ==========================================

def get_server_jackpot() -> int:
    """Devuelve el importe acumulado actual del bote del servidor."""
    with ECONOMY_LOCK:
        data = load_economy_data()
        return int(data.get("server_jackpot", DEFAULT_JACKPOT))


def modify_server_jackpot(delta: int) -> int:
    """Modifica el bote acumulado y persiste los cambios."""
    with ECONOMY_LOCK:
        data = load_economy_data()
        current = int(data.get("server_jackpot", DEFAULT_JACKPOT))
        new_val = max(DEFAULT_JACKPOT, current + delta)
        data["server_jackpot"] = new_val
        save_economy_data(data)
        return new_val


def reset_server_jackpot(base_amount: int = DEFAULT_JACKPOT) -> int:
    """Reinicia el bote del servidor a la cantidad base tras ser reclamado."""
    with ECONOMY_LOCK:
        data = load_economy_data()
        data["server_jackpot"] = base_amount
        save_economy_data(data)
        return base_amount


# ==========================================
# BANCA: DEPÓSITOS Y RETIRADAS
# ==========================================

def deposit_cash(user_id: Any, amount: Union[int, str]) -> Tuple[bool, str, Dict[str, int]]:
    """Deposita Porros de efectivo al banco de forma atómica. Soporta número entero o 'all'/'max'/'todo'."""
    uid = str(user_id)
    with ECONOMY_LOCK:
        bal = get_balance(uid)
        cash = bal["cash"]

        if isinstance(amount, str):
            amt_lower = amount.strip().lower()
            if amt_lower in ("all", "todo", "max"):
                dep_amount = cash
            else:
                try:
                    dep_amount = int(amt_lower)
                except ValueError:
                    return False, "Cantidad inválida. Especifica un número entero positivo o 'all'.", bal
        else:
            dep_amount = int(amount)

        if dep_amount <= 0:
            return False, "La cantidad a depositar debe ser mayor a 0 Porros.", bal

        if cash < dep_amount:
            return False, f"No tienes suficientes Porros en efectivo. Saldo disponible: {cash:,} Porros.", bal

        new_bal = modify_balance(uid, cash_delta=-dep_amount, bank_delta=+dep_amount)
        _bot_log(f"🏦 [Banco] {uid} depositó {dep_amount:,} Porros en su cuenta bancaria.")
        return True, f"Has depositado {PORRO_EMOJI} **{dep_amount:,}** Porros en el banco.", new_bal


def withdraw_cash(user_id: Any, amount: Union[int, str]) -> Tuple[bool, str, Dict[str, int]]:
    """Retira Porros del banco al efectivo de forma atómica. Soporta número entero o 'all'/'max'/'todo'."""
    uid = str(user_id)
    with ECONOMY_LOCK:
        bal = get_balance(uid)
        bank = bal["bank"]

        if isinstance(amount, str):
            amt_lower = amount.strip().lower()
            if amt_lower in ("all", "todo", "max"):
                with_amount = bank
            else:
                try:
                    with_amount = int(amt_lower)
                except ValueError:
                    return False, "Cantidad inválida. Especifica un número entero positivo o 'all'.", bal
        else:
            with_amount = int(amount)

        if with_amount <= 0:
            return False, "La cantidad a retirar debe ser mayor a 0 Porros.", bal

        if bank < with_amount:
            return False, f"No tienes suficientes Porros en el banco. Saldo disponible: {bank:,} Porros.", bal

        new_bal = modify_balance(uid, cash_delta=+with_amount, bank_delta=-with_amount)
        _bot_log(f"🏧 [Banco] {uid} retiró {with_amount:,} Porros de su cuenta bancaria.")
        return True, f"Has retirado {PORRO_EMOJI} **{with_amount:,}** Porros del banco.", new_bal


# ==========================================
# TRANSFERENCIAS Y SISTEMA DE TRABAJO
# ==========================================

def transfer_funds(
    from_user_id: Any,
    to_user_id: Any,
    amount: int,
) -> Tuple[bool, str, Optional[Dict[str, int]], Optional[Dict[str, int]]]:
    """Transfiere Porros en efectivo de un usuario a otro de forma atómica."""
    from_uid = str(from_user_id)
    to_uid = str(to_user_id)

    if from_uid == to_uid:
        return False, "No puedes transferirte Porros a ti mismo.", None, None

    if amount <= 0:
        return False, "La cantidad a transferir debe ser mayor a 0 Porros.", None, None

    with ECONOMY_LOCK:
        sender_bal = get_balance(from_uid)
        if sender_bal["cash"] < amount:
            return (
                False,
                f"No tienes suficientes Porros en efectivo. Saldo actual: {sender_bal['cash']:,} Porros.",
                None,
                None,
            )

        new_sender = modify_balance(from_uid, cash_delta=-amount)
        new_recipient = modify_balance(to_uid, cash_delta=amount)

        _bot_log(f"💸 [Transferencia] {from_uid} envió {amount:,} Porros a {to_uid}.")
        return True, "Transferencia realizada con éxito.", new_sender, new_recipient


def can_work(user_id: Any, cooldown_seconds: int = 7200) -> Tuple[bool, float]:
    """Comprueba si un usuario puede trabajar según su cooldown (por defecto 2 horas)."""
    user = ensure_user(user_id)
    last_work_str = user.get("last_work")
    if not last_work_str:
        return True, 0.0

    try:
        last_work_dt = datetime.fromisoformat(last_work_str)
        now = datetime.now(timezone.utc)
        elapsed = (now - last_work_dt).total_seconds()
        if elapsed >= cooldown_seconds:
            return True, 0.0
        return False, cooldown_seconds - elapsed
    except Exception:
        return True, 0.0


def execute_work(
    user_id: Any,
    cooldown_seconds: int = 7200,
    min_reward: int = 200,
    max_reward: int = 800,
) -> Tuple[bool, str, int]:
    """Ejecuta una jornada laboral y abona la recompensa si no está en cooldown."""
    uid = str(user_id)
    with ECONOMY_LOCK:
        allowed, remaining = can_work(uid, cooldown_seconds)
        if not allowed:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            seconds = int(remaining % 60)
            if hours > 0:
                time_str = f"**{hours}h {minutes}m**"
            elif minutes > 0:
                time_str = f"**{minutes}m {seconds}s**"
            else:
                time_str = f"**{seconds}s**"
            return (
                False,
                f"⏳ Ya has trabajado recientemente. Tienes que esperar {time_str} para volver a currar.",
                0,
            )

        reward = random.randint(min_reward, max_reward)
        job_story = random.choice(WORK_MESSAGES)

        modify_balance(uid, cash_delta=reward)
        data = load_economy_data()
        data["users"][uid]["last_work"] = datetime.now(timezone.utc).isoformat()
        save_economy_data(data)

        _bot_log(f"💼 [Trabajo] {uid} ganó {reward:,} Porros con: '{job_story[:40]}...'")
        return True, job_story, reward


# ==========================================
# ROBO CON CHECK DE INMUNIDAD (CARTERA BLINDADA)
# ==========================================

def user_has_shield(user_id: Any, member: Optional[Any] = None) -> bool:
    """Verifica si el usuario tiene inmunidad activa '🛡️ Cartera Blindada' por inventario o rol."""
    uid = str(user_id)
    user_data = ensure_user(uid)
    inv = user_data.get("inventory", [])
    if any("cartera blindada" in str(item).lower() for item in inv):
        return True

    if member is not None:
        roles = getattr(member, "roles", [])
        for r in roles:
            if str(getattr(r, "id", "")) == "1549520453926912062":
                return True
            if "cartera blindada" in getattr(r, "name", "").lower():
                return True
    return False


def can_rob(user_id: Any, cooldown_seconds: int = 7200) -> Tuple[bool, float]:
    """Comprueba si un usuario puede robar según su cooldown (por defecto 2 horas)."""
    user = ensure_user(user_id)
    last_rob_str = user.get("last_rob")
    if not last_rob_str:
        return True, 0.0

    try:
        last_rob_dt = datetime.fromisoformat(last_rob_str)
        now = datetime.now(timezone.utc)
        elapsed = (now - last_rob_dt).total_seconds()
        if elapsed >= cooldown_seconds:
            return True, 0.0
        return False, cooldown_seconds - elapsed
    except Exception:
        return True, 0.0


def execute_rob(
    robber_id: Any,
    victim_id: Any,
    victim_member: Optional[Any] = None,
    cooldown_seconds: int = 7200,
) -> Tuple[bool, str, int]:
    """
    Ejecuta un intento de robo (/robar):
    - 50% probabilidad de éxito.
    - Roba entre el 20% y el 50% del efectivo (cash) de la víctima (el banco es 100% inmune).
    - Chequeo de '🛡️ Cartera Blindada': inmunidad absoluta; el atraco falla al 100% y el ladrón paga el 15% de su cash a la víctima.
    - Si falla normalmente: el ladrón es interceptado y paga el 15% de su cash a la víctima o policía.
    """
    r_uid = str(robber_id)
    v_uid = str(victim_id)

    if r_uid == v_uid:
        return False, "❌ No puedes robarte a ti mismo. Ve al casino si quieres perder dinero.", 0

    with ECONOMY_LOCK:
        allowed, remaining = can_rob(r_uid, cooldown_seconds)
        if not allowed:
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            time_str = f"**{mins}m {secs}s**" if mins > 0 else f"**{secs}s**"
            return False, f"⏳ Tienes a la policía buscándote. Espera {time_str} para volver a atracar.", 0

        robber_bal = get_balance(r_uid)
        victim_bal = get_balance(v_uid)

        if victim_bal["cash"] < 100:
            return False, f"❌ La víctima está tiesa (solo tiene {victim_bal['cash']:,} Porros en efectivo). No merece el riesgo.", 0

        # Check Cartera Blindada
        if user_has_shield(v_uid, victim_member):
            # 100% fallo y multa del 15% del efectivo del ladrón pagado a la víctima
            fine = max(100, int(robber_bal["cash"] * 0.15)) if robber_bal["cash"] > 0 else 0
            if fine > 0 and robber_bal["cash"] >= fine:
                modify_balance(r_uid, cash_delta=-fine)
                modify_balance(v_uid, cash_delta=+fine)
            data = load_economy_data()
            data["users"][r_uid]["last_rob"] = datetime.now(timezone.utc).isoformat()
            save_economy_data(data)

            msg = (
                f"🛡️ **¡ATRACO FRUSTRADO POR CARTERA BLINDADA!**\n"
                f"La víctima posee la **`🛡️ Cartera Blindada`** activa. El sistema de electrochoque y blindaje "
                f"te ha neutralizado en el acto. Has tenido que pagar una fianza indemnizatoria de {PORRO_EMOJI} **{fine:,}** Porros a la víctima."
            )
            _bot_log(f"🛡️ [Robo Bloqueado] {r_uid} intentó robar a {v_uid} (Cartera Blindada). Multa: {fine} Porros.")
            return False, msg, -fine

        # Intento de robo estándar (50% éxito)
        success = random.random() < 0.50
        data = load_economy_data()
        data["users"][r_uid]["last_rob"] = datetime.now(timezone.utc).isoformat()
        save_economy_data(data)

        if success:
            steal_pct = random.uniform(0.20, 0.50)
            stolen = max(1, int(victim_bal["cash"] * steal_pct))
            modify_balance(v_uid, cash_delta=-stolen)
            modify_balance(r_uid, cash_delta=+stolen)

            msg = (
                f"🥷 **¡GOLPE MAESTRO!**\n"
                f"Aprovechaste un descuido y le birlaste {PORRO_EMOJI} **{stolen:,}** Porros "
                f"({int(steal_pct * 100)}% de su efectivo) sin que se diera cuenta."
            )
            _bot_log(f"🥷 [Robo Exitoso] {r_uid} robó {stolen:,} Porros a {v_uid}.")
            return True, msg, stolen
        else:
            fine = max(100, int(robber_bal["cash"] * 0.15)) if robber_bal["cash"] > 0 else 0
            if fine > 0 and robber_bal["cash"] >= fine:
                modify_balance(r_uid, cash_delta=-fine)
                modify_balance(v_uid, cash_delta=+fine)

            msg = (
                f"🚨 **¡ATRACO FALLIDO!**\n"
                f"Te tropezaste con una lata haciendo un ruido tremendo y fuiste pillado in fraganti. "
                f"Tuviste que soltar {PORRO_EMOJI} **{fine:,}** Porros en compensación a la víctima para que no te llevaran detenido."
            )
            _bot_log(f"🚨 [Robo Fallido] {r_uid} falló contra {v_uid}. Multa: {fine} Porros.")
            return False, msg, -fine


# ==========================================
# TIENDA OFICIAL V2 (9 ARTÍCULOS)
# ==========================================

def get_shop_catalog() -> Dict[str, Dict[str, Any]]:
    """Devuelve el catálogo maestro de 9 ítems de la tienda."""
    return SHOP_ITEMS


def buy_shop_item(
    user_id: Any,
    item_key: str,
    member: Optional[Any] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]], Dict[str, int]]:
    """Compra un artículo de la tienda y añade el rol si procede."""
    uid = str(user_id)
    item_key_clean = item_key.strip().lower()

    # Mapeo flexible de identificadores
    matched_item = None
    for k, it in SHOP_ITEMS.items():
        if k == item_key_clean or it["name"].lower() == item_key_clean or k in item_key_clean:
            matched_item = it
            break

    if not matched_item:
        return False, f"❌ El artículo '{item_key}' no existe en el catálogo de la tienda.", None, get_balance(uid)

    item_id = matched_item["id"]
    item_name = matched_item["name"]
    price = matched_item["price"]

    with ECONOMY_LOCK:
        user_data = ensure_user(uid)
        inv = user_data.setdefault("inventory", [])
        bal = get_balance(uid)

        # Chequeo de posesión única
        if matched_item.get("unique", False):
            if item_name in inv or (matched_item["type"] == "role" and user_has_shield(uid, member) and item_id == "cartera_blindada"):
                return False, f"❌ Ya posees **{item_name}**. Este artículo no es acumulable.", matched_item, bal

        if bal["cash"] < price:
            return (
                False,
                f"❌ No tienes suficientes Porros en efectivo ({PORRO_EMOJI}) para comprar **{item_name}**.\n"
                f"Precio: **{price:,}** Porros | Saldo en efectivo: **{bal['cash']:,}** Porros.\n"
                f"💡 Si tienes saldo en el banco, usa `/retirar`.",
                matched_item,
                bal,
            )

        # Deducir precio y añadir al inventario
        new_bal = modify_balance(uid, cash_delta=-price)
        data = load_economy_data()
        data["users"][uid].setdefault("inventory", []).append(item_name)
        save_economy_data(data)

        _bot_log(f"🛒 [Tienda] {uid} compró '{item_name}' por {price:,} Porros.")
        return True, f"✅ ¡Has adquirido **{item_name}** por {PORRO_EMOJI} **{price:,}** Porros!", matched_item, new_bal


def build_shop_embed(user_id: Any) -> discord.Embed:
    """Construye el embed oficial del catálogo de la tienda categorizado con el saldo del usuario."""
    bal = get_balance(user_id)
    cash_str = f"{bal['cash']:,}"

    embed = discord.Embed(
        title="🏪 Tienda Oficial de Porros — 'Asistente'",
        description=(
            "Bienvenido al mercado oficial del servidor. Adquiere roles de estatus, ventajas e ítems de inventario.\n\n"
            "📌 **Cómo comprar de forma segura:**\n"
            "1. Elige un artículo en el **menú desplegable** de abajo.\n"
            "2. Presiona el botón verde **`[ 🛒 Comprar Artículo ]`** para confirmar tu compra."
        ),
        color=0xF39C12,
        timestamp=datetime.now(timezone.utc),
    )

    # 1. Roles de Estatus y Protección
    embed.add_field(
        name="🎭 Roles de Estatus y Protección",
        value=(
            f"• **🛡️ Cartera Blindada** — {PORRO_EMOJI} **50,000** Porros\n"
            f"  *Inmunidad total contra /robar (falla 100% y multa 15%).*\n"
            f"• **🚬 Camello del Barrio** — {PORRO_EMOJI} **85,000** Porros\n"
            f"  *Rol cosmético exclusivo en verde porro (#2ECC71).*\n"
            f"• **🎰 Ludópata Rehabilitado** — {PORRO_EMOJI} **40,000** Porros\n"
            f"  *Rol cosmético exclusivo en rojo casino (#E74C3C).*"
        ),
        inline=False,
    )

    # 2. Ítems de Inventario
    embed.add_field(
        name="🎒 Ítems de Inventario",
        value=(
            f"• **🚬 Porro de Oro** — {PORRO_EMOJI} **75,000** Porros\n"
            f"  *Coleccionable de inventario de máximo prestigio y flexeo.*\n"
            f"• **🍗 Pollo de Pelea Dopado** — {PORRO_EMOJI} **25,000** Porros\n"
            f"  *Ítem de combate para duelos de cockfight y apuestas.*"
        ),
        inline=False,
    )

    # 3. Pases de Experiencia (XP)
    embed.add_field(
        name="⚡ Pases y Bonos de Experiencia (XP)",
        value=(
            f"• **⚡ Chute de XP (24h)** — {PORRO_EMOJI} **15,000** Porros\n"
            f"  *Boost temporal de +5% de XP en Cakey Bot durante 24 horas.*\n"
            f"• **🔥 Pase Semanal de XP** — {PORRO_EMOJI} **75,000** Porros\n"
            f"  *Boost temporal de +10% de XP en Cakey Bot durante 7 días.*\n"
            f"• **💠 Pase Mensual de XP** — {PORRO_EMOJI} **250,000** Porros\n"
            f"  *Boost temporal de +15% de XP en Cakey Bot durante 30 días.*\n"
            f"• **👑 Aura de XP Permanente** — {PORRO_EMOJI} **1,000,000** Porros\n"
            f"  *Pase perpetuo élite con boost de +10% de XP permanente.*"
        ),
        inline=False,
    )

    embed.set_footer(
        text=f"Tu saldo en efectivo: {cash_str} Porros • Si tienes saldo en el banco usa /retirar"
    )
    return embed


class ShopItemSelect(discord.ui.Select):
    """Menú desplegable con los 9 artículos oficiales de la tienda."""

    def __init__(self):
        options = [
            discord.SelectOption(
                label="🛡️ Cartera Blindada (50k)",
                value="cartera_blindada",
                description="50.000 Porros • Inmunidad a robos",
                emoji="🛡️",
            ),
            discord.SelectOption(
                label="🚬 Porro de Oro (75k)",
                value="porro_oro",
                description="75.000 Porros • Flexeo de inventario",
                emoji="🚬",
            ),
            discord.SelectOption(
                label="🚬 Camello del Barrio (85k)",
                value="camello_barrio",
                description="85.000 Porros • Rol Verde (#2ECC71)",
                emoji="🚬",
            ),
            discord.SelectOption(
                label="🎰 Ludópata Rehabilitado (40k)",
                value="ludopata_rehabilitado",
                description="40.000 Porros • Rol Rojo (#E74C3C)",
                emoji="🎰",
            ),
            discord.SelectOption(
                label="🍗 Pollo de Pelea Dopado (25k)",
                value="pollo_pelea",
                description="25.000 Porros • Duelos de combate",
                emoji="🍗",
            ),
            discord.SelectOption(
                label="⚡ Chute de XP 24h (15k)",
                value="chute_xp",
                description="15.000 Porros • Boost +5% XP por 24h",
                emoji="⚡",
            ),
            discord.SelectOption(
                label="🔥 Pase Semanal de XP (75k)",
                value="pase_semanal_xp",
                description="75.000 Porros • Boost +10% XP por 7d",
                emoji="🔥",
            ),
            discord.SelectOption(
                label="💠 Pase Mensual de XP (250k)",
                value="pase_mensual_xp",
                description="250.000 Porros • Boost +15% XP por 30d",
                emoji="💠",
            ),
            discord.SelectOption(
                label="👑 Aura de XP Permanente (1M)",
                value="aura_xp",
                description="1.000.000 Porros • Boost +10% XP permanente",
                emoji="👑",
            ),
        ]
        super().__init__(
            placeholder="🛒 Selecciona un artículo de la tienda...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        view: "ShopInteractiveView" = self.view
        if interaction.user.id != view.author_id:
            await interaction.response.send_message(
                "❌ Esta tienda pertenece a otro usuario. Usa `/tienda` para abrir la tuya.",
                ephemeral=True,
            )
            return

        selected_key = self.values[0]
        view.selected_item = selected_key
        item_info = SHOP_ITEMS.get(selected_key)
        item_name = item_info["name"] if item_info else selected_key
        price = item_info["price"] if item_info else 0

        # Actualizar el botón de compra con el nombre y precio del artículo seleccionado
        view.buy_btn.label = f"🛒 Comprar {item_name} ({price:,} Porros)"
        view.buy_btn.disabled = False

        await interaction.response.edit_message(view=view)


class ShopInteractiveView(discord.ui.View):
    """
    Vista interactiva para /tienda con menú desplegable y botón explícito de confirmación de compra.
    Evita compras accidentales asegurando que la transacción solo se ejecute al pulsar el botón.
    """

    def __init__(self, author_id: Any, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.author_id = int(author_id)
        self.selected_item: Optional[str] = None
        self.message: Optional[discord.Message] = None

        # Desplegable de artículos (Fila 0)
        self.select_menu = ShopItemSelect()
        self.add_item(self.select_menu)

        # Botón verde de compra explícita (Fila 1)
        self.buy_btn = discord.ui.Button(
            label="🛒 Comprar Artículo",
            style=discord.ButtonStyle.success,
            row=1,
            disabled=False,
        )
        self.buy_btn.callback = self._on_buy_clicked
        self.add_item(self.buy_btn)

    async def _on_buy_clicked(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Esta tienda pertenece a otro usuario. Usa `/tienda` para abrir la tuya.",
                ephemeral=True,
            )
            return

        if not self.selected_item:
            await interaction.response.send_message(
                "⚠️ Selecciona primero un artículo del menú desplegable antes de presionar el botón de compra.",
                ephemeral=True,
            )
            return

        item_key = self.selected_item
        ok, msg, item_data, new_bal = buy_shop_item(
            interaction.user.id,
            item_key,
            member=interaction.user,
        )

        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return

        # Auto-asignación de rol si es de tipo 'role'
        role_added = False
        if item_data and item_data.get("type") == "role" and hasattr(interaction.user, "add_roles"):
            role_id_str = item_data.get("role_id")
            if role_id_str and interaction.guild:
                role = interaction.guild.get_role(int(role_id_str))
                if role:
                    try:
                        await interaction.user.add_roles(role, reason="Compra interactiva en /tienda")
                        role_added = True
                    except Exception as e:
                        _bot_log(f"Aviso auto-asignando rol {role.name}: {e}")

        confirm_embed = discord.Embed(
            title="🛒 ¡Compra Realizada con Éxito!",
            description=(
                f"{msg}\n\n"
                f"**Saldo restante en efectivo:** {PORRO_EMOJI} **{new_bal['cash']:,}** Porros"
            ),
            color=0x2ECC71,
            timestamp=datetime.now(timezone.utc),
        )
        if role_added:
            confirm_embed.add_field(
                name="🎭 Rol Asignado",
                value=f"¡El rol `{item_data['name']}` ha sido añadido a tu perfil de Discord!",
                inline=False,
            )
        confirm_embed.set_footer(text="Gracias por tu compra • Consulta tu inventario con /balance")

        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

        # Actualizar el embed principal de la tienda con el nuevo saldo
        try:
            updated_embed = build_shop_embed(self.author_id)
            if interaction.message:
                await interaction.message.edit(embed=updated_embed, view=self)
        except Exception as e:
            _bot_log(f"Aviso actualizando embed de tienda tras compra: {e}")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


# ==========================================
# SALARIO ACUMULATIVO CON DECAIMIENTO DEL 5%
# ==========================================

def calculate_daily_salary(member: Optional[Any] = None, user_roles: Optional[List[str]] = None) -> int:
    """Calcula el salario diario base (S) según los roles de nivel y podio del usuario."""
    role_names_lower = []
    if member is not None and hasattr(member, "roles"):
        role_names_lower = [r.name.lower() for r in member.roles]
    elif user_roles:
        role_names_lower = [str(r).lower() for r in user_roles]

    if not role_names_lower:
        return DEFAULT_BASE_SALARY

    total_daily = 0
    matched = False

    for key, info in ROLE_SALARIES.items():
        kws = info["kw"]
        for r_name in role_names_lower:
            if any(kw in r_name for kw in kws):
                total_daily += info["daily"]
                matched = True
                break

    if not matched or total_daily == 0:
        return DEFAULT_BASE_SALARY

    return total_daily


def calculate_accumulated_salary(
    daily_salary: int,
    elapsed_seconds: float,
    decay_rate: float = 0.05,
) -> int:
    """
    Fórmula de salario acumulativo con decaimiento continuo:
    n = días transcurridos = elapsed_seconds / 86400.0
    P = S * (1 - (1 - d)^n) / d
    Tope asintótico: S / d = 20 * S
    """
    if daily_salary <= 0 or elapsed_seconds <= 0:
        return 0

    n_days = max(0.0, elapsed_seconds / 86400.0)
    # Factor de acumulación: (1 - (1 - d)^n) / d
    base = 1.0 - decay_rate
    factor = (1.0 - math.pow(base, n_days)) / decay_rate
    # Límite asintótico máximo: 1 / decay_rate = 20.0
    factor = min(factor, 1.0 / decay_rate)

    accumulated = int(round(daily_salary * factor))
    return max(1, accumulated)


def can_claim_salary(user_id: Any, cooldown_seconds: int = 86400) -> Tuple[bool, float]:
    """Comprueba si un usuario puede cobrar su salario acumulado (cooldown de 24 horas)."""
    user = ensure_user(user_id)
    last_sal_str = user.get("last_salary")
    if not last_sal_str:
        return True, 0.0

    try:
        last_sal_dt = datetime.fromisoformat(last_sal_str)
        now = datetime.now(timezone.utc)
        elapsed = (now - last_sal_dt).total_seconds()
        if elapsed >= cooldown_seconds:
            return True, 0.0
        return False, cooldown_seconds - elapsed
    except Exception:
        return True, 0.0


def claim_salary(user_id: Any, member: Optional[Any] = None) -> Tuple[bool, str, int, int]:
    """
    Reclama el salario acumulado aplicando la fórmula de decaimiento del 5%:
    Devuelve (éxito, mensaje, salario_cobrado, salario_diario_base).
    """
    uid = str(user_id)
    with ECONOMY_LOCK:
        user = ensure_user(uid)
        last_sal_str = user.get("last_salary")
        daily_salary = calculate_daily_salary(member)

        now = datetime.now(timezone.utc)

        if not last_sal_str:
            # Primer cobro: abona 1 día completo de salario base
            payout = daily_salary
            modify_balance(uid, cash_delta=payout)
            data = load_economy_data()
            data["users"][uid]["last_salary"] = now.isoformat()
            save_economy_data(data)

            msg = (
                f"💵 **¡PRIMER SALARIO COBRADO!**\n"
                f"Has recibido tu salario inaugural de {PORRO_EMOJI} **{payout:,}** Porros.\n"
                f"Salario diario base de tu rango: **{daily_salary:,}** Porros/día."
            )
            _bot_log(f"💵 [Salario] {uid} cobró salario inaugural: {payout:,} Porros.")
            return True, msg, payout, daily_salary

        last_sal_dt = datetime.fromisoformat(last_sal_str)
        elapsed = (now - last_sal_dt).total_seconds()

        if elapsed < 86400:
            remaining = 86400 - elapsed
            hours = int(remaining // 3600)
            mins = int((remaining % 3600) // 60)
            time_str = f"**{hours}h {mins}m**" if hours > 0 else f"**{mins}m**"
            projected = calculate_accumulated_salary(daily_salary, elapsed)
            return (
                False,
                f"⏳ Ya has cobrado tu salario hoy. Podrás volver a cobrar en {time_str}.\n"
                f"Salario base de tu rango: **{daily_salary:,}** Porros/día (Acumulado actual: **{projected:,}** Porros).",
                0,
                daily_salary,
            )

        payout = calculate_accumulated_salary(daily_salary, elapsed, decay_rate=0.05)
        days_float = round(elapsed / 86400.0, 1)

        modify_balance(uid, cash_delta=payout)
        data = load_economy_data()
        data["users"][uid]["last_salary"] = now.isoformat()
        save_economy_data(data)

        msg = (
            f"💵 **¡SALARIO COBRADO CON ÉXITO!**\n"
            f"Tiempo acumulado: **{days_float} días** (con decaimiento del 5% diario).\n"
            f"Total recibido: {PORRO_EMOJI} **+{payout:,}** Porros.\n"
            f"Salario base de tu rango: **{daily_salary:,}** Porros/día."
        )
        _bot_log(f"💵 [Salario] {uid} cobró salario acumulado de {payout:,} Porros tras {days_float} días.")
        return True, msg, payout, daily_salary


# ==========================================
# MOTOR DE LA MÁQUINA TRAGAPERRAS 5x3 (SLOTS)
# ==========================================

class SlotEngine:
    """Motor y evaluación de combinaciones para la máquina tragaperras 5x3 de Alta Tensión."""

    def __init__(self, symbols_dict: Optional[Dict[str, Any]] = None):
        self.symbols = symbols_dict or SLOT_SYMBOLS
        self.symbol_keys = list(self.symbols.keys())
        self.weights = [self.symbols[k]["weight"] for k in self.symbol_keys]

    def spin_grid(self) -> List[List[str]]:
        """Genera una matriz 3 filas x 5 columnas (15 casilleros) de símbolos usando pesos calibrados."""
        grid = []
        for _ in range(3):
            row = random.choices(self.symbol_keys, weights=self.weights, k=5)
            grid.append(row)
        return grid

    def evaluate_line(self, line_syms: List[str]) -> Tuple[Optional[str], int, float]:
        """
        Evalúa una línea de 5 casilleros buscando ventanas consecutivas de tamaño k = 5, 4, 3
        en cualquier posición de la línea (Opción B: [0..4], [0..3]/[1..4], [0..2]/[1..3]/[2..4]).
        Wild sustituye a cualquier regular; una ventana de Wilds puros también premia.
        Se prioriza la longitud más larga (k=5 > k=4 > k=3) y el multiplicador más alto.
        Devuelve (best_sym, best_count, best_mult).
        """
        regular_keys = ["Gold", "Diamond", "Mythic", "Legendary", "Masters", "Pro"]

        for k in (5, 4, 3):
            best_sym_k = None
            best_mult_k = 0.0

            for start in range(len(line_syms) - k + 1):
                window = line_syms[start : start + k]

                if "Scatter" in window:
                    continue

                if all(s == "Wild" for s in window):
                    w_mult = self.symbols["Wild"]["mults"].get(k, 0.0)
                    if w_mult > best_mult_k:
                        best_mult_k = w_mult
                        best_sym_k = "Wild"
                    continue

                nw = [s for s in window if s != "Wild"]
                if len(nw) > 0 and all(s == nw[0] for s in nw) and nw[0] in regular_keys:
                    reg = nw[0]
                    reg_mult = self.symbols[reg]["mults"].get(k, 0.0)
                    if reg_mult > best_mult_k:
                        best_mult_k = reg_mult
                        best_sym_k = reg

            if best_mult_k > 0:
                return best_sym_k, k, best_mult_k

        return None, 0, 0.0

    def evaluate(
        self,
        grid: List[List[str]],
        bet: int,
        multiplier: float = 1.0,
        is_free_spin: bool = False,
    ) -> Dict[str, Any]:
        """
        Evalúa las 7 líneas de pago clásicas aprobadas por Jose, Pantalla Completa,
        comodines WILD, dispersores SCATTER, multiplicadores y Free Spins.
        """
        winning_lines = []
        total_mult = 0.0

        # 1. Evaluación de las 7 Líneas de Pago Clásicas
        for line_name, coords in SLOT_PAYLINES:
            line_syms = [grid[r][c] for r, c in coords]
            sym, count, mult = self.evaluate_line(line_syms)
            if mult > 0:
                final_mult = mult * multiplier
                total_mult += final_mult
                winning_lines.append({
                    "line": f"{line_name} ({count}x)",
                    "symbol": sym,
                    "count": count,
                    "emoji": self.symbols[sym]["emoji"],
                    "mult": round(final_mult, 2),
                })

        # 2. Pantalla Completa (15 de 15)
        all_syms = [grid[r][c] for r in range(3) for c in range(5)]
        full_screen_hit = False
        if "Scatter" not in all_syms:
            nw = [s for s in all_syms if s != "Wild"]
            if len(nw) == 0 or all(s == nw[0] for s in nw):
                matched = "Wild" if len(nw) == 0 else nw[0]
                full_mult = 500.0 * multiplier
                total_mult += full_mult
                full_screen_hit = True
                winning_lines.append({
                    "line": f"🌟 ¡¡PANTALLA COMPLETA 15/15 ({self.symbols[matched]['name']})!!",
                    "symbol": matched,
                    "count": 15,
                    "emoji": self.symbols[matched]["emoji"],
                    "mult": round(full_mult, 2),
                })

        # 3. Evaluación de Dispersores SCATTER (en cualquier posición de los 15 casilleros)
        scatter_count = sum(row.count("Scatter") for row in grid)
        free_spins_triggered = False
        free_spins_count = 0
        free_spins_multiplier = 1

        if scatter_count >= 3:
            if scatter_count == 3:
                sc_mult = 4.0
                fs_c = 5
            elif scatter_count == 4:
                sc_mult = 13.0
                fs_c = 8
            else:  # >= 5
                sc_mult = 48.0
                fs_c = 12

            sc_final = sc_mult * multiplier
            total_mult += sc_final
            winning_lines.append({
                "line": f"Scatter ({scatter_count} Porros)",
                "symbol": "Scatter",
                "count": scatter_count,
                "emoji": self.symbols["Scatter"]["emoji"],
                "mult": round(sc_final, 2),
            })
            free_spins_triggered = True
            free_spins_count = 3 if is_free_spin else fs_c
            free_spins_multiplier = 2

        payout = int(bet * total_mult)
        net = payout - (0 if is_free_spin else bet)

        # 4. Detección de Botes Progresivos en la Línea Central (L1: 5 casillas)
        l1_syms = [grid[1][c] for c in range(5)]
        grand_jackpot_hit = (
            all(s == "Pro" for s in l1_syms) or
            all(s == "Wild" for s in l1_syms)
        )
        mini_jackpot_hit = all(s == "Masters" for s in l1_syms)

        # 5. Título y color según el resultado
        if grand_jackpot_hit:
            title = "### 💥 ¡¡GRAND JACKPOT DEL SERVIDOR!! 💥"
            accent_color = 16766720  # Dorado intenso
        elif mini_jackpot_hit:
            title = "### 💎 ¡¡MINI JACKPOT DEL SERVIDOR!! 💎"
            accent_color = 16766720  # Dorado
        elif full_screen_hit:
            title = "### 🌟 ¡¡PANTALLA COMPLETA 15/15!! 🌟"
            accent_color = 16766720
        elif free_spins_triggered and not is_free_spin:
            title = "### 🌀 ¡¡RONDA DE FREE SPINS DESBLOQUEADA!! 🌀"
            accent_color = 10181046  # Violeta neón #9B59B6
        elif total_mult == 0:
            title = "### No Win"
            accent_color = 15684432  # Rojo #EF5350
        elif total_mult < 5.0:
            title = "### You Won!"
            accent_color = 6732650   # Verde #66B96A
        elif total_mult < 20.0:
            title = "### Good Win!"
            accent_color = 6732650   # Verde #66B96A
        else:
            title = "### Big Win!"
            accent_color = 16766720  # Dorado #FFC107

        return {
            "grid": grid,
            "bet": bet,
            "total_mult": round(total_mult, 2),
            "payout": payout,
            "net": net,
            "winning_lines": winning_lines,
            "title": title,
            "accent_color": accent_color,
            "scatter_count": scatter_count,
            "free_spins_triggered": free_spins_triggered,
            "free_spins_count": free_spins_count,
            "free_spins_multiplier": free_spins_multiplier,
            "grand_jackpot_hit": grand_jackpot_hit,
            "mini_jackpot_hit": mini_jackpot_hit,
            "full_screen_hit": full_screen_hit,
            "is_free_spin": is_free_spin,
        }

    def simulate_monte_carlo(self, spins: int = 100000, bet: int = 1000) -> Dict[str, Any]:
        """Simula N tiradas para validar matemáticamente el RTP (110.0%) y Hit Rate."""
        total_bet = spins * bet
        total_payout = 0
        wins_count = 0
        multi_line_wins = 0
        scatters_hit = 0
        free_spins_played = 0
        symbol_hits = {k: 0 for k in self.symbol_keys}

        for _ in range(spins):
            grid = self.spin_grid()
            res = self.evaluate(grid, bet)
            spin_payout = res["payout"]

            if res.get("free_spins_triggered"):
                scatters_hit += 1
                fs_rem = res.get("free_spins_count", 5)
                while fs_rem > 0:
                    free_spins_played += 1
                    fs_rem -= 1
                    fs_grid = self.spin_grid()
                    fs_res = self.evaluate(fs_grid, bet, multiplier=2.0, is_free_spin=True)
                    spin_payout += fs_res["payout"]
                    if fs_res.get("free_spins_triggered"):
                        fs_rem += 3

            total_payout += spin_payout
            if spin_payout > 0:
                wins_count += 1
                if len(res.get("winning_lines", [])) > 1:
                    multi_line_wins += 1
                for wl in res.get("winning_lines", []):
                    sym_name = wl.get("symbol")
                    if sym_name in symbol_hits:
                        symbol_hits[sym_name] += 1

        rtp = (total_payout / total_bet) * 100
        win_rate = (wins_count / spins) * 100

        return {
            "spins": spins,
            "total_bet": total_bet,
            "total_payout": total_payout,
            "rtp_percent": round(rtp, 2),
            "house_edge_percent": round(100 - rtp, 2),
            "win_rate_percent": round(win_rate, 2),
            "multi_line_rate_percent": round((multi_line_wins / spins) * 100, 2),
            "scatters_hit": scatters_hit,
            "free_spins_played": free_spins_played,
            "symbol_hits": symbol_hits,
        }

    def build_discord_v2_payload(
        self,
        result: Dict[str, Any],
        user_id: str,
        remaining_free_spins: int = 0,
        total_bonus_won: int = 0,
    ) -> Dict[str, Any]:
        """Construye el payload diccionario raw de Discord Components V2 para envío HTTP."""
        grid = result["grid"]
        grid_lines = []
        for row in grid:
            grid_lines.append(" ".join(self.symbols[k]["emoji"] for k in row))
        grid_text = "\n".join(grid_lines)

        content_parts = [grid_text]

        if result.get("winning_lines"):
            lines_header = "**Winning Lines:**" if len(result["winning_lines"]) > 1 else "**Winning Line:**"
            content_parts.append("\n" + lines_header)
            for wl in result["winning_lines"]:
                content_parts.append(f"• {wl['emoji']} {wl['line']} (×{wl['mult']})")

        if result.get("jackpot_won", 0) > 0:
            jp_title = "¡GRAND JACKPOT RECLAMADO!" if result.get("jackpot_type") == "grand" else "¡MINI JACKPOT (25%) RECLAMADO!"
            content_parts.append(f"\n💥 **{jp_title}** {PORRO_EMOJI}{result['jackpot_won']:,}")

        if result.get("free_spins_triggered") and not result.get("is_free_spin"):
            sc_c = result.get("scatter_count", 3)
            fs_c = result.get("free_spins_count", 5)
            content_parts.append(
                f"\n🎉 **¡BONUS DESBLOQUEADO!** {sc_c} Scatters <:Porro:1535685303317172305> en pantalla.\n"
                f"¡Premio y **{fs_c} Tiradas Gratis (Free Spins)** con multiplicador **×2**!"
            )
        elif result.get("is_free_spin"):
            if result.get("retrigger"):
                content_parts.append("\n⚡ **¡RE-TRIGGER!** +3 Tiradas Gratis adicionales.")
            if remaining_free_spins > 0:
                content_parts.append(
                    f"\n🌀 **Tiradas restantes:** **{remaining_free_spins}** (Multiplicador ×2)\n"
                    f"💰 **Bonus acumulado:** {PORRO_EMOJI}**{total_bonus_won:,}**"
                )
            else:
                content_parts.append(
                    f"\n🌟 **¡RONDA DE BONUS COMPLETADA!**\n"
                    f"💰 **Ganancia total acreditada:** {PORRO_EMOJI}**{total_bonus_won:,}** Porros"
                )

        payout_str = f"{result['payout']:,}"
        content_parts.append(f"\n**Payout:** {PORRO_EMOJI}{payout_str}")

        body_text = "\n".join(content_parts)

        bet = result["bet"]
        if result.get("free_spins_triggered") and not result.get("is_free_spin"):
            fs_initial = result.get("free_spins_count", 5)
            action_buttons = [
                {
                    "type": 2,
                    "id": 7,
                    "custom_id": f"slots:free-spin:{user_id}:{bet}:{fs_initial}:2:0",
                    "style": 3,  # Success
                    "label": f"🌀 Jugar Tiradas Gratis ({fs_initial} restantes)",
                },
                {
                    "type": 2,
                    "id": 8,
                    "custom_id": "slots:payouts",
                    "style": 2,
                    "label": "Payouts",
                },
            ]
        elif result.get("is_free_spin") and remaining_free_spins > 0:
            action_buttons = [
                {
                    "type": 2,
                    "id": 7,
                    "custom_id": f"slots:free-spin:{user_id}:{bet}:{remaining_free_spins}:2:{total_bonus_won}",
                    "style": 1,
                    "label": f"🌀 Tirada Gratis ({remaining_free_spins} restantes)",
                },
                {
                    "type": 2,
                    "id": 8,
                    "custom_id": "slots:payouts",
                    "style": 2,
                    "label": "Payouts",
                },
            ]
        else:
            action_buttons = [
                {
                    "type": 2,
                    "id": 7,
                    "custom_id": f"slots:play-again:{bet}:{user_id}",
                    "style": 1,
                    "label": "Play Again",
                },
                {
                    "type": 2,
                    "id": 8,
                    "custom_id": "slots:payouts",
                    "style": 2,
                    "label": "Payouts",
                },
            ]

        components = [
            {
                "type": 17,
                "id": 1,
                "accent_color": result["accent_color"],
                "components": [
                    {
                        "type": 10,
                        "id": 2,
                        "content": result["title"],
                    },
                    {
                        "type": 14,
                        "id": 3,
                        "spacing": 1,
                        "divider": True,
                    },
                    {
                        "type": 10,
                        "id": 4,
                        "content": body_text,
                    },
                    {
                        "type": 14,
                        "id": 5,
                        "spacing": 1,
                        "divider": True,
                    },
                    {
                        "type": 1,
                        "id": 6,
                        "components": action_buttons,
                    },
                ],
                "spoiler": False,
            }
        ]

        return {
            "flags": 32768,
            "components": components,
        }


# Instancia global del motor de tragaperras
slot_engine = SlotEngine()


def build_payouts_text() -> str:
    """Genera el texto con la tabla de pagos y estado del bote del servidor."""
    jackpot = get_server_jackpot()
    lines = [
        "🎰 **TABLA DE PAGOS Y REGLAS — TRAGAPERRAS 5×3 DE PORROS**",
        "La máquina evalúa **7 líneas de pago clásicas reales** en cuadrícula de 5 rodillos × 3 filas:",
        "• **L1**: Centro | **L2**: Arriba | **L3**: Abajo",
        "• **L4**: V Suave | **L5**: V Invertida | **L6**: Diagonal Descendente | **L7**: Diagonal Ascendente",
        "",
        "**Multiplicadores por acierto (3 / 4 / 5 en línea de izquierda a derecha):**",
        "• <:absolutecinema:1478115607336714300> **WILD (Comodín)**: **×27.0** / **×88.0** / **×275.0** — Sustituye a cualquier regular. 5 en L1 = ¡Grand Jackpot!",
        "• <:Ranked_Pro:1550129987972104252> **Ranked Pro**: **×21.0** / **×68.0** / **×220.0** — 5 en L1 = **Grand Jackpot** (100% bote).",
        "• <:Ranked_Masters:1550129992837496833> **Ranked Masters**: **×8.5** / **×27.0** / **×84.0** — 5 en L1 = **Mini Jackpot** (25% bote).",
        "• <:Ranked_Legendary:1550129997774323732> **Ranked Legendary**: **×3.0** / **×10.5** / **×34.0**",
        "• <:Ranked_Mythic:1550130000852820099> **Ranked Mythic**: **×1.4** / **×4.9** / **×16.0**",
        "• <:Ranked_Diamond:1550130004074041434> **Ranked Diamond**: **×0.67** / **×2.15** / **×6.9**",
        "• <:Ranked_Gold:1550130006896812084> **Ranked Gold**: **×0.34** / **×1.05** / **×3.5**",
        "",
        "**Patrones Especiales y Bonos:**",
        "• 🌟 **Pantalla Completa (15 casilleros)**: **×500.0** directo al llenar toda la cuadrícula del mismo símbolo o Wilds.",
        "• <:Porro:1535685303317172305> **SCATTER (3 / 4 / 5 en pantalla)**: **×4.0** + 5 Spins / **×13.0** + 8 Spins / **×48.0** + 12 Spins (a ×2).",
        "",
        f"💰 **Bote Progresivo Acumulado:** {PORRO_EMOJI} **{jackpot:,}** Porros *(3% de pérdidas netas alimenta el bote)*",
    ]
    return "\n".join(lines)


def handle_slots_spin(user_id: Any, bet: int) -> Tuple[bool, str, Optional[Dict[str, Any]], Optional[Dict[str, int]]]:
    """Ejecuta el ciclo de una tirada de slots 5x3 de forma segura."""
    uid = str(user_id)
    if bet < 50:
        return False, "La apuesta mínima en la tragaperras es de 50 Porros.", None, None

    with ECONOMY_LOCK:
        bal = get_balance(uid)
        if bal["cash"] < bet:
            return (
                False,
                f"No tienes suficientes Porros en efectivo ({PORRO_EMOJI}). Saldo disponible: **{bal['cash']:,}** Porros.",
                None,
                bal,
            )

        modify_balance(uid, cash_delta=-bet)

        grid = slot_engine.spin_grid()
        res = slot_engine.evaluate(grid, bet)

        if res.get("grand_jackpot_hit"):
            jackpot_amount = get_server_jackpot()
            res["jackpot_won"] = jackpot_amount
            res["jackpot_type"] = "grand"
            res["payout"] += jackpot_amount
            res["title"] = "### 💥 ¡¡GRAND JACKPOT DEL SERVIDOR!! 💥"
            res["accent_color"] = 16766720
            reset_server_jackpot()
            _bot_log(f"🎰 [GRAND JACKPOT] ¡{uid} ha ganado el bote del servidor de {jackpot_amount:,} Porros!")
        elif res.get("mini_jackpot_hit"):
            curr_jp = get_server_jackpot()
            mini_amount = int(curr_jp * 0.25)
            res["jackpot_won"] = mini_amount
            res["jackpot_type"] = "mini"
            res["payout"] += mini_amount
            res["title"] = "### 💎 ¡¡MINI JACKPOT DEL SERVIDOR!! 💎"
            res["accent_color"] = 16766720
            modify_server_jackpot(-mini_amount)
            _bot_log(f"🎰 [MINI JACKPOT] ¡{uid} ha ganado el mini bote (25%) de {mini_amount:,} Porros!")

        if res["payout"] > 0:
            modify_balance(uid, cash_delta=res["payout"])

        if res["net"] < 0:
            loss = abs(res["net"])
            feed = max(1, int(loss * JACKPOT_FEED_PERCENT))
            modify_server_jackpot(feed)

        updated_bal = get_balance(uid)
        return True, "OK", res, updated_bal


# ==========================================
# VISTAS INTERACTIVAS DISCORD COMPONENTS V2
# ==========================================

class SlotsPlayAgainButton(Button):
    def __init__(self, bet: int, user_id: str):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="Play Again",
            custom_id=f"slots:play-again:{bet}:{user_id}",
        )
        self.bet = bet
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        await handle_slots_play_again(interaction, self.custom_id)


class SlotsPayoutsButton(Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Payouts",
            custom_id="slots:payouts",
        )

    async def callback(self, interaction: discord.Interaction):
        await handle_slots_payouts(interaction)


class SlotsFreeSpinButton(Button):
    def __init__(self, bet: int, user_id: str, remaining: int, multiplier: int = 2, total_won: int = 0):
        super().__init__(
            style=discord.ButtonStyle.success if remaining in (5, 8, 12) else discord.ButtonStyle.primary,
            label=f"🌀 Tirada Gratis ({remaining} restantes)",
            custom_id=f"slots:free-spin:{user_id}:{bet}:{remaining}:{multiplier}:{total_won}",
        )
        self.bet = bet
        self.user_id = user_id
        self.remaining = remaining
        self.multiplier = multiplier
        self.total_won = total_won

    async def callback(self, interaction: discord.Interaction):
        await handle_slots_free_spin(interaction, self.custom_id)


class SlotsLayoutView(LayoutView):
    """Vista interactiva nativa 5x3 con Discord Components V2."""

    def __init__(
        self,
        result: Dict[str, Any],
        user_id: str,
        bet: int,
        remaining_free_spins: int = 0,
        total_bonus_won: int = 0,
    ):
        super().__init__(timeout=300.0)
        self.result = result
        self.user_id = str(user_id)
        self.bet = bet
        self.remaining_free_spins = remaining_free_spins
        self.total_bonus_won = total_bonus_won

        grid = result["grid"]
        grid_lines = []
        for row in grid:
            grid_lines.append(" ".join(SLOT_SYMBOLS[k]["emoji"] for k in row))
        grid_text = "\n".join(grid_lines)

        content_parts = [grid_text]

        if result.get("winning_lines"):
            lines_header = "**Winning Lines:**" if len(result["winning_lines"]) > 1 else "**Winning Line:**"
            content_parts.append("\n" + lines_header)
            for wl in result["winning_lines"]:
                content_parts.append(f"• {wl['emoji']} {wl['line']} (×{wl['mult']})")

        if result.get("jackpot_won", 0) > 0:
            jp_title = "¡GRAND JACKPOT RECLAMADO!" if result.get("jackpot_type") == "grand" else "¡MINI JACKPOT (25%) RECLAMADO!"
            content_parts.append(f"\n💥 **{jp_title}** {PORRO_EMOJI}{result['jackpot_won']:,}")

        if result.get("free_spins_triggered") and not result.get("is_free_spin"):
            sc_c = result.get("scatter_count", 3)
            fs_c = result.get("free_spins_count", 5)
            content_parts.append(
                f"\n🎉 **¡BONUS DESBLOQUEADO!** {sc_c} Scatters <:Porro:1535685303317172305> en pantalla.\n"
                f"¡Premio y **{fs_c} Tiradas Gratis (Free Spins)** con multiplicador **×2**!"
            )
        elif result.get("is_free_spin"):
            if result.get("retrigger"):
                content_parts.append("\n⚡ **¡RE-TRIGGER!** +3 Tiradas Gratis adicionales.")
            if remaining_free_spins > 0:
                content_parts.append(
                    f"\n🌀 **Tiradas restantes:** **{remaining_free_spins}** (Multiplicador ×2)\n"
                    f"💰 **Bonus acumulado:** {PORRO_EMOJI}**{total_bonus_won:,}**"
                )
            else:
                content_parts.append(
                    f"\n🌟 **¡RONDA DE BONUS COMPLETADA!**\n"
                    f"💰 **Ganancia total acreditada:** {PORRO_EMOJI}**{total_bonus_won:,}** Porros"
                )

        payout_str = f"{result['payout']:,}"
        content_parts.append(f"\n**Payout:** {PORRO_EMOJI}{payout_str}")

        body_text = "\n".join(content_parts)

        if result.get("free_spins_triggered") and not result.get("is_free_spin"):
            fs_c = result.get("free_spins_count", 5)
            fs_btn = SlotsFreeSpinButton(bet, self.user_id, remaining=fs_c, multiplier=2, total_won=0)
            payouts_btn = SlotsPayoutsButton()
            action_row = ActionRow(fs_btn, payouts_btn)
        elif result.get("is_free_spin") and remaining_free_spins > 0:
            fs_btn = SlotsFreeSpinButton(
                bet,
                self.user_id,
                remaining=remaining_free_spins,
                multiplier=2,
                total_won=total_bonus_won,
            )
            payouts_btn = SlotsPayoutsButton()
            action_row = ActionRow(fs_btn, payouts_btn)
        else:
            play_again_btn = SlotsPlayAgainButton(bet, self.user_id)
            payouts_btn = SlotsPayoutsButton()
            action_row = ActionRow(play_again_btn, payouts_btn)

        container = Container(
            TextDisplay(result["title"]),
            Separator(spacing=SeparatorSpacing.small, visible=True),
            TextDisplay(body_text),
            Separator(spacing=SeparatorSpacing.small, visible=True),
            action_row,
            accent_color=result["accent_color"],
        )
        self.add_item(container)


async def handle_slots_play_again(interaction: discord.Interaction, custom_id: str) -> None:
    """Procesa el botón 'Play Again' validando titularidad y fondos."""
    try:
        parts = custom_id.split(":")
        if len(parts) >= 4:
            bet = int(parts[2])
            allowed_user_id = parts[3]
        else:
            bet = 100
            allowed_user_id = str(interaction.user.id)
    except Exception:
        bet = 100
        allowed_user_id = str(interaction.user.id)

    if str(interaction.user.id) != str(allowed_user_id):
        await interaction.response.send_message(
            "❌ Solo quien inició esta tirada puede usar este botón. Usa `/slots` para jugar con tu saldo.",
            ephemeral=True,
        )
        return

    ok, err_msg, res, bal = handle_slots_spin(interaction.user.id, bet)
    if not ok:
        await interaction.response.send_message(
            f"❌ {err_msg}\n💡 Usa `/trabajar` para conseguir más Porros.",
            ephemeral=True,
        )
        return

    new_view = SlotsLayoutView(res, str(interaction.user.id), bet)
    await interaction.response.edit_message(view=new_view)


async def handle_slots_free_spin(interaction: discord.Interaction, custom_id: str) -> None:
    """Procesa una tirada gratis de la ronda de bonus sin coste alguno para el usuario."""
    try:
        parts = custom_id.split(":")
        allowed_user_id = parts[2]
        bet = int(parts[3])
        remaining = int(parts[4])
        multiplier = float(parts[5])
        total_bonus_won = int(parts[6])
    except Exception:
        await interaction.response.send_message("❌ Datos de tirada gratis inválidos.", ephemeral=True)
        return

    if str(interaction.user.id) != str(allowed_user_id):
        await interaction.response.send_message(
            "❌ Solo quien desbloqueó esta ronda de Free Spins puede jugarla.",
            ephemeral=True,
        )
        return

    if remaining <= 0:
        await interaction.response.send_message("❌ No te quedan tiradas gratis en esta ronda.", ephemeral=True)
        return

    with ECONOMY_LOCK:
        grid = slot_engine.spin_grid()
        res = slot_engine.evaluate(grid, bet, multiplier=multiplier, is_free_spin=True)

        if res.get("free_spins_triggered"):
            remaining += 3
            res["retrigger"] = True

        new_remaining = remaining - 1
        spin_payout = res["payout"]
        new_total_won = total_bonus_won + spin_payout

        if spin_payout > 0:
            modify_balance(interaction.user.id, cash_delta=spin_payout)

        res["is_free_spin"] = True
        res["remaining_free_spins"] = new_remaining
        res["total_bonus_won"] = new_total_won

        if new_remaining > 0:
            res["title"] = f"### 🌀 Tirada Gratis (×{int(multiplier)})"
            res["accent_color"] = 10181046
        else:
            res["title"] = "### 🏆 ¡¡FIN DE LA RONDA DE FREE SPINS!! 🏆"
            res["accent_color"] = 16766720

    new_view = SlotsLayoutView(
        res,
        str(interaction.user.id),
        bet,
        remaining_free_spins=new_remaining,
        total_bonus_won=new_total_won,
    )
    await interaction.response.edit_message(view=new_view)


async def handle_slots_payouts(interaction: discord.Interaction) -> None:
    """Responde efímeramente con la tabla de multiplicadores y líneas de pago."""
    text = build_payouts_text()
    await interaction.response.send_message(text, ephemeral=True)


async def handle_slots_interaction(interaction: discord.Interaction) -> bool:
    """Intermediario para capturar pulsaciones de botones de slots si la vista no estaba en memoria."""
    if interaction.type != discord.InteractionType.component:
        return False

    custom_id = interaction.data.get("custom_id", "")
    if custom_id.startswith("slots:play-again:"):
        await handle_slots_play_again(interaction, custom_id)
        return True
    elif custom_id.startswith("slots:free-spin:"):
        await handle_slots_free_spin(interaction, custom_id)
        return True
    elif custom_id == "slots:payouts":
        await handle_slots_payouts(interaction)
        return True

    return False


# ==========================================
# 8. CASINO NATIVO: BLACKJACK 21
# ==========================================

BJ_SUITS = ["♠️", "♥️", "♦️", "♣️"]
BJ_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]


def format_bj_card(card: Tuple[str, str]) -> str:
    """Devuelve la representación visual de una carta, ej: 'A♠️', '10♦️'."""
    suit, rank = card
    return f"{rank}{suit}"


def get_bj_card_value(card: Tuple[str, str]) -> int:
    """Devuelve el valor numérico base de una carta (As cuenta como 11 aquí)."""
    _, rank = card
    if rank in ("J", "Q", "K"):
        return 10
    elif rank == "A":
        return 11
    else:
        return int(rank)


class BlackjackHand:
    """Mano de cartas de Blackjack con evaluación dinámica de Ases flexibles y detección de Blackjack natural."""

    def __init__(self, cards: Optional[List[Tuple[str, str]]] = None):
        self.cards: List[Tuple[str, str]] = list(cards) if cards else []

    def add_card(self, card: Tuple[str, str]) -> None:
        self.cards.append(card)

    @property
    def value(self) -> int:
        total = 0
        aces = 0
        for card in self.cards:
            total += get_bj_card_value(card)
            if card[1] == "A":
                aces += 1
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    @property
    def is_soft(self) -> bool:
        total = 0
        aces = 0
        for card in self.cards:
            total += get_bj_card_value(card)
            if card[1] == "A":
                aces += 1
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return aces > 0 and total <= 21

    @property
    def is_blackjack(self) -> bool:
        """Blackjack natural inicial: exactamente 2 cartas sumando 21."""
        return len(self.cards) == 2 and self.value == 21

    @property
    def is_bust(self) -> bool:
        return self.value > 21

    def format_cards(self, hide_first: bool = False) -> str:
        """Formatea las cartas como '[ 🂠 ? ] [ K♠️ ]' o '[ A♣️ ] [ 8♥️ ]'."""
        if not self.cards:
            return "[ Mano vacía ]"
        if hide_first:
            parts = ["[ 🂠 ? ]"]
            for c in self.cards[1:]:
                parts.append(f"[ {format_bj_card(c)} ]")
            return " ".join(parts)
        return " ".join(f"[ {format_bj_card(c)} ]" for c in self.cards)

    def format_score(self, hide_first: bool = False) -> str:
        """Devuelve el texto descriptivo de la puntuación."""
        if hide_first:
            if len(self.cards) > 1:
                vis_val = get_bj_card_value(self.cards[1])
                return f"{vis_val} + ?"
            return "?"
        if self.is_blackjack:
            return "21 (Blackjack)"
        if self.is_bust:
            return f"{self.value} (Bust)"
        if self.is_soft and self.value < 21:
            return f"{self.value} (Soft)"
        return str(self.value)


class BlackjackEngine:
    """Motor de Blackjack con zapato de 6 barajas (312 cartas) y rebarajado automático al bajar de 52 cartas."""

    def __init__(self, num_decks: int = 6):
        self.num_decks = num_decks
        self.cards: List[Tuple[str, str]] = []
        self.reset_shoe()

    def reset_shoe(self) -> None:
        single_deck = [(suit, rank) for suit in BJ_SUITS for rank in BJ_RANKS]
        self.cards = single_deck * self.num_decks
        random.shuffle(self.cards)

    def draw(self) -> Tuple[str, str]:
        if len(self.cards) < 52:
            self.reset_shoe()
        return self.cards.pop()

    def play_dealer_turn(self, dealer_hand: BlackjackHand) -> None:
        """El crupier debe pedir con 16 o menos y plantarse obligatoriamente con 17 o más (S17)."""
        while dealer_hand.value < 17:
            dealer_hand.add_card(self.draw())


# Instancia global del zapato para simular la mesa persistente de casino
blackjack_engine = BlackjackEngine(num_decks=6)

# Registro de partidas activas para impedir partidas simultáneas por el mismo usuario
ACTIVE_BLACKJACK_GAMES: Dict[int, Any] = {}


def parse_blackjack_bet(user_id: Any, apuesta_str: str) -> Tuple[bool, int, str]:
    """Valida y calcula el monto de la apuesta en Porros (mínimo 50 o 'all'/'todo'/'max')."""
    bal = get_balance(user_id)
    cash = bal["cash"]
    clean_str = str(apuesta_str).strip().lower()

    if clean_str in ("all", "todo", "max"):
        bet = cash
    else:
        try:
            bet = int(clean_str)
        except ValueError:
            return False, 0, "Cantidad de apuesta inválida. Debe ser un número entero mayor o igual a 50 o 'all'/'todo'."

    if bet < 50:
        return False, 0, f"La apuesta mínima en Blackjack es de 50 Porros ({PORRO_EMOJI})."

    if cash < bet:
        return False, 0, f"No tienes suficientes Porros en efectivo ({cash:,} disponibles). Usa `/trabajar` o retira de tu `/banco`."

    return True, bet, ""


def build_blackjack_embed(
    user: Union[discord.User, discord.Member],
    player_hand: BlackjackHand,
    dealer_hand: BlackjackHand,
    bet: int,
    dealer_revealed: bool = False,
    result_text: Optional[str] = None,
    color: int = 0x3498DB,
    auto_stand: bool = False,
) -> discord.Embed:
    """Construye el Embed de alta fidelidad visual para la partida de Blackjack."""
    embed = discord.Embed(
        title="🎰 Blackjack 21 — Casino Asistente",
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    desc_lines = []
    if auto_stand:
        desc_lines.append("⏱️ *Turno resuelto automáticamente por inactividad de 60s (Auto-Stand).*")
    if result_text:
        desc_lines.append(result_text)
    else:
        desc_lines.append("Tu turno: Elige si **Pedir**, **Plantarte** o **Doblar** tu apuesta.")
    embed.description = "\n\n".join(desc_lines)

    dealer_cards_str = dealer_hand.format_cards(hide_first=not dealer_revealed)
    dealer_score_str = dealer_hand.format_score(hide_first=not dealer_revealed)
    embed.add_field(
        name="🤵 Crupier (Casa)",
        value=f"{dealer_cards_str}\n**Puntuación:** `{dealer_score_str}`",
        inline=False,
    )

    player_cards_str = player_hand.format_cards()
    player_score_str = player_hand.format_score()
    embed.add_field(
        name=f"🧑 {user.display_name} (Jugador)",
        value=f"{player_cards_str}\n**Puntuación:** `{player_score_str}`",
        inline=False,
    )

    embed.add_field(
        name="💰 Apuesta",
        value=f"{PORRO_EMOJI} **{bet:,}** Porros",
        inline=True,
    )
    embed.add_field(
        name="🎰 Bote Acumulado",
        value=f"{PORRO_EMOJI} **{get_server_jackpot():,}** Porros",
        inline=True,
    )

    embed.set_footer(text="Blackjack 21 • Casino Oficial • 6 Barajas (S17)")
    if hasattr(user, "display_avatar") and user.display_avatar:
        embed.set_author(name=user.display_name, icon_url=str(user.display_avatar.url))
    return embed


class BlackjackView(discord.ui.View):
    """Vista interactiva nativa con botones para Blackjack 21 con timeout de 60s y auto-stand."""

    def __init__(
        self,
        user_id: int,
        user: Union[discord.User, discord.Member],
        bet: int,
        engine: Optional[BlackjackEngine] = None,
        player_hand: Optional[BlackjackHand] = None,
        dealer_hand: Optional[BlackjackHand] = None,
    ):
        super().__init__(timeout=60.0)
        self.user_id = user_id
        self.user = user
        self.bet = bet
        self.engine = engine or blackjack_engine
        self.player_hand = player_hand or BlackjackHand()
        self.dealer_hand = dealer_hand or BlackjackHand()
        self.message: Optional[discord.Message] = None
        self.resolved = False
        self._lock = asyncio.Lock()

        # Chequeo inicial para el botón Doblar: solo con 2 cartas y si tiene efectivo para igualar
        bal = get_balance(self.user_id)
        if bal["cash"] < self.bet or len(self.player_hand.cards) != 2:
            self.set_double_disabled(True)

    def set_double_disabled(self, disabled: bool) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "bj:double":
                child.disabled = disabled

    def disable_all_buttons(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Esta partida de Blackjack no es tuya. Usa `/blackjack` para iniciar tu propia mesa.",
                ephemeral=True,
            )
            return False
        return True

    async def do_hit(self, interaction: discord.Interaction) -> None:
        async with self._lock:
            if self.resolved:
                return

            card = self.engine.draw()
            self.player_hand.add_card(card)
            self.set_double_disabled(True)

            if self.player_hand.is_bust:
                self.resolved = True
                self.disable_all_buttons()
                jackpot_feed = max(1, int(self.bet * JACKPOT_FEED_PERCENT))
                with ECONOMY_LOCK:
                    modify_server_jackpot(jackpot_feed)
                    ACTIVE_BLACKJACK_GAMES.pop(self.user_id, None)

                embed = build_blackjack_embed(
                    user=self.user,
                    player_hand=self.player_hand,
                    dealer_hand=self.dealer_hand,
                    bet=self.bet,
                    dealer_revealed=True,
                    result_text=(
                        f"💥 **¡Te has pasado! (Bust: {self.player_hand.value})**\n"
                        f"Has perdido **{self.bet:,}** Porros ({PORRO_EMOJI}).\n"
                        f"🎰 Se han añadido **+{jackpot_feed:,}** Porros al bote del servidor."
                    ),
                    color=0xE74C3C,
                )
                await interaction.response.edit_message(embed=embed, view=self)
                self.stop()
                return

            if self.player_hand.value == 21:
                await self._resolve_dealer_and_finish(interaction)
                return

            embed = build_blackjack_embed(
                user=self.user,
                player_hand=self.player_hand,
                dealer_hand=self.dealer_hand,
                bet=self.bet,
                dealer_revealed=False,
                result_text="Has pedido carta. ¿Deseas **Pedir** otra o **Plantarte**?",
                color=0x3498DB,
            )
            await interaction.response.edit_message(embed=embed, view=self)

    async def do_stand(self, interaction: discord.Interaction) -> None:
        async with self._lock:
            if self.resolved:
                return
            await self._resolve_dealer_and_finish(interaction)

    async def do_double(self, interaction: discord.Interaction) -> None:
        async with self._lock:
            if self.resolved:
                return

            if len(self.player_hand.cards) != 2:
                await interaction.response.send_message(
                    "❌ Solo puedes doblar la apuesta en tu primer turno con exactamente 2 cartas.",
                    ephemeral=True,
                )
                return

            bal = get_balance(self.user_id)
            if bal["cash"] < self.bet:
                await interaction.response.send_message(
                    f"❌ No tienes suficientes Porros en efectivo para doblar la apuesta ({bal['cash']:,} disponibles, necesitas {self.bet:,}).",
                    ephemeral=True,
                )
                self.set_double_disabled(True)
                try:
                    await interaction.message.edit(view=self)
                except Exception:
                    pass
                return

            # Descontar la apuesta adicional para duplicar
            with ECONOMY_LOCK:
                modify_balance(self.user_id, cash_delta=-self.bet)
            self.bet *= 2
            self.set_double_disabled(True)

            # Recibir exactamente 1 carta
            card = self.engine.draw()
            self.player_hand.add_card(card)

            if self.player_hand.is_bust:
                self.resolved = True
                self.disable_all_buttons()
                jackpot_feed = max(1, int(self.bet * JACKPOT_FEED_PERCENT))
                with ECONOMY_LOCK:
                    modify_server_jackpot(jackpot_feed)
                    ACTIVE_BLACKJACK_GAMES.pop(self.user_id, None)

                embed = build_blackjack_embed(
                    user=self.user,
                    player_hand=self.player_hand,
                    dealer_hand=self.dealer_hand,
                    bet=self.bet,
                    dealer_revealed=True,
                    result_text=(
                        f"💥 **¡Doblaste y te has pasado! (Bust: {self.player_hand.value})**\n"
                        f"Has perdido **{self.bet:,}** Porros ({PORRO_EMOJI}).\n"
                        f"🎰 Se han añadido **+{jackpot_feed:,}** Porros al bote del servidor."
                    ),
                    color=0xE74C3C,
                )
                await interaction.response.edit_message(embed=embed, view=self)
                self.stop()
                return

            # Resolver crupier inmediatamente tras doblar
            await self._resolve_dealer_and_finish(interaction)

    @discord.ui.button(label="🃏 Pedir", style=discord.ButtonStyle.primary, custom_id="bj:hit")
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.do_hit(interaction)

    @discord.ui.button(label="🛑 Plantarse", style=discord.ButtonStyle.danger, custom_id="bj:stand")
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.do_stand(interaction)

    @discord.ui.button(label="⚡ Doblar", style=discord.ButtonStyle.success, custom_id="bj:double")
    async def double(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.do_double(interaction)

    async def _resolve_dealer_and_finish(
        self,
        interaction: Optional[discord.Interaction] = None,
        auto_stand: bool = False,
    ) -> None:
        self.resolved = True
        self.disable_all_buttons()

        # Turno del Crupier
        self.engine.play_dealer_turn(self.dealer_hand)

        player_score = self.player_hand.value
        dealer_score = self.dealer_hand.value
        dealer_bust = self.dealer_hand.is_bust

        payout = 0
        jackpot_feed = 0

        with ECONOMY_LOCK:
            if dealer_bust:
                win_net = self.bet
                payout = self.bet * 2
                modify_balance(self.user_id, cash_delta=payout)
                res_msg = (
                    f"🎉 **¡El crupier se ha pasado! (Bust: {dealer_score})**\n"
                    f"¡Has ganado **+{win_net:,}** Porros limpios ({PORRO_EMOJI})!\n"
                    f"💰 Total ingresado en efectivo: **{payout:,}** Porros."
                )
                color = 0x2ECC71
            elif player_score > dealer_score:
                win_net = self.bet
                payout = self.bet * 2
                modify_balance(self.user_id, cash_delta=payout)
                res_msg = (
                    f"🎉 **¡Has ganado a la casa!**\n"
                    f"Tu puntuación (**{player_score}**) supera a la del crupier (**{dealer_score}**).\n"
                    f"¡Has ganado **+{win_net:,}** Porros limpios ({PORRO_EMOJI})!\n"
                    f"💰 Total ingresado en efectivo: **{payout:,}** Porros."
                )
                color = 0x2ECC71
            elif player_score == dealer_score:
                payout = self.bet
                modify_balance(self.user_id, cash_delta=payout)
                res_msg = (
                    f"🤝 **¡Empate (Push)!**\n"
                    f"Mismo puntaje (**{player_score}**). Se te devuelve tu apuesta íntegra de **{payout:,}** Porros ({PORRO_EMOJI})."
                )
                color = 0xF1C40F
            else:
                jackpot_feed = max(1, int(self.bet * JACKPOT_FEED_PERCENT))
                modify_server_jackpot(jackpot_feed)
                res_msg = (
                    f"💀 **La casa gana.**\n"
                    f"El crupier (**{dealer_score}**) supera tu puntuación (**{player_score}**).\n"
                    f"Has perdido **{self.bet:,}** Porros ({PORRO_EMOJI}).\n"
                    f"🎰 Se han añadido **+{jackpot_feed:,}** Porros al bote del servidor."
                )
                color = 0xE74C3C

            ACTIVE_BLACKJACK_GAMES.pop(self.user_id, None)

        embed = build_blackjack_embed(
            user=self.user,
            player_hand=self.player_hand,
            dealer_hand=self.dealer_hand,
            bet=self.bet,
            dealer_revealed=True,
            result_text=res_msg,
            color=color,
            auto_stand=auto_stand,
        )

        if interaction and not interaction.response.is_done():
            await interaction.response.edit_message(embed=embed, view=self)
        elif self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass
        self.stop()

    async def on_timeout(self) -> None:
        async with self._lock:
            if self.resolved:
                return
            await self._resolve_dealer_and_finish(interaction=None, auto_stand=True)
