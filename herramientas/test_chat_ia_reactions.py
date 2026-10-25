"""
Tests unitarios para el sistema de reacciones dinámicas con emojis en Chat IA (Área 2):
- Extracción limpia y limitada a 1 de etiquetas [ACTION_REACT: ...] (extract_reaction_tag).
- Resolución resiliente de emojis Unicode, menciones de servidor activas y fallbacks unitarios (resolve_reaction_emoji).
- Ejecución asíncrona en _handle_message_safe con fallback automático ante excepción de Discord.
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.chat_ia import (
    REACTION_SINGLE_UNICODE_FALLBACK,
    extract_reaction_tag,
    resolve_reaction_emoji,
    _handle_message_safe,
)


class DummyEmoji:
    def __init__(self, name: str, eid: int, animated: bool = False, available: bool = True):
        self.name = name
        self.id = eid
        self.animated = animated
        self.available = available


class DummyGuild:
    def __init__(self, emojis):
        self.emojis = emojis
        self.id = 111
        self.name = "Sanvi"
        self.member_count = 50
        self.voice_channels = []
        self.text_channels = []
        self.members = []
        self.voice_client = None

    def get_member(self, uid):
        return None


class TestChatIAReactions(unittest.TestCase):
    def test_extract_reaction_tag_no_tag(self):
        text = "Hola colega, todo bien por aquí."
        clean, raw_react = extract_reaction_tag(text)
        self.assertEqual(clean, text)
        self.assertIsNone(raw_react)

    def test_extract_reaction_tag_single_colon_emoji(self):
        text = "Jajaja qué grande eres [ACTION_REACT: :pensando:]"
        clean, raw_react = extract_reaction_tag(text)
        self.assertEqual(clean, "Jajaja qué grande eres")
        self.assertEqual(raw_react, ":pensando:")

    def test_extract_reaction_tag_single_unicode_emoji(self):
        text = "Vaya fumada te acabas de marcar [ACTION_REACT: 🤔]"
        clean, raw_react = extract_reaction_tag(text)
        self.assertEqual(clean, "Vaya fumada te acabas de marcar")
        self.assertEqual(raw_react, "🤔")

    def test_extract_reaction_tag_multiple_tags_keeps_only_first(self):
        text = "Brutal [ACTION_REACT: :KEKWLaugh:] jajaja [ACTION_REACT: 💀] [ACTION_REACT: :Porro:]"
        clean, raw_react = extract_reaction_tag(text)
        self.assertNotIn("ACTION_REACT", clean)
        self.assertEqual(clean, "Brutal  jajaja")
        self.assertEqual(raw_react, ":KEKWLaugh:")

    def test_resolve_reaction_emoji_unicode_simple_and_compound(self):
        self.assertEqual(resolve_reaction_emoji("🤔"), "🤔")
        self.assertEqual(resolve_reaction_emoji(" 💀 "), "💀")
        self.assertEqual(resolve_reaction_emoji("❤️"), "❤️")
        self.assertEqual(resolve_reaction_emoji("😂💀"), "😂")
        self.assertEqual(resolve_reaction_emoji("🔥👀"), "🔥")
        self.assertIsNone(resolve_reaction_emoji(""))
        self.assertIsNone(resolve_reaction_emoji("   "))

    def test_resolve_reaction_emoji_active_guild_emoji(self):
        e_pensando = DummyEmoji("pensando", 1476989472502452255, animated=False, available=True)
        e_kekw = DummyEmoji("KEKWLaugh", 1535679941059018903, animated=True, available=True)
        guild = DummyGuild([e_pensando, e_kekw])

        self.assertIs(resolve_reaction_emoji(":pensando:", guild=guild), e_pensando)
        self.assertIs(resolve_reaction_emoji("pensando", guild=guild), e_pensando)
        self.assertIs(resolve_reaction_emoji("<:pensando:1476989472502452255>", guild=guild), e_pensando)
        self.assertIs(resolve_reaction_emoji("<a:KEKWLaugh:1535679941059018903>", guild=guild), e_kekw)

    def test_resolve_reaction_emoji_disabled_guild_emoji_fallbacks(self):
        e_porro = DummyEmoji("Porro", 1535685303317172305, animated=False, available=False)
        e_monkey = DummyEmoji("monkeythink", 1535684318993584219, animated=False, available=False)
        e_skill = DummyEmoji("skillissue", 1535727329156931624, animated=False, available=False)
        e_aura = DummyEmoji("aura", 1535728704129466462, animated=False, available=False)
        e_cringe_active = DummyEmoji("pepeCringe", 1530996221810966690, animated=False, available=True)

        guild_with_cringe = DummyGuild([e_porro, e_monkey, e_skill, e_aura, e_cringe_active])
        self.assertEqual(resolve_reaction_emoji(":Porro:", guild=guild_with_cringe), "🚬")
        self.assertEqual(resolve_reaction_emoji(":monkeythink:", guild=guild_with_cringe), "🤔")
        self.assertIs(resolve_reaction_emoji(":skillissue:", guild=guild_with_cringe), e_cringe_active)
        # gigachad no está en guild_with_cringe, así que :aura: cae a su fallback unitario 🗿
        self.assertEqual(resolve_reaction_emoji(":aura:", guild=guild_with_cringe), "🗿")

        # Si pepeCringe tampoco está activo, skillissue cae a 💀
        e_cringe_disabled = DummyEmoji("pepeCringe", 1530996221810966690, animated=False, available=False)
        guild_no_cringe = DummyGuild([e_skill, e_cringe_disabled])
        self.assertEqual(resolve_reaction_emoji(":skillissue:", guild=guild_no_cringe), "💀")

    def test_resolve_reaction_emoji_without_guild(self):
        # Con guild=None: is_safe=True devuelve formato Discord <:name:id>
        self.assertEqual(
            resolve_reaction_emoji(":pensando:", guild=None),
            "<:pensando:1476989472502452255>",
        )
        self.assertEqual(
            resolve_reaction_emoji("KEKWLaugh", guild=None),
            "<a:KEKWLaugh:1535679941059018903>",
        )
        # Con guild=None: is_safe=False devuelve el fallback unitario de REACTION_SINGLE_UNICODE_FALLBACK o DISABLED_EMOJI_FALLBACK
        self.assertEqual(resolve_reaction_emoji(":monkeythink:", guild=None), "🤔")
        self.assertEqual(resolve_reaction_emoji("porro", guild=None), "🚬")
        self.assertEqual(resolve_reaction_emoji(":blue_screen:", guild=None), "💥")
        self.assertIn("monkeythink", REACTION_SINGLE_UNICODE_FALLBACK)


class TestChatIAReactionsAsync(unittest.IsolatedAsyncioTestCase):
    async def _build_mock_message(self, content: str = "<@999> qué pasa máquina"):
        bot_user = MagicMock()
        bot_user.id = 999

        author = MagicMock()
        author.id = 12345
        author.name = "joselito3499"
        author.display_name = "Joselito"
        author.bot = False
        author.roles = []
        author.voice = None
        author.display_avatar.url = "https://example.com/avatar.png"

        channel = MagicMock()
        channel.name = "general"
        channel.typing = MagicMock()
        channel.typing.return_value.__aenter__ = AsyncMock(return_value=None)
        channel.typing.return_value.__aexit__ = AsyncMock(return_value=None)

        async def _empty_history(*args, **kwargs):
            if False:
                yield None

        channel.history = _empty_history

        e_pensando = DummyEmoji("pensando", 1476989472502452255, animated=False, available=True)
        guild = DummyGuild([e_pensando])

        msg = MagicMock()
        msg.content = content
        msg.author = author
        msg.channel = channel
        msg.guild = guild
        msg.mentions = [bot_user]
        msg.role_mentions = []
        msg.reference = None
        msg.attachments = []
        msg.add_reaction = AsyncMock()
        msg.reply = AsyncMock()

        mock_bot = MagicMock()
        mock_bot.user = bot_user
        return msg, mock_bot, e_pensando

    async def test_handle_message_safe_adds_reaction_and_strips_tag(self):
        msg, mock_bot, e_pensando = await self._build_mock_message()

        with patch("modulos.chat_ia._get_bot", return_value=mock_bot), patch(
            "modulos.chat_ia.get_live_levels_dict", new=AsyncMock(return_value={})
        ), patch("modulos.chat_ia.search_web_lite", return_value=""), patch(
            "modulos.chat_ia.call_gemini_multiturn",
            return_value="¡Qué grande eres colega! [ACTION_REACT: :pensando:]",
        ), patch("modulos.chat_ia.user_cooldowns", {}):
            await _handle_message_safe(msg)

        msg.add_reaction.assert_awaited_once_with(e_pensando)
        msg.reply.assert_awaited_once()
        replied_text = msg.reply.call_args[0][0]
        self.assertEqual(replied_text, "¡Qué grande eres colega!")
        self.assertNotIn("ACTION_REACT", replied_text)

    async def test_handle_message_safe_reaction_exception_falls_back_to_thinking_unicode(self):
        msg, mock_bot, e_pensando = await self._build_mock_message()
        # Simular que el primer add_reaction falla y el segundo con "🤔" funciona
        msg.add_reaction = AsyncMock(side_effect=[ RuntimeError("HTTPException 400 Unknown Emoji"), None ])

        with patch("modulos.chat_ia._get_bot", return_value=mock_bot), patch(
            "modulos.chat_ia.get_live_levels_dict", new=AsyncMock(return_value={})
        ), patch("modulos.chat_ia.search_web_lite", return_value=""), patch(
            "modulos.chat_ia.call_gemini_multiturn",
            return_value="Jajaja brutal [ACTION_REACT: :pensando:]",
        ), patch("modulos.chat_ia.user_cooldowns", {}):
            await _handle_message_safe(msg)

        self.assertEqual(msg.add_reaction.await_count, 2)
        self.assertEqual(msg.add_reaction.await_args_list[0].args[0], e_pensando)
        self.assertEqual(msg.add_reaction.await_args_list[1].args[0], "🤔")
        msg.reply.assert_awaited_once_with("Jajaja brutal")


if __name__ == "__main__":
    unittest.main()
