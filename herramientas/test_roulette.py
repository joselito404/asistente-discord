"""
Suite de Pruebas Unitarias, de Integración y Simulación Monte Carlo para la Ruleta Europea 37 Casillas (/ruleta):
1. Cilindro europeo de 37 casillas (0 a 36) y formato circular de vecinos.
2. Clasificación rigurosa de colores (18 rojos, 18 negros, 1 verde), paridades, rangos, docenas y columnas.
3. Regla canónica del 0 verde (pierde en suertes sencillas, docenas y columnas; gana únicamente en pleno 0).
4. Pagos exactos para cada tipo de apuesta (1:1, 2:1, 35:1).
5. Simulación Monte Carlo de 50.000 tiradas verificando el RTP teórico del 97.30% (+/- 0.5%).
6. Impacto financiero en balance: descuento atómico, cobro, validación de saldo y alimentación del 3% a jackpot en pérdidas.
7. Interfaz interactiva RouletteActionView (repetir y duplicar apuesta, control de permisos de usuario y timeout).
8. Registro e integridad de /ruleta en ECONOMY_SLASH_COMMANDS, ALL_SLASH_COMMANDS y reexportaciones en bot_service.
"""

import os
import sys
import shutil
import tempfile
import asyncio
import random
from unittest.mock import AsyncMock, MagicMock

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Asegurar que la raíz del proyecto esté en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import discord
import modulos.economia as eco
from modulos.economia import (
    ROULETTE_SEQUENCE,
    ROULETTE_RED,
    ROULETTE_BLACK,
    ROULETTE_GREEN,
    ROULETTE_BET_INFO,
    RouletteEngine,
    RouletteActionView,
    parse_roulette_bet,
    build_roulette_embed,
    format_roulette_pocket,
    normalize_roulette_bet_type,
    is_roulette_winner,
    roulette_engine,
    DEFAULT_JACKPOT,
    JACKPOT_FEED_PERCENT,
)
from modulos.comandos import (
    ECONOMY_SLASH_COMMANDS,
    ALL_SLASH_COMMANDS,
    cmd_ruleta,
)


