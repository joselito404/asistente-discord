"""
Módulo de Economía Core para 'Asistente':
- Persistencia atómica de datos ('datos/economia.json') con RLock.
- Gestión de saldos (efectivo, banco, patrimonio) y bote global (jackpot).
- Operaciones bancarias: depósitos, retiradas y transferencias.
- Mecánicas de ingresos y delitos: /trabajar, /crimen, /robar y /salario.
- Clasificación de riqueza (/ranking) y panel de administración (/admin_dinero).
"""

import os
import sys
import json
import math
import random
import asyncio
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Set

import discord

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

# Canales y categoría oficiales de Economía y Casino (🎲・CASINO & ECONOMÍA・🎲)
ECONOMY_CATEGORY_ID = 1549512417610956871
ALLOWED_ECONOMY_CHANNELS = {
    1549458785485987890,  # #🎰casino-y-apuestas🎰
    1550894047382610081,  # #🎰casino-y-apuestas-2🎰
    1549512919694442547,  # #🏪tienda-y-mercado🏪
    1537574896605265970,  # #🛠️apps-solo-mods🛠️
}

# Apuestas mínimas oficiales unificadas en 100 Porros
MIN_SLOTS_BET = 100
MIN_BLACKJACK_BET = 100
MIN_ROULETTE_BET = 100
MIN_COINFLIP_BET = 100



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

        # Sinergia de Cartera (Bolsa Sanvi / Aura)
        try:
            from modulos.bolsa_sanvi import get_user_portfolio_buff
            aura_buff = get_user_portfolio_buff(uid)
            if aura_buff > 0:
                mult += aura_buff
                aura_pct = int(round(aura_buff * 100))
                mult_label = f"{mult_label} + Sinergia Aura +{aura_pct}%" if mult_label else f"Sinergia Aura +{aura_pct}%"
        except Exception:
            pass
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

        # Sinergia de Cartera (Bolsa Sanvi / Aura)
        try:
            from modulos.bolsa_sanvi import get_user_portfolio_buff
            aura_buff = get_user_portfolio_buff(uid)
            if aura_buff > 0:
                mult += aura_buff
                aura_pct = int(round(aura_buff * 100))
                mult_label = f"{mult_label} + Sinergia Aura +{aura_pct}%" if mult_label else f"Sinergia Aura +{aura_pct}%"
        except Exception:
            pass
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


