#!/usr/bin/env python3
"""Authorize the bot's Spotify PKCE client on a local computer once."""

import argparse
import os
import sys
from pathlib import Path

from spotipy.cache_handler import CacheFileHandler
from spotipy.oauth2 import SpotifyPKCE

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"


def main():
    parser = argparse.ArgumentParser(
        description="Create a local Spotify PKCE token cache for Railway."
    )
    parser.add_argument(
        "--cache-path",
        default=".spotify-token-cache.json",
        help="where to write the private token cache (default: %(default)s)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing local token cache after authorization",
    )
    args = parser.parse_args()

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", DEFAULT_REDIRECT_URI)
    if not client_id:
        print("Set SPOTIFY_CLIENT_ID in your local shell first.", file=sys.stderr)
        return 2

    cache_path = Path(args.cache_path).expanduser().resolve()
    if cache_path.exists() and not args.force:
        print(
            f"Cache already exists at {cache_path}; use --force to replace it.",
            file=sys.stderr,
        )
        return 2
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    cache_handler = CacheFileHandler(cache_path=str(cache_path))
    auth_manager = SpotifyPKCE(
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope="",
        cache_handler=cache_handler,
        open_browser=True,
    )

    try:
        # The access token is intentionally not printed or returned to stdout.
        auth_manager.get_access_token(check_cache=False)
    except Exception as exc:
        print(
            f"Spotify PKCE authorization failed ({type(exc).__name__}). "
            "Check the app's exact redirect URI and try again.",
            file=sys.stderr,
        )
        return 1

    token_info = cache_handler.get_cached_token()
    if not isinstance(token_info, dict) or not token_info.get("refresh_token"):
        print(
            "Authorization completed, but no refresh token was saved. "
            "Do not use this cache; retry authorization.",
            file=sys.stderr,
        )
        return 1

    token_info.setdefault("scope", "")
    cache_handler.save_token_to_cache(token_info)
    os.chmod(cache_path, 0o600)
    print("Spotify authorization completed.")
    print(f"Private token cache saved to: {cache_path}")
    print(
        "Set Railway's SPOTIFY_TOKEN_CACHE_JSON variable from this file's "
        "contents. The cache contains credentials; transfer it only through "
        "Railway's secret Variables UI, never through chat or GitHub."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
