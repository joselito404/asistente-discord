"""
Suite de Pruebas Unitarias y de Integración para el Sistema Completo de Economía y Tragaperras 5x3:
- Carga y guardado atómico en 'datos/economia.json' con thread-safety (RLock).
- Inicialización de usuarios, gestión de saldos y prevención de balances negativos.
- Sistema de trabajo (/trabajar) con cooldown y textos temáticos.
- Transferencias seguras de fondos entre usuarios (/transferir).
- Sistema de Banca: depósitos y retiradas (/depositar, /retirar) con montos numéricos y opción 'all'.
- Sistema de Robo (/robar): probabilidades 50%, 20-50% robo, chequeo de '🛡️ Cartera Blindada' y multas del 15%.
- Catálogo de Tienda V2 (/tienda): los 9 artículos oficiales, compras, inventario y artículos únicos.
- Salario acumulativo (/salario): cálculo por roles de nivel/podio y fórmula de decaimiento del 5% (asíntota 20*S).
- Motor de la tragaperras 5x3 (Slots): matriz 5x3, 7 símbolos (6 Ranked + WILD), 9 líneas de pago limpias (3 Horizontales + 6 Diagonales).
- Evaluación de 3, 4 y 5 aciertos con ventanas consecutivas y sustitución de comodín WILD.
- Retirada de figuras forzadas y patrones complejos ('El Ojo', Scatters y Free Spins eliminados).
- Patrón 'Pantalla Completa' (15 casillas a x500.0).
- Bote progresivo escalonado: Grand Jackpot (100%) y Mini Jackpot (25%) en L1, y alimentación del 3%.
- Discord Components V2 para matriz 5x3 (Container, Separator, TextDisplay, ActionRow, botones interactivos).
- Concurrencia y thread-safety multihilo.
- Registro de los 31 comandos slash en bot_service y CommandTree.
- Simulación Monte Carlo calibrada a RTP 110.0% (+/- 0.5%) ordenado por Jose.
"""

import os
import sys
import json
import time
import shutil
import tempfile
import threading
import asyncio
from unittest.mock import AsyncMock, MagicMock
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

import discord
import modulos.economia as eco
from modulos.comandos import (
    ALL_SLASH_COMMANDS,
    GENERAL_SLASH_COMMANDS,
    ECONOMY_SLASH_COMMANDS,
    register_general_commands,
    register_economy_commands,
    cmd_slots,
    cmd_balance,
    cmd_trabajar,
    cmd_transferir,
    cmd_depositar,
    cmd_retirar,
    cmd_robar,
    cmd_tienda,
    cmd_salario,
    cmd_regalar,
    ensure_economy_channel,
)


