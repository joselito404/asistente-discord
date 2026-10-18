"""
Motor de simulación y réplica exacta de la Tragaperras (Slots) de UnbelievaBoat para Asistente.
Incluye:
- Matriz 3x3 de carretes.
- 6 Símbolos Brawl Stars Ranked con multiplicadores idénticos.
- Evaluación de 5 líneas de pago (Top, Mid, Bot, Diag ↘︎, Diag ↗︎).
- Simulación Monte Carlo para calibrar RTP (Return to Player) idéntico (~93-95%).
- Generador de payload Discord V2 (Containers + Buttons) y Discord Embed.
- Función para enviar tirada de prueba real a Discord.
"""

import random
import sys
from typing import Dict, List, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==========================================
# CONSTANTES Y SÍMBOLOS OFICIALES DEL SERVIDOR
# ==========================================
PORRO_EMOJI = "<:Porro:1535685303317172305>"

SYMBOLS = {
    "Gold": {
        "id": "1550130006896812084",
        "emoji": "<:Ranked_Gold:1550130006896812084>",
        "name": "Ranked_Gold",
        "mult": 1.5,
        "weight": 42,  # Común (~42%)
    },
    "Diamond": {
        "id": "1550130004074041434",
        "emoji": "<:Ranked_Diamond:1550130004074041434>",
        "name": "Ranked_Diamond",
        "mult": 3.0,
        "weight": 26,  # Poco común
    },
    "Mythic": {
        "id": "1550130000852820099",
        "emoji": "<:Ranked_Mythic:1550130000852820099>",
        "name": "Ranked_Mythic",
        "mult": 5.0,
        "weight": 16,  # Raro
    },
    "Legendary": {
        "id": "1550129997774323732",
        "emoji": "<:Ranked_Legendary:1550129997774323732>",
        "name": "Ranked_Legendary",
        "mult": 10.0,
        "weight": 9,   # Épico
    },
    "Masters": {
        "id": "1550129992837496833",
        "emoji": "<:Ranked_Masters:1550129992837496833>",
        "name": "Ranked_Masters",
        "mult": 25.0,
        "weight": 5,   # Mítico
    },
    "Pro": {
        "id": "1550129987972104252",
        "emoji": "<:Ranked_Pro:1550129987972104252>",
        "name": "Ranked_Pro",
        "mult": 50.0,
        "weight": 2,   # Jackpot
    },
}

# 5 Líneas de pago evaluadas
PAYLINES = [
    ("Top row", [(0, 0), (0, 1), (0, 2)]),
    ("Middle row", [(1, 0), (1, 1), (1, 2)]),
    ("Bottom row", [(2, 0), (2, 1), (2, 2)]),
    ("Diagonal ↘︎", [(0, 0), (1, 1), (2, 2)]),
    ("Diagonal ↗︎", [(2, 0), (1, 1), (0, 2)]),
]


