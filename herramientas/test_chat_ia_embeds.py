"""
Suite de Pruebas Unitarias para la Comprensión de Embeds, Componentes y Bots en Chat IA:
- Extracción universal de mensajes de Discord (clean_content, components V2, embeds, attachments).
- Embed de balance de Economia Asistente (1 billón de porros).
- Componentes interactivos V2 (TextDisplay, Container, ActionRow, Botones).
- Mensajes híbridos (Texto + Embed).
- Simulación de contexto de respuesta citada (reply_ref_ctx) ante mensajes de bots.
- Simulación de turnos cronológicos (turns) para Gemini preservando contexto financiero de bots.
"""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Asegurar BASE_DIR en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import site
user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.append(user_site)

import discord
from modulos.chat_ia import (
    extract_discord_message_text,
    _extract_embed_text,
    _extract_components_text,
    BOT_PERSONALITIES,
    ACTIVE_PERSONALITY,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_A,
    SYSTEM_PROMPT_B,
)


class TestChatIAEmbedsVision(unittest.TestCase):
    """Pruebas unitarias de visión completa de Embeds, Componentes y Bots en Chat IA."""

    def test_extract_embed_balance_economia_asistente(self):
        """Caso 1: Embed de balance de Economia Asistente con 1 billón de porros."""
        embed_mock = MagicMock()
        embed_mock.title = "🌿 Balance Oficial de Iván (@racerwasp)"
        embed_mock.description = "Estado de cuenta y patrimonio en el servidor"
        embed_mock.author = SimpleNamespace(name="Economia Asistente")
        f1 = SimpleNamespace(name="💵 Efectivo", value="1.000 Porros")
        f2 = SimpleNamespace(name="🏦 Banco", value="1.000.000.000.000 Porros")
        f3 = SimpleNamespace(name="💎 Patrimonio Total", value="1.000.001.000.000 Porros")
        embed_mock.fields = [f1, f2, f3]
        embed_mock.footer = SimpleNamespace(text="Economia Asistente v2.0 • Hoy a las 22:30")

        msg_mock = SimpleNamespace(
            clean_content="",
            content="",
            components=[],
            embeds=[embed_mock],
            attachments=[],
        )

        extracted = extract_discord_message_text(msg_mock, max_len=600)
        self.assertIn("1.000.000.000.000 Porros", extracted)
        self.assertIn("Balance Oficial de Iván", extracted)
        self.assertIn("Banco: 1.000.000.000.000 Porros", extracted)
        self.assertIn("Patrimonio Total", extracted)
        self.assertTrue(extracted.startswith("[Embed:"))

    def test_extract_components_v2_container_textdisplay(self):
        """Caso 2: Componentes interactivos V2 (Container, TextDisplay y Botones)."""
        text_display = SimpleNamespace(content="🎰 ¡JACKPOT REVENTADO EN SLOTS! Premio: 50.000.000 Porros")
        button = SimpleNamespace(label="Ver Clasificación", value=None)
        action_row = SimpleNamespace(children=[button])
        container = SimpleNamespace(children=[text_display, action_row])

        msg_mock = SimpleNamespace(
            clean_content="",
            content="",
            components=[container],
            embeds=[],
            attachments=[],
        )

        extracted = extract_discord_message_text(msg_mock)
        self.assertIn("50.000.000 Porros", extracted)
        self.assertIn("JACKPOT REVENTADO", extracted)
        self.assertIn("Ver Clasificación", extracted)
        self.assertIn("[Componentes:", extracted)

    def test_extract_hybrid_text_plus_embed(self):
        """Caso 3: Mensaje que combina texto plano del bot + Embed con detalles."""
        embed_mock = MagicMock()
        embed_mock.title = "Atraco Exitoso"
        embed_mock.description = "Has robado 15.000 Porros a Joselito"
        embed_mock.author = None
        embed_mock.fields = [SimpleNamespace(name="Víctima", value="Joselito"), SimpleNamespace(name="Botín", value="15.000 Porros")]
        embed_mock.footer = None

        msg_mock = SimpleNamespace(
            clean_content="🚨 ¡Alerta de crimen en el servidor!",
            content="🚨 ¡Alerta de crimen en el servidor!",
            components=[],
            embeds=[embed_mock],
            attachments=[],
        )

        extracted = extract_discord_message_text(msg_mock)
        self.assertIn("¡Alerta de crimen en el servidor!", extracted)
        self.assertIn("Atraco Exitoso", extracted)
        self.assertIn("15.000 Porros", extracted)

    def test_reply_ref_context_simulation_bot_quote(self):
        """Caso 4: Simulación de reply_ref_ctx citando el mensaje del bot de economía."""
        # Embed del bot
        embed_mock = MagicMock()
        embed_mock.title = "Balance de RobaAbuelas"
        embed_mock.description = None
        embed_mock.author = None
        embed_mock.fields = [SimpleNamespace(name="Total", value="1.000.000.000 Porros")]
        embed_mock.footer = None

        bot_author = SimpleNamespace(display_name="Economia Asistente", name="economia_asistente", bot=True)
        quoted_msg = MagicMock(spec=discord.Message)
        quoted_msg.author = bot_author
        quoted_msg.clean_content = ""
        quoted_msg.content = ""
        quoted_msg.components = []
        quoted_msg.embeds = [embed_mock]
        quoted_msg.attachments = []

        # Mensaje del usuario que cita
        user_author = SimpleNamespace(display_name="Iván", name="racerwasp", bot=False)
        user_msg = MagicMock(spec=discord.Message)
        user_msg.author = user_author
        user_msg.clean_content = "@Asistente mira lo forrado que estoy colega"
        user_msg.reference = SimpleNamespace(resolved=quoted_msg, message_id=123456789)

        # Lógica simulada de reply_ref_ctx (igual a chat_ia.py)
        reply_ref_ctx = ""
        if getattr(user_msg, "reference", None):
            ref_m = getattr(user_msg.reference, "resolved", None)
            if ref_m:
                ref_txt = extract_discord_message_text(ref_m, max_len=400)
                if ref_txt:
                    author_name = getattr(ref_m.author, "display_name", "Usuario")
                    if getattr(ref_m.author, "bot", False):
                        reply_ref_ctx = f"\n[RESPONDIENDO DIRECTAMENTE AL MENSAJE DEL BOT {author_name}]: \"{ref_txt}\""
                    else:
                        reply_ref_ctx = f"\n[RESPONDIENDO DIRECTAMENTE AL MENSAJE DE {author_name}]: \"{ref_txt}\""

        self.assertIn("[RESPONDIENDO DIRECTAMENTE AL MENSAJE DEL BOT Economia Asistente]:", reply_ref_ctx)
        self.assertIn("1.000.000.000 Porros", reply_ref_ctx)
        self.assertIn("Balance de RobaAbuelas", reply_ref_ctx)

    def test_gemini_turns_with_bot_embed_history(self):
        """Caso 5: Simulación de turns para Gemini con mensajes cronológicos conteniendo embeds de bots."""
        asistente_user = SimpleNamespace(id=999, display_name="Asistente", name="asistente", bot=True)
        bot_asistente = SimpleNamespace(user=asistente_user)

        user1 = SimpleNamespace(display_name="Iván", name="racerwasp", bot=False)
        bot_eco = SimpleNamespace(display_name="Economia Asistente", name="economia_asistente", bot=True)

        # Mensaje 1: Iván tira /balance
        msg1 = SimpleNamespace(author=user1, clean_content="/balance", components=[], embeds=[], attachments=[])

        # Mensaje 2: Economia Asistente responde con tarjeta Embed de saldo
        embed_eco = MagicMock()
        embed_eco.title = "🌿 Balance Oficial"
        embed_eco.description = None
        embed_eco.author = None
        embed_eco.fields = [
            SimpleNamespace(name="Efectivo", value="500 Porros"),
            SimpleNamespace(name="Banco", value="1.000.000.000.000 Porros"),
        ]
        embed_eco.footer = None
        msg2 = SimpleNamespace(author=bot_eco, clean_content="", components=[], embeds=[embed_eco], attachments=[])

        # Mensaje 3: Iván cita o habla en el canal
        msg3 = SimpleNamespace(author=user1, clean_content="Asistente qué te parece mi cuenta bancaria?", components=[], embeds=[], attachments=[])

        raw_msgs = [msg1, msg2, msg3]

        # Lógica de turns idéntica a chat_ia.py
        import re
        turns = []
        for m in raw_msgs[-12:]:
            raw_extracted = extract_discord_message_text(m, max_len=400)
            m_text = re.sub(r"<@&?\d+>", "", raw_extracted).strip()
            if not m_text:
                continue
            is_bot = (m.author == bot_asistente.user)
            role = "model" if is_bot else "user"
            author_label = getattr(m.author, "display_name", "Usuario")
            if getattr(m.author, "bot", False) and not is_bot:
                author_label += " [BOT]"
            prefix = "" if is_bot else f"{author_label}: "
            formatted = f"{prefix}{m_text}"

            if turns and turns[-1]["role"] == role:
                turns[-1]["parts"][0]["text"] += f"\n{formatted}"
            else:
                turns.append({
                    "role": role,
                    "parts": [{"text": formatted}]
                })

        # Comprobaciones
        self.assertTrue(len(turns) > 0)
        # Como no hay respuestas de Asistente (model), todos los mensajes se combinan o agrupan en role="user"
        all_text = "\n".join([p["text"] for t in turns for p in t["parts"]])
        self.assertIn("Economia Asistente [BOT]:", all_text)
        self.assertIn("1.000.000.000.000 Porros", all_text)
        self.assertIn("Iván: /balance", all_text)
        self.assertIn("Iván: Asistente qué te parece mi cuenta bancaria?", all_text)

    def test_bot_personalities_a_and_b(self):
        """Caso 6: Verifica que Asistente es la Personalidad A activa y Asistenta está guardada como Personalidad B."""
        self.assertEqual(ACTIVE_PERSONALITY, "A")
        self.assertEqual(SYSTEM_PROMPT, SYSTEM_PROMPT_A)
        self.assertIn("A", BOT_PERSONALITIES)
        self.assertIn("B", BOT_PERSONALITIES)

        pers_a = BOT_PERSONALITIES["A"]
        self.assertEqual(pers_a["name"], "Asistente")
        self.assertIn("avatar_asistente_original.png", pers_a["avatar_path"])
        self.assertIn("Eres 'Asistente'", pers_a["system_prompt"])

        pers_b = BOT_PERSONALITIES["B"]
        self.assertEqual(pers_b["name"], "Asistenta")
        self.assertIn("media_1792796615874.jpg", pers_b["avatar_path"])
        self.assertIn("Eres 'Asistenta'", pers_b["system_prompt"])
        self.assertIn("hablas en femenino", pers_b["system_prompt"])


if __name__ == "__main__":
    unittest.main()
