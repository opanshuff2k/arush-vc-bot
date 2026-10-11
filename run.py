"""Keep Render's web service healthy and supervise the Telegram bot process."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Sequence

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("arush-vc-bot.runner")


async def handle_http_request(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    """Answer Render health checks without importing the bot application."""
    status = "200 OK"
    body = b"ok\n"
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=5)
        parts = request_line.decode("ascii", "replace").strip().split()
        if len(parts) != 3:
            status, body = "400 Bad Request", b"bad request\n"
        else:
            method, target, _version = parts
            header_bytes = 0
            while True:
                header = await asyncio.wait_for(reader.readline(), timeout=5)
                header_bytes += len(header)
                if not header or header in (b"\r\n", b"\n"):
                    break
                if header_bytes > 8192:
                    status, body = "431 Request Header Fields Too Large", b"headers too large\n"
                    break

            path = target.split("?", 1)[0]
            if status == "200 OK" and method != "GET":
                status, body = "405 Method Not Allowed", b"method not allowed\n"
            elif status == "200 OK" and path not in ("/", "/healthz"):
                status, body = "404 Not Found", b"not found\n"
    except (asyncio.TimeoutError, ConnectionError, OSError):
        status, body = "400 Bad Request", b"bad request\n"

    response = (
        f"HTTP/1.1 {status}\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "Cache-Control: no-store\r\n"
        "\r\n"
    ).encode("ascii") + body
    try:
        writer.write(response)
        await writer.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass


async def wait_before_restart(stop_event: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        pass


async def supervise_bot(
    stop_event: asyncio.Event,
    command: Sequence[str] | None = None,
) -> None:
    """Restart the bot with capped exponential backoff until shutdown."""
    bot_command = list(command or (sys.executable, "-m", "ARUSHxVCBOT"))
    restart_delay = 2.0

    while not stop_event.is_set():
        child_environment = os.environ.copy()
        child_environment["ARUSH_SUPERVISED"] = "1"
        LOGGER.info("Starting Telegram bot process")
        try:
            process = await asyncio.create_subprocess_exec(
                *bot_command,
                env=child_environment,
            )
        except OSError:
            LOGGER.exception("Could not start the Telegram bot process")
            await wait_before_restart(stop_event, restart_delay)
            restart_delay = min(restart_delay * 2, 60.0)
            continue

        process_wait = asyncio.create_task(process.wait())
        stop_wait = asyncio.create_task(stop_event.wait())
        done, pending = await asyncio.wait(
            (process_wait, stop_wait),
            return_when=asyncio.FIRST_COMPLETED,
        )

        if stop_wait in done:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process_wait, timeout=10)
                except asyncio.TimeoutError:
                    process.kill()
                    await process_wait
            else:
                await process_wait
            for task in pending:
                task.cancel()
            return

        stop_wait.cancel()
        await asyncio.gather(stop_wait, return_exceptions=True)
        return_code = process_wait.result()
        LOGGER.error(
            "Telegram bot exited with status %s; restarting in %.0f seconds",
            return_code,
            restart_delay,
        )
        await wait_before_restart(stop_event, restart_delay)
        restart_delay = min(restart_delay * 2, 60.0)


async def main() -> None:
    try:
        port = int(os.environ.get("PORT", "10000"))
    except ValueError as error:
        raise SystemExit("PORT must be an integer between 1 and 65535") from error
    if not 1 <= port <= 65535:
        raise SystemExit("PORT must be an integer between 1 and 65535")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(shutdown_signal, stop_event.set)

    server = await asyncio.start_server(
        handle_http_request,
        host="0.0.0.0",
        port=port,
        limit=8192,
    )
    LOGGER.info("Health handler listening on 0.0.0.0:%s (/healthz)", port)

    supervisor_task = asyncio.create_task(supervise_bot(stop_event))
    try:
        async with server:
            await stop_event.wait()
    finally:
        server.close()
        await server.wait_closed()
        stop_event.set()
        await supervisor_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
