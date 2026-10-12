"""Fetch YouTube track metadata without relying on the legacy search API."""

import asyncio
import logging
import os
import tempfile
from typing import Optional

import yt_dlp

YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={}"
logger = logging.getLogger(__name__)


class _SafeYtDlpLogger:
    """Forward yt-dlp messages while redacting cookie-related diagnostics."""

    def __init__(self, target_logger):
        self.target_logger = target_logger

    @staticmethod
    def _safe_message(message):
        text = str(message)
        if "cookie" in text.casefold() or "\t" in text:
            return "yt-dlp cookie diagnostic suppressed; sensitive details redacted"
        return text

    def debug(self, message):
        return None

    def warning(self, message):
        self.target_logger.warning(self._safe_message(message))

    def error(self, message):
        self.target_logger.error(self._safe_message(message))


def _valid_cookie_text(contents: str) -> bool:
    has_cookie = False
    for line in contents.splitlines():
        if not line.strip() or (line.startswith("#") and not line.startswith("#HttpOnly_")):
            continue
        if len(line.split("\t")) != 7:
            return False
        has_cookie = True
    return has_cookie


def _valid_cookie_file(cookie_file: str) -> bool:
    try:
        with open(cookie_file, encoding="utf-8") as cookie_input:
            return _valid_cookie_text(cookie_input.read())
    except (OSError, UnicodeError):
        return False


def _duration_text(seconds: Optional[int]) -> Optional[str]:
    if seconds is None:
        return None
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _add_cookiefile_option(options: dict) -> None:
    cookie_file = os.getenv("COOKIES_FILE")
    if cookie_file and os.path.isfile(cookie_file):
        if _valid_cookie_file(cookie_file):
            options["cookiefile"] = cookie_file
            return
        logger.warning("Ignoring invalid YouTube cookie file; contents redacted")

    cookie_contents = os.getenv("YOUTUBE_COOKIES")
    if cookie_contents:
        cookie_contents = (
            cookie_contents.replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
        )
        if not _valid_cookie_text(cookie_contents):
            logger.warning("Ignoring invalid YOUTUBE_COOKIES format; contents redacted")
            return
        cookie_file = os.path.join(
            tempfile.gettempdir(), f"arush-youtube-cookies-{os.getpid()}.txt"
        )
        descriptor = os.open(cookie_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as cookie_output:
            cookie_output.write(cookie_contents)
        os.chmod(cookie_file, 0o600)
        options["cookiefile"] = cookie_file
        return

    local_cookie_file = "cookies.txt"
    if os.path.isfile(local_cookie_file):
        if _valid_cookie_file(local_cookie_file):
            options["cookiefile"] = local_cookie_file
        else:
            logger.warning("Ignoring invalid local YouTube cookie file; contents redacted")
    elif cookie_file:
        logger.warning("Configured YouTube cookies file is missing")


def _fetch_youtube_track_sync(link: str, *, videoid: bool = False) -> dict:
    value = str(link or "").strip()
    if not value:
        raise ValueError("A YouTube URL or search query is required")

    if videoid and not value.startswith(("http://", "https://")):
        target = YOUTUBE_WATCH_URL.format(value)
    elif value.startswith(("http://", "https://")):
        target = value
    else:
        target = f"ytsearch1:{value}"

    options = {
        "quiet": True,
        "no_warnings": True,
        "logger": _SafeYtDlpLogger(logger),
        "skip_download": True,
        "extract_flat": True,
        "noplaylist": True,
        "geo_bypass": True,
        "extractor_args": {"youtube": {"player_client": ["web_embedded"]}},
        "js_runtimes": {"node": {}},
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 30,
    }
    _add_cookiefile_option(options)
    with yt_dlp.YoutubeDL(options) as downloader:
        result = downloader.extract_info(target, download=False)

    if not result:
        raise LookupError("YouTube returned no track metadata")

    entries = result.get("entries") if isinstance(result, dict) else None
    info = next((entry for entry in entries or () if entry), None) if entries is not None else result
    if not isinstance(info, dict):
        raise LookupError("YouTube search returned no tracks")

    vidid = info.get("id")
    title = info.get("title")
    if not vidid or not title:
        raise LookupError("YouTube track metadata is incomplete")

    thumbnail = info.get("thumbnail")
    if not thumbnail:
        thumbnails = info.get("thumbnails") or []
        if thumbnails:
            thumbnail = thumbnails[-1].get("url")
    if not thumbnail:
        thumbnail = f"https://i.ytimg.com/vi/{vidid}/hqdefault.jpg"

    track_details = {
        "title": title,
        "link": info.get("webpage_url") or YOUTUBE_WATCH_URL.format(vidid),
        "vidid": vidid,
        "duration_min": _duration_text(info.get("duration")),
        "thumb": thumbnail.split("?")[0],
    }
    return track_details


async def fetch_youtube_track(link: str, *, videoid: bool = False) -> dict:
    """Resolve a YouTube link or search query off the event loop."""
    return await asyncio.to_thread(
        _fetch_youtube_track_sync,
        link,
        videoid=videoid,
    )
