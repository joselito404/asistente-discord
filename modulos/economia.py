"""
Módulo de Economía Nativa y Minijuego de Tragaperras V2 de Alta Tensión para 'Asistente':
- Moneda oficial: Porros (<:Porro:1535685303317172305>).
- Almacenamiento seguro y atómico en 'datos/economia.json' con thread-safety (RLock).
- Gestión de saldos: get_balance, modify_balance, transfer_funds.
- Sistema de trabajo (/trabajar): retribución balanceada y textos cómicos del servidor con cooldown de 2 horas.
- Máquina tragaperras V2 (/slots):
  * Matriz 3x3 y 8 símbolos: 6 Brawl Stars Ranked, Comodín WILD (<:absolutecinema:1478115607336714300>) y Dispersor SCATTER (<:Porro:1535685303317172305>).
  * 9 Líneas de Pago Reales evaluadas simultáneamente de izquierda a derecha.
  * Ronda de Bonus de 5 Tiradas Gratis (Free Spins) con multiplicador x2 al obtener 3+ Scatters.
  * Bote Progresivo Escalonado: Grand Jackpot (100% bote) y Mini Jackpot (25% bote).
  * Calibración Monte Carlo a RTP 110% (High Payouts EV+ ordenado por Jose).
  * Componentes Discord V2: Container (tipo 17), Separator (tipo 14), TextDisplay (tipo 10) y ActionRow (tipo 1).
"""

import os
import sys
import json
import random
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

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
JACKPOT_FEED_PERCENT = 0.03  # 3% de pérdidas va al bote del servidor

ECONOMY_LOCK = threading.RLock()

# Símbolos oficiales de Tragaperras V2: 6 Brawl Stars Ranked + WILD + SCATTER
# Suma de pesos = 38 + 24 + 15 + 9 + 5 + 3 + 2 + 4 = 100
# Calibrado a RTP 110.0% (+/- 0.5%) y Hit Rate ~46.3% con 9 líneas y Free Spins
SLOT_SYMBOLS = {
    "Gold": {
        "id": "1550130006896812084",
        "emoji": "<:Ranked_Gold:1550130006896812084>",
        "name": "Ranked_Gold",
        "mult": 0.86,
        "weight": 38,  # Común (~38%)
    },
    "Diamond": {
        "id": "1550130004074041434",
        "emoji": "<:Ranked_Diamond:1550130004074041434>",
        "name": "Ranked_Diamond",
        "mult": 1.68,
        "weight": 24,  # Poco común
    },
    "Mythic": {
        "id": "1550130000852820099",
        "emoji": "<:Ranked_Mythic:1550130000852820099>",
        "name": "Ranked_Mythic",
        "mult": 3.0,
        "weight": 15,  # Raro
    },
    "Legendary": {
        "id": "1550129997774323732",
        "emoji": "<:Ranked_Legendary:1550129997774323732>",
        "name": "Ranked_Legendary",
        "mult": 5.8,
        "weight": 9,   # Épico
    },
    "Masters": {
        "id": "1550129992837496833",
        "emoji": "<:Ranked_Masters:1550129992837496833>",
        "name": "Ranked_Masters",
        "mult": 15.0,
        "weight": 5,   # Mítico (Mini Jackpot en L1)
    },
    "Pro": {
        "id": "1550129987972104252",
        "emoji": "<:Ranked_Pro:1550129987972104252>",
        "name": "Ranked_Pro",
        "mult": 32.0,
        "weight": 3,   # Jackpot Supremo (Grand Jackpot en L1)
    },
    "Wild": {
        "id": "1478115607336714300",
        "emoji": "<:absolutecinema:1478115607336714300>",
        "name": "WILD",
        "mult": 65.0,
        "weight": 2,   # Comodín Universal (Grand Jackpot en L1 si 3 Wilds)
    },
    "Scatter": {
        "id": "1535685303317172305",
        "emoji": "<:Porro:1535685303317172305>",
        "name": "SCATTER",
        "mult": 5.0,
        "weight": 4,   # Dispersor: Paga en cualquier posición y activa 5 Free Spins a x2
    },
}

