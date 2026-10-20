"""
Suite de Pruebas Unitarias y de Integración Exhaustiva para el Centro de Control del Casino (/casino):
1. Generación de embed principal con bote acumulado y saldo del usuario (cash, bank, total).
2. Generación de las 4 vistas de detalle (slots, blackjack, ruleta, coinflip) con datos oficiales, RTP, reglas y cartera.
3. Componentes interactivos de CasinoHubView (Select con 4 opciones y Botón '🏠 Menú Principal').
4. Navegación en CasinoHubView: cambio de embed al seleccionar juego y retorno a menú principal.
5. Control de permisos estricto: rechazo efímero a terceros tanto en menú desplegable como en botón volver.
6. Manejo de Timeout (90s): desactivación limpia de todos los componentes interactivos sin crash.
7. Presencia e integridad de /casino en ECONOMY_SLASH_COMMANDS (14 comandos) y ALL_SLASH_COMMANDS (36 comandos).
8. Reexportación pública en bot_service (CasinoHubView, build_casino_hub_embed, cmd_casino).
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
    CasinoHubView,
    CasinoHubSelect,
    build_casino_hub_embed,
    CASINO_GAMES_INFO,
    DEFAULT_JACKPOT,
    get_server_jackpot,
    get_balance,
)
from modulos.comandos import (
    ECONOMY_SLASH_COMMANDS,
    ALL_SLASH_COMMANDS,
    cmd_casino,
)


def run_tests():
    print("=" * 70)
    print("🎰 INICIANDO SUITE DE PRUEBAS DEL CENTRO DE CONTROL DEL CASINO (/casino)")
    print("=" * 70)

    temp_dir = tempfile.mkdtemp()
    temp_json = os.path.join(temp_dir, "economia_test.json")
    original_path = eco.ECONOMY_DATA_PATH
    eco.ECONOMY_DATA_PATH = temp_json
    eco._ECONOMY_CACHE = None

    try:
        # TEST 1: Generación de Embed Principal (Bote y Saldo)
        print("\n[TEST 1] Generación de Embed Principal (Bote Acumulado y Saldo de Cartera)...")
        uid_tester = 100000000000000099
        mock_user = MagicMock()
        mock_user.id = uid_tester
        mock_user.display_name = "CasinoVIP"

        eco.ensure_user(uid_tester, default_cash=7500)
        eco.modify_balance(uid_tester, bank_delta=+15000)
        eco.modify_server_jackpot(+12500)  # Bote = 25000 + 12500 = 37500

        embed_home = build_casino_hub_embed(mock_user, selected_game=None)
        assert embed_home is not None
        assert "Casino Central Sanvi" in embed_home.title
        assert "37,500" in embed_home.description  # Bote grande y visible
        assert "<:Porro:1535685303317172305>" in embed_home.description

        # Verificar campos de cartera y catálogo
        field_dict = {f.name: f.value for f in embed_home.fields}
        assert "💼 Tu Balance Personal" in field_dict
        bal_text = field_dict["💼 Tu Balance Personal"]
        assert "7,500" in bal_text
        assert "15,000" in bal_text
        assert "22,500" in bal_text

        assert "🎮 Catálogo Oficial de Juegos Activos" in field_dict
        cat_text = field_dict["🎮 Catálogo Oficial de Juegos Activos"]
        assert "/slots" in cat_text
        assert "/blackjack" in cat_text
        assert "/ruleta" in cat_text
        assert "/coinflip" in cat_text
        print("  ✅ TEST 1 PASADO: Embed Principal con bote acumulado y cartera validado.")

        # TEST 2: Generación de las 4 Vistas Detalladas de Juegos
        print("\n[TEST 2] Generación de Vistas de Detalle (slots, blackjack, ruleta, coinflip)...")
        expected_keys = ["slots", "blackjack", "ruleta", "coinflip"]
        for g_key in expected_keys:
            embed_detail = build_casino_hub_embed(mock_user, selected_game=g_key)
            assert embed_detail is not None
            info = CASINO_GAMES_INFO[g_key]
            assert info["title"] == embed_detail.title
            assert info["command"] in embed_detail.description

            detail_fields = {f.name: f.value for f in embed_detail.fields}
            assert "📊 Retorno y Ventaja (RTP)" in detail_fields
            assert info["rtp"] == detail_fields["📊 Retorno y Ventaja (RTP)"]
            assert "💰 Tabla de Pagos" in detail_fields
            assert "⚙️ Reglas Especiales y Mecánicas" in detail_fields
            assert "💼 Tu Cartera Actual" in detail_fields
            assert "7,500" in detail_fields["💼 Tu Cartera Actual"]
            assert "🏆 Bote Progresivo Acumulado" in detail_fields
            assert "37,500" in detail_fields["🏆 Bote Progresivo Acumulado"]

        # Validaciones de contenido específico
        slots_embed = build_casino_hub_embed(mock_user, selected_game="slots")
        assert "110.03% RTP" in slots_embed.fields[0].value
        assert "7 Líneas" in slots_embed.fields[2].value
        assert "Grand Jackpot" in slots_embed.fields[2].value

        bj_embed = build_casino_hub_embed(mock_user, selected_game="blackjack")
        assert "99.50% RTP" in bj_embed.fields[0].value
        assert "3:2" in bj_embed.fields[1].value
        assert "6 Barajas" in bj_embed.fields[2].value
        assert "S17" in bj_embed.fields[2].value

        ruleta_embed = build_casino_hub_embed(mock_user, selected_game="ruleta")
        assert "97.30% RTP" in ruleta_embed.fields[0].value
        assert "35:1" in ruleta_embed.fields[1].value
        assert "0 Verde" in ruleta_embed.fields[2].value

        coinflip_embed = build_casino_hub_embed(mock_user, selected_game="coinflip")
        assert "50/50 Justo" in coinflip_embed.fields[0].value
        assert "98%" in coinflip_embed.fields[1].value
        assert "Retención Atómica" in coinflip_embed.fields[2].value
        print("  ✅ TEST 2 PASADO: Las 4 vistas de detalle generadas con datos exactos y RTP oficial.")

        # TEST 3: Componentes e Integridad de CasinoHubView
        print("\n[TEST 3] Estructura interactiva de CasinoHubView (Select y Botón)...")
        view = CasinoHubView(author_id=uid_tester)
        assert view.timeout == 90.0, f"Timeout esperado de 90s, obtenido: {view.timeout}"
        assert view.author_id == uid_tester

        # Comprobar componentes
        assert len(view.children) == 2, f"Se esperaban 2 componentes, encontrados: {len(view.children)}"
        select_item = next(c for c in view.children if isinstance(c, discord.ui.Select))
        home_button = next(c for c in view.children if isinstance(c, discord.ui.Button))

        assert len(select_item.options) == 4, f"Se esperaban 4 opciones de juego, encontradas: {len(select_item.options)}"
        option_values = [opt.value for opt in select_item.options]
        assert option_values == ["slots", "blackjack", "ruleta", "coinflip"]
        assert home_button.label == "🏠 Menú Principal"
        assert home_button.style == discord.ButtonStyle.secondary
        print("  ✅ TEST 3 PASADO: Estructura de CasinoHubView con Select (4 opciones) y Botón Home validada.")

        # TEST 4: Navegación Interactiva (Select y Home Button)
        print("\n[TEST 4] Navegación interactiva (selección en Select y retorno con botón)...")
        mock_inter = AsyncMock()
        mock_inter.user = mock_user
        mock_inter.response = AsyncMock()

        # Simular selección de 'blackjack' en el menú desplegable
        select_item._values = ["blackjack"]
        select_item._view = view
        asyncio.run(select_item.callback(mock_inter))

        assert view.current_game == "blackjack"
        mock_inter.response.edit_message.assert_called_once()
        _, edit_kwargs = mock_inter.response.edit_message.call_args
        edited_embed = edit_kwargs.get("embed")
        assert "Blackjack 21" in edited_embed.title
        assert edit_kwargs.get("view") == view

        # Simular clic en el botón '🏠 Menú Principal'
        mock_inter.response.edit_message.reset_mock()
        asyncio.run(home_button.callback(mock_inter))

        assert view.current_game is None
        mock_inter.response.edit_message.assert_called_once()
        _, home_kwargs = mock_inter.response.edit_message.call_args
        home_edited_embed = home_kwargs.get("embed")
        assert "Casino Central Sanvi" in home_edited_embed.title
        print("  ✅ TEST 4 PASADO: Navegación bidireccional (Select -> Detalle -> Home) verificada.")

        # TEST 5: Control de Permisos y Bloqueo a Terceros
        print("\n[TEST 5] Control de permisos y bloqueo efímero a terceros...")
        impostor = MagicMock()
        impostor.id = 999999999999999999
        impostor.display_name = "Metomentodo"

        mock_impostor_inter = AsyncMock()
        mock_impostor_inter.user = impostor
        mock_impostor_inter.response = AsyncMock()

        # Intento de uso de Select por tercero
        select_item._values = ["ruleta"]
        asyncio.run(select_item.callback(mock_impostor_inter))
        mock_impostor_inter.response.send_message.assert_called_once()
        send_args, send_kwargs = mock_impostor_inter.response.send_message.call_args
        assert "otro usuario" in send_args[0]
        assert send_kwargs.get("ephemeral") is True
        assert view.current_game != "ruleta"  # No se actualizó

        # Intento de uso de Botón Home por tercero
        mock_impostor_inter.response.send_message.reset_mock()
        asyncio.run(home_button.callback(mock_impostor_inter))
        mock_impostor_inter.response.send_message.assert_called_once()
        btn_args, btn_kwargs = mock_impostor_inter.response.send_message.call_args
        assert "otro usuario" in btn_args[0]
        assert btn_kwargs.get("ephemeral") is True
        print("  ✅ TEST 5 PASADO: Bloqueo efímero estricto a terceros en Select y Botón validado.")

        # TEST 6: Manejo de Timeout (90 segundos)
        print("\n[TEST 6] Manejo seguro de Timeout (desactivación sin crash)...")
        view_timeout = CasinoHubView(author_id=uid_tester, timeout=90.0)
        mock_msg = AsyncMock()
        view_timeout.message = mock_msg

        asyncio.run(view_timeout.on_timeout())
        for child in view_timeout.children:
            assert child.disabled is True, f"El componente {child} debería estar desactivado"

        mock_msg.edit.assert_called_once_with(view=view_timeout)
        print("  ✅ TEST 6 PASADO: Timeout a los 90s desactiva componentes y actualiza mensaje limpiamente.")

        # TEST 7: Comando Slash /casino y Catálogo de Comandos
        print("\n[TEST 7] Presencia e integridad de /casino en ECONOMY_SLASH_COMMANDS...")
        assert cmd_casino in ECONOMY_SLASH_COMMANDS, "cmd_casino debe estar en ECONOMY_SLASH_COMMANDS"
        assert cmd_casino in ALL_SLASH_COMMANDS, "cmd_casino debe estar en ALL_SLASH_COMMANDS"
        assert cmd_casino.name == "casino"
        assert len(cmd_casino.parameters) == 0, f"/casino no debe requerir parámetros obligatorios, tiene {len(cmd_casino.parameters)}"

        assert len(ECONOMY_SLASH_COMMANDS) == 19, f"Se esperaban 19 comandos de economía, encontrados: {len(ECONOMY_SLASH_COMMANDS)}"
        assert len(ALL_SLASH_COMMANDS) == 41, f"Se esperaban 41 comandos en total, encontrados: {len(ALL_SLASH_COMMANDS)}"

        eco_cmd_names = [c.name for c in ECONOMY_SLASH_COMMANDS]
        expected_eco = [
            "slots", "balance", "trabajar", "transferir", "depositar", "retirar",
            "robar", "tienda", "salario", "blackjack", "bj", "ruleta", "coinflip",
            "casino", "crimen", "ranking", "inventario", "usar", "admin_dinero"
        ]
        assert eco_cmd_names == expected_eco, f"Lista de comandos de economía discrepante: {eco_cmd_names}"
        print("  ✅ TEST 7 PASADO: /casino registrado en catálogo (19 comandos economía / 41 totales).")

        # TEST 8: Reexportación en bot_service
        print("\n[TEST 8] Reexportación pública en bot_service.py...")
        import bot_service
        for attr in ["CasinoHubView", "build_casino_hub_embed", "cmd_casino"]:
            assert hasattr(bot_service, attr), f"bot_service debe reexportar '{attr}'"

        # Verificar que /casino esté registrado en economy_tree de bot_service y no en tree general
        tree_cmds = [c.name for c in bot_service.tree.get_commands()]
        economy_tree_cmds = [c.name for c in bot_service.economy_tree.get_commands()]
        assert "casino" not in tree_cmds, "casino no debe estar en el árbol general de Asistente"
        assert "casino" in economy_tree_cmds, "casino debe estar en el árbol de economía"
        assert len(economy_tree_cmds) == 19, f"economy_tree debe tener 19 comandos, tiene {len(economy_tree_cmds)}"
        print("  ✅ TEST 8 PASADO: Reexportación y asignación al CommandTree de Economía verificada.")

        print("\n" + "=" * 70)
        print("🎉 TODOS LOS TESTS DEL CENTRO DE CONTROL DEL CASINO PASARON (8/8)")
        print("=" * 70)

    finally:
        eco.ECONOMY_DATA_PATH = original_path
        eco._ECONOMY_CACHE = None
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
