"""Fetch YouTube track metadata without relying on the legacy search API."""

import asyncio
import logging
import os
import tempfile
from typing import Optional

import yt_dlp

YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={}"
logger = logging.getLogger(__name__)


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
        options["cookiefile"] = cookie_file
        return

    cookie_contents = os.getenv("YOUTUBE_COOKIES")
    if cookie_contents:
        cookie_file = os.path.join(
            tempfile.gettempdir(), f"arush-youtube-cookies-{os.getpid()}.txt"
        )
        descriptor = os.open(cookie_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as cookie_output:
            cookie_output.write(cookie_contents)
        os.chmod(cookie_file, 0o600)
        options["cookiefile"] = cookie_file
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
        "skip_download": True,
        "extract_flat": True,
        "noplaylist": True,
        "geo_bypass": True,
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
