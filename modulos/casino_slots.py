"""
Módulo de Tragaperras 5x3 (/slots) de Alta Tensión para 'Asistente':
- Matriz 5x3 (15 casilleros) con 7 símbolos: 6 Brawl Stars Ranked y WILD (sin Scatters).
- 9 Líneas de pago limpias: 3 Horizontales completas (5 casillas con ventanas consecutivas) + 6 Diagonales rectas de 3 casillas.
- Pantalla completa a x500.0 y Bote Progresivo (Grand y Mini).
- Calibrado a RTP 110.0% (+/- 0.5%) y Hit Rate ~70.9%.
- Componentes Discord V2 (LayoutView, Container, TextDisplay, ActionRow).
"""

import os
import sys
import random
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Union

import discord
from discord.enums import SeparatorSpacing
from discord.ui import LayoutView, Container, Separator, TextDisplay, ActionRow, Button

from modulos.economia_core import (
    PORRO_EMOJI,
    ECONOMY_LOCK,
    _bot_log,
    _bs,
    ensure_user,
    get_balance,
    modify_balance,
    get_server_jackpot,
    modify_server_jackpot,
    reset_server_jackpot,
    JACKPOT_FEED_PERCENT,
)

MIN_SLOTS_BET = 100
MIN_BLACKJACK_BET = 100
MIN_ROULETTE_BET = 100
MIN_COINFLIP_BET = 100

# Símbolos oficiales de Tragaperras 5x3: 6 Brawl Stars Ranked + WILD
# Suma de pesos = 40 + 25 + 15 + 10 + 5 + 3 + 2 = 100
# Calibrado a RTP 110.0% (+/- 0.5%) y Hit Rate ~70.9% con 3 Horizontales y 6 Diagonales
SLOT_SYMBOLS = {
    "Gold": {
        "id": "1550130006896812084",
        "emoji": "<:Ranked_Gold:1550130006896812084>",
        "name": "Ranked_Gold",
        "mults": {3: 0.32, 4: 1.20, 5: 4.00},
        "weight": 40,
    },
    "Diamond": {
        "id": "1550130004074041434",
        "emoji": "<:Ranked_Diamond:1550130004074041434>",
        "name": "Ranked_Diamond",
        "mults": {3: 0.70, 4: 2.35, 5: 7.80},
        "weight": 25,
    },
    "Mythic": {
        "id": "1550130000852820099",
        "emoji": "<:Ranked_Mythic:1550130000852820099>",
        "name": "Ranked_Mythic",
        "mults": {3: 1.50, 4: 5.20, 5: 17.50},
        "weight": 15,
    },
    "Legendary": {
        "id": "1550129997774323732",
        "emoji": "<:Ranked_Legendary:1550129997774323732>",
        "name": "Ranked_Legendary",
        "mults": {3: 3.50, 4: 12.00, 5: 38.00},
        "weight": 10,
    },
    "Masters": {
        "id": "1550129992837496833",
        "emoji": "<:Ranked_Masters:1550129992837496833>",
        "name": "Ranked_Masters",
        "mults": {3: 9.00, 4: 30.00, 5: 92.00},
        "weight": 5,
    },
    "Pro": {
        "id": "1550129987972104252",
        "emoji": "<:Ranked_Pro:1550129987972104252>",
        "name": "Ranked_Pro",
        "mults": {3: 22.00, 4: 75.00, 5: 240.00},
        "weight": 3,
    },
    "Wild": {
        "id": "1478115607336714300",
        "emoji": "<:absolutecinema:1478115607336714300>",
        "name": "WILD",
        "mults": {3: 30.00, 4: 95.00, 5: 290.00},
        "weight": 2,
    },
}

