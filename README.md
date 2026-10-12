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
If YouTube requires an authenticated session, provide a valid Netscape-format
cookies file on the host and set `COOKIES_FILE` in `.env` to its path. Keep the
file private; it is ignored by Git and must not be committed or shared.

## Branding

- Maintainer: **ARUSH**
- Bot name: **@ARUSHxVC_BOT**
- Repository: https://github.com/opanshuff2k/arush-vc-bot

## License

GNU GPL v3. See [LICENSE](LICENSE). Original author notices and license terms must remain intact when this project is redistributed.
