import asyncio
import importlib.util
import json
import os
import stat
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


_MISSING = object()


class FakeCacheFileHandler:
    def __init__(self, cache_path):
        self.cache_path = Path(cache_path)

    def get_cached_token(self):
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def save_token_to_cache(self, token_info):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(token_info), encoding="utf-8")
        os.chmod(self.cache_path, 0o600)


class FakeSpotifyPKCE:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.__class__.instances.append(self)


class FakeSpotifyClient:
    def __init__(self, auth_manager=None):
        self.auth_manager = auth_manager

    def track(self, link):
        self.link = link
        return {
            "name": "Example Song",
            "artists": [
                {"name": "Example Artist"},
                {"name": "Various Artists"},
            ],
        }



def load_spotify_module():
    root = Path(__file__).resolve().parents[1]
    module_names = (
        "ARUSHxVCBOT",
        "ARUSHxVCBOT.platforms",
        "ARUSHxVCBOT.platforms.youtube_metadata",
        "spotipy",
        "spotipy.cache_handler",
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
        spotipy_module.Spotify = FakeSpotifyClient
        cache_module = types.ModuleType("spotipy.cache_handler")
        cache_module.CacheFileHandler = FakeCacheFileHandler
        oauth_module = types.ModuleType("spotipy.oauth2")
        oauth_module.SpotifyPKCE = FakeSpotifyPKCE
        spotipy_module.cache_handler = cache_module
        spotipy_module.oauth2 = oauth_module

        config_module = types.ModuleType("config")
        config_module.SPOTIFY_CLIENT_ID = "test-client-id"
        config_module.SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
        config_module.SPOTIFY_TOKEN_CACHE_PATH = "/tmp/unused-test-cache.json"
        config_module.SPOTIFY_TOKEN_CACHE_JSON = None

        sys.modules["ARUSHxVCBOT"] = bot_package
        sys.modules["ARUSHxVCBOT.platforms"] = platforms_package
        sys.modules["ARUSHxVCBOT.platforms.youtube_metadata"] = metadata_module
        sys.modules["spotipy"] = spotipy_module
        sys.modules["spotipy.cache_handler"] = cache_module
        sys.modules["spotipy.oauth2"] = oauth_module
        sys.modules["config"] = config_module

        path = root / "ARUSHxVCBOT" / "platforms" / "Spotify.py"
        spec = importlib.util.spec_from_file_location("spotify_platform_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, config_module
    finally:
        for name, old_value in previous.items():
            if old_value is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old_value


spotify_module, fake_config = load_spotify_module()


class SpotifyMetadataTests(unittest.TestCase):
    def setUp(self):
        FakeSpotifyPKCE.instances.clear()

    def test_client_id_only_initializes_pkce_from_secure_bootstrap_cache(self):
        cache_json = json.dumps(
            {
                "access_token": "test-access-token",
                "refresh_token": "test-refresh-token",
                "expires_at": 4102444800,
                "scope": "",
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / ".spotify-token-cache.json"
            fake_config.SPOTIFY_CLIENT_ID = "test-client-id"
            fake_config.SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
            fake_config.SPOTIFY_TOKEN_CACHE_PATH = str(cache_path)
            fake_config.SPOTIFY_TOKEN_CACHE_JSON = cache_json

            api = spotify_module.SpotifyAPI()

            self.assertIsNotNone(api.spotify)
            self.assertIsNone(api.error_reason)
            self.assertEqual(api.auth_manager.kwargs["client_id"], "test-client-id")
            self.assertEqual(
                api.auth_manager.kwargs["redirect_uri"],
                "http://127.0.0.1:8888/callback",
            )
            self.assertEqual(api.auth_manager.kwargs["scope"], "")
            self.assertFalse(api.auth_manager.kwargs["open_browser"])
            self.assertNotIn("client_secret", api.auth_manager.kwargs)
            self.assertEqual(
                stat.S_IMODE(cache_path.stat().st_mode),
                0o600,
            )
            self.assertEqual(
                json.loads(cache_path.read_text(encoding="utf-8"))["refresh_token"],
                "test-refresh-token",
            )

    def test_missing_cache_does_not_start_interactive_auth(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_config.SPOTIFY_CLIENT_ID = "test-client-id"
            fake_config.SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
            fake_config.SPOTIFY_TOKEN_CACHE_PATH = str(
                Path(temp_dir) / "missing-cache.json"
            )
            fake_config.SPOTIFY_TOKEN_CACHE_JSON = None

            api = spotify_module.SpotifyAPI()

            self.assertIsNone(api.spotify)
            self.assertIsNone(api.auth_manager)
            self.assertIn("token cache", api.error_reason)
            self.assertEqual(FakeSpotifyPKCE.instances, [])

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

    def test_track_fails_clearly_when_pkce_client_is_missing(self):
        api = spotify_module.SpotifyAPI.__new__(spotify_module.SpotifyAPI)
        api.spotify = None
        api.error_reason = "Spotify PKCE token cache is not configured"
        with self.assertRaisesRegex(RuntimeError, "Spotify PKCE"):
            asyncio.run(api.track("https://open.spotify.com/track/example"))


if __name__ == "__main__":
    unittest.main()