# 9 Líneas de pago reales evaluadas simultáneamente en la matriz 3x3 (izquierda a derecha)
SLOT_PAYLINES = [
    ("L1: Centro", [(1, 0), (1, 1), (1, 2)]),
    ("L2: Arriba", [(0, 0), (0, 1), (0, 2)]),
    ("L3: Abajo", [(2, 0), (2, 1), (2, 2)]),
    ("L4: Diagonal ↘︎", [(0, 0), (1, 1), (2, 2)]),
    ("L5: Diagonal ↗︎", [(2, 0), (1, 1), (0, 2)]),
    ("L6: Zig-Zag V", [(0, 0), (1, 1), (0, 2)]),
    ("L7: Zig-Zag V Invertida", [(2, 0), (1, 1), (2, 2)]),
    ("L8: Onda Descendente", [(0, 0), (0, 1), (1, 2)]),
    ("L9: Onda Ascendente", [(2, 0), (2, 1), (1, 2)]),
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
            "version": "1.0",
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
                "inventory": [],
                "portfolio": {},
            }
            save_economy_data(data)
        else:
            user = users[uid]
            modified = False
            if "cash" not in user:
                user["cash"] = default_cash
                modified = True
            if "bank" not in user:
                user["bank"] = DEFAULT_STARTING_BANK
                modified = True
            if "last_work" not in user:
                user["last_work"] = None
                modified = True
            if "inventory" not in user:
                user["inventory"] = []
                modified = True
            if "portfolio" not in user:
                user["portfolio"] = {}
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
# MOTOR DE LA MÁQUINA TRAGAPERRAS V2 (SLOTS)
# ==========================================

