"""
Suite de Validación Exhaustiva de The Sanvi Daily / Starboard Gráfico 2.0.
Especificación técnica: docs/DISENO_SANVI_DAILY.md

Pruebas cubiertas:
1. Renderizado visual con Pillow:
   - Formato de salida PNG válido.
   - Dimensiones exactas 800 x 1000 px.
   - Portada con texto corto, largo y vacío.
   - Portada con avatar de autor simulado y sin él.
   - Portada con imagen fotográfica adjunta y sin ella.
2. Persistencia atómica de starboard.json:
   - Estructura JSON y escritura atómica con Lock.
3. Lógica de activación, filtros y anti-autobombo:
   - Ignorar canales excluidos (#⭐muro-de-la-fama⭐, backup, apps-solo-mods, staff).
   - Ignorar emojis que no sean ⭐.
   - Descarte estricto de auto-votos (anti-autobombo).
   - Umbral de 2 estrellas: con 1 estrella válida no entra; con 2 estrellas entra.
4. Idempotencia:
   - Re-reacciones al mismo mensaje no imprimen nuevas portadas ni duplican entradas.
   - Se actualiza el embed en Discord si varía el número de estrellas.
5. Permanencia irrevocable:
   - Retirar estrellas (reaction_remove) por debajo de 2 no elimina la portada ni la entrada.
"""

import os
import io
import sys
import json
import tempfile
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from PIL import Image

# Añadir raíz al sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import modulos.starboard as sb_mod
from modulos.starboard import (
    render_sanvi_daily_cover,
    load_starboard_data,
    save_starboard_data,
    handle_starboard_reaction_add,
    handle_starboard_reaction_remove,
    STARBOARD_CHANNEL_ID,
    STAR_EMOJI,
    MIN_STARS_THRESHOLD,
    EXCLUDED_CHANNEL_IDS,
)


