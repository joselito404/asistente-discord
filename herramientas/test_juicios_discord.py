"""
Suite de Pruebas Unitarias y de Integración Exhaustiva para Juicios Comunitarios en Discord:
Especificación canónica docs/DISENO_JUICIOS_DISCORD.md aprobada por Jose:
1. Modo Dual de Fianza:
   - Modo Económico (fianza > 0): retención atómica de fianza a ambas partes y COURT_FEE = 50 a server_jackpot.
   - Modo Moral (fianza == 0): 0 Porros retenidos y 0 tasas judiciales.
2. Veto procesal a partes implicadas (ni demandante ni acusado pueden votar).
3. Votación popular, idempotencia y conmutación limpia de votos.
4. Quorum insuficiente (< 2 votos): caso desestimado y devolución íntegra de fianzas.
5. Resoluciones judiciales completas:
   - Culpable: demandante gana el pozo total (2 * fianza) + rol temporal 'Culpable de Skill Issue'.
   - Inocente: acusado gana el pozo total (2 * fianza) como costas indemnizatorias.
   - Empate (In dubio pro reo): restitución del 100% de fianzas a ambas partes.
6. Comandos slash /juicio demandar y /juicio estado:
   - Filtros de validación: bot, auto-demanda, motivo vacío / >250 caracteres, fianza fuera de rango.
   - Control de solvencia económica de demandante y demandado.
   - Concurrencia de canal: un solo juicio activo simultáneo por canal.
   - Registro en GENERAL_SLASH_COMMANDS y ALL_SLASH_COMMANDS.
"""

import os
import sys
import shutil
import tempfile
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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
from modulos.juicios_discord import (
    MIN_BAIL,
    MAX_BAIL,
    DEFAULT_BAIL,
    COURT_FEE,
    TRIAL_DURATION,
    MIN_QUORUM,
    SKILL_ISSUE_ROLE_NAME,
    ACTIVE_TRIALS,
    TRIALS_LOCK,
    TrialSession,
    TrialView,
    render_vote_bar,
    build_trial_embed,
    resolve_trial,
    cmd_juicio,
    cmd_juicio_demandar,
    cmd_juicio_estado,
)
from modulos.comandos_generales import GENERAL_SLASH_COMMANDS
from modulos.comandos import ALL_SLASH_COMMANDS


def create_mock_member(user_id: int, name: str, is_bot: bool = False, roles=None):
    m = MagicMock(spec=discord.Member)
    m.id = user_id
    m.display_name = name
    m.name = name
    m.mention = f"<@{user_id}>"
    m.bot = is_bot
    m.roles = roles or []
    m.add_roles = AsyncMock()
    m.remove_roles = AsyncMock()
    return m


def create_mock_interaction(user, channel_id=123456789, guild=None):
    interaction = MagicMock(spec=discord.Interaction)
    interaction.user = user
    interaction.channel_id = channel_id
    interaction.channel = MagicMock()
    interaction.guild_id = 999888777
    interaction.guild = guild or MagicMock(spec=discord.Guild)
    interaction.guild.name = "Los Mongolos del Sanvi"
    interaction.guild.roles = []
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    interaction.original_response = AsyncMock(return_value=MagicMock(spec=discord.Message))
    interaction.message = MagicMock(spec=discord.Message)
    interaction.message.edit = AsyncMock()
    return interaction


