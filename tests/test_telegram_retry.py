import asyncio
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "ARUSHxVCBOT"
    / "core"
    / "telegram_retry.py"
)
SPEC = importlib.util.spec_from_file_location("telegram_retry", MODULE_PATH)
telegram_retry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(telegram_retry)


class FakeFloodWait(Exception):
    def __init__(self, value):
        self.value = value


class TelegramFloodWaitRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_waits_for_server_duration_then_retries(self):
        attempts = 0
        waits = []
        logger = Mock()

        async def operation():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise FakeFloodWait(2923)
            return "started"

        async def fake_sleep(seconds):
            waits.append(seconds)

        result = await telegram_retry.retry_telegram_flood_wait(
            operation,
            flood_wait_error=FakeFloodWait,
            logger=logger,
            operation_name="bot authorization",
            sleep=fake_sleep,
        )

        self.assertEqual(result, "started")
        self.assertEqual(attempts, 2)
        self.assertEqual(waits, [2928])
        logger.warning.assert_called_once()

    async def test_returns_without_sleep_when_no_flood_wait_occurs(self):
        waits = []

        async def operation():
            return "started"

        async def fake_sleep(seconds):
            waits.append(seconds)

        result = await telegram_retry.retry_telegram_flood_wait(
            operation,
            flood_wait_error=FakeFloodWait,
            logger=Mock(),
            operation_name="bot authorization",
            sleep=fake_sleep,
        )

        self.assertEqual(result, "started")
        self.assertEqual(waits, [])

    async def test_does_not_swallow_other_exceptions(self):
        async def operation():
            raise RuntimeError("unexpected failure")

        with self.assertRaisesRegex(RuntimeError, "unexpected failure"):
            await telegram_retry.retry_telegram_flood_wait(
                operation,
                flood_wait_error=FakeFloodWait,
                logger=Mock(),
                operation_name="bot authorization",
                sleep=asyncio.sleep,
            )


if __name__ == "__main__":
    unittest.main()
