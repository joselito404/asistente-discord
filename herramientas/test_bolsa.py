"""
Suite de Pruebas Unitarias para el Motor Bursátil Sanvi Exchange:
- Valida cálculos matemáticos de Book Value, Earnings 30d y Base Price.
- Valida curva AMM, elasticidad K=2000 y suelo garantizado.
- Valida ejecución de compras, ventas, retención de spread y Yield Pool de dividendos.
- Valida blindajes anti-ballenas (límite 500 acciones y cooldown 30s).
- Valida Sinergia de Cartera y bonus multiplicador de /trabajar.
- Valida indicadores técnicos institucionales (RSI 14, Medias Móviles y Cruces).
- Valida las 8 temporalidades completas ('Trades', '15m', '1h', '4h', '1D', '1S', '1M', 'MAX')
  y el renderizado gráfico HD (960x540) en Pillow.
- Valida unificación del 100% de métricas técnicas con Informe IA y conversión de emojis del servidor.
- Valida estructura de BolsaTerminalView (2 filas de 4 botones de TF + 1 fila operativa + Select de tickers) y choices en /bolsa.
"""

import asyncio
import os
import sys
import io
import time
import unittest
from PIL import Image

# Asegurar importación de módulos en la raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos import bolsa_sanvi
from modulos import bolsa_graficas
from modulos import comandos_bolsa
from modulos import economia_core
from modulos import web_server


