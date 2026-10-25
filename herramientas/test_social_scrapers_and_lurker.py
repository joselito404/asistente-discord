"""
Suite de Tests Unitarios para:
- Scrapers Sociales Enriquecidos (YouTube, Twitter/X, Reddit, TikTok)
- Memoria Social Dinámica y Grafo de Relaciones (social_graph.json)
- Búsqueda Histórica Profunda y Mini-RAG (Historial de canal y Starboard)
- Reacciones Autónomas de Baja Frecuencia (Drop-in Lurker)
"""

import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json
import os
import sys
import io
import time
from datetime import datetime, timezone

# Asegurar importación de módulos del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import discord

from modulos.social_scrapers import (
    fetch_youtube_info,
    fetch_twitter_info,
    fetch_reddit_info,
    fetch_tiktok_info,
    resolve_social_url,
)
from modulos.social_memory import (
    _make_pair_key,
    load_social_graph,
    save_social_graph,
    record_voice_duo,
    record_duel_interaction,
    get_affinity,
    get_social_dynamics_ctx,
    SOCIAL_GRAPH_PATH,
)
from modulos.chat_ia import (
    search_starboard_moments,
    search_deep_channel_history,
    format_episodic_memory,
    check_lurker_reaction,
    LURKER_ALLOWED_CHANNELS,
    _LAST_LURKER_REACT,
    fetch_url_content,
    _URL_CONTENT_CACHE,
)


class TestSocialScrapers(unittest.TestCase):
    """Pruebas unitarias para los scrapers sociales (YouTube, Twitter/X, Reddit, TikTok)."""

    def test_fetch_youtube_info(self):
        sample_yt_json = json.dumps({
            "title": "Tutorial Avanzado de Python",
            "author_name": "Canal Dev",
            "type": "video",
            "provider_name": "YouTube"
        }).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = sample_yt_json
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            # Vídeo normal
            res1 = fetch_youtube_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            self.assertIsNotNone(res1)
            self.assertIn("Tutorial Avanzado de Python", res1)
            self.assertIn("Canal Dev", res1)
            self.assertIn("VÍDEO DE YOUTUBE", res1)

            # Short de YouTube
            res_short = fetch_youtube_info("https://youtube.com/shorts/abcdef12345")
            self.assertIsNotNone(res_short)
            self.assertIn("SHORT DE YOUTUBE", res_short)

            # URL corta youtu.be
            res_short_url = fetch_youtube_info("https://youtu.be/dQw4w9WgXcQ")
            self.assertIsNotNone(res_short_url)

        # URL no YouTube debe retornar None sin llamar a urlopen
        self.assertIsNone(fetch_youtube_info("https://github.com/torvalds/linux"))

    def test_fetch_twitter_info(self):
        sample_tweet_json = json.dumps({
            "code": 200,
            "message": "OK",
            "tweet": {
                "text": "Nuevo lanzamiento oficial de la versión 3.0!",
                "author": {
                    "name": "Dev Team",
                    "screen_name": "devteam"
                },
                "likes": 1250,
                "retweets": 340,
                "media": {
                    "photos": [{"url": "https://pbs.twimg.com/photo1.jpg"}]
                }
            }
        }).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = sample_tweet_json
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = fetch_twitter_info("https://x.com/devteam/status/1234567890123456789")
            self.assertIsNotNone(res)
            self.assertIn("@devteam", res)
            self.assertIn("Dev Team", res)
            self.assertIn("Nuevo lanzamiento oficial", res)
            self.assertIn("Foto/Imagen adjunta", res)
            self.assertIn("1,250", res)
            self.assertIn("340", res)

        self.assertIsNone(fetch_twitter_info("https://not-twitter.com/post/123"))

    def test_fetch_reddit_info(self):
        sample_reddit_json = json.dumps([
            {
                "data": {
                    "children": [
                        {
                            "data": {
                                "title": "¿Cuál es vuestra build favorita?",
                                "author": "Gamer123",
                                "subreddit": "gaming",
                                "score": 450,
                                "selftext": "A mí me encanta la build de destreza y magia."
                            }
                        }
                    ]
                }
            }
        ]).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = sample_reddit_json
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = fetch_reddit_info("https://www.reddit.com/r/gaming/comments/xyz123/cual_es_vuestra_build/")
            self.assertIsNotNone(res)
            self.assertIn("r/gaming", res)
            self.assertIn("Gamer123", res)
            self.assertIn("¿Cuál es vuestra build favorita?", res)
            self.assertIn("destreza y magia", res)
            self.assertIn("450", res)

        self.assertIsNone(fetch_reddit_info("https://example.com/post"))

    def test_fetch_tiktok_info(self):
        sample_tt_json = json.dumps({
            "title": "Un día en la vida de un dev",
            "author_name": "dev_influencer"
        }).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = sample_tt_json
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            res = fetch_tiktok_info("https://www.tiktok.com/@dev_influencer/video/123456789")
            self.assertIsNotNone(res)
            self.assertIn("Un día en la vida de un dev", res)
            self.assertIn("@dev_influencer", res)

    def test_resolve_social_url_and_cache(self):
        test_url = "https://youtube.com/watch?v=mocktest123"
        fake_content = "[VÍDEO DE YOUTUBE LEÍDO: 'Test Video' por Autor (video) (https://youtube.com/watch?v=mocktest123)]"

        with patch("modulos.social_scrapers.fetch_youtube_info", return_value=fake_content):
            resolved = resolve_social_url(test_url)
            self.assertEqual(resolved, fake_content)

            # Integración en fetch_url_content y almacenamiento en caché
            res_content = fetch_url_content(test_url)
            self.assertEqual(res_content, fake_content)
            self.assertIn(test_url, _URL_CONTENT_CACHE)
            self.assertEqual(_URL_CONTENT_CACHE[test_url]["content"], fake_content)