class SlotEngine:
    def __init__(self, symbols_dict: Dict = None):
        self.symbols = symbols_dict or SYMBOLS
        self.symbol_keys = list(self.symbols.keys())
        self.weights = [self.symbols[k]["weight"] for k in self.symbol_keys]

    def spin_grid(self) -> List[List[str]]:
        """Genera una matriz 3x3 de símbolos usando pesos ponderados."""
        grid = []
        for _ in range(3):
            row = random.choices(self.symbol_keys, weights=self.weights, k=3)
            grid.append(row)
        return grid

    def evaluate(self, grid: List[List[str]], bet: int) -> Dict:
        """Evalúa las 5 líneas de pago, calcula multiplicadores y ganancias."""
        winning_lines = []
        total_mult = 0.0

        for line_name, coords in PAYLINES:
            s0 = grid[coords[0][0]][coords[0][1]]
            s1 = grid[coords[1][0]][coords[1][1]]
            s2 = grid[coords[2][0]][coords[2][1]]

            if s0 == s1 == s2:
                sym_data = self.symbols[s0]
                mult = sym_data["mult"]
                total_mult += mult
                winning_lines.append({
                    "line": line_name,
                    "symbol": s0,
                    "emoji": sym_data["emoji"],
                    "mult": mult
                })

        payout = int(bet * total_mult)
        net = payout - bet

        # Determinación de título y color
        if total_mult == 0:
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
            "total_mult": total_mult,
            "payout": payout,
            "net": net,
            "winning_lines": winning_lines,
            "title": title,
            "accent_color": accent_color,
        }

    def simulate_monte_carlo(self, spins: int = 100000, bet: int = 1000) -> Dict:
        """Simula N tiradas para validar matemáticamente el RTP y volatilidad."""
        total_bet = spins * bet
        total_payout = 0
        wins_count = 0
        multi_line_wins = 0
        symbol_hits = {k: 0 for k in self.symbol_keys}

        for _ in range(spins):
            grid = self.spin_grid()
            res = self.evaluate(grid, bet)
            total_payout += res["payout"]
            if res["payout"] > 0:
                wins_count += 1
                if len(res["winning_lines"]) > 1:
                    multi_line_wins += 1
                for wl in res["winning_lines"]:
                    symbol_hits[wl["symbol"]] += 1

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

    def build_discord_v2_payload(self, result: Dict, user_id: str) -> Dict:
        """Construye el payload exacto de Discord Components V2 (Container + Dividers + Buttons)."""
        grid = result["grid"]
        grid_lines = []
        for row in grid:
            grid_lines.append(" ".join(self.symbols[k]["emoji"] for k in row))
        grid_text = "\n".join(grid_lines)

        content_parts = [grid_text]

        if result["winning_lines"]:
            lines_header = "**Winning Lines:**" if len(result["winning_lines"]) > 1 else "**Winning Line:**"
            content_parts.append("\n" + lines_header)
            for wl in result["winning_lines"]:
                content_parts.append(f"• {wl['emoji']} {wl['line']} (×{wl['mult']})")

        payout_str = f"{result['payout']:,}"
        content_parts.append(f"\n**Payout:** {PORRO_EMOJI}{payout_str}")

        body_text = "\n".join(content_parts)

        # Discord Component V2 Container payload
        components = [
            {
                "type": 17,  # Container
                "id": 1,
                "accent_color": result["accent_color"],
                "components": [
                    {
                        "type": 10,  # Text
                        "id": 2,
                        "content": result["title"]
                    },
                    {
                        "type": 14,  # Divider
                        "id": 3,
                        "spacing": 1,
                        "divider": True
                    },
                    {
                        "type": 10,  # Text
                        "id": 4,
                        "content": body_text
                    },
                    {
                        "type": 14,  # Divider
                        "id": 5,
                        "spacing": 1,
                        "divider": True
                    },
                    {
                        "type": 1,  # ActionRow
                        "id": 6,
                        "components": [
                            {
                                "type": 2,  # Button
                                "id": 7,
                                "custom_id": f"slots:play-again:{result['bet']}:{user_id}",
                                "style": 1,  # Primary (Blurple)
                                "label": "Play Again"
                            },
                            {
                                "type": 2,  # Button
                                "id": 8,
                                "custom_id": "slots:payouts",
                                "style": 2,  # Secondary (Grey)
                                "label": "Payouts"
                            }
                        ]
                    }
                ],
                "spoiler": False
            }
        ]

        return {
            "flags": 32768,  # Is components v2 message
            "components": components
        }


def send_test_to_discord(channel_id: str = "1558235213606682717", force_win: bool = False):
    from herramientas.discord_client import request
    engine = SlotEngine()
    if force_win:
        # Forzar una tirada ganadora bonita para ver el render completo
        grid = [
            ["Gold", "Gold", "Gold"],
            ["Mythic", "Legendary", "Diamond"],
            ["Diamond", "Gold", "Gold"]
        ]
        res = engine.evaluate(grid, 5000)
    else:
        grid = engine.spin_grid()
        res = engine.evaluate(grid, 5000)

    payload = engine.build_discord_v2_payload(res, "1305627063147036683")
    print(f"Enviando mensaje a {channel_id} con título {res['title']}...")
    resp = request(f"/channels/{channel_id}/messages", method="POST", data=payload)
    print("Respuesta de Discord:", resp.get("id"))
    return resp


if __name__ == "__main__":
    engine = SlotEngine()
    print("--- EJECUTANDO SIMULACIÓN MONTE CARLO (100,000 TIRADAS) ---")
    stats = engine.simulate_monte_carlo(100000, 1000)
    for k, v in stats.items():
        print(f"{k}: {v}")
    
    print("\n--- EJEMPLO DE TIRADA ALEATORIA ---")
    grid = engine.spin_grid()
    res = engine.evaluate(grid, 1000)
    print("Título:", res["title"])
    for r in grid:
        print(" ", [SYMBOLS[s]["name"] for s in r])
    print("Líneas ganadoras:", [wl['line'] + ' ' + wl['symbol'] for wl in res["winning_lines"]])
    print("Multiplicador total:", res["total_mult"])
    print("Payout:", res["payout"])

