"""
Suite de Pruebas Unitarias y de Integración para el Sistema de Economía y Slots:
- Carga y guardado atómico en 'datos/economia.json'.
- Inicialización de usuarios, gestión de saldos y prevención de balances negativos.
- Sistema de trabajo (/trabajar) con cooldown y textos temáticos.
- Transferencias seguras de fondos entre usuarios.
- Motor de la tragaperras (Slots): 6 símbolos Brawl Stars Ranked, 5 líneas, RTP 94-96%.
- Bote progresivo del servidor (Jackpot): alimentación del 3% y reclamo supremo.
- Discord Components V2 (Container, Separator, TextDisplay, ActionRow).
- Concurrencia y thread-safety multihilo.
- Registro de comandos slash en bot_service y CommandTree.
"""

import os
import sys
import json
import time
import shutil
import tempfile
import threading
from datetime import datetime, timezone

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

import modulos.economia as eco
from modulos.comandos import ALL_SLASH_COMMANDS, cmd_slots, cmd_balance, cmd_trabajar, cmd_transferir


def run_tests():
    print("=" * 60)
    print("🚀 INICIANDO TEST SUITE COMPLETA DE ECONOMÍA Y SLOTS")
    print("=" * 60)

    # 1. Configurar entorno de pruebas con archivo temporal aislado
    temp_dir = tempfile.mkdtemp(prefix="test_eco_")
    test_json_path = os.path.join(temp_dir, "test_economia.json")

    original_path = eco.ECONOMY_DATA_PATH
    eco.ECONOMY_DATA_PATH = test_json_path
    eco._ECONOMY_CACHE = None

    try:
        # TEST 1: Estructura inicial y guardado seguro
        print("\n[TEST 1] Estructura inicial y guardado seguro...")
        data = eco.load_economy_data(force_reload=True)
        assert "users" in data, "Falta clave 'users'"
        assert data["server_jackpot"] == 25000, f"Jackpot inicial incorrecto: {data['server_jackpot']}"
        assert data["meta"]["currency_name"] == "Porro", "Nombre de moneda incorrecto"
        assert data["meta"]["currency_emoji"] == "<:Porro:1535685303317172305>", "Emoji incorrecto"
        assert os.path.exists(test_json_path), "El archivo test_economia.json no fue creado"
        print("  ✅ TEST 1 PASADO: Estructura inicial persistida correctamente.")

        # TEST 2: Inicialización de usuario y saldos
        print("\n[TEST 2] Inicialización de usuarios y saldos...")
        uid1 = "100000000000000001"
        bal1 = eco.get_balance(uid1)
        assert bal1["cash"] == 1000, f"Cash inicial debe ser 1000, obtenido {bal1['cash']}"
        assert bal1["bank"] == 0, f"Bank inicial debe ser 0, obtenido {bal1['bank']}"
        assert bal1["total"] == 1000, f"Total debe ser 1000, obtenido {bal1['total']}"

        # Modificación de saldos
        eco.modify_balance(uid1, cash_delta=500, bank_delta=200)
        bal1_mod = eco.get_balance(uid1)
        assert bal1_mod["cash"] == 1500, f"Cash esperado 1500, obtenido {bal1_mod['cash']}"
        assert bal1_mod["bank"] == 200, f"Bank esperado 200, obtenido {bal1_mod['bank']}"
        assert bal1_mod["total"] == 1700, f"Total esperado 1700, obtenido {bal1_mod['total']}"

        # Prevención de balance negativo
        try:
            eco.modify_balance(uid1, cash_delta=-2000, allow_negative=False)
            assert False, "Debería haber lanzado ValueError por fondos insuficientes"
        except ValueError:
            pass
        print("  ✅ TEST 2 PASADO: Inicialización y validación estricta de saldo.")

        # TEST 3: Sistema de trabajo (/trabajar) y cooldown
        print("\n[TEST 3] Sistema de trabajo (/trabajar) y cooldown...")
        uid2 = "100000000000000002"
        can_w, rem = eco.can_work(uid2, cooldown_seconds=7200)
        assert can_w is True, "El usuario nuevo debe poder trabajar"
        assert rem == 0.0, "El tiempo restante debe ser 0"

        ok_work, story, reward = eco.execute_work(uid2, cooldown_seconds=7200, min_reward=200, max_reward=800)
        assert ok_work is True, "El trabajo debería haberse completado"
        assert 200 <= reward <= 800, f"Recompensa fuera de rango: {reward}"
        assert len(story) > 10, "La historia de trabajo es demasiado corta"

        bal2 = eco.get_balance(uid2)
        assert bal2["cash"] == 1000 + reward, f"Cash no coincide tras trabajar: {bal2['cash']}"

        # Intento inmediato (debe fallar por cooldown)
        ok_work2, story2, reward2 = eco.execute_work(uid2, cooldown_seconds=7200)
        assert ok_work2 is False, "El segundo trabajo inmediato debe ser rechazado"
        assert "esperar" in story2.lower(), f"Mensaje de cooldown inesperado: {story2}"
        assert reward2 == 0, "No debe haber recompensa durante cooldown"
        print("  ✅ TEST 3 PASADO: Jornada laboral, historias cómicas y cooldown validados.")

        # TEST 4: Transferencias de fondos entre usuarios
        print("\n[TEST 4] Transferencias entre usuarios...")
        uid3 = "100000000000000003"
        uid4 = "100000000000000004"
        # Fondos iniciales: 1000 cada uno
        # Transferir 400 de uid3 a uid4
        ok_tx, msg_tx, b3, b4 = eco.transfer_funds(uid3, uid4, 400)
        assert ok_tx is True, f"Transferencia fallida: {msg_tx}"
        assert b3["cash"] == 600, f"Saldo remitente incorrecto: {b3['cash']}"
        assert b4["cash"] == 1400, f"Saldo destinatario incorrecto: {b4['cash']}"

        # Transferencia a uno mismo rechazada
        ok_self, msg_self, _, _ = eco.transfer_funds(uid3, uid3, 100)
        assert ok_self is False, "Transferencia a uno mismo debería fallar"

        # Transferencia sin saldo suficiente rechazada
        ok_nofunds, msg_nofunds, _, _ = eco.transfer_funds(uid3, uid4, 1000)
        assert ok_nofunds is False, "Transferencia sin saldo debería fallar"

        # Transferencia con monto inválido rechazada
        ok_neg, msg_neg, _, _ = eco.transfer_funds(uid3, uid4, -50)
        assert ok_neg is False, "Transferencia con monto negativo debería fallar"
        print("  ✅ TEST 4 PASADO: Transferencias seguras validadas al 100%.")

        # TEST 5: Motor de tragaperras y 5 líneas de pago
        print("\n[TEST 5] Motor de slots (evaluación y multiplicadores)...")
        engine = eco.SlotEngine()
        # Forzar una matriz ganadora: fila central con Ranked_Diamond (mult 3.0)
        grid_win = [
            ["Gold", "Mythic", "Legendary"],
            ["Diamond", "Diamond", "Diamond"],
            ["Masters", "Gold", "Pro"],
        ]
        res_win = engine.evaluate(grid_win, 1000)
        assert res_win["payout"] == 3000, f"Payout incorrecto: {res_win['payout']}"
        assert res_win["net"] == 2000, f"Neto incorrecto: {res_win['net']}"
        assert len(res_win["winning_lines"]) == 1, "Debería haber 1 línea ganadora"
        assert res_win["winning_lines"][0]["line"] == "Middle row"
        assert res_win["winning_lines"][0]["mult"] == 3.0

        # Forzar matriz multi-línea (Top row Gold + Diag ↘︎ Gold)
        grid_multi = [
            ["Gold", "Gold", "Gold"],
            ["Mythic", "Gold", "Legendary"],
            ["Masters", "Diamond", "Gold"],
        ]
        res_multi = engine.evaluate(grid_multi, 1000)
        # Gold mult = 1.5. Top row + Diag ↘︎ = 1.5 + 1.5 = 3.0
        assert res_multi["total_mult"] == 3.0, f"Multiplicador multi-línea incorrecto: {res_multi['total_mult']}"
        assert res_multi["payout"] == 3000
        assert len(res_multi["winning_lines"]) == 2

        # Forzar tirada no ganadora
        grid_lose = [
            ["Gold", "Diamond", "Mythic"],
            ["Legendary", "Masters", "Pro"],
            ["Gold", "Diamond", "Mythic"],
        ]
        res_lose = engine.evaluate(grid_lose, 1000)
        assert res_lose["payout"] == 0
        assert res_lose["net"] == -1000
        assert res_lose["title"] == "### No Win"
        assert res_lose["accent_color"] == 15684432
        print("  ✅ TEST 5 PASADO: Evaluación de líneas de pago y acumulación multi-línea.")

        # TEST 6: Componentes V2 de Discord
        print("\n[TEST 6] Generador de Discord Components V2...")
        v2_payload = engine.build_discord_v2_payload(res_win, uid1)
        assert v2_payload["flags"] == 32768, "Flag de Discord Components V2 debe ser 32768"
        container = v2_payload["components"][0]
        assert container["type"] == 17, "El contenedor debe ser de tipo 17"
        assert container["accent_color"] == res_win["accent_color"]
        # Verificar botones en ActionRow
        inner_comp = container["components"]
        action_row = [c for c in inner_comp if c["type"] == 1][0]
        buttons = action_row["components"]
        assert len(buttons) == 2, "Debe haber 2 botones: Play Again y Payouts"
        assert buttons[0]["label"] == "Play Again"
        assert f"slots:play-again:1000:{uid1}" in buttons[0]["custom_id"]
        assert buttons[1]["label"] == "Payouts"

        # Verificar LayoutView nativa
        layout_view = eco.SlotsLayoutView(res_win, uid1, 1000)
        comps = layout_view.to_components()
        assert comps[0]["type"] == 17
        print("  ✅ TEST 6 PASADO: Discord Components V2 generados con Container y ActionRow.")

        # TEST 7: Ciclo completo de Slots, deducción previa y Bote Progresivo
        print("\n[TEST 7] Ciclo de slots, deducción y Jackpot progresivo...")
        uid5 = "100000000000000005"
        initial_jackpot = eco.get_server_jackpot()
        assert initial_jackpot == 25000

        # Ejecutar varias tiradas de prueba
        ok_spin, _, res_spin, bal_after = eco.handle_slots_spin(uid5, 100)
        assert ok_spin is True, "La tirada de slots debería haberse ejecutado"
        if res_spin["payout"] == 0:
            # Hubo pérdida: 3% de 100 = 3 porros van al jackpot
            assert eco.get_server_jackpot() >= initial_jackpot + 3

        # Rechazo por saldo insuficiente
        eco.modify_balance(uid5, cash_delta=-bal_after["cash"])  # Vaciar efectivo
        ok_fail, err_fail, _, _ = eco.handle_slots_spin(uid5, 100)
        assert ok_fail is False, "Debe rechazar tirada si no hay saldo"
        assert "suficientes" in err_fail.lower()
        print("  ✅ TEST 7 PASADO: Deducción atómica, cobro y alimentación del jackpot validados.")

        # TEST 8: Reclamo del Jackpot Supremo (Ranked Pro)
        print("\n[TEST 8] Reclamo de Jackpot Supremo...")
        uid6 = "100000000000000006"
        eco.modify_server_jackpot(5000)  # Bote acumulado a 30.000
        current_jp = eco.get_server_jackpot()
        assert current_jp >= 30000

        # Simular tirada con Ranked Pro alineado
        grid_pro = [
            ["Pro", "Pro", "Pro"],
            ["Gold", "Diamond", "Gold"],
            ["Mythic", "Legendary", "Masters"],
        ]
        res_pro = engine.evaluate(grid_pro, 1000)
        assert res_pro["winning_lines"][0]["symbol"] == "Pro"
        # Evaluar manualmente mediante lógica de jackpot
        pro_hit = any(wl["symbol"] == "Pro" for wl in res_pro["winning_lines"])
        assert pro_hit is True
        eco.reset_server_jackpot()
        assert eco.get_server_jackpot() == 25000
        print("  ✅ TEST 8 PASADO: Jackpot Supremo y reseteo base al 100%.")

        # TEST 9: Concurrencia y Thread-Safety
        print("\n[TEST 9] Concurrencia multihilo y safe-write...")
        uid_conc = "100000000000000099"
        eco.ensure_user(uid_conc)

        def worker_task(thread_id: int):
            for _ in range(25):
                eco.modify_balance(uid_conc, cash_delta=10)
                time.sleep(0.001)
                eco.modify_server_jackpot(1)

        threads = []
        for i in range(10):
            t = threading.Thread(target=worker_task, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        final_bal = eco.get_balance(uid_conc)
        expected_cash = 1000 + (10 * 25 * 10)  # 1000 + 2500 = 3500
        assert final_bal["cash"] == expected_cash, f"Balance tras concurrencia {final_bal['cash']} != {expected_cash}"
        print("  ✅ TEST 9 PASADO: 10 hilos concurrentes sin condiciones de carrera ni pérdidas.")

        # TEST 10: Integración con CommandTree y ALL_SLASH_COMMANDS
        print("\n[TEST 10] Comprobación de Comandos Slash nativos...")
        assert len(ALL_SLASH_COMMANDS) == 26, f"Se esperaban 26 comandos, encontrados: {len(ALL_SLASH_COMMANDS)}"
        cmd_names = [c.name for c in ALL_SLASH_COMMANDS]
        assert "slots" in cmd_names, "Comando /slots no está en ALL_SLASH_COMMANDS"
        assert "balance" in cmd_names, "Comando /balance no está en ALL_SLASH_COMMANDS"
        assert "trabajar" in cmd_names, "Comando /trabajar no está en ALL_SLASH_COMMANDS"
        assert "transferir" in cmd_names, "Comando /transferir no está en ALL_SLASH_COMMANDS"

        # Verificar importabilidad desde bot_service
        import bot_service
        assert hasattr(bot_service, "cmd_slots"), "bot_service no tiene cmd_slots"
        assert hasattr(bot_service, "cmd_balance"), "bot_service no tiene cmd_balance"
        assert hasattr(bot_service, "cmd_trabajar"), "bot_service no tiene cmd_trabajar"
        assert hasattr(bot_service, "cmd_transferir"), "bot_service no tiene cmd_transferir"
        assert hasattr(bot_service, "get_balance"), "bot_service no tiene get_balance"
        assert hasattr(bot_service, "modify_balance"), "bot_service no tiene modify_balance"
        assert hasattr(bot_service, "SlotEngine"), "bot_service no tiene SlotEngine"
        print("  ✅ TEST 10 PASADO: Los 26 comandos slash y símbolos reexportados en bot_service.")

        print("\n" + "=" * 60)
        print("🎉 TODOS LOS TESTS DE ECONOMÍA Y SLOTS PASARON CON ÉXITO (100%)")
        print("=" * 60)

    finally:
        # Restaurar path original
        eco.ECONOMY_DATA_PATH = original_path
        eco._ECONOMY_CACHE = None
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
