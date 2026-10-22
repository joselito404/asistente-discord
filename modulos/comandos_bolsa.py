import re
"""



Módulo de Comandos Slash e Interfaces Interactivas de la Bolsa Sanvi:



- /bolsa [ticker]: Terminal bursátil estilo Trading 212 con gráfico de velas Pillow y botones interactivos.



- /cartera [usuario]: Cartera de acciones, valor actual, PnL y bono de Sinergia de Cartera para /trabajar.



- /aura [usuario]: Desglose contable de Aura (Book Value de por vida + Earnings 30d 50/50).



"""







import io



from typing import Optional, Any



from datetime import datetime, timezone







import discord



from discord import app_commands



from discord.ui import View, Button, Modal, TextInput







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



    generate_market_report,



    calculate_book_value,



    calculate_earnings_30d,



    load_cakey_history,



    CANONICAL_SEEDS,
    is_market_halted,
    get_market_halt_reason,
    set_market_halt,



)



from modulos.bolsa_graficas import generate_candlestick_chart











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



        price_used = res.get("ask_price") if self.action == "buy" else res.get("bid_price")



        total = res.get("total_cost") if self.action == "buy" else res.get("total_income")



        color = 0x00E676 if self.action == "buy" else 0xFF5252







        embed = discord.Embed(



            title=f"✅ Orden de {action_name} Ejecutada — ${self.ticker}",



            description=(



                f"• **Acciones operadas:** `{shares:,}` acciones\n"



                f"• **Precio de ejecución:** `{price_used:,.2f}` Porros/acción\n"



                f"• **Importe total:** `{total:,.2f}` Porros\n"



                f"• **Comisión Yield Pool (0.5%):** `+{res.get('fee_to_pool', 0):,.2f}` Porros\n"



                f"• **Comisión Deflacionaria (0.5%):** `-{res.get('fee_burned', 0):,.2f}` Porros (quemados)\n"



                f"• **Acciones en tu cartera:** `{res.get('user_new_holdings', 0):,}` acciones\n"



                f"• **Nueva cotización:** `{res.get('new_market_price', 0):,.2f}` Porros"



            ),



            color=color,



            timestamp=datetime.now(timezone.utc),



        )



        embed.set_footer(text="Sanvi Exchange 24/7 • Automated Market Maker")



        await interaction.response.send_message(embed=embed, ephemeral=True)











