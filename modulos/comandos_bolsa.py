"""
Módulo de Comandos Slash e Interfaces Interactivas de la Bolsa Sanvi:
- /bolsa [ticker]: Terminal bursátil estilo Trading 212 con gráfico de velas HD Pillow,
  8 temporalidades ('Trades', '15m', '1h', '4h', '1D', '1S', '1M', 'MAX'),
  selector nativo de tickers en vivo y botones interactivos.
- /cartera [usuario]: Cartera de acciones, valor actual, PnL y bono de Sinergia de Cartera para /trabajar.
- /aura [usuario]: Desglose contable de Aura (Book Value de por vida + Earnings 30d 50/50).
"""

import io
import re
from typing import Optional, Any
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ui import View, Button, Select, Modal, TextInput

from modulos.bolsa_sanvi import (
    TICKERS,
    calculate_base_price,
    calculate_market_price,
    get_bid_ask_prices,
    execute_buy_order,
    execute_sell_order,
    get_user_portfolio_aura,
    get_user_portfolio_buff,
    load_market_data,
    load_pool_data,
    calculate_rsi,
    calculate_moving_averages,
    get_ticker_technical_metrics,
    get_member_stats,
    generate_market_report,
    calculate_book_value,
    calculate_earnings_30d,
    load_cakey_history,
    CANONICAL_SEEDS,
    is_market_halted,
    get_market_halt_reason,
    set_market_halt,
    change_founder_ticker,
)
from modulos.bolsa_graficas import (
    TIMEFRAME_CONFIG,
    normalize_timeframe,
    generate_candlestick_chart,
)

EMOJI_PORRO = "<:Porro:1535685303317172305>"
EMOJI_AURA = "<:aura:1492161433260380222>"

TICKER_UI_META = {
    "JOSE": {"emoji": "👑", "tier": "Mega Cap", "desc": "Joselito · Fundador & Líder de Aura"},
    "TERRE": {"emoji": "⚡", "tier": "Large Cap", "desc": "Terre · Inversor & Pilar del Sanvi"},
    "OMEN": {"emoji": "🔥", "tier": "Large Cap", "desc": "Omen · Veterano de Voz & Chat"},
    "RACER": {"emoji": "🏎️", "tier": "Large Cap", "desc": "Racer · Velocidad & Liquidez Activa"},
}


