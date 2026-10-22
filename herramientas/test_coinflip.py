"""
Suite de Pruebas Unitarias y de Integración Exhaustiva para Coinflip Dual (PvE y PvP):
1. Validación y parseo de apuestas (/coinflip apuesta) con montos numéricos y all-in ('all', 'todo', 'max').
2. Modo PvE: resolución 50/50 justa, cobro 1:1 en aciertos (retorno 2x) y 3% a jackpot en pérdidas.
3. Simulación Monte Carlo PvE (5.000 tiradas verificando 50/50 +/- 2%).
4. Modo PvP: retención y deducción atómica de la apuesta del retador bajo ECONOMY_LOCK y registro en ACTIVE_COINFLIP_DUELS.
5. Modo PvP: aceptación de desafío con deducción al rival, reparto exacto del 98% al ganador y 2% al server_jackpot (conservación del 100% de la masa monetaria).
6. Modo PvP: rechazo del desafío (por rival o retador) con reembolso íntegro del 100% al retador y limpieza de duelos activos.
7. Modo PvP: resolución por Timeout (60s) con reembolso íntegro del 100% al retador.
8. Modo PvP: protección contra rival sin fondos suficientes al momento de aceptar, con reembolso automático al retador.
9. Control de permisos en CoinflipChallengeView (bloqueo a terceros y al propio retador en aceptar).
10. CoinflipActionView (PvE): repetición de tirada con chequeo de saldo, bloqueo a terceros y timeout.
11. Presencia de /coinflip en ECONOMY_SLASH_COMMANDS (13 comandos) y ALL_SLASH_COMMANDS (35 comandos) y reexportación en bot_service.
"""

import os
import sys
import shutil
import tempfile
import asyncio
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
    CoinflipEngine,
    coinflip_engine,
    CoinflipActionView,
    CoinflipChallengeView,
    ACTIVE_COINFLIP_DUELS,
    parse_coinflip_bet,
    normalize_coinflip_side,
    build_coinflip_embed,
    DEFAULT_JACKPOT,
    JACKPOT_FEED_PERCENT,
)
from modulos.comandos import (
    ECONOMY_SLASH_COMMANDS,
    ALL_SLASH_COMMANDS,
    cmd_coinflip,
    _handle_coinflip_command,
)