class BolsaTerminalView(View):
    def __init__(self, ticker: str, current_tf: str = "1D"):
        super().__init__(timeout=180)
        self.ticker = ticker.upper()
        self.current_tf = current_tf
        self._setup_buttons()

    def _setup_buttons(self):
        self.clear_items()
        # Fila 0: 5 botones de timeframe
        timeframes = [
            ("Trades", "Trades"),
            ("15m", "15m"),
            ("1h", "1h"),
            ("4h", "4h"),
            ("1D", "1D"),
        ]
        for label, tf in timeframes:
            style = discord.ButtonStyle.primary if tf == self.current_tf else discord.ButtonStyle.secondary
            btn = Button(
                label=label,
                style=style,
                custom_id=f"bolsa:tf:{tf}:{self.ticker}",
                row=0,
            )
            btn.callback = self._create_tf_callback(tf)
            self.add_item(btn)

        # Fila 1: Operativa e información
        btn_buy = Button(label="🛒 Comprar", style=discord.ButtonStyle.success, custom_id=f"bolsa:buy:{self.ticker}", row=1)
        btn_buy.callback = self._btn_buy_callback
        self.add_item(btn_buy)

        btn_sell = Button(label="💰 Vender", style=discord.ButtonStyle.danger, custom_id=f"bolsa:sell:{self.ticker}", row=1)
        btn_sell.callback = self._btn_sell_callback
        self.add_item(btn_sell)

        btn_report = Button(label="📊 Informe IA", style=discord.ButtonStyle.primary, custom_id=f"bolsa:report:{self.ticker}", row=1)
        btn_report.callback = self._btn_report_callback
        self.add_item(btn_report)

        btn_web = Button(
            label="🌐 Web Terminal",
            style=discord.ButtonStyle.link,
            url="https://asistente-discord-sj3k.onrender.com/bolsa",
            row=1,
        )
        self.add_item(btn_web)

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
        report_text = await generate_market_report(self.ticker)
        await interaction.followup.send(report_text, ephemeral=True)

    async def _switch_timeframe(self, interaction: discord.Interaction, tf: str):
        await interaction.response.defer()
        try:
            from modulos.bolsa_graficas import TIMEFRAME_CONFIG, normalize_timeframe
            canon_tf = normalize_timeframe(tf)
            self.current_tf = canon_tf
            self._setup_buttons()

            mercado = load_market_data()
            ticker_data = mercado.get("tickers", {}).get(self.ticker, {})
            history = ticker_data.get("order_history", [])
            info = TICKERS.get(self.ticker, {"name": self.ticker})
            prices = get_bid_ask_prices(self.ticker)
            img_bytes = generate_candlestick_chart(
                ticker=self.ticker,
                history_candles=history,
                timeframe=canon_tf,
                current_price=prices["market"],
                company_name=info.get("name", self.ticker),
            )
            file = discord.File(img_bytes, filename=f"bolsa_{self.ticker}.png")

            tf_cfg = TIMEFRAME_CONFIG.get(canon_tf, {})
            badge_label = tf_cfg.get("label", canon_tf)
            res_label = tf_cfg.get("resolution_label", "")

            embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed(title=f"${self.ticker}")
            embed.set_image(url=f"attachment://bolsa_{self.ticker}.png")
            embed.set_footer(text=f"Temporalidad: {badge_label} ({res_label}) • Sanvi Exchange 24/7 • Trading 212 Style")

            await interaction.edit_original_response(embed=embed, attachments=[file], view=self)
        except Exception as e:
            await interaction.followup.send(f"❌ Error al cambiar temporalidad a {tf}: {e}")


async def handle_bolsa_interaction(interaction: discord.Interaction) -> bool:
    """Intermediario global para capturar y procesar cualquier botón de la Bolsa Sanvi."""
    if interaction.type != discord.InteractionType.component:
        return False

    custom_id = interaction.data.get("custom_id", "")
    if not custom_id.startswith("bolsa:"):
        return False

    parts = custom_id.split(":")
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

    action = parts[1] if len(parts) >= 2 else ""

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
        report_text = await generate_market_report(ticker)
        await interaction.followup.send(report_text, ephemeral=True)
        return True
    elif action == "tf":
        from modulos.bolsa_graficas import normalize_timeframe, TIMEFRAME_CONFIG
        tf_raw = parts[2] if len(parts) >= 3 else "1D"
        tf = normalize_timeframe(tf_raw)
        await interaction.response.defer()
        try:
            mercado = load_market_data()
            ticker_data = mercado.get("tickers", {}).get(ticker, {})
            history = ticker_data.get("order_history", [])
            info = TICKERS.get(ticker, {"name": ticker})
            prices = get_bid_ask_prices(ticker)
            img_bytes = generate_candlestick_chart(
                ticker=ticker,
                history_candles=history,
                timeframe=tf,
                current_price=prices["market"],
                company_name=info.get("name", ticker),
            )
            file = discord.File(img_bytes, filename=f"bolsa_{ticker}.png")
            embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed(title=f"${ticker}")
            embed.set_image(url=f"attachment://bolsa_{ticker}.png")

            tf_cfg = TIMEFRAME_CONFIG.get(tf, {})
            badge_label = tf_cfg.get("label", tf)
            res_label = tf_cfg.get("resolution_label", "")
            embed.set_footer(text=f"Temporalidad: {badge_label} ({res_label}) • Sanvi Exchange 24/7 • Trading 212 Style")

            view = BolsaTerminalView(ticker, tf)
            await interaction.edit_original_response(embed=embed, attachments=[file], view=view)
            return True
        except Exception as e:
            await interaction.followup.send(f"❌ Error al cambiar temporalidad a {tf}: {e}")
            return True

    return False