class TestSocialMemory(unittest.TestCase):
    """Pruebas para el grafo de relaciones y dinamismo social en social_memory.py."""

    def setUp(self):
        self.tmp_graph_path = os.path.join(BASE_DIR, "datos", "test_social_graph.json")
        self.patcher = patch("modulos.social_memory.SOCIAL_GRAPH_PATH", self.tmp_graph_path)
        self.patcher.start()
        # Asegurar fichero inicial limpio
        if os.path.exists(self.tmp_graph_path):
            os.remove(self.tmp_graph_path)

    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.tmp_graph_path):
            try:
                os.remove(self.tmp_graph_path)
            except Exception:
                pass

    def test_make_pair_key_ordering(self):
        # Independientemente del orden de los argumentos, la clave debe ser id_menor:id_mayor
        k1 = _make_pair_key(100, 200)
        k2 = _make_pair_key(200, 100)
        self.assertEqual(k1, k2)
        self.assertEqual(k1, "100:200")

    def test_record_voice_and_duels(self):
        user_a = 111111111
        user_b = 222222222

        # Registrar minutos en llamada
        record_voice_duo(user_a, user_b, minutes=45.0)
        aff = get_affinity(user_a, user_b)
        self.assertEqual(aff["voice_minutes_together"], 45.0)
        self.assertGreaterEqual(aff["affinity_score"], 3)  # 45 // 15 = 3

        # Registrar duelos
        record_duel_interaction(user_a, user_b)
        record_duel_interaction(user_a, user_b)
        aff2 = get_affinity(user_a, user_b)
        self.assertEqual(aff2["duels_count"], 2)
        self.assertEqual(aff2["affinity_score"], 2 * 2 + 3)  # 4 + 3 = 7

    def test_get_social_dynamics_ctx(self):
        # Mock de guild y miembros
        guild = MagicMock(spec=discord.Guild)

        m_joselito = MagicMock(spec=discord.Member)
        m_joselito.id = 857923274771136522
        m_joselito.display_name = "Joselito"
        m_joselito.bot = False

        m_ivan = MagicMock(spec=discord.Member)
        m_ivan.id = 999304511464149104
        m_ivan.display_name = "Iván"
        m_ivan.bot = False

        msg = MagicMock(spec=discord.Message)
        msg.author = m_ivan
        msg.mentions = []

        raw_msgs = [msg]

        ctx = get_social_dynamics_ctx(author=m_joselito, guild=guild, raw_msgs=raw_msgs)
        self.assertIn("DINÁMICA SOCIAL", ctx)
        self.assertIn("Joselito", ctx)
        self.assertIn("Iván", ctx)
        self.assertIn("colegas habituales", ctx)