async def run_async_tests():
    print("=" * 70)
    print("⚖️ INICIANDO SUITE DE PRUEBAS DEL SISTEMA DE JUICIOS EN DISCORD")
    print("=" * 70)

    # Crear entorno temporal aislado para economía
    temp_dir = tempfile.mkdtemp()
    test_json_path = os.path.join(temp_dir, "economia_test.json")
    original_path = eco.ECONOMY_DATA_PATH
    eco.ECONOMY_DATA_PATH = test_json_path
    eco._ECONOMY_CACHE = None
    ACTIVE_TRIALS.clear()

    try:
        # TEST 1: Parámetros canónicos y barra visual de escrutinio
        print("\n[TEST 1] Verificación de constantes canónicas y render_vote_bar...")
        assert MIN_BAIL == 100, f"MIN_BAIL esperado 100, obtenido {MIN_BAIL}"
        assert MAX_BAIL == 2500, f"MAX_BAIL esperado 2500, obtenido {MAX_BAIL}"
        assert DEFAULT_BAIL == 300, f"DEFAULT_BAIL esperado 300, obtenido {DEFAULT_BAIL}"
        assert COURT_FEE == 50, f"COURT_FEE esperado 50, obtenido {COURT_FEE}"
        assert TRIAL_DURATION == 120, f"TRIAL_DURATION esperado 120s, obtenido {TRIAL_DURATION}"
        assert MIN_QUORUM == 2, f"MIN_QUORUM esperado 2, obtenido {MIN_QUORUM}"

        # Test barra visual
        bar_empty, pg, pi = render_vote_bar(0, 0)
        assert bar_empty == "⬜" * 10
        assert pg == 0.0 and pi == 0.0

        bar_half, pg, pi = render_vote_bar(5, 5)
        assert bar_half == "🟥" * 5 + "🟩" * 5
        assert pg == 50.0 and pi == 50.0

        bar_guilty_heavy, pg, pi = render_vote_bar(9, 1)
        assert bar_guilty_heavy == "🟥" * 9 + "🟩" * 1
        assert pg == 90.0 and pi == 10.0
        print("  ✅ TEST 1 PASADO: Constantes y barra visual verificadas correctamente.")

        # TEST 2: Veto procesal a partes implicadas (Acusador y Acusado no pueden votar)
        print("\n[TEST 2] Veto procesal a partes implicadas en TrialView...")
        plaintiff = create_mock_member(1001, "DemandantePepe")
        defendant = create_mock_member(1002, "AcusadoPaco")
        juror1 = create_mock_member(1003, "JuradoExterno1")

        session = TrialSession(
            channel_id=5551,
            guild_id=999,
            plaintiff=plaintiff,
            defendant=defendant,
            reason="Se desconectó a mitad de la partida",
            bail=300,
            fee_paid=50,
        )
        view = TrialView(session)

        # 2.1 Intento de voto por parte del demandante
        inter_p = create_mock_interaction(plaintiff, channel_id=5551)
        await view._handle_vote(inter_p, "culpable")
        assert len(session.votes_guilty) == 0
        call_msg = inter_p.response.send_message.call_args[0][0]
        assert "Incompatibilidad Judicial" in call_msg and inter_p.response.send_message.call_args[1].get("ephemeral") is True

        # 2.2 Intento de voto por parte del acusado
        inter_d = create_mock_interaction(defendant, channel_id=5551)
        await view._handle_vote(inter_d, "inocente")
        assert len(session.votes_innocent) == 0
        call_msg = inter_d.response.send_message.call_args[0][0]
        assert "Incompatibilidad Judicial" in call_msg and inter_d.response.send_message.call_args[1].get("ephemeral") is True
        print("  ✅ TEST 2 PASADO: Veto estricto a demandante y acusado verificado.")

        # TEST 3: Votación de jurados externos, idempotencia y conmutación
        print("\n[TEST 3] Votación de jurado popular, idempotencia y conmutación limpia...")
        inter_j1 = create_mock_interaction(juror1, channel_id=5551)

        # 3.1 Primer voto a Culpable
        await view._handle_vote(inter_j1, "culpable")
        assert juror1.id in session.votes_guilty
        assert juror1.id not in session.votes_innocent
        assert "Has votado **Culpable**" in inter_j1.response.send_message.call_args[0][0]

        # 3.2 Repetición del mismo voto (Idempotencia)
        inter_j1_repeat = create_mock_interaction(juror1, channel_id=5551)
        await view._handle_vote(inter_j1_repeat, "culpable")
        assert len(session.votes_guilty) == 1
        assert "Ya has votado **Culpable**" in inter_j1_repeat.response.send_message.call_args[0][0]

        # 3.3 Conmutación de voto a Inocente
        inter_j1_switch = create_mock_interaction(juror1, channel_id=5551)
        await view._handle_vote(inter_j1_switch, "inocente")
        assert juror1.id not in session.votes_guilty
        assert juror1.id in session.votes_innocent
        assert "conmutado tu voto a **Inocente**" in inter_j1_switch.response.send_message.call_args[0][0]

        # 3.4 Botón Ver Cargos
        inter_charges = create_mock_interaction(juror1, channel_id=5551)
        await view.btn_charges.callback(inter_charges)
        cargos_text = inter_charges.response.send_message.call_args[0][0]
        assert "EXPEDIENTE JUDICIAL DE LA CAUSA" in cargos_text
        assert "Se desconectó a mitad de la partida" in cargos_text
        assert inter_charges.response.send_message.call_args[1].get("ephemeral") is True
        print("  ✅ TEST 3 PASADO: Votación, idempotencia, conmutación y expediente verificados.")

        # TEST 4: Resolución por Quorum Insuficiente (< 2 votos externos)
        print("\n[TEST 4] Caso desestimado por Quorum Insuficiente (< 2 votos)...")
        u_p = 2001
        u_d = 2002
        eco.ensure_user(u_p, default_cash=1000)
        eco.ensure_user(u_d, default_cash=1000)
        initial_jackpot = eco.get_server_jackpot()

        # Deducir fianza de 300 + tasa 50 a demandante, y fianza de 300 a acusado
        with eco.ECONOMY_LOCK:
            eco.modify_balance(u_p, cash_delta=-(300 + COURT_FEE))
            eco.modify_balance(u_d, cash_delta=-300)
            eco.modify_server_jackpot(COURT_FEE)

        p_mem = create_mock_member(u_p, "Demandante4")
        d_mem = create_mock_member(u_d, "Acusado4")
        sess_quorum = TrialSession(
            channel_id=5554,
            guild_id=999,
            plaintiff=p_mem,
            defendant=d_mem,
            reason="Prueba falta quorum",
            bail=300,
            fee_paid=COURT_FEE,
        )
        sess_quorum.view = TrialView(sess_quorum)
        sess_quorum.message = MagicMock(spec=discord.Message)
        sess_quorum.message.edit = AsyncMock()
        ACTIVE_TRIALS[5554] = sess_quorum

        # Solo 1 voto emitido (< MIN_QUORUM = 2)
        sess_quorum.votes_guilty.add(9999)

        await resolve_trial(sess_quorum)
        assert sess_quorum.resolved is True
        assert 5554 not in ACTIVE_TRIALS

        # Verificación de saldos: se reembolsa fianza íntegra (300) a ambos. Tasa 50 queda en jackpot.
        cash_p = eco.get_balance(u_p)["cash"]
        cash_d = eco.get_balance(u_d)["cash"]
        assert cash_p == 1000 - COURT_FEE, f"Demandante debe tener 950 (fianza devuelta, tasa no), obtenido {cash_p}"
        assert cash_d == 1000, f"Acusado debe tener 1000 (fianza devuelta integra), obtenido {cash_d}"
        assert eco.get_server_jackpot() == initial_jackpot + COURT_FEE
        print("  ✅ TEST 4 PASADO: Falta de quorum desestima y devuelve fianzas íntegras.")

        # TEST 5: Resolución de Veredicto CULPABLE (Culpable > Inocente)
        print("\n[TEST 5] Veredicto CULPABLE: pozo a demandante y rol temporal...")
        u_p5 = 2005
        u_d5 = 2006
        eco.ensure_user(u_p5, default_cash=1000)
        eco.ensure_user(u_d5, default_cash=1000)

        with eco.ECONOMY_LOCK:
            eco.modify_balance(u_p5, cash_delta=-(300 + COURT_FEE))
            eco.modify_balance(u_d5, cash_delta=-300)

        # Configurar rol de skill issue en mock guild
        mock_guild = MagicMock(spec=discord.Guild)
        mock_guild.name = "Los Mongolos del Sanvi"
        skill_role = MagicMock(spec=discord.Role)
        skill_role.name = SKILL_ISSUE_ROLE_NAME
        mock_guild.roles = [skill_role]

        p_mem5 = create_mock_member(u_p5, "Demandante5")
        d_mem5 = create_mock_member(u_d5, "Acusado5")
        mock_guild.get_member = MagicMock(return_value=d_mem5)

        sess_guilty = TrialSession(
            channel_id=5555,
            guild_id=999,
            plaintiff=p_mem5,
            defendant=d_mem5,
            reason="Manqueó estrepitosamente en Ranked",
            bail=300,
            fee_paid=COURT_FEE,
            guild=mock_guild,
        )
        sess_guilty.view = TrialView(sess_guilty)
        sess_guilty.message = MagicMock(spec=discord.Message)
        sess_guilty.message.edit = AsyncMock()
        ACTIVE_TRIALS[5555] = sess_guilty

        # 3 votos Culpable vs 0 votos Inocente
        sess_guilty.votes_guilty.update([8001, 8002, 8003])

        with patch("modulos.juicios_discord.SKILL_ISSUE_DURATION", 0.001):
            await resolve_trial(sess_guilty)
            if getattr(sess_guilty, "role_task", None):
                await sess_guilty.role_task

        assert sess_guilty.resolved is True
        assert 5555 not in ACTIVE_TRIALS

        # Demandante se lleva el pozo de fianza (+600) -> 650 iniciales tras fianza + 600 = 1250
        cash_p5 = eco.get_balance(u_p5)["cash"]
        cash_d5 = eco.get_balance(u_d5)["cash"]
        assert cash_p5 == 1000 - COURT_FEE + 300, f"Demandante debe ganar 300 netos (1250), obtenido {cash_p5}"
        assert cash_d5 == 700, f"Acusado pierde fianza (700), obtenido {cash_d5}"
        assert d_mem5.add_roles.called, "El acusado debe recibir el rol temporal de Skill Issue"
        print("  ✅ TEST 5 PASADO: Veredicto CULPABLE asigna pozo y sanción de rol.")

        # TEST 6: Resolución de Veredicto INOCENTE (Inocente > Culpable)
        print("\n[TEST 6] Veredicto INOCENTE: costas indemnizatorias al acusado...")
        u_p6 = 2007
        u_d6 = 2008
        eco.ensure_user(u_p6, default_cash=1000)
        eco.ensure_user(u_d6, default_cash=1000)

        with eco.ECONOMY_LOCK:
            eco.modify_balance(u_p6, cash_delta=-(300 + COURT_FEE))
            eco.modify_balance(u_d6, cash_delta=-300)

        p_mem6 = create_mock_member(u_p6, "Demandante6")
        d_mem6 = create_mock_member(u_d6, "Acusado6")

        sess_innocent = TrialSession(
            channel_id=5556,
            guild_id=999,
            plaintiff=p_mem6,
            defendant=d_mem6,
            reason="Acusación falsa de robo",
            bail=300,
            fee_paid=COURT_FEE,
        )
        sess_innocent.view = TrialView(sess_innocent)
        sess_innocent.message = MagicMock(spec=discord.Message)
        sess_innocent.message.edit = AsyncMock()
        ACTIVE_TRIALS[5556] = sess_innocent

        # 3 votos Inocente vs 1 voto Culpable
        sess_innocent.votes_innocent.update([8001, 8002, 8003])
        sess_innocent.votes_guilty.add(8004)

        await resolve_trial(sess_innocent)
        assert sess_innocent.resolved is True

        cash_p6 = eco.get_balance(u_p6)["cash"]
        cash_d6 = eco.get_balance(u_d6)["cash"]
        # Acusado se lleva el pozo de fianza (+600) -> 700 + 600 = 1300
        assert cash_d6 == 1300, f"Acusado debe ganar 300 netos de costas (1300), obtenido {cash_d6}"
        assert cash_p6 == 650, f"Demandante pierde fianza y tasa (650), obtenido {cash_p6}"
        print("  ✅ TEST 6 PASADO: Veredicto INOCENTE indemniza al acusado con costas.")

        # TEST 7: Resolución de EMPATE Judicial (In dubio pro reo)
        print("\n[TEST 7] Empate judicial: in dubio pro reo con devolución de fianzas...")
        u_p7 = 2009
        u_d7 = 2010
        eco.ensure_user(u_p7, default_cash=1000)
        eco.ensure_user(u_d7, default_cash=1000)

        with eco.ECONOMY_LOCK:
            eco.modify_balance(u_p7, cash_delta=-(300 + COURT_FEE))
            eco.modify_balance(u_d7, cash_delta=-300)

        p_mem7 = create_mock_member(u_p7, "Demandante7")
        d_mem7 = create_mock_member(u_d7, "Acusado7")

        sess_tie = TrialSession(
            channel_id=5557,
            guild_id=999,
            plaintiff=p_mem7,
            defendant=d_mem7,
            reason="Disputa sobre quién pagaba la pizza",
            bail=300,
            fee_paid=COURT_FEE,
        )
        sess_tie.view = TrialView(sess_tie)
        sess_tie.message = MagicMock(spec=discord.Message)
        sess_tie.message.edit = AsyncMock()
        ACTIVE_TRIALS[5557] = sess_tie

        # 2 votos Culpable vs 2 votos Inocente
        sess_tie.votes_guilty.update([8001, 8002])
        sess_tie.votes_innocent.update([8003, 8004])

        await resolve_trial(sess_tie)
        assert sess_tie.resolved is True

        cash_p7 = eco.get_balance(u_p7)["cash"]
        cash_d7 = eco.get_balance(u_d7)["cash"]
        assert cash_p7 == 950, f"Demandante recupera fianza 300 (950), obtenido {cash_p7}"
        assert cash_d7 == 1000, f"Acusado recupera fianza 300 (1000), obtenido {cash_d7}"
        print("  ✅ TEST 7 PASADO: Empate judicial devuelve fianzas íntegras.")

        # TEST 8: Modo Moral Honorífico (Fianza == 0)
        print("\n[TEST 8] Modo Moral Honorífico (Fianza == 0, sin tasas ni retención)...")
        u_p8 = 2011
        u_d8 = 2012
        eco.ensure_user(u_p8, default_cash=50)  # Saldo bajo
        eco.ensure_user(u_d8, default_cash=0)   # Saldo cero

        p_mem8 = create_mock_member(u_p8, "DemandanteMoral")
        d_mem8 = create_mock_member(u_d8, "AcusadoMoral")

        sess_moral = TrialSession(
            channel_id=5558,
            guild_id=999,
            plaintiff=p_mem8,
            defendant=d_mem8,
            reason="Dijo que venía en 5 minutos y tardó 3 horas",
            bail=0,
            fee_paid=0,
        )
        sess_moral.view = TrialView(sess_moral)
        sess_moral.message = MagicMock(spec=discord.Message)
        sess_moral.message.edit = AsyncMock()
        ACTIVE_TRIALS[5558] = sess_moral

        # 2 votos Culpable vs 0 Inocente
        sess_moral.votes_guilty.update([8001, 8002])
        await resolve_trial(sess_moral)

        # Saldos intactos
        cash_p8 = eco.get_balance(u_p8)["cash"]
        cash_d8 = eco.get_balance(u_d8)["cash"]
        assert cash_p8 == 50
        assert cash_d8 == 0
        print("  ✅ TEST 8 PASADO: Modo moral no altera fondos ni tasas.")

        # TEST 9: Comando Slash /juicio demandar (Validaciones y Flujos)
        print("\n[TEST 9] Comando Slash /juicio demandar y validaciones...")
        u_slash_p = 3001
        u_slash_d = 3002
        eco.ensure_user(u_slash_p, default_cash=1000)
        eco.ensure_user(u_slash_d, default_cash=1000)

        p_cmd = create_mock_member(u_slash_p, "DemandanteSlash")
        d_cmd = create_mock_member(u_slash_d, "AcusadoSlash")
        bot_member = create_mock_member(9999, "CarlBot", is_bot=True)

        # 9.1 Demanda a un bot
        inter = create_mock_interaction(p_cmd, channel_id=7701)
        await cmd_juicio_demandar.callback(inter, bot_member, "Spam", 300)
        assert "No puedes demandar a un bot" in inter.response.send_message.call_args[0][0]

        # 9.2 Auto-demanda
        inter = create_mock_interaction(p_cmd, channel_id=7701)
        await cmd_juicio_demandar.callback(inter, p_cmd, "Auto-odio", 300)
        assert "No puedes demandarte a ti mismo" in inter.response.send_message.call_args[0][0]

        # 9.3 Motivo vacío o > 250 chars
        inter = create_mock_interaction(p_cmd, channel_id=7701)
        await cmd_juicio_demandar.callback(inter, d_cmd, "   ", 300)
        assert "motivo o cargo válido" in inter.response.send_message.call_args[0][0]

        inter = create_mock_interaction(p_cmd, channel_id=7701)
        await cmd_juicio_demandar.callback(inter, d_cmd, "A" * 251, 300)
        assert "no puede superar los 250 caracteres" in inter.response.send_message.call_args[0][0]

        # 9.4 Fianza fuera de rango
        inter = create_mock_interaction(p_cmd, channel_id=7701)
        await cmd_juicio_demandar.callback(inter, d_cmd, "Falta menor", 50)
        assert "debe ser exactamente `0` (modo moral) o estar comprendida entre **100** y **2,500**" in inter.response.send_message.call_args[0][0]

        inter = create_mock_interaction(p_cmd, channel_id=7701)
        await cmd_juicio_demandar.callback(inter, d_cmd, "Falta menor", 3000)
        assert "debe ser exactamente `0` (modo moral) o estar comprendida entre **100** y **2,500**" in inter.response.send_message.call_args[0][0]

        # 9.5 Fondos insuficientes del demandante
        eco.ensure_user(3003, default_cash=100)
        p_pobre = create_mock_member(3003, "Pobre")
        inter = create_mock_interaction(p_pobre, channel_id=7701)
        await cmd_juicio_demandar.callback(inter, d_cmd, "Deudas", 300)
        assert "No tienes suficiente efectivo para abrir el juicio" in inter.response.send_message.call_args[0][0]

        # 9.6 Fondos insuficientes del acusado
        eco.ensure_user(3004, default_cash=50)
        d_pobre = create_mock_member(3004, "AcusadoPobre")
        inter = create_mock_interaction(p_cmd, channel_id=7701)
        await cmd_juicio_demandar.callback(inter, d_pobre, "Deudas", 300)
        assert "no dispone de suficiente efectivo para cubrir la fianza" in inter.response.send_message.call_args[0][0]

        # 9.7 Apertura exitosa de juicio económico
        inter = create_mock_interaction(p_cmd, channel_id=7701)
        def close_coro(coro):
            coro.close()
            return MagicMock()

        with patch("asyncio.create_task", side_effect=close_coro):
            await cmd_juicio_demandar.callback(inter, d_cmd, "Causa legítima", 300)
            assert 7701 in ACTIVE_TRIALS
            assert "has sido sentado en el banquillo" in inter.response.send_message.call_args[1]["content"]

        # 9.8 Concurrencia: segundo juicio en el mismo canal
        inter_dup = create_mock_interaction(p_cmd, channel_id=7701)
        await cmd_juicio_demandar.callback(inter_dup, d_cmd, "Otro caso", 300)
        assert "Ya existe un juicio popular activo en este canal" in inter_dup.response.send_message.call_args[0][0]

        # 9.9 Consulta de estado con /juicio estado
        inter_st = create_mock_interaction(p_cmd, channel_id=7701)
        await cmd_juicio_estado.callback(inter_st)
        assert inter_st.response.send_message.call_args[1].get("ephemeral") is True
        assert inter_st.response.send_message.call_args[1].get("embed") is not None

        # Estado en canal sin juicio
        inter_st_empty = create_mock_interaction(p_cmd, channel_id=99999)
        await cmd_juicio_estado.callback(inter_st_empty)
        assert "No hay ningún juicio activo en este canal" in inter_st_empty.response.send_message.call_args[0][0]
        print("  ✅ TEST 9 PASADO: Validaciones, fondos, concurrencia y comando /juicio verificados.")

        # TEST 10: Presencia en catálogos de comandos slash
        print("\n[TEST 10] Presencia de /juicio en GENERAL_SLASH_COMMANDS y ALL_SLASH_COMMANDS...")
        assert cmd_juicio in GENERAL_SLASH_COMMANDS, "cmd_juicio debe estar en GENERAL_SLASH_COMMANDS"
        assert cmd_juicio in ALL_SLASH_COMMANDS, "cmd_juicio debe estar en ALL_SLASH_COMMANDS"
        subcommands = [sc.name for sc in cmd_juicio.commands]
        assert "demandar" in subcommands, "Subcomando 'demandar' debe existir en /juicio"
        assert "estado" in subcommands, "Subcomando 'estado' debe existir en /juicio"
        print(f"  ✅ TEST 10 PASADO: /juicio registrado con subcomandos {subcommands}.")

        print("\n" + "=" * 70)
        print("🎉 ¡TODOS LOS TESTS DE JUICIOS EN DISCORD HAN PASADO AL 100%! 🎉")
        print("=" * 70)

    finally:
        eco.ECONOMY_DATA_PATH = original_path
        eco._ECONOMY_CACHE = None
        ACTIVE_TRIALS.clear()
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(run_async_tests())
