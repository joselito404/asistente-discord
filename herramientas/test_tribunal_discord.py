"""
Suite de Pruebas Unitarias para Juicios Comunitarios de El Tribunal en Discord.
Especificación técnica: docs/DISENO_TRIBUNAL_DISCORD.md
Módulo bajo prueba: modulos/tribunal_discord.py y comando /juicio en modulos/comandos_generales.py.

Pruebas cubiertas:
1. Apertura de juicios y validaciones:
   - Saldo suficiente de demandante y acusado.
   - Saldo insuficiente del demandante (fianza + 50 de tasa judicial).
   - Saldo insuficiente del acusado (fianza).
   - Veto de autodemandas.
   - Veto de llevar a juicio a un bot.
   - Bloqueo de juicios concurrentes en el mismo canal.
   - Retención atómica de fianzas y cobro de tasa no reembolsable al server_jackpot.
2. Votación y jurado popular:
   - Veto de voto a demandante y demandado.
   - Voto válido de terceros (Culpable e Inocente).
   - Cambio / conmutación de voto (Culpable -> Inocente y viceversa).
   - Idempotencia del voto repetido.
   - Cálculo de la barra visual de veredicto.
3. Resoluciones y sentencias:
   - Falta de quorum (< 2 votos): Caso desestimado, devolución de fianzas (tasa judicial no devuelta).
   - Culpable (Culpable > Inocente): Demandante recibe fianza doble, asignación de rol 'Culpable de Skill Issue'.
   - Inocente (Inocente > Culpable): Acusado recibe fianza doble por costas procesales.
   - Empate (Culpable == Inocente): In dubio pro reo, devolución de fianzas.
4. Comando Slash /juicio:
   - Acción 'demandar' con validaciones de fianza y motivo.
   - Acción 'estado' con juicio activo y sin juicio activo.
"""

import os
import sys
import json
import tempfile
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

# Añadir raíz al sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import modulos.economia_core as eco_mod
import modulos.tribunal_discord as trib_mod
from modulos.tribunal_discord import (
    TrialState,
    TrialView,
    ACTIVE_TRIALS,
    TRIALS_LOCK,
    MIN_BAIL,
    MAX_BAIL,
    DEFAULT_BAIL,
    COURT_FEE,
    MIN_QUORUM,
    CULPABLE_ROLE_NAME,
    start_trial,
    resolve_trial,
    get_active_trial,
)
import modulos.comandos_generales as cmd_gen


def _make_mock_user(user_id: int, name: str, is_bot: bool = False):
    """Crea un mock de discord.Member/User."""
    user = MagicMock()
    user.id = user_id
    user.display_name = name
    user.name = name
    user.mention = f"<@{user_id}>"
    user.bot = is_bot
    user.add_roles = AsyncMock()
    return user


def _make_mock_interaction(
    user_id: int = 1001,
    channel_id: int = 2001,
    guild_id: int = 3001,
    user_name: str = "Demandante",
):
    """Crea un mock de discord.Interaction."""
    interaction = MagicMock()
    interaction.user = _make_mock_user(user_id, user_name)
    interaction.channel_id = channel_id
    interaction.guild_id = guild_id
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    guild = MagicMock()
    guild.id = guild_id
    role = MagicMock()
    role.name = CULPABLE_ROLE_NAME
    guild.roles = [role]
    guild.get_member = MagicMock(return_value=None)
    interaction.guild = guild

    channel = MagicMock()
    channel.id = channel_id
    channel.name = "⚖️el-tribunal-gaming⚖️"
    interaction.channel = channel
    return interaction


