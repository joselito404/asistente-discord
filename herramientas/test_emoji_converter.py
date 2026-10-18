"""
Suite de Pruebas Unitarias para el Auto-Conversor de Emojis del Servidor.
Valida:
1. Conversión de emojis estáticos y animados vía catálogo canónico (:aura:, :Porro:, :gigachad:, :KEKWLaugh:, etc.).
2. Insensibilidad a mayúsculas/minúsculas (:porro: -> <:Porro:ID>).
3. Protección de bloques de código markdown (inline y multilínea).
4. No duplicación de menciones ya formateadas (<:aura:ID> o <a:KEKWLaugh:ID>).
5. Integración en tiempo real con guild.emojis y control de estado 'available':
   - Emojis activos (available=True) -> Mención nativa de Discord.
   - Emojis deshabilitados por pérdida de Server Boost (available=False) -> Fallback seguro a emoji base / Unicode.
6. Texto mixto con horas y dos puntos no-emojis.
7. Integridad exhaustiva del catálogo de 124 emojis (98 estáticos, 26 animados).
"""

import sys
import os
import unittest
from types import SimpleNamespace

# Asegurar path para importar modulos y bot_service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.chat_ia import (
    SERVER_EMOJIS_DATA,
    DISABLED_EMOJI_FALLBACK,
    format_server_emojis,
)


class MockDiscordEmoji:
    """Mock ligero de un objeto discord.Emoji."""
    def __init__(self, name: str, emoji_id: int, animated: bool = False, available: bool = True):
        self.name = name
        self.id = emoji_id
        self.animated = animated
        self.available = available

    def __str__(self):
        prefix = "a" if self.animated else ""
        return f"<{prefix}:{self.name}:{self.id}>"


class MockGuild:
    """Mock ligero de un objeto discord.Guild."""
    def __init__(self, emojis):
        self.emojis = emojis


