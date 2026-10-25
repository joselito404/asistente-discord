"""
Suite de tests unitarios para la Retención Permanente de Audios,
Salvaguarda de Cuota de Disco y Generador de Crónicas de Voz (/resumen_llamada).
"""

import asyncio
import io
import json
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Asegurar path raíz del proyecto
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import discord
from discord import app_commands

from modulos import voz
from modulos import comandos_generales
from modulos import comandos
import bot_service


class TestVozRetentionAndQuota(unittest.TestCase):
    """Pruebas de retención permanente y salvaguarda de cuota en disco."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.metadata_file = os.path.join(self.test_dir, "recordings_metadata.json")

    def tearDown(self):
        # Limpiar directorio temporal
        for fname in os.listdir(self.test_dir):
            try:
                os.remove(os.path.join(self.test_dir, fname))
            except Exception:
                pass
        try:
            os.rmdir(self.test_dir)
        except Exception:
            pass

    def test_infinite_retention_preserves_old_recordings(self):
        """Verifica que grabaciones con más de 24 horas y días de antigüedad NO se eliminan."""
        now = time.time()
        # Crear 3 grabaciones: 1 hora, 36 horas y 5 días de antigüedad
        old_entries = [
            {"id": "rec_1h", "filename": "rec_1h.wav", "epoch": now - 3600, "user": "Jose", "transcription": "Hola"},
            {"id": "rec_36h", "filename": "rec_36h.wav", "epoch": now - (36 * 3600), "user": "David", "transcription": "Buenas"},
            {"id": "rec_5d", "filename": "rec_5d.wav", "epoch": now - (5 * 24 * 3600), "user": "Pedro", "transcription": "GG"},
        ]

        for e in old_entries:
            fpath = os.path.join(self.test_dir, e["filename"])
            with open(fpath, "wb") as f:
                f.write(b"RIFF" + b"\x00" * 100)

        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(old_entries, f)

        with patch.object(voz, "RECORDINGS_DIR", self.test_dir), \
             patch.object(voz, "METADATA_FILE", self.metadata_file):
            valid = voz.load_recordings_metadata()

            # Todas las entradas deben conservarse íntegramente
            self.assertEqual(len(valid), 3)
            self.assertEqual({v["id"] for v in valid}, {"rec_1h", "rec_36h", "rec_5d"})

            # Todos los archivos deben seguir existiendo en el disco
            for e in old_entries:
                self.assertTrue(os.path.exists(os.path.join(self.test_dir, e["filename"])))

    def test_enforce_storage_quota_fifo_purge(self):
        """Verifica que al superar la cuota máxima, se purgan los audios más antiguos (FIFO) hasta estabilizar."""
        # Creamos 5 archivos de 100 KB cada uno = 500 KB total
        file_size = 100 * 1024
        files = []
        now = time.time()
        turns_log = []

        for i in range(5):
            fname = f"rec_{i}.wav"
            fpath = os.path.join(self.test_dir, fname)
            with open(fpath, "wb") as f:
                f.write(b"x" * file_size)
            # Asignar tiempos de modificación escalonados (0 es el más antiguo)
            mtime = now - (500 - i * 100)
            os.utime(fpath, (mtime, mtime))
            files.append((fname, fpath, mtime))
            turns_log.append({
                "id": f"rec_{i}",
                "filename": fname,
                "epoch": mtime,
                "user": f"User_{i}",
                "transcription": f"Texto {i}"
            })

        # Cuota simulada: max_bytes = 350 KB, target_bytes = 200 KB
        # Como hay 500 KB, debe purgar hasta quedar <= 200 KB (debe borrar rec_0, rec_1, rec_2 -> 3 archivos)
        max_bytes = 350 * 1024
        target_bytes = 200 * 1024

        with patch.object(voz, "RECORDINGS_DIR", self.test_dir), \
             patch.object(voz, "METADATA_FILE", self.metadata_file), \
             patch.object(voz, "VOICE_TURNS_LOG", turns_log):

            purged_count = voz.enforce_storage_quota(target_bytes=target_bytes, max_bytes=max_bytes)

            self.assertEqual(purged_count, 3)

            # Los 3 más antiguos (rec_0, rec_1, rec_2) deben haber sido eliminados
            self.assertFalse(os.path.exists(os.path.join(self.test_dir, "rec_0.wav")))
            self.assertFalse(os.path.exists(os.path.join(self.test_dir, "rec_1.wav")))
            self.assertFalse(os.path.exists(os.path.join(self.test_dir, "rec_2.wav")))

            # Los 2 más recientes (rec_3, rec_4) deben preservarse
            self.assertTrue(os.path.exists(os.path.join(self.test_dir, "rec_3.wav")))
            self.assertTrue(os.path.exists(os.path.join(self.test_dir, "rec_4.wav")))

            # El registro en memoria y archivo de metadata deben contener solo 2 entradas
            self.assertEqual(len(turns_log), 2)
            self.assertEqual([t["filename"] for t in turns_log], ["rec_3.wav", "rec_4.wav"])

    def test_enforce_storage_quota_no_purge_if_under_limit(self):
        """Verifica que si no se supera el límite de cuota, no se borra ningún archivo."""
        fname = "rec_single.wav"
        fpath = os.path.join(self.test_dir, fname)
        with open(fpath, "wb") as f:
            f.write(b"x" * 1024)

        turns_log = [{"id": "single", "filename": fname, "epoch": time.time()}]

        with patch.object(voz, "RECORDINGS_DIR", self.test_dir), \
             patch.object(voz, "METADATA_FILE", self.metadata_file), \
             patch.object(voz, "VOICE_TURNS_LOG", turns_log):
            purged = voz.enforce_storage_quota(target_bytes=350 * 1024 * 1024, max_bytes=450 * 1024 * 1024)
            self.assertEqual(purged, 0)
            self.assertTrue(os.path.exists(fpath))
            self.assertEqual(len(turns_log), 1)


class TestCallSummary(unittest.IsolatedAsyncioTestCase):
    """Pruebas del generador de crónicas y resúmenes de llamadas con IA."""

    async def test_generate_call_summary_empty(self):
        """Verifica que si no hay transcripciones válidas, retorna un Embed informativo vacío."""
        now = time.time()
        empty_turns = [
            {"epoch": now - 300, "user": "Jose", "transcription": "[Silencio]"},
            {"epoch": now - 200, "user": "David", "transcription": "[Ruido]"},
            {"epoch": now - 100, "user": "Alvaro", "transcription": "(audio procesado)"},
        ]

        with patch.object(voz, "VOICE_TURNS_LOG", empty_turns):
            embed = await voz.generate_call_summary(hours=2.0, channel_name="general-voz")
            self.assertIsInstance(embed, discord.Embed)
            self.assertIn("general-voz", embed.title)
            self.assertIn("No se han detectado conversaciones", embed.description)

    async def test_generate_call_summary_with_dialogue(self):
        """Verifica que con diálogo real genera la crónica estructurada con participantes, puntos clave y frase."""
        now = time.time()
        simulated_turns = [
            {"epoch": now - 1800, "user": "Jose", "timestamp": "2026-10-25 14:00:00", "transcription": "Buenas gente, ¿echamos un Valorant?"},
            {"epoch": now - 1500, "user": "David", "timestamp": "2026-10-25 14:05:00", "transcription": "Dale, me pillo a Reyna."},
            {"epoch": now - 1200, "user": "Jose", "timestamp": "2026-10-25 14:10:00", "transcription": "Vaya clutch que te has marcado."},
            {"epoch": now - 900, "user": "Jose", "timestamp": "2026-10-25 14:15:00", "transcription": "GG partida ganada."},
        ]

        # Test con fallback determinista (sin red hacia Gemini)
        with patch.object(voz, "VOICE_TURNS_LOG", simulated_turns), \
             patch.object(voz, "_bs", return_value=MagicMock(get_available_models=lambda: [], GEMINI_KEY="")):
            embed = await voz.generate_call_summary(hours=1.0, channel_name="gaming-room")

            self.assertIsInstance(embed, discord.Embed)
            self.assertIn("gaming-room", embed.title)
            self.assertIn("Participantes y Actividad", embed.description)
            self.assertIn("Jose", embed.description)
            self.assertIn("David", embed.description)
            self.assertIn("Puntos Clave", embed.description)
            self.assertIn("Momento o Frase Destacada", embed.description)
            self.assertIn("4 intervenciones", embed.footer.text)
            self.assertIn("Jose", embed.footer.text)


class TestSlashCommandRegistration(unittest.TestCase):
    """Pruebas del registro de /resumen_llamada en árboles y módulos de comandos."""

    def test_command_exists_in_generales(self):
        """Verifica que cmd_resumen_llamada esté definido y presente en GENERAL_SLASH_COMMANDS."""
        self.assertTrue(hasattr(comandos_generales, "cmd_resumen_llamada"))
        self.assertIn(comandos_generales.cmd_resumen_llamada, comandos_generales.GENERAL_SLASH_COMMANDS)
        self.assertEqual(len(comandos_generales.GENERAL_SLASH_COMMANDS), 24)

    def test_command_reexported_in_comandos(self):
        """Verifica que cmd_resumen_llamada esté reexportado en la fachada modulos/comandos.py."""
        self.assertTrue(hasattr(comandos, "cmd_resumen_llamada"))
        self.assertIn(comandos.cmd_resumen_llamada, comandos.ALL_SLASH_COMMANDS)
        self.assertEqual(len(comandos.ALL_SLASH_COMMANDS), len(comandos.GENERAL_SLASH_COMMANDS) + len(comandos.ECONOMY_SLASH_COMMANDS))

    def test_register_in_command_tree(self):
        """Verifica que el comando se registra sin excepciones en un CommandTree de Discord."""
        client = discord.Client(intents=discord.Intents.default())
        tree = app_commands.CommandTree(client)
        comandos_generales.register_general_commands(tree)
        registered_names = [c.name for c in tree.get_commands()]
        self.assertIn("resumen_llamada", registered_names)


if __name__ == "__main__":
    unittest.main()