def run_tests():
    print("=" * 70)
    print("🪙 INICIANDO SUITE DE PRUEBAS DEL MOTOR COINFLIP DUAL (PvE Y PvP)")
    print("=" * 70)

    # 1. Configurar entorno temporal aislado para no alterar datos de producción
    temp_dir = tempfile.mkdtemp(prefix="test_coinflip_")
    test_json_path = os.path.join(temp_dir, "test_economia.json")

    original_path = eco.ECONOMY_DATA_PATH
    eco.ECONOMY_DATA_PATH = test_json_path
    eco._ECONOMY_CACHE = None
    eco.ACTIVE_COINFLIP_DUELS.clear()

    try:
        # TEST 1: Validación y parseo de apuestas (/coinflip apuesta)
        print("\n[TEST 1] Validación y parseo de apuestas (/coinflip apuesta)...")
        uid_bet = "300000000000000001"
        eco.ensure_user(uid_bet, default_cash=1000)

        # Apuesta numérica válida
        ok, bet, err = parse_coinflip_bet(uid_bet, "100")
        assert ok is True and bet == 100, f"Debe aceptar 100, error: {err}"

        # Apuesta por debajo del mínimo (100)
        ok, bet, err = parse_coinflip_bet(uid_bet, "49")
        assert ok is False and "mínima en Coinflip es de 100" in err
        ok, bet, err = parse_coinflip_bet(uid_bet, "99")
        assert ok is False and "mínima en Coinflip es de 100" in err

        # Apuestas all-in: 'all', 'todo', 'max'
        ok, bet, err = parse_coinflip_bet(uid_bet, "all")
        assert ok is True and bet == 1000, f"all debe ser 1000, obtenido {bet}"

        ok, bet, err = parse_coinflip_bet(uid_bet, "TODO")
        assert ok is True and bet == 1000

        ok, bet, err = parse_coinflip_bet(uid_bet, "max")
        assert ok is True and bet == 1000

        # Saldo insuficiente
        ok, bet, err = parse_coinflip_bet(uid_bet, "2500")
        assert ok is False and "No tienes suficientes Porros" in err

        # Formato inválido
        ok, bet, err = parse_coinflip_bet(uid_bet, "invalido")
        assert ok is False and "inválida" in err

        # Normalización de lados
        assert normalize_coinflip_side("cara") == "cara"
        assert normalize_coinflip_side("cruz") == "cruz"
        assert normalize_coinflip_side("🪙 Cara") == "cara"
        assert normalize_coinflip_side("🪙 Cruz") == "cruz"
        assert normalize_coinflip_side("tails") == "cruz"
        print("  ✅ TEST 1 PASADO: Parseo y validación de apuestas y lados verificado.")

        # TEST 2: Modo PvE: resolución y cálculo financiero (pago 1:1 y 3% a jackpot)
        print("\n[TEST 2] Modo PvE: cobro 1:1 en aciertos y 3% a jackpot en pérdidas...")
        uid_pve = "300000000000000002"
        eco.ensure_user(uid_pve, default_cash=1000)
        engine = CoinflipEngine()

        # 2.1 Acierto (Victoria 1:1, retorno 2x)
        # Apuesta 200 a 'cara', la moneda cae en 'cara'
        res_win = engine.play_pve(user_id=uid_pve, bet_amount=200, choice="cara", rng_outcome="cara")
        assert res_win["won"] is True
        assert res_win["outcome"] == "cara"
        assert res_win["net_gain"] == 200
        assert res_win["payout"] == 400
        assert res_win["jackpot_feed"] == 0
        assert res_win["user_cash"] == 1200, f"Cash esperado 1200, obtenido {res_win['user_cash']}"
        assert eco.get_balance(uid_pve)["cash"] == 1200

        # 2.2 Fallo (Derrota, pérdida neta y 3% al jackpot)
        # Apuesta 300 a 'cara', la moneda cae en 'cruz'
        jackpot_before = eco.get_server_jackpot()
        res_loss = engine.play_pve(user_id=uid_pve, bet_amount=300, choice="cara", rng_outcome="cruz")
        assert res_loss["won"] is False
        assert res_loss["outcome"] == "cruz"
        assert res_loss["net_gain"] == -300
        assert res_loss["payout"] == 0
        expected_feed = max(1, int(300 * JACKPOT_FEED_PERCENT))  # 3% de 300 = 9
        assert res_loss["jackpot_feed"] == expected_feed
        assert res_loss["user_cash"] == 900
        assert eco.get_balance(uid_pve)["cash"] == 900
        assert eco.get_server_jackpot() == jackpot_before + expected_feed
        print("  ✅ TEST 2 PASADO: Mecánica financiera PvE (1:1 payout y 3% jackpot feed) verificada.")

        # TEST 3: Simulación Monte Carlo PvE (5.000 tiradas 50/50)
        print("\n[TEST 3] Simulación Monte Carlo PvE (5.000 tiradas)...")
        cara_count = 0
        cruz_count = 0
        for _ in range(5000):
            flip = engine.flip_coin()
            if flip == "cara":
                cara_count += 1
            else:
                cruz_count += 1

        pct_cara = (cara_count / 5000) * 100
        pct_cruz = (cruz_count / 5000) * 100
        print(f"  📊 Resultado: Cara = {pct_cara:.2f}% | Cruz = {pct_cruz:.2f}%")
        assert 48.0 <= pct_cara <= 52.0, f"Probabilidad de Cara fuera del margen 50/50: {pct_cara}%"
        assert 48.0 <= pct_cruz <= 52.0, f"Probabilidad de Cruz fuera del margen 50/50: {pct_cruz}%"
        print("  ✅ TEST 3 PASADO: Equidad justa 50/50 confirmada en simulación.")

        # TEST 4: Modo PvP: Retención atómica de fondos del retador y bloqueo de concurrencia
        print("\n[TEST 4] Modo PvP: Retención de fondos y control de concurrencia...")
        uid_c = "400000000000000001"
        uid_r = "400000000000000002"
        eco.ensure_user(uid_c, default_cash=1000)
        eco.ensure_user(uid_r, default_cash=1000)

        mock_challenger = MagicMock()
        mock_challenger.id = int(uid_c)
        mock_challenger.display_name = "Retador 1"
        mock_challenger.mention = f"<@{uid_c}>"

        mock_rival = MagicMock()
        mock_rival.id = int(uid_r)
        mock_rival.display_name = "Rival 1"
        mock_rival.mention = f"<@{uid_r}>"
        mock_rival.bot = False

        inter_pvp = AsyncMock()
        inter_pvp.user = mock_challenger
        inter_pvp.response.is_done = MagicMock(return_value=False)

        asyncio.run(_handle_coinflip_command(inter_pvp, apuesta="200", lado="cara", rival=mock_rival))

        # El saldo del retador debe haber sido descontado en 200 (queda en 800)
        assert eco.get_balance(uid_c)["cash"] == 800, f"Cash del retador debe ser 800, tiene {eco.get_balance(uid_c)['cash']}"
        # El saldo del rival no se toca hasta que acepte (queda en 1000)
        assert eco.get_balance(uid_r)["cash"] == 1000

        # Ambos deben estar registrados en ACTIVE_COINFLIP_DUELS
        assert uid_c in eco.ACTIVE_COINFLIP_DUELS
        assert uid_r in eco.ACTIVE_COINFLIP_DUELS

        # Intento de segundo reto por parte del retador mientras está en duelo
        inter_dup = AsyncMock()
        inter_dup.user = mock_challenger
        asyncio.run(_handle_coinflip_command(inter_dup, apuesta="100", lado="cara", rival=mock_rival))
        inter_dup.response.send_message.assert_called_once()
        args, kwargs = inter_dup.response.send_message.call_args
        assert "Ya tienes un duelo de Coinflip activo" in args[0]
        assert kwargs.get("ephemeral") is True
        # El cash del retador sigue siendo 800 (no hay doble descuento)
        assert eco.get_balance(uid_c)["cash"] == 800

        # Limpiar para los siguientes tests
        eco.modify_balance(uid_c, cash_delta=+200)
        eco.ACTIVE_COINFLIP_DUELS.clear()
        print("  ✅ TEST 4 PASADO: Retención atómica y blindaje contra dobles retos verificado.")

        # TEST 5: Modo PvP: Aceptación de desafío, reparto 98%/2% y conservación monetaria
        print("\n[TEST 5] Modo PvP: Aceptación de duelo, 98% a ganador y 2% a jackpot...")
        uid_c5 = "500000000000000001"
        uid_r5 = "500000000000000002"
        eco.ensure_user(uid_c5, default_cash=1000)
        eco.ensure_user(uid_r5, default_cash=1000)

        # Retador apuesta 200 (se retiene previamente)
        eco.modify_balance(uid_c5, cash_delta=-200)
        eco.ACTIVE_COINFLIP_DUELS[uid_c5] = True
        eco.ACTIVE_COINFLIP_DUELS[uid_r5] = True

        mock_c5 = MagicMock()
        mock_c5.id = int(uid_c5)
        mock_c5.display_name = "Alice"

        mock_r5 = MagicMock()
        mock_r5.id = int(uid_r5)
        mock_r5.display_name = "Bob"

        # CoinflipEngine resolución forzada a 'cara' (gana challenger Alice)
        jackpot_start = eco.get_server_jackpot()
        res_pvp_win_c = engine.resolve_pvp(
            challenger_id=uid_c5,
            rival_id=uid_r5,
            bet_amount=200,
            challenger_side="cara",
            rng_outcome="cara",
        )

        assert res_pvp_win_c["winner_id"] == uid_c5
        assert res_pvp_win_c["winner_role"] == "challenger"
        assert res_pvp_win_c["total_pot"] == 400
        assert res_pvp_win_c["jackpot_cut"] == 8  # 2% de 400 = 8
        assert res_pvp_win_c["winner_prize"] == 392  # 98% de 400 = 392

        # Bob (rival) fue debitado en 200 (1000 - 200 = 800)
        assert eco.get_balance(uid_r5)["cash"] == 800
        # Alice (challenger) cobró 392 (800 inicial restante + 392 = 1192)
        assert eco.get_balance(uid_c5)["cash"] == 1192
        # Jackpot subió en 8
        assert eco.get_server_jackpot() == jackpot_start + 8

        # Conservación estricta de fondos:
        # Total inicial: 1000 + 1000 = 2000
        # Total final: 1192 (Alice) + 800 (Bob) + 8 (Jackpot) = 2000. Balance perfecto al céntimo.
        total_final = eco.get_balance(uid_c5)["cash"] + eco.get_balance(uid_r5)["cash"] + 8
        assert total_final == 2000, f"La masa monetaria total debe ser 2000, obtenido {total_final}"

        # Prueba con victoria del rival (Bob gana cuando sale cruz)
        res_pvp_win_r = engine.resolve_pvp(
            challenger_id=uid_c5,
            rival_id=uid_r5,
            bet_amount=100,
            challenger_side="cara",
            rng_outcome="cruz",
        )
        assert res_pvp_win_r["winner_id"] == uid_r5
        assert res_pvp_win_r["winner_role"] == "rival"
        assert res_pvp_win_r["total_pot"] == 200
        assert res_pvp_win_r["jackpot_cut"] == 4
        assert res_pvp_win_r["winner_prize"] == 196
        print("  ✅ TEST 5 PASADO: Reparto exacto (98% ganador, 2% jackpot) y conservación monetaria verificada.")

        # TEST 6: Modo PvP: Rechazo de desafío y reembolso íntegro del 100%
        print("\n[TEST 6] Modo PvP: Rechazo de desafío y reembolso al retador...")
        uid_c6 = "600000000000000001"
        uid_r6 = "600000000000000002"
        eco.ensure_user(uid_c6, default_cash=1000)
        eco.ensure_user(uid_r6, default_cash=1000)

        # Retador apuesta 300 (descontado al iniciar)
        eco.modify_balance(uid_c6, cash_delta=-300)
        eco.ACTIVE_COINFLIP_DUELS[str(uid_c6)] = True
        eco.ACTIVE_COINFLIP_DUELS[str(uid_r6)] = True

        mock_c6 = MagicMock()
        mock_c6.id = int(uid_c6)
        mock_c6.display_name = "Retador 6"

        mock_r6 = MagicMock()
        mock_r6.id = int(uid_r6)
        mock_r6.display_name = "Rival 6"

        view_reject = CoinflipChallengeView(
            challenger_id=int(uid_c6),
            challenger=mock_c6,
            rival_id=int(uid_r6),
            rival=mock_r6,
            bet_amount=300,
            challenger_side="cara",
        )

        # El rival pulsa [ 🏳️ Rechazar ]
        mock_inter_decl = AsyncMock()
        mock_inter_decl.user.id = int(uid_r6)
        mock_inter_decl.response.is_done = MagicMock(return_value=False)

        asyncio.run(view_reject.do_decline(mock_inter_decl))

        assert view_reject.resolved is True
        # El retador debe haber recibido el reembolso íntegro de 300 (vuelve a 1000)
        assert eco.get_balance(uid_c6)["cash"] == 1000, f"Cash del retador debe volver a 1000, tiene {eco.get_balance(uid_c6)['cash']}"
        # El rival mantiene sus 1000 intactos
        assert eco.get_balance(uid_r6)["cash"] == 1000
        # ACTIVE_COINFLIP_DUELS debe estar limpio
        assert str(uid_c6) not in eco.ACTIVE_COINFLIP_DUELS
        assert str(uid_r6) not in eco.ACTIVE_COINFLIP_DUELS
        print("  ✅ TEST 6 PASADO: Rechazo con reembolso del 100% verificado.")

        # TEST 7: Modo PvP: Resolución por Timeout (60 segundos)
        print("\n[TEST 7] Modo PvP: Timeout (60s) con reembolso automático...")
        uid_c7 = "700000000000000001"
        uid_r7 = "700000000000000002"
        eco.ensure_user(uid_c7, default_cash=1000)
        eco.ensure_user(uid_r7, default_cash=1000)

        # Retador apuesta 450
        eco.modify_balance(uid_c7, cash_delta=-450)
        eco.ACTIVE_COINFLIP_DUELS[str(uid_c7)] = True
        eco.ACTIVE_COINFLIP_DUELS[str(uid_r7)] = True

        mock_c7 = MagicMock()
        mock_c7.id = int(uid_c7)
        mock_c7.display_name = "Retador 7"

        mock_r7 = MagicMock()
        mock_r7.id = int(uid_r7)
        mock_r7.display_name = "Rival 7"

        view_timeout = CoinflipChallengeView(
            challenger_id=int(uid_c7),
            challenger=mock_c7,
            rival_id=int(uid_r7),
            rival=mock_r7,
            bet_amount=450,
            challenger_side="cara",
        )
        view_timeout.message = AsyncMock()

        # Simular disparo de timeout
        asyncio.run(view_timeout.on_timeout())

        assert view_timeout.resolved is True
        # Reembolso íntegro al retador (550 + 450 = 1000)
        assert eco.get_balance(uid_c7)["cash"] == 1000
        assert str(uid_c7) not in eco.ACTIVE_COINFLIP_DUELS
        assert str(uid_r7) not in eco.ACTIVE_COINFLIP_DUELS
        print("  ✅ TEST 7 PASADO: Timeout a los 60s con reembolso del 100% verificado.")

        # TEST 8: Modo PvP: Rival sin fondos suficientes al aceptar
        print("\n[TEST 8] Modo PvP: Protección contra rival tieso (sin fondos)...")
        uid_c8 = "800000000000000001"
        uid_r8 = "800000000000000002"
        eco.ensure_user(uid_c8, default_cash=1000)
        eco.ensure_user(uid_r8, default_cash=50)  # Rival solo tiene 50

        # Retador apuesta 500 (descontado al retar)
        eco.modify_balance(uid_c8, cash_delta=-500)
        eco.ACTIVE_COINFLIP_DUELS[str(uid_c8)] = True
        eco.ACTIVE_COINFLIP_DUELS[str(uid_r8)] = True

        mock_c8 = MagicMock()
        mock_c8.id = int(uid_c8)
        mock_c8.display_name = "Retador 8"

        mock_r8 = MagicMock()
        mock_r8.id = int(uid_r8)
        mock_r8.display_name = "Rival Tieso"

        view_broke = CoinflipChallengeView(
            challenger_id=int(uid_c8),
            challenger=mock_c8,
            rival_id=int(uid_r8),
            rival=mock_r8,
            bet_amount=500,
            challenger_side="cara",
        )

        # El rival pulsa aceptar
        mock_inter_accept = AsyncMock()
        mock_inter_accept.user.id = int(uid_r8)
        mock_inter_accept.response.is_done = MagicMock(return_value=False)

        asyncio.run(view_broke.do_accept(mock_inter_accept))

        assert view_broke.resolved is True
        # El retador debe ser reembolsado inmediatamente
        assert eco.get_balance(uid_c8)["cash"] == 1000
        # El rival no puede quedar en negativo
        assert eco.get_balance(uid_r8)["cash"] == 50
        assert str(uid_c8) not in eco.ACTIVE_COINFLIP_DUELS
        assert str(uid_r8) not in eco.ACTIVE_COINFLIP_DUELS
        print("  ✅ TEST 8 PASADO: Cancelación y reembolso automático si el rival no tiene saldo suficiente.")

        # TEST 9: Control de interacción y permisos en CoinflipChallengeView
        print("\n[TEST 9] Control de permisos en CoinflipChallengeView (bloqueo a terceros)...")
        uid_c9 = 900000000000000001
        uid_r9 = 900000000000000002
        uid_intruder = 999999999999999999

        mock_c9 = MagicMock()
        mock_c9.id = uid_c9
        mock_c9.display_name = "Challenger 9"

        mock_r9 = MagicMock()
        mock_r9.id = uid_r9
        mock_r9.display_name = "Rival 9"

        view_perms = CoinflipChallengeView(
            challenger_id=uid_c9,
            challenger=mock_c9,
            rival_id=uid_r9,
            rival=mock_r9,
            bet_amount=100,
        )

        # Intruso intenta pulsar [ Aceptar ]
        mock_inter_int = AsyncMock()
        mock_inter_int.user.id = uid_intruder
        asyncio.run(view_perms.do_accept(mock_inter_int))
        mock_inter_int.response.send_message.assert_called_once()
        args, kwargs = mock_inter_int.response.send_message.call_args
        assert "Solo Rival 9 puede aceptar" in args[0]
        assert kwargs.get("ephemeral") is True

        # Challenger intenta pulsar [ Aceptar ] en su propio reto
        mock_inter_self = AsyncMock()
        mock_inter_self.user.id = uid_c9
        asyncio.run(view_perms.do_accept(mock_inter_self))
        mock_inter_self.response.send_message.assert_called_once()
        args_s, kwargs_s = mock_inter_self.response.send_message.call_args
        assert "No puedes aceptar tu propio desafío" in args_s[0]
        assert kwargs_s.get("ephemeral") is True

        # Intruso intenta pulsar [ Rechazar ]
        mock_inter_int2 = AsyncMock()
        mock_inter_int2.user.id = uid_intruder
        asyncio.run(view_perms.do_decline(mock_inter_int2))
        mock_inter_int2.response.send_message.assert_called_once()
        args_d, kwargs_d = mock_inter_int2.response.send_message.call_args
        assert "No participas en este duelo" in args_d[0]
        assert kwargs_d.get("ephemeral") is True
        print("  ✅ TEST 9 PASADO: Control estricto de permisos y bloqueos efímeros verificado.")

        # TEST 10: CoinflipActionView (PvE): repetición, permisos y timeout
        print("\n[TEST 10] CoinflipActionView (PvE): repetición de tirada y chequeo de saldo...")
        uid_pve10 = 100000000000000001
        eco.ensure_user(uid_pve10, default_cash=1000)

        mock_u10 = MagicMock()
        mock_u10.id = uid_pve10
        mock_u10.display_name = "Player PvE"

        view_action = CoinflipActionView(
            user_id=uid_pve10,
            user=mock_u10,
            bet_amount=200,
            side="cara",
            engine=engine,
        )

        # Chequeo de interacción de intruso
        inter_int_pve = AsyncMock()
        inter_int_pve.user.id = uid_intruder
        allowed = asyncio.run(view_action.interaction_check(inter_int_pve))
        assert allowed is False
        inter_int_pve.response.send_message.assert_called_once()

        # Repetición legítima por el dueño con saldo suficiente
        inter_owner_pve = AsyncMock()
        inter_owner_pve.user.id = uid_pve10
        inter_owner_pve.response.is_done = MagicMock(return_value=False)

        cash_before = eco.get_balance(uid_pve10)["cash"]
        asyncio.run(view_action.do_flip_again(inter_owner_pve))
        # Cash debe haber cambiado (o +200 si ganó o -200 si perdió)
        cash_after = eco.get_balance(uid_pve10)["cash"]
        assert cash_after in (cash_before + 200, cash_before - 200)

        # Timeout de la vista
        view_action.message = AsyncMock()
        asyncio.run(view_action.on_timeout())
        for child in view_action.children:
            if isinstance(child, discord.ui.Button):
                assert child.disabled is True
        print("  ✅ TEST 10 PASADO: CoinflipActionView validada en repetición, saldo y timeout.")

        # TEST 11: Presencia en ECONOMY_SLASH_COMMANDS y reexportación en bot_service
        print("\n[TEST 11] Integridad de /coinflip en el Runner Dual y bot_service...")
        assert cmd_coinflip in ECONOMY_SLASH_COMMANDS, "cmd_coinflip debe estar en ECONOMY_SLASH_COMMANDS"
        assert cmd_coinflip in ALL_SLASH_COMMANDS, "cmd_coinflip debe estar en ALL_SLASH_COMMANDS"
        assert cmd_coinflip.name == "coinflip"
        assert len(cmd_coinflip.parameters) == 3, f"cmd_coinflip debe tener 3 parámetros, tiene {len(cmd_coinflip.parameters)}"

        # Verificar choices de 'lado'
        lado_param = next(p for p in cmd_coinflip.parameters if p.name == "lado")
        assert len(lado_param.choices) == 2, f"El parámetro lado debe tener 2 opciones, tiene {len(lado_param.choices)}"
        choice_vals = [ch.value for ch in lado_param.choices]
        assert "cara" in choice_vals and "cruz" in choice_vals

        import bot_service
        for attr in [
            "CoinflipEngine",
            "coinflip_engine",
            "ACTIVE_COINFLIP_DUELS",
            "CoinflipActionView",
            "CoinflipChallengeView",
            "parse_coinflip_bet",
            "normalize_coinflip_side",
            "build_coinflip_embed",
            "cmd_coinflip",
        ]:
            assert hasattr(bot_service, attr), f"bot_service debe reexportar {attr}"

        assert len(ECONOMY_SLASH_COMMANDS) == 23, f"Debe haber 20 comandos de economía, hay {len(ECONOMY_SLASH_COMMANDS)}"
        assert len(ALL_SLASH_COMMANDS) == 46, f"Debe haber 43 comandos en total, hay {len(ALL_SLASH_COMMANDS)}"
        print("  ✅ TEST 11 PASADO: Registro de /coinflip y reexportación en bot_service confirmada.")

        print("\n" + "=" * 70)
        print("🎉 TODOS LOS TESTS DE COINFLIP DUAL PASARON SATISFACTORIAMENTE (11/11)")
        print("=" * 70)

    finally:
        eco.ECONOMY_DATA_PATH = original_path
        eco._ECONOMY_CACHE = None
        eco.ACTIVE_COINFLIP_DUELS.clear()
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