def run_tests():
    print("=" * 70)
    print("🎡 INICIANDO SUITE DE PRUEBAS DEL MOTOR RULETA EUROPEA 37 CASILLAS")
    print("=" * 70)

    # 1. Configurar entorno temporal aislado para no alterar datos de producción
    temp_dir = tempfile.mkdtemp(prefix="test_roulette_")
    test_json_path = os.path.join(temp_dir, "test_economia.json")

    original_path = eco.ECONOMY_DATA_PATH
    eco.ECONOMY_DATA_PATH = test_json_path
    eco._ECONOMY_CACHE = None

    try:
        # TEST 1: Cilindro europeo de 37 casillas y vecinos circulares
        print("\n[TEST 1] Cilindro europeo de 37 casillas y vecinos circulares...")
        assert len(ROULETTE_SEQUENCE) == 37, f"El cilindro debe tener exactamente 37 casillas, tiene {len(ROULETTE_SEQUENCE)}"
        assert set(ROULETTE_SEQUENCE) == set(range(37)), "El cilindro debe contener todos los números de 0 a 36 sin repetición ni omisión"

        official_sequence = [
            0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10,
            5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
        ]
        assert ROULETTE_SEQUENCE == official_sequence, "La secuencia del cilindro europeo no coincide con la oficial de casino"

        engine = RouletteEngine()

        # Comprobar vecinos circulares en el 0 (inicio de lista)
        disp_0 = engine.get_cylinder_display(0)
        assert "[ 3🟥 ] ➔ [ 26⬛ ] ➔ 👑 [ 0🟩 ] 👑 ➔ [ 32🟥 ] ➔ [ 15⬛ ]" == disp_0, f"Vecinos del 0 incorrectos: {disp_0}"

        # Comprobar vecinos circulares en el 26 (final de lista)
        disp_26 = engine.get_cylinder_display(26)
        assert "[ 35⬛ ] ➔ [ 3🟥 ] ➔ 👑 [ 26⬛ ] 👑 ➔ [ 0🟩 ] ➔ [ 32🟥 ]" == disp_26, f"Vecinos del 26 incorrectos: {disp_26}"

        # Comprobar vecinos en número central (ej. 32)
        disp_32 = engine.get_cylinder_display(32)
        assert "[ 26⬛ ] ➔ [ 0🟩 ] ➔ 👑 [ 32🟥 ] 👑 ➔ [ 15⬛ ] ➔ [ 19🟥 ]" == disp_32, f"Vecinos del 32 incorrectos: {disp_32}"
        print("  ✅ TEST 1 PASADO: Cilindro europeo de 37 casillas y rotación circular de vecinos verificada.")

        # TEST 2: Clasificación de colores, paridades, docenas y columnas
        print("\n[TEST 2] Clasificación de colores, paridades, docenas y columnas...")
        assert len(ROULETTE_RED) == 18, f"Debe haber 18 rojos, hay {len(ROULETTE_RED)}"
        assert len(ROULETTE_BLACK) == 18, f"Debe haber 18 negros, hay {len(ROULETTE_BLACK)}"
        assert ROULETTE_GREEN == {0}, "Solo el 0 debe ser verde"
        assert ROULETTE_RED.isdisjoint(ROULETTE_BLACK), "Rojos y negros deben ser disjuntos"
        assert 0 not in ROULETTE_RED and 0 not in ROULETTE_BLACK, "El 0 no puede ser ni rojo ni negro"
        assert (ROULETTE_RED | ROULETTE_BLACK | ROULETTE_GREEN) == set(range(37))

        # Docenas
        d1 = {n for n in range(1, 37) if is_roulette_winner(n, "docena1")}
        d2 = {n for n in range(1, 37) if is_roulette_winner(n, "docena2")}
        d3 = {n for n in range(1, 37) if is_roulette_winner(n, "docena3")}
        assert d1 == set(range(1, 13)) and len(d1) == 12
        assert d2 == set(range(13, 25)) and len(d2) == 12
        assert d3 == set(range(25, 37)) and len(d3) == 12
        assert d1.isdisjoint(d2) and d2.isdisjoint(d3)

        # Columnas
        c1 = {n for n in range(1, 37) if is_roulette_winner(n, "columna1")}
        c2 = {n for n in range(1, 37) if is_roulette_winner(n, "columna2")}
        c3 = {n for n in range(1, 37) if is_roulette_winner(n, "columna3")}
        assert c1 == {1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34} and len(c1) == 12
        assert c2 == {2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35} and len(c2) == 12
        assert c3 == {3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36} and len(c3) == 12
        assert c1.isdisjoint(c2) and c2.isdisjoint(c3)

        # Paridad y Mitades
        pares = {n for n in range(1, 37) if is_roulette_winner(n, "par")}
        impares = {n for n in range(1, 37) if is_roulette_winner(n, "impar")}
        assert len(pares) == 18 and all(n % 2 == 0 for n in pares)
        assert len(impares) == 18 and all(n % 2 != 0 for n in impares)
        bajas = {n for n in range(1, 37) if is_roulette_winner(n, "baja")}
        altas = {n for n in range(1, 37) if is_roulette_winner(n, "alta")}
        assert bajas == set(range(1, 19)) and len(bajas) == 18
        assert altas == set(range(19, 37)) and len(altas) == 18
        print("  ✅ TEST 2 PASADO: Clasificación matemática exacta de colores, docenas, columnas, paridad y mitades.")

        # TEST 3: Regla del 0 verde (pierde en suertes sencillas, gana solo en pleno 0)
        print("\n[TEST 3] Regla del 0 verde (pierde en suertes sencillas, gana solo en pleno 0)...")
        assert is_roulette_winner(0, "rojo") is False, "El 0 no debe ganar en rojo"
        assert is_roulette_winner(0, "negro") is False, "El 0 no debe ganar en negro"
        assert is_roulette_winner(0, "par") is False, "El 0 no debe ganar en par"
        assert is_roulette_winner(0, "impar") is False, "El 0 no debe ganar en impar"
        assert is_roulette_winner(0, "baja") is False, "El 0 no debe ganar en 1-18"
        assert is_roulette_winner(0, "alta") is False, "El 0 no debe ganar en 19-36"
        assert is_roulette_winner(0, "docena1") is False, "El 0 no debe ganar en docena 1"
        assert is_roulette_winner(0, "docena2") is False, "El 0 no debe ganar en docena 2"
        assert is_roulette_winner(0, "docena3") is False, "El 0 no debe ganar en docena 3"
        assert is_roulette_winner(0, "columna1") is False, "El 0 no debe ganar en columna 1"
        assert is_roulette_winner(0, "columna2") is False, "El 0 no debe ganar en columna 2"
        assert is_roulette_winner(0, "columna3") is False, "El 0 no debe ganar en columna 3"
        assert is_roulette_winner(0, "pleno", bet_number=7) is False, "El 0 no debe ganar en pleno a otro número"
        assert is_roulette_winner(0, "pleno", bet_number=0) is True, "El 0 DEBE ganar si se apostó a pleno al 0"
        print("  ✅ TEST 3 PASADO: Regla del 0 verde verificada al 100%.")

        # TEST 4: Pagos exactos para cada tipo (1:1, 2:1, 35:1)
        print("\n[TEST 4] Pagos exactos para cada tipo (1:1, 2:1, 35:1)...")
        # 1:1 netos (payout total = bet * 2)
        for t in ["rojo", "negro", "par", "impar", "baja", "alta"]:
            assert ROULETTE_BET_INFO[t]["mult"] == 1
            assert ROULETTE_BET_INFO[t]["payout_ratio"] == "1:1"

        # 2:1 netos (payout total = bet * 3)
        for t in ["docena1", "docena2", "docena3", "columna1", "columna2", "columna3"]:
            assert ROULETTE_BET_INFO[t]["mult"] == 2
            assert ROULETTE_BET_INFO[t]["payout_ratio"] == "2:1"

        # 35:1 neto (payout total = bet * 36)
        assert ROULETTE_BET_INFO["pleno"]["mult"] == 35
        assert ROULETTE_BET_INFO["pleno"]["payout_ratio"] == "35:1"

        # Verificación de cálculos en tiradas reales simuladas
        uid_test = 800000000000000001
        eco.ensure_user(uid_test, default_cash=100000)

        # Victoria 1:1 en rojo con bola en 32 (rojo)
        res_color = engine.spin_wheel(uid_test, bet_amount=1000, bet_type="rojo", rng_number=32)
        assert res_color["won"] is True
        assert res_color["net_gain"] == 1000
        assert res_color["payout"] == 2000

        # Victoria 2:1 en docena1 con bola en 5
        res_doc = engine.spin_wheel(uid_test, bet_amount=1000, bet_type="docena1", rng_number=5)
        assert res_doc["won"] is True
        assert res_doc["net_gain"] == 2000
        assert res_doc["payout"] == 3000

        # Victoria 2:1 en columna2 con bola en 14 (14 % 3 == 2)
        res_col = engine.spin_wheel(uid_test, bet_amount=1000, bet_type="columna2", rng_number=14)
        assert res_col["won"] is True
        assert res_col["net_gain"] == 2000
        assert res_col["payout"] == 3000

        # Victoria 35:1 en pleno al 17 con bola en 17
        res_pleno = engine.spin_wheel(uid_test, bet_amount=1000, bet_type="pleno", bet_number=17, rng_number=17)
        assert res_pleno["won"] is True
        assert res_pleno["net_gain"] == 35000
        assert res_pleno["payout"] == 36000

        # Victoria 35:1 en pleno al 0 con bola en 0
        res_pleno0 = engine.spin_wheel(uid_test, bet_amount=1000, bet_type="pleno", bet_number=0, rng_number=0)
        assert res_pleno0["won"] is True
        assert res_pleno0["net_gain"] == 35000
        assert res_pleno0["payout"] == 36000
        print("  ✅ TEST 4 PASADO: Pagos exactos 1:1, 2:1 y 35:1 comprobados en tiradas simuladas.")

        # TEST 5: Simulación Monte Carlo de 50.000 tiradas verificando RTP 97.30% (+/- 0.5%)
        print("\n[TEST 5] Simulación Monte Carlo de 50.000 tiradas verificando RTP 97.30% (+/- 0.5%)...")
        random.seed(42)
        total_bet = 0
        total_return = 0
        bet_types = [
            "rojo", "negro", "par", "impar", "baja", "alta",
            "docena1", "docena2", "docena3", "columna1", "columna2", "columna3", "pleno"
        ]

        for i in range(50000):
            b_type = bet_types[i % len(bet_types)]
            b_num = (i * 7) % 37 if b_type == "pleno" else None
            mult = ROULETTE_BET_INFO[b_type]["mult"]
            ball = random.randint(0, 36)

            total_bet += 100
            if is_roulette_winner(ball, b_type, b_num):
                total_return += 100 * (1 + mult)

        rtp = (total_return / total_bet) * 100.0
        print(f"  📊 Resultado Monte Carlo Ruleta: Tiradas=50,000 | Total Apostado={total_bet:,} | Total Retornado={total_return:,} | RTP={rtp:.2f}%")
        # El RTP teórico es exactamente 36/37 = 97.297% (~97.30%). Rango tolerado: 96.80% - 97.80% (+/- 0.5%)
        assert 96.80 <= rtp <= 97.80, f"RTP fuera de margen de 97.30% (+/- 0.5%): {rtp:.2f}%"
        print("  ✅ TEST 5 PASADO: RTP empírico verificado en 97.30% (+/- 0.5%) en 50.000 tiradas.")

        # TEST 6: Descuento, cobro y alimentación del 3% a jackpot
        print("\n[TEST 6] Descuento, cobro y alimentación del 3% a jackpot...")
        uid_jackpot = 800000000000000002
        eco.ensure_user(uid_jackpot, default_cash=10000)
        eco.reset_server_jackpot(DEFAULT_JACKPOT)
        initial_jackpot = eco.get_server_jackpot()
        assert initial_jackpot == DEFAULT_JACKPOT

        # Tirada perdedora: apuesta 2000 a rojo, bola cae en 2 (negro)
        res_loss = engine.spin_wheel(uid_jackpot, bet_amount=2000, bet_type="rojo", rng_number=2)
        assert res_loss["won"] is False
        assert res_loss["net_gain"] == -2000
        assert res_loss["payout"] == 0
        expected_feed = int(2000 * JACKPOT_FEED_PERCENT)  # 60
        assert res_loss["jackpot_feed"] == expected_feed
        assert eco.get_server_jackpot() == initial_jackpot + expected_feed
        assert eco.get_balance(uid_jackpot)["cash"] == 8000  # 10000 - 2000

        # Tirada ganadora: apuesta 1000 a par, bola cae en 4 (par)
        jackpot_before_win = eco.get_server_jackpot()
        res_win = engine.spin_wheel(uid_jackpot, bet_amount=1000, bet_type="par", rng_number=4)
        assert res_win["won"] is True
        assert res_win["net_gain"] == 1000
        assert res_win["payout"] == 2000
        assert res_win["jackpot_feed"] == 0
        assert eco.get_server_jackpot() == jackpot_before_win  # No cambia en victoria
        assert eco.get_balance(uid_jackpot)["cash"] == 9000  # 8000 - 1000 + 2000

        # Validación de saldo insuficiente
        try:
            engine.spin_wheel(uid_jackpot, bet_amount=20000, bet_type="negro")
            assert False, "Debió lanzar ValueError por fondos insuficientes"
        except ValueError as e:
            assert "insuficientes" in str(e).lower()

        # Parseo de apuestas (mínimo 50, all-in)
        ok, b_val, _ = parse_roulette_bet(uid_jackpot, "500")
        assert ok is True and b_val == 500

        ok, b_val, _ = parse_roulette_bet(uid_jackpot, "all")
        assert ok is True and b_val == 9000

        ok, b_val, err = parse_roulette_bet(uid_jackpot, "20")
        assert ok is False and "mínima" in err.lower()

        ok, b_val, err = parse_roulette_bet(uid_jackpot, "100000")
        assert ok is False and "suficientes" in err.lower()
        print("  ✅ TEST 6 PASADO: Descuento atómico, liquidación, parseo de apuestas y aporte del 3% a jackpot validados.")

        # TEST 7: Interfaz interactiva RouletteActionView (repetir y duplicar)
        print("\n[TEST 7] Interfaz interactiva RouletteActionView (repetir y duplicar)...")
        uid_view = 800000000000000003
        eco.ensure_user(uid_view, default_cash=10000)

        mock_user = MagicMock()
        mock_user.id = uid_view
        mock_user.display_name = "Ruleta Master"
        mock_user.display_avatar.url = "https://example.com/avatar.png"

        view = RouletteActionView(
            user_id=uid_view,
            user=mock_user,
            bet_amount=100,
            bet_type="rojo",
            engine=engine,
        )
        view.message = AsyncMock()

        # Control de permisos (interaction_check)
        mock_owner_inter = AsyncMock()
        mock_owner_inter.user.id = uid_view
        assert asyncio.run(view.interaction_check(mock_owner_inter)) is True

        mock_intruder_inter = AsyncMock()
        mock_intruder_inter.user.id = 999999999999999999
        assert asyncio.run(view.interaction_check(mock_intruder_inter)) is False
        mock_intruder_inter.response.send_message.assert_called_once()
        args, kwargs = mock_intruder_inter.response.send_message.call_args
        assert "no es tuya" in args[0]
        assert kwargs.get("ephemeral") is True

        # Botón Repetir Apuesta (roulette:repeat)
        repeat_btn = next(c for c in view.children if getattr(c, "custom_id", None) == "roulette:repeat")
        assert repeat_btn is not None
        mock_repeat_inter = MagicMock()
        mock_repeat_inter.user.id = uid_view
        mock_repeat_inter.response = AsyncMock()
        mock_repeat_inter.response.is_done = MagicMock(return_value=False)

        asyncio.run(repeat_btn.callback(mock_repeat_inter))
        mock_repeat_inter.response.edit_message.assert_called_once()
        assert view.bet_amount == 100

        # Botón Duplicar Apuesta (roulette:double)
        double_btn = next(c for c in view.children if getattr(c, "custom_id", None) == "roulette:double")
        assert double_btn is not None
        mock_double_inter = MagicMock()
        mock_double_inter.user.id = uid_view
        mock_double_inter.response = AsyncMock()
        mock_double_inter.response.is_done = MagicMock(return_value=False)

        asyncio.run(double_btn.callback(mock_double_inter))
        mock_double_inter.response.edit_message.assert_called_once()
        assert view.bet_amount == 200

        # Timeout: deshabilita todos los botones
        asyncio.run(view.on_timeout())
        for child in view.children:
            if isinstance(child, discord.ui.Button):
                assert child.disabled is True

        # Comprobar generación de Embed
        res_sample = {
            "won": True,
            "winning_number": 32,
            "color": "rojo",
            "color_emoji": "🟥",
            "cylinder_display": engine.get_cylinder_display(32),
            "bet_amount": 500,
            "bet_type": "rojo",
            "bet_desc": "🔴 Rojo",
            "payout_ratio": "1:1",
            "multiplier": 1,
            "net_gain": 500,
            "payout": 1000,
            "jackpot_feed": 0,
            "user_cash": 10500,
            "server_jackpot": 25000,
        }
        embed = build_roulette_embed(mock_user, res_sample)
        assert "Ruleta Europea" in embed.title
        assert "ENHORABUENA" in embed.description
        assert "👑 [ 32🟥 ] 👑" in embed.description
        print("  ✅ TEST 7 PASADO: RouletteActionView (repetir, duplicar, seguridad y timeout) y Embed validados.")

        # TEST 8: Registro en ECONOMY_SLASH_COMMANDS y bot_service
        print("\n[TEST 8] Registro en ECONOMY_SLASH_COMMANDS y bot_service...")
        assert cmd_ruleta in ECONOMY_SLASH_COMMANDS, "cmd_ruleta debe estar en ECONOMY_SLASH_COMMANDS"
        assert cmd_ruleta in ALL_SLASH_COMMANDS, "cmd_ruleta debe estar en ALL_SLASH_COMMANDS"
        assert cmd_ruleta.name == "ruleta"
        assert len(cmd_ruleta.parameters) == 3, f"cmd_ruleta debe tener 3 parámetros (apuesta, tipo, numero), tiene {len(cmd_ruleta.parameters)}"

        # Verificar choices de tipo en cmd_ruleta
        tipo_param = next(p for p in cmd_ruleta.parameters if p.name == "tipo")
        assert len(tipo_param.choices) == 13, f"El parámetro tipo debe tener 13 opciones oficiales, tiene {len(tipo_param.choices)}"

        choice_values = [ch.value for ch in tipo_param.choices]
        expected_values = [
            "rojo", "negro", "par", "impar", "baja", "alta",
            "docena1", "docena2", "docena3", "columna1", "columna2", "columna3", "pleno"
        ]
        assert choice_values == expected_values, f"Choices de tipo incorrectos: {choice_values}"

        import bot_service
        for attr in [
            "ROULETTE_SEQUENCE",
            "ROULETTE_RED",
            "ROULETTE_BLACK",
            "ROULETTE_GREEN",
            "RouletteEngine",
            "roulette_engine",
            "RouletteActionView",
            "parse_roulette_bet",
            "build_roulette_embed",
            "cmd_ruleta",
        ]:
            assert hasattr(bot_service, attr), f"bot_service debe reexportar {attr}"

        assert len(ECONOMY_SLASH_COMMANDS) == 14, f"Debe haber 14 comandos de economía, hay {len(ECONOMY_SLASH_COMMANDS)}"
        assert len(ALL_SLASH_COMMANDS) == 36, f"Debe haber 36 comandos en total, hay {len(ALL_SLASH_COMMANDS)}"
        print("  ✅ TEST 8 PASADO: Presencia en ECONOMY_SLASH_COMMANDS y reexportación pública en bot_service confirmada.")

        print("\n" + "=" * 70)
        print("🎉 TODOS LOS TESTS DE RULETA EUROPEA PASARON SATISFACTORIAMENTE (8/8)")
        print("=" * 70)

    finally:
        eco.ECONOMY_DATA_PATH = original_path
        eco._ECONOMY_CACHE = None
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
