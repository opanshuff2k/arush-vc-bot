"""Download YouTube media locally for voice-chat playback."""

import asyncio
import logging
import os
import tempfile
from typing import Optional

import yt_dlp

YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={}"
DOWNLOAD_DIR = "ARUSHxVCBOT6BtojOs3CnEsDOE4sK1z"
logger = logging.getLogger(__name__)


def _add_cookiefile_option(options: dict) -> None:
    cookie_file = os.getenv("COOKIES_FILE")
    if cookie_file and os.path.isfile(cookie_file):
        options["cookiefile"] = cookie_file
        return

    cookie_contents = os.getenv("YOUTUBE_COOKIES")
    if cookie_contents:
        cookie_contents = cookie_contents.replace("\\n", "\n").replace("\\t", "\t")
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
        options["cookiefile"] = local_cookie_file
    elif cookie_file:
        logger.warning("Configured YouTube cookies file is missing")


def normalize_youtube_url(link: str) -> str:
    """Accept a YouTube URL or bare video ID and return a watch URL."""
    value = str(link or "").strip()
    if value.startswith(("https://", "http://")):
        return value
    if not value:
        raise ValueError("A YouTube URL or video ID is required")
    return YOUTUBE_WATCH_URL.format(value)


def _download_sync(link: str, *, video: bool, download_dir: str) -> Optional[str]:
    os.makedirs(download_dir, exist_ok=True)
    options = {
        "format": "best[ext=mp4]/best" if video else "bestaudio/best",
        "outtmpl": os.path.join(download_dir, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "overwrites": False,
    }

    _add_cookiefile_option(options)

    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(normalize_youtube_url(link), download=True)
        if not info:
            return None

        candidates = [info.get("filepath")]
        candidates.extend(
            item.get("filepath") for item in info.get("requested_downloads", [])
        )
        candidates.append(downloader.prepare_filename(info))
        for path in candidates:
            if path and os.path.isfile(path) and os.path.getsize(path) > 0:
                return path
    return None


async def download_youtube_media(
    link: str, *, video: bool = False, download_dir: Optional[str] = None
) -> Optional[str]:
    """Run yt-dlp off the event loop and return the downloaded file path."""
    try:
        return await asyncio.to_thread(
            _download_sync,
            link,
            video=video,
            download_dir=download_dir or DOWNLOAD_DIR,
        )
    except Exception as error:
        logger.warning("YouTube media download failed (%s)", type(error).__name__)
        return None