class BolsaOrderModal(Modal):
    def __init__(self, ticker: str, action: str):
        self.ticker = ticker.upper()
        self.action = action.lower()  # "buy" o "sell"
        action_label = "Comprar" if self.action == "buy" else "Vender"
        super().__init__(title=f"{action_label} Acciones de ${self.ticker}")

        self.shares_input = TextInput(
            label="Cantidad de acciones (1 a 500)",
            placeholder="Ej: 10, 50, 100",
            min_length=1,
            max_length=4,
            required=True,
        )
        self.add_item(self.shares_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            shares = int(self.shares_input.value.strip())
        except ValueError:
            await interaction.response.send_message(
                "❌ Debes introducir un número entero válido de acciones.", ephemeral=True
            )
            return

        if shares < 1 or shares > 500:
            await interaction.response.send_message(
                "❌ La orden debe ser de entre 1 y 500 acciones (blindaje anti-ballenas).", ephemeral=True
            )
            return

        if is_market_halted():
            r = get_market_halt_reason()
            err_msg = "⛔ La Bolsa Sanvi está temporalmente suspendida por mantenimiento o emergencia."
            if r:
                err_msg += f" Motivo: {r}"
            await interaction.response.send_message(err_msg, ephemeral=True)
            return

        user_id = interaction.user.id
        if self.action == "buy":
            res = execute_buy_order(user_id, self.ticker, shares)
        else:
            res = execute_sell_order(user_id, self.ticker, shares)

        if not res.get("success"):
            await interaction.response.send_message(f"❌ {res.get('error')}", ephemeral=True)
            return

        action_name = "Compra" if self.action == "buy" else "Venta"
        price_used = res.get("ask_price") or res.get("price") or 0.0
        total = res.get("total_cost") if self.action == "buy" else res.get("total_payout", res.get("total_income", 0.0))
        fee_pool = res.get("spread_to_pool", res.get("fee_to_pool", 0.0))
        fee_burn = res.get("spread_burned", res.get("fee_burned", 0.0))
        new_holdings = res.get("user_total_shares", res.get("user_new_holdings", 0))
        new_mp = calculate_market_price(self.ticker)
        color = 0x00E676 if self.action == "buy" else 0xFF5252

        embed = discord.Embed(
            title=f"✅ Orden de {action_name} Ejecutada — ${self.ticker}",
            description=(
                f"• **Acciones operadas:** `{shares:,}` acciones\n"
                f"• **Precio de ejecución:** `{price_used:,.2f}` {EMOJI_PORRO}/acción\n"
                f"• **Importe total:** `{total:,.2f}` {EMOJI_PORRO}\n"
                f"• **Comisión Yield Pool (0.5%):** `+{fee_pool:,.2f}` {EMOJI_PORRO}\n"
                f"• **Comisión Deflacionaria (0.5%):** `-{fee_burn:,.2f}` {EMOJI_PORRO} *(quemados)*\n"
                f"• **Acciones en tu cartera:** `{new_holdings:,}` acciones\n"
                f"• **Nueva cotización:** `{new_mp:,.2f}` {EMOJI_PORRO}"
            ),
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text="Sanvi Exchange 24/7 • Automated Market Maker")
        await interaction.response.send_message(embed=embed, ephemeral=True)


def build_market_report_embed(ticker: str, report_text: str) -> discord.Embed:
    """Construye un Embed institucional elegante para el Informe IA de Sanvi Capital."""
    sym = ticker.upper().lstrip("$")
    info = TICKERS.get(sym, {"name": sym})
    tech = get_ticker_technical_metrics(sym)
    quotes = get_bid_ask_prices(sym)

    rsi = tech["rsi"]
    mas = tech["mas"]
    ema_14 = mas.get("ema_14") or tech["market_price"]
    sma_50 = mas.get("sma_50") or tech["market_price"]
    base_p = tech["base_price"]
    market_p = tech["market_price"]

    upper_rep = (report_text or "").upper()
    if "COMPRAR" in upper_rep or "BUY" in upper_rep or rsi < 38:
        color = 0x00E676
    elif "BENEFICIOS" in upper_rep or "TAKE PROFIT" in upper_rep or "VENDER" in upper_rep or rsi > 70:
        color = 0xFF5252
    else:
        color = 0x00A3FF

    embed = discord.Embed(
        title=f"🐺 Informe Institucional Sanvi Capital — ${sym} ({info.get('name', sym)})",
        description=report_text,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="💵 Cotización en Vivo",
        value=f"**{market_p:,.2f}** {EMOJI_PORRO}\nAsk `{quotes['ask']:,.2f}` | Bid `{quotes['bid']:,.2f}`",
        inline=True,
    )
    embed.add_field(
        name="🏛️ Aura Fundamental",
        value=f"**{base_p:,.2f}** {EMOJI_AURA}\nPrima: `{((market_p - base_p) / base_p * 100.0):+.2f}%`",
        inline=True,
    )
    embed.add_field(
        name="📊 RSI (14d) & Medias",
        value=f"RSI: `{rsi:.1f}`\nEMA 14: `{ema_14:.2f}` | SMA 50: `{sma_50:.2f}`",
        inline=True,
    )
    embed.set_footer(text="Sanvi Capital Research • Datos 100% sincronizados con la Terminal Bursátil")
    return embed


class BolsaTerminalView(View):
    def __init__(self, ticker: str, current_tf: str = "1D"):
        super().__init__(timeout=300)
        self.ticker = ticker.upper().lstrip("$")
        self.current_tf = normalize_timeframe(current_tf)
        self._setup_items()

    def _setup_items(self):
        self.clear_items()

        # Fila 0: 4 botones de temporalidad intradía rápida
        row0_tfs = ["Trades", "15m", "1h", "4h"]
        for tf in row0_tfs:
            style = discord.ButtonStyle.primary if tf == self.current_tf else discord.ButtonStyle.secondary
            btn = Button(
                label=tf,
                style=style,
                custom_id=f"bolsa:tf:{tf}:{self.ticker}",
                row=0,
            )
            btn.callback = self._create_tf_callback(tf)
            self.add_item(btn)

        # Fila 1: 4 botones de temporalidad macro / histórica
        row1_tfs = ["1D", "1S", "1M", "MAX"]
        for tf in row1_tfs:
            style = discord.ButtonStyle.primary if tf == self.current_tf else discord.ButtonStyle.secondary
            btn = Button(
                label=tf,
                style=style,
                custom_id=f"bolsa:tf:{tf}:{self.ticker}",
                row=1,
            )
            btn.callback = self._create_tf_callback(tf)
            self.add_item(btn)

        # Fila 2: Operativa e información
        btn_buy = Button(
            label="🛒 Comprar",
            style=discord.ButtonStyle.success,
            custom_id=f"bolsa:buy:{self.ticker}",
            row=2,
        )
        btn_buy.callback = self._btn_buy_callback
        self.add_item(btn_buy)

        btn_sell = Button(
            label="💰 Vender",
            style=discord.ButtonStyle.danger,
            custom_id=f"bolsa:sell:{self.ticker}",
            row=2,
        )
        btn_sell.callback = self._btn_sell_callback
        self.add_item(btn_sell)

        btn_report = Button(
            label="📊 Informe IA",
            style=discord.ButtonStyle.primary,
            custom_id=f"bolsa:report:{self.ticker}",
            row=2,
        )
        btn_report.callback = self._btn_report_callback
        self.add_item(btn_report)

        btn_web = Button(
            label="🌐 Web Terminal",
            style=discord.ButtonStyle.link,
            url="https://asistente-discord-sj3k.onrender.com/bolsa",
            row=2,
        )
        self.add_item(btn_web)

        # Fila 3: Desplegable Select para cambiar de acción en vivo
        options = []
        for sym, info in TICKERS.items():
            meta = TICKER_UI_META.get(sym, {"emoji": "📈", "tier": "Cap", "desc": info["name"]})
            mp = calculate_market_price(sym)
            options.append(
                discord.SelectOption(
                    label=f"${sym} — {info['name']} ({meta['tier']})",
                    value=sym,
                    description=f"Cotización: {mp:.2f} Porros · {meta['desc']}",
                    emoji=meta["emoji"],
                    default=(sym == self.ticker),
                )
            )

        ticker_select = Select(
            placeholder="🔄 Cambiar acción cotizada ($JOSE, $TERRE, $OMEN, $RACER)...",
            custom_id=f"bolsa:select:{self.current_tf}",
            options=options,
            row=3,
        )
        ticker_select.callback = self._select_ticker_callback
        self.add_item(ticker_select)

    def _create_tf_callback(self, tf: str):
        async def callback(interaction: discord.Interaction):
            await self._switch_timeframe(interaction, tf)
        return callback

    async def _btn_buy_callback(self, interaction: discord.Interaction):
        modal = BolsaOrderModal(self.ticker, "buy")
        await interaction.response.send_modal(modal)

    async def _btn_sell_callback(self, interaction: discord.Interaction):
        modal = BolsaOrderModal(self.ticker, "sell")
        await interaction.response.send_modal(modal)

    async def _btn_report_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        report_text = await generate_market_report(self.ticker, guild=interaction.guild)
        report_embed = build_market_report_embed(self.ticker, report_text)
        await interaction.followup.send(embed=report_embed, ephemeral=True)

    async def _select_ticker_callback(self, interaction: discord.Interaction):
        values = interaction.data.get("values", []) if interaction.data else []
        new_ticker = values[0].upper() if values else self.ticker
        await interaction.response.defer()
        try:
            self.ticker = new_ticker
            embed, file, new_view = await build_bolsa_terminal(self.ticker, self.current_tf)
            await interaction.edit_original_response(embed=embed, attachments=[file], view=new_view)
        except Exception as e:
            await interaction.followup.send(f"❌ Error al cambiar a ${new_ticker}: {e}", ephemeral=True)

    async def _switch_timeframe(self, interaction: discord.Interaction, tf: str):
        await interaction.response.defer()
        try:
            canon_tf = normalize_timeframe(tf)
            self.current_tf = canon_tf
            embed, file, new_view = await build_bolsa_terminal(self.ticker, canon_tf)
            await interaction.edit_original_response(embed=embed, attachments=[file], view=new_view)
        except Exception as e:
            await interaction.followup.send(f"❌ Error al cambiar temporalidad a {tf}: {e}", ephemeral=True)


async def handle_bolsa_interaction(interaction: discord.Interaction) -> bool:
    """Intermediario global para capturar y procesar cualquier botón o desplegable de la Bolsa Sanvi."""
    if interaction.type != discord.InteractionType.component:
        return False

    custom_id = interaction.data.get("custom_id", "")
    if not custom_id.startswith("bolsa:"):
        return False

    parts = custom_id.split(":")
    action = parts[1] if len(parts) >= 2 else ""

    # Caso desplegable de selección de Ticker: bolsa:select:<tf>
    if action == "select":
        tf_raw = parts[2] if len(parts) >= 3 else "1D"
        tf = normalize_timeframe(tf_raw)
        values = interaction.data.get("values", [])
        new_ticker = values[0].upper() if values else "JOSE"
        if new_ticker not in TICKERS:
            new_ticker = "JOSE"
        await interaction.response.defer()
        try:
            embed, file, view = await build_bolsa_terminal(new_ticker, tf)
            await interaction.edit_original_response(embed=embed, attachments=[file], view=view)
            return True
        except Exception as e:
            await interaction.followup.send(f"❌ Error al cambiar a ${new_ticker}: {e}", ephemeral=True)
            return True

    # Identificar ticker para acciones buy, sell, report y tf
    ticker = None
    if len(parts) >= 3 and parts[2].upper() in TICKERS:
        ticker = parts[2].upper()
    elif len(parts) >= 4 and parts[3].upper() in TICKERS:
        ticker = parts[3].upper()
    else:
        if interaction.message and interaction.message.embeds:
            title = interaction.message.embeds[0].title or ""
            m = re.search(r"\$([A-Z0-9]+)", title)
            if m and m.group(1).upper() in TICKERS:
                ticker = m.group(1).upper()

    if not ticker:
        ticker = "JOSE"

    if action == "buy":
        modal = BolsaOrderModal(ticker, "buy")
        await interaction.response.send_modal(modal)
        return True
    elif action == "sell":
        modal = BolsaOrderModal(ticker, "sell")
        await interaction.response.send_modal(modal)
        return True
    elif action == "report":
        await interaction.response.defer(ephemeral=True)
        report_text = await generate_market_report(ticker, guild=interaction.guild)
        report_embed = build_market_report_embed(ticker, report_text)
        await interaction.followup.send(embed=report_embed, ephemeral=True)
        return True
    elif action == "tf":
        tf_raw = parts[2] if len(parts) >= 3 else "1D"
        tf = normalize_timeframe(tf_raw)
        await interaction.response.defer()
        try:
            embed, file, view = await build_bolsa_terminal(ticker, tf)
            await interaction.edit_original_response(embed=embed, attachments=[file], view=view)
            return True
        except Exception as e:
            await interaction.followup.send(f"❌ Error al cambiar temporalidad a {tf}: {e}", ephemeral=True)
            return True

    return False


async def build_bolsa_terminal(
    ticker: str,
    timeframe: str = "1D",
) -> tuple[discord.Embed, discord.File, BolsaTerminalView]:
    """Construye el Embed institucional, la gráfica PNG HD y la vista de la Terminal Bursátil."""
    t = ticker.upper().lstrip("$")
    canon_tf = normalize_timeframe(timeframe)
    tf_cfg = TIMEFRAME_CONFIG.get(canon_tf, TIMEFRAME_CONFIG["1D"])
    info = TICKERS.get(t, {"name": t})
    meta = TICKER_UI_META.get(t, {"emoji": "📈", "tier": "Large Cap", "desc": info["name"]})

    prices = get_bid_ask_prices(t)
    stats = get_member_stats(t)
    bv = calculate_book_value(stats["level"], stats["voice_hours"], stats["messages"])
    e30 = calculate_earnings_30d(stats["delta_voice_hours"], stats["delta_messages"])

    tech = get_ticker_technical_metrics(t)
    base_p = tech["base_price"]
    market_p = prices["market"]
    rsi = tech["rsi"]
    mas = tech["mas"]
    ema_14 = mas.get("ema_14") or market_p
    sma_50 = mas.get("sma_50") or market_p
    cross_signal = tech["cross_signal"]

    mercado = load_market_data()
    pool_data = load_pool_data()
    t_data = mercado.get("tickers", {}).get(t, {})
    amm_shares = t_data.get("amm_shares", 9900)
    user_shares = 10000 - amm_shares
    float_pct = (user_shares / 10000.0) * 100.0
    history = t_data.get("order_history", [])

    # Variación porcentual respecto al suelo fundamental (Aura Base)
    pct_vs_base = ((market_p - base_p) / base_p) * 100.0 if base_p > 0 else 0.0
    trend_badge = f"🟢 `+{pct_vs_base:.2f}%`" if pct_vs_base >= 0 else f"🔴 `{pct_vs_base:.2f}%`"
    market_cap = market_p * 10000.0
    accum_pool = float(pool_data.get("accumulated_pool", 0.0))

    # Estado cualitativo de RSI y Cruce
    if rsi >= 70:
        rsi_state = "Sobrecompra"
    elif rsi <= 30:
        rsi_state = "Sobreventa"
    else:
        rsi_state = "Neutral"

    if cross_signal == "GOLDEN_CROSS":
        signal_label = "🟢 Alcista"
    elif cross_signal == "DEATH_CROSS":
        signal_label = "🟡 Consolidación"
    else:
        signal_label = "⚪ Estable"

    # Barra visual de Float (12 bloques)
    filled_blocks = max(1, min(12, int(round((user_shares / 10000.0) * 12)))) if user_shares > 0 else 0
    progress_bar = "▰" * filled_blocks + "▱" * (12 - filled_blocks)

    # Gráfico HD (960x540)
    img_bytes = generate_candlestick_chart(
        ticker=t,
        history_candles=history,
        timeframe=canon_tf,
        current_price=market_p,
        company_name=info.get("name", t),
    )
    file = discord.File(img_bytes, filename=f"bolsa_{t}.png")

    embed = discord.Embed(
        title=f"{meta['emoji']} Terminal Bursátil — ${t} ({info['name']})",
        description=(
            f"**Cotización:** `{market_p:,.2f}` {EMOJI_PORRO} ({trend_badge} s/Aura)  •  "
            f"**Cap. Bursátil:** `{market_cap:,.0f}` {EMOJI_PORRO}\n"
            f"🏆 **Yield Pool Dividendos:** `{accum_pool:,.2f}` {EMOJI_PORRO} acumulados  •  "
            f"** Temporalidad:** `{tf_cfg.get('label', canon_tf)}`"
        ),
        color=0x00E676 if market_p >= base_p else 0xFF5252,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_image(url=f"attachment://bolsa_{t}.png")

    embed.add_field(
        name="💵 Cotización y Horquilla",
        value=(
            f"Precio: **{market_p:,.2f}** {EMOJI_PORRO}\n"
            f"Ask (Compra): `{prices['ask']:,.2f}`\n"
            f"Bid (Venta): `{prices['bid']:,.2f}`"
        ),
        inline=True,
    )
    embed.add_field(
        name="🏛️ Valor Fundamental",
        value=(
            f"Aura Base: **{base_p:,.2f}** {EMOJI_AURA}\n"
            f"Book Value: `{bv:,.2f}` | E30d: `+{e30:,.2f}`\n"
            f"Prima Mercado: `+{max(0.0, pct_vs_base):.2f}%`"
        ),
        inline=True,
    )
    embed.add_field(
        name="📊 Pulso Técnico",
        value=(
            f"RSI (14): `{rsi:.1f}` ({rsi_state})\n"
            f"EMA 14: `{ema_14:,.2f}` | SMA 50: `{sma_50:,.2f}`\n"
            f"Señal: `{signal_label}`"
        ),
        inline=True,
    )

    if is_market_halted():
        r = get_market_halt_reason()
        halt_desc = f"⛔ **SUSPENDIDO POR EMERGENCIA**\n*{r}*" if r else "⛔ **SUSPENDIDO POR MANTENIMIENTO TÉCNICO**"
        embed.add_field(name="🚨 ESTADO DEL MERCADO", value=halt_desc, inline=False)

    embed.add_field(
        name="📜 Distribución del Float (10.000 acc.)",
        value=(
            f"`{progress_bar}`  En Cartera: `{user_shares:,}` acc. (`{float_pct:.1f}%`)  •  "
            f"Liquidez AMM: `{amm_shares:,}` acc.  •  Últimos trades: `{len(history)}`"
        ),
        inline=False,
    )

    badge_label = tf_cfg.get("label", canon_tf)
    res_label = tf_cfg.get("resolution_label", "")
    embed.set_footer(text=f"Temporalidad: {badge_label} ({res_label}) • Sanvi Exchange 24/7 • Trading 212 HD")

    view = BolsaTerminalView(t, canon_tf)
    return embed, file, view


# ==========================================
# DEFINICIÓN DE COMANDOS SLASH
# ==========================================

cmd_bolsa = app_commands.Group(
    name="bolsa",
    description="Terminal bursátil y gestión de la Bolsa Sanvi",
)


@cmd_bolsa.command(
    name="ver",
    description="Abre la terminal bursátil y gráfica HD estilo Trading 212 de un miembro cotizado",
)
@app_commands.describe(ticker="Selecciona la acción cotizada a consultar (por defecto $JOSE)")
@app_commands.choices(
    ticker=[
        app_commands.Choice(name="👑 $JOSE — Joselito (Mega Cap)", value="JOSE"),
        app_commands.Choice(name="⚡ $TERRE — Terre (Large Cap)", value="TERRE"),
        app_commands.Choice(name="🔥 $OMEN — Omen (Large Cap)", value="OMEN"),
        app_commands.Choice(name="🏎️ $RACER — Racer (Large Cap)", value="RACER"),
    ]
)
async def cmd_bolsa_ver(interaction: discord.Interaction, ticker: Optional[str] = "JOSE"):
    t = (ticker or "JOSE").upper().replace("$", "").strip()
    if t not in TICKERS:
        valid_tickers = ", ".join([f"`${k}`" for k in TICKERS.keys()])
        await interaction.response.send_message(
            f"❌ Ticker no reconocido. Tickers disponibles: {valid_tickers}", ephemeral=True
        )
        return

    await interaction.response.defer()
    try:
        embed, file, view = await build_bolsa_terminal(t, "1D")
        await interaction.followup.send(embed=embed, file=file, view=view)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al abrir la terminal bursátil de ${t}: {e}", ephemeral=True)


@cmd_bolsa.command(
    name="ticker",
    description="Cambia el ticker bursátil de tu acción cotizada (exclusivo para fundadores, coste: 5.000 Porros)",
)
@app_commands.describe(nuevo="Introduce el nuevo ticker bursátil (3 a 6 caracteres alfanuméricos, ej: JOS3, TERRE)")
async def cmd_bolsa_ticker(interaction: discord.Interaction, nuevo: str):
    await interaction.response.defer(ephemeral=True)
    try:
        success, msg = change_founder_ticker(interaction.user.id, new_ticker=nuevo)
        if success:
            embed = discord.Embed(
                title="🏛️ Bolsa Sanvi — Cambio de Ticker Oficial",
                description=f"✅ {msg}",
                color=0x2ECC71,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text="Bolsa Sanvi • Transacción Atómica y Deflación de 5.000 Porros")
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="⛔ Operación Denegada — Cambio de Ticker",
                description=f"❌ {msg}",
                color=0xE74C3C,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text="Bolsa Sanvi • Requisitos y Blindajes de Fundador")
            await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al procesar el cambio de ticker: {e}", ephemeral=True)



@app_commands.command(
    name="cartera",
    description="Consulta tu cartera de acciones, valor actual, PnL y bono de Sinergia de Cartera",
)
@app_commands.describe(usuario="Miembro cuya cartera quieres consultar (opcional, por defecto tú)")
async def cmd_cartera(interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
    await interaction.response.defer()
    try:
        target = usuario or interaction.user
        uid = str(target.id)

        mercado = load_market_data()
        tickers_data = mercado.get("tickers", {})
        pool_data = load_pool_data()

        user_holdings = {}
        total_val = 0.0

        for t_name, t_info in tickers_data.items():
            holdings = t_info.get("holdings", {})
            shares = holdings.get(uid, 0)
            if shares > 0:
                prices = get_bid_ask_prices(t_name)
                val = shares * prices["market"]
                total_val += val
                user_holdings[t_name] = {
                    "shares": shares,
                    "market_price": prices["market"],
                    "value": val,
                }

        aura_total = get_user_portfolio_aura(target.id)
        buff = get_user_portfolio_buff(target.id)
        buff_pct = int(round(buff * 100))

        embed = discord.Embed(
            title=f"💼 Cartera Bursátil — {target.display_name}",
            description=(
                f"• 💰 **Valor de Cartera:** `{total_val:,.2f}` {EMOJI_PORRO}\n"
                f"• 👑 **Aura Total Retenida:** `{aura_total:,.2f}` {EMOJI_AURA}\n"
                f"• ⚡ **Bono Sinergia de Cartera:** `+{buff_pct}%` en `/trabajar`\n"
                f"• 🏆 **Pool de Dividendos Pendiente:** `{pool_data.get('accumulated_pool', 0):,.2f}` {EMOJI_PORRO} acumulados"
            ),
            color=0x2ECC71 if total_val > 0 else 0x95A5A6,
            timestamp=datetime.now(timezone.utc),
        )
        if hasattr(target, "display_avatar") and target.display_avatar:
            embed.set_thumbnail(url=str(target.display_avatar.url))

        if user_holdings:
            for t_name, h_info in user_holdings.items():
                name = TICKERS.get(t_name, {}).get("name", t_name)
                embed.add_field(
                    name=f"${t_name} ({name})",
                    value=(
                        f"• Acciones: `{h_info['shares']:,}`\n"
                        f"• Cotización: `{h_info['market_price']:,.2f}` {EMOJI_PORRO}\n"
                        f"• Valor: `{h_info['value']:,.2f}` {EMOJI_PORRO}"
                    ),
                    inline=True,
                )
        else:
            embed.add_field(
                name="Sin Acciones",
                value="Actualmente no posees acciones en cartera. ¡Usa `/bolsa` para invertir en tus colegas!",
                inline=False,
            )

        embed.set_footer(text="Mantener acciones te da un bonus de hasta +25% en /trabajar y reparto de dividendos")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al consultar la cartera: {e}", ephemeral=True)


@app_commands.command(
    name="aura",
    description="Consulta el desglose contable de Aura y valor fundamental de un miembro",
)
@app_commands.describe(usuario="Miembro cuyo Aura quieres consultar (opcional, por defecto tú)")
async def cmd_aura(interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
    await interaction.response.defer()
    try:
        target = usuario or interaction.user
        found_key = None
        target_ticker = None
        target_name = target.display_name

        for t_sym, t_info in TICKERS.items():
            if t_info.get("user_id") == target.id or t_info.get("alt_user_id") == target.id:
                target_ticker = t_sym
                found_key = t_info.get("cakey_user")
                target_name = t_info.get("name")
                break

        if target_ticker:
            stats = get_member_stats(target_ticker)
            level = stats["level"]
            voice_hours = stats["voice_hours"]
            messages = stats["messages"]
            bv = calculate_book_value(level, voice_hours, messages)
            e30d = calculate_earnings_30d(stats["delta_voice_hours"], stats["delta_messages"])
            total_aura = round(bv + e30d, 2)
        elif found_key and found_key in CANONICAL_SEEDS:
            c_seed = CANONICAL_SEEDS[found_key]
            level = c_seed["level"]
            voice_hours = c_seed["voice_hours"]
            messages = c_seed["messages"]
            bv = calculate_book_value(level, voice_hours, messages)
            e30d = 0.0
            total_aura = round(bv + e30d, 2)
        else:
            level = 20
            voice_hours = 10.0
            messages = 100
            bv = calculate_book_value(level, voice_hours, messages)
            e30d = calculate_earnings_30d(10.0, 100)
            total_aura = round(bv + e30d, 2)

        embed = discord.Embed(
            title=f"👑 Desglose de Aura — {target_name}",
            description=(
                f"**Aura Fundamental (Precio Base):** `{total_aura:,.2f}` {EMOJI_AURA}\n"
                f"El Aura representa el valor contable intrínseco de cada acción del miembro."
            ),
            color=0xF1C40F,
            timestamp=datetime.now(timezone.utc),
        )
        if hasattr(target, "display_avatar") and target.display_avatar:
            embed.set_thumbnail(url=str(target.display_avatar.url))

        embed.add_field(
            name="🏛️ Book Value (Suelo Histórico)",
            value=(
                f"• **Suelo Contable (Book Value):** `{bv:,.2f}` {EMOJI_PORRO}\n"
                f"• Nivel: `{level}` (`+{0.8 * level:,.2f}`)\n"
                f"• Voz Histórica: `{voice_hours:.1f}h` (`+{0.2 * voice_hours:,.2f}`)\n"
                f"• Mensajes: `{messages:,}` (`+{0.02 * messages:,.2f}`)"
            ),
            inline=False,
        )
        embed.add_field(
            name="📈 Rendimiento Mensual (Earnings 30d — 50/50)",
            value=(
                f"• **Earnings Recientes (E30d):** `+{e30d:,.2f}` {EMOJI_PORRO}\n"
                f"• Balance: 50% horas de voz / 50% mensajes en 30 días"
            ),
            inline=False,
        )

        if target_ticker:
            prices = get_bid_ask_prices(target_ticker)
            embed.add_field(
                name=f"💹 Cotización Bursátil (${target_ticker})",
                value=f"Cotiza actualmente a **{prices['market']:,.2f}** {EMOJI_PORRO} en el Sanvi Exchange (`/bolsa {target_ticker}`).",
                inline=False,
            )

        embed.set_footer(text="Fuente de datos: Cakey Bot Leaderboard Web • Persistencia en Render")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error al consultar el Aura: {e}", ephemeral=True)
