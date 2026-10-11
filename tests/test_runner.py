import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

from run import handle_http_request, supervise_bot


class HealthHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = await asyncio.start_server(
            handle_http_request,
            host="127.0.0.1",
            port=0,
        )
        self.port = self.server.sockets[0].getsockname()[1]

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    async def request(self, target="/healthz", method="GET"):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        writer.write(f"{method} {target} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode())
        await writer.drain()
        response = await reader.read()
        writer.close()
        await writer.wait_closed()
        return response

    async def test_health_endpoint_returns_200(self):
        response = await self.request()
        self.assertIn(b"HTTP/1.1 200 OK", response)
        self.assertTrue(response.endswith(b"ok\n"))

    async def test_unknown_path_returns_404(self):
        response = await self.request("/unknown")
        self.assertIn(b"HTTP/1.1 404 Not Found", response)

    async def test_non_get_method_returns_405(self):
        response = await self.request("/healthz", method="POST")
        self.assertIn(b"HTTP/1.1 405 Method Not Allowed", response)


class SupervisorTests(unittest.IsolatedAsyncioTestCase):
    async def test_restarts_child_after_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "attempts.txt"
            child_code = (
                "from pathlib import Path; import os; "
                "Path(os.environ['RUNNER_TEST_MARKER']).open('a').write('start\\n'); "
                "raise SystemExit(7)"
            )
            environment = os.environ.copy()
            environment["RUNNER_TEST_MARKER"] = str(marker)
            previous_environment = os.environ.copy()
            os.environ.update({"RUNNER_TEST_MARKER": str(marker)})
            stop_event = asyncio.Event()
            supervisor = asyncio.create_task(
                supervise_bot(
                    stop_event,
                    command=(sys.executable, "-c", child_code),
                )
            )
            try:
                deadline = asyncio.get_running_loop().time() + 6
                while asyncio.get_running_loop().time() < deadline:
                    attempts = marker.read_text().count("start\n") if marker.exists() else 0
                    if attempts >= 2:
                        break
                    await asyncio.sleep(0.05)
                else:
                    self.fail("Supervisor did not restart the child process")
            finally:
                stop_event.set()
                await asyncio.wait_for(supervisor, timeout=3)
                os.environ.clear()
                os.environ.update(previous_environment)

            self.assertGreaterEqual(marker.read_text().count("start\n"), 2)


if __name__ == "__main__":
    unittest.main()
