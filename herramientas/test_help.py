"""
Suite de Pruebas Unitarias para el Comando Interactivo /help y Estados de Presencia:
1. Existencia e integridad de /help en GENERAL_SLASH_COMMANDS y CommandTree.
2. Construcción correcta del Embed General de Bienvenida (título, descripción, campos, footer).
3. Generación exhaustiva de los Embeds para las 5 categorías ('ia', 'voz', 'bolsa', 'casino', 'comunidad').
4. Validación de componentes interactivos HelpSelect y HelpView (5 opciones, placeholders, callbacks).
"""

import os
import sys
import unittest
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
from discord import app_commands
from modulos.comandos_generales import (
    cmd_help,
    GENERAL_SLASH_COMMANDS,
    register_general_commands,
    build_help_embed,
    HelpSelect,
    HelpView,
    HELP_CATEGORIES_INFO,
)


class TestHelpCommand(unittest.TestCase):
    """Pruebas unitarias completas del comando /help y sus componentes."""

    def test_01_cmd_help_registration(self):
        """Verifica que cmd_help existe, es un Command y está en GENERAL_SLASH_COMMANDS."""
        self.assertIsNotNone(cmd_help)
        self.assertEqual(cmd_help.name, "help")
        self.assertIn(cmd_help, GENERAL_SLASH_COMMANDS)

        # Probar registro en CommandTree simulado
        client = discord.Client(intents=discord.Intents.default())
        tree = app_commands.CommandTree(client)
        register_general_commands(tree)
        registered = tree.get_command("help")
        self.assertIsNotNone(registered)
        self.assertEqual(registered.name, "help")

    def test_02_build_general_embed(self):
        """Verifica que el embed inicial se construye con título, descripción y campos correctos."""
        embed = build_help_embed(None)
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Centro de Comandos y Asistencia", embed.title)
        self.assertTrue(len(embed.description) > 20)
        self.assertEqual(len(embed.fields), 5)

        field_names = [f.name for f in embed.fields]
        self.assertTrue(any("IA" in name for name in field_names))
        self.assertTrue(any("Voz" in name for name in field_names))
        self.assertTrue(any("Bolsa" in name for name in field_names))
        self.assertTrue(any("Casino" in name for name in field_names))
        self.assertTrue(any("Comunidad" in name for name in field_names))

        self.assertIsNotNone(embed.footer.text)
        self.assertIn("efímera", embed.footer.text.lower())

    def test_03_build_category_embeds(self):
        """Verifica que cada una de las 5 categorías genera su embed con campos y límites válidos."""
        expected_categories = ["ia", "voz", "bolsa", "casino", "comunidad"]
        self.assertEqual(set(HELP_CATEGORIES_INFO.keys()), set(expected_categories))

        for cat in expected_categories:
            embed = build_help_embed(cat)
            self.assertIsInstance(embed, discord.Embed)
            self.assertTrue(len(embed.title) > 0)
            self.assertTrue(len(embed.description) > 0)
            self.assertTrue(len(embed.fields) >= 4, f"Categoría {cat} tiene menos de 4 comandos")

            # Comprobar que HelpView.build_embed devuelve lo mismo
            embed_view = HelpView.build_embed(cat)
            self.assertEqual(embed.title, embed_view.title)
            self.assertEqual(len(embed.fields), len(embed_view.fields))

            # Comprobar límites de Discord
            self.assertLessEqual(len(embed.title), 256)
            self.assertLessEqual(len(embed.description), 4096)
            for f in embed.fields:
                self.assertLessEqual(len(f.name), 256)
                self.assertLessEqual(len(f.value), 1024)

    def test_04_help_select_and_view(self):
        """Verifica que HelpSelect tiene 5 opciones válidas y se integra en HelpView."""
        view = HelpView(timeout=180.0)
        self.assertEqual(len(view.children), 1)
        select = view.children[0]
        self.assertIsInstance(select, HelpSelect)
        self.assertEqual(len(select.options), 5)

        option_values = [opt.value for opt in select.options]
        self.assertEqual(option_values, ["ia", "voz", "bolsa", "casino", "comunidad"])

    def test_05_help_select_callback(self):
        """Simula una interacción al seleccionar una categoría y verifica que edita el mensaje."""
        select = HelpSelect()
        view = HelpView()
        select._view = view

        select._values = ["bolsa"]
        interaction_mock = MagicMock(spec=discord.Interaction)
        interaction_mock.response = MagicMock()
        interaction_mock.response.edit_message = AsyncMock()

        import asyncio
        asyncio.run(select.callback(interaction_mock))

        interaction_mock.response.edit_message.assert_called_once()
        call_kwargs = interaction_mock.response.edit_message.call_args[1]
        self.assertIn("embed", call_kwargs)
        self.assertIn("Bolsa", call_kwargs["embed"].title)


if __name__ == "__main__":
    unittest.main()
