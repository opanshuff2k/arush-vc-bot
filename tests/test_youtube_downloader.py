import asyncio
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

if "yt_dlp" not in sys.modules:
    sys.modules["yt_dlp"] = types.SimpleNamespace(YoutubeDL=None)

downloader_path = (
    Path(__file__).resolve().parents[1]
    / "ARUSHxVCBOT"
    / "platforms"
    / "youtube_downloader.py"
)
spec = importlib.util.spec_from_file_location("youtube_downloader", downloader_path)
youtube_downloader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(youtube_downloader)


class FakeYoutubeDL:
    def __init__(self, options):
        self.options = options
        self.path = os.path.join(
            options["outtmpl"].replace("%(id)s", "abc123").replace("%(ext)s", "webm")
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def extract_info(self, url, download):
        self.url = url
        self.download = download
        with open(self.path, "wb") as output:
            output.write(b"media")
        return {
            "id": "abc123",
            "ext": "webm",
            "requested_downloads": [{"filepath": self.path}],
        }

    def prepare_filename(self, info):
        return self.path


class EmptyYoutubeDL(FakeYoutubeDL):
    def extract_info(self, url, download):
        return None


class FailingYoutubeDL(FakeYoutubeDL):
    def extract_info(self, url, download):
        raise RuntimeError("extract failed")


class YoutubeDownloaderTests(unittest.TestCase):
    def test_normalizes_video_id_and_preserves_url(self):
        self.assertEqual(
            youtube_downloader.normalize_youtube_url("abc123"),
            "https://www.youtube.com/watch?v=abc123",
        )
        link = "https://youtu.be/abc123"
        self.assertEqual(youtube_downloader.normalize_youtube_url(link), link)

    def test_downloads_audio_in_a_worker_thread_using_audio_format(self):
        with tempfile.TemporaryDirectory() as directory:
            factory = Mock(side_effect=FakeYoutubeDL)
            with patch.object(youtube_downloader.yt_dlp, "YoutubeDL", factory):
                path = asyncio.run(
                    youtube_downloader.download_youtube_media(
                        "abc123", video=False, download_dir=directory
                    )
                )
            self.assertTrue(path)
            self.assertTrue(os.path.isfile(path))
            self.assertEqual(os.path.getsize(path), 5)
            self.assertEqual(factory.call_args.args[0]["format"], "bestaudio/best")

    def test_downloads_video_using_mp4_preferred_format(self):
        with tempfile.TemporaryDirectory() as directory:
            factory = Mock(side_effect=FakeYoutubeDL)
            with patch.object(youtube_downloader.yt_dlp, "YoutubeDL", factory):
                path = asyncio.run(
                    youtube_downloader.download_youtube_media(
                        "abc123", video=True, download_dir=directory
                    )
                )
            self.assertTrue(path)
            self.assertEqual(
                factory.call_args.args[0]["format"], "best[ext=mp4]/best"
            )

    def test_uses_configured_cookie_file_for_download(self):
        with tempfile.TemporaryDirectory() as directory:
            cookie_file = os.path.join(directory, "cookies.txt")
            with open(cookie_file, "w", encoding="utf-8") as cookie_output:
                cookie_output.write("# Netscape HTTP Cookie File\n")
            factory = Mock(side_effect=FakeYoutubeDL)
            with patch.dict(os.environ, {"COOKIES_FILE": cookie_file}):
                with patch.object(youtube_downloader.yt_dlp, "YoutubeDL", factory):
                    path = asyncio.run(
                        youtube_downloader.download_youtube_media(
                            "abc123", download_dir=directory
                        )
                    )
            self.assertTrue(path)
            options = factory.call_args.args[0]
            self.assertEqual(options["cookiefile"], cookie_file)
            self.assertEqual(options["retries"], 5)
            self.assertEqual(options["fragment_retries"], 5)

    def test_returns_none_when_extractor_produces_no_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(youtube_downloader.yt_dlp, "YoutubeDL", EmptyYoutubeDL):
                path = asyncio.run(
                    youtube_downloader.download_youtube_media(
                        "abc123", download_dir=directory
                    )
                )
            self.assertIsNone(path)

    def test_returns_none_when_extractor_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(youtube_downloader.yt_dlp, "YoutubeDL", FailingYoutubeDL):
                path = asyncio.run(
                    youtube_downloader.download_youtube_media(
                        "abc123", download_dir=directory
                    )
                )
            self.assertIsNone(path)


if __name__ == "__main__":
    unittest.main()
