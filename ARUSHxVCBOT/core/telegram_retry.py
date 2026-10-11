import asyncio


async def retry_telegram_flood_wait(
    operation,
    *,
    flood_wait_error,
    logger,
    operation_name,
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
            await sleep(wait_seconds)
