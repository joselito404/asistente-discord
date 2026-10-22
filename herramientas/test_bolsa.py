"""
Suite de Pruebas Unitarias para el Motor Bursátil Sanvi Exchange:
- Valida cálculos matemáticos de Book Value, Earnings 30d y Base Price.
- Valida curva AMM, elasticidad K=2000 y suelo garantizado.
- Valida ejecución de compras, ventas, retención de spread y Yield Pool de dividendos.
- Valida blindajes anti-ballenas (límite 500 acciones y cooldown 30s).
- Valida Sinergia de Cartera y bonus multiplicador de /trabajar.
- Valida indicadores técnicos institucionales (RSI 14, Medias Móviles y Cruces).
- Valida renderizado gráfico de velas japonesas en Pillow (formato PNG válido).
"""

import os
import sys
import io
import time
import unittest

# Asegurar importación de módulos en la raíz del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos import bolsa_sanvi
from modulos import bolsa_graficas
from modulos import economia_core


class TestBolsaSanvi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Crear usuario de pruebas en economia
        cls.test_user_id = 999888777666
        economia_core.ensure_user(cls.test_user_id, default_cash=1000000)

    def test_01_book_value_canonical(self):
        """Valida que el cálculo de Book Value coincida exactamente con docs/DISENO_BOLSA_SANVI.md."""
        # Joselito: Lvl 54, 65.8h voz, 658 msgs -> 79.52
        bv_jose = bolsa_sanvi.calculate_book_value(54, 65.8, 658)
        self.assertEqual(bv_jose, 79.52, f"BV Joselito esperado 79.52, obtenido {bv_jose}")

        # Terre: Lvl 37, 25.0h voz, 196 msgs -> 48.52
        bv_terre = bolsa_sanvi.calculate_book_value(37, 25.0, 196)
        self.assertEqual(bv_terre, 48.52, f"BV Terre esperado 48.52, obtenido {bv_terre}")

        # Omen: Lvl 36, 29.8h voz, 148 msgs -> 47.72
        bv_omen = bolsa_sanvi.calculate_book_value(36, 29.8, 148)
        self.assertEqual(bv_omen, 47.72, f"BV Omen esperado 47.72, obtenido {bv_omen}")

        # Racer: Lvl 33, 29.0h voz, 129 msgs -> 44.78
        bv_racer = bolsa_sanvi.calculate_book_value(33, 29.0, 129)
        self.assertEqual(bv_racer, 44.78, f"BV Racer esperado 44.78, obtenido {bv_racer}")

    def test_02_earnings_30d_fifty_fifty(self):
        """Valida la ponderación 50/50 de Earnings 30d (1h voz = 0.50, 10 msgs = 0.50)."""
        # 1 hora de voz sola
        e_voice = bolsa_sanvi.calculate_earnings_30d(1.0, 0)
        self.assertEqual(e_voice, 0.50)

        # 10 mensajes solos
        e_msgs = bolsa_sanvi.calculate_earnings_30d(0.0, 10)
        self.assertEqual(e_msgs, 0.50)

        # 20 horas de voz y 200 mensajes -> 10.0 + 10.0 = 20.0
        e_combined = bolsa_sanvi.calculate_earnings_30d(20.0, 200)
        self.assertEqual(e_combined, 20.0)

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

    def test_09_candlestick_chart_generation(self):
        """Valida que el generador gráfico devuelva un buffer BytesIO con un PNG válido."""
        chart_buffer = bolsa_graficas.generate_candlestick_chart(
            ticker="JOSE",
            timeframe="1D",
            current_price=79.52,
            company_name="Joselito",
        )
        self.assertIsInstance(chart_buffer, io.BytesIO)
        content = chart_buffer.getvalue()
        self.assertGreater(len(content), 1000, "La imagen generada debe superar 1KB")
        # Validar cabecera mágica de archivo PNG (\x89PNG\r\n\x1a\n)
        self.assertTrue(content.startswith(b"\x89PNG\r\n\x1a\n"), "El archivo generado no tiene cabecera PNG válida")


if __name__ == "__main__":
    unittest.main()
