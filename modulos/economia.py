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
from collections import Counter
from datetime import datetime, timezone, timedelta
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

# Textos de delitos (/crimen) inspirados en el lore del servidor
CRIME_SUCCESS_MESSAGES = [
    "Interceptaste un furgón blindado con cargamento de GPUs RTX 5060 camino a la torre AM5 y colocaste el botín en el mercado negro.",
    "Falsificaste un acta de El Tribunal Gaming para cobrar los derechos de autor de los veredictos sin que los Magistrados se enteraran.",
    "Entraste de madrugada al almacén clandestino de UnbelievaBoat y vaciaste la cámara acorazada antes de su jubilación.",
    "Hackeaste la máquina de bebidas de la sala de voz y te llevaste un palé entero de Monster Blanco sin dejar huellas.",
    "Organizaste una timba ilegal de ajedrez rápido con Stockfish trucado y desplumaste a tres incautos seguidos.",
    "Desviaste un contenedor de merchandising exclusivo de manhwas en el puerto y lo vendiste a precio de coleccionista.",
    "Clonaste la tarjeta de acceso VIP del Casino Central Sanvi y diste el cambiazo en la caja de fichas antes del relevo.",
    "Secuestraste temporalmente el bot de música en #llamada y cobraste rescate en Porros para quitar el bucle de reggaetón.",
    "Manipulaste las cuotas de una apuesta clandestina de Brawl Stars Ranked y te embolsaste toda la banca.",
    "Te colaste en los servidores de Cakey Bot disfrazado de técnico de mantenimiento y saliste con los bolsillos llenos.",
    "Vendiste pases VIP falsos para la premiere del próximo arco de Solo Leveling y desapareciste en patinete eléctrico.",
    "Abiste la caja fuerte de la taberna del servidor con una horquilla y un clip mientras todos debatían en #general.",
]

