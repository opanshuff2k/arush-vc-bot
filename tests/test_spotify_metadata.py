import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


_MISSING = object()


def load_spotify_module():
    root = Path(__file__).resolve().parents[1]
    module_names = (
        "ARUSHxVCBOT",
        "ARUSHxVCBOT.platforms",
        "ARUSHxVCBOT.platforms.youtube_metadata",
        "spotipy",
        "spotipy.oauth2",
        "config",
    )
    previous = {name: sys.modules.get(name, _MISSING) for name in module_names}

    try:
        bot_package = types.ModuleType("ARUSHxVCBOT")
        bot_package.__path__ = [str(root / "ARUSHxVCBOT")]
        platforms_package = types.ModuleType("ARUSHxVCBOT.platforms")
        platforms_package.__path__ = [str(root / "ARUSHxVCBOT" / "platforms")]

        metadata_module = types.ModuleType(
            "ARUSHxVCBOT.platforms.youtube_metadata"
        )
        metadata_module.fetch_youtube_track = AsyncMock()

        spotipy_module = types.ModuleType("spotipy")
        spotipy_module.Spotify = lambda **kwargs: None
        oauth_module = types.ModuleType("spotipy.oauth2")
        oauth_module.SpotifyClientCredentials = lambda *args, **kwargs: None
        spotipy_module.oauth2 = oauth_module

        config_module = types.ModuleType("config")
        config_module.SPOTIFY_CLIENT_ID = "test-client-id"
        config_module.SPOTIFY_CLIENT_SECRET = "test-client-secret"

        sys.modules["ARUSHxVCBOT"] = bot_package
        sys.modules["ARUSHxVCBOT.platforms"] = platforms_package
        sys.modules["ARUSHxVCBOT.platforms.youtube_metadata"] = metadata_module
        sys.modules["spotipy"] = spotipy_module
        sys.modules["spotipy.oauth2"] = oauth_module
        sys.modules["config"] = config_module

        path = root / "ARUSHxVCBOT" / "platforms" / "Spotify.py"
        spec = importlib.util.spec_from_file_location("spotify_platform_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, old_value in previous.items():
            if old_value is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old_value


spotify_module = load_spotify_module()


class FakeSpotifyClient:
    def track(self, link):
        self.link = link
        return {
            "name": "Example Song",
            "artists": [
                {"name": "Example Artist"},
                {"name": "Various Artists"},
            ],
        }


class SpotifyMetadataTests(unittest.TestCase):
    def test_track_uses_spotify_metadata_and_current_youtube_resolver(self):
        api = spotify_module.SpotifyAPI.__new__(spotify_module.SpotifyAPI)
        api.spotify = FakeSpotifyClient()
        youtube_details = {
            "title": "Example Song Example Artist",
            "link": "https://youtube.com/watch?v=video123",
            "vidid": "video123",
            "duration_min": "3:00",
            "thumb": "https://i.ytimg.com/vi/video123/hqdefault.jpg",
        }

        with patch.object(
            spotify_module,
            "fetch_youtube_track",
            new=AsyncMock(return_value=youtube_details),
        ) as resolver:
            details, track_id = asyncio.run(
                api.track("https://open.spotify.com/track/example")
            )

        self.assertEqual(api.spotify.link, "https://open.spotify.com/track/example")
        resolver.assert_awaited_once_with("Example Song Example Artist")
        self.assertEqual(details, youtube_details)
        self.assertEqual(track_id, "video123")

    def test_track_fails_clearly_when_api_client_is_missing(self):
        api = spotify_module.SpotifyAPI.__new__(spotify_module.SpotifyAPI)
        api.spotify = None
        with self.assertRaisesRegex(RuntimeError, "credentials are not configured"):
            asyncio.run(api.track("https://open.spotify.com/track/example"))


if __name__ == "__main__":
    unittest.main()