def _create_dummy_image_bytes(width: int = 100, height: int = 100, color: str = "blue") -> bytes:
    """Crea una imagen PNG en memoria para pruebas."""
    img = Image.new("RGBA", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestStarboardRender(unittest.TestCase):
    """Validación del renderizador visual con Pillow (The Sanvi Daily)."""

    def test_01_render_basic_dimensions_and_format(self):
        """Valida que la portada sea un PNG válido con dimensiones exactas 800x1000."""
        png_bytes = render_sanvi_daily_cover(
            author_name="Joselito",
            author_avatar_bytes=None,
            content="¡Vaya locura de partida ayer!",
            created_at_str="22/10/2026 21:00 UTC",
            edition_num=1,
            stars_count=2,
            attachment_bytes=None,
        )

        self.assertTrue(png_bytes.startswith(b"\x89PNG\r\n\x1a\n"), "La salida debe ser un PNG válido")
        img = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(img.size, (800, 1000), "Las dimensiones deben ser exactamente 800x1000 px")

    def test_02_render_with_avatar_and_attachment(self):
        """Valida que la portada procese correctamente avatar del autor e imagen adjunta sepia."""
        avatar_bytes = _create_dummy_image_bytes(128, 128, color="red")
        attachment_bytes = _create_dummy_image_bytes(400, 300, color="green")

        png_bytes = render_sanvi_daily_cover(
            author_name="SuperStar",
            author_avatar_bytes=avatar_bytes,
            content="Declaración histórica con prueba fotográfica adjunta.",
            created_at_str="22/10/2026 21:05 UTC",
            edition_num=42,
            stars_count=5,
            attachment_bytes=attachment_bytes,
        )

        self.assertTrue(png_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
        img = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(img.size, (800, 1000))

    def test_03_render_long_text_and_empty_text(self):
        """Valida que textos muy largos se ajusten con comillas sin desbordar ni fallar."""
        long_content = "Palabra " * 150
        png_bytes_long = render_sanvi_daily_cover(
            author_name="Charlatan",
            author_avatar_bytes=None,
            content=long_content,
            created_at_str="22/10/2026 21:10 UTC",
            edition_num=2,
            stars_count=3,
        )
        self.assertTrue(png_bytes_long.startswith(b"\x89PNG\r\n\x1a\n"))

        png_bytes_empty = render_sanvi_daily_cover(
            author_name="Mudo",
            author_avatar_bytes=None,
            content="",
            created_at_str="22/10/2026 21:12 UTC",
            edition_num=3,
            stars_count=2,
        )
        self.assertTrue(png_bytes_empty.startswith(b"\x89PNG\r\n\x1a\n"))


class TestStarboardLogic(unittest.IsolatedAsyncioTestCase):
    """Validación de reglas de negocio, anti-autobombo, umbrales e idempotencia."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_json_path = os.path.join(self.temp_dir.name, "starboard_test.json")
        self.patch_path = patch.object(sb_mod, "STARBOARD_DATA_PATH", self.test_json_path)
        self.patch_path.start()

    def tearDown(self):
        self.patch_path.stop()
        self.temp_dir.cleanup()

    def test_04_persistence_atomic_read_write(self):
        """Valida la carga y guardado atómico de datos de starboard."""
        initial = load_starboard_data()
        self.assertEqual(initial["next_edition_number"], 1)
        self.assertEqual(initial["entries"], {})

        initial["next_edition_number"] = 2
        initial["entries"]["test_key"] = {"edition_number": 1, "stars_count": 2}
        save_starboard_data(initial)

        reloaded = load_starboard_data()
        self.assertEqual(reloaded["next_edition_number"], 2)
        self.assertIn("test_key", reloaded["entries"])

    async def test_05_ignore_excluded_channels_and_wrong_emojis(self):
        """Valida que reacciones en canales excluidos o con otros emojis sean ignoradas."""
        bot = MagicMock()
        bot.get_channel = MagicMock()

        # Emoji incorrecto (ej: 👍)
        payload_wrong_emoji = MagicMock()
        payload_wrong_emoji.emoji = "👍"
        payload_wrong_emoji.channel_id = 999999
        await handle_starboard_reaction_add(payload_wrong_emoji, bot)
        bot.get_channel.assert_not_called()

        # Canal excluido (ej: #⭐muro-de-la-fama⭐)
        payload_excluded = MagicMock()
        payload_excluded.emoji = STAR_EMOJI
        payload_excluded.channel_id = STARBOARD_CHANNEL_ID
        await handle_starboard_reaction_add(payload_excluded, bot)
        bot.get_channel.assert_not_called()

    async def test_06_anti_self_star_and_threshold(self):
        """Valida que la estrella del autor no cuente y que el umbral sea estrictamente 2 estrellas válidas."""
        bot = MagicMock()
        channel = AsyncMock()
        bot.get_channel.return_value = channel

        # Autor del mensaje ID 100
        author = MagicMock()
        author.id = 100
        author.name = "AutorCélebre"
        author.display_name = "Autor Célebre"
        author.display_avatar.read = AsyncMock(return_value=b"fake_avatar")

        message = MagicMock()
        message.id = 500
        message.channel = channel
        message.channel.id = 777
        message.author = author
        message.content = "Mensaje histórico"
        message.created_at = datetime.now(timezone.utc)
        message.jump_url = "https://discord.com/channels/1/777/500"
        message.attachments = []

        channel.fetch_message = AsyncMock(return_value=message)

        # Canal de destino Starboard
        sb_channel = AsyncMock()
        sb_channel.name = "⭐muro-de-la-fama⭐"
        sent_msg = MagicMock()
        sent_msg.id = 88888
        sb_channel.send = AsyncMock(return_value=sent_msg)

        # Caso A: Solo el autor reacciona a su propio mensaje (1 estrella, pero es suya)
        user_author = MagicMock(id=100)
        reaction_self = MagicMock()
        reaction_self.emoji = STAR_EMOJI

        async def _users_self():
            yield user_author

        reaction_self.users = _users_self
        message.reactions = [reaction_self]

        payload = MagicMock()
        payload.emoji = STAR_EMOJI
        payload.channel_id = 777
        payload.message_id = 500

        await handle_starboard_reaction_add(payload, bot)
        # No debe enviar nada a Starboard
        sb_channel.send.assert_not_called()
        data = load_starboard_data()
        self.assertEqual(len(data["entries"]), 0)

        # Caso B: El autor + 1 usuario externo (2 estrellas en total, pero solo 1 válida)
        user_external_1 = MagicMock(id=201)

        async def _users_1_valid():
            yield user_author
            yield user_external_1

        reaction_self.users = _users_1_valid
        await handle_starboard_reaction_add(payload, bot)
        # Sigue sin alcanzar el umbral mínimo de 2 estrellas válidas
        sb_channel.send.assert_not_called()
        self.assertEqual(len(load_starboard_data()["entries"]), 0)

        # Caso C: El autor + 2 usuarios externos (3 estrellas en total, 2 estrellas válidas) -> ¡PUBLICA!
        user_external_2 = MagicMock(id=202)

        async def _users_2_valid():
            yield user_author
            yield user_external_1
            yield user_external_2

        reaction_self.users = _users_2_valid

        # Configurar retorno para get_channel de STARBOARD_CHANNEL_ID
        def _get_channel_side_effect(cid):
            if cid == 777:
                return channel
            elif cid == STARBOARD_CHANNEL_ID:
                return sb_channel
            return None

        bot.get_channel.side_effect = _get_channel_side_effect

        await handle_starboard_reaction_add(payload, bot)

        # Debe haberse publicado la Edición Nº 1
        sb_channel.send.assert_called_once()
        data = load_starboard_data()
        self.assertEqual(data["next_edition_number"], 2)
        entry_key = "777_500"
        self.assertIn(entry_key, data["entries"])
        entry = data["entries"][entry_key]
        self.assertEqual(entry["edition_number"], 1)
        self.assertEqual(entry["stars_count"], 2)
        self.assertEqual(entry["starboard_message_id"], 88888)

    async def test_07_idempotence_and_re_reaction(self):
        """Valida que si un mensaje ya publicado recibe una 3ª estrella, se edita y no se duplica."""
        bot = MagicMock()
        channel = AsyncMock()
        channel.id = 777

        author = MagicMock(id=100, name="Pepe", display_name="Pepe")
        message = MagicMock(
            id=501,
            channel=channel,
            author=author,
            content="Célebre frase",
            created_at=datetime.now(timezone.utc),
            jump_url="https://url",
            attachments=[],
        )
        channel.fetch_message = AsyncMock(return_value=message)

        # Simular que ya está en starboard.json con 2 estrellas
        initial_data = {
            "next_edition_number": 3,
            "entries": {
                "777_501": {
                    "edition_number": 2,
                    "orig_channel_id": 777,
                    "orig_message_id": 501,
                    "starboard_message_id": 99999,
                    "author_id": 100,
                    "author_name": "Pepe",
                    "stars_count": 2,
                    "stargazers": [201, 202],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "has_image": False,
                }
            },
        }
        save_starboard_data(initial_data)

        # Mensaje ya publicado en discord
        sb_channel = AsyncMock()
        existing_sb_msg = AsyncMock()
        embed_mock = MagicMock()
        existing_sb_msg.embeds = [embed_mock]
        sb_channel.fetch_message = AsyncMock(return_value=existing_sb_msg)

        def _get_ch(cid):
            if cid == 777:
                return channel
            if cid == STARBOARD_CHANNEL_ID:
                return sb_channel
            return None

        bot.get_channel.side_effect = _get_ch

        # Ahora el mensaje tiene 3 usuarios externos que han reaccionado
        async def _users_3():
            yield MagicMock(id=201)
            yield MagicMock(id=202)
            yield MagicMock(id=203)

        reaction = MagicMock(emoji=STAR_EMOJI, users=_users_3)
        message.reactions = [reaction]

        payload = MagicMock(emoji=STAR_EMOJI, channel_id=777, message_id=501)
        await handle_starboard_reaction_add(payload, bot)

        # No debe haber hecho un nuevo send en sb_channel
        sb_channel.send.assert_not_called()
        # Debe haber editado existing_sb_msg
        existing_sb_msg.edit.assert_called_once()
        embed_mock.set_footer.assert_called_with(text="Edición Nº 2 • Inmortalizado con 3 ⭐")

        # El JSON debe haberse actualizado a 3 estrellas sin variar next_edition_number
        data = load_starboard_data()
        self.assertEqual(data["next_edition_number"], 3)
        self.assertEqual(data["entries"]["777_501"]["stars_count"], 3)
        self.assertEqual(len(data["entries"]["777_501"]["stargazers"]), 3)

    async def test_08_permanence_on_reaction_remove(self):
        """Valida que retirar estrellas no elimine la portada del canal ni de la persistencia."""
        bot = MagicMock()
        channel = AsyncMock()
        channel.id = 777

        author = MagicMock(id=100, name="Pepe", display_name="Pepe")
        message = MagicMock(
            id=502,
            channel=channel,
            author=author,
            content="Frase que perdió votos",
            created_at=datetime.now(timezone.utc),
            jump_url="https://url",
            attachments=[],
        )
        channel.fetch_message = AsyncMock(return_value=message)

        # Simular entrada existente en starboard.json con 2 estrellas
        save_starboard_data({
            "next_edition_number": 4,
            "entries": {
                "777_502": {
                    "edition_number": 3,
                    "orig_channel_id": 777,
                    "orig_message_id": 502,
                    "starboard_message_id": 11111,
                    "author_id": 100,
                    "author_name": "Pepe",
                    "stars_count": 2,
                    "stargazers": [201, 202],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "has_image": False,
                }
            }
        })

        sb_channel = AsyncMock()
        existing_sb_msg = AsyncMock()
        embed_mock = MagicMock()
        existing_sb_msg.embeds = [embed_mock]
        existing_sb_msg.delete = AsyncMock()
        sb_channel.fetch_message = AsyncMock(return_value=existing_sb_msg)

        def _get_ch(cid):
            if cid == 777:
                return channel
            if cid == STARBOARD_CHANNEL_ID:
                return sb_channel
            return None

        bot.get_channel.side_effect = _get_ch

        # Un usuario retira la estrella, queda solo 1 stargazer
        async def _users_1():
            yield MagicMock(id=201)

        reaction = MagicMock(emoji=STAR_EMOJI, users=_users_1)
        message.reactions = [reaction]

        payload = MagicMock(emoji=STAR_EMOJI, channel_id=777, message_id=502)
        await handle_starboard_reaction_remove(payload, bot)

        # PERMANENCIA: El mensaje NUNCA debe ser eliminado
        existing_sb_msg.delete.assert_not_called()
        # Debe haber editado el embed reflejando la nueva cifra
        existing_sb_msg.edit.assert_called_once()
        embed_mock.set_footer.assert_called_with(text="Edición Nº 3 • Inmortalizado con 1 ⭐")

        # La entrada permanece en starboard.json
        data = load_starboard_data()
        self.assertIn("777_502", data["entries"])
        self.assertEqual(data["entries"]["777_502"]["stars_count"], 1)

    async def test_09_bot_slots_interaction_and_components_v2(self):
        """Valida que mensajes de bot con componentes V2 (slots) atribuyan la autoría al usuario real y extraigan el texto."""
        from modulos.starboard import _resolve_message_author, _extract_message_text, _clean_discord_text

        # 1. Simular bot y usuario humano real (Joselito)
        bot_author = MagicMock()
        bot_author.id = 999000
        bot_author.bot = True
        bot_author.name = "Economia Asistente"
        bot_author.display_name = "ECONOMIA ASISTENTE"

        human_user = MagicMock()
        human_user.id = 123456
        human_user.bot = False
        human_user.name = "Joselito"
        human_user.display_name = "Joselito"
        human_user.display_avatar.read = AsyncMock(return_value=b"fake_human_avatar")

        # 2. Simular estructura de componentes V2 de slots (/slots)
        comp_title = MagicMock()
        comp_title.type = 10  # TextDisplay
        comp_title.content = "### 🎰 TRAGAPERRAS 5×3 — ¡PREMIO!"

        comp_body = MagicMock()
        comp_body.type = 10  # TextDisplay
        comp_body.content = "🍋 🍋 🍋 🍋 🍋\n**Línea Ganadora:** • 🍋 Centro (×10)\n**Premio Total:** 50,000 Porros"

        container = MagicMock()
        container.type = 17  # Container
        container.components = [comp_title, comp_body]

        action_button = MagicMock()
        action_button.type = 2  # Button
        action_button.custom_id = "slots:play-again:100:123456"

        # Mensaje de Discord generado por el bot vía interacción de Joselito
        channel = AsyncMock()
        channel.id = 777
        channel.name = "casino-y-apuestas"

        message = MagicMock()
        message.id = 600
        message.channel = channel
        message.author = bot_author
        message.interaction = MagicMock()
        message.interaction.user = human_user
        message.content = ""  # En Components V2 content es vacío
        message.components = [container]
        message.embeds = []
        message.attachments = []
        message.created_at = datetime.now(timezone.utc)
        message.jump_url = "https://discord.com/channels/1/777/600"

        # A) Verificación unitaria de _resolve_message_author
        resolved_author = _resolve_message_author(message)
        self.assertEqual(resolved_author.id, 123456, "Debe resolver al usuario humano real de la interacción")
        self.assertEqual(resolved_author.display_name, "Joselito")

        # B) Verificación unitaria de _extract_message_text
        extracted_text = _extract_message_text(message)
        self.assertIn("TRAGAPERRAS 5×3", extracted_text)
        self.assertIn("50,000 Porros", extracted_text)
        self.assertNotIn("(Mensaje sin texto adjunto", extracted_text)

        # C) Verificación de sanitización tipográfica para la portada
        cleaned = _clean_discord_text(extracted_text)
        self.assertNotIn("###", cleaned, "Debe retirar encabezados markdown")
        self.assertNotIn("**", cleaned, "Debe retirar marcas de negrita")
        self.assertIn("TRAGAPERRAS 5×3 — ¡PREMIO!", cleaned)

        # D) Integración reactiva en handle_starboard_reaction_add
        bot = MagicMock()
        channel.fetch_message = AsyncMock(return_value=message)

        sb_channel = AsyncMock()
        sb_channel.name = "⭐muro-de-la-fama⭐"
        sent_sb_msg = MagicMock()
        sent_sb_msg.id = 77777
        sb_channel.send = AsyncMock(return_value=sent_sb_msg)

        def _get_ch(cid):
            if cid == 777:
                return channel
            if cid == STARBOARD_CHANNEL_ID:
                return sb_channel
            return None

        bot.get_channel.side_effect = _get_ch

        # Anti-autobombo: La estrella de Joselito (el ganador) NO cuenta
        user_joselito = MagicMock(id=123456)
        user_fan1 = MagicMock(id=301)
        user_fan2 = MagicMock(id=302)

        async def _users_with_self():
            yield user_joselito
            yield user_fan1

        reaction = MagicMock(emoji=STAR_EMOJI, users=_users_with_self)
        message.reactions = [reaction]

        payload = MagicMock(emoji=STAR_EMOJI, channel_id=777, message_id=600)
        await handle_starboard_reaction_add(payload, bot)
        sb_channel.send.assert_not_called()  # Solo 1 estrella válida (la de Joselito no cuenta)

        # Con 2 estrellas de fans externos (3 en total contando a Joselito), se publica
        async def _users_threshold():
            yield user_joselito
            yield user_fan1
            yield user_fan2

        reaction.users = _users_threshold
        await handle_starboard_reaction_add(payload, bot)

        sb_channel.send.assert_called_once()
        _, kwargs = sb_channel.send.call_args
        embed_sent = kwargs["embed"]

        # Validar que el embed atribuye la autoría a Joselito y no a Economia Asistente
        self.assertIn("<@123456>", embed_sent.description)
        self.assertNotIn("<@999000>", embed_sent.description)

        # Validar persistencia atómica con el autor humano
        data = load_starboard_data()
        self.assertIn("777_600", data["entries"])
        entry = data["entries"]["777_600"]
        self.assertEqual(entry["author_id"], 123456)
        self.assertEqual(entry["author_name"], "Joselito")
        self.assertEqual(entry["stars_count"], 2)


if __name__ == "__main__":
    unittest.main()