CRIME_FAIL_MESSAGES = [
    "Intentaste puentear la alarma del Casino Central Sanvi, pero activaste los láseres y la patrulla te confiscó la fianza.",
    "Fuiste a vender GPUs de contrabando y el comprador resultó ser un inspector encubierto de El Tribunal Gaming.",
    "Te quedaste dormido esperando a que abriera la bóveda del banco y te despertaron las sirenas de la redada policial.",
    "Tropezaste con el cable Ethernet del servidor en plena huida, desconectaste el router y te atraparon en el suelo.",
    "Intentaste sobornar al guardia de seguridad con Porros de chocolate y te cayó una multa ejemplar por desacato.",
    "Dejaste tu cuenta de Discord abierta en el ordenador del golpe y la policía te identificó en menos de dos minutos.",
    "La bolsa con el botín tenía un agujero, fuiste dejando un rastro de Porros hasta tu casa y te llamaron al timbre.",
    "Intentaste hackear el cajero automático usando un script copiado sin leer y bloqueaste tu propia cuenta con multa.",
    "El conductor de la furgoneta de escape se puso a jugar una ranked de Brawl Stars y os acorralaron en la rotonda.",
    "Confundiste la puerta trasera de la joyería con la comisaría del barrio y entraste directo al calabozo.",
    "Un dron de vigilancia te grabó en 4K intentando forzar la máquina expendedora de Monster Blanco.",
    "Sonó tu micrófono abierto en mitad del golpe sigiloso y los agentes te esperaron en la salida con la receta lista.",
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
    "monster_blanco": {
        "id": "monster_blanco",
        "name": "🥤 Monster Blanco",
        "price": 25000,
        "type": "consumable",
        "description": "Bebida energética suprema. Al usarla con /usar resetea al instante tus cooldowns de /trabajar, /crimen y /robar.",
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
        "description": "Pase temporal con boost de +5% de XP en Cakey Bot durante 24 horas (se guarda en /inventario y se activa con /usar).",
        "unique": False,
    },
    "pase_semanal_xp": {
        "id": "pase_semanal_xp",
        "name": "🔥 Pase Semanal de XP",
        "price": 75000,
        "type": "role",
        "role_id": "1549880941466357940",
        "role_name": "🔥 Pase Semanal de XP",
        "duration_hours": 168,
        "description": "Pase temporal con boost de +10% de XP en Cakey Bot durante 7 días (se guarda en /inventario y se activa con /usar).",
        "unique": False,
    },
    "pase_mensual_xp": {
        "id": "pase_mensual_xp",
        "name": "💠 Pase Mensual de XP",
        "price": 250000,
        "type": "role",
        "role_id": "1549880942909329539",
        "role_name": "💠 Pase Mensual de XP",
        "duration_hours": 720,
        "description": "Pase temporal con boost de +15% de XP en Cakey Bot durante 30 días (se guarda en /inventario y se activa con /usar).",
        "unique": False,
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
                "last_crime": None,
                "last_rob": None,
                "last_salary": None,
                "inventory": [],
                "active_buffs": [],
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
                ("last_crime", None),
                ("last_rob", None),
                ("last_salary", None),
                ("inventory", []),
                ("active_buffs", []),
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
                "last_crime": None,
                "last_rob": None,
                "last_salary": None,
                "inventory": [],
                "active_buffs": [],
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


LEVEL_ROLE_MULTIPLIERS = [
    (
        1.40,
        "👑 +40% Bono Nivel",
        {"1543230295770267658", "1543230392348446750", "1543230459373293718"},
        ["mítico", "mitico", "ancestral", "supremo"],
    ),
    (
        1.30,
        "🌟 +30% Bono Nivel",
        {"1543230221308657704"},
        ["legendario"],
    ),
    (
        1.25,
        "⚔️ +25% Bono Nivel",
        {"1543229770437628075", "1543230152295452833"},
        ["élite", "elite", "maestro"],
    ),
    (
        1.20,
        "🌸 +20% Bono Nivel",
        {"1543228972354109464", "1543229622869561477"},
        ["experimentado", "alto rango"],
    ),
    (
        1.10,
        "🔷 +10% Bono Nivel",
        {"1543009740001640539", "1543226107929567343"},
        ["rango medio", "veterano"],
    ),
]


def get_level_role_multiplier(
    member: Optional[Any] = None,
    user_roles: Optional[List[str]] = None,
) -> Tuple[float, Optional[str]]:
    """
    Evalúa los roles del miembro (por nombre o ID oficial) y devuelve el multiplicador
    más alto aplicable para /trabajar y /crimen: (multiplicador, etiqueta_bono).
    """
    role_ids = set()
    role_names_lower = []

    if member is not None and hasattr(member, "roles"):
        for r in member.roles:
            rid = str(getattr(r, "id", ""))
            rname = str(getattr(r, "name", "")).lower()
            if rid:
                role_ids.add(rid)
            if rname:
                role_names_lower.append(rname)

    if user_roles:
        for r in user_roles:
            r_str = str(r).strip()
            role_ids.add(r_str)
            role_names_lower.append(r_str.lower())

    if not role_ids and not role_names_lower:
        return 1.0, None

    for mult, label, target_ids, target_kws in LEVEL_ROLE_MULTIPLIERS:
        if role_ids & target_ids:
            return mult, label
        for r_name in role_names_lower:
            if any(kw in r_name for kw in target_kws):
                return mult, label

    return 1.0, None


def can_work(user_id: Any, cooldown_seconds: int = 14400) -> Tuple[bool, float]:
    """Comprueba si un usuario puede trabajar según su cooldown (por defecto 4 horas = 14400s)."""
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
    cooldown_seconds: int = 14400,
    min_reward: int = 1000,
    max_reward: int = 2500,
    member: Optional[Any] = None,
    user_roles: Optional[List[str]] = None,
) -> Tuple[bool, str, int]:
    """Ejecuta una jornada laboral y abona la recompensa con multiplicador de rol de nivel si no está en cooldown."""
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

        base_reward = random.randint(min_reward, max_reward)
        mult, mult_label = get_level_role_multiplier(member, user_roles)
        reward = int(round(base_reward * mult))
        job_story = random.choice(WORK_MESSAGES)
        if mult > 1.0 and mult_label:
            job_story = f"{job_story}\n*(Bono aplicado: **{mult_label}** — Base: {base_reward:,} Porros)*"

        modify_balance(uid, cash_delta=reward)
        data = load_economy_data()
        data["users"][uid]["last_work"] = datetime.now(timezone.utc).isoformat()
        if member is not None and hasattr(member, "name") and member.name:
            data["users"][uid]["username"] = str(member.name)
        save_economy_data(data)

        _bot_log(f"💼 [Trabajo] {uid} ganó {reward:,} Porros (x{mult}) con: '{job_story[:40]}...'")
        return True, job_story, reward


def can_crime(user_id: Any, cooldown_seconds: int = 43200) -> Tuple[bool, float]:
    """Comprueba si un usuario puede cometer un delito (/crimen) según su cooldown (por defecto 12 horas = 43200s)."""
    user = ensure_user(user_id)
    last_crime_str = user.get("last_crime")
    if not last_crime_str:
        return True, 0.0

    try:
        last_crime_dt = datetime.fromisoformat(last_crime_str)
        now = datetime.now(timezone.utc)
        elapsed = (now - last_crime_dt).total_seconds()
        if elapsed >= cooldown_seconds:
            return True, 0.0
        return False, cooldown_seconds - elapsed
    except Exception:
        return True, 0.0


def execute_crime(
    user_id: Any,
    member: Optional[Any] = None,
    user_roles: Optional[List[str]] = None,
    cooldown_seconds: int = 43200,
    min_reward: int = 1800,
    max_reward: int = 3500,
) -> Tuple[bool, str, int]:
    """
    Ejecuta un delito de alto riesgo (/crimen):
    - Cooldown por defecto: 12 horas (43.200s).
    - 50% éxito: gana entre 1.800 y 3.500 Porros base multiplicados por el bono de rol de nivel.
    - 50% fallo: multa del 10% del efectivo (cash) con suelo mínimo de 500 Porros (sin dejar cash negativo).
      El 3% de la multa alimenta el server_jackpot.
    """
    uid = str(user_id)
    with ECONOMY_LOCK:
        allowed, remaining = can_crime(uid, cooldown_seconds)
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
                f"⏳ La policía sigue patrullando tras tu último golpe. Tienes que esperar {time_str} para volver a usar `/crimen`.",
                0,
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        success = random.random() < 0.50

        if success:
            base_reward = random.randint(min_reward, max_reward)
            mult, mult_label = get_level_role_multiplier(member, user_roles)
            reward = int(round(base_reward * mult))
            story = random.choice(CRIME_SUCCESS_MESSAGES)
            bonus_line = f"\n*(Bono aplicado: **{mult_label}** — Base: {base_reward:,} Porros)*" if (mult > 1.0 and mult_label) else ""

            modify_balance(uid, cash_delta=reward)
            data = load_economy_data()
            data["users"][uid]["last_crime"] = now_iso
            if member is not None and hasattr(member, "name") and member.name:
                data["users"][uid]["username"] = str(member.name)
            save_economy_data(data)

            msg = (
                f"🦹 **¡GOLPE CRIMINAL EXITOSO!**\n"
                f"{story}{bonus_line}\n\n"
                f"**Botín conseguido:** {PORRO_EMOJI} **+{reward:,}** Porros"
            )
            _bot_log(f"🦹 [Crimen Exitoso] {uid} ganó {reward:,} Porros (x{mult}).")
            return True, msg, reward
        else:
            bal = get_balance(uid)
            cash = bal["cash"]
            fine = min(cash, max(500, int(round(cash * 0.10)))) if cash > 0 else 0
            story = random.choice(CRIME_FAIL_MESSAGES)

            if fine > 0:
                modify_balance(uid, cash_delta=-fine)
                jackpot_feed = max(1, int(fine * JACKPOT_FEED_PERCENT))
                modify_server_jackpot(jackpot_feed)
            else:
                jackpot_feed = 0

            data = load_economy_data()
            data["users"][uid]["last_crime"] = now_iso
            if member is not None and hasattr(member, "name") and member.name:
                data["users"][uid]["username"] = str(member.name)
            save_economy_data(data)

            if fine > 0:
                fine_text = (
                    f"**Multa confiscada (10%, mín. 500):** {PORRO_EMOJI} **-{fine:,}** Porros\n"
                    f"-# *🎰 +{jackpot_feed:,} Porros enviados al bote acumulado del servidor.*"
                )
            else:
                fine_text = "**Multa:** Te pillaron sin un solo Porro encima, así que te soltaron tras pasar por el calabozo."

            msg = (
                f"🚓 **¡REDADA POLICIAL!**\n"
                f"{story}\n\n"
                f"{fine_text}"
            )
            _bot_log(f"🚓 [Crimen Fallido] {uid} perdió {fine:,} Porros de multa.")
            return False, msg, -fine


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

    # 2. Ítems de Inventario y Consumibles
    embed.add_field(
        name="🎒 Ítems de Inventario y Consumibles",
        value=(
            f"• **🚬 Porro de Oro** — {PORRO_EMOJI} **75,000** Porros\n"
            f"  *Coleccionable de inventario de máximo prestigio y flexeo.*\n"
            f"• **🥤 Monster Blanco** — {PORRO_EMOJI} **25,000** Porros\n"
            f"  *Consumible supremo: úsalo con `/usar` para resetear al instante `/trabajar`, `/crimen` y `/robar`.*"
        ),
        inline=False,
    )

    # 3. Pases de Experiencia (XP)
    embed.add_field(
        name="⚡ Pases y Bonos de Experiencia (XP)",
        value=(
            f"• **⚡ Chute de XP (24h)** — {PORRO_EMOJI} **15,000** Porros\n"
            f"  *Boost temporal de +5% de XP en Cakey Bot durante 24h (se guarda en `/inventario` y se activa con `/usar`).*\n"
            f"• **🔥 Pase Semanal de XP** — {PORRO_EMOJI} **75,000** Porros\n"
            f"  *Boost temporal de +10% de XP en Cakey Bot durante 7 días (se guarda en `/inventario` y se activa con `/usar`).*\n"
            f"• **💠 Pase Mensual de XP** — {PORRO_EMOJI} **250,000** Porros\n"
            f"  *Boost temporal de +15% de XP en Cakey Bot durante 30 días (se guarda en `/inventario` y se activa con `/usar`).*\n"
            f"• **👑 Aura de XP Permanente** — {PORRO_EMOJI} **1,000,000** Porros\n"
            f"  *Pase perpetuo élite con boost de +10% de XP permanente (se asigna al instante).*"
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
                label="🥤 Monster Blanco (25k)",
                value="monster_blanco",
                description="25.000 Porros • Resetea trabajar, crimen y robar",
                emoji="🥤",
            ),
            discord.SelectOption(
                label="⚡ Chute de XP 24h (15k)",
                value="chute_xp",
                description="15.000 Porros • Boost +5% XP por 24h (activar con /usar)",
                emoji="⚡",
            ),
            discord.SelectOption(
                label="🔥 Pase Semanal de XP (75k)",
                value="pase_semanal_xp",
                description="75.000 Porros • Boost +10% XP por 7d (activar con /usar)",
                emoji="🔥",
            ),
            discord.SelectOption(
                label="💠 Pase Mensual de XP (250k)",
                value="pase_mensual_xp",
                description="250.000 Porros • Boost +15% XP por 30d (activar con /usar)",
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

        # Auto-asignación de rol solo para roles permanentes (sin duration_hours)
        role_added = False
        is_temp_or_consumable = bool(
            item_data and (item_data.get("duration_hours") or item_data.get("type") == "consumable")
        )
        if (
            item_data
            and item_data.get("type") == "role"
            and not item_data.get("duration_hours")
            and hasattr(interaction.user, "add_roles")
        ):
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
                name="🎭 Rol Permanente Asignado",
                value=f"¡El rol `{item_data['name']}` ha sido añadido a tu perfil de Discord!",
                inline=False,
            )
        elif is_temp_or_consumable:
            confirm_embed.add_field(
                name="🎒 Guardado en tu Inventario",
                value=(
                    f"**{item_data['name']}** se ha guardado en tu `/inventario`.\n"
                    f"✨ Cuando quieras activarlo o consumirlo, ejecuta **`/usar`**."
                ),
                inline=False,
            )
        confirm_embed.set_footer(text="Gracias por tu compra • Consulta tus objetos con /inventario")

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
# INVENTARIO, /USAR Y EXPIRACIÓN DE BUFFOS
# ==========================================

USABLE_ITEM_KEYS = ("monster_blanco", "chute_xp", "pase_semanal_xp", "pase_mensual_xp")


def use_inventory_item(
    user_id: Any,
    item_key: str,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Consume un artículo activable del inventario del usuario (/usar):
    - 'monster_blanco': elimina 1 unidad y resetea last_work, last_crime y last_rob.
    - Pases temporales de XP ('chute_xp', 'pase_semanal_xp', 'pase_mensual_xp'):
      elimina 1 unidad y registra/extiende su entrada en user['active_buffs'].
    """
    uid = str(user_id)
    key_clean = item_key.strip().lower()

    matched_item = None
    for k in USABLE_ITEM_KEYS:
        it = SHOP_ITEMS.get(k)
        if not it:
            continue
        if k == key_clean or it["name"].lower() == key_clean or k in key_clean:
            matched_item = it
            break

    if not matched_item:
        return (
            False,
            f"❌ El artículo '{item_key}' no es un consumible ni un pase activable con `/usar`.",
            None,
        )

    item_id = matched_item["id"]
    item_name = matched_item["name"]

    with ECONOMY_LOCK:
        user = ensure_user(uid)
        inv = user.setdefault("inventory", [])
        if item_name not in inv:
            return (
                False,
                f"❌ No tienes **{item_name}** en tu `/inventario`. Puedes adquirirlo en `/tienda`.",
                None,
            )

        # Consumir 1 unidad
        inv.remove(item_name)
        now = datetime.now(timezone.utc)

        if item_id == "monster_blanco":
            user["last_work"] = None
            user["last_crime"] = None
            user["last_rob"] = None
            data = load_economy_data()
            save_economy_data(data)
            msg = (
                "🥤 ¡Te has tomado un **Monster Blanco** bien frío!\n"
                "⚡ Tus tiempos de espera de **`/trabajar`**, **`/crimen`** y **`/robar`** han quedado **a cero** al instante."
            )
            _bot_log(f"🥤 [Usar] {uid} consumió Monster Blanco y reseteó sus cooldowns.")
            return True, msg, matched_item

        duration_hours = int(matched_item.get("duration_hours", 0))
        role_id = matched_item.get("role_id")
        active_buffs = user.setdefault("active_buffs", [])

        existing_buff = None
        for b in active_buffs:
            if b.get("item_id") == item_id:
                existing_buff = b
                break

        if existing_buff:
            try:
                curr_exp = datetime.fromisoformat(existing_buff["expires_at"])
                if curr_exp > now:
                    new_exp = curr_exp + timedelta(hours=duration_hours)
                    extended = True
                else:
                    new_exp = now + timedelta(hours=duration_hours)
                    extended = False
            except Exception:
                new_exp = now + timedelta(hours=duration_hours)
                extended = False
            existing_buff["expires_at"] = new_exp.isoformat()
            existing_buff["name"] = item_name
            existing_buff["role_id"] = role_id
        else:
            new_exp = now + timedelta(hours=duration_hours)
            extended = False
            active_buffs.append({
                "item_id": item_id,
                "name": item_name,
                "role_id": role_id,
                "activated_at": now.isoformat(),
                "expires_at": new_exp.isoformat(),
            })

        data = load_economy_data()
        save_economy_data(data)

        total_rem_hours = max(1, int(round((new_exp - now).total_seconds() / 3600)))
        if extended:
            msg = (
                f"⚡ ¡Has extendido tu **{item_name}** por **+{duration_hours}h** adicionales!\n"
                f"⏳ **Duración total restante:** ~**{total_rem_hours} horas**."
            )
        else:
            msg = (
                f"✨ ¡Has activado **{item_name}** desde tu inventario!\n"
                f"⏳ **Duración activa:** **{duration_hours} horas**."
            )
        _bot_log(f"⚡ [Usar] {uid} activó '{item_name}' hasta {new_exp.isoformat()}.")
        return True, msg, matched_item


def check_and_expire_buffs(now_dt: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Recorre los usuarios en datos/economia.json, detecta pases temporales de XP cuya
    fecha expires_at haya vencido (<= now_dt), los elimina de active_buffs y devuelve
    la lista de buffs expirados para retirar sus roles en Discord.
    """
    now = now_dt or datetime.now(timezone.utc)
    expired_list: List[Dict[str, Any]] = []

    with ECONOMY_LOCK:
        data = load_economy_data()
        users = data.get("users", {})
        modified = False

        for uid, udata in users.items():
            buffs = udata.get("active_buffs")
            if not buffs or not isinstance(buffs, list):
                continue

            kept_buffs = []
            for b in buffs:
                exp_str = b.get("expires_at")
                if not exp_str:
                    modified = True
                    continue
                try:
                    exp_dt = datetime.fromisoformat(exp_str)
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    modified = True
                    continue

                if exp_dt <= now:
                    expired_list.append({
                        "user_id": str(uid),
                        "item_id": b.get("item_id"),
                        "role_id": b.get("role_id"),
                        "name": b.get("name"),
                        "expires_at": exp_str,
                    })
                    modified = True
                else:
                    kept_buffs.append(b)

            if len(kept_buffs) != len(buffs):
                udata["active_buffs"] = kept_buffs
                modified = True

        if modified:
            save_economy_data(data)

    return expired_list


def _format_remaining_time(expires_at_str: str, now: Optional[datetime] = None) -> str:
    now_dt = now or datetime.now(timezone.utc)
    try:
        exp_dt = datetime.fromisoformat(expires_at_str)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        rem_sec = max(0, int((exp_dt - now_dt).total_seconds()))
        days = rem_sec // 86400
        hours = (rem_sec % 86400) // 3600
        mins = (rem_sec % 3600) // 60
        if days > 0:
            return f"{days}d {hours}h restantes"
        if hours > 0:
            return f"{hours}h {mins}m restantes"
        return f"{mins}m restantes"
    except Exception:
        return "Tiempo desconocido"


def build_inventory_embed(
    user_id: Any,
    display_name: str,
    avatar_url: Optional[str] = None,
) -> discord.Embed:
    """Construye el embed de /inventario detallando objetos agrupados, roles permanentes y pases XP activos."""
    check_and_expire_buffs()
    user = ensure_user(user_id)
    bal = get_balance(user_id)
    inv = user.get("inventory", [])
    active_buffs = user.get("active_buffs", [])

    counts = Counter(inv)
    perm_role_names = {
        it["name"]
        for it in SHOP_ITEMS.values()
        if it.get("type") == "role" and not it.get("duration_hours")
    }
    usable_names = {
        SHOP_ITEMS[k]["name"]
        for k in USABLE_ITEM_KEYS
        if k in SHOP_ITEMS
    }

    perm_owned = []
    usable_owned = []
    collectibles_owned = []

    for item_name, qty in counts.items():
        qty_str = f" **×{qty}**" if qty > 1 else ""
        if item_name in perm_role_names:
            perm_owned.append(f"• {item_name}")
        elif item_name in usable_names:
            usable_owned.append(f"• {item_name}{qty_str} *(usable con `/usar`)*")
        else:
            collectibles_owned.append(f"• {item_name}{qty_str}")

    embed = discord.Embed(
        title=f"🎒 Inventario y Pases de {display_name}",
        description=(
            f"💵 **Efectivo:** {PORRO_EMOJI} **{bal['cash']:,}** | "
            f"🏦 **Banco:** {PORRO_EMOJI} **{bal['bank']:,}** | "
            f"💎 **Total:** {PORRO_EMOJI} **{bal['total']:,}**"
        ),
        color=0x9B59B6,
        timestamp=datetime.now(timezone.utc),
    )
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    embed.add_field(
        name="🎭 Roles Permanentes Adquiridos",
        value="\n".join(perm_owned) if perm_owned else "*Ningún rol permanente en propiedad.*",
        inline=False,
    )
    embed.add_field(
        name="🧪 Consumibles y Pases Listos para `/usar`",
        value="\n".join(usable_owned) if usable_owned else "*No tienes consumibles ni pases pendientes de activar.*",
        inline=False,
    )
    embed.add_field(
        name="🏆 Coleccionables y Trofeos",
        value="\n".join(collectibles_owned) if collectibles_owned else "*Sin coleccionables en la vitrina.*",
        inline=False,
    )

    now = datetime.now(timezone.utc)
    if active_buffs:
        buff_lines = []
        for b in active_buffs:
            b_name = b.get("name", b.get("item_id", "Pase XP"))
            rem_str = _format_remaining_time(b.get("expires_at", ""), now)
            buff_lines.append(f"• **{b_name}** — ⏳ `{rem_str}`")
        buff_val = "\n".join(buff_lines)
    else:
        buff_val = "*Ningún pase temporal de XP activo en este momento.*"

    embed.add_field(
        name="⚡ Pases Temporales de XP Activos",
        value=buff_val,
        inline=False,
    )
    embed.set_footer(text="Usa /tienda para comprar artículos y /usar para activar consumibles o pases XP")
    return embed


class InventoryView(discord.ui.View):
    """Vista interactiva efímera de /inventario con botón para presumir el inventario en público."""

    def __init__(
        self,
        author_id: Any,
        target_id: Any,
        target_display_name: str,
        target_avatar_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        super().__init__(timeout=timeout)
        self.author_id = int(author_id)
        self.target_id = int(target_id)
        self.target_display_name = target_display_name
        self.target_avatar_url = target_avatar_url

    @discord.ui.button(
        label="📢 Mostrar en público",
        style=discord.ButtonStyle.primary,
        custom_id="inventory:show_public",
    )
    async def show_public_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Solo quien consultó este inventario puede publicarlo.",
                ephemeral=True,
            )
            return

        button.disabled = True
        button.label = "✅ Mostrado en público"
        pub_embed = build_inventory_embed(
            self.target_id,
            self.target_display_name,
            self.target_avatar_url,
        )
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            content=f"📢 **{interaction.user.display_name}** ha compartido el inventario de **{self.target_display_name}**:",
            embed=pub_embed,
            ephemeral=False,
        )


# ==========================================
# CLASIFICACIÓN DE RIQUEZA (/RANKING)
# ==========================================

def get_economy_leaderboard(sort_by: str = "total", limit: int = 10) -> List[Dict[str, Any]]:
    """
    Devuelve la clasificación de usuarios ordenada de mayor a menor según:
    - 'total' (cash + bank)
    - 'cash' (efectivo)
    - 'bank' (banco)
    """
    field = sort_by.strip().lower()
    if field not in ("total", "cash", "bank"):
        field = "total"

    with ECONOMY_LOCK:
        data = load_economy_data()
        users = data.get("users", {})
        entries: List[Dict[str, Any]] = []
        for uid, udata in users.items():
            cash = int(udata.get("cash", 0))
            bank = int(udata.get("bank", 0))
            total = cash + bank
            entries.append({
                "user_id": str(uid),
                "username": udata.get("username"),
                "cash": cash,
                "bank": bank,
                "total": total,
            })

    entries.sort(key=lambda x: (x[field], x["total"], x["cash"]), reverse=True)
    for idx, item in enumerate(entries, start=1):
        item["rank"] = idx

    if limit and limit > 0:
        return entries[:limit]
    return entries


def build_ranking_embed(
    sort_by: str = "total",
    requester_id: Optional[Any] = None,
    guild: Optional[discord.Guild] = None,
) -> discord.Embed:
    """Construye el embed público de /ranking con el Top 10 y la posición del solicitante."""
    field = sort_by.strip().lower()
    if field not in ("total", "cash", "bank"):
        field = "total"

    all_entries = get_economy_leaderboard(sort_by=field, limit=0)
    top_entries = all_entries[:10]

    titles = {
        "total": "🏆 Clasificación de Riqueza — 💎 Patrimonio Total",
        "cash": "🏆 Clasificación de Riqueza — 💵 Efectivo en Mano",
        "bank": "🏆 Clasificación de Riqueza — 🏦 Cámara Bancaria",
    }
    colors = {
        "total": 0xF1C40F,
        "cash": 0x2ECC71,
        "bank": 0x3498DB,
    }

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = []

    for entry in top_entries:
        rank = entry["rank"]
        uid_str = entry["user_id"]
        medal = medals.get(rank, f"`#{rank:02d}`")

        display_label = None
        if guild is not None:
            try:
                member = guild.get_member(int(uid_str))
                if member:
                    display_label = f"**{member.display_name}** (`@{member.name}`)"
            except Exception:
                pass
        if not display_label:
            uname = entry.get("username")
            display_label = f"**@{uname}**" if uname else f"<@{uid_str}>"

        if field == "total":
            val_str = f"{PORRO_EMOJI} **{entry['total']:,}** *(💵 {entry['cash']:,} | 🏦 {entry['bank']:,})*"
        elif field == "cash":
            val_str = f"{PORRO_EMOJI} **{entry['cash']:,}** en efectivo *(💎 Total: {entry['total']:,})*"
        else:
            val_str = f"{PORRO_EMOJI} **{entry['bank']:,}** en banco *(💎 Total: {entry['total']:,})*"

        lines.append(f"{medal} {display_label} — {val_str}")

    desc = "\n".join(lines) if lines else "*Todavía no hay usuarios registrados en la economía.*"
    jackpot = get_server_jackpot()

    embed = discord.Embed(
        title=titles[field],
        description=(
            f"🎰 **Bote Progresivo del Servidor:** {PORRO_EMOJI} **{jackpot:,}** Porros\n\n"
            f"{desc}"
        ),
        color=colors[field],
        timestamp=datetime.now(timezone.utc),
    )

    if requester_id is not None:
        req_uid = str(requester_id)
        req_entry = next((e for e in all_entries if e["user_id"] == req_uid), None)
        if req_entry:
            embed.set_footer(
                text=(
                    f"Tu posición: #{req_entry['rank']} de {len(all_entries)} • "
                    f"Total: {req_entry['total']:,} Porros (Efectivo: {req_entry['cash']:,} | Banco: {req_entry['bank']:,})"
                )
            )
        else:
            embed.set_footer(text=f"Total de participantes registrados: {len(all_entries)}")
    else:
        embed.set_footer(text=f"Total de participantes registrados: {len(all_entries)}")

    return embed


class RankingCategorySelect(discord.ui.Select):
    """Selector interactivo para cambiar la categoría del ranking en vivo."""

    def __init__(self, current_sort: str = "total"):
        options = [
            discord.SelectOption(
                label="💎 Patrimonio Total (Efectivo + Banco)",
                value="total",
                description="Los miembros más ricos del servidor en total",
                emoji="💎",
                default=(current_sort == "total"),
            ),
            discord.SelectOption(
                label="💵 Efectivo en Mano (Cash)",
                value="cash",
                description="Quienes llevan más Porros sueltos encima (¡atracables!)",
                emoji="💵",
                default=(current_sort == "cash"),
            ),
            discord.SelectOption(
                label="🏦 Saldo en el Banco (Bank)",
                value="bank",
                description="Las mayores fortunas protegidas en cámara acorazada",
                emoji="🏦",
                default=(current_sort == "bank"),
            ),
        ]
        super().__init__(
            placeholder="📊 Cambiar categoría del ranking...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        view: "RankingView" = self.view
        selected_sort = self.values[0]
        view.sort_by = selected_sort
        for opt in self.options:
            opt.default = (opt.value == selected_sort)

        embed = build_ranking_embed(
            sort_by=selected_sort,
            requester_id=interaction.user.id,
            guild=interaction.guild,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class RankingView(discord.ui.View):
    """Vista interactiva pública de /ranking."""

    def __init__(self, author_id: Optional[Any] = None, sort_by: str = "total", timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.author_id = int(author_id) if author_id is not None else None
        self.sort_by = sort_by
        self.message: Optional[discord.Message] = None
        self.select_menu = RankingCategorySelect(current_sort=sort_by)
        self.add_item(self.select_menu)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


# ==========================================
# PANEL FINANCIERO DE ADMINISTRACIÓN (/ADMIN_DINERO)
# ==========================================

def _normalize_target_field(target_field: str) -> str:
    tf = str(target_field).strip().lower()
    if tf in ("bank", "banco"):
        return "bank"
    return "cash"


def admin_modify_money(
    target_user_id: Any,
    action: str,
    amount: int,
    target_field: str = "cash",
    username: Optional[str] = None,
) -> Tuple[bool, str, Dict[str, int]]:
    """
    Ejecuta una operación administrativa ('dar', 'quitar', 'fijar') sobre el saldo
    de efectivo ('cash') o banco ('bank') de un miembro.
    """
    act = str(action).strip().lower()
    field = _normalize_target_field(target_field)
    field_label = "Efectivo (Cash)" if field == "cash" else "Banco (Bank)"
    uid = str(target_user_id)

    if act not in ("dar", "quitar", "fijar"):
        return False, f"❌ Acción administrativa inválida: '{action}'. Usa 'dar', 'quitar' o 'fijar'.", get_balance(uid)

    if act in ("dar", "quitar") and amount <= 0:
        return False, "❌ Para dar o quitar Porros, la cantidad debe ser un entero mayor que 0.", get_balance(uid)

    if act == "fijar" and amount < 0:
        return False, "❌ No se puede fijar un saldo negativo.", get_balance(uid)

    with ECONOMY_LOCK:
        user = ensure_user(uid)
        if username:
            user["username"] = str(username)

        current_val = int(user.get(field, 0))
        if act == "dar":
            new_val = current_val + int(amount)
            verb_desc = f"Se han añadido {PORRO_EMOJI} **+{amount:,}** Porros a **{field_label}**."
        elif act == "quitar":
            new_val = max(0, current_val - int(amount))
            removed = current_val - new_val
            verb_desc = f"Se han retirado {PORRO_EMOJI} **-{removed:,}** Porros de **{field_label}**."
        else:  # fijar
            new_val = int(amount)
            verb_desc = f"Se ha fijado el saldo de **{field_label}** en {PORRO_EMOJI} **{new_val:,}** Porros."

        user[field] = new_val
        data = load_economy_data()
        save_economy_data(data)
        new_bal = get_balance(uid)

    _bot_log(f"🛠️ [Admin Dinero] acción={act} usuario={uid} campo={field} cantidad={amount} -> nuevo={new_val}")
    return True, verb_desc, new_bal


def admin_airdrop_role(
    targets: List[Tuple[Any, Optional[str]]],
    amount: int,
    target_field: str = "cash",
    role_name: str = "Rol",
) -> Tuple[bool, str, int]:
    """
    Reparte 'amount' Porros a todos los miembros humanos incluidos en 'targets' [(user_id, username), ...].
    Devuelve (éxito, mensaje, número_de_beneficiarios).
    """
    if amount <= 0:
        return False, "❌ La cantidad del airdrop debe ser mayor que 0 Porros.", 0

    if not targets:
        return False, f"❌ No se encontraron miembros humanos con el rol **{role_name}**.", 0

    field = _normalize_target_field(target_field)
    field_label = "Efectivo (Cash)" if field == "cash" else "Banco (Bank)"

    with ECONOMY_LOCK:
        count = 0
        for uid_raw, uname in targets:
            uid = str(uid_raw)
            user = ensure_user(uid)
            if uname:
                user["username"] = str(uname)
            user[field] = int(user.get(field, 0)) + int(amount)
            count += 1

        data = load_economy_data()
        save_economy_data(data)

    total_distributed = count * int(amount)
    msg = (
        f"🪂 **¡AIRDROP COMPLETADO!**\n"
        f"Se han repartido {PORRO_EMOJI} **+{amount:,}** Porros en **{field_label}** a **{count} miembros** "
        f"con el rol **{role_name}**.\n"
        f"💰 **Masa monetaria inyectada:** {PORRO_EMOJI} **{total_distributed:,}** Porros."
    )
    _bot_log(f"🪂 [Admin Airdrop] +{amount:,} Porros ({field}) a {count} miembros del rol '{role_name}'.")
    return True, msg, count


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


# ==========================================
# RULETA EUROPEA 37 CASILLAS (0-36)
# ==========================================

# Secuencia circular oficial del cilindro europeo (37 casillas)
ROULETTE_SEQUENCE: List[int] = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10,
    5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

ROULETTE_RED: set = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
ROULETTE_BLACK: set = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}
ROULETTE_GREEN: set = {0}

ROULETTE_BET_INFO: Dict[str, Dict[str, Any]] = {
    "rojo": {"name": "🔴 Rojo", "mult": 1, "payout_ratio": "1:1"},
    "negro": {"name": "⚫ Negro", "mult": 1, "payout_ratio": "1:1"},
    "par": {"name": "⚖️ Par", "mult": 1, "payout_ratio": "1:1"},
    "impar": {"name": "⚡ Impar", "mult": 1, "payout_ratio": "1:1"},
    "baja": {"name": "📉 1-18 (Baja)", "mult": 1, "payout_ratio": "1:1"},
    "alta": {"name": "📈 19-36 (Alta)", "mult": 1, "payout_ratio": "1:1"},
    "docena1": {"name": "1️⃣ 1ª Docena (1-12)", "mult": 2, "payout_ratio": "2:1"},
    "docena2": {"name": "2️⃣ 2ª Docena (13-24)", "mult": 2, "payout_ratio": "2:1"},
    "docena3": {"name": "3️⃣ 3ª Docena (25-36)", "mult": 2, "payout_ratio": "2:1"},
    "columna1": {"name": "🏛️ Columna 1", "mult": 2, "payout_ratio": "2:1"},
    "columna2": {"name": "🏛️ Columna 2", "mult": 2, "payout_ratio": "2:1"},
    "columna3": {"name": "🏛️ Columna 3", "mult": 2, "payout_ratio": "2:1"},
    "pleno": {"name": "🎯 Pleno", "mult": 35, "payout_ratio": "35:1"},
}


def format_roulette_pocket(num: int) -> str:
    """Devuelve la representación con emoji de color de la casilla de ruleta."""
    if num == 0:
        return f"{num}🟩"
    elif num in ROULETTE_RED:
        return f"{num}🟥"
    else:
        return f"{num}⬛"


def normalize_roulette_bet_type(bet_type: str) -> str:
    """Normaliza el tipo de apuesta a su clave canónica interna."""
    s = str(bet_type).strip().lower()
    if s in ("rojo", "red", "🔴 rojo", "🔴"):
        return "rojo"
    if s in ("negro", "black", "⚫ negro", "⚫"):
        return "negro"
    if s in ("par", "even", "⚖️ par", "⚖️"):
        return "par"
    if s in ("impar", "odd", "⚡ impar", "⚡"):
        return "impar"
    if s in ("baja", "1-18", "1-18 (baja)", "📉 1-18 (baja)", "low", "falta"):
        return "baja"
    if s in ("alta", "19-36", "19-36 (alta)", "📈 19-36 (alta)", "high", "pasa"):
        return "alta"
    if s in ("docena1", "docena_1", "1ª docena (1-12)", "1 docena", "1st dozen", "1-12", "1ª docena", "1 docena (1-12)"):
        return "docena1"
    if s in ("docena2", "docena_2", "2ª docena (13-24)", "2 docena", "2nd dozen", "13-24", "2ª docena", "2 docena (13-24)"):
        return "docena2"
    if s in ("docena3", "docena_3", "3ª docena (25-36)", "3 docena", "3rd dozen", "25-36", "3ª docena", "3 docena (25-36)"):
        return "docena3"
    if s in ("columna1", "col1", "columna_1", "columna 1", "🏛️ columna 1", "1st column"):
        return "columna1"
    if s in ("columna2", "col2", "columna_2", "columna 2", "🏛️ columna 2", "2nd column"):
        return "columna2"
    if s in ("columna3", "col3", "columna_3", "columna 3", "🏛️ columna 3", "3rd column"):
        return "columna3"
    if s in ("pleno", "single", "directo", "numero", "🎯 pleno (0-36)", "🎯 pleno (número exacto 0-36)", "🎯 pleno"):
        return "pleno"
    return s


def is_roulette_winner(winning_num: int, norm_type: str, bet_number: Optional[int] = None) -> bool:
    """Evalúa si una apuesta resulta ganadora ante el número de la bola (regla del 0 verde)."""
    if winning_num == 0:
        return norm_type == "pleno" and bet_number == 0
    if norm_type == "rojo":
        return winning_num in ROULETTE_RED
    elif norm_type == "negro":
        return winning_num in ROULETTE_BLACK
    elif norm_type == "par":
        return winning_num % 2 == 0
    elif norm_type == "impar":
        return winning_num % 2 != 0
    elif norm_type == "baja":
        return 1 <= winning_num <= 18
    elif norm_type == "alta":
        return 19 <= winning_num <= 36
    elif norm_type == "docena1":
        return 1 <= winning_num <= 12
    elif norm_type == "docena2":
        return 13 <= winning_num <= 24
    elif norm_type == "docena3":
        return 25 <= winning_num <= 36
    elif norm_type == "columna1":
        return winning_num % 3 == 1
    elif norm_type == "columna2":
        return winning_num % 3 == 2
    elif norm_type == "columna3":
        return winning_num % 3 == 0
    elif norm_type == "pleno":
        return winning_num == bet_number
    return False


def parse_roulette_bet(user_id: Any, apuesta_str: str) -> Tuple[bool, int, str]:
    """Valida y calcula el monto de la apuesta en Porros para la ruleta (mínimo 50 o 'all'/'todo'/'max')."""
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
        return False, 0, f"La apuesta mínima en la Ruleta es de 50 Porros ({PORRO_EMOJI})."

    if cash < bet:
        return False, 0, f"No tienes suficientes Porros en efectivo ({cash:,} disponibles). Usa `/trabajar` o retira de tu `/banco`."

    return True, bet, ""


class RouletteEngine:
    """Motor matemático de Ruleta Europea de 37 casillas (0 a 36)."""

    def __init__(self):
        self.sequence = ROULETTE_SEQUENCE
        self.red_numbers = ROULETTE_RED
        self.black_numbers = ROULETTE_BLACK
        self.green_numbers = ROULETTE_GREEN

    def get_color(self, number: int) -> Tuple[str, str]:
        """Devuelve (nombre_color, emoji) para un número."""
        if number == 0:
            return "verde", "🟩"
        elif number in self.red_numbers:
            return "rojo", "🟥"
        else:
            return "negro", "⬛"

    def get_cylinder_display(self, winning_num: int) -> str:
        """Genera visualización del cilindro europeo con los 2 vecinos a cada lado:
        [ N-2 ] ➔ [ N-1 ] ➔ 👑 [ N ] 👑 ➔ [ N+1 ] ➔ [ N+2 ]
        """
        idx = self.sequence.index(winning_num)
        n = len(self.sequence)
        p_minus_2 = format_roulette_pocket(self.sequence[(idx - 2) % n])
        p_minus_1 = format_roulette_pocket(self.sequence[(idx - 1) % n])
        p_curr = format_roulette_pocket(winning_num)
        p_plus_1 = format_roulette_pocket(self.sequence[(idx + 1) % n])
        p_plus_2 = format_roulette_pocket(self.sequence[(idx + 2) % n])
        return f"[ {p_minus_2} ] ➔ [ {p_minus_1} ] ➔ 👑 [ {p_curr} ] 👑 ➔ [ {p_plus_1} ] ➔ [ {p_plus_2} ]"

    def spin_wheel(
        self,
        user_id: Any,
        bet_amount: int,
        bet_type: str,
        bet_number: Optional[int] = None,
        rng_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Valida apuesta y saldo con modify_balance, ejecuta el giro y retorna el resultado."""
        if bet_amount < 50:
            raise ValueError(f"La apuesta mínima en la Ruleta es de 50 Porros ({PORRO_EMOJI}).")

        norm_type = normalize_roulette_bet_type(bet_type)
        if norm_type not in ROULETTE_BET_INFO:
            raise ValueError(f"Tipo de apuesta '{bet_type}' no reconocido.")

        if norm_type == "pleno":
            if bet_number is None or not (0 <= bet_number <= 36):
                raise ValueError("Para una apuesta a Pleno debes especificar un número entre 0 y 36.")

        uid = str(user_id)
        with ECONOMY_LOCK:
            # Descontar apuesta (valida saldo de forma atómica con modify_balance)
            modify_balance(uid, cash_delta=-bet_amount)

            try:
                # Lanzar bola de forma aleatoria (0 a 36)
                winning_num = rng_number if rng_number is not None else random.randint(0, 36)
                won = is_roulette_winner(winning_num, norm_type, bet_number)
                mult = ROULETTE_BET_INFO[norm_type]["mult"]
                color_name, color_emoji = self.get_color(winning_num)
                cylinder_display = self.get_cylinder_display(winning_num)

                if won:
                    net_gain = bet_amount * mult
                    payout = bet_amount + net_gain
                    modify_balance(uid, cash_delta=payout)
                    jackpot_feed = 0
                else:
                    net_gain = -bet_amount
                    payout = 0
                    jackpot_feed = max(1, int(bet_amount * JACKPOT_FEED_PERCENT))
                    modify_server_jackpot(jackpot_feed)

                bal = get_balance(uid)
                cur_jackpot = get_server_jackpot()

                bet_desc = ROULETTE_BET_INFO[norm_type]["name"]
                if norm_type == "pleno":
                    bet_desc = f"🎯 Pleno al {bet_number} ({format_roulette_pocket(bet_number)})"

                return {
                    "won": won,
                    "winning_number": winning_num,
                    "color": color_name,
                    "color_emoji": color_emoji,
                    "cylinder_display": cylinder_display,
                    "bet_amount": bet_amount,
                    "bet_type": norm_type,
                    "bet_type_name": ROULETTE_BET_INFO[norm_type]["name"],
                    "bet_number": bet_number,
                    "bet_desc": bet_desc,
                    "multiplier": mult if won else 0,
                    "payout_ratio": ROULETTE_BET_INFO[norm_type]["payout_ratio"],
                    "net_gain": net_gain,
                    "payout": payout,
                    "jackpot_feed": jackpot_feed,
                    "user_cash": bal["cash"],
                    "server_jackpot": cur_jackpot,
                }
            except Exception as e:
                # En caso de error, reembolsar apuesta
                modify_balance(uid, cash_delta=bet_amount)
                raise e


roulette_engine = RouletteEngine()


def build_roulette_embed(
    user: Union[discord.User, discord.Member],
    result: Dict[str, Any],
) -> discord.Embed:
    """Construye el Embed oficial de alta fidelidad visual para la Ruleta Europea."""
    winning_num = result["winning_number"]
    color_name = result["color"]
    color_emoji = result["color_emoji"]
    won = result["won"]
    net_gain = result["net_gain"]
    payout = result["payout"]
    bet_amount = result["bet_amount"]
    bet_desc = result["bet_desc"]
    payout_ratio = result["payout_ratio"]
    cylinder = result["cylinder_display"]
    jackpot_feed = result["jackpot_feed"]
    user_cash = result["user_cash"]
    server_jackpot = result["server_jackpot"]

    if winning_num == 0:
        embed_color = 0x2ECC71  # Verde casino
    elif color_name == "rojo":
        embed_color = 0xE74C3C  # Rojo
    else:
        embed_color = 0x2C3E50  # Negro/Gris oscuro

    embed = discord.Embed(
        title="🎰 Ruleta Europea 37 Casillas — Casino Asistente",
        color=embed_color,
        timestamp=datetime.now(timezone.utc),
    )

    desc_lines = [
        f"🎡 **Cilindro Europeo:**\n{cylinder}\n",
    ]

    if won:
        desc_lines.append(
            f"🎉 **¡ENHORABUENA, HAS GANADO!**\n"
            f"• La bola cayó en **{winning_num} {color_emoji}** ({color_name.title()}).\n"
            f"• Apuesta: **{bet_desc}** (Pago {payout_ratio}).\n"
            f"• ¡Has ganado **+{net_gain:,}** Porros limpios ({PORRO_EMOJI})!\n"
            f"💰 Total acreditado: **{payout:,}** Porros."
        )
    else:
        desc_lines.append(
            f"💀 **¡HAS PERDIDO!**\n"
            f"• La bola cayó en **{winning_num} {color_emoji}** ({color_name.title()}).\n"
            f"• Tu apuesta: **{bet_desc}**.\n"
            f"• Has perdido **{bet_amount:,}** Porros ({PORRO_EMOJI}).\n"
            f"🎰 Se han añadido **+{jackpot_feed:,}** Porros al bote del servidor."
        )

    embed.description = "\n".join(desc_lines)

    embed.add_field(
        name="🎯 Casilla Ganadora",
        value=f"**{winning_num} {color_emoji}** ({color_name.title()})",
        inline=True,
    )
    embed.add_field(
        name="🎲 Tu Apuesta",
        value=f"**{bet_desc}**",
        inline=True,
    )
    embed.add_field(
        name="💰 Apuesta",
        value=f"{PORRO_EMOJI} **{bet_amount:,}** Porros",
        inline=True,
    )
    embed.add_field(
        name="💵 Saldo en Efectivo",
        value=f"{PORRO_EMOJI} **{user_cash:,}** Porros",
        inline=True,
    )
    embed.add_field(
        name="🎰 Bote Acumulado",
        value=f"{PORRO_EMOJI} **{server_jackpot:,}** Porros",
        inline=True,
    )

    embed.set_footer(text="Ruleta Europea 37 Casillas • RTP 97.30% • Casino Oficial")
    if hasattr(user, "display_avatar") and user.display_avatar:
        embed.set_author(name=user.display_name, icon_url=str(user.display_avatar.url))

    return embed


class RouletteActionView(discord.ui.View):
    """Vista interactiva con botones para re-apostar en la Ruleta con timeout de 60s."""

    def __init__(
        self,
        user_id: int,
        user: Union[discord.User, discord.Member],
        bet_amount: int,
        bet_type: str,
        bet_number: Optional[int] = None,
        engine: Optional[RouletteEngine] = None,
    ):
        super().__init__(timeout=60.0)
        self.user_id = int(user_id)
        self.user = user
        self.bet_amount = bet_amount
        self.bet_type = bet_type
        self.bet_number = bet_number
        self.engine = engine or roulette_engine
        self.message: Optional[discord.Message] = None
        self._lock = asyncio.Lock()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Esta tirada de ruleta no es tuya. Usa `/ruleta` para hacer tus propias apuestas.",
                ephemeral=True,
            )
            return False
        return True

    def disable_all_buttons(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    async def do_spin(self, interaction: discord.Interaction, new_bet: int) -> None:
        async with self._lock:
            bal = get_balance(self.user_id)
            if bal["cash"] < new_bet:
                await interaction.response.send_message(
                    f"❌ No tienes suficientes Porros en efectivo para apostar {new_bet:,} "
                    f"({bal['cash']:,} disponibles). Usa `/trabajar` o retira de tu `/banco`.",
                    ephemeral=True,
                )
                return

            self.bet_amount = new_bet
            res = self.engine.spin_wheel(
                user_id=self.user_id,
                bet_amount=self.bet_amount,
                bet_type=self.bet_type,
                bet_number=self.bet_number,
            )

            embed = build_roulette_embed(user=self.user, result=res)
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=self)
            elif self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    pass

    @discord.ui.button(
        label="🔄 Repetir Apuesta",
        style=discord.ButtonStyle.primary,
        custom_id="roulette:repeat",
    )
    async def repeat_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.do_spin(interaction, new_bet=self.bet_amount)

    @discord.ui.button(
        label="🪙 Duplicar Apuesta",
        style=discord.ButtonStyle.success,
        custom_id="roulette:double",
    )
    async def double_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.do_spin(interaction, new_bet=self.bet_amount * 2)

    async def on_timeout(self) -> None:
        self.disable_all_buttons()
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


# ==========================================
# COINFLIP DUAL (PvE Y PvP) (/coinflip)
# ==========================================

ACTIVE_COINFLIP_DUELS: Dict[Any, Any] = {}


def normalize_coinflip_side(side: Any) -> str:
    """Normaliza la elección del lado de la moneda a 'cara' o 'cruz'."""
    if hasattr(side, "value"):
        side = side.value
    s = str(side or "cara").strip().lower()
    if s in ("cruz", "tails", "x", "🪙 cruz"):
        return "cruz"
    return "cara"


def parse_coinflip_bet(user_id: Any, apuesta_str: str) -> Tuple[bool, int, str]:
    """Valida y calcula el monto de la apuesta en Porros para Coinflip (mínimo 50 o 'all'/'todo'/'max')."""
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
        return False, 0, f"La apuesta mínima en Coinflip es de 50 Porros ({PORRO_EMOJI})."

    if cash < bet:
        return False, 0, f"No tienes suficientes Porros en efectivo ({cash:,} disponibles). Usa `/trabajar` o retira de tu `/banco`."

    return True, bet, ""


class CoinflipEngine:
    """Motor matemático del juego Coinflip (Cara o Cruz) en modalidades PvE (contra la casa) y PvP (duelos)."""

    def __init__(self):
        self.sides = ["cara", "cruz"]

    def flip_coin(self, rng_outcome: Optional[str] = None) -> str:
        """Devuelve el resultado del lanzamiento de moneda (50/50 justo)."""
        if rng_outcome in self.sides:
            return rng_outcome
        return random.choice(self.sides)

    def play_pve(
        self,
        user_id: Any,
        bet_amount: int,
        choice: str = "cara",
        rng_outcome: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ejecuta una tirada PvE contra la casa:
        - 50/50 justo (cara o cruz).
        - Cobro 1:1 en caso de acierto (retorno 2x la apuesta).
        - Descuento atómico inicial.
        - Si pierde, el 3% de la pérdida neta alimenta el server_jackpot.
        """
        if bet_amount < 50:
            raise ValueError(f"La apuesta mínima en Coinflip es de 50 Porros ({PORRO_EMOJI}).")

        player_choice = normalize_coinflip_side(choice)
        uid = str(user_id)

        with ECONOMY_LOCK:
            modify_balance(uid, cash_delta=-bet_amount)

            try:
                outcome = self.flip_coin(rng_outcome)
                won = (outcome == player_choice)

                if won:
                    net_gain = bet_amount
                    payout = bet_amount * 2
                    modify_balance(uid, cash_delta=payout)
                    jackpot_feed = 0
                else:
                    net_gain = -bet_amount
                    payout = 0
                    jackpot_feed = max(1, int(bet_amount * JACKPOT_FEED_PERCENT))
                    modify_server_jackpot(jackpot_feed)

                bal = get_balance(uid)
                cur_jackpot = get_server_jackpot()

                return {
                    "won": won,
                    "choice": player_choice,
                    "outcome": outcome,
                    "bet_amount": bet_amount,
                    "net_gain": net_gain,
                    "payout": payout,
                    "jackpot_feed": jackpot_feed,
                    "user_cash": bal["cash"],
                    "server_jackpot": cur_jackpot,
                }
            except Exception as e:
                modify_balance(uid, cash_delta=bet_amount)
                raise e

    def resolve_pvp(
        self,
        challenger_id: Any,
        rival_id: Any,
        bet_amount: int,
        challenger_side: str = "cara",
        rng_outcome: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resuelve un duelo PvP entre dos miembros:
        - Verifica y descuenta atómicamente la apuesta del rival.
        - Resolución 50/50 justa.
        - El 2% del bote total (2 * apuesta) se envía al server_jackpot.
        - El 98% restante del bote total se abona instantáneamente al ganador.
        """
        c_uid = str(challenger_id)
        r_uid = str(rival_id)
        c_side = normalize_coinflip_side(challenger_side)
        r_side = "cruz" if c_side == "cara" else "cara"

        with ECONOMY_LOCK:
            r_bal = get_balance(r_uid)
            if r_bal["cash"] < bet_amount:
                raise ValueError("El rival no tiene fondos suficientes en efectivo.")

            modify_balance(r_uid, cash_delta=-bet_amount)

            try:
                outcome = self.flip_coin(rng_outcome)
                if outcome == c_side:
                    winner_id = c_uid
                    loser_id = r_uid
                    winner_role = "challenger"
                else:
                    winner_id = r_uid
                    loser_id = c_uid
                    winner_role = "rival"

                total_pot = bet_amount * 2
                jackpot_cut = max(1, int(total_pot * 0.02))  # 2% del bote total acumulado
                winner_prize = total_pot - jackpot_cut        # 98% restante

                modify_server_jackpot(jackpot_cut)
                modify_balance(winner_id, cash_delta=winner_prize)

                return {
                    "outcome": outcome,
                    "winner_id": winner_id,
                    "loser_id": loser_id,
                    "winner_role": winner_role,
                    "challenger_side": c_side,
                    "rival_side": r_side,
                    "bet_amount": bet_amount,
                    "total_pot": total_pot,
                    "jackpot_cut": jackpot_cut,
                    "winner_prize": winner_prize,
                    "server_jackpot": get_server_jackpot(),
                }
            except Exception as e:
                modify_balance(r_uid, cash_delta=bet_amount)
                raise e


coinflip_engine = CoinflipEngine()


def build_coinflip_embed(
    mode: str,
    user: Optional[Union[discord.User, discord.Member]] = None,
    result: Optional[Dict[str, Any]] = None,
    challenger: Optional[Union[discord.User, discord.Member]] = None,
    rival: Optional[Union[discord.User, discord.Member]] = None,
    winner: Optional[Union[discord.User, discord.Member]] = None,
    loser: Optional[Union[discord.User, discord.Member]] = None,
    bet: Optional[int] = None,
    challenger_side: Optional[str] = None,
    rival_side: Optional[str] = None,
    cancelled_by: Optional[Union[discord.User, discord.Member]] = None,
) -> discord.Embed:
    """Construye los Embeds de alta fidelidad visual para Coinflip (PvE y PvP)."""
    if mode == "pve" and result is not None:
        won = result["won"]
        outcome = result["outcome"]
        choice = result["choice"]
        bet_amount = result["bet_amount"]
        net_gain = result["net_gain"]
        payout = result["payout"]
        jackpot_feed = result["jackpot_feed"]
        user_cash = result["user_cash"]
        server_jackpot = result["server_jackpot"]

        color = 0x2ECC71 if won else 0xE74C3C
        embed = discord.Embed(
            title="🪙 Coinflip (Cara o Cruz) — Casino Asistente",
            color=color,
            timestamp=datetime.now(timezone.utc),
        )

        if won:
            desc = (
                f"🪙 **Resultado del Lanzamiento:**\n"
                f"¡La moneda giró en el aire y cayó en **`{outcome.upper()}`**!\n\n"
                f"🎉 **¡ENHORABUENA, HAS ACERTADO!**\n"
                f"• Tu elección: **`{choice.capitalize()}`**\n"
                f"• ¡Has ganado **+{net_gain:,}** Porros limpios ({PORRO_EMOJI})!\n"
                f"💰 Total acreditado: **{payout:,}** Porros."
            )
        else:
            desc = (
                f"🪙 **Resultado del Lanzamiento:**\n"
                f"¡La moneda giró en el aire y cayó en **`{outcome.upper()}`**!\n\n"
                f"💀 **¡MALA SUERTE, HAS FALLADO!**\n"
                f"• Tu elección: **`{choice.capitalize()}`**\n"
                f"• Has perdido **{bet_amount:,}** Porros ({PORRO_EMOJI}).\n"
                f"🎰 Se han añadido **+{jackpot_feed:,}** Porros al bote del servidor."
            )

        embed.description = desc
        embed.add_field(name="🎯 Resultado", value=f"🪙 **{outcome.capitalize()}**", inline=True)
        embed.add_field(name="🎲 Tu Elección", value=f"🪙 **{choice.capitalize()}**", inline=True)
        embed.add_field(name="💰 Apuesta", value=f"{PORRO_EMOJI} **{bet_amount:,}**", inline=True)
        embed.add_field(name="💵 Saldo en Efectivo", value=f"{PORRO_EMOJI} **{user_cash:,}**", inline=True)
        embed.add_field(name="🎰 Bote Acumulado", value=f"{PORRO_EMOJI} **{server_jackpot:,}**", inline=True)
        embed.set_footer(text="Coinflip PvE • Probabilidad 50/50 • Pago 1:1 • Casino Oficial")
        if user and hasattr(user, "display_avatar") and user.display_avatar:
            embed.set_author(name=user.display_name, icon_url=str(user.display_avatar.url))
        return embed

    elif mode == "pvp_pending":
        c_name = challenger.display_name if challenger else "Retador"
        r_name = rival.display_name if rival else "Rival"
        b_amt = bet or 0
        total_pot = b_amt * 2
        jackpot_cut = max(1, int(total_pot * 0.02))
        winner_prize = total_pot - jackpot_cut
        c_side = (challenger_side or "cara").capitalize()
        r_side = (rival_side or "cruz").capitalize()

        embed = discord.Embed(
            title="⚔️ Duelo de Coinflip PvP — ¡Desafío Lanzado!",
            color=0xF1C40F,
            timestamp=datetime.now(timezone.utc),
        )
        embed.description = (
            f"⚔️ **{c_name}** ha desafiado a **{r_name}** a un duelo a cara o cruz.\n\n"
            f"• 💰 **Apuesta por jugador:** {PORRO_EMOJI} **{b_amt:,}** Porros\n"
            f"• 🏆 **Bote Total:** {PORRO_EMOJI} **{total_pot:,}** Porros\n"
            f"• 👑 **Premio Ganador (98%):** {PORRO_EMOJI} **{winner_prize:,}** Porros\n"
            f"• 🎰 **Comisión Jackpot (2%):** **+{jackpot_cut:,}** Porros\n\n"
            f"• 🪙 **{c_name}:** Elige **`{c_side}`**\n"
            f"• 🪙 **{r_name}:** Recibe **`{r_side}`**\n\n"
            f"-# ⏳ **{r_name}**, pulsa `[ ⚔️ Aceptar Desafío ]` para combatir o `[ 🏳️ Rechazar ]`. (Expiración en 60s)"
        )
        embed.set_footer(text="Duelo PvP Coinflip • 50/50 Justo • 2% al Jackpot")
        if challenger and hasattr(challenger, "display_avatar") and challenger.display_avatar:
            embed.set_author(name=f"Desafío de {c_name}", icon_url=str(challenger.display_avatar.url))
        return embed

    elif mode == "pvp_result" and result is not None:
        w_name = winner.display_name if winner else "Ganador"
        l_name = loser.display_name if loser else "Perdedor"
        outcome = result["outcome"]
        total_pot = result["total_pot"]
        winner_prize = result["winner_prize"]
        jackpot_cut = result["jackpot_cut"]
        cur_jackpot = result["server_jackpot"]
        b_amt = result["bet_amount"]

        w_side = result["challenger_side"] if result["winner_role"] == "challenger" else result["rival_side"]
        l_side = result["rival_side"] if result["winner_role"] == "challenger" else result["challenger_side"]

        embed = discord.Embed(
            title="👑 ¡Victoria en el Duelo de Coinflip! ⚔️",
            color=0x2ECC71,
            timestamp=datetime.now(timezone.utc),
        )
        embed.description = (
            f"🪙 **Resultado del Lanzamiento:**\n"
            f"¡La moneda giró en el aire y cayó en **`{outcome.upper()}`**!\n\n"
            f"👑 **¡VICTORIA PARA {w_name}!**\n"
            f"💀 **{l_name} ha caído en combate.**\n\n"
            f"• 💰 **Bote Total en Juego:** {PORRO_EMOJI} **{total_pot:,}** Porros\n"
            f"• 👑 **Premio Acreditado (98%):** {PORRO_EMOJI} **+{winner_prize:,}** Porros\n"
            f"• 🎰 **Comisión al Jackpot (2%):** **+{jackpot_cut:,}** Porros"
        )
        embed.add_field(name="🎯 Moneda", value=f"🪙 **{outcome.capitalize()}**", inline=True)
        embed.add_field(name="👑 Vencedor", value=f"**{w_name}** (`{w_side.capitalize()}`)", inline=True)
        embed.add_field(name="💀 Derrotado", value=f"{l_name} (`{l_side.capitalize()}`)", inline=True)
        embed.add_field(name="💰 Apuesta Base", value=f"{PORRO_EMOJI} **{b_amt:,}**", inline=True)
        embed.add_field(name="🎰 Bote Servidor", value=f"{PORRO_EMOJI} **{cur_jackpot:,}**", inline=True)
        embed.set_footer(text="Duelo PvP Coinflip • Resolución 50/50 Justa • Casino Oficial")
        if winner and hasattr(winner, "display_avatar") and winner.display_avatar:
            embed.set_thumbnail(url=str(winner.display_avatar.url))
        return embed

    elif mode == "pvp_cancelled":
        c_name = challenger.display_name if challenger else "Retador"
        r_name = rival.display_name if rival else "Rival"
        by_name = cancelled_by.display_name if cancelled_by else "Un participante"
        b_amt = bet or 0

        embed = discord.Embed(
            title="🏳️ Duelo de Coinflip Cancelado",
            color=0xE74C3C,
            timestamp=datetime.now(timezone.utc),
        )
        embed.description = (
            f"El desafío entre **{c_name}** y **{r_name}** ha sido cancelado por **{by_name}**.\n\n"
            f"💰 **Reembolso:** Se ha devuelto la fianza íntegra de {PORRO_EMOJI} **{b_amt:,}** Porros a **{c_name}**."
        )
        embed.set_footer(text="Duelo PvP Coinflip • Cancelación sin comisiones")
        return embed

    elif mode == "pvp_timeout":
        c_name = challenger.display_name if challenger else "Retador"
        r_name = rival.display_name if rival else "Rival"
        b_amt = bet or 0

        embed = discord.Embed(
            title="⏳ Duelo de Coinflip Expirado (Timeout)",
            color=0xE74C3C,
            timestamp=datetime.now(timezone.utc),
        )
        embed.description = (
            f"**{r_name}** no respondió al desafío dentro del límite de 60 segundos.\n\n"
            f"💰 **Reembolso:** Se ha devuelto el 100% de la apuesta retenida ({PORRO_EMOJI} **{b_amt:,}** Porros) a **{c_name}**."
        )
        embed.set_footer(text="Duelo PvP Coinflip • Reembolso automático por inactividad")
        return embed

    elif mode == "pvp_insufficient_funds":
        c_name = challenger.display_name if challenger else "Retador"
        r_name = rival.display_name if rival else "Rival"
        b_amt = bet or 0

        embed = discord.Embed(
            title="❌ Duelo Rechazado — Fondos Insuficientes",
            color=0xE74C3C,
            timestamp=datetime.now(timezone.utc),
        )
        embed.description = (
            f"**{r_name}** intentó aceptar el duelo pero no dispone de los {PORRO_EMOJI} **{b_amt:,}** Porros requeridos en efectivo.\n\n"
            f"💰 **Reembolso:** Se ha devuelto el 100% de la fianza ({PORRO_EMOJI} **{b_amt:,}** Porros) a **{c_name}**."
        )
        embed.set_footer(text="Duelo PvP Coinflip • Fianza reembolsada al retador")
        return embed

    else:
        return discord.Embed(title="🪙 Coinflip", description="Partida de Coinflip.", color=0x3498DB)


class CoinflipActionView(discord.ui.View):
    """Vista interactiva con botón para repetir tirada PvE con timeout de 60s."""

    def __init__(
        self,
        user_id: int,
        user: Union[discord.User, discord.Member],
        bet_amount: int,
        side: str = "cara",
        engine: Optional[CoinflipEngine] = None,
    ):
        super().__init__(timeout=60.0)
        self.user_id = int(user_id)
        self.user = user
        self.bet_amount = bet_amount
        self.side = normalize_coinflip_side(side)
        self.engine = engine or coinflip_engine
        self.message: Optional[discord.Message] = None
        self._lock = asyncio.Lock()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Esta tirada de Coinflip no es tuya. Usa `/coinflip` para jugar tus propias partidas.",
                ephemeral=True,
            )
            return False
        return True

    def disable_all_buttons(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    async def do_flip_again(self, interaction: discord.Interaction) -> None:
        async with self._lock:
            bal = get_balance(self.user_id)
            if bal["cash"] < self.bet_amount:
                await interaction.response.send_message(
                    f"❌ No tienes suficientes Porros en efectivo para repetir la tirada de {self.bet_amount:,} "
                    f"({bal['cash']:,} disponibles). Usa `/trabajar` o retira de tu `/banco`.",
                    ephemeral=True,
                )
                return

            res = self.engine.play_pve(
                user_id=self.user_id,
                bet_amount=self.bet_amount,
                choice=self.side,
            )
            embed = build_coinflip_embed(mode="pve", user=self.user, result=res)
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=self)
            elif self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    pass

    @discord.ui.button(
        label="🔄 Tirar Otra Vez",
        style=discord.ButtonStyle.primary,
        custom_id="coinflip:again",
    )
    async def flip_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.do_flip_again(interaction)

    async def on_timeout(self) -> None:
        self.disable_all_buttons()
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class CoinflipChallengeView(discord.ui.View):
    """Vista interactiva para desafíos PvP de Coinflip con timeout de 60s."""

    def __init__(
        self,
        challenger_id: int,
        challenger: Union[discord.User, discord.Member],
        rival_id: int,
        rival: Union[discord.User, discord.Member],
        bet_amount: int,
        challenger_side: str = "cara",
        engine: Optional[CoinflipEngine] = None,
    ):
        super().__init__(timeout=60.0)
        self.challenger_id = int(challenger_id)
        self.challenger = challenger
        self.rival_id = int(rival_id)
        self.rival = rival
        self.bet_amount = bet_amount
        self.challenger_side = normalize_coinflip_side(challenger_side)
        self.rival_side = "cruz" if self.challenger_side == "cara" else "cara"
        self.engine = engine or coinflip_engine
        self.message: Optional[discord.Message] = None
        self.resolved: bool = False
        self._lock = asyncio.Lock()

    def disable_all_buttons(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    async def do_accept(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.rival_id:
            if interaction.user.id == self.challenger_id:
                await interaction.response.send_message(
                    "❌ No puedes aceptar tu propio desafío. Espera a que responda tu rival o pulsa [ 🏳️ Rechazar ] para cancelar.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"❌ Solo {getattr(self.rival, 'display_name', 'el rival')} puede aceptar este desafío.",
                    ephemeral=True,
                )
            return

        async with self._lock:
            if self.resolved:
                return

            rival_bal = get_balance(self.rival_id)
            if rival_bal["cash"] < self.bet_amount:
                self.resolved = True
                self.disable_all_buttons()
                with ECONOMY_LOCK:
                    modify_balance(self.challenger_id, cash_delta=+self.bet_amount)
                    ACTIVE_COINFLIP_DUELS.pop(str(self.challenger_id), None)
                    ACTIVE_COINFLIP_DUELS.pop(str(self.rival_id), None)
                    ACTIVE_COINFLIP_DUELS.pop(self.challenger_id, None)
                    ACTIVE_COINFLIP_DUELS.pop(self.rival_id, None)

                embed = build_coinflip_embed(
                    mode="pvp_insufficient_funds",
                    challenger=self.challenger,
                    rival=self.rival,
                    bet=self.bet_amount,
                )
                if not interaction.response.is_done():
                    await interaction.response.edit_message(content=None, embed=embed, view=self)
                elif self.message:
                    try:
                        await self.message.edit(content=None, embed=embed, view=self)
                    except Exception:
                        pass
                self.stop()
                return

            self.resolved = True
            self.disable_all_buttons()

            with ECONOMY_LOCK:
                ACTIVE_COINFLIP_DUELS.pop(str(self.challenger_id), None)
                ACTIVE_COINFLIP_DUELS.pop(str(self.rival_id), None)
                ACTIVE_COINFLIP_DUELS.pop(self.challenger_id, None)
                ACTIVE_COINFLIP_DUELS.pop(self.rival_id, None)
                res = self.engine.resolve_pvp(
                    challenger_id=self.challenger_id,
                    rival_id=self.rival_id,
                    bet_amount=self.bet_amount,
                    challenger_side=self.challenger_side,
                )

            winner_user = self.challenger if str(res["winner_id"]) == str(self.challenger_id) else self.rival
            loser_user = self.rival if str(res["winner_id"]) == str(self.challenger_id) else self.challenger

            embed = build_coinflip_embed(
                mode="pvp_result",
                challenger=self.challenger,
                rival=self.rival,
                winner=winner_user,
                loser=loser_user,
                result=res,
            )
            if not interaction.response.is_done():
                await interaction.response.edit_message(content=None, embed=embed, view=self)
            elif self.message:
                try:
                    await self.message.edit(content=None, embed=embed, view=self)
                except Exception:
                    pass
            self.stop()

    async def do_decline(self, interaction: discord.Interaction) -> None:
        if interaction.user.id not in (self.rival_id, self.challenger_id):
            await interaction.response.send_message(
                "❌ No participas en este duelo de Coinflip.",
                ephemeral=True,
            )
            return

        async with self._lock:
            if self.resolved:
                return

            self.resolved = True
            self.disable_all_buttons()

            with ECONOMY_LOCK:
                modify_balance(self.challenger_id, cash_delta=+self.bet_amount)
                ACTIVE_COINFLIP_DUELS.pop(str(self.challenger_id), None)
                ACTIVE_COINFLIP_DUELS.pop(str(self.rival_id), None)
                ACTIVE_COINFLIP_DUELS.pop(self.challenger_id, None)
                ACTIVE_COINFLIP_DUELS.pop(self.rival_id, None)

            cancelled_by = self.rival if interaction.user.id == self.rival_id else self.challenger
            embed = build_coinflip_embed(
                mode="pvp_cancelled",
                challenger=self.challenger,
                rival=self.rival,
                bet=self.bet_amount,
                cancelled_by=cancelled_by,
            )
            if not interaction.response.is_done():
                await interaction.response.edit_message(content=None, embed=embed, view=self)
            elif self.message:
                try:
                    await self.message.edit(content=None, embed=embed, view=self)
                except Exception:
                    pass
            self.stop()

    @discord.ui.button(
        label="⚔️ Aceptar Desafío",
        style=discord.ButtonStyle.success,
        custom_id="coinflip:accept",
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.do_accept(interaction)

    @discord.ui.button(
        label="🏳️ Rechazar",
        style=discord.ButtonStyle.danger,
        custom_id="coinflip:decline",
    )
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.do_decline(interaction)

    async def on_timeout(self) -> None:
        async with self._lock:
            if self.resolved:
                return

            self.resolved = True
            self.disable_all_buttons()

            with ECONOMY_LOCK:
                modify_balance(self.challenger_id, cash_delta=+self.bet_amount)
                ACTIVE_COINFLIP_DUELS.pop(str(self.challenger_id), None)
                ACTIVE_COINFLIP_DUELS.pop(str(self.rival_id), None)
                ACTIVE_COINFLIP_DUELS.pop(self.challenger_id, None)
                ACTIVE_COINFLIP_DUELS.pop(self.rival_id, None)

            embed = build_coinflip_embed(
                mode="pvp_timeout",
                challenger=self.challenger,
                rival=self.rival,
                bet=self.bet_amount,
            )
            if self.message:
                try:
                    await self.message.edit(content=None, embed=embed, view=self)
                except Exception:
                    pass


# ==========================================
# CENTRO DE CONTROL DEL CASINO (/casino)
# ==========================================

CASINO_GAMES_INFO = {
    "slots": {
        "title": "🎰 Tragaperras 5x3 — Sanvi Slots",
        "command": "`/slots [apuesta]` (ej: `/slots 100`, `/slots all`)",
        "description": "Máquina tragaperras de alta tensión con matriz 5x3 (15 casilleros) inspirada en rangos de Brawl Stars, comodines WILD y dispersores SCATTER.",
        "rtp": "**110.03% RTP** (Calibrado Monte Carlo con Hit Rate ~73.83%)",
        "paytable": (
            "• <:absolutecinema:1478115607336714300> **WILD (Comodín)**: ×15.0 / ×49.0 / ×152.0 (5 en L1 = ¡Grand Jackpot!)\n"
            "• <:Ranked_Pro:1550129987972104252> **Ranked Pro**: ×11.6 / ×37.5 / ×122.0 (5 en L1 = Grand Jackpot)\n"
            "• <:Ranked_Masters:1550129992837496833> **Ranked Masters**: ×4.7 / ×15.0 / ×46.5 (5 en L1 = Mini Jackpot)\n"
            "• <:Ranked_Legendary:1550129997774323732> **Ranked Legendary**: ×1.65 / ×5.8 / ×18.8\n"
            "• <:Ranked_Mythic:1550130000852820099> **Ranked Mythic**: ×0.78 / ×2.7 / ×8.9\n"
            "• <:Ranked_Diamond:1550130004074041434> **Ranked Diamond**: ×0.37 / ×1.2 / ×3.8\n"
            "• <:Ranked_Gold:1550130006896812084> **Ranked Gold**: ×0.19 / ×0.58 / ×1.95"
        ),
        "special_rules": (
            "• **7 Líneas Limpias**: Centro, Arriba, Abajo, V Suave, V Invertida, Diagonal Descendente y Ascendente.\n"
            "• **Free Spins a ×2**: 3, 4 o 5 Scatters otorgan 5, 8 o 12 tiradas gratis acumulativas.\n"
            "• **Pantalla Completa**: Llenar los 15 casilleros otorga pago masivo directo de **×500.0**.\n"
            "• **Bote Progresivo**: 5 Pro o Wilds en L1 ganan el 100% del Grand Jackpot. 5 Masters en L1 ganan el 25% (Mini Jackpot)."
        ),
        "color": 0xF1C40F,
    },
    "blackjack": {
        "title": "🃏 Blackjack 21 — Mesa Clásica Sanvi",
        "command": "`/blackjack [apuesta]` o `/bj [apuesta]` (ej: `/blackjack 200`, `/bj all`)",
        "description": "El clásico juego de cartas americano contra el crupier de la casa. Llega a 21 sin pasarte.",
        "rtp": "**≈ 99.50% RTP** (Estrategia básica óptima)",
        "paytable": (
            "• **Blackjack Natural (21 con 2 cartas)**: Pago **3:2** (1.5x ganancia neta).\n"
            "• **Victoria Regular**: Pago **1:1** (1x ganancia neta).\n"
            "• **Empate (Push)**: Recuperas el 100% de tu apuesta.\n"
            "• **Derrota o Pasarse (Bust)**: Pierdes la apuesta (3% alimenta el jackpot)."
        ),
        "special_rules": (
            "• **Zapato de 6 Barajas (312 cartas)**: Barajado continuo con corte de seguridad a < 52 cartas.\n"
            "• **Reglas del Crupier (S17)**: El crupier pide carta obligatoriamente con ≤ 16 y se planta en 17 o más.\n"
            "• **Doblar Apuesta (Double Down)**: En el primer turno puedes duplicar tu apuesta para recibir exactamente 1 sola carta final.\n"
            "• **Ases Dinámicos**: Los Ases computan como 11 o 1 para evitar pasarse automáticamente."
        ),
        "color": 0x2ECC71,
    },
    "ruleta": {
        "title": "🎡 Ruleta Europea — Cilindro de Montecarlo",
        "command": "`/ruleta [apuesta] [tipo]` (ej: `/ruleta 100 rojo`, `/ruleta 500 par`, `/ruleta 50 pleno 0`)",
        "description": "Ruleta europea oficial con cilindro de 37 casillas (números del 0 al 36) y regla del 0 verde.",
        "rtp": "**97.30% RTP** (Ventaja de la casa fija del 2.70% por el 0 verde)",
        "paytable": (
            "• **Suertes Sencillas (1:1)**: Rojo / Negro, Par / Impar, Pasa (19-36) / Falta (1-18).\n"
            "• **Docenas y Columnas (2:1)**: 1ª, 2ª o 3ª Docena (1-12, 13-24, 25-36) / Columna 1, 2 o 3.\n"
            "• **Pleno Directo (35:1)**: Número individual exacto (0 al 36)."
        ),
        "special_rules": (
            "• **Regla del 0 Verde**: Si la bola cae en el 0 verde, todas las apuestas de suertes sencillas, docenas y columnas pierden; sólo gana el Pleno directo al 0.\n"
            "• **Vecinos del Cilindro**: Interfaz visual interactiva que muestra las 5 casillas contiguas reales en la rueda física.\n"
            "• **Acción Rápida**: Botones interactivos `[🔄 Repetir]` y `[⚡ Duplicar x2]` tras cada tirada."
        ),
        "color": 0xE74C3C,
    },
    "coinflip": {
        "title": "🪙 Coinflip Dual — Cara o Cruz (PvE & PvP)",
        "command": "`/coinflip [apuesta] [lado] [rival]` (ej: `/coinflip 100 cara`, `/coinflip 500 cruz @rival`)",
        "description": "Lanzamiento de moneda 50/50. Juega en solitario contra la casa (PvE) o reta a cualquier miembro del servidor a un duelo de honor (PvP).",
        "rtp": "**50/50 Justo** (PvE 1:1 payout | PvP 98% a ganador, 2% jackpot)",
        "paytable": (
            "• **Modo PvE (vs Casa)**: Victoria paga **1:1** (doblas tu apuesta). Derrota descuenta apuesta (3% al bote).\n"
            "• **Modo PvP (vs Miembro)**: Bote acumulado de ambos jugadores. El ganador se lleva el **98%** del pozo y el **2%** restante alimenta el bote del servidor."
        ),
        "special_rules": (
            "• **Retención Atómica en Duelos**: La fianza del retador queda bloqueada y asegurada al lanzar el reto.\n"
            "• **Aceptación y Rechazo Interactivo**: El rival dispone de 60 segundos con botones interactivos `[⚔️ Aceptar Desafío]` y `[🏳️ Rechazar]`.\n"
            "• **Protección Total contra Timeout**: Si el rival no responde en 60s o cancela, el 100% de los fondos se reembolsa al retador inmediatamente."
        ),
        "color": 0x3498DB,
    },
}


def build_casino_hub_embed(
    user: Union[discord.User, discord.Member],
    selected_game: Optional[str] = None,
) -> discord.Embed:
    """
    Construye el embed del Hub Central del Casino (/casino):
    - Si selected_game is None: Vista General de Bienvenida con bote y saldos.
    - Si selected_game in ('slots', 'blackjack', 'ruleta', 'coinflip'): Vista Detallada del juego.
    """
    uid = getattr(user, "id", user)
    bal = get_balance(uid)
    server_jackpot = get_server_jackpot()

    if selected_game and selected_game in CASINO_GAMES_INFO:
        info = CASINO_GAMES_INFO[selected_game]
        embed = discord.Embed(
            title=info["title"],
            description=f"{info['description']}\n\n**Comando:** {info['command']}",
            color=info["color"],
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="📊 Retorno y Ventaja (RTP)", value=info["rtp"], inline=False)
        embed.add_field(name="💰 Tabla de Pagos", value=info["paytable"], inline=False)
        embed.add_field(name="⚙️ Reglas Especiales y Mecánicas", value=info["special_rules"], inline=False)
        embed.add_field(
            name="💼 Tu Cartera Actual",
            value=f"💵 Efectivo: {PORRO_EMOJI} **{bal['cash']:,}** | 🏦 Banco: {PORRO_EMOJI} **{bal['bank']:,}**",
            inline=True,
        )
        embed.add_field(
            name="🏆 Bote Progresivo Acumulado",
            value=f"{PORRO_EMOJI} **{server_jackpot:,}** Porros",
            inline=True,
        )
        embed.set_footer(
            text="Usa el menú desplegable para cambiar de juego o pulsa '🏠 Menú Principal' para volver.",
            icon_url="https://cdn.discordapp.com/emojis/1535685303317172305.webp?size=96&quality=lossless",
        )
        return embed

    # Vista General Principal
    embed = discord.Embed(
        title="🎰 Casino Central Sanvi — Salón Oficial de Juegos",
        description=(
            "¡Bienvenido al salón de azar oficial de Sanvi! Todos los juegos son 100% justos, "
            "transparentes y respaldados por la economía nativa de **Porros**.\n\n"
            f"🏆 **Bote Acumulado del Servidor:**\n"
            f"> {PORRO_EMOJI} **{server_jackpot:,}** Porros en juego\n"
            f"> *(Una fracción de las pérdidas netas y duelos alimenta continuamente el bote)*\n"
        ),
        color=0xF1C40F,
        timestamp=datetime.now(timezone.utc),
    )

    embed.add_field(
        name="💼 Tu Balance Personal",
        value=(
            f"• 💵 **Efectivo:** {PORRO_EMOJI} **{bal['cash']:,}** Porros\n"
            f"• 🏦 **Banco:** {PORRO_EMOJI} **{bal['bank']:,}** Porros\n"
            f"• 📈 **Total:** {PORRO_EMOJI} **{bal['total']:,}** Porros"
        ),
        inline=False,
    )

    embed.add_field(
        name="🎮 Catálogo Oficial de Juegos Activos",
        value=(
            "• 🎰 **Tragaperras 5x3** (`/slots [apuesta]`): RTP 110.03% • 7 Líneas • Free Spins • Bote Progresivo\n"
            "• 🃏 **Blackjack 21** (`/blackjack [apuesta]`): 6 Barajas • Crupier S17 • Pago 3:2 • Doblar apuesta\n"
            "• 🎡 **Ruleta Europea** (`/ruleta [apuesta] [tipo]`): 37 Casillas • RTP 97.30% • Suertes sencillas • Pleno 35:1\n"
            "• 🪙 **Coinflip Dual** (`/coinflip [apuesta] [lado] [rival]`): Modo PvE 50/50 y Duelos PvP 1v1 entre miembros"
        ),
        inline=False,
    )

    embed.set_footer(
        text="Selecciona un juego en el menú desplegable inferior para ver sus reglas, pagos y sintaxis.",
        icon_url="https://cdn.discordapp.com/emojis/1535685303317172305.webp?size=96&quality=lossless",
    )
    return embed


class CasinoHubSelect(discord.ui.Select):
    """Menú desplegable con las 4 opciones de juego del Casino Central."""

    def __init__(self):
        options = [
            discord.SelectOption(
                label="🎰 Tragaperras 5x3",
                value="slots",
                description="RTP 110.03% • 7 Líneas • Free Spins • Bote Progresivo",
                emoji="🎰",
            ),
            discord.SelectOption(
                label="🃏 Blackjack 21",
                value="blackjack",
                description="6 Barajas • Crupier S17 • Pago 3:2 • Doblar apuesta",
                emoji="🃏",
            ),
            discord.SelectOption(
                label="🎡 Ruleta Europea",
                value="ruleta",
                description="37 Casillas • RTP 97.30% • Suertes sencillas • Pleno 35:1",
                emoji="🎡",
            ),
            discord.SelectOption(
                label="🪙 Coinflip Dual",
                value="coinflip",
                description="Modo PvE 50/50 y Duelos PvP 1v1 entre miembros",
                emoji="🪙",
            ),
        ]
        super().__init__(
            placeholder="🎲 Selecciona un juego para ver detalles y reglas...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        view: "CasinoHubView" = self.view
        if interaction.user.id != view.author_id:
            await interaction.response.send_message(
                "❌ Este panel del Casino pertenece a otro usuario. Usa `/casino` para abrir el tuyo.",
                ephemeral=True,
            )
            return

        selected_game = self.values[0]
        view.current_game = selected_game
        embed = build_casino_hub_embed(interaction.user, selected_game=selected_game)
        await interaction.response.edit_message(embed=embed, view=view)


class CasinoHubView(discord.ui.View):
    """
    Vista interactiva del Centro de Control del Casino (/casino):
    - Select con las 4 opciones de juego.
    - Botón '🏠 Menú Principal' para regresar a la vista general.
    - Control de permisos exclusivo para el autor (bloqueo efímero a terceros).
    - Timeout de 90 segundos que desactiva los controles sin crash.
    """

    def __init__(self, author_id: Any, timeout: float = 90.0):
        super().__init__(timeout=timeout)
        self.author_id = int(author_id)
        self.current_game: Optional[str] = None
        self.message: Optional[discord.Message] = None

        self.select_menu = CasinoHubSelect()
        self.add_item(self.select_menu)

    @discord.ui.button(
        label="🏠 Menú Principal",
        style=discord.ButtonStyle.secondary,
        row=1,
        custom_id="casino:home",
    )
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Este panel del Casino pertenece a otro usuario. Usa `/casino` para abrir el tuyo.",
                ephemeral=True,
            )
            return

        self.current_game = None
        embed = build_casino_hub_embed(interaction.user, selected_game=None)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass





