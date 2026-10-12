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
a mode-`0600` temporary file at runtime. Never put cookie contents in GitHub or
chat; enter them directly in Railway Variables. Cookie files are ignored by Git.

## Branding

- Maintainer: **ARUSH**
- Bot name: **@ARUSHxVC_BOT**
- Repository: https://github.com/opanshuff2k/arush-vc-bot

## License

GNU GPL v3. See [LICENSE](LICENSE). Original author notices and license terms must remain intact when this project is redistributed.