class SlotEngine:
    """Motor y evaluación de combinaciones para la máquina tragaperras V2 de Alta Tensión."""

    def __init__(self, symbols_dict: Optional[Dict[str, Any]] = None):
        self.symbols = symbols_dict or SLOT_SYMBOLS
        self.symbol_keys = list(self.symbols.keys())
        self.weights = [self.symbols[k]["weight"] for k in self.symbol_keys]

    def spin_grid(self) -> List[List[str]]:
        """Genera una matriz 3x3 de símbolos usando pesos calibrados."""
        grid = []
        for _ in range(3):
            row = random.choices(self.symbol_keys, weights=self.weights, k=3)
            grid.append(row)
        return grid

    def evaluate(
        self,
        grid: List[List[str]],
        bet: int,
        multiplier: float = 1.0,
        is_free_spin: bool = False,
    ) -> Dict[str, Any]:
        """
        Evalúa las 9 líneas de pago reales, comodines WILD, dispersores SCATTER,
        multiplicadores acumulados y rondas de Free Spins.
        """
        winning_lines = []
        total_mult = 0.0

        # 1. Evaluación de las 9 Líneas de Pago (con comodín WILD)
        for line_name, coords in SLOT_PAYLINES:
            s0 = grid[coords[0][0]][coords[0][1]]
            s1 = grid[coords[1][0]][coords[1][1]]
            s2 = grid[coords[2][0]][coords[2][1]]

            # Caso 1: 3 Comodines WILD en la línea
            if s0 == "Wild" and s1 == "Wild" and s2 == "Wild":
                sym_data = self.symbols["Wild"]
                mult = sym_data["mult"] * multiplier
                total_mult += mult
                winning_lines.append({
                    "line": line_name,
                    "symbol": "Wild",
                    "emoji": sym_data["emoji"],
                    "mult": round(mult, 2),
                })
            else:
                syms = [s0, s1, s2]
                # El Scatter no forma líneas regulares; solo símbolos regulares y Wilds
                if "Scatter" not in syms:
                    non_wild = [s for s in syms if s != "Wild"]
                    # Línea válida si todos los símbolos no-wild son iguales
                    if len(non_wild) > 0 and all(s == non_wild[0] for s in non_wild):
                        matched_sym = non_wild[0]
                        sym_data = self.symbols[matched_sym]
                        mult = sym_data["mult"] * multiplier
                        total_mult += mult
                        winning_lines.append({
                            "line": line_name,
                            "symbol": matched_sym,
                            "emoji": sym_data["emoji"],
                            "mult": round(mult, 2),
                        })

        # 2. Evaluación de Dispersores SCATTER (cualquier posición en los 9 casilleros)
        scatter_count = sum(row.count("Scatter") for row in grid)
        free_spins_triggered = False
        free_spins_count = 0
        free_spins_multiplier = 1

        if scatter_count >= 3:
            sc_data = self.symbols["Scatter"]
            sc_mult = sc_data["mult"] * multiplier
            total_mult += sc_mult
            winning_lines.append({
                "line": f"Scatter ({scatter_count} Porros)",
                "symbol": "Scatter",
                "emoji": sc_data["emoji"],
                "mult": round(sc_mult, 2),
            })
            free_spins_triggered = True
            # En tirada base otorga 5; si ya está en free spins otorga +3 por re-trigger
            free_spins_count = 3 if is_free_spin else 5
            free_spins_multiplier = 2

        payout = int(bet * total_mult)
        net = payout - (0 if is_free_spin else bet)

        # 3. Detección de Botes Progresivos en la Línea Central (L1)
        # L1: (1,0), (1,1), (1,2)
        l1_s0 = grid[1][0]
        l1_s1 = grid[1][1]
        l1_s2 = grid[1][2]

        grand_jackpot_hit = (
            (l1_s0 == "Pro" and l1_s1 == "Pro" and l1_s2 == "Pro") or
            (l1_s0 == "Wild" and l1_s1 == "Wild" and l1_s2 == "Wild")
        )
        mini_jackpot_hit = (l1_s0 == "Masters" and l1_s1 == "Masters" and l1_s2 == "Masters")

        # 4. Determinación de título y color según resultado
        if grand_jackpot_hit:
            title = "### 💥 ¡¡GRAND JACKPOT DEL SERVIDOR!! 💥"
            accent_color = 16766720  # Dorado intenso
        elif mini_jackpot_hit:
            title = "### 💎 ¡¡MINI JACKPOT DEL SERVIDOR!! 💎"
            accent_color = 16766720  # Dorado
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
            "is_free_spin": is_free_spin,
        }

    def simulate_monte_carlo(self, spins: int = 100000, bet: int = 1000) -> Dict[str, Any]:
        """
        Simula N tiradas para validar matemáticamente el RTP (calibrado a 110%)
        y la frecuencia de aciertos con las 9 líneas, Wilds y Free Spins.
        """
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

            # Si se activan free spins en la tirada base, se juega la ronda completa a x2
            if res.get("free_spins_triggered"):
                scatters_hit += 1
                fs_rem = res.get("free_spins_count", 5)
                while fs_rem > 0:
                    free_spins_played += 1
                    fs_rem -= 1
                    fs_grid = self.spin_grid()
                    fs_res = self.evaluate(fs_grid, bet, multiplier=2.0, is_free_spin=True)
                    spin_payout += fs_res["payout"]
                    # Re-trigger en tirada gratis añade +3 giros
                    if fs_res.get("free_spins_triggered"):
                        fs_rem += fs_res.get("free_spins_count", 3)

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

        # Mensajes temáticos de Free Spins
        if result.get("free_spins_triggered") and not result.get("is_free_spin"):
            sc_c = result.get("scatter_count", 3)
            content_parts.append(
                f"\n🎉 **¡BONUS DESBLOQUEADO!** {sc_c} Scatters <:Porro:1535685303317172305> en pantalla.\n"
                f"¡Premio de consolación y **5 Tiradas Gratis (Free Spins)** con multiplicador **×2**!"
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

        # Construcción de botones interactivos
        bet = result["bet"]
        if result.get("free_spins_triggered") and not result.get("is_free_spin"):
            action_buttons = [
                {
                    "type": 2,
                    "id": 7,
                    "custom_id": f"slots:free-spin:{user_id}:{bet}:5:2:0",
                    "style": 3,  # Success (Green)
                    "label": "🌀 Jugar Tiradas Gratis (5 restantes)",
                },
                {
                    "type": 2,
                    "id": 8,
                    "custom_id": "slots:payouts",
                    "style": 2,  # Secondary
                    "label": "Payouts",
                },
            ]
        elif result.get("is_free_spin") and remaining_free_spins > 0:
            action_buttons = [
                {
                    "type": 2,
                    "id": 7,
                    "custom_id": f"slots:free-spin:{user_id}:{bet}:{remaining_free_spins}:2:{total_bonus_won}",
                    "style": 1,  # Primary
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
                    "style": 1,  # Primary (Blurple)
                    "label": "Play Again",
                },
                {
                    "type": 2,
                    "id": 8,
                    "custom_id": "slots:payouts",
                    "style": 2,  # Secondary (Grey)
                    "label": "Payouts",
                },
            ]

        components = [
            {
                "type": 17,  # Container
                "id": 1,
                "accent_color": result["accent_color"],
                "components": [
                    {
                        "type": 10,  # Text
                        "id": 2,
                        "content": result["title"],
                    },
                    {
                        "type": 14,  # Divider
                        "id": 3,
                        "spacing": 1,
                        "divider": True,
                    },
                    {
                        "type": 10,  # Text
                        "id": 4,
                        "content": body_text,
                    },
                    {
                        "type": 14,  # Divider
                        "id": 5,
                        "spacing": 1,
                        "divider": True,
                    },
                    {
                        "type": 1,  # ActionRow
                        "id": 6,
                        "components": action_buttons,
                    },
                ],
                "spoiler": False,
            }
        ]

        return {
            "flags": 32768,  # Is components v2 message
            "components": components,
        }


# Instancia global del motor de tragaperras
slot_engine = SlotEngine()


def build_payouts_text() -> str:
    """Genera el texto de ayuda con la tabla de pagos y estado del bote del servidor."""
    jackpot = get_server_jackpot()
    lines = [
        "🎰 **TABLA DE PAGOS Y REGLAS — TRAGAPERRAS V2 DE PORROS**",
        "La máquina evalúa **9 líneas de pago reales simultáneas** en cuadrícula de 3×3 (izquierda a derecha):",
        "• **L1**: Centro `[(1,0), (1,1), (1,2)]` | **L2**: Arriba | **L3**: Abajo",
        "• **L4**: Diagonal ↘︎ | **L5**: Diagonal ↗︎ | **L6**: Zig-Zag V `(Arriba-Centro-Arriba)`",
        "• **L7**: Zig-Zag V Invertida | **L8**: Onda Descendente | **L9**: Onda Ascendente",
        "",
        "**Multiplicadores por combinación de 3 símbolos:**",
        "• <:absolutecinema:1478115607336714300> **WILD (Comodín)**: **×65.0** — Sustituye a cualquier símbolo regular. 3 en L1 = ¡Grand Jackpot!",
        "• <:Porro:1535685303317172305> **SCATTER**: **×5.0** en cualquier posición. 3+ activan **5 Tiradas Gratis (Free Spins)** con multiplicador **×2**.",
        "• <:Ranked_Pro:1550129987972104252> **Ranked Pro**: **×32.0** — 3 en línea central (L1) = **Grand Jackpot** (100% del bote).",
        "• <:Ranked_Masters:1550129992837496833> **Ranked Masters**: **×15.0** — 3 en línea central (L1) = **Mini Jackpot** (25% del bote).",
        "• <:Ranked_Legendary:1550129997774323732> **Ranked Legendary**: **×5.8**",
        "• <:Ranked_Mythic:1550130000852820099> **Ranked Mythic**: **×3.0**",
        "• <:Ranked_Diamond:1550130004074041434> **Ranked Diamond**: **×1.68**",
        "• <:Ranked_Gold:1550130006896812084> **Ranked Gold**: **×0.86**",
        "",
        f"💰 **Bote Progresivo Acumulado:** {PORRO_EMOJI} **{jackpot:,}** Porros",
        "*(Un 3% de las pérdidas netas alimenta este bote progresivo)*",
        "",
        "ℹ️ *Si alineas múltiples combinaciones ganadoras en una misma tirada, los multiplicadores se suman acumulativamente.*",
    ]
    return "\n".join(lines)


def handle_slots_spin(user_id: Any, bet: int) -> Tuple[bool, str, Optional[Dict[str, Any]], Optional[Dict[str, int]]]:
    """
    Ejecuta el ciclo de una tirada de slots V2 de forma segura:
    1. Comprueba saldo en efectivo (cash).
    2. Deduce la apuesta antes de la tirada.
    3. Gira rodillos y evalúa combinaciones (9 líneas, Wilds, Scatters).
    4. Procesa Grand Jackpot (100%) o Mini Jackpot (25%) en L1.
    5. Acredita premio y añade el 3% de pérdidas al bote del servidor si procede.
    """
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

        # 1. Deducir apuesta antes de la tirada
        modify_balance(uid, cash_delta=-bet)

        # 2. Generar tirada y evaluar
        grid = slot_engine.spin_grid()
        res = slot_engine.evaluate(grid, bet)

        # 3. Comprobar Jackpots Progresivos en Línea Central (L1)
        if res.get("grand_jackpot_hit"):
            jackpot_amount = get_server_jackpot()
            res["jackpot_won"] = jackpot_amount
            res["jackpot_type"] = "grand"
            res["payout"] += jackpot_amount
            res["title"] = "### 💥 ¡¡GRAND JACKPOT DEL SERVIDOR!! 💥"
            res["accent_color"] = 16766720  # Dorado intenso
            reset_server_jackpot()
            _bot_log(f"🎰 [GRAND JACKPOT] ¡{uid} ha ganado el bote del servidor de {jackpot_amount:,} Porros!")
        elif res.get("mini_jackpot_hit"):
            curr_jp = get_server_jackpot()
            mini_amount = int(curr_jp * 0.25)
            res["jackpot_won"] = mini_amount
            res["jackpot_type"] = "mini"
            res["payout"] += mini_amount
            res["title"] = "### 💎 ¡¡MINI JACKPOT DEL SERVIDOR!! 💎"
            res["accent_color"] = 16766720  # Dorado
            modify_server_jackpot(-mini_amount)
            _bot_log(f"🎰 [MINI JACKPOT] ¡{uid} ha ganado el mini bote (25%) de {mini_amount:,} Porros!")

        # 4. Abonar premio si payout > 0
        if res["payout"] > 0:
            modify_balance(uid, cash_delta=res["payout"])

        # 5. Si hubo pérdida neta, alimentar el 3% al bote del servidor
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
            style=discord.ButtonStyle.success if remaining == 5 else discord.ButtonStyle.primary,
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
    """Vista interactiva nativa con Discord Components V2 (Container, Separator, TextDisplay y ActionRow)."""

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

        # Mensajes temáticos de Free Spins
        if result.get("free_spins_triggered") and not result.get("is_free_spin"):
            sc_c = result.get("scatter_count", 3)
            content_parts.append(
                f"\n🎉 **¡BONUS DESBLOQUEADO!** {sc_c} Scatters <:Porro:1535685303317172305> en pantalla.\n"
                f"¡Premio de consolación y **5 Tiradas Gratis (Free Spins)** con multiplicador **×2**!"
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

        # Configuración de ActionRow
        if result.get("free_spins_triggered") and not result.get("is_free_spin"):
            fs_btn = SlotsFreeSpinButton(bet, self.user_id, remaining=5, multiplier=2, total_won=0)
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
        # slots:play-again:<bet>:<user_id>
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
        # slots:free-spin:<user_id>:<bet>:<remaining>:<multiplier>:<total_bonus_won>
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
        # Generar tirada gratis con multiplicador doble (x2) sin deducir saldo
        grid = slot_engine.spin_grid()
        res = slot_engine.evaluate(grid, bet, multiplier=multiplier, is_free_spin=True)

        # Si vuelven a salir >=3 scatters, se re-triggean +3 tiradas
        if res.get("free_spins_triggered"):
            remaining += 3
            res["retrigger"] = True

        new_remaining = remaining - 1
        spin_payout = res["payout"]
        new_total_won = total_bonus_won + spin_payout

        # Acreditar la ganancia al usuario de forma atómica
        if spin_payout > 0:
            modify_balance(interaction.user.id, cash_delta=spin_payout)

        res["is_free_spin"] = True
        res["remaining_free_spins"] = new_remaining
        res["total_bonus_won"] = new_total_won

        if new_remaining > 0:
            res["title"] = f"### 🌀 Tirada Gratis (×{int(multiplier)})"
            res["accent_color"] = 10181046  # Violeta neón #9B59B6
        else:
            res["title"] = "### 🏆 ¡¡FIN DE LA RONDA DE FREE SPINS!! 🏆"
            res["accent_color"] = 16766720  # Dorado #FFC107

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