# Las 9 Líneas de pago limpias aprobadas por Jose en matriz 5x3 (3 Horizontales + 6 Diagonales de 3 casillas)
SLOT_PAYLINES = [
    ("Línea Arriba", [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]),
    ("Línea Centro", [(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)]),
    ("Línea Abajo", [(2, 0), (2, 1), (2, 2), (2, 3), (2, 4)]),
    ("Diagonal Descendente", [(0, 0), (1, 1), (2, 2)]),
    ("Diagonal Descendente", [(0, 1), (1, 2), (2, 3)]),
    ("Diagonal Descendente", [(0, 2), (1, 3), (2, 4)]),
    ("Diagonal Ascendente", [(2, 0), (1, 1), (0, 2)]),
    ("Diagonal Ascendente", [(2, 1), (1, 2), (0, 3)]),
    ("Diagonal Ascendente", [(2, 2), (1, 3), (0, 4)]),
]



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
        Evalúa una línea de pago en matriz 5x3:
        - Si la línea tiene 3 casillas (diagonales D1-D6): evalúa si las 3 casillas coinciden (k=3).
        - Si la línea tiene 5 casillas (horizontales L1-L3): evalúa ventanas consecutivas de tamaño
          k = 5, 4, 3 en cualquier posición de la fila, priorizando mayor k y mayor multiplicador.
        Wild sustituye a cualquier regular; una racha de Wilds puros también premia.
        Devuelve (best_sym, best_count, best_mult).
        """
        regular_keys = ["Gold", "Diamond", "Mythic", "Legendary", "Masters", "Pro"]

        if len(line_syms) == 3:
            if all(s == "Wild" for s in line_syms):
                w_mult = self.symbols["Wild"]["mults"].get(3, 0.0)
                if w_mult > 0:
                    return "Wild", 3, w_mult
            nw = [s for s in line_syms if s != "Wild"]
            if len(nw) > 0 and all(s == nw[0] for s in nw) and nw[0] in regular_keys:
                reg = nw[0]
                reg_mult = self.symbols[reg]["mults"].get(3, 0.0)
                if reg_mult > 0:
                    return reg, 3, reg_mult
            return None, 0, 0.0

        # Horizontales (5 casillas): evaluar k in (5, 4, 3) con ventanas consecutivas
        for k in (5, 4, 3):
            best_cand = None
            best_mult = 0.0
            for start in range(len(line_syms) - k + 1):
                window = line_syms[start:start+k]
                if all(s == "Wild" for s in window):
                    w_mult = self.symbols["Wild"]["mults"].get(k, 0.0)
                    if w_mult > best_mult:
                        best_mult = w_mult
                        best_cand = ("Wild", k, w_mult)
                else:
                    nw = [s for s in window if s != "Wild"]
                    if len(nw) > 0 and all(s == nw[0] for s in nw) and nw[0] in regular_keys:
                        reg = nw[0]
                        reg_mult = self.symbols[reg]["mults"].get(k, 0.0)
                        if reg_mult > best_mult:
                            best_mult = reg_mult
                            best_cand = (reg, k, reg_mult)
            if best_cand is not None:
                return best_cand

        return None, 0, 0.0

    def evaluate(
        self,
        grid: List[List[str]],
        bet: int,
        multiplier: float = 1.0,
        is_free_spin: bool = False,
    ) -> Dict[str, Any]:
        """
        Evalúa las 9 líneas de pago limpias aprobadas por Jose, Pantalla Completa,
        comodines WILD, multiplicadores y botes progresivos.
        """
        winning_lines = []
        total_mult = 0.0

        # 1. Evaluación de las 9 Líneas de Pago Limpias (3 Horizontales + 6 Diagonales)
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

        payout = int(bet * total_mult)
        net = payout - (0 if is_free_spin else bet)

        # 3. Detección de Botes Progresivos en la Línea Central (L1: 5 casillas)
        l1_syms = [grid[1][c] for c in range(5)]
        grand_jackpot_hit = (
            all(s == "Pro" for s in l1_syms) or
            all(s == "Wild" for s in l1_syms)
        )
        mini_jackpot_hit = all(s == "Masters" for s in l1_syms)

        # 4. Título y color según el resultado
        if grand_jackpot_hit:
            title = "### 💥 ¡¡GRAND JACKPOT DEL SERVIDOR!! 💥"
            accent_color = 16766720  # Dorado intenso
        elif mini_jackpot_hit:
            title = "### 💎 ¡¡MINI JACKPOT DEL SERVIDOR!! 💎"
            accent_color = 16766720  # Dorado
        elif full_screen_hit:
            title = "### 🌟 ¡¡PANTALLA COMPLETA 15/15!! 🌟"
            accent_color = 16766720
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
            "grand_jackpot_hit": grand_jackpot_hit,
            "mini_jackpot_hit": mini_jackpot_hit,
            "full_screen_hit": full_screen_hit,
            "scatter_count": 0,
            "free_spins_triggered": False,
            "free_spins_count": 0,
            "free_spins_multiplier": 1,
            "is_free_spin": is_free_spin,
        }

    def simulate_monte_carlo(self, spins: int = 100000, bet: int = 1000) -> Dict[str, Any]:
        """Simula N tiradas para validar matemáticamente el RTP (110.0%) y Hit Rate."""
        total_bet = spins * bet
        total_payout = 0
        wins_count = 0
        multi_line_wins = 0
        symbol_hits = {k: 0 for k in self.symbol_keys}

        for _ in range(spins):
            grid = self.spin_grid()
            res = self.evaluate(grid, bet)
            spin_payout = res["payout"]
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

        payout_str = f"{result['payout']:,}"
        content_parts.append(f"\n**Payout:** {PORRO_EMOJI}{payout_str}")

        body_text = "\n".join(content_parts)

        bet = result["bet"]
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
        "La máquina evalúa **9 líneas de pago limpias reales** en cuadrícula de 5 rodillos × 3 filas:",
        "• **Horizontales**: Línea Arriba, Línea Centro, Línea Abajo (premia por 3, 4 o 5 seguidos en la fila).",
        "• **Diagonales**: Diagonales Descendentes y Ascendentes (premia por 3 aciertos en línea recta).",
        "",
        "**Multiplicadores por acierto (3 / 4 / 5 aciertos):**",
        "• <:absolutecinema:1478115607336714300> **WILD (Comodín)**: **×30.0** / **×95.0** / **×290.0** — Sustituye a cualquier regular. 5 en Línea Centro = ¡Grand Jackpot!",
        "• <:Ranked_Pro:1550129987972104252> **Ranked Pro**: **×22.0** / **×75.0** / **×240.0** — 5 en Línea Centro = **Grand Jackpot** (100% bote).",
        "• <:Ranked_Masters:1550129992837496833> **Ranked Masters**: **×9.0** / **×30.0** / **×92.0** — 5 en Línea Centro = **Mini Jackpot** (25% bote).",
        "• <:Ranked_Legendary:1550129997774323732> **Ranked Legendary**: **×3.5** / **×12.0** / **×38.0**",
        "• <:Ranked_Mythic:1550130000852820099> **Ranked Mythic**: **×1.5** / **×5.2** / **×17.5**",
        "• <:Ranked_Diamond:1550130004074041434> **Ranked Diamond**: **×0.70** / **×2.35** / **×7.8**",
        "• <:Ranked_Gold:1550130006896812084> **Ranked Gold**: **×0.32** / **×1.20** / **×4.0**",
        "",
        "**Patrones Especiales y Bote:**",
        "• 🌟 **Pantalla Completa (15 casilleros)**: **×500.0** directo al llenar toda la cuadrícula del mismo símbolo o Wilds.",
        f"• 💰 **Bote Progresivo Acumulado:** {PORRO_EMOJI} **{jackpot:,}** Porros *(3% de pérdidas netas alimenta el bote)*",
    ]
    return "\n".join(lines)



def handle_slots_spin(user_id: Any, bet: int) -> Tuple[bool, str, Optional[Dict[str, Any]], Optional[Dict[str, int]]]:
    """Ejecuta el ciclo de una tirada de slots 5x3 de forma segura."""
    uid = str(user_id)
    if bet < MIN_SLOTS_BET:
        return False, f"La apuesta mínima en la tragaperras es de {MIN_SLOTS_BET} Porros.", None, None

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
            try:
                from modulos.bolsa_sanvi import add_to_dividend_pool
                add_to_dividend_pool(int(loss * 0.01))
            except Exception:
                pass

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

        payout_str = f"{result['payout']:,}"
        content_parts.append(f"\n**Payout:** {PORRO_EMOJI}{payout_str}")

        body_text = "\n".join(content_parts)

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



