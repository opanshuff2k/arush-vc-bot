import asyncio
import importlib.util
import os
import stat
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
            options = factory.call_args.args[0]
            self.assertEqual(options["format"], "bestaudio/best")
            self.assertEqual(
                options["extractor_args"]["youtube"]["player_client"],
                ["web_embedded"],
            )
            self.assertIn("node", options["js_runtimes"])

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
                cookie_output.write(
                    "# Netscape HTTP Cookie File\n"
                    "example.com\tTRUE\t/\tFALSE\t0\tSID\tfake\n"
                )
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

    def test_uses_cookie_contents_from_environment_variable(self):
        cookie_contents = "# Netscape HTTP Cookie File\nexample.com\tTRUE\t/\tFALSE\t0\tSID\tsecret\n"
        with tempfile.TemporaryDirectory() as directory:
            cookie_path = os.path.join(directory, "missing-cookies.txt")
            download_directory = os.path.join(directory, "downloads")
            factory = Mock(side_effect=FakeYoutubeDL)
            with patch.dict(
                os.environ,
                {"COOKIES_FILE": cookie_path, "YOUTUBE_COOKIES": cookie_contents},
            ):
                with patch.object(
                    youtube_downloader.tempfile, "gettempdir", return_value=directory
                ):
                    with patch.object(youtube_downloader.yt_dlp, "YoutubeDL", factory):
                        path = asyncio.run(
                            youtube_downloader.download_youtube_media(
                                "abc123", download_dir=download_directory
                            )
                        )

            options = factory.call_args.args[0]
            materialized_path = options["cookiefile"]
            with open(materialized_path, encoding="utf-8") as cookie_file:
                self.assertEqual(cookie_file.read(), cookie_contents)
            self.assertEqual(stat.S_IMODE(os.stat(materialized_path).st_mode), 0o600)
            self.assertTrue(path)

    def test_decodes_escaped_newlines_and_tabs_in_cookie_variable(self):
        escaped = "# Netscape HTTP Cookie File\\n.example.com\\tTRUE\\t/\\tTRUE\\t0\\tSID\\tfake\\n"
        expected = escaped.replace("\\n", "\n").replace("\\t", "\t")
        with tempfile.TemporaryDirectory() as directory:
            download_directory = os.path.join(directory, "downloads")
            with patch.dict(
                os.environ,
                {
                    "COOKIES_FILE": os.path.join(directory, "missing.txt"),
                    "YOUTUBE_COOKIES": escaped,
                },
            ):
                with patch.object(
                    youtube_downloader.tempfile, "gettempdir", return_value=directory
                ):
                    with patch.object(
                        youtube_downloader.yt_dlp,
                        "YoutubeDL",
                        Mock(side_effect=FakeYoutubeDL),
                    ) as factory:
                        asyncio.run(
                            youtube_downloader.download_youtube_media(
                                "abc123", download_dir=download_directory
                            )
                        )
            with open(factory.call_args.args[0]["cookiefile"], encoding="utf-8") as cookie_file:
                self.assertEqual(cookie_file.read(), expected)

    def test_rejects_invalid_cookie_format_without_logging_contents(self):
        sensitive_value = "DO_NOT_LOG_THIS_COOKIE_VALUE"
        invalid_cookie = (
            "example.com\tTRUE\t/\tFALSE\t0\tSID\t"
            f"{sensitive_value}\textra-field\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            factory = Mock(side_effect=FakeYoutubeDL)
            with patch.dict(
                os.environ,
                {
                    "COOKIES_FILE": os.path.join(directory, "missing.txt"),
                    "YOUTUBE_COOKIES": invalid_cookie,
                },
            ):
                with patch.object(youtube_downloader.yt_dlp, "YoutubeDL", factory):
                    with patch.object(youtube_downloader.logger, "warning") as warning:
                        asyncio.run(
                            youtube_downloader.download_youtube_media(
                                "abc123", download_dir=directory
                            )
                        )

            options = factory.call_args.args[0]
            self.assertNotIn("cookiefile", options)
            self.assertNotIn(
                sensitive_value,
                " ".join(str(call) for call in warning.call_args_list),
            )

    def test_redacts_cookie_details_from_yt_dlp_warnings(self):
        target_logger = Mock()
        safe_logger = youtube_downloader._SafeYtDlpLogger(target_logger)
        sensitive_value = "DO_NOT_LOG_THIS_COOKIE_VALUE"
        safe_logger.warning(
            "Skipping cookie file entry: .youtube.com\\tSID\\t" + sensitive_value
        )
        message = target_logger.warning.call_args.args[0]
        self.assertNotIn(sensitive_value, message)
        self.assertIn("redacted", message)

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