def can_rob(user_id: Any, cooldown_seconds: int = 86400) -> Tuple[bool, float]:
    """Comprueba si un usuario puede robar según su cooldown (por defecto 24 horas)."""
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
    cooldown_seconds: int = 86400,
) -> Tuple[bool, str, int]:
    """
    Ejecuta un intento de robo (/robar):
    - Cooldown: 24 horas (86.400 segundos).
    - 50% probabilidad de éxito: roba entre el 20% y el 33% del efectivo (cash) de la víctima.
    - Chequeo de '🛡️ Cartera Blindada': inmunidad absoluta; el atraco falla al 100%.
    - En cualquier fallo (normal o por Cartera Blindada):
      * Multa total: 15% del efectivo del ladrón.
      * 10% del efectivo se abona a la víctima como compensación.
      * 5% del efectivo se ingresa en el server_jackpot.
    """
    r_uid = str(robber_id)
    v_uid = str(victim_id)

    if r_uid == v_uid:
        return False, "❌ No puedes robarte a ti mismo. Ve al casino si quieres perder dinero.", 0

    with ECONOMY_LOCK:
        allowed, remaining = can_rob(r_uid, cooldown_seconds)
        if not allowed:
            hours = int(remaining // 3600)
            mins = int((remaining % 3600) // 60)
            secs = int(remaining % 60)
            if hours > 0:
                time_str = f"**{hours}h {mins}m**"
            elif mins > 0:
                time_str = f"**{mins}m {secs}s**"
            else:
                time_str = f"**{secs}s**"
            return False, f"⏳ Tienes a la policía buscándote. Espera {time_str} para volver a atracar.", 0

        robber_bal = get_balance(r_uid)
        victim_bal = get_balance(v_uid)

        if victim_bal["cash"] < 100:
            return False, f"❌ La víctima está tiesa (solo tiene {victim_bal['cash']:,} Porros en efectivo). No merece el riesgo.", 0

        # Check Cartera Blindada
        if user_has_shield(v_uid, victim_member):
            total_fine = min(robber_bal["cash"], max(100, int(round(robber_bal["cash"] * 0.15)))) if robber_bal["cash"] > 0 else 0
            victim_share = int(round(total_fine * (10.0 / 15.0)))
            jackpot_share = total_fine - victim_share

            if total_fine > 0:
                modify_balance(r_uid, cash_delta=-total_fine)
            if victim_share > 0:
                modify_balance(v_uid, cash_delta=+victim_share)
            if jackpot_share > 0:
                modify_server_jackpot(jackpot_share)

            data = load_economy_data()
            data["users"][r_uid]["last_rob"] = datetime.now(timezone.utc).isoformat()
            save_economy_data(data)

            msg = (
                f"🛡️ **¡ATRACO FRUSTRADO POR CARTERA BLINDADA!**\n"
                f"La víctima posee la **`🛡️ Cartera Blindada`** activa. El sistema de electrochoque y blindaje "
                f"te ha neutralizado en el acto.\n\n"
                f"🚨 **Multa total aplicada (15%):** {PORRO_EMOJI} **{total_fine:,}** Porros\n"
                f"• 💰 Indemnización a la víctima (10%): {PORRO_EMOJI} **+{victim_share:,}** Porros\n"
                f"• 🎰 Bote acumulado del servidor (5%): {PORRO_EMOJI} **+{jackpot_share:,}** Porros"
            )
            _bot_log(f"🛡️ [Robo Bloqueado] {r_uid} intentó robar a {v_uid} (Cartera Blindada). Multa: {total_fine} Porros (Víctima: {victim_share}, Jackpot: {jackpot_share}).")
            return False, msg, -total_fine

        # Intento de robo estándar (50% éxito)
        success = random.random() < 0.50
        data = load_economy_data()
        data["users"][r_uid]["last_rob"] = datetime.now(timezone.utc).isoformat()
        save_economy_data(data)

        if success:
            steal_pct = random.uniform(0.20, 0.33)
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
            total_fine = min(robber_bal["cash"], max(100, int(round(robber_bal["cash"] * 0.15)))) if robber_bal["cash"] > 0 else 0
            victim_share = int(round(total_fine * (10.0 / 15.0)))
            jackpot_share = total_fine - victim_share

            if total_fine > 0:
                modify_balance(r_uid, cash_delta=-total_fine)
            if victim_share > 0:
                modify_balance(v_uid, cash_delta=+victim_share)
            if jackpot_share > 0:
                modify_server_jackpot(jackpot_share)

            msg = (
                f"🚨 **¡ATRACO FALLIDO!**\n"
                f"Te tropezaste con una lata haciendo un ruido tremendo y fuiste pillado in fraganti.\n\n"
                f"🚨 **Multa total aplicada (15%):** {PORRO_EMOJI} **{total_fine:,}** Porros\n"
                f"• 💰 Indemnización a la víctima (10%): {PORRO_EMOJI} **+{victim_share:,}** Porros\n"
                f"• 🎰 Bote acumulado del servidor (5%): {PORRO_EMOJI} **+{jackpot_share:,}** Porros"
            )
            _bot_log(f"🚨 [Robo Fallido] {r_uid} falló contra {v_uid}. Multa: {total_fine} Porros (Víctima: {victim_share}, Jackpot: {jackpot_share}).")
            return False, msg, -total_fine




# ==========================================
# SALARIO ACUMULATIVO CON DECAIMIENTO DEL 5%
# ==========================================

LEVEL_ROLE_MIN_LEVELS = [
    ("supremo", 100),
    ("ancestral", 90),
    ("mítico", 80),
    ("mitico", 80),
    ("legendario", 70),
    ("maestro", 60),
    ("élite", 50),
    ("elite", 50),
    ("alto rango", 40),
    ("experimentado", 30),
    ("veterano", 20),
    ("rango medio", 10),
]


def calculate_daily_salary(
    member: Optional[Any] = None,
    user_roles: Optional[List[str]] = None,
    user_level: Optional[int] = None,
) -> int:
    """
    Calcula el salario diario base (S) según el nivel exacto del usuario (Opción A progresiva)
    más el plus de podio si posee los roles correspondientes.
    """
    role_names_lower = []
    if member is not None and hasattr(member, "roles"):
        role_names_lower = [r.name.lower() for r in member.roles]
    elif user_roles:
        role_names_lower = [str(r).lower() for r in user_roles]

    inferred_role_level = 0
    for kw, min_lvl in LEVEL_ROLE_MIN_LEVELS:
        for r_name in role_names_lower:
            if kw in r_name:
                if min_lvl > inferred_role_level:
                    inferred_role_level = min_lvl
                break

    explicit_lvl = int(user_level) if user_level is not None else 0
    L = max(explicit_lvl, inferred_role_level)

    # Fórmula progresiva por nivel L (Opción A):
    if L < 10:
        base_salary = 0
    elif L < 20:
        base_salary = 2000 + (L - 10) * 200
    elif L < 30:
        base_salary = 4000 + (L - 20) * 300
    elif L < 40:
        base_salary = 7000 + (L - 30) * 450
    elif L < 50:
        base_salary = 11500 + (L - 40) * 650
    elif L < 60:
        base_salary = 18000 + (L - 50) * 1000
    elif L < 70:
        base_salary = 28000 + (L - 60) * 1400
    elif L < 80:
        base_salary = 42000 + (L - 70) * 2000
    elif L < 90:
        base_salary = 62000 + (L - 80) * 2800
    elif L < 100:
        base_salary = 90000 + (L - 90) * 4000
    else:
        base_salary = 130000 + (L - 100) * 5000

    # Plus de Podio
    podium_bonus = 0
    for r_name in role_names_lower:
        if any(kw in r_name for kw in ("top 1", "top1")):
            podium_bonus = max(podium_bonus, 8000)
        elif any(kw in r_name for kw in ("top 2", "top2")):
            podium_bonus = max(podium_bonus, 5000)
        elif any(kw in r_name for kw in ("top 3", "top3")):
            podium_bonus = max(podium_bonus, 3000)

    return base_salary + podium_bonus


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


def claim_salary(
    user_id: Any,
    member: Optional[Any] = None,
    user_roles: Optional[List[str]] = None,
    now_dt: Optional[datetime] = None,
    user_level: Optional[int] = None,
) -> Tuple[bool, str, int, int]:
    """
    Reclama el salario acumulado aplicando la fórmula de decaimiento del 5%:
    Devuelve (éxito, mensaje, salario_cobrado, salario_diario_base).
    """
    uid = str(user_id)
    with ECONOMY_LOCK:
        user = ensure_user(uid)
        last_sal_str = user.get("last_salary")
        daily_salary = calculate_daily_salary(member=member, user_roles=user_roles, user_level=user_level)

        if daily_salary <= 0:
            return (
                False,
                "❌ Necesitas alcanzar al menos el **Nivel 10 (`🔷 Pendejo de Rango Medio`)** para cobrar salario diario.",
                0,
                0,
            )

        now = now_dt or datetime.now(timezone.utc)

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