async def build_bolsa_terminal(ticker: str) -> tuple[discord.Embed, discord.File, BolsaTerminalView]:



    t = ticker.upper()



    info = TICKERS.get(t, {"name": t})



    prices = get_bid_ask_prices(t)



    base_p = calculate_base_price(t)



    mercado = load_market_data()



    t_data = mercado.get("tickers", {}).get(t, {})



    amm_shares = t_data.get("amm_shares", 9900)



    user_shares = 10000 - amm_shares



    history = t_data.get("order_history", [])







    # Métricas técnicas



    price_series = [o.get("price", base_p) for o in history] or [base_p]



    rsi = calculate_rsi(price_series)



    mas = calculate_moving_averages(price_series)







    # Gráfico



    img_bytes = generate_candlestick_chart(

        ticker=t,

        history_candles=history,

        timeframe="1D",

        current_price=prices["market"],

        company_name=info.get("name", t),

    )



    file = discord.File(img_bytes, filename=f"bolsa_{t}.png")







    embed = discord.Embed(



        title=f"📈 Terminal Bursátil — ${t} ({info['name']})",



        color=0x00E676 if prices["market"] >= base_p else 0xFF5252,



        timestamp=datetime.now(timezone.utc),



    )



    embed.set_image(url=f"attachment://bolsa_{t}.png")







    embed.add_field(



        name="💵 Cotización de Mercado",



        value=f"**{prices['market']:,.2f}** Porros\nAsk: `{prices['ask']:,.2f}` | Bid: `{prices['bid']:,.2f}`",



        inline=True,



    )



    embed.add_field(



        name="🏛️ Valor Fundamental (Aura)",



        value=f"**{base_p:,.2f}** Porros\n*(Suelo Book Value + E30d)*",



        inline=True,



    )



    embed.add_field(



        name="📊 Indicadores Técnicos",



        value=f"RSI (14d): `{rsi:.1f}`\nEMA 14: `{mas['ema_14']:.2f}` | SMA 50: `{mas['sma_50']:.2f}`",



        inline=True,



    )






    if is_market_halted():
        r = get_market_halt_reason()
        halt_desc = f"⛔ **SUSPENDIDO POR EMERGENCIA**\n*{r}*" if r else "⛔ **SUSPENDIDO POR MANTENIMIENTO TÉCNICO**"
        embed.add_field(name="🚨 ESTADO DEL MERCADO", value=halt_desc, inline=False)

    embed.add_field(
        name="📜 Circulación / Float",



        value=f"En Cartera: `{user_shares:,}` / 10.000\nAMM Bot: `{amm_shares:,}` / 10.000",



        inline=False,



    )



    embed.set_footer(text="Temporalidad: 1D · velas 30m • Sanvi Exchange 24/7 • Trading 212 Style")







    view = BolsaTerminalView(t, "1D")



    return embed, file, view











# ==========================================



# DEFINICIÓN DE COMANDOS SLASH



# ==========================================







@app_commands.command(name="bolsa", description="Abre la terminal bursátil y gráfica de cotización estilo Trading 212 de un miembro")



@app_commands.describe(ticker="Símbolo del ticker a consultar (ej: JOSE, TERRE, OMEN, RACER)")



async def cmd_bolsa(interaction: discord.Interaction, ticker: str):



    t = ticker.upper().replace("$", "").strip()



    if t not in TICKERS:



        valid_tickers = ", ".join([f"`${k}`" for k in TICKERS.keys()])



        await interaction.response.send_message(



            f"❌ Ticker no reconocido. Tickers disponibles: {valid_tickers}", ephemeral=True



        )



        return







    await interaction.response.defer()



    try:



        embed, file, view = await build_bolsa_terminal(t)



        await interaction.followup.send(embed=embed, file=file, view=view)



    except Exception as e:



        await interaction.followup.send(f"❌ Error al abrir la terminal bursátil de ${t}: {e}", ephemeral=True)