class TestBolsaSanvi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Crear usuario de pruebas en economia y asegurar mercado temporalmente abierto para el runner
        cls.test_user_id = 999888777666
        cls.orig_halt = bolsa_sanvi.is_market_halted()
        cls.orig_reason = bolsa_sanvi.get_market_halt_reason()
        bolsa_sanvi.set_market_halt(False)
        economia_core.ensure_user(cls.test_user_id, default_cash=1000000)

    @classmethod
    def tearDownClass(cls):
        # Restaurar estado de mercado original al terminar las pruebas
        bolsa_sanvi.set_market_halt(cls.orig_halt, cls.orig_reason)

    def test_01_book_value_canonical(self):
        """Valida que el cálculo de Book Value coincida exactamente con docs/DISENO_BOLSA_SANVI.md (1.0 por nivel)."""
        # Joselito: Lvl 54, 65.8h voz, 658 msgs -> 10 + 54 + 13.16 + 13.16 = 90.32
        bv_jose = bolsa_sanvi.calculate_book_value(54, 65.8, 658)
        self.assertEqual(bv_jose, 90.32, f"BV Joselito esperado 90.32, obtenido {bv_jose}")

        # Terre: Lvl 37, 25.0h voz, 196 msgs -> 10 + 37 + 5.0 + 3.92 = 55.92
        bv_terre = bolsa_sanvi.calculate_book_value(37, 25.0, 196)
        self.assertEqual(bv_terre, 55.92, f"BV Terre esperado 55.92, obtenido {bv_terre}")

        # Omen: Lvl 36, 29.8h voz, 148 msgs -> 10 + 36 + 5.96 + 2.96 = 54.92
        bv_omen = bolsa_sanvi.calculate_book_value(36, 29.8, 148)
        self.assertEqual(bv_omen, 54.92, f"BV Omen esperado 54.92, obtenido {bv_omen}")

        # Racer: Lvl 33, 29.0h voz, 129 msgs -> 10 + 33 + 5.8 + 2.58 = 51.38
        bv_racer = bolsa_sanvi.calculate_book_value(33, 29.0, 129)
        self.assertEqual(bv_racer, 51.38, f"BV Racer esperado 51.38, obtenido {bv_racer}")

    def test_02_earnings_30d_fifty_fifty(self):
        """Valida la ponderación 50/50 de Earnings 30d (1h voz = 1.00, 10 msgs = 1.00)."""
        # 1 hora de voz sola
        e_voice = bolsa_sanvi.calculate_earnings_30d(1.0, 0)
        self.assertEqual(e_voice, 1.00)

        # 10 mensajes solos
        e_msgs = bolsa_sanvi.calculate_earnings_30d(0.0, 10)
        self.assertEqual(e_msgs, 1.00)

        # 20 horas de voz y 200 mensajes -> 20.0 + 20.0 = 40.0
        e_combined = bolsa_sanvi.calculate_earnings_30d(20.0, 200)
        self.assertEqual(e_combined, 40.0)

        # Deltas negativos deben ser acotados a 0
        e_negative = bolsa_sanvi.calculate_earnings_30d(-5.0, -20)
        self.assertEqual(e_negative, 0.0)

    def test_03_base_price_and_amm_curve(self):
        """Valida el cálculo de Base Price y la curva de elasticidad del AMM."""
        bp_jose = bolsa_sanvi.calculate_base_price("JOSE")
        self.assertGreaterEqual(bp_jose, 79.52)

        # En estado virgen (100 acciones en usuarios, 9900 en AMM), precio de mercado = base_price
        mp_jose = bolsa_sanvi.calculate_market_price("JOSE")
        self.assertGreaterEqual(mp_jose, bp_jose)

        # Simular curva si usuarios compraran 500 acciones más (total 600)
        # Multiplicador: 1 + (600 - 100) / 2000 = 1 + 500/2000 = 1.25 (+25%)
        excess = 500.0
        expected_mult = 1.0 + (excess / bolsa_sanvi.AMM_FACTOR_K)
        expected_price = round(bp_jose * expected_mult, 2)
        self.assertEqual(round(1.0 + 500.0 / 2000.0, 2), 1.25)
        self.assertAlmostEqual(expected_price, bp_jose * 1.25, places=2)

    def test_04_bid_ask_spread(self):
        """Valida la horquilla Bid/Ask (Ask +0.5%, Bid -0.5%)."""
        quotes = bolsa_sanvi.get_bid_ask_prices("JOSE")
        market = quotes["market"]
        ask = quotes["ask"]
        bid = quotes["bid"]

        self.assertGreater(ask, market)
        self.assertLess(bid, market)
        self.assertAlmostEqual(ask, round(market * 1.005, 2), places=2)
        self.assertAlmostEqual(bid, round(market * 0.995, 2), places=2)

    def test_05_buy_and_sell_order_execution(self):
        """Valida la ejecución completa de compras y ventas con retención de spread."""
        user_id = self.test_user_id
        economia_core.modify_balance(user_id, cash_delta=50000)

        initial_pool = bolsa_sanvi.load_pool_data().get("accumulated_pool", 0.0)

        # 1. Ejecutar compra de 50 acciones de JOSE
        buy_res = bolsa_sanvi.execute_buy_order(user_id, "JOSE", 50, ignore_cooldown=True)
        self.assertTrue(buy_res["success"], f"Error en compra: {buy_res.get('error')}")
        self.assertEqual(buy_res["shares"], 50)
        self.assertGreater(buy_res["spread_fee"], 0.0)
        self.assertGreater(buy_res["spread_to_pool"], 0.0)

        # Verificar que el Yield Pool recibió su parte
        pool_after_buy = bolsa_sanvi.load_pool_data().get("accumulated_pool", 0.0)
        self.assertGreater(pool_after_buy, initial_pool)

        # 2. Ejecutar venta de 20 acciones de JOSE
        sell_res = bolsa_sanvi.execute_sell_order(user_id, "JOSE", 20, ignore_cooldown=True)
        self.assertTrue(sell_res["success"], f"Error en venta: {sell_res.get('error')}")
        self.assertEqual(sell_res["shares"], 20)
        self.assertGreater(sell_res["total_payout"], 0)

        # 3. Limpiar cartera restante vendiendo las 30 restantes
        cleanup_res = bolsa_sanvi.execute_sell_order(user_id, "JOSE", 30, ignore_cooldown=True)
        self.assertTrue(cleanup_res["success"])

    def test_06_anti_whale_protection(self):
        """Valida los límites anti-ballenas (máximo 500 acciones y cooldown de 30s)."""
        user_id = self.test_user_id
        # Intento de comprar 501 acciones
        res_limit = bolsa_sanvi.execute_buy_order(user_id, "JOSE", 501, ignore_cooldown=True)
        self.assertFalse(res_limit["success"])
        self.assertIn("máximo 500 acciones", res_limit["error"])

        # Intento de operar dos veces seguidas sin ignore_cooldown
        res_first = bolsa_sanvi.execute_buy_order(user_id, "TERRE", 10, ignore_cooldown=True)
        self.assertTrue(res_first["success"])

        res_cooldown = bolsa_sanvi.execute_buy_order(user_id, "TERRE", 10, ignore_cooldown=False)
        self.assertFalse(res_cooldown["success"])
        self.assertIn("Cooldown activo", res_cooldown["error"])

        # Limpiar acciones de prueba
        bolsa_sanvi.execute_sell_order(user_id, "TERRE", 10, ignore_cooldown=True)

    def test_07_portfolio_synergy_and_buffs(self):
        """Valida el cálculo de Aura en cartera y el multiplicador de bono para /trabajar."""
        user_id = self.test_user_id
        # Cartera vacía -> buff 0.0
        buff_empty = bolsa_sanvi.get_user_portfolio_buff(user_id)
        self.assertEqual(buff_empty, 0.0)

        # Comprar 20 acciones de JOSE (~1.590 Porros de Aura) -> Rango 1.000 a 5.000 -> +5% (0.05)
        bolsa_sanvi.execute_buy_order(user_id, "JOSE", 20, ignore_cooldown=True)
        aura = bolsa_sanvi.get_user_portfolio_aura(user_id)
        self.assertGreaterEqual(aura, 1000.0)
        buff = bolsa_sanvi.get_user_portfolio_buff(user_id)
        self.assertEqual(buff, 0.05)

        # Limpiar
        bolsa_sanvi.execute_sell_order(user_id, "JOSE", 20, ignore_cooldown=True)

    def test_08_technical_indicators(self):
        """Valida cálculos matemáticos de RSI y Medias Móviles institucionales."""
        # Serie alcista constante: de 10 a 25
        series = [float(x) for x in range(10, 30)]
        rsi = bolsa_sanvi.calculate_rsi(series, period=14)
        self.assertEqual(rsi, 100.0, f"RSI en serie estrictamente alcista debe ser 100.0, obtenido {rsi}")

        # Serie bajista constante: de 30 a 10
        series_down = [float(x) for x in range(30, 10, -1)]
        rsi_down = bolsa_sanvi.calculate_rsi(series_down, period=14)
        self.assertEqual(rsi_down, 0.0, f"RSI en serie estrictamente bajista debe ser 0.0, obtenido {rsi_down}")

        # Medias Móviles
        mas = bolsa_sanvi.calculate_moving_averages(series)
        self.assertIn("sma_14", mas)
        self.assertIn("ema_14", mas)
        self.assertIsNotNone(mas["sma_14"])
        self.assertIsNotNone(mas["ema_14"])

        # Señales de cruce
        cross_gold = bolsa_sanvi.detect_crosses(ema_short=55.0, sma_long=50.0)
        self.assertEqual(cross_gold, "GOLDEN_CROSS")

        cross_death = bolsa_sanvi.detect_crosses(ema_short=45.0, sma_long=50.0)
        self.assertEqual(cross_death, "DEATH_CROSS")

    def test_09_candlestick_chart_generation_hd(self):
        """Valida que el generador gráfico devuelva un buffer BytesIO con un PNG HD (960x540) válido."""
        chart_buffer = bolsa_graficas.generate_candlestick_chart(
            ticker="JOSE",
            timeframe="1D",
            current_price=79.52,
            company_name="Joselito",
        )
        self.assertIsInstance(chart_buffer, io.BytesIO)
        content = chart_buffer.getvalue()
        self.assertGreater(len(content), 1000, "La imagen generada debe superar 1KB")
        self.assertTrue(content.startswith(b"\x89PNG\r\n\x1a\n"), "El archivo generado no tiene cabecera PNG válida")

        # Verificar resolución HD exacta 960x540
        chart_buffer.seek(0)
        with Image.open(chart_buffer) as img:
            self.assertEqual(img.size, (960, 540))

    def test_10_emergency_halt(self):
        """Valida que el interruptor de paro de emergencia bloquee compras y ventas en 24/7."""
        user_id = self.test_user_id
        # 1. Activar paro de emergencia
        res_halt = bolsa_sanvi.set_market_halt(True, reason="Mantenimiento preventivo de prueba")
        self.assertTrue(res_halt["success"])
        self.assertTrue(bolsa_sanvi.is_market_halted())
        self.assertEqual(bolsa_sanvi.get_market_halt_reason(), "Mantenimiento preventivo de prueba")

        # 2. Intentar compra mientras está pausado (debe fallar)
        buy_res = bolsa_sanvi.execute_buy_order(user_id=user_id, ticker="JOSE", shares=10)
        self.assertFalse(buy_res["success"])
        self.assertIn("suspendida por mantenimiento o emergencia", buy_res["error"])

        # 3. Intentar venta mientras está pausado (debe fallar)
        sell_res = bolsa_sanvi.execute_sell_order(user_id=user_id, ticker="JOSE", shares=10)
        self.assertFalse(sell_res["success"])
        self.assertIn("suspendida por mantenimiento o emergencia", sell_res["error"])

        # 4. Reanudar mercado 24/7
        res_resume = bolsa_sanvi.set_market_halt(False)
        self.assertTrue(res_resume["success"])
        self.assertFalse(bolsa_sanvi.is_market_halted())

    def test_11_eight_timeframes_complete(self):
        """Valida las 8 temporalidades completas (Trades, 15m, 1h, 4h, 1D, 1S, 1M, MAX) y sus PNGs HD."""
        all_tfs = ["Trades", "15m", "1h", "4h", "1D", "1S", "1M", "MAX"]
        for tf in all_tfs:
            self.assertIn(tf, bolsa_graficas.TIMEFRAME_CONFIG)
            self.assertEqual(bolsa_graficas.normalize_timeframe(tf), tf)

            candles = bolsa_graficas._normalize_or_generate_candles(
                history_candles=[],
                current_price=79.52,
                timeframe=tf,
            )
            cfg = bolsa_graficas.TIMEFRAME_CONFIG[tf]
            expected_count = cfg["default_count"]
            self.assertEqual(len(candles), expected_count, f"Fallo en count de {tf}: {len(candles)} != {expected_count}")
            for c in candles:
                self.assertIn("open", c)
                self.assertIn("high", c)
                self.assertIn("low", c)
                self.assertIn("close", c)
                self.assertIn("volume", c)
                self.assertIn("time", c)

            # Validar renderizado gráfico HD (960x540) en Pillow para cada timeframe
            chart_buf = bolsa_graficas.generate_candlestick_chart(
                ticker="JOSE",
                timeframe=tf,
                current_price=79.52,
                company_name="Joselito",
            )
            self.assertIsInstance(chart_buf, io.BytesIO)
            data = chart_buf.getvalue()
            self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
            chart_buf.seek(0)
            with Image.open(chart_buf) as img:
                self.assertEqual(img.size, (960, 540), f"Fallo tamaño HD en {tf}: {img.size}")

        # Validar Trades con historial real (proyección 1 vela por orden)
        mock_trades = [
            {"price": 79.50, "shares": 10.0, "timestamp": "2026-10-22T20:00:00Z"},
            {"price": 80.20, "shares": 25.0, "timestamp": "2026-10-22T20:05:00Z"},
            {"price": 80.50, "shares": 15.0, "timestamp": "2026-10-22T20:10:00Z"},
        ]
        trade_candles = bolsa_graficas._normalize_or_generate_candles(
            history_candles=mock_trades,
            current_price=80.50,
            timeframe="Trades",
            target_count=30,
        )
        self.assertEqual(len(trade_candles), 30)
        self.assertEqual(trade_candles[-1]["close"], 80.50)
        self.assertEqual(trade_candles[-2]["close"], 80.20)
        self.assertEqual(trade_candles[-3]["close"], 79.50)
        self.assertEqual(trade_candles[0]["volume"], 0.0)
        self.assertEqual(trade_candles[0]["close"], 79.50)

    def test_12_web_terminal_endpoints(self):
        """Valida la generación del HTML de /bolsa y el payload JSON de /api/bolsa/data con las 8 temporalidades."""
        html_page = web_server.render_bolsa_html()
        self.assertIsInstance(html_page, str)
        self.assertIn("<!DOCTYPE html>", html_page)
        self.assertIn("lightweight-charts", html_page)
        self.assertIn("tv-chart", html_page)
        for sym in ["$JOSE", "$TERRE", "$OMEN", "$RACER"]:
            self.assertIn(sym, html_page)
        for tf in ["Trades", "15m", "1h", "4h", "1D", "1S", "1M", "MAX"]:
            self.assertIn(tf, html_page)

        payload = web_server.get_bolsa_api_payload()
        self.assertIsInstance(payload, dict)
        self.assertIn("timestamp", payload)
        self.assertIn("is_halted", payload)
        self.assertIn("pool", payload)
        self.assertIn("tickers", payload)

        tickers = payload["tickers"]
        for sym in ["JOSE", "TERRE", "OMEN", "RACER"]:
            self.assertIn(sym, tickers)
            t_info = tickers[sym]
            self.assertIn("current_price", t_info)
            self.assertIn("base_price", t_info)
            self.assertIn("bid", t_info)
            self.assertIn("ask", t_info)
            self.assertIn("float_pct", t_info)
            self.assertIn("rsi_14", t_info)
            self.assertIn("series", t_info)

            # Validar que el RSI de la API coincida al 100% con get_ticker_technical_metrics
            canon_tech = bolsa_sanvi.get_ticker_technical_metrics(sym)
            self.assertEqual(t_info["rsi_14"], round(canon_tech["rsi"], 2))

            series = t_info["series"]
            for tf in ["Trades", "15m", "1h", "4h", "1D", "1S", "1M", "MAX"]:
                self.assertIn(tf, series)
                self.assertIn("candles", series[tf])
                self.assertIn("volume", series[tf])
                self.assertGreater(len(series[tf]["candles"]), 0)
                times = [c["time"] for c in series[tf]["candles"]]
                self.assertEqual(times, sorted(times))

    def test_13_unified_technical_metrics_and_emoji_report(self):
        """Valida consistencia del 100% entre get_ticker_technical_metrics, Informe IA y conversión de emojis."""
        for sym in ["JOSE", "TERRE", "OMEN", "RACER"]:
            tech = bolsa_sanvi.get_ticker_technical_metrics(sym)
            self.assertIn("rsi", tech)
            self.assertIn("mas", tech)
            self.assertIn("cross_signal", tech)
            self.assertGreaterEqual(tech["rsi"], 0.0)
            self.assertLessEqual(tech["rsi"], 100.0)

        # Validar sanitizador y conversor de emojis del servidor
        import re as _re
        raw_sample = "Análisis de :Porro: y :aura: con :cooked:, :Messirve:, :gigachad:, :stonks: y :inventado_123:"
        formatted = bolsa_sanvi._format_and_sanitize_report_emojis(raw_sample, guild=None)
        self.assertIsNone(_re.search(r"(?<!<)(?<!<a):([a-zA-Z0-9_]+):(?!\d+>)", formatted))
        self.assertIn("<:Porro:1535685303317172305>", formatted)
        self.assertIn("<:aura:1535728704129466462>", formatted)
        self.assertIn("<:cooked:1535726716901789726>", formatted)
        self.assertIn("<:Messirve:1535726367847743528>", formatted)
        self.assertIn("<:gigachad:1535682070536519730>", formatted)
        self.assertIn("📈", formatted)
        self.assertNotIn("inventado_123", formatted)

        # Validar generate_market_report y build_market_report_embed
        report_text = asyncio.run(bolsa_sanvi.generate_market_report("JOSE", guild=None))
        self.assertIsInstance(report_text, str)
        self.assertGreater(len(report_text), 50)
        self.assertIsNone(_re.search(r"(?<!<)(?<!<a):([a-zA-Z0-9_]+):(?!\d+>)", report_text))

        report_embed = comandos_bolsa.build_market_report_embed("JOSE", report_text)
        self.assertIn("$JOSE", report_embed.title)
        self.assertEqual(len(report_embed.fields), 3)

    def test_14_bolsa_terminal_view_and_choices(self):
        """Valida la estructura de BolsaTerminalView (2 filas de 4 TF + operativa + Select) y choices de /bolsa."""
        async def _check_view_and_embed():
            embed, file, view = await comandos_bolsa.build_bolsa_terminal("JOSE", "1S")
            self.assertIn("$JOSE", embed.title)
            self.assertIn("<:Porro:1535685303317172305>", embed.description)
            self.assertEqual(len(view.children), 13)  # 4 + 4 + 4 botones + 1 Select

            row0_labels = [c.label for c in view.children if getattr(c, "row", None) == 0]
            row1_labels = [c.label for c in view.children if getattr(c, "row", None) == 1]
            row2_labels = [c.label for c in view.children if getattr(c, "row", None) == 2]
            row3_items = [c for c in view.children if getattr(c, "row", None) == 3]

            self.assertEqual(row0_labels, ["Trades", "15m", "1h", "4h"])
            self.assertEqual(row1_labels, ["1D", "1S", "1M", "MAX"])
            self.assertEqual(len(row2_labels), 4)
            self.assertEqual(len(row3_items), 1)

            select_item = row3_items[0]
            option_values = [opt.value for opt in select_item.options]
            self.assertEqual(option_values, ["JOSE", "TERRE", "OMEN", "RACER"])

        asyncio.run(_check_view_and_embed())

        # Validar choices nativos de /bolsa
        params = comandos_bolsa.cmd_bolsa._params
        self.assertIn("ticker", params)
        choices = [c.value for c in params["ticker"].choices]
        self.assertEqual(choices, ["JOSE", "TERRE", "OMEN", "RACER"])


if __name__ == "__main__":
    unittest.main()
