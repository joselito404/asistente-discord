"""
Suite de Pruebas Unitarias y de Integración para el Sistema de Blackjack 21 Nativo:
1. Cálculo de manos con Ases flexibles (manos blandas y duras, múltiples Ases, reducción dinámica).
2. Detección precisa de Blackjack Natural (exactamente 2 cartas sumando 21 vs 21 con 3+ cartas).
3. Reglas del Dealer (Dealer stands on all 17s - hard 17 y soft 17, dealer hits on <= 16, dealer bust).
4. Zapato de 6 barajas (312 cartas) y rebarajado automático al bajar de 52 cartas.
5. Validación y parseo de apuestas con montos numéricos y opciones 'all' / 'todo' / 'max'.
6. Mecánica de Doblar (Double Down: chequeo de saldo, duplicación de apuesta, 1 sola carta y resolución).
7. Impacto financiero en balance: descuento atómico, victoria 1:1, Blackjack natural 3:2, empate (push) y pérdida con 3% a jackpot.
8. Control de concurrencia y bloqueo de partidas solapadas (ACTIVE_BLACKJACK_GAMES).
9. Control de interacción y permisos en BlackjackView (rechazo efímero a terceros).
10. Resolución de timeout (Auto-stand de seguridad a 60s).
11. Registro e integridad de /blackjack y /bj en ECONOMY_SLASH_COMMANDS y ALL_SLASH_COMMANDS.
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
    BlackjackHand,
    BlackjackEngine,
    BlackjackView,
    ACTIVE_BLACKJACK_GAMES,
    parse_blackjack_bet,
    build_blackjack_embed,
    format_bj_card,
    get_bj_card_value,
    BJ_SUITS,
    BJ_RANKS,
    DEFAULT_JACKPOT,
    JACKPOT_FEED_PERCENT,
)
from modulos.comandos import (
    ECONOMY_SLASH_COMMANDS,
    ALL_SLASH_COMMANDS,
    cmd_blackjack,
    cmd_bj,
)


def run_tests():
    print("=" * 70)
    print("🎰 INICIANDO SUITE DE PRUEBAS DEL MOTOR BLACKJACK 21 NATIVO")
    print("=" * 70)

    # 1. Configurar entorno temporal aislado para no alterar datos de producción
    temp_dir = tempfile.mkdtemp(prefix="test_bj_")
    test_json_path = os.path.join(temp_dir, "test_economia.json")

    original_path = eco.ECONOMY_DATA_PATH
    eco.ECONOMY_DATA_PATH = test_json_path
    eco._ECONOMY_CACHE = None
    eco.ACTIVE_BLACKJACK_GAMES.clear()

    try:
        # TEST 1: Zapato de 6 barajas (312 cartas) y rebarajado automático
        print("\n[TEST 1] Zapato de 6 barajas (312 cartas) y rebarajado automático...")
        engine = BlackjackEngine(num_decks=6)
        assert len(engine.cards) == 312, f"El zapato debe contener 312 cartas, tiene {len(engine.cards)}"

        # Verificar distribución de palos y rangos
        counts = {}
        for suit, rank in engine.cards:
            counts[(suit, rank)] = counts.get((suit, rank), 0) + 1
        for suit in BJ_SUITS:
            for rank in BJ_RANKS:
                assert counts.get((suit, rank), 0) == 6, f"Cada carta debe aparecer 6 veces, {(suit, rank)} aparece {counts.get((suit, rank), 0)}"

        # Simular robo hasta bajar de 52 cartas
        while len(engine.cards) >= 52:
            engine.draw()
        assert len(engine.cards) == 51
        # Al pedir la siguiente, debe detectar < 52 y rebarajar automáticamente a 312 antes de entregarla
        next_card = engine.draw()
        assert isinstance(next_card, tuple) and len(next_card) == 2
        assert len(engine.cards) == 311, f"Tras rebarajar y entregar 1 carta debe haber 311, hay {len(engine.cards)}"
        print("  ✅ TEST 1 PASADO: Zapato de 312 cartas y rebarajado a < 52 verificado.")

        # TEST 2: Cálculo de manos con Ases flexibles (blandas y duras)
        print("\n[TEST 2] Cálculo de manos con Ases flexibles (blandas y duras)...")
        # Mano suave A + 8 = 19
        h1 = BlackjackHand([("♠️", "A"), ("♥️", "8")])
        assert h1.value == 19, f"A + 8 debe ser 19, obtenido {h1.value}"
        assert h1.is_soft is True, "A + 8 debe ser mano blanda (Soft 19)"
        assert h1.is_bust is False

        # Mano dura A + 8 + 5 = 14 (As reducido de 11 a 1)
        h1.add_card(("♦️", "5"))
        assert h1.value == 14, f"A + 8 + 5 debe ser 14, obtenido {h1.value}"
        assert h1.is_soft is False, "A + 8 + 5 debe ser mano dura (Hard 14)"
        assert h1.is_bust is False

        # Mano con 2 Ases iniciales: A + A = 12 (uno como 11, otro como 1)
        h2 = BlackjackHand([("♠️", "A"), ("♦️", "A")])
        assert h2.value == 12, f"A + A debe ser 12, obtenido {h2.value}"
        assert h2.is_soft is True, "A + A debe ser blanda (Soft 12)"

        # Mano con 2 Ases y un 9: A + A + 9 = 21 (uno como 11, uno como 1, + 9)
        h2.add_card(("♣️", "9"))
        assert h2.value == 21, f"A + A + 9 debe ser 21, obtenido {h2.value}"
        assert h2.is_soft is True, "A + A + 9 debe ser blanda (Soft 21)"
        assert h2.is_bust is False

        # Mano con 2 Ases y un 10: A + A + 10 = 12 (ambos Ases forzados a 1)
        h3 = BlackjackHand([("♠️", "A"), ("♦️", "A"), ("♣️", "10")])
        assert h3.value == 12, f"A + A + 10 debe ser 12, obtenido {h3.value}"
        assert h3.is_soft is False, "A + A + 10 debe ser dura (Hard 12)"

        # Mano dura sin Ases: 10 + 6 + 5 = 21
        h4 = BlackjackHand([("♠️", "10"), ("♥️", "6"), ("♦️", "5")])
        assert h4.value == 21, f"10 + 6 + 5 debe ser 21, obtenido {h4.value}"
        assert h4.is_soft is False, "10 + 6 + 5 no debe ser blanda"

        # Manos pasadas (Bust)
        h_bust1 = BlackjackHand([("♠️", "10"), ("♥️", "7"), ("♦️", "8")])
        assert h_bust1.value == 25, f"10 + 7 + 8 debe ser 25, obtenido {h_bust1.value}"
        assert h_bust1.is_bust is True, "25 debe ser Bust"
        assert h_bust1.is_soft is False

        h_bust2 = BlackjackHand([("♠️", "A"), ("♥️", "5"), ("♦️", "7"), ("♣️", "10")])
        assert h_bust2.value == 23, f"A + 5 + 7 + 10 debe ser 23 (1+5+7+10), obtenido {h_bust2.value}"
        assert h_bust2.is_bust is True, "23 debe ser Bust"
        print("  ✅ TEST 2 PASADO: Ases dinámicos, manos blandas/duras y detección de Bust verificadas.")

        # TEST 3: Detección estricta de Blackjack Natural
        print("\n[TEST 3] Detección estricta de Blackjack Natural...")
        # Blackjack Naturales (exactamente 2 cartas con As + 10-val)
        bj_k = BlackjackHand([("♠️", "A"), ("♥️", "K")])
        assert bj_k.is_blackjack is True, "A + K debe ser Blackjack Natural"

        bj_10 = BlackjackHand([("♦️", "10"), ("♣️", "A")])
        assert bj_10.is_blackjack is True, "10 + A debe ser Blackjack Natural"

        bj_q = BlackjackHand([("♥️", "Q"), ("♠️", "A")])
        assert bj_q.is_blackjack is True, "Q + A debe ser Blackjack Natural"

        bj_j = BlackjackHand([("♣️", "J"), ("♦️", "A")])
        assert bj_j.is_blackjack is True, "J + A debe ser Blackjack Natural"

        # NO Natural Blackjack (21 con 3+ cartas)
        not_bj1 = BlackjackHand([("♠️", "7"), ("♥️", "7"), ("♦️", "7")])
        assert not_bj1.value == 21
        assert not_bj1.is_blackjack is False, "7 + 7 + 7 = 21 NO es Blackjack Natural"

        not_bj2 = BlackjackHand([("♠️", "9"), ("♥️", "2"), ("♦️", "K")])
        assert not_bj2.value == 21
        assert not_bj2.is_blackjack is False, "9 + 2 + K = 21 NO es Blackjack Natural"

        not_bj3 = BlackjackHand([("♠️", "A"), ("♥️", "9")])
        assert not_bj3.value == 20
        assert not_bj3.is_blackjack is False, "A + 9 = 20 NO es Blackjack Natural"
        print("  ✅ TEST 3 PASADO: Detección estricta de Blackjack Natural verificada.")

        # TEST 4: Reglas del Crupier (Dealer stands on all 17s - S17)
        print("\n[TEST 4] Reglas del Crupier (Plantarse en >= 17 y pedir en <= 16)...")
        # Dealer en Hard 17: se planta inmediatamente
        d1 = BlackjackHand([("♠️", "10"), ("♥️", "7")])
        mock_eng1 = BlackjackEngine()
        mock_eng1.draw = MagicMock(return_value=("♦️", "5"))
        mock_eng1.play_dealer_turn(d1)
        assert d1.value == 17
        mock_eng1.draw.assert_not_called()

        # Dealer en Soft 17 (A + 6): se planta inmediatamente (regla S17 oficial del servidor)
        d2 = BlackjackHand([("♠️", "A"), ("♥️", "6")])
        mock_eng2 = BlackjackEngine()
        mock_eng2.draw = MagicMock(return_value=("♦️", "5"))
        mock_eng2.play_dealer_turn(d2)
        assert d2.value == 17
        mock_eng2.draw.assert_not_called()

        # Dealer en 16: pide carta
        d3 = BlackjackHand([("♠️", "10"), ("♥️", "6")])
        mock_eng3 = BlackjackEngine()
        mock_eng3.draw = MagicMock(side_effect=[("♦️", "3")])  # 16 + 3 = 19
        mock_eng3.play_dealer_turn(d3)
        assert d3.value == 19
        assert mock_eng3.draw.call_count == 1

        # Dealer en 12: pide dos veces hasta llegar a 18
        d4 = BlackjackHand([("♠️", "8"), ("♥️", "4")])
        mock_eng4 = BlackjackEngine()
        mock_eng4.draw = MagicMock(side_effect=[("♦️", "3"), ("♣️", "3")])  # 12 + 3 = 15 -> 15 + 3 = 18
        mock_eng4.play_dealer_turn(d4)
        assert d4.value == 18
        assert mock_eng4.draw.call_count == 2

        # Dealer se pasa (Bust): 16 + 8 = 24
        d5 = BlackjackHand([("♠️", "10"), ("♥️", "6")])
        mock_eng5 = BlackjackEngine()
        mock_eng5.draw = MagicMock(side_effect=[("♦️", "8")])
        mock_eng5.play_dealer_turn(d5)
        assert d5.value == 24
        assert d5.is_bust is True
        print("  ✅ TEST 4 PASADO: Reglas del crupier (stands on 17+, hits on <=16, bust) verificadas.")

        # TEST 5: Validación y parseo de apuestas (/blackjack apuesta)
        print("\n[TEST 5] Validación y parseo de apuestas (/blackjack apuesta)...")
        uid_bet = "200000000000000001"
        eco.ensure_user(uid_bet, default_cash=1000)

        # Apuesta numérica válida
        ok, bet, err = parse_blackjack_bet(uid_bet, "150")
        assert ok is True and bet == 150, f"Debe aceptar 150, err: {err}"

        # Apuesta menor al mínimo (< 100)
        ok, bet, err = parse_blackjack_bet(uid_bet, "49")
        assert ok is False and "mínima en Blackjack es de 100" in err
        ok, bet, err = parse_blackjack_bet(uid_bet, "99")
        assert ok is False and "mínima en Blackjack es de 100" in err

        # Apuestas de all-in: 'all', 'todo', 'max'
        ok, bet, err = parse_blackjack_bet(uid_bet, "all")
        assert ok is True and bet == 1000, f"all debe ser 1000, obtenido {bet}"

        ok, bet, err = parse_blackjack_bet(uid_bet, "TODO")
        assert ok is True and bet == 1000

        ok, bet, err = parse_blackjack_bet(uid_bet, "Max")
        assert ok is True and bet == 1000

        # Fondos insuficientes
        ok, bet, err = parse_blackjack_bet(uid_bet, "5000")
        assert ok is False and "No tienes suficientes Porros" in err

        # Formato inválido
        ok, bet, err = parse_blackjack_bet(uid_bet, "invalid_amount")
        assert ok is False and "inválida" in err
        print("  ✅ TEST 5 PASADO: Parseo y validación de apuestas (min 100, all-in, límites) verificado.")

        # TEST 6: Mecánica financiera (Descuento, Pago 3:2, Pago 1:1, Push y Pérdida)
        print("\n[TEST 6] Impacto financiero en balance (Descuento, 3:2, 1:1, Empate y Jackpot)...")
        uid_fin = "200000000000000002"
        eco.ensure_user(uid_fin, default_cash=1000)

        # 6.1 Descuento inicial
        eco.modify_balance(uid_fin, cash_delta=-100)
        assert eco.get_balance(uid_fin)["cash"] == 900, "El cash tras descontar 100 debe ser 900"

        # 6.2 Blackjack Natural (Pago 3:2: profit 1.5x -> total return 2.5x)
        win_net_bj = int(100 * 1.5)  # 150
        payout_bj = 100 + win_net_bj  # 250
        eco.modify_balance(uid_fin, cash_delta=payout_bj)
        assert eco.get_balance(uid_fin)["cash"] == 1150, f"Cash tras BJ 3:2 debe ser 1150, obtenido {eco.get_balance(uid_fin)['cash']}"

        # 6.3 Victoria Regular (Pago 1:1: profit 1.0x -> total return 2.0x)
        eco.modify_balance(uid_fin, cash_delta=-200)  # 1150 - 200 = 950
        win_net_reg = 200
        payout_reg = 200 + win_net_reg  # 400
        eco.modify_balance(uid_fin, cash_delta=payout_reg)
        assert eco.get_balance(uid_fin)["cash"] == 1350, f"Cash tras ganar 1:1 debe ser 1350, obtenido {eco.get_balance(uid_fin)['cash']}"

        # 6.4 Empate (Push: devolución íntegra del 100%)
        eco.modify_balance(uid_fin, cash_delta=-300)  # 1350 - 300 = 1050
        eco.modify_balance(uid_fin, cash_delta=300)  # Devolución 300
        assert eco.get_balance(uid_fin)["cash"] == 1350, f"Cash tras empate debe mantenerse en 1350, obtenido {eco.get_balance(uid_fin)['cash']}"

        # 6.5 Pérdida y alimentación del 3% al bote acumulado
        jackpot_before = eco.get_server_jackpot()
        lost_bet = 500
        eco.modify_balance(uid_fin, cash_delta=-lost_bet)  # 1350 - 500 = 850
        jackpot_feed = max(1, int(lost_bet * JACKPOT_FEED_PERCENT))  # 15 Porros
        eco.modify_server_jackpot(jackpot_feed)
        assert eco.get_server_jackpot() == jackpot_before + 15, f"Bote debe incrementarse en 15, obtenido {eco.get_server_jackpot()}"
        assert eco.get_balance(uid_fin)["cash"] == 850
        print("  ✅ TEST 6 PASADO: Cálculos financieros (descuento, pagos 3:2, 1:1, push y jackpot) verificados.")

        # TEST 7: Mecánica de Doblar (Double Down)
        print("\n[TEST 7] Mecánica de Doblar (Double Down)...")
        uid_dd = "200000000000000003"
        eco.ensure_user(uid_dd, default_cash=1000)

        # Inicializar view simulada
        mock_user = MagicMock()
        mock_user.id = int(uid_dd)
        mock_user.display_name = "Jugador Doblar"

        # Apuesta inicial 200 descontada
        eco.modify_balance(uid_dd, cash_delta=-200)  # Cash = 800

        player_hand_dd = BlackjackHand([("♠️", "5"), ("♥️", "6")])  # 11 inicial
        dealer_hand_dd = BlackjackHand([("♦️", "10"), ("♣️", "7")])  # Crupier 17
        mock_eng_dd = BlackjackEngine()
        mock_eng_dd.draw = MagicMock(return_value=("♠️", "10"))  # Recibe 10 -> 21

        view_dd = BlackjackView(
            user_id=int(uid_dd),
            user=mock_user,
            bet=200,
            engine=mock_eng_dd,
            player_hand=player_hand_dd,
            dealer_hand=dealer_hand_dd,
        )

        # Chequear que el botón Doblar no está deshabilitado inicialmente
        for item in view_dd.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "bj:double":
                assert item.disabled is False, "Botón Doblar debe estar activo con 2 cartas y fondos suficientes"

        # Simular click en Doblar
        mock_interaction = AsyncMock()
        mock_interaction.user.id = int(uid_dd)
        mock_interaction.response.is_done = MagicMock(return_value=False)

        asyncio.run(view_dd.do_double(mock_interaction))

        # Debe haber descontado otros 200 de cash (saldo final tras duplicar y ganar: 800 - 200 + 800 = 1400)
        # Apuesta duplicada = 400. Pago 1:1 = 800.
        assert view_dd.bet == 400, f"La apuesta debe ser 400 tras doblar, tiene {view_dd.bet}"
        assert len(player_hand_dd.cards) == 3, f"Debe tener exactamente 3 cartas tras doblar, tiene {len(player_hand_dd.cards)}"
        assert player_hand_dd.value == 21
        assert view_dd.resolved is True
        assert eco.get_balance(uid_dd)["cash"] == 1400, f"Cash esperado 1400, obtenido {eco.get_balance(uid_dd)['cash']}"
        print("  ✅ TEST 7 PASADO: Mecánica de Doblar (Double Down) verificada.")

        # TEST 8: Control de concurrencia y bloqueo de partidas solapadas
        print("\n[TEST 8] Control de concurrencia y bloqueo de partidas simultáneas...")
        uid_conc = 300000000000000001
        eco.ensure_user(uid_conc, default_cash=1000)

        assert uid_conc not in eco.ACTIVE_BLACKJACK_GAMES
        # Registrar partida activa
        eco.ACTIVE_BLACKJACK_GAMES[uid_conc] = True

        # Intentar ejecutar nueva partida mientras hay una activa
        mock_inter_conc = AsyncMock()
        mock_inter_conc.user.id = uid_conc
        mock_inter_conc.user.display_name = "Concurrente"

        from modulos.comandos import _handle_blackjack_command
        asyncio.run(_handle_blackjack_command(mock_inter_conc, "100"))

        # Debe rechazar con mensaje efímero y no descontar saldo
        mock_inter_conc.response.send_message.assert_called_once()
        args, kwargs = mock_inter_conc.response.send_message.call_args
        assert "Ya tienes una partida de Blackjack activa en curso" in args[0]
        assert kwargs.get("ephemeral") is True
        assert eco.get_balance(uid_conc)["cash"] == 1000, "No debe descontar saldo si la partida fue bloqueada"

        # Al liberarse, permite volver a jugar
        eco.ACTIVE_BLACKJACK_GAMES.pop(uid_conc, None)
        assert uid_conc not in eco.ACTIVE_BLACKJACK_GAMES
        print("  ✅ TEST 8 PASADO: Bloqueo atómico de partidas simultáneas (ACTIVE_BLACKJACK_GAMES) verificado.")

        # TEST 9: Control de interacción y permisos en BlackjackView
        print("\n[TEST 9] Control de interacción (Bloqueo de clics de terceros)...")
        owner_id = 400000000000000001
        intruder_id = 999999999999999999

        mock_owner = MagicMock()
        mock_owner.id = owner_id
        mock_owner.display_name = "Mesa Owner"

        view_perms = BlackjackView(
            user_id=owner_id,
            user=mock_owner,
            bet=100,
        )

        # Dueño de la partida
        inter_owner = AsyncMock()
        inter_owner.user.id = owner_id
        allowed = asyncio.run(view_perms.interaction_check(inter_owner))
        assert allowed is True, "El dueño debe poder interactuar"

        # Intruso / tercero
        inter_intruder = AsyncMock()
        inter_intruder.user.id = intruder_id
        rejected = asyncio.run(view_perms.interaction_check(inter_intruder))
        assert rejected is False, "Terceros deben ser bloqueados"
        inter_intruder.response.send_message.assert_called_once()
        args_i, kwargs_i = inter_intruder.response.send_message.call_args
        assert "Esta partida de Blackjack no es tuya" in args_i[0]
        assert kwargs_i.get("ephemeral") is True
        print("  ✅ TEST 9 PASADO: Bloqueo efímero a terceros en BlackjackView verificado.")

        # TEST 10: Auto-stand en caso de Timeout (60 segundos)
        print("\n[TEST 10] Resolución por Timeout (Auto-stand a los 60s)...")
        uid_to = 500000000000000001
        eco.ensure_user(uid_to, default_cash=1000)
        eco.modify_balance(uid_to, cash_delta=-100)  # Cash = 900

        mock_to_user = MagicMock()
        mock_to_user.id = uid_to
        mock_to_user.display_name = "Jugador Ausente"

        # Jugador tiene 19, crupier tiene 18
        p_hand_to = BlackjackHand([("♠️", "10"), ("♥️", "9")])
        d_hand_to = BlackjackHand([("♦️", "10"), ("♣️", "8")])
        eng_to = BlackjackEngine()
        eng_to.draw = MagicMock(return_value=("♦️", "2"))

        view_to = BlackjackView(
            user_id=uid_to,
            user=mock_to_user,
            bet=100,
            engine=eng_to,
            player_hand=p_hand_to,
            dealer_hand=d_hand_to,
        )
        view_to.message = AsyncMock()
        eco.ACTIVE_BLACKJACK_GAMES[uid_to] = view_to

        # Disparar timeout
        asyncio.run(view_to.on_timeout())

        assert view_to.resolved is True
        assert uid_to not in eco.ACTIVE_BLACKJACK_GAMES, "Debe ser removido de partidas activas tras timeout"
        # 19 supera a 18 -> victoria 1:1 (+200) -> 900 + 200 = 1100
        assert eco.get_balance(uid_to)["cash"] == 1100
        view_to.message.edit.assert_called_once()
        _, edit_kw = view_to.message.edit.call_args
        embed_sent = edit_kw.get("embed")
        assert "Auto-Stand" in embed_sent.description
        print("  ✅ TEST 10 PASADO: Auto-stand y resolución segura por timeout verificados.")

        # TEST 11: Registro de comandos slash /blackjack y /bj
        print("\n[TEST 11] Registro de comandos slash /blackjack y /bj en el Runner Dual...")
        assert cmd_blackjack in ECONOMY_SLASH_COMMANDS, "cmd_blackjack debe estar en ECONOMY_SLASH_COMMANDS"
        assert cmd_bj in ECONOMY_SLASH_COMMANDS, "cmd_bj debe estar en ECONOMY_SLASH_COMMANDS"
        assert cmd_blackjack in ALL_SLASH_COMMANDS, "cmd_blackjack debe estar en ALL_SLASH_COMMANDS"
        assert cmd_bj in ALL_SLASH_COMMANDS, "cmd_bj debe estar en ALL_SLASH_COMMANDS"

        assert cmd_blackjack.name == "blackjack"
        assert cmd_bj.name == "bj"
        assert len(ECONOMY_SLASH_COMMANDS) == 20, f"Debe haber 20 comandos de economía, hay {len(ECONOMY_SLASH_COMMANDS)}"
        assert len(ALL_SLASH_COMMANDS) == 43, f"Debe haber 43 comandos en total, hay {len(ALL_SLASH_COMMANDS)}"
        print("  ✅ TEST 11 PASADO: Presencia e integridad de /blackjack y /bj en ECONOMY_SLASH_COMMANDS.")

        print("\n" + "=" * 70)
        print("🎉 TODOS LOS TESTS DE BLACKJACK 21 NATIVO PASARON SATISFACTORIAMENTE (11/11)")
        print("=" * 70)

    finally:
        # Restaurar entorno
        eco.ECONOMY_DATA_PATH = original_path
        eco._ECONOMY_CACHE = None
        eco.ACTIVE_BLACKJACK_GAMES.clear()
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