class TestTribunalDiscordBase(unittest.IsolatedAsyncioTestCase):
    """Clase base que aísla la base de datos de economía y los juicios activos."""

    async def asyncSetUp(self):
        # Crear archivo temporal de economía
        self.tmp_eco_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp_eco_path = self.tmp_eco_file.name
        self.tmp_eco_file.close()

        # Guardar path original de economía
        self.orig_eco_path = eco_mod.ECONOMY_DATA_PATH
        eco_mod.ECONOMY_DATA_PATH = self.tmp_eco_path

        # Inicializar economía con estructura fresca
        eco_mod._ECONOMY_CACHE = None
        data = {
            "users": {
                "1001": {"cash": 1000, "bank": 0},  # Demandante
                "1002": {"cash": 1000, "bank": 0},  # Acusado
                "2001": {"cash": 500, "bank": 0},   # Jurado 1
                "2002": {"cash": 500, "bank": 0},   # Jurado 2
                "2003": {"cash": 500, "bank": 0},   # Jurado 3
                "1003": {"cash": 40, "bank": 0},    # Tiesos
            },
            "server_jackpot": 25000,
            "meta": {"currency_name": "Porro", "emergency_halt": False},
        }
        with open(self.tmp_eco_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        eco_mod.load_economy_data(force_reload=True)

        # Limpiar juicios activos
        with TRIALS_LOCK:
            ACTIVE_TRIALS.clear()

    async def asyncTearDown(self):
        # Cancelar temporizadores pendientes
        with TRIALS_LOCK:
            for trial in list(ACTIVE_TRIALS.values()):
                if trial.timer_task and not trial.timer_task.done():
                    trial.timer_task.cancel()
            ACTIVE_TRIALS.clear()

        # Restaurar path original
        eco_mod.ECONOMY_DATA_PATH = self.orig_eco_path
        eco_mod._ECONOMY_CACHE = None
        if os.path.exists(self.tmp_eco_path):
            try:
                os.remove(self.tmp_eco_path)
            except Exception:
                pass


class TestTribunalApertura(TestTribunalDiscordBase):
    """Pruebas de validación de apertura y retención de fondos."""

    async def test_01_apertura_exitosa_descuento_y_tasa(self):
        """Valida que un juicio con fondos descuenta fianza a ambas partes y 50 de tasa al bote."""
        interaction = _make_mock_interaction(user_id=1001, channel_id=5001)
        defendant = _make_mock_user(user_id=1002, name="Acusado")

        initial_jackpot = eco_mod.get_server_jackpot()
        success, msg, trial = await start_trial(
            interaction=interaction,
            defendant=defendant,
            reason="Tiró flash a su propio equipo en CS2",
            bail=300,
            duration=60,
        )

        self.assertTrue(success, f"Error al iniciar juicio: {msg}")
        self.assertIsNotNone(trial)
        self.assertEqual(trial.channel_id, 5001)
        self.assertEqual(trial.bail, 300)
        self.assertEqual(trial.fee, COURT_FEE)

        # Verificar saldos
        bal_plaintiff = eco_mod.get_balance(1001)
        bal_defendant = eco_mod.get_balance(1002)
        # Demandante: 1000 - (300 + 50) = 650
        self.assertEqual(bal_plaintiff["cash"], 650)
        # Acusado: 1000 - 300 = 700
        self.assertEqual(bal_defendant["cash"], 700)
        # Jackport: +50
        self.assertEqual(eco_mod.get_server_jackpot(), initial_jackpot + 50)

        # Comprobar que está en ACTIVE_TRIALS
        self.assertIn(5001, ACTIVE_TRIALS)

    async def test_02_saldo_insuficiente_demandante(self):
        """Valida que si el demandante no tiene fianza + 50 tasa, no se abre el juicio."""
        interaction = _make_mock_interaction(user_id=1003, channel_id=5002)  # 1003 tiene solo 40 Porros
        defendant = _make_mock_user(user_id=1002, name="Acusado")

        success, msg, trial = await start_trial(
            interaction=interaction,
            defendant=defendant,
            reason="Skill issue general",
            bail=300,
        )

        self.assertFalse(success)
        self.assertIsNone(trial)
        self.assertIn("Saldo insuficiente", msg)
        self.assertNotIn(5002, ACTIVE_TRIALS)

    async def test_03_saldo_insuficiente_acusado(self):
        """Valida que si el acusado no cubre la fianza, no se abre el juicio."""
        interaction = _make_mock_interaction(user_id=1001, channel_id=5003)  # Demandante tiene 1000
        defendant = _make_mock_user(user_id=1003, name="AcusadoTieso")        # Acusado tiene 40

        success, msg, trial = await start_trial(
            interaction=interaction,
            defendant=defendant,
            reason="Debe dinero y no tiene",
            bail=300,
        )

        self.assertFalse(success)
        self.assertIsNone(trial)
        self.assertIn("no tiene suficientes Porros", msg)
        # Demandante no debió sufrir cargos
        self.assertEqual(eco_mod.get_balance(1001)["cash"], 1000)

    async def test_04_veto_autodemanda_y_veto_bots(self):
        """Valida que nadie puede demandarse a sí mismo ni a un bot."""
        interaction = _make_mock_interaction(user_id=1001, channel_id=5004)
        same_user = _make_mock_user(user_id=1001, name="Mismo")
        bot_user = _make_mock_user(user_id=9999, name="Botito", is_bot=True)

        # Autodemanda
        s1, m1, t1 = await start_trial(interaction, same_user, "Crisis de identidad", 300)
        self.assertFalse(s1)
        self.assertIn("No puedes demandarte a ti mismo", m1)

        # Bot
        s2, m2, t2 = await start_trial(interaction, bot_user, "Bot malo", 300)
        self.assertFalse(s2)
        self.assertIn("No puedes llevar a juicio a un bot", m2)

    async def test_05_bloqueo_juicios_concurrentes_en_mismo_canal(self):
        """Valida que solo puede haber 1 juicio activo por canal simultáneamente."""
        interaction = _make_mock_interaction(user_id=1001, channel_id=5005)
        defendant = _make_mock_user(user_id=1002, name="Acusado")

        s1, m1, t1 = await start_trial(interaction, defendant, "Causa 1", 300)
        self.assertTrue(s1)

        # Segundo intento en el mismo canal
        s2, m2, t2 = await start_trial(interaction, defendant, "Causa 2", 300)
        self.assertFalse(s2)
        self.assertIn("Ya hay un juicio activo en este canal", m2)


class TestTribunalVotacion(TestTribunalDiscordBase):
    """Pruebas del jurado popular, reglas de voto y conmutación."""

    def setUpTrial(self) -> TrialState:
        return TrialState(
            channel_id=6001,
            guild_id=3001,
            plaintiff_id=1001,
            plaintiff_name="Demandante",
            plaintiff_mention="<@1001>",
            defendant_id=1002,
            defendant_name="Acusado",
            defendant_mention="<@1002>",
            reason="Flashada en base",
            bail=300,
            duration=180,
        )

    def test_01_veto_partes_interesadas(self):
        """Valida que ni el demandante ni el acusado pueden votar."""
        trial = self.setUpTrial()

        ok_p, msg_p = trial.vote(1001, "culpable")
        self.assertFalse(ok_p)
        self.assertIn("parte interesada", msg_p)

        ok_d, msg_d = trial.vote(1002, "inocente")
        self.assertFalse(ok_d)
        self.assertIn("parte interesada", msg_d)

        self.assertEqual(trial.total_votes, 0)

    def test_02_voto_valido_y_cambio_de_voto(self):
        """Valida emisión de voto y conmutación limpia entre culpable e inocente."""
        trial = self.setUpTrial()
        juror_id = 2001

        # Vota Culpable
        ok, msg = trial.vote(juror_id, "culpable")
        self.assertTrue(ok)
        self.assertIn(juror_id, trial.votes_culpable)
        self.assertNotIn(juror_id, trial.votes_inocente)
        self.assertEqual(trial.total_votes, 1)

        # Repite Culpable (idempotente)
        ok_rep, msg_rep = trial.vote(juror_id, "culpable")
        self.assertTrue(ok_rep)
        self.assertIn("Ya habías votado", msg_rep)
        self.assertEqual(trial.total_votes, 1)

        # Cambia a Inocente
        ok_switch, msg_switch = trial.vote(juror_id, "inocente")
        self.assertTrue(ok_switch)
        self.assertNotIn(juror_id, trial.votes_culpable)
        self.assertIn(juror_id, trial.votes_inocente)
        self.assertEqual(trial.total_votes, 1)

    def test_03_barra_progreso_visual(self):
        """Valida la generación visual de la barra de veredicto."""
        trial = self.setUpTrial()
        self.assertIn("50% / 50%", trial.build_progress_bar())

        trial.vote(2001, "culpable")
        trial.vote(2002, "culpable")
        trial.vote(2003, "inocente")

        bar = trial.build_progress_bar()
        self.assertIn("🟥", bar)
        self.assertIn("🟩", bar)
        self.assertIn("66%", bar)
        self.assertIn("33%", bar)


class TestTribunalResolucion(TestTribunalDiscordBase):
    """Pruebas de resoluciones: Culpable, Inocente, Empate y Desestimación."""

    async def _setup_active_trial(self, channel_id: int = 7001, bail: int = 300) -> TrialState:
        interaction = _make_mock_interaction(user_id=1001, channel_id=channel_id)
        defendant = _make_mock_user(user_id=1002, name="Acusado")
        defendant_member = MagicMock()
        defendant_member.id = 1002
        defendant_member.add_roles = AsyncMock()
        interaction.guild.get_member.return_value = defendant_member

        ok, msg, trial = await start_trial(interaction, defendant, "Causa de prueba", bail=bail, duration=60)
        self.assertTrue(ok)
        trial.message = MagicMock()
        trial.message.edit = AsyncMock()
        return trial

    async def test_01_resolucion_falta_de_quorum(self):
        """Valida que con menos de 2 votos ajenos el juicio se desestima y se devuelven las fianzas."""
        trial = await self._setup_active_trial(7001, bail=300)
        # Solo 1 voto (insuficiente para quorum de 2)
        trial.vote(2001, "culpable")

        res_trial = await resolve_trial(7001)
        self.assertIsNotNone(res_trial)
        self.assertEqual(res_trial.status, "dismissed")
        self.assertNotIn(7001, ACTIVE_TRIALS)

        # Comprobar devolución de fianzas (300 Porros c/u devueltos)
        # Demandante: 650 + 300 = 950 (los 50 de tasa no se devuelven)
        self.assertEqual(eco_mod.get_balance(1001)["cash"], 950)
        # Acusado: 700 + 300 = 1000
        self.assertEqual(eco_mod.get_balance(1002)["cash"], 1000)

    async def test_02_resolucion_culpable_transferencia_y_rol(self):
        """Valida veredicto Culpable: demandante recibe 2 * fianza y se intenta asignar el rol."""
        trial = await self._setup_active_trial(7002, bail=300)
        trial.vote(2001, "culpable")
        trial.vote(2002, "culpable")
        trial.vote(2003, "inocente")

        res_trial = await resolve_trial(7002)
        self.assertEqual(res_trial.status, "culpable")

        # Demandante recibe 2 * 300 = 600 Porros
        # Saldo previo de demandante tras apertura: 650 -> 650 + 600 = 1250
        self.assertEqual(eco_mod.get_balance(1001)["cash"], 1250)
        # Acusado no recupera fianza: saldo sigue en 700
        self.assertEqual(eco_mod.get_balance(1002)["cash"], 700)

    async def test_03_resolucion_inocente_costas_judiciales(self):
        """Valida veredicto Inocente: acusado recibe 2 * fianza por indemnización de costas."""
        trial = await self._setup_active_trial(7003, bail=300)
        trial.vote(2001, "inocente")
        trial.vote(2002, "inocente")
        trial.vote(2003, "culpable")

        res_trial = await resolve_trial(7003)
        self.assertEqual(res_trial.status, "inocente")

        # Demandante no recupera fianza: saldo sigue en 650
        self.assertEqual(eco_mod.get_balance(1001)["cash"], 650)
        # Acusado recibe 2 * 300 = 600 Porros: 700 + 600 = 1300
        self.assertEqual(eco_mod.get_balance(1002)["cash"], 1300)

    async def test_04_resolucion_empate_in_dubio_pro_reo(self):
        """Valida veredicto Empate: In dubio pro reo, se devuelven las fianzas íntegras a ambos."""
        trial = await self._setup_active_trial(7004, bail=300)
        trial.vote(2001, "culpable")
        trial.vote(2002, "inocente")

        res_trial = await resolve_trial(7004)
        self.assertEqual(res_trial.status, "tie")

        # Demandante: 650 + 300 = 950
        self.assertEqual(eco_mod.get_balance(1001)["cash"], 950)
        # Acusado: 700 + 300 = 1000
        self.assertEqual(eco_mod.get_balance(1002)["cash"], 1000)


class TestTribunalComandosSlash(TestTribunalDiscordBase):
    """Pruebas del comando slash /juicio."""

    async def test_01_comando_juicio_estado_sin_juicio(self):
        """Valida que /juicio accion:estado sin juicio activo responde con aviso informativo."""
        interaction = _make_mock_interaction(channel_id=8001)
        choice = MagicMock()
        choice.value = "estado"

        callback = getattr(cmd_gen.cmd_juicio, "callback", cmd_gen.cmd_juicio)
        await callback(interaction, accion=choice)
        interaction.response.send_message.assert_called_once()
        args, kwargs = interaction.response.send_message.call_args
        self.assertIn("No hay ningún juicio activo", kwargs.get("content", args[0] if args else ""))

    async def test_02_comando_juicio_demandar_sin_acusado(self):
        """Valida que /juicio accion:demandar sin acusado arroja error."""
        interaction = _make_mock_interaction(channel_id=8002)
        choice = MagicMock()
        choice.value = "demandar"

        callback = getattr(cmd_gen.cmd_juicio, "callback", cmd_gen.cmd_juicio)
        await callback(interaction, accion=choice, acusado=None, motivo="Test")
        interaction.response.send_message.assert_called_once()
        args, kwargs = interaction.response.send_message.call_args
        self.assertIn("Debes especificar el miembro", kwargs.get("content", args[0] if args else ""))

    async def test_03_comando_juicio_demandar_exito(self):
        """Valida flujo completo de /juicio accion:demandar exitoso."""
        interaction = _make_mock_interaction(channel_id=8003)
        defendant = _make_mock_user(user_id=1002, name="Acusado")
        choice = MagicMock()
        choice.value = "demandar"

        callback = getattr(cmd_gen.cmd_juicio, "callback", cmd_gen.cmd_juicio)
        await callback(
            interaction,
            accion=choice,
            acusado=defendant,
            motivo="Robó el drop en Helldivers 2",
            fianza=250,
        )

        interaction.response.defer.assert_called_once()
        interaction.followup.send.assert_called_once()
        self.assertIn(8003, ACTIVE_TRIALS)


if __name__ == "__main__":
    unittest.main()
