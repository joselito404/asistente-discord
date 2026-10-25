"""
Suite Integral de Pruebas Unitarias para Inteligencia Contextual y Lectura de Documentos en Chat IA:
- Extracción y transformación de URLs de Google Docs y Google Sheets (edit, view, tab=..., spreadsheets).
- Caché en memoria con TTL para URLs.
- Simulación de lectura exitosa, truncado a 12.000 caracteres y respuesta ante documentos privados (HTTP 403).
- Normalización y búsqueda transversal de canales sin emojis (find_channel_by_name / normalize_channel_name).
- Extracción transversal de fijados (pins) y lectura automática de enlaces en pins.
- Directivas estrictas anti-alucinación en SYSTEM_PROMPT_BODY.
- Manejo resiliente de timeouts en cascada de Gemini (12s sin cooldown agresivo).
"""

import os
import sys
import time
import socket
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock, patch

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Asegurar BASE_DIR y paquetes de usuario en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import site
user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.append(user_site)

import discord
import modulos.chat_ia as chat_ia
from modulos.chat_ia import (
    extract_google_docs_url,
    fetch_url_content,
    normalize_channel_name,
    find_channel_by_name,
    get_pins_context,
    _URL_CONTENT_CACHE,
    _URL_CACHE_TTL,
    GoogleDocInfo,
    SYSTEM_PROMPT_BODY,
    SYSTEM_PROMPT_A,
    SYSTEM_PROMPT_B,
    call_gemini_multiturn,
    mark_model_cooldown,
    model_cooldowns,
)