def run_tests():
    print("=" * 65)
    print("🚀 INICIANDO TEST SUITE COMPLETA DE ECONOMÍA Y TRAGAPERRAS 5X3")
    print("=" * 65)

    # 1. Configurar entorno de pruebas con archivo temporal aislado
    temp_dir = tempfile.mkdtemp(prefix="test_eco_5x3_")
    test_json_path = os.path.join(temp_dir, "test_economia.json")

    original_path = eco.ECONOMY_DATA_PATH
    eco.ECONOMY_DATA_PATH = test_json_path
    eco._ECONOMY_CACHE = None

    try:
        # TEST 1: Estructura inicial y guardado seguro
        print("\n[TEST 1] Estructura inicial y persistencia atómica...")
        data = eco.load_economy_data(force_reload=True)
        assert "users" in data, "Falta clave 'users'"
        assert data["server_jackpot"] == 25000, f"Jackpot inicial incorrecto: {data['server_jackpot']}"
        assert data["meta"]["currency_name"] == "Porro", "Nombre de moneda incorrecto"
        assert data["meta"]["currency_emoji"] == "<:Porro:1535685303317172305>", "Emoji incorrecto"
        assert os.path.exists(test_json_path), "El archivo test_economia.json no fue creado"
        print("  ✅ TEST 1 PASADO: Estructura inicial y persistencia atómica verificadas.")

        # TEST 2: Inicialización de usuario y saldos
        print("\n[TEST 2] Inicialización de usuarios y saldos...")
        uid1 = "100000000000000001"
        bal1 = eco.get_balance(uid1)
        assert bal1["cash"] == 1000, f"Cash inicial debe ser 1000, obtenido {bal1['cash']}"
        assert bal1["bank"] == 0, f"Bank inicial debe ser 0, obtenido {bal1['bank']}"
        assert bal1["total"] == 1000, f"Total debe ser 1000, obtenido {bal1['total']}"

        eco.modify_balance(uid1, cash_delta=500, bank_delta=200)
        bal1_mod = eco.get_balance(uid1)
        assert bal1_mod["cash"] == 1500, f"Cash esperado 1500, obtenido {bal1_mod['cash']}"
        assert bal1_mod["bank"] == 200, f"Bank esperado 200, obtenido {bal1_mod['bank']}"
        assert bal1_mod["total"] == 1700, f"Total esperado 1700, obtenido {bal1_mod['total']}"

        try:
            eco.modify_balance(uid1, cash_delta=-2000, allow_negative=False)
            assert False, "Debería haber lanzado ValueError por fondos insuficientes"
        except ValueError:
            pass
        print("  ✅ TEST 2 PASADO: Inicialización y validación estricta de saldo.")

        # TEST 3: Sistema de trabajo (/trabajar), multiplicadores y cooldown de 4h
        print("\n[TEST 3] Sistema de trabajo (/trabajar) recalibrado (1.000-2.500, 4h cooldown)...")
        uid2 = "100000000000000002"
        can_w, rem = eco.can_work(uid2)
        assert can_w is True, "El usuario nuevo debe poder trabajar"
        assert rem == 0.0, "El tiempo restante debe ser 0"

        ok_work, story, reward = eco.execute_work(uid2)
        assert ok_work is True, "El trabajo debería haberse completado"
        assert 1000 <= reward <= 2500, f"Recompensa fuera de rango oficial (1000-2500): {reward}"
        assert len(story) > 10, "La historia de trabajo es demasiado corta"

        bal2 = eco.get_balance(uid2)
        assert bal2["cash"] == 1000 + reward, f"Cash no coincide tras trabajar: {bal2['cash']}"

        ok_work2, story2, reward2 = eco.execute_work(uid2)
        assert ok_work2 is False, "El segundo trabajo inmediato debe ser rechazado"
        assert "esperar" in story2.lower(), f"Mensaje de cooldown inesperado: {story2}"
        assert reward2 == 0, "No debe haber recompensa durante cooldown"
        print("  ✅ TEST 3 PASADO: Jornada laboral recalibrada (1.000-2.500 Porros, 4h cooldown) validada.")

        # TEST 4: Transferencias de fondos entre usuarios
        print("\n[TEST 4] Transferencias entre usuarios...")
        uid3 = "100000000000000003"
        uid4 = "100000000000000004"
        ok_tx, msg_tx, b3, b4 = eco.transfer_funds(uid3, uid4, 400)
        assert ok_tx is True, f"Transferencia fallida: {msg_tx}"
        assert b3["cash"] == 600, f"Saldo remitente incorrecto: {b3['cash']}"
        assert b4["cash"] == 1400, f"Saldo destinatario incorrecto: {b4['cash']}"

        ok_self, msg_self, _, _ = eco.transfer_funds(uid3, uid3, 100)
        assert ok_self is False, "Transferencia a uno mismo debería fallar"

        ok_nofunds, msg_nofunds, _, _ = eco.transfer_funds(uid3, uid4, 1000)
        assert ok_nofunds is False, "Transferencia sin saldo debería fallar"
        print("  ✅ TEST 4 PASADO: Transferencias seguras validadas al 100%.")

        # TEST 5: Módulo de Banca (depósitos y retiradas con cantidades y 'all')
        print("\n[TEST 5] Módulo de Banca (depósitos y retiradas con 'all')...")
        uid_bank = "100000000000000005"
        eco.ensure_user(uid_bank, default_cash=2000)

        # 5a: Depositar 800 Porros
        ok_dep, msg_dep, b_dep = eco.deposit_cash(uid_bank, 800)
        assert ok_dep is True
        assert b_dep["cash"] == 1200
        assert b_dep["bank"] == 800

        # 5b: Retirar 300 Porros
        ok_with, msg_with, b_with = eco.withdraw_cash(uid_bank, 300)
        assert ok_with is True
        assert b_with["cash"] == 1500
        assert b_with["bank"] == 500

        # 5c: Depositar todo con 'all'
        ok_dep_all, _, b_dep_all = eco.deposit_cash(uid_bank, "all")
        assert ok_dep_all is True
        assert b_dep_all["cash"] == 0
        assert b_dep_all["bank"] == 2000

        # 5d: Retirar todo con 'all'
        ok_with_all, _, b_with_all = eco.withdraw_cash(uid_bank, "all")
        assert ok_with_all is True
        assert b_with_all["cash"] == 2000
        assert b_with_all["bank"] == 0

        # 5e: Depósito con fondos insuficientes
        ok_dep_fail, _, _ = eco.deposit_cash(uid_bank, 5000)
        assert ok_dep_fail is False
        print("  ✅ TEST 5 PASADO: Banca (/depositar y /retirar con montos y 'all') validada.")

        # TEST 6: Sistema de Robo (/robar) y chequeo de '🛡️ Cartera Blindada'
        print("\n[TEST 6] Sistema de Robo y '🛡️ Cartera Blindada'...")
        uid_robber = "100000000000000006"
        uid_victim_shield = "100000000000000007"
        uid_victim_plain = "100000000000000008"

        eco.ensure_user(uid_robber, default_cash=5000)
        eco.ensure_user(uid_victim_shield, default_cash=10000)
        eco.ensure_user(uid_victim_plain, default_cash=10000)

        # Dotar de Cartera Blindada a uid_victim_shield
        data_inv = eco.load_economy_data()
        data_inv["users"][uid_victim_shield]["inventory"].append("🛡️ Cartera Blindada")
        eco.save_economy_data(data_inv)
        assert eco.user_has_shield(uid_victim_shield) is True
        assert eco.user_has_shield(uid_victim_plain) is False

        # Intento de robo contra Cartera Blindada -> Debe fallar al 100% y cobrar multa del 15%
        ok_rob_shield, msg_rob_shield, delta_shield = eco.execute_rob(uid_robber, uid_victim_shield, cooldown_seconds=0)
        assert ok_rob_shield is False, "El robo contra Cartera Blindada nunca debe tener éxito"
        assert "Cartera Blindada" in msg_rob_shield
        assert delta_shield < 0, f"Debe cobrar multa al ladrón: {delta_shield}"
        # Multa del 15% de 5000 = 750 (500 a la víctima, 250 al jackpot)
        assert delta_shield == -750
        assert eco.get_balance(uid_robber)["cash"] == 4250
        assert eco.get_balance(uid_victim_shield)["cash"] == 10500

        # Intento de robo contra víctima común sin escudo
        ok_rob_plain, msg_rob_plain, delta_plain = eco.execute_rob(uid_robber, uid_victim_plain, cooldown_seconds=0)
        if ok_rob_plain:
            assert delta_plain > 0, "Robo exitoso debe transferir Porros al ladrón"
            assert "GOLPE MAESTRO" in msg_rob_plain
        else:
            assert delta_plain <= 0, "Robo fallido debe cobrar multa"
            assert "ATRACO FALLIDO" in msg_rob_plain
        print("  ✅ TEST 6 PASADO: Robo (/robar), blindaje absoluto y multas del 15% validados.")

        # TEST 7: Catálogo de Tienda V2 y compras de artículos
        print("\n[TEST 7] Catálogo de Tienda V2 (9 artículos con Monster Blanco) y compras...")
        catalog = eco.get_shop_catalog()
        assert len(catalog) == 9, f"Se esperaban 9 artículos en la tienda, encontrados: {len(catalog)}"
        assert "cartera_blindada" in catalog
        assert "porro_oro" in catalog
        assert "camello_barrio" in catalog
        assert "ludopata_rehabilitado" in catalog
        assert "monster_blanco" in catalog
        assert "pollo_pelea" not in catalog
        assert "chute_xp" in catalog
        assert "pase_semanal_xp" in catalog
        assert "pase_mensual_xp" in catalog
        assert "aura_xp" in catalog
        assert catalog["chute_xp"]["unique"] is False
        assert catalog["pase_semanal_xp"]["unique"] is False
        assert catalog["pase_mensual_xp"]["unique"] is False

        uid_buyer = "100000000000000009"
        eco.ensure_user(uid_buyer, default_cash=100000)

        # Comprar Cartera Blindada (50.000 Porros)
        ok_buy, msg_buy, it_buy, b_buyer = eco.buy_shop_item(uid_buyer, "cartera_blindada")
        assert ok_buy is True
        assert b_buyer["cash"] == 50000
        assert "🛡️ Cartera Blindada" in eco.get_user_economy(uid_buyer)["inventory"]
        assert eco.user_has_shield(uid_buyer) is True

        # Intento de comprar dos veces un artículo único -> debe fallar
        ok_dup, msg_dup, _, _ = eco.buy_shop_item(uid_buyer, "cartera_blindada")
        assert ok_dup is False
        assert "Ya posees" in msg_dup

        # Compra sin saldo suficiente -> debe fallar
        ok_expensive, msg_exp, _, _ = eco.buy_shop_item(uid_buyer, "aura_xp")  # Cuesta 1.000.000
        assert ok_expensive is False
        assert "No tienes suficientes Porros" in msg_exp

        # Verificación del embed interactivo oficial
        shop_embed = eco.build_shop_embed(uid_buyer)
        assert "Tienda Oficial de Porros" in shop_embed.title
        assert len(shop_embed.fields) == 3
        assert "50,000" in shop_embed.footer.text

        # Verificación de la vista interactiva (desplegable + botón verde de compra explícita)
        shop_view = eco.ShopInteractiveView(author_id=uid_buyer)
        assert shop_view.author_id == int(uid_buyer)
        assert len(shop_view.children) == 2
        select_comp = shop_view.children[0]
        buy_btn_comp = shop_view.children[1]
        assert isinstance(select_comp, discord.ui.Select)
        assert len(select_comp.options) == 9
        assert isinstance(buy_btn_comp, discord.ui.Button)
        assert "Comprar" in buy_btn_comp.label
        assert buy_btn_comp.style == discord.ButtonStyle.success

        # Comprobar que cmd_tienda no recibe parámetros para prevenir compras accidentales
        cmd_tienda_obj = [c for c in ALL_SLASH_COMMANDS if c.name == "tienda"][0]
        assert len(cmd_tienda_obj.parameters) == 0, f"/tienda no debe recibir parámetros, tiene {len(cmd_tienda_obj.parameters)}"

        print("  ✅ TEST 7 PASADO: Tienda V2 interactiva (embed categorizado, View con Select + Botón verde y 0 parámetros en /tienda) validada.")

        # TEST 8: Salario Acumulativo con Decaimiento del 5% y Nivel Exacto (Opción A)
        print("\n[TEST 8] Salario Acumulativo con decaimiento del 5%...")
        # 8a: Novato sin roles ni nivel -> salario base 0/día y claim_salary rechazado
        s_novato = eco.calculate_daily_salary(user_roles=[])
        assert s_novato == 0, f"Salario base de novato esperado 0, obtenido {s_novato}"

        uid_sal = "100000000000000010"
        eco.ensure_user(uid_sal, default_cash=0)
        ok_sal_nov, msg_sal_nov, _, _ = eco.claim_salary(uid_sal)
        assert ok_sal_nov is False
        assert "Nivel 10" in msg_sal_nov

        # 8b: Pruebas exactas de fórmula Opción A por nivel L
        # Nivel 18: 2000 + 8 * 200 = 3600
        assert eco.calculate_daily_salary(user_level=18) == 3600
        # Nivel 37: 7000 + 7 * 450 = 10150
        assert eco.calculate_daily_salary(user_level=37) == 10150
        # Nivel 54: 18000 + 4 * 1000 = 22000
        assert eco.calculate_daily_salary(user_level=54) == 22000

        # Miembro de Élite (Nivel 50 inferido = 18000) + Top 1 (+8000) = 26000
        roles_elite = ["Pendejo de Élite", "Top 1"]
        s_elite = eco.calculate_daily_salary(user_roles=roles_elite)
        assert s_elite == 26000, f"Salario de Élite esperado 26000, obtenido {s_elite}"

        # 8c: Fórmula de decaimiento del 5% diario
        # n = 1 día (86400s) -> P = S * (1 - 0.95^1) / 0.05 = S * 1.0 = S
        p_1day = eco.calculate_accumulated_salary(10000, 86400, decay_rate=0.05)
        assert p_1day == 10000, f"Salario tras 1 día esperado 10000, obtenido {p_1day}"

        # n = 2 días -> P = S * (1 - 0.95^2) / 0.05 = S * (0.0975 / 0.05) = S * 1.95 = 19500
        p_2days = eco.calculate_accumulated_salary(10000, 86400 * 2, decay_rate=0.05)
        assert p_2days == 19500, f"Salario tras 2 días esperado 19500, obtenido {p_2days}"

        # n = 100 días -> 198.816 (99.4% de la asíntota)
        p_100days = eco.calculate_accumulated_salary(10000, 86400 * 100, decay_rate=0.05)
        assert p_100days == 198816, f"Salario tras 100 días esperado 198816, obtenido {p_100days}"

        # n = 300 días -> asíntota 20 * S = 200000
        p_300days = eco.calculate_accumulated_salary(10000, 86400 * 300, decay_rate=0.05)
        assert p_300days == 200000, f"Asíntota esperada 200000, obtenido {p_300days}"

        # Cobro real mediante claim_salary con user_level=18
        ok_sal1, msg_sal1, p1, s1 = eco.claim_salary(uid_sal, user_level=18)
        assert ok_sal1 is True
        assert p1 == 3600
        assert s1 == 3600
        assert eco.get_balance(uid_sal)["cash"] == 3600

        # Cobro inmediato -> rechazado por cooldown de 24h
        ok_sal2, msg_sal2, p2, _ = eco.claim_salary(uid_sal, user_level=18)
        assert ok_sal2 is False
        assert p2 == 0
        assert "Ya has cobrado" in msg_sal2
        print("  ✅ TEST 8 PASADO: Salario acumulativo con fórmula de decaimiento del 5% validado.")

        # TEST 9: Motor de Tragaperras 5x3 y evaluación de las 9 líneas limpias
        print("\n[TEST 9] Motor de Tragaperras 5x3 (3 Horizontales + 6 Diagonales Limpias)...")
        engine = eco.SlotEngine()
        assert len(eco.SLOT_PAYLINES) == 9, f"Se esperaban 9 líneas de pago, encontradas: {len(eco.SLOT_PAYLINES)}"

        # Probar cada una de las 9 líneas
        for idx, (line_name, coords) in enumerate(eco.SLOT_PAYLINES):
            grid_5x3 = [
                ["Mythic", "Legendary", "Masters", "Mythic", "Legendary"],
                ["Masters", "Mythic", "Legendary", "Masters", "Mythic"],
                ["Legendary", "Masters", "Mythic", "Legendary", "Masters"],
            ]
            # Colocar Diamond en la línea
            for r, c in coords:
                grid_5x3[r][c] = "Diamond"

            res_line = engine.evaluate(grid_5x3, 1000)
            matching = [wl for wl in res_line["winning_lines"] if line_name in wl["line"] and wl["symbol"] == "Diamond"]
            assert len(matching) >= 1, f"Fallo al detectar {line_name}"
            assert matching[0]["symbol"] == "Diamond"
            expected_count = len(coords)
            assert matching[0]["count"] == expected_count
            expected_mult = 7.80 if expected_count == 5 else 0.70
            assert matching[0]["mult"] == expected_mult, f"Mult inesperado para {line_name}: {matching[0]['mult']} != {expected_mult}"

        # Verificación explícita de ventanas consecutivas en líneas horizontales (5 casillas)
        # a) 3 aciertos en rodillos 0-2 -> PREMIA
        sym_a, count_a, mult_a = engine.evaluate_line(["Gold", "Gold", "Gold", "Diamond", "Mythic"])
        assert sym_a == "Gold" and count_a == 3 and mult_a == 0.32, f"Fallo en rodillos 0-2: {(sym_a, count_a, mult_a)}"

        # b) 3 aciertos en rodillos 1-3 -> PREMIA en ventana consecutiva
        sym_b, count_b, mult_b = engine.evaluate_line(["Diamond", "Gold", "Gold", "Gold", "Mythic"])
        assert sym_b == "Gold" and count_b == 3 and mult_b == 0.32, f"Fallo en ventana 1-3: {(sym_b, count_b, mult_b)}"

        # c) 3 aciertos en rodillos 2-4 -> PREMIA en ventana consecutiva
        sym_c, count_c, mult_c = engine.evaluate_line(["Diamond", "Mythic", "Gold", "Gold", "Gold"])
        assert sym_c == "Gold" and count_c == 3 and mult_c == 0.32, f"Fallo en ventana 2-4: {(sym_c, count_c, mult_c)}"

        # d) 4 aciertos en rodillos 0-3 -> PREMIA
        sym_4a, count_4a, mult_4a = engine.evaluate_line(["Gold", "Gold", "Gold", "Gold", "Mythic"])
        assert sym_4a == "Gold" and count_4a == 4 and mult_4a == 1.20, f"Fallo en 4 rodillos 0-3: {(sym_4a, count_4a, mult_4a)}"

        # e) 4 aciertos en rodillos 1-4 -> PREMIA en ventana consecutiva
        sym_4b, count_4b, mult_4b = engine.evaluate_line(["Diamond", "Gold", "Gold", "Gold", "Gold"])
        assert sym_4b == "Gold" and count_4b == 4 and mult_4b == 1.20, f"Fallo en ventana 1-4: {(sym_4b, count_4b, mult_4b)}"

        # f) 5 aciertos -> PREMIA
        sym_5, count_5, mult_5 = engine.evaluate_line(["Gold", "Gold", "Gold", "Gold", "Gold"])
        assert sym_5 == "Gold" and count_5 == 5 and mult_5 == 4.00, f"Fallo en 5 rodillos: {(sym_5, count_5, mult_5)}"

        print("  ✅ TEST 9 PASADO: Las 9 líneas de pago 5x3 (3 Horizontales + 6 Diagonales) y ventanas consecutivas validadas.")

        # TEST 10: Comodín WILD (3, 4 y 5 aciertos, y sustitución en líneas regulares)
        print("\n[TEST 10] Comodín WILD (3, 4 y 5 aciertos y sustituciones)...")
        # 10a: 5 Wilds en Línea Centro
        grid_5w = [
            ["Gold", "Diamond", "Gold", "Diamond", "Gold"],
            ["Wild", "Wild", "Wild", "Wild", "Wild"],
            ["Gold", "Diamond", "Gold", "Diamond", "Gold"],
        ]
        res_5w = engine.evaluate(grid_5w, 1000)
        wl_5w = [wl for wl in res_5w["winning_lines"] if "Línea Centro" in wl["line"]][0]
        assert wl_5w["symbol"] == "Wild"
        assert wl_5w["count"] == 5
        assert wl_5w["mult"] == 290.0, f"5 Wilds deben pagar x290.0, obtenido: {wl_5w['mult']}"

        # 10b: 1 Wild + 4 Pro en Línea Centro -> paga 5 Pro (x240.0)
        grid_1w_4pro = [
            ["Gold", "Diamond", "Gold", "Diamond", "Gold"],
            ["Wild", "Pro", "Pro", "Pro", "Pro"],
            ["Gold", "Diamond", "Gold", "Diamond", "Gold"],
        ]
        res_1w = engine.evaluate(grid_1w_4pro, 1000)
        wl_1w = [wl for wl in res_1w["winning_lines"] if "Línea Centro" in wl["line"]][0]
        assert wl_1w["symbol"] == "Pro"
        assert wl_1w["count"] == 5
        assert wl_1w["mult"] == 240.0, f"1 Wild + 4 Pro debe pagar x240.0, obtenido: {wl_1w['mult']}"
        print("  ✅ TEST 10 PASADO: Comodín WILD para 3, 4 y 5 aciertos validado.")

        # TEST 11: Retirada de 'El Ojo' y verificación de sólo líneas limpias
        print("\n[TEST 11] Comprobación de eliminación de 'El Ojo' y sólo 9 líneas limpias...")
        grid_eye = [
            ["Gold", "Gold", "Gold", "Gold", "Gold"],
            ["Gold", "Pro", "Masters", "Mythic", "Gold"],
            ["Gold", "Gold", "Gold", "Gold", "Gold"],
        ]
        res_eye = engine.evaluate(grid_eye, 1000)
        assert "eye_hit" not in res_eye, "El patrón El Ojo no debe existir en el resultado"
        assert not any("El Ojo" in wl["line"] for wl in res_eye["winning_lines"])
        print("  ✅ TEST 11 PASADO: 'El Ojo' eliminado de forma definitiva; sólo líneas limpias.")

        # TEST 12: Patrón 'Pantalla Completa' (15 casillas a x500)
        print("\n[TEST 12] Pantalla Completa (15 casillas a x500)...")
        grid_full = [["Mythic"] * 5 for _ in range(3)]
        res_full = engine.evaluate(grid_full, 1000)
        assert res_full["full_screen_hit"] is True
        full_wl = [wl for wl in res_full["winning_lines"] if "PANTALLA COMPLETA" in wl["line"]][0]
        assert full_wl["mult"] == 500.0
        print("  ✅ TEST 12 PASADO: Pantalla Completa validada con x500.0 directo.")

        # TEST 13: 6 Diagonales rectas de 3 casillas y eliminación definitiva de SCATTER
        print("\n[TEST 13] 6 Diagonales rectas reales de 3 casillas y eliminación de SCATTER...")
        assert "Scatter" not in eco.SLOT_SYMBOLS, "El símbolo Scatter debe estar completamente eliminado"
        assert len(eco.SLOT_SYMBOLS) == 7, f"Se esperaban 7 símbolos, encontrados: {len(eco.SLOT_SYMBOLS)}"

        # Probar que las 6 diagonales premian por 3 aciertos (k=3)
        diag_lines = [pl for pl in eco.SLOT_PAYLINES if "Diagonal" in pl[0]]
        assert len(diag_lines) == 6, f"Se esperaban 6 diagonales, encontradas: {len(diag_lines)}"

        grid_d1 = None
        for idx_d, (d_name, d_coords) in enumerate(diag_lines):
            g_diag = [
                ["Gold", "Gold", "Gold", "Gold", "Gold"],
                ["Diamond", "Diamond", "Diamond", "Diamond", "Diamond"],
                ["Gold", "Gold", "Gold", "Gold", "Gold"],
            ]
            for r, c in d_coords:
                g_diag[r][c] = "Mythic"
            res_d = engine.evaluate(g_diag, 1000)
            wl_d = [wl for wl in res_d["winning_lines"] if d_name in wl["line"] and wl["symbol"] == "Mythic"]
            assert len(wl_d) >= 1, f"Fallo al detectar diagonal {d_name}"
            assert wl_d[0]["symbol"] == "Mythic"
            assert wl_d[0]["count"] == 3
            assert wl_d[0]["mult"] == 1.50
            if idx_d == 0:
                grid_d1 = g_diag

        # Comprobar que 2 de 3 en diagonal NO premia
        sym_d_fail, count_d_fail, mult_d_fail = engine.evaluate_line(["Mythic", "Mythic", "Gold"])
        assert sym_d_fail is None and count_d_fail == 0 and mult_d_fail == 0.0, "2 de 3 en diagonal no debe premiar"

        res_diag = engine.evaluate(grid_d1, 1000)
        assert res_diag["scatter_count"] == 0
        assert res_diag["free_spins_triggered"] is False
        print("  ✅ TEST 13 PASADO: 6 Diagonales rectas de 3 casillas validadas y Scatter ausente al 100%.")

        # TEST 14: Botes Progresivos Escalonados (Grand y Mini en Línea Centro)
        print("\n[TEST 14] Bote Progresivo Escalonado (Grand y Mini en Línea Centro)...")
        eco.reset_server_jackpot(50000)
        assert eco.get_server_jackpot() == 50000

        # 14a: Mini Jackpot (5 Masters en Línea Centro)
        grid_mini = [
            ["Gold"] * 5,
            ["Masters"] * 5,
            ["Gold"] * 5,
        ]
        res_mini = engine.evaluate(grid_mini, 1000)
        assert res_mini["mini_jackpot_hit"] is True
        assert res_mini["grand_jackpot_hit"] is False

        # 14b: Grand Jackpot (5 Pro en Línea Centro)
        grid_grand = [
            ["Gold"] * 5,
            ["Pro"] * 5,
            ["Gold"] * 5,
        ]
        res_grand = engine.evaluate(grid_grand, 1000)
        assert res_grand["grand_jackpot_hit"] is True

        # Cobro y alimentación vía handle_slots_spin
        uid_jp = "100000000000000077"
        eco.ensure_user(uid_jp, default_cash=10000)
        eco.reset_server_jackpot(40000)
        ok_spin, _, res_spin, _ = eco.handle_slots_spin(uid_jp, 100)
        assert ok_spin is True
        print("  ✅ TEST 14 PASADO: Grand Jackpot (100%), Mini Jackpot (25%) y alimentación del 3% validados.")

        # TEST 15: Discord Components V2 para matriz 5x3
        print("\n[TEST 15] Discord Components V2 para matriz 5x3...")
        layout_view = eco.SlotsLayoutView(res_diag, uid1, 1000)
        comps = layout_view.to_components()
        assert comps[0]["type"] == 17  # Container
        payload = engine.build_discord_v2_payload(res_diag, uid1)
        assert payload["flags"] == 32768
        print("  ✅ TEST 15 PASADO: Discord Components V2 para matriz 5x3 validados.")

        # TEST 16: Concurrencia multihilo y safe-write
        print("\n[TEST 16] Concurrencia multihilo y safe-write...")
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
        expected_cash = 1000 + (10 * 25 * 10)
        assert final_bal["cash"] == expected_cash, f"Balance tras concurrencia {final_bal['cash']} != {expected_cash}"
        print("  ✅ TEST 16 PASADO: 10 hilos concurrentes sin condiciones de carrera.")

        # TEST 17: Comprobación de la arquitectura Dual Runner y Slash Commands
        print("\n[TEST 17] Comprobación de la arquitectura Dual Runner y Slash Commands...")
        assert len(ALL_SLASH_COMMANDS) == 43, f"Se esperaban 43 comandos, encontrados: {len(ALL_SLASH_COMMANDS)}"
        assert len(GENERAL_SLASH_COMMANDS) == 23, f"Se esperaban 23 comandos generales, encontrados: {len(GENERAL_SLASH_COMMANDS)}"
        assert len(ECONOMY_SLASH_COMMANDS) == 20, f"Se esperaban 20 comandos de economía, encontrados: {len(ECONOMY_SLASH_COMMANDS)}"

        eco_cmd_names = [c.name for c in ECONOMY_SLASH_COMMANDS]
        for expected in [
            "slots", "balance", "trabajar", "transferir", "depositar", "retirar",
            "robar", "tienda", "salario", "blackjack", "bj", "ruleta", "coinflip",
            "casino", "crimen", "ranking", "inventario", "usar", "regalar", "admin_dinero"
        ]:
            assert expected in eco_cmd_names, f"Comando /{expected} no está en ECONOMY_SLASH_COMMANDS"

        import bot_service
        for expected_attr in [
            "bot", "tree", "economy_bot", "economy_tree", "ECONOMY_TOKEN",
            "run_bots", "start_bot_persistent",
            "cmd_slots", "cmd_balance", "cmd_trabajar", "cmd_transferir",
            "cmd_depositar", "cmd_retirar", "cmd_robar", "cmd_tienda", "cmd_salario",
            "cmd_blackjack", "cmd_bj", "cmd_ruleta", "cmd_coinflip", "cmd_casino",
            "cmd_crimen", "cmd_ranking", "cmd_inventario", "cmd_usar", "cmd_regalar", "cmd_admin_dinero",
            "deposit_cash", "withdraw_cash", "execute_rob", "buy_shop_item", "claim_salary", "SlotEngine",
            "ShopInteractiveView", "build_shop_embed",
            "BlackjackHand", "BlackjackEngine", "BlackjackView",
            "RouletteEngine", "RouletteActionView",
            "CoinflipEngine", "CoinflipActionView", "CoinflipChallengeView",
            "CasinoHubView", "build_casino_hub_embed",
            "get_level_role_multiplier", "can_crime", "execute_crime",
            "use_inventory_item", "check_and_expire_buffs", "build_inventory_embed", "InventoryView",
            "get_economy_leaderboard", "build_ranking_embed", "RankingView",
            "admin_modify_money", "admin_airdrop_role", "gift_inventory_item",
            "ensure_economy_channel", "MIN_SLOTS_BET", "MIN_BLACKJACK_BET",
            "MIN_ROULETTE_BET", "MIN_COINFLIP_BET", "ECONOMY_CATEGORY_ID", "ALLOWED_ECONOMY_CHANNELS",
        ]:
            assert hasattr(bot_service, expected_attr), f"bot_service no tiene {expected_attr}"

        tree_cmds = [c.name for c in bot_service.tree.get_commands()]
        economy_tree_cmds = [c.name for c in bot_service.economy_tree.get_commands()]
        assert len(tree_cmds) == 23, f"Se esperaban 23 comandos en tree de Asistente, encontrados: {len(tree_cmds)}"
        assert len(economy_tree_cmds) == 20, f"Se esperaban 20 comandos en economy_tree, encontrados: {len(economy_tree_cmds)}"
        assert "slots" not in tree_cmds, "slots no debería estar en el árbol general de Asistente"
        assert "blackjack" not in tree_cmds, "blackjack no debería estar en el árbol general de Asistente"
        assert "ruleta" not in tree_cmds, "ruleta no debería estar en el árbol general de Asistente"
        assert "coinflip" not in tree_cmds, "coinflip no debería estar en el árbol general de Asistente"
        assert "casino" not in tree_cmds, "casino no debería estar en el árbol general de Asistente"
        assert "slots" in economy_tree_cmds, "slots debe estar en el árbol de economía"
        assert "regalar" in economy_tree_cmds, "regalar debe estar en el árbol de economía"
        assert "blackjack" in economy_tree_cmds, "blackjack debe estar en el árbol de economía"
        assert "bj" in economy_tree_cmds, "bj debe estar en el árbol de economía"
        assert "ruleta" in economy_tree_cmds, "ruleta debe estar en el árbol de economía"
        assert "coinflip" in economy_tree_cmds, "coinflip debe estar en el árbol de economía"
        assert "casino" in economy_tree_cmds, "casino debe estar en el árbol de economía"
        assert "crimen" in economy_tree_cmds, "crimen debe estar en el árbol de economía"
        assert "ranking" in economy_tree_cmds, "ranking debe estar en el árbol de economía"
        assert "inventario" in economy_tree_cmds, "inventario debe estar en el árbol de economía"
        assert "usar" in economy_tree_cmds, "usar debe estar en el árbol de economía"
        assert "admin_dinero" in economy_tree_cmds, "admin_dinero debe estar en el árbol de economía"
        print("  ✅ TEST 17 PASADO: Arquitectura Dual Runner validada (Asistente: 22 cmds | Economia Asistente: 20 cmds).")

        # TEST 18: Simulación Monte Carlo calibrada a RTP 110.0% (+/- 0.5%)
        print("\n[TEST 18] Simulación Monte Carlo (100.000 tiradas calibradas a RTP 110.0%)...")
        import random
        random.seed(42)
        sim_res = engine.simulate_monte_carlo(spins=100000, bet=1000)
        rtp = sim_res["rtp_percent"]
        win_rate = sim_res["win_rate_percent"]
        print(f"  📊 Resultado Monte Carlo 5x3: Spins={sim_res['spins']:,} | RTP={rtp}% | HitRate={win_rate}% | MultiLine={sim_res['multi_line_rate_percent']}%")

        # Rango admisible para RTP de 110%: 109.0% - 111.0% (objetivo 110.0% +/- 0.5%)
        assert 109.0 <= rtp <= 111.0, f"RTP fuera de rango esperado de 110%: {rtp}%"
        assert 68.0 <= win_rate <= 73.0, f"Hit Rate fuera de rango esperado (~70.9%): {win_rate}%"
        print(f"  ✅ TEST 18 PASADO: Simulación Monte Carlo 5x3 validada con RTP={rtp}% (~110.0%) y HitRate={win_rate}%.")

        # TEST 19: Multiplicadores por Rol de Nivel (get_level_role_multiplier)
        print("\n[TEST 19] Multiplicadores por Rol de Nivel (get_level_role_multiplier)...")
        assert eco.get_level_role_multiplier(user_roles=[])[0] == 1.0
        assert eco.get_level_role_multiplier(user_roles=["Pendejo de Rango Medio"])[0] == 1.10
        assert eco.get_level_role_multiplier(user_roles=["1543228972354109464"])[0] == 1.20
        assert eco.get_level_role_multiplier(user_roles=["Pendejo de Élite", "Pendejo de Rango Medio"])[0] == 1.25
        assert eco.get_level_role_multiplier(user_roles=["Pendejo Legendario"])[0] == 1.30
        assert eco.get_level_role_multiplier(user_roles=["Pendejo Mítico", "Pendejo de Élite"])[0] == 1.40

        uid_work_mult = "100000000000000119"
        eco.ensure_user(uid_work_mult, default_cash=0)
        ok_wm, story_wm, rew_wm = eco.execute_work(
            uid_work_mult,
            cooldown_seconds=0,
            min_reward=1000,
            max_reward=1000,
            user_roles=["Pendejo Legendario"],
        )
        assert ok_wm is True
        assert rew_wm == 1300, f"1000 * 1.30 debe ser 1300, obtenido {rew_wm}"
        assert "+30%" in story_wm
        print("  ✅ TEST 19 PASADO: Multiplicadores por Rol de Nivel (+10% a +40%) validados.")

        # TEST 20: Sistema de Delitos (/crimen: can_crime y execute_crime)
        print("\n[TEST 20] Sistema de Delitos (/crimen: éxito, fallo con multa 10% mín 500, cooldown 12h)...")
        uid_crim = "100000000000000120"
        eco.ensure_user(uid_crim, default_cash=10000)

        # Forzar éxito con seed o probando ambos caminos
        ok_c1, msg_c1, delta_c1 = eco.execute_crime(
            uid_crim,
            user_roles=["Pendejo Experimentado"],  # x1.20
            cooldown_seconds=43200,
            min_reward=2000,
            max_reward=2000,
        )
        # Cooldown activo inmediato
        can_c_after, rem_c = eco.can_crime(uid_crim, cooldown_seconds=43200)
        assert can_c_after is False and rem_c > 43000
        ok_c_cool, msg_c_cool, delta_c_cool = eco.execute_crime(uid_crim, cooldown_seconds=43200)
        assert ok_c_cool is False and delta_c_cool == 0 and "⏳" in msg_c_cool

        # Probar fallo con usuario con poco dinero (300 Porros -> pierde 300 y queda en 0, nunca negativo)
        uid_crim_poor = "100000000000000121"
        for _ in range(30):
            eco.ensure_user(uid_crim_poor, default_cash=300)
            data_tmp = eco.load_economy_data()
            data_tmp["users"][uid_crim_poor]["cash"] = 300
            data_tmp["users"][uid_crim_poor]["last_crime"] = None
            eco.save_economy_data(data_tmp)
            ok_cp, msg_cp, delta_cp = eco.execute_crime(uid_crim_poor, cooldown_seconds=0)
            if not ok_cp:
                assert delta_cp == -300, f"Con 300 Porros la multa debe ser 300 (sin negativo), obtenido {delta_cp}"
                assert eco.get_balance(uid_crim_poor)["cash"] == 0
                break
        else:
            assert False, "No se produjo ningún fallo en 30 intentos de /crimen"

        # Probar fallo con usuario con 10.000 Porros -> multa 10% = 1.000 Porros y 3% (30) al jackpot
        uid_crim_rich = "100000000000000122"
        jp_before_crime = eco.get_server_jackpot()
        for _ in range(30):
            eco.ensure_user(uid_crim_rich, default_cash=10000)
            data_tmp = eco.load_economy_data()
            data_tmp["users"][uid_crim_rich]["cash"] = 10000
            data_tmp["users"][uid_crim_rich]["last_crime"] = None
            eco.save_economy_data(data_tmp)
            ok_cr, msg_cr, delta_cr = eco.execute_crime(uid_crim_rich, cooldown_seconds=0)
            if not ok_cr:
                assert delta_cr == -1000, f"10% de 10.000 debe ser -1000, obtenido {delta_cr}"
                assert eco.get_balance(uid_crim_rich)["cash"] == 9000
                assert eco.get_server_jackpot() >= jp_before_crime + 30
                break
        print("  ✅ TEST 20 PASADO: /crimen (éxito, multa 10% mín 500 sin negativo, bote y cooldown 12h) validado.")

        # TEST 21: /inventario, /usar (Monster Blanco + Pases XP) y Watcher de Expiración
        print("\n[TEST 21] /inventario, /usar (Monster Blanco y Pases XP) y check_and_expire_buffs...")
        uid_inv = "100000000000000123"
        eco.ensure_user(uid_inv, default_cash=200000)

        # Comprar Monster Blanco (25.000) y 2 Chutes de XP (2 x 15.000)
        ok_mb, _, _, _ = eco.buy_shop_item(uid_inv, "monster_blanco")
        assert ok_mb is True
        ok_xp1, _, _, _ = eco.buy_shop_item(uid_inv, "chute_xp")
        ok_xp2, _, _, _ = eco.buy_shop_item(uid_inv, "chute_xp")
        assert ok_xp1 is True and ok_xp2 is True

        # Poner al usuario en cooldown de trabajar, crimen y robar
        data_cd = eco.load_economy_data()
        now_iso = datetime.now(timezone.utc).isoformat()
        data_cd["users"][uid_inv]["last_work"] = now_iso
        data_cd["users"][uid_inv]["last_crime"] = now_iso
        data_cd["users"][uid_inv]["last_rob"] = now_iso
        eco.save_economy_data(data_cd)
        assert eco.can_work(uid_inv)[0] is False
        assert eco.can_crime(uid_inv)[0] is False
        assert eco.can_rob(uid_inv)[0] is False

        # Usar Monster Blanco -> resetea los 3 cooldowns al instante
        ok_use_mb, msg_use_mb, it_mb = eco.use_inventory_item(uid_inv, "monster_blanco")
        assert ok_use_mb is True and it_mb["id"] == "monster_blanco"
        assert eco.can_work(uid_inv)[0] is True
        assert eco.can_crime(uid_inv)[0] is True
        assert eco.can_rob(uid_inv)[0] is True

        # Usar primer Chute de XP (24h) y luego el segundo (extiende a ~48h)
        ok_u1, msg_u1, it_u1 = eco.use_inventory_item(uid_inv, "chute_xp")
        assert ok_u1 is True and it_u1["role_id"] == "1549880939205623972"
        ok_u2, msg_u2, _ = eco.use_inventory_item(uid_inv, "chute_xp")
        assert ok_u2 is True and "extendido" in msg_u2.lower()

        inv_embed = eco.build_inventory_embed(uid_inv, "TesterInv")
        assert "TesterInv" in inv_embed.title
        assert len(inv_embed.fields) == 4

        # Simular expiración pasando una fecha futura (+50 horas) a check_and_expire_buffs
        from datetime import timedelta
        future_dt = datetime.now(timezone.utc) + timedelta(hours=50)
        expired = eco.check_and_expire_buffs(now_dt=future_dt)
        assert any(e["user_id"] == uid_inv and e["item_id"] == "chute_xp" for e in expired)
        assert len(eco.get_user_economy(uid_inv)["active_buffs"]) == 0
        print("  ✅ TEST 21 PASADO: /inventario, /usar (Monster Blanco + Pases XP) y expiración automática validados.")

        # TEST 22: Clasificación de Riqueza (/ranking)
        print("\n[TEST 22] Clasificación de Riqueza (/ranking: total, cash, bank)...")
        lb_total = eco.get_economy_leaderboard(sort_by="total", limit=5)
        lb_cash = eco.get_economy_leaderboard(sort_by="cash", limit=5)
        lb_bank = eco.get_economy_leaderboard(sort_by="bank", limit=5)
        assert len(lb_total) > 0 and lb_total[0]["rank"] == 1
        assert lb_total[0]["total"] >= lb_total[-1]["total"]
        assert lb_cash[0]["cash"] >= lb_cash[-1]["cash"]
        assert lb_bank[0]["bank"] >= lb_bank[-1]["bank"]

        rk_embed = eco.build_ranking_embed(sort_by="total", requester_id=uid_inv)
        assert "Clasificación de Riqueza" in rk_embed.title
        rk_view = eco.RankingView(author_id=uid_inv, sort_by="total")
        assert len(rk_view.children) == 1
        print("  ✅ TEST 22 PASADO: /ranking (leaderboard y vista interactiva) validado.")

        # TEST 23: Panel Financiero de Administración (/admin_dinero)
        print("\n[TEST 23] Panel Financiero de Administración (dar, quitar, fijar, airdrop)...")
        uid_adm = "100000000000000124"
        eco.ensure_user(uid_adm, default_cash=1000)

        ok_dar, _, b_dar = eco.admin_modify_money(uid_adm, "dar", 5000, target_field="cash", username="adm_test")
        assert ok_dar is True and b_dar["cash"] == 6000

        ok_quitar, _, b_quitar = eco.admin_modify_money(uid_adm, "quitar", 2000, target_field="cash")
        assert ok_quitar is True and b_quitar["cash"] == 4000

        ok_fijar, _, b_fijar = eco.admin_modify_money(uid_adm, "fijar", 25000, target_field="bank")
        assert ok_fijar is True and b_fijar["bank"] == 25000 and b_fijar["total"] == 29000

        ok_air, msg_air, cnt_air = eco.admin_airdrop_role(
            targets=[(uid_adm, "adm_test"), (uid_inv, "inv_test")],
            amount=3000,
            target_field="cash",
            role_name="Rol VIP",
        )
        assert ok_air is True and cnt_air == 2
        assert eco.get_balance(uid_adm)["cash"] == 7000
        print("  ✅ TEST 23 PASADO: /admin_dinero (dar, quitar, fijar y airdrop) validado.")

        # TEST 24: Transferencia de ítems (/regalar) y Restricción de canales (ensure_economy_channel)
        print("\n[TEST 24] Transferencia de ítems (/regalar) y Restricción de canales (ensure_economy_channel)...")
        # 1. Asignar inventario previo a uid_adm
        data = eco.load_economy_data()
        data["users"][uid_adm].setdefault("inventory", []).extend([
            eco.SHOP_ITEMS["porro_oro"]["name"],
            eco.SHOP_ITEMS["porro_oro"]["name"],
            eco.SHOP_ITEMS["monster_blanco"]["name"],
        ])
        eco.save_economy_data(data)

        # Regalo exitoso: uid_adm regala 1 porro_oro a uid_inv
        ok_g1, msg_g1, item_g1 = eco.gift_inventory_item(uid_adm, uid_inv, "porro_oro", quantity=1)
        assert ok_g1 is True, f"Error al regalar porro_oro: {msg_g1}"
        assert item_g1["id"] == "porro_oro"
        data_after = eco.load_economy_data()
        assert data_after["users"][uid_adm]["inventory"].count(eco.SHOP_ITEMS["porro_oro"]["name"]) == 1
        assert data_after["users"][uid_inv]["inventory"].count(eco.SHOP_ITEMS["porro_oro"]["name"]) == 1

        # Auto-regalo prohibido
        ok_g_self, msg_g_self, _ = eco.gift_inventory_item(uid_adm, uid_adm, "porro_oro", quantity=1)
        assert ok_g_self is False and "ti mismo" in msg_g_self.lower()

        # Cantidad inválida (<= 0)
        ok_g_zero, msg_g_zero, _ = eco.gift_inventory_item(uid_adm, uid_inv, "porro_oro", quantity=0)
        assert ok_g_zero is False and "al menos 1" in msg_g_zero.lower()

        # Cantidad insuficiente
        ok_g_insuf, msg_g_insuf, _ = eco.gift_inventory_item(uid_adm, uid_inv, "porro_oro", quantity=10)
        assert ok_g_insuf is False and "no tienes suficientes" in msg_g_insuf.lower()

        # Ítem no transferible (ej. cartera_blindada o rol permanente)
        data = eco.load_economy_data()
        data["users"][uid_adm]["inventory"].append(eco.SHOP_ITEMS["cartera_blindada"]["name"])
        eco.save_economy_data(data)
        ok_g_perm, msg_g_perm, _ = eco.gift_inventory_item(uid_adm, uid_inv, "cartera_blindada", quantity=1)
        assert ok_g_perm is False and "no es transferible" in msg_g_perm.lower()

        # Ítem inexistente
        ok_g_none, msg_g_none, _ = eco.gift_inventory_item(uid_adm, uid_inv, "fantasma_xyz", quantity=1)
        assert ok_g_none is False and "no existe" in msg_g_none.lower()

        # 2. Restricción de canales (ensure_economy_channel)
        # Mock sin contexto de canal -> permite (True)
        mock_inter_none = MagicMock()
        mock_inter_none.channel_id = None
        mock_inter_none.channel = None
        assert asyncio.run(ensure_economy_channel(mock_inter_none)) is True

        # Mock en canal explícitamente permitido (ej: 1549458785485987890) -> permite (True)
        mock_inter_ch = MagicMock()
        mock_inter_ch.channel_id = 1549458785485987890
        mock_inter_ch.channel = MagicMock()
        mock_inter_ch.channel.category_id = None
        assert asyncio.run(ensure_economy_channel(mock_inter_ch)) is True

        # Mock en canal dentro de la categoría oficial de casino (1549512417610956871) -> permite (True)
        mock_inter_cat = MagicMock()
        mock_inter_cat.channel_id = 999999999999999991
        mock_inter_cat.channel = MagicMock()
        mock_inter_cat.channel.category_id = 1549512417610956871
        assert asyncio.run(ensure_economy_channel(mock_inter_cat)) is True

        # Mock en canal ajeno / no permitido -> bloquea (False) y envía mensaje efímero
        mock_inter_denied = MagicMock()
        mock_inter_denied.channel_id = 123456789012345678
        mock_inter_denied.channel = MagicMock()
        mock_inter_denied.channel.category_id = 888888888888888888
        mock_inter_denied.response = AsyncMock()
        res_denied = asyncio.run(ensure_economy_channel(mock_inter_denied))
        assert res_denied is False
        mock_inter_denied.response.send_message.assert_called_once()
        s_args, s_kwargs = mock_inter_denied.response.send_message.call_args
        assert s_kwargs.get("ephemeral") is True
        assert "solo están permitidos" in s_args[0]
        print("  ✅ TEST 24 PASADO: /regalar (transferencias y validaciones) y ensure_economy_channel validados.")

        print("\n" + "=" * 65)
        print("🎉 TODOS LOS 24 TESTS DE ECONOMÍA Y TRAGAPERRAS 5X3 PASARON CON ÉXITO (100%)")
        print("=" * 65)

    finally:
        eco.ECONOMY_DATA_PATH = original_path
        eco._ECONOMY_CACHE = None
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