class TestMiniRAGAndStarboard(unittest.IsolatedAsyncioTestCase):
    """Pruebas para la búsqueda histórica profunda y Mini-RAG."""

    def test_search_starboard_moments(self):
        # Búsqueda en datos/starboard.json real
        res = search_starboard_moments("¿Quién tiene el mensaje más votado en el starboard?", limit=2)
        self.assertTrue(len(res) > 0)
        top_entry = res[0]
        self.assertIn("stars_count", top_entry)
        self.assertIn("author_name", top_entry)

    async def test_search_deep_channel_history(self):
        channel = MagicMock()

        # Simular historial asíncrono
        class AsyncMsgIterator:
            def __init__(self, items):
                self.items = items
                self.idx = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.idx < len(self.items):
                    item = self.items[self.idx]
                    self.idx += 1
                    return item
                raise StopAsyncIteration

        m1 = MagicMock()
        m1.author.bot = False
        m1.author.display_name = "Joselito"
        m1.clean_content = "El torneo de ajedrez empieza el viernes."
        m1.created_at = datetime(2026, 10, 20, 15, 30, tzinfo=timezone.utc)
        m1.id = 1001

        m2 = MagicMock()
        m2.author.bot = False
        m2.author.display_name = "Iván"
        m2.clean_content = "Buenas tardes a todos."
        m2.created_at = datetime(2026, 10, 20, 15, 35, tzinfo=timezone.utc)
        m2.id = 1002

        channel.history = MagicMock(return_value=AsyncMsgIterator([m1, m2]))

        results = await search_deep_channel_history(channel, "te acuerdas del torneo de ajedrez?", limit=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["author"], "Joselito")
        self.assertIn("torneo de ajedrez", results[0]["content"])

    def test_format_episodic_memory(self):
        deep_msgs = [{
            "author": "Joselito",
            "content": "Ajedrez a tope.",
            "time": "20/10 15:30",
            "id": 1001
        }]
        sb_entries = [{
            "edition_number": 5,
            "author_name": "Joselito",
            "stars_count": 4
        }]
        res = format_episodic_memory(deep_msgs, sb_entries)
        self.assertIn("MEMORIA EPISÓDICA E HISTORIAL PROFUNDO RESCATADO", res)
        self.assertIn("Edición #5", res)
        self.assertIn("Ajedrez a tope", res)


class TestDropInLurker(unittest.IsolatedAsyncioTestCase):
    """Pruebas para las reacciones autónomas del Drop-in Lurker."""

    def setUp(self):
        _LAST_LURKER_REACT.clear()

    async def test_lurker_forbidden_channel(self):
        # Canal fuera de la lista permitida
        channel = MagicMock()
        channel.name = "general-offtopic"
        channel.id = 5555

        msg = MagicMock()
        msg.author.bot = False
        msg.channel = channel
        msg.clean_content = "jajajaja puro cine"

        res = await check_lurker_reaction(msg, force=False)
        self.assertIsNone(res)
        msg.add_reaction.assert_not_called()

    async def test_lurker_trigger_keywords_and_reaction(self):
        channel = MagicMock()
        channel.name = "la-shit-de-todos-los-dias"
        channel.id = 1455700883378536559

        msg = MagicMock()
        msg.author.bot = False
        msg.channel = channel
        msg.guild = MagicMock()
        msg.guild.emojis = []
        msg.clean_content = "esto es puro cine hermano"
        msg.add_reaction = AsyncMock()

        # Forzar para ignorar el dado aleatorio del 30%
        res = await check_lurker_reaction(msg, force=True)
        self.assertIsNotNone(res)
        msg.add_reaction.assert_awaited_once()

    async def test_lurker_laughter_streak(self):
        channel = MagicMock()
        channel.name = "shit-post"
        channel.id = 1455700883378536560

        msg = MagicMock()
        msg.author.bot = False
        msg.channel = channel
        msg.guild = MagicMock()
        msg.guild.emojis = []
        msg.clean_content = "xdxdxd jajajaja me meo"
        msg.add_reaction = AsyncMock()

        res = await check_lurker_reaction(msg, force=True)
        self.assertIsNotNone(res)
        msg.add_reaction.assert_awaited_once()

    async def test_lurker_rate_limit_45_minutes(self):
        channel = MagicMock()
        channel.name = "gaming-general"
        channel.id = 999888777

        msg = MagicMock()
        msg.author.bot = False
        msg.channel = channel
        msg.guild = MagicMock()
        msg.guild.emojis = []
        msg.clean_content = "estoy cooked total"
        msg.add_reaction = AsyncMock()

        # Primera reacción exitosa
        res1 = await check_lurker_reaction(msg, force=True)
        self.assertIsNotNone(res1)
        self.assertIn(channel.id, _LAST_LURKER_REACT)

        # Inmediatamente después, sin force, debe respetar el cooldown y no reaccionar
        msg2 = MagicMock()
        msg2.author.bot = False
        msg2.channel = channel
        msg2.clean_content = "jajajaja puro cine"
        msg2.add_reaction = AsyncMock()

        res2 = await check_lurker_reaction(msg2, force=False)
        self.assertIsNone(res2)
        msg2.add_reaction.assert_not_called()


if __name__ == "__main__":
    unittest.main()
