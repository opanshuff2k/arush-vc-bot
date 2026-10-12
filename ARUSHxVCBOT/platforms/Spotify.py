# Copyright (c) 2025 Nand Yaduwanshi <NoxxOP>
# Location: Supaul, Bihar
#
# All rights reserved.
#
# This code is the intellectual property of Nand Yaduwanshi.
# You are not allowed to copy, modify, redistribute, or use this
# code for commercial or personal projects without explicit permission.
#
# Allowed:
# - Forking for personal learning
# - Submitting improvements via pull requests
#
# Not Allowed:
# - Claiming this code as your own
# - Re-uploading without credit or permission
# - Selling or using commercially
#
# Contact for permissions:
# Email: badboy809075@gmail.com

import asyncio
import json
import logging
import os
import re
from pathlib import Path

import spotipy
from spotipy.cache_handler import CacheFileHandler
from spotipy.oauth2 import SpotifyPKCE

import config
from ARUSHxVCBOT.platforms.youtube_metadata import fetch_youtube_track

LOGGER = logging.getLogger(__name__)


def _seed_token_cache(cache_path: str, cache_json: str = None):
    """Seed a private Spotipy cache from Railway's one-time bootstrap secret."""
    path = Path(cache_path)
    handler = CacheFileHandler(cache_path=str(path))

    cached = handler.get_cached_token()
    if cached is not None or path.exists() or not cache_json:
        return cached

    try:
        token_info = json.loads(cache_json)
    except (TypeError, json.JSONDecodeError):
        LOGGER.warning("Spotify PKCE bootstrap cache is not valid JSON")
        return None

    if not isinstance(token_info, dict):
        LOGGER.warning("Spotify PKCE bootstrap cache has an invalid structure")
        return None
    if not token_info.get("access_token") or not token_info.get("refresh_token"):
        LOGGER.warning("Spotify PKCE bootstrap cache is missing required tokens")
        return None
    if "expires_at" not in token_info:
        LOGGER.warning("Spotify PKCE bootstrap cache is missing its expiry")
        return None

    # A blank scope is valid for public catalog metadata and avoids requesting
    # permissions to private user data.
    token_info.setdefault("scope", "")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as cache_file:
            json.dump(token_info, cache_file, separators=(",", ":"))
        os.chmod(path, 0o600)
    except FileExistsError:
        pass
    except OSError as exc:
        LOGGER.warning("Could not initialize Spotify PKCE cache (%s)", type(exc).__name__)
        return None

    return handler.get_cached_token()


class SpotifyAPI:
    def __init__(self):
        self.regex = r"^(https:\/\/open.spotify.com\/)(.*)$"
        self.client_id = config.SPOTIFY_CLIENT_ID
        self.redirect_uri = config.SPOTIFY_REDIRECT_URI
        self.cache_path = config.SPOTIFY_TOKEN_CACHE_PATH
        self.auth_manager = None
        self.spotify = None
        self.error_reason = "Spotify PKCE token cache is not configured"

        if not self.client_id:
            self.error_reason = "Spotify Client ID is missing"
            return
        if not self.redirect_uri:
            self.error_reason = "Spotify PKCE redirect URI is missing"
            return

        token_info = _seed_token_cache(
            self.cache_path, config.SPOTIFY_TOKEN_CACHE_JSON
        )
        if (
            not isinstance(token_info, dict)
            or not token_info.get("refresh_token")
            or "scope" not in token_info
        ):
            LOGGER.info("Spotify PKCE is not ready: token cache is missing or incomplete")
            return

        try:
            self.cache_handler = CacheFileHandler(cache_path=self.cache_path)
            self.auth_manager = SpotifyPKCE(
                client_id=self.client_id,
                redirect_uri=self.redirect_uri,
                scope="",
                cache_handler=self.cache_handler,
                open_browser=False,
            )
            self.spotify = spotipy.Spotify(auth_manager=self.auth_manager)
            self.error_reason = None
        except Exception as exc:
            self.error_reason = "Spotify PKCE could not be initialized"
            LOGGER.warning("Spotify PKCE initialization failed (%s)", type(exc).__name__)

    async def valid(self, link: str):
        return bool(re.search(self.regex, link))

    def _require_client(self):
        if self.spotify is None:
            raise RuntimeError(self.error_reason or "Spotify PKCE is not configured")
        return self.spotify

    async def track(self, link: str):
        client = self._require_client()
        track = await asyncio.to_thread(client.track, link)
        title = track.get("name")
        if not title:
            raise LookupError("Spotify returned incomplete track metadata")

        artists = [
            artist["name"]
            for artist in track.get("artists") or []
            if artist.get("name") and "Various Artists" not in artist["name"]
        ]
        query = " ".join([title, *artists])
        details = await fetch_youtube_track(query)
        return details, details["vidid"]

    async def playlist(self, url):
        client = self._require_client()
        playlist = await asyncio.to_thread(client.playlist, url)
        playlist_id = playlist["id"]
        results = []
        for item in playlist["tracks"]["items"]:
            music_track = item["track"]
            info = music_track["name"]
            for artist in music_track["artists"]:
                fetched = f' {artist["name"]}'
                if "Various Artists" not in fetched:
                    info += fetched
            results.append(info)
        return results, playlist_id

    async def album(self, url):
        client = self._require_client()
        album = await asyncio.to_thread(client.album, url)
        album_id = album["id"]
        results = []
        for item in album["tracks"]["items"]:
            info = item["name"]
            for artist in item["artists"]:
                fetched = f' {artist["name"]}'
                if "Various Artists" not in fetched:
                    info += fetched
            results.append(info)
        return results, album_id

    async def artist(self, url):
        client = self._require_client()
        artistinfo = await asyncio.to_thread(client.artist, url)
        artist_id = artistinfo["id"]
        artisttoptracks = await asyncio.to_thread(client.artist_top_tracks, url)
        results = []
        for item in artisttoptracks["tracks"]:
            info = item["name"]
            for artist in item["artists"]:
                fetched = f' {artist["name"]}'
                if "Various Artists" not in fetched:
                    info += fetched
            results.append(info)
        return results, artist_id


# ©️ Copyright Reserved - @NoxxOP  Nand Yaduwanshi
# 🔗 GitHub : https://github.com/opanshuff2k/arush-vc-bot