class TestEmojiConverter(unittest.TestCase):

    def test_catalog_integrity(self):
        """Verifica que el catálogo contiene exactamente los 124 emojis del servidor."""
        self.assertEqual(len(SERVER_EMOJIS_DATA), 124)
        static = [v for v in SERVER_EMOJIS_DATA.values() if not v["animated"]]
        animated = [v for v in SERVER_EMOJIS_DATA.values() if v["animated"]]
        self.assertEqual(len(static), 98)
        self.assertEqual(len(animated), 26)

        # Primeros 50 estáticos son seguros (Free Tier), 48 restantes en riesgo
        safe_static = [v for v in static if v["is_safe"]]
        at_risk_static = [v for v in static if not v["is_safe"]]
        self.assertEqual(len(safe_static), 50)
        self.assertEqual(len(at_risk_static), 48)

        # Todos los animados son seguros (límite free es 50 y solo hay 26)
        self.assertTrue(all(v["is_safe"] for v in animated))

        # Todos los 48 en riesgo deben tener fallback configurado
        for v in at_risk_static:
            k = v["name"].lower()
            self.assertIn(k, DISABLED_EMOJI_FALLBACK, f"Emoji en riesgo sin fallback: {k}")

    def test_basic_conversion_offline(self):
        """Verifica conversión directa sin guild usando el catálogo canónico."""
        # Estáticos icónicos
        self.assertEqual(format_server_emojis(":aura:"), "<:aura:1535728704129466462>")
        self.assertEqual(format_server_emojis(":Porro:"), "<:Porro:1535685303317172305>")
        self.assertEqual(format_server_emojis(":gigachad:"), "<:gigachad:1535682070536519730>")
        self.assertEqual(format_server_emojis(":absolutecinema:"), "<:absolutecinema:1478115607336714300>")
        self.assertEqual(format_server_emojis(":Messirve:"), "<:Messirve:1535726367847743528>")
        self.assertEqual(format_server_emojis(":cooked:"), "<:cooked:1535726716901789726>")
        self.assertEqual(format_server_emojis(":skillissue:"), "<:skillissue:1535727329156931624>")
        self.assertEqual(format_server_emojis(":Ranked_Masters:"), "<:Ranked_Masters:1550129992837496833>")

        # Animados
        self.assertEqual(format_server_emojis(":KEKWLaugh:"), "<a:KEKWLaugh:1535679941059018903>")
        self.assertEqual(format_server_emojis(":Thisisfine:"), "<a:Thisisfine:1535679070312857672>")
        self.assertEqual(format_server_emojis(":chadgif:"), "<a:chadgif:1535680346199162982>")

    def test_case_insensitivity(self):
        """Verifica que el bot puede escribir en minúsculas y se resuelve el nombre canónico exacto."""
        self.assertEqual(format_server_emojis(":porro:"), "<:Porro:1535685303317172305>")
        self.assertEqual(format_server_emojis(":messirve:"), "<:Messirve:1535726367847743528>")
        self.assertEqual(format_server_emojis(":kekwlaugh:"), "<a:KEKWLaugh:1535679941059018903>")
        self.assertEqual(format_server_emojis(":thisisfine:"), "<a:Thisisfine:1535679070312857672>")
        self.assertEqual(format_server_emojis(":sigma_male_bale:"), "<:Sigma_Male_Bale:1535677801808535702>")

    def test_code_block_protection(self):
        """Verifica que los emojis dentro de bloques de código no se alteran."""
        # Inline code
        text_inline = "Usa el comando `print(':aura:')` para testear :gigachad:"
        expected_inline = "Usa el comando `print(':aura:')` para testear <:gigachad:1535682070536519730>"
        self.assertEqual(format_server_emojis(text_inline), expected_inline)

        # Multiline code block
        text_block = "Mira este bloque:\n```python\n# :Porro:\nvalue = ':aura:'\n```\n¡Y aquí fuera sí :Porro:!"
        expected_block = "Mira este bloque:\n```python\n# :Porro:\nvalue = ':aura:'\n```\n¡Y aquí fuera sí <:Porro:1535685303317172305>!"
        self.assertEqual(format_server_emojis(text_block), expected_block)

    def test_preformatted_emojis_not_corrupted(self):
        """Verifica que los emojis que ya están en formato Discord no sufren doble reemplazo."""
        already_formatted = "Ya tengo <:aura:1535728704129466462> y <a:KEKWLaugh:1535679941059018903> aquí."
        self.assertEqual(format_server_emojis(already_formatted), already_formatted)

        mixed = "Mezclado: <:aura:1535728704129466462> con :Porro: y <a:KEKWLaugh:1535679941059018903>"
        expected_mixed = "Mezclado: <:aura:1535728704129466462> con <:Porro:1535685303317172305> y <a:KEKWLaugh:1535679941059018903>"
        self.assertEqual(format_server_emojis(mixed), expected_mixed)

    def test_live_guild_active_boost(self):
        """Verifica resolución en tiempo real cuando el servidor tiene Boost activo (available=True)."""
        mock_emojis = [
            MockDiscordEmoji("aura", 1535728704129466462, animated=False, available=True),
            MockDiscordEmoji("Porro", 1535685303317172305, animated=False, available=True),
            MockDiscordEmoji("KEKWLaugh", 1535679941059018903, animated=True, available=True),
        ]
        guild = MockGuild(mock_emojis)

        result = format_server_emojis("¡Qué locura :aura: :porro: :KEKWLaugh:!", guild=guild)
        expected = "¡Qué locura <:aura:1535728704129466462> <:Porro:1535685303317172305> <a:KEKWLaugh:1535679941059018903>!"
        self.assertEqual(result, expected)

    def test_live_guild_boost_expired_fallback(self):
        """
        Prueba crítica: Simula la expiración de las mejoras de Jose.
        Discord marca 'available=False' en slots 51-98.
        El conversor debe interceptar y sustituir por el fallback seguro, nunca dejar texto roto.
        """
        mock_emojis = [
            # Slot 85 (En riesgo, ahora deshabilitado por falta de Boost)
            MockDiscordEmoji("aura", 1535728704129466462, animated=False, available=False),
            # Slot 58 (En riesgo, ahora deshabilitado)
            MockDiscordEmoji("Porro", 1535685303317172305, animated=False, available=False),
            # Slot 76 (En riesgo, ahora deshabilitado)
            MockDiscordEmoji("cooked", 1535726716901789726, animated=False, available=False),
            # Slot 33 (Seguro, slot 33 < 50, sigue disponible)
            MockDiscordEmoji("gigachad", 1535682070536519730, animated=False, available=True),
            # Animado (Seguro, 26 < 50, sigue disponible)
            MockDiscordEmoji("KEKWLaugh", 1535679941059018903, animated=True, available=True),
        ]
        guild = MockGuild(mock_emojis)

        text = "Vaya momento :aura:, estamos :cooked:, saca el :Porro:, mira al :gigachad: :KEKWLaugh:"
        result = format_server_emojis(text, guild=guild)

        # :aura: debe caer a fallback seguro (<:gigachad:...>)
        # :cooked: debe caer a fallback seguro (💀)
        # :Porro: debe caer a fallback seguro (🚬)
        # :gigachad: sigue activo en Discord (<:gigachad:...>)
        # :KEKWLaugh: sigue activo en Discord (<a:KEKWLaugh:...>)
        expected = (
            "Vaya momento <:gigachad:1535682070536519730>, estamos 💀, saca el 🚬, "
            "mira al <:gigachad:1535682070536519730> <a:KEKWLaugh:1535679941059018903>"
        )
        self.assertEqual(result, expected)

    def test_non_emoji_colons_intact(self):
        """Verifica que números y dos puntos no relacionados con emojis quedan intactos."""
        text = "Son las 12:30 de la noche y el ratio es 16:9 con :not_an_emoji: y :gigachad:"
        expected = "Son las 12:30 de la noche y el ratio es 16:9 con :not_an_emoji: y <:gigachad:1535682070536519730>"
        self.assertEqual(format_server_emojis(text), expected)

    def test_edge_cases(self):
        """Verifica entradas vacías o tipos no esperados."""
        self.assertEqual(format_server_emojis(""), "")
        self.assertEqual(format_server_emojis(None), None)
        self.assertEqual(format_server_emojis(123), 123)


if __name__ == "__main__":
    unittest.main()