class TestChatIAIntelligence(unittest.IsolatedAsyncioTestCase):
    """Test suite para las capacidades avanzadas de inteligencia, Google Docs y canales transversales."""

    def setUp(self):
        # Limpiar caché antes de cada prueba
        _URL_CONTENT_CACHE.clear()

    def test_extract_google_docs_url_edit_and_view(self):
        """Caso 1: Detección y transformación de Google Docs normal (edit y view)."""
        url_edit = "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
        info = extract_google_docs_url(url_edit)
        self.assertIsNotNone(info)
        self.assertEqual(info["type"], "docs")
        self.assertEqual(info["id"], "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        self.assertIsNone(info["tab"])
        self.assertEqual(info["export_url"], "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/export?format=txt")
        self.assertIsNone(info["fallback_export_url"])
        # Compatibilidad con string
        self.assertEqual(str(info), info["export_url"])
        self.assertEqual(info, info["export_url"])

        url_view = "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/view?usp=sharing"
        info_view = extract_google_docs_url(url_view)
        self.assertIsNotNone(info_view)
        self.assertEqual(info_view["export_url"], "https://docs.google.com/document/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/export?format=txt")

    def test_extract_google_docs_url_with_tab(self):
        """Caso 2: Detección de Google Docs con parámetro de pestaña tab=..."""
        url_tab = "https://docs.google.com/document/d/1xyz_abc_789/edit?tab=t.usxff8opcjps#heading=h.123"
        info = extract_google_docs_url(url_tab)
        self.assertIsNotNone(info)
        self.assertEqual(info["type"], "docs")
        self.assertEqual(info["id"], "1xyz_abc_789")
        self.assertEqual(info["tab"], "t.usxff8opcjps")
        self.assertEqual(info["export_url"], "https://docs.google.com/document/d/1xyz_abc_789/export?format=txt&tab=t.usxff8opcjps")
        self.assertEqual(info["fallback_export_url"], "https://docs.google.com/document/d/1xyz_abc_789/export?format=txt")

    def test_extract_google_sheets_url(self):
        """Caso 3: Detección y exportación de Google Sheets a CSV."""
        url_sheet = "https://docs.google.com/spreadsheets/d/1_sheet_abc_456/edit#gid=0"
        info = extract_google_docs_url(url_sheet)
        self.assertIsNotNone(info)
        self.assertEqual(info["type"], "sheets")
        self.assertEqual(info["id"], "1_sheet_abc_456")
        self.assertEqual(info["export_url"], "https://docs.google.com/spreadsheets/d/1_sheet_abc_456/export?format=csv")

    def test_extract_google_docs_url_non_google(self):
        """Caso 4: URLs no pertenecientes a Google Docs retornan None."""
        self.assertIsNone(extract_google_docs_url("https://example.com/not-docs"))
        self.assertIsNone(extract_google_docs_url("https://google.com/search?q=test"))
        self.assertIsNone(extract_google_docs_url(""))

    def test_url_cache_ttl_and_hits(self):
        """Caso 5: Caché en memoria con TTL para evitar peticiones repetidas."""
        test_url = "https://docs.google.com/document/d/test_doc_cache/edit"
        _URL_CONTENT_CACHE[test_url] = {
            "content": "[CONTENIDO CACHEADO]",
            "expires_at": time.time() + 900
        }

        # Al llamar con caché válida, devuelve directamente el contenido sin llamada web
        res = fetch_url_content(test_url)
        self.assertEqual(res, "[CONTENIDO CACHEADO]")

        # Si el TTL expira, se refresca
        _URL_CONTENT_CACHE[test_url]["expires_at"] = time.time() - 10
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"NUEVO CONTENIDO REFRESCO"
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            res_refreshed = fetch_url_content(test_url)
            self.assertIn("NUEVO CONTENIDO REFRESCO", res_refreshed)
            self.assertIn("DOCUMENTO DE GOOGLE DOCS LEÍDO CON ÉXITO", res_refreshed)

    def test_google_docs_private_403_warning(self):
        """Caso 6: Retorno de advertencia estricta ante documento privado (401/403/404)."""
        import urllib.error
        test_url = "https://docs.google.com/document/d/private_doc_123/edit"

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url=test_url, code=403, msg="Forbidden", hdrs={}, fp=None
            )
            result = fetch_url_content(test_url)
            self.assertIn("AVISO GOOGLE DOCS", result)
            self.assertIn("es privado o no tiene permisos de lectura pública", result)
            self.assertIn("NO inventes su contenido", result)

    def test_google_docs_truncation_limit(self):
        """Caso 7: Truncado seguro a 12.000 caracteres conservando contenido útil."""
        test_url = "https://docs.google.com/document/d/huge_doc_123/edit"
        huge_text = ("Manhwa Top Item " * 1500).encode("utf-8")  # ~24.000 chars

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = huge_text
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            result = fetch_url_content(test_url)
            self.assertIn("Contenido truncado a 12.000 caracteres", result)
            self.assertIn("DOCUMENTO DE GOOGLE DOCS LEÍDO CON ÉXITO", result)

    def test_normalize_channel_name(self):
        """Caso 8: Normalización de canales quitando emojis, caracteres especiales y mayúsculas."""
        self.assertEqual(normalize_channel_name("📖cultura📖"), "cultura")
        self.assertEqual(normalize_channel_name("🛠️apps-solo-mods🛠️"), "apps-solo-mods")
        self.assertEqual(normalize_channel_name("⚖️el-tribunal-gaming⚖️"), "el-tribunal-gaming")
        self.assertEqual(normalize_channel_name("🎭roles🎭"), "roles")
        self.assertEqual(normalize_channel_name("la-shit-de-todos-los-dias"), "la-shit-de-todos-los-dias")
        self.assertEqual(normalize_channel_name("💡sugerencias💡"), "sugerencias")

    def test_find_channel_by_name(self):
        """Caso 9: Búsqueda flexible de canales por query con y sin emojis o menciones."""
        ch_cultura = SimpleNamespace(name="📖cultura📖")
        ch_apps = SimpleNamespace(name="🛠️apps-solo-mods🛠️")
        ch_tribunal = SimpleNamespace(name="⚖️el-tribunal-gaming⚖️")
        ch_general = SimpleNamespace(name="la-shit-de-todos-los-dias")

        guild_mock = SimpleNamespace(text_channels=[ch_cultura, ch_apps, ch_tribunal, ch_general])

        # Búsquedas exactas
        self.assertEqual(find_channel_by_name(guild_mock, "cultura"), ch_cultura)
        self.assertEqual(find_channel_by_name(guild_mock, "apps-solo-mods"), ch_apps)
        self.assertEqual(find_channel_by_name(guild_mock, "el-tribunal-gaming"), ch_tribunal)

        # Búsquedas contextuales ("fijado en cultura", "tier list de cultura")
        self.assertEqual(find_channel_by_name(guild_mock, "fijado en cultura"), ch_cultura)
        self.assertEqual(find_channel_by_name(guild_mock, "¿cuál es el top de cultura?"), ch_cultura)
        self.assertEqual(find_channel_by_name(guild_mock, "tribunal"), ch_tribunal)
        self.assertIsNone(find_channel_by_name(guild_mock, "canal_inexistente_xyz"))

    async def test_get_pins_context_cross_channel_with_google_docs(self):
        """Caso 10: Extracción transversal de pins y lectura automática de enlaces en pins."""
        # Simulamos canal #📖cultura📖 con un pin que contiene el top 69 manhwas de Joselito
        pin_cultura = MagicMock()
        pin_cultura.author.display_name = "joselito3499"
        pin_cultura.clean_content = (
            "📌 Aquí tenéis mi Tier List Oficial Top 69 Manhwas:\n"
            "https://docs.google.com/document/d/top69_joselito_manhwas/edit\n"
            "Top 1: SSS-Class Suicide Hunter | Top 2: Latna Saga"
        )

        ch_cultura = AsyncMock()
        ch_cultura.name = "📖cultura📖"
        ch_cultura.pins.return_value = [pin_cultura]

        ch_origen = AsyncMock()
        ch_origen.name = "🛠️apps-solo-mods🛠️"
        ch_origen.pins.return_value = []

        guild_mock = SimpleNamespace(text_channels=[ch_cultura, ch_origen])
        ch_origen.guild = guild_mock
        ch_cultura.guild = guild_mock

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"TOP 1: SSS-Class Suicide Hunter\nTOP 2: Survival Story of a Sword King in a Fantasy World (Latna Saga)\nTOP 3: The Greatest Estate Developer"
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            # Pregunta hecha desde #apps-solo-mods sobre el fijado en cultura
            ctx = await get_pins_context(ch_origen, query="cuál es el top de manhwas en cultura", guild=guild_mock)

            self.assertIn("MENSAJES FIJADOS/PINNED EN #📖cultura📖", ctx)
            self.assertIn("DOCUMENTO/ENLACE VINCULADO AL PIN EN #📖cultura📖", ctx)
            self.assertIn("SSS-Class Suicide Hunter", ctx)
            self.assertIn("Latna Saga", ctx)

    def test_anti_hallucination_rule_in_system_prompt(self):
        """Caso 11: Presencia obligatoria de la Regla 7 anti-alucinación en todos los system prompts."""
        rule_snippet = "VETO ABSOLUTO A INVENTAR CONTENIDO DE DOCUMENTOS O ENLACES"
        self.assertIn(rule_snippet, SYSTEM_PROMPT_BODY)
        self.assertIn(rule_snippet, SYSTEM_PROMPT_A)
        self.assertIn(rule_snippet, SYSTEM_PROMPT_B)

        # Prohibición explícita de inventar Solo Leveling / ORV si no están en el texto
        self.assertIn("Solo Leveling, Omniscient Reader's Viewpoint", SYSTEM_PROMPT_BODY)

    def test_call_gemini_multiturn_timeout_no_aggressive_cooldown(self):
        """Caso 12: En caso de timeout de red en Gemini (12s), conmutar sin cooldown agresivo de 45s."""
        # Limpiar cooldowns
        chat_ia.model_cooldowns.clear()

        # Simulamos que gemini-2.5-flash da socket.timeout
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = socket.timeout("timed out")

            with patch("modulos.chat_ia._get_gemini_key", return_value="fake_key"):
                # Ejecutamos con 1 solo modelo simulado en lista
                with patch("modulos.chat_ia.get_available_models", return_value=["gemini-2.5-flash"]):
                    res = call_gemini_multiturn([{"role": "user", "parts": [{"text": "Hola"}]}])
                    # No debe tener cooldown de 45s en model_cooldowns
                    self.assertNotIn("gemini-2.5-flash", chat_ia.model_cooldowns)
                    self.assertIn("Cuota de IA temporalmente saturada", res)


if __name__ == "__main__":
    unittest.main()
