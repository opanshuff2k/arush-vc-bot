# ARUSHxVC-BOT

A customized Telegram voice-chat music bot maintained by **ARUSH**.

> This project is a modified version of the original ShrutiMusic project by Nand Yaduwanshi (NoxxOP). Changes and rebranding were made by ARUSH in 2026. The project remains licensed under GNU GPL v3.

## Setup

1. Install Python, FFmpeg and the dependencies in `requirements.txt`.
2. Copy `.env.example` to `.env`.
3. Add your own Telegram, MongoDB and session credentials.
4. Start the bot through the supervised launcher:

```bash
bash start
```

`bash start` runs a small HTTP health handler for Render and supervises the Telegram bot process,
restarting it with backoff if it exits. The `/` and `/healthz` endpoints report process liveness;
they do not verify that Telegram or MongoDB is connected. Render's free web services may sleep
after inactivity, so this free deployment path cannot guarantee uninterrupted bot availability.

## Branding

- Maintainer: **ARUSH**
- Bot name: **@ARUSHxVC_BOT**
- Repository: https://github.com/opanshuff2k/arush-vc-bot

## License

GNU GPL v3. See [LICENSE](LICENSE). Original author notices and license terms must remain intact when this project is redistributed.
