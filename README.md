# ARUSHxVC-BOT

A customized Telegram voice-chat music bot maintained by **ARUSH**.

> This project is a modified version of the original ShrutiMusic project by Nand Yaduwanshi (NoxxOP). Changes and rebranding were made by ARUSH in 2026. The project remains licensed under GNU GPL v3.

## Setup

1. Install Python, FFmpeg and the dependencies in `requirements.txt`.
2. Copy `.env.example` to `.env`.
3. Add your own Telegram, MongoDB and session credentials.
4. Start the bot:

```bash
python3 -m ARUSHxVCBOT
```

### Optional YouTube cookies
If YouTube requires an authenticated session, either set `COOKIES_FILE` to a
private Netscape-format cookie file on the host, or set the Railway secret
variable `YOUTUBE_COOKIES` to the file's contents. The bot writes the latter to
a mode-`0600` temporary file at runtime, and decodes literal `\\n` / `\\t`
separators. Never put cookie contents in GitHub or chat; enter them directly in
Railway Variables. Cookie files are ignored by Git.

Set the Railway variable once; it is reused for later playback and deploys, so
you do not need to re-export cookies for every song. YouTube may invalidate a
session eventually, but the `The page needs to be reloaded` error can also come
from yt-dlp's logged-in player selection, which the bot handles automatically.

### Spotify links with Client ID only (PKCE)
Spotify links use Spotify only for public track metadata; playable audio still
comes from YouTube. This setup uses Authorization Code with PKCE, so no Spotify
Client Secret is required. It does require one-time authorization by a Spotify
user, a token cache, and a persistent Railway volume.

1. In the Spotify Developer Dashboard, add the exact redirect URI
   `http://127.0.0.1:8888/callback` to the app's Redirect URIs. Keep any other
   existing redirect URI if it is used elsewhere.
2. On a computer with a browser, install Spotipy and run the authorization
   helper. Set `SPOTIFY_CLIENT_ID` to the app's public Client ID first:

   ```bash
   python3 -m pip install 'spotipy>=2.26.0,<3'
   export SPOTIFY_CLIENT_ID='your-client-id'
   export SPOTIFY_REDIRECT_URI='http://127.0.0.1:8888/callback'
   python3 scripts/spotify_pkce_auth.py
   ```

   Sign in to Spotify and approve the request. The helper writes a private
   `.spotify-token-cache.json` file locally. Do not commit it or send its
   contents in chat.
3. In Railway, mount a **persistent volume** at `/data`. Set
   `SPOTIFY_CLIENT_ID`, `SPOTIFY_REDIRECT_URI`, and
   `SPOTIFY_TOKEN_CACHE_PATH=/data/.spotify-token-cache.json`. Set
   `SPOTIFY_TOKEN_CACHE_JSON` to the one-line JSON contents of the local cache
   file using Railway Variables. This value contains access and refresh tokens;
   treat it as a secret. The bot seeds the cache file on the volume at startup,
   then Spotipy refreshes and updates the persistent cache automatically.
4. After Railway has successfully started with the persistent cache, remove
   the bootstrap variable `SPOTIFY_TOKEN_CACHE_JSON` from Railway to avoid
   keeping a second copy of the token. The volume cache remains in use.

The helper requests no private-user scopes, so private playlists may not be
available. Spotify refresh tokens expire after six months; if authorization
expires, run the helper again and replace the bootstrap cache. The bot does not
play Spotify audio.

## Branding

- Maintainer: **ARUSH**
- Bot name: **@ARUSHxVC_BOT**
- Repository: https://github.com/opanshuff2k/arush-vc-bot

## License

GNU GPL v3. See [LICENSE](LICENSE). Original author notices and license terms must remain intact when this project is redistributed.