@app_commands.command(name="cartera", description="Consulta tu cartera de acciones, valor actual, PnL y bono de Sinergia de Cartera")



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



                f"• 💰 **Valor de Cartera:** `{total_val:,.2f}` Porros\n"



                f"• 👑 **Aura Total Retenida:** `{aura_total:,.2f}` pts\n"



                f"• ⚡ **Bono Sinergia de Cartera:** `+{buff_pct}%` en `/trabajar`\n"



                f"• 🏆 **Pool Semanal Pendiente:** `{pool_data.get('accumulated_pool', 0):,.2f}` Porros acumulados"



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



                    value=f"• Acciones: `{h_info['shares']:,}`\n• Cotización: `{h_info['market_price']:,.2f}`\n• Valor: `{h_info['value']:,.2f}` Porros",



                    inline=True,



                )



        else:



            embed.add_field(



                name="Sin Acciones",



                value="Actualmente no posees acciones en cartera. ¡Usa `/bolsa [ticker]` para invertir en tus colegas!",



                inline=False,



            )







        embed.set_footer(text="Mantener acciones te da un bonus de hasta +25% en /trabajar y dividendos los domingos")



        await interaction.followup.send(embed=embed)



    except Exception as e:



        await interaction.followup.send(f"❌ Error al consultar la cartera: {e}", ephemeral=True)











@app_commands.command(name="aura", description="Consulta el desglose contable de Aura y valor fundamental de un miembro")



@app_commands.describe(usuario="Miembro cuyo Aura quieres consultar (opcional, por defecto tú)")



async def cmd_aura(interaction: discord.Interaction, usuario: Optional[discord.Member] = None):



    await interaction.response.defer()



    try:



        target = usuario or interaction.user



        cakey_history = load_cakey_history()



        snapshots = cakey_history.get("snapshots", {})







        # Buscar usuario en tickers o en snapshots



        found_key = None



        target_ticker = None



        target_name = target.display_name







        for t_sym, t_info in TICKERS.items():



            if t_info.get("user_id") == target.id or t_info.get("alt_user_id") == target.id:



                target_ticker = t_sym



                found_key = t_info.get("cakey_user")



                target_name = t_info.get("name")



                break







        # Obtener datos de Cakey



        if found_key and found_key in CANONICAL_SEEDS:



            c_seed = CANONICAL_SEEDS[found_key]



            level = c_seed["level"]



            voice_hours = c_seed["voice_hours"]



            messages = c_seed["messages"]



        else:



            # Fallback a aspirante



            level = 20



            voice_hours = 10.0



            messages = 100







        bv = calculate_book_value(level, voice_hours, messages)



        e30d = calculate_earnings_30d(10.0, 100)  # Estimación activa inicial



        total_aura = round(bv + e30d, 2)







        embed = discord.Embed(



            title=f"👑 Desglose de Aura — {target_name}",



            description=(



                f"**Aura Fundamental (Precio Base):** `{total_aura:,.2f}` Porros\n"



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



                f"• **Suelo Contable (Book Value):** `{bv:,.2f}` Porros\n"



                f"• Nivel: `{level}` (`+{0.8 * level:,.2f}`)\n"



                f"• Voz Histórica: `{voice_hours:.1f}h` (`+{0.2 * voice_hours:,.2f}`)\n"



                f"• Mensajes: `{messages:,}` (`+{0.02 * messages:,.2f}`)"



            ),



            inline=False,



        )



        embed.add_field(



            name="📈 Rendimiento Mensual (Earnings 30d — 50/50)",



            value=(



                f"• **Earnings Recientes (E30d):** `+{e30d:,.2f}` Porros\n"



                f"• Balance: 50% horas de voz / 50% mensajes en 30 días"



            ),



            inline=False,



        )







        if target_ticker:



            prices = get_bid_ask_prices(target_ticker)



            embed.add_field(



                name=f"💹 Cotización Bursátil (${target_ticker})",



                value=f"Cotiza actualmente a **{prices['market']:,.2f}** Porros en el Sanvi Exchange (`/bolsa {target_ticker}`).",



                inline=False,



            )







        embed.set_footer(text="Fuente de datos: Cakey Bot Leaderboard Web • Persistencia en Render")



        await interaction.followup.send(embed=embed)



    except Exception as e:



        await interaction.followup.send(f"❌ Error al consultar el Aura: {e}", ephemeral=True)



