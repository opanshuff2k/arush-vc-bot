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

metadata_path = (
    Path(__file__).resolve().parents[1]
    / "ARUSHxVCBOT"
    / "platforms"
    / "youtube_metadata.py"
)
spec = importlib.util.spec_from_file_location("youtube_metadata", metadata_path)
youtube_metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(youtube_metadata)


class FakeYoutubeDL:
    last_target = None
    result = {
        "entries": [
            {
                "id": "dQw4w9WgXcQ",
                "title": "Example track",
                "duration": 213,
            }
        ]
    }

    def __init__(self, options):
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def extract_info(self, target, download):
        type(self).last_target = target
        self.target = target
        self.download = download
        return self.result


class YoutubeMetadataTests(unittest.TestCase):
    def test_search_query_returns_track_details(self):
        factory = Mock(side_effect=FakeYoutubeDL)
        with patch.object(youtube_metadata.yt_dlp, "YoutubeDL", factory):
            details = asyncio.run(
                youtube_metadata.fetch_youtube_track("Example track")
            )

        self.assertEqual(FakeYoutubeDL.last_target, "ytsearch1:Example track")
        options = factory.call_args.args[0]
        self.assertEqual(
            options["extractor_args"]["youtube"]["player_client"],
            ["web_embedded"],
        )
        self.assertIn("node", options["js_runtimes"])
        self.assertEqual(details["vidid"], "dQw4w9WgXcQ")
        self.assertEqual(details["duration_min"], "3:33")
        self.assertEqual(
            details["link"], "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        self.assertEqual(
            details["thumb"],
            "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        )

    def test_video_id_is_converted_to_watch_url(self):
        factory = Mock(side_effect=FakeYoutubeDL)
        with patch.object(youtube_metadata.yt_dlp, "YoutubeDL", factory):
            details = asyncio.run(
                youtube_metadata.fetch_youtube_track(
                    "dQw4w9WgXcQ", videoid=True
                )
            )
        self.assertEqual(details["vidid"], "dQw4w9WgXcQ")
        self.assertEqual(factory.call_args.args[0]["extract_flat"], True)
        self.assertEqual(
            FakeYoutubeDL.last_target,
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )

    def test_uses_configured_cookie_file_when_it_exists(self):
        factory = Mock(side_effect=FakeYoutubeDL)
        with patch.dict(os.environ, {"COOKIES_FILE": "private-cookies.txt"}):
            with patch.object(youtube_metadata.os.path, "isfile", return_value=True):
                with patch.object(youtube_metadata.yt_dlp, "YoutubeDL", factory):
                    asyncio.run(youtube_metadata.fetch_youtube_track("Example track"))
        options = factory.call_args.args[0]
        self.assertEqual(options["cookiefile"], "private-cookies.txt")
        self.assertEqual(options["retries"], 5)

    def test_materializes_secret_cookie_variable_with_private_permissions(self):
        cookie_contents = "# Netscape HTTP Cookie File\nexample.com\tTRUE\t/\tFALSE\t0\tSID\tsecret\n"
        with tempfile.TemporaryDirectory() as directory:
            cookie_path = os.path.join(directory, "missing-cookies.txt")
            factory = Mock(side_effect=FakeYoutubeDL)
            with patch.dict(
                os.environ,
                {"COOKIES_FILE": cookie_path, "YOUTUBE_COOKIES": cookie_contents},
            ):
                with patch.object(
                    youtube_metadata.tempfile, "gettempdir", return_value=directory
                ):
                    with patch.object(youtube_metadata.yt_dlp, "YoutubeDL", factory):
                        asyncio.run(
                            youtube_metadata.fetch_youtube_track("Example track")
                        )

            materialized_path = factory.call_args.args[0]["cookiefile"]
            with open(materialized_path, encoding="utf-8") as cookie_file:
                self.assertEqual(cookie_file.read(), cookie_contents)
            self.assertEqual(stat.S_IMODE(os.stat(materialized_path).st_mode), 0o600)

    def test_decodes_escaped_newlines_and_tabs(self):
        escaped = "# Netscape HTTP Cookie File\\n.example.com\\tTRUE\\t/\\tTRUE\\t0\\tSID\\tfake\\n"
        expected = escaped.replace("\\n", "\n").replace("\\t", "\t")
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                {
                    "COOKIES_FILE": os.path.join(directory, "missing.txt"),
                    "YOUTUBE_COOKIES": escaped,
                },
            ):
                with patch.object(
                    youtube_metadata.tempfile, "gettempdir", return_value=directory
                ):
                    with patch.object(youtube_metadata.yt_dlp, "YoutubeDL", Mock(side_effect=FakeYoutubeDL)) as factory:
                        asyncio.run(
                            youtube_metadata.fetch_youtube_track("Example track")
                        )
            with open(factory.call_args.args[0]["cookiefile"], encoding="utf-8") as cookie_file:
                self.assertEqual(cookie_file.read(), expected)

    def test_empty_search_results_raise_clear_error(self):
        class EmptyYoutubeDL(FakeYoutubeDL):
            def extract_info(self, target, download):
                return {"entries": []}

        with patch.object(youtube_metadata.yt_dlp, "YoutubeDL", EmptyYoutubeDL):
            with self.assertRaisesRegex(LookupError, "no tracks"):
                asyncio.run(youtube_metadata.fetch_youtube_track("no match"))


if __name__ == "__main__":
    unittest.main()
