"""
Módulo de Scrapers Enriquecidos para Enlaces Sociales (YouTube, Twitter/X, Reddit, TikTok):
- YouTube: Consulta endpoint oEmbed oficial (título, autor/canal, tipo; soporte vídeos estándar, cortos youtu.be y shorts).
- Twitter / X: Consulta API abierta FXTwitter (texto, autor, @handle, likes, retweets, indicador multimedia).
- Reddit: Endpoint .json de Reddit con User-Agent descriptivo (subreddit, autor, título, score, selftext).
- TikTok: Endpoint oEmbed oficial de TikTok (título, autor).
- Despachador transversal resolve_social_url(url) con integración limpia y manejo robusto de excepciones.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

REDDIT_USER_AGENT = "AsistenteDiscordBot/1.0 (by /u/Joselito)"


def fetch_youtube_info(url: str) -> Optional[str]:
    """Extrae metadatos oficiales de vídeos, shorts y enlaces cortos de YouTube vía oEmbed."""
    if not url or not isinstance(url, str):
        return None

    # Detectar dominios YouTube
    yt_pattern = re.compile(
        r"^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?v=|shorts/|embed/)|youtu\.be/)[a-zA-Z0-9_\-]+",
        re.IGNORECASE,
    )
    if not yt_pattern.search(url):
        return None

    oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(url, safe='')}&format=json"
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    try:
        req = urllib.request.Request(oembed_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))

        title = data.get("title", "Sin título").strip()
        author_name = data.get("author_name", "Canal de YouTube").strip()
        content_type = data.get("type", "video")

        kind_str = "Short de YouTube" if "/shorts/" in url else "Vídeo de YouTube"
        return f"\n[{kind_str.upper()} LEÍDO: '{title}' por {author_name} ({content_type}) ({url})]\n"
    except Exception:
        return None


def fetch_twitter_info(url: str) -> Optional[str]:
    """Extrae texto, autor, estadísticas e indicador multimedia de tweets de Twitter/X vía FXTwitter API."""
    if not url or not isinstance(url, str):
        return None

    match = re.search(
        r"(?:https?://)?(?:www\.|mobile\.)?(?:twitter\.com|x\.com|fxtwitter\.com|vxtwitter\.com)/([a-zA-Z0-9_]+)/status/(\d+)",
        url,
        re.IGNORECASE,
    )
    if not match:
        return None

    user = match.group(1)
    status_id = match.group(2)
    fxtwitter_url = f"https://api.fxtwitter.com/{user}/status/{status_id}"
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    try:
        req = urllib.request.Request(fxtwitter_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))

        tweet = data.get("tweet", {})
        if not tweet:
            return None

        text = tweet.get("text", "").strip()
        author_info = tweet.get("author", {})
        author_name = author_info.get("name", user).strip()
        screen_name = author_info.get("screen_name", user).strip()
        likes = tweet.get("likes", 0)
        retweets = tweet.get("retweets", 0)

        # Detectar multimedia
        media = tweet.get("media", {}) or {}
        has_photos = bool(media.get("photos"))
        has_videos = bool(media.get("videos"))
        media_tag = ""
        if has_photos and has_videos:
            media_tag = " [Fotos y Vídeo]"
        elif has_photos:
            media_tag = " [Foto/Imagen adjunta]"
        elif has_videos:
            media_tag = " [Vídeo adjunto]"

        stats_str = f"❤️ {likes:,} | 🔁 {retweets:,}"
        return (
            f"\n[TWEET DE X/TWITTER LEÍDO: @{screen_name} ({author_name}) ({url})]:\n"
            f"{text}{media_tag} ({stats_str})\n"
        )
    except Exception:
        return None


def fetch_reddit_info(url: str) -> Optional[str]:
    """Extrae título, subreddit, autor, score y selftext de un post de Reddit vía endpoint .json."""
    if not url or not isinstance(url, str):
        return None

    is_reddit = bool(
        re.search(r"reddit\.com/r/([^/]+)/comments/([a-zA-Z0-9_]+)", url, re.IGNORECASE)
        or re.search(r"redd\.it/([a-zA-Z0-9_]+)", url, re.IGNORECASE)
    )
    if not is_reddit:
        return None

    clean_url = url.split("?")[0].rstrip("/")
    json_url = f"{clean_url}.json"
    headers = {"User-Agent": REDDIT_USER_AGENT}

    try:
        req = urllib.request.Request(json_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))

        if not isinstance(data, list) or not data:
            return None

        post_data = data[0]["data"]["children"][0]["data"]
        title = post_data.get("title", "Sin título").strip()
        author = post_data.get("author", "desconocido").strip()
        subreddit = post_data.get("subreddit", "").strip()
        score = post_data.get("score", 0)
        selftext = post_data.get("selftext", "").strip()

        if len(selftext) > 3000:
            selftext = selftext[:3000] + "\n... [Texto truncado]"

        body_preview = selftext if selftext else post_data.get("url_overridden_by_dest", "[Sin texto en el cuerpo]")

        return (
            f"\n[POST DE REDDIT LEÍDO: r/{subreddit} - '{title}' por u/{author} (Score: {score:,}) ({url})]:\n"
            f"{body_preview}\n"
        )
    except Exception:
        return None


def fetch_tiktok_info(url: str) -> Optional[str]:
    """Extrae título y autor de un vídeo de TikTok vía endpoint oEmbed oficial."""
    if not url or not isinstance(url, str):
        return None

    if not re.search(r"tiktok\.com/", url, re.IGNORECASE):
        return None

    oembed_url = f"https://www.tiktok.com/oembed?url={urllib.parse.quote(url, safe='')}&format=json"
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    try:
        req = urllib.request.Request(oembed_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))

        title = data.get("title", "Sin descripción").strip()
        author_name = data.get("author_name", "Desconocido").strip()
        return f"\n[VÍDEO DE TIKTOK LEÍDO: '{title}' por @{author_name} ({url})]\n"
    except Exception:
        return None


def resolve_social_url(url: str) -> Optional[str]:
    """
    Despachador transversal que identifica URLs de redes sociales populares (YouTube,
    Twitter/X, Reddit, TikTok) y extrae su contenido enriquecido mediante APIs abiertas y oEmbed.
    Devuelve None si no coincide o si la petición falla, permitiendo fallback al lector genérico.
    """
    if not url or not isinstance(url, str):
        return None

    lowered = url.lower()

    if "youtube.com" in lowered or "youtu.be" in lowered:
        yt_res = fetch_youtube_info(url)
        if yt_res:
            return yt_res

    if "twitter.com" in lowered or "x.com" in lowered or "fxtwitter.com" in lowered or "vxtwitter.com" in lowered:
        tw_res = fetch_twitter_info(url)
        if tw_res:
            return tw_res

    if "reddit.com" in lowered or "redd.it" in lowered:
        rd_res = fetch_reddit_info(url)
        if rd_res:
            return rd_res

    if "tiktok.com" in lowered:
        tt_res = fetch_tiktok_info(url)
        if tt_res:
            return tt_res

    return None
