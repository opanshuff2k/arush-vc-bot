import asyncio


async def disconnect_uninitialized_client(client):
    """Reset a partially connected Pyrogram client before retrying its start."""
    if getattr(client, "is_connected", False) and not getattr(
        client, "is_initialized", False
    ):
        await client.disconnect()


async def retry_telegram_flood_wait(
    operation,
    *,
    flood_wait_error,
    logger,
    operation_name,
    before_retry=None,
    sleep=asyncio.sleep,
):
    """Retry a Telegram operation after honoring the server-provided FloodWait."""
    while True:
        try:
            return await operation()
        except flood_wait_error as error:
            wait_seconds = max(0, int(error.value)) + 5
            logger.warning(
                "Telegram rate-limited %s; keeping the process alive and retrying "
                "in %s seconds.",
                operation_name,
                wait_seconds,
            )
            if before_retry is not None:
                await before_retry()
            await sleep(wait_seconds)
