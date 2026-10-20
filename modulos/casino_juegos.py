"""
Módulo de Juegos de Casino (Blackjack, Ruleta, Coinflip y Hub) para 'Asistente':
- Blackjack 21 nativo (zapato 6 barajas, 3:2 blackjack, doblar, timeout y concurrencia).
- Ruleta Europea de 37 casillas (0 verde, vecinos circulares, RTP 97.30%, suertes sencillas/múltiples).
- Coinflip dual (PvE contra la casa 50/50 y PvP 1v1 con aceptación de reto).
- Centro de control interactivo (/casino) con bote acumulado y reglas.
"""

import os
import sys
import random
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any, Union, Set

import discord
from discord.ui import View, Button, Select

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
    JACKPOT_FEED_PERCENT,
    MIN_BLACKJACK_BET,
    MIN_ROULETTE_BET,
    MIN_COINFLIP_BET,
)
from modulos.casino_slots import MIN_SLOTS_BET

# Alias de compatibilidad

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
    """Valida y calcula el monto de la apuesta en Porros (mínimo 100 o 'all'/'todo'/'max')."""
    bal = get_balance(user_id)
    cash = bal["cash"]
    clean_str = str(apuesta_str).strip().lower()

    if clean_str in ("all", "todo", "max"):
        bet = cash
    else:
        try:
            bet = int(clean_str)
        except ValueError:
            return False, 0, f"Cantidad de apuesta inválida. Debe ser un número entero mayor o igual a {MIN_BLACKJACK_BET} o 'all'/'todo'."

    if bet < MIN_BLACKJACK_BET:
        return False, 0, f"La apuesta mínima en Blackjack es de {MIN_BLACKJACK_BET} Porros ({PORRO_EMOJI})."

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
    """Valida y calcula el monto de la apuesta en Porros para la ruleta (mínimo 100 o 'all'/'todo'/'max')."""
    bal = get_balance(user_id)
    cash = bal["cash"]
    clean_str = str(apuesta_str).strip().lower()

    if clean_str in ("all", "todo", "max"):
        bet = cash
    else:
        try:
            bet = int(clean_str)
        except ValueError:
            return False, 0, f"Cantidad de apuesta inválida. Debe ser un número entero mayor o igual a {MIN_ROULETTE_BET} o 'all'/'todo'."

    if bet < MIN_ROULETTE_BET:
        return False, 0, f"La apuesta mínima en la Ruleta es de {MIN_ROULETTE_BET} Porros ({PORRO_EMOJI})."

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
        if bet_amount < MIN_ROULETTE_BET:
            raise ValueError(f"La apuesta mínima en la Ruleta es de {MIN_ROULETTE_BET} Porros ({PORRO_EMOJI}).")

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
    """Valida y calcula el monto de la apuesta en Porros para Coinflip (mínimo 100 o 'all'/'todo'/'max')."""
    bal = get_balance(user_id)
    cash = bal["cash"]
    clean_str = str(apuesta_str).strip().lower()

    if clean_str in ("all", "todo", "max"):
        bet = cash
    else:
        try:
            bet = int(clean_str)
        except ValueError:
            return False, 0, f"Cantidad de apuesta inválida. Debe ser un número entero mayor o igual a {MIN_COINFLIP_BET} o 'all'/'todo'."

    if bet < MIN_COINFLIP_BET:
        return False, 0, f"La apuesta mínima en Coinflip es de {MIN_COINFLIP_BET} Porros ({PORRO_EMOJI})."

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
        if bet_amount < MIN_COINFLIP_BET:
            raise ValueError(f"La apuesta mínima en Coinflip es de {MIN_COINFLIP_BET} Porros ({PORRO_EMOJI}).")

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
        "command": "`/ruleta [apuesta] [tipo]` (ej: `/ruleta 100 rojo`, `/ruleta 500 par`, `/ruleta 100 pleno 0`)",
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







ROULETTE_WHEEL_ORDER = ROULETTE_SEQUENCE
