import importlib.util
import unittest
from enum import Enum
from pathlib import Path


compat_path = Path(__file__).resolve().parents[1] / "ntgcalls_compat.py"
spec = importlib.util.spec_from_file_location("ntgcalls_compat", compat_path)
ntgcalls_compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ntgcalls_compat)


class ConnectionState(Enum):
    CONNECTING = 1
    CONNECTED = 2
    CLOSED = 16


class FakeNTgCalls:
    def on_connection_change(self, callback):
        self.registered_callback = callback
        return "registered"


class AlreadyCompatibleNTgCalls:
    def on_disconnect(self, callback):
        self.registered_callback = callback


class NtgcallsCompatTests(unittest.TestCase):
    def test_bridges_disconnect_to_closed_state_only(self):
        module = type(
            "FakeNtgcalls",
            (),
            {"NTgCalls": FakeNTgCalls, "ConnectionState": ConnectionState},
        )
        self.assertTrue(ntgcalls_compat.ensure_on_disconnect_compat(module))

        client = FakeNTgCalls()
        called = []
        result = client.on_disconnect(called.append)
        self.assertEqual(result, "registered")
        client.registered_callback(123, ConnectionState.CONNECTED)
        self.assertEqual(called, [])
        client.registered_callback(123, ConnectionState.CLOSED)
        self.assertEqual(called, [123])

    def test_keeps_native_disconnect_method_when_present(self):
        module = type(
            "FakeNtgcalls",
            (),
            {"NTgCalls": AlreadyCompatibleNTgCalls, "ConnectionState": ConnectionState},
        )
        original = AlreadyCompatibleNTgCalls.on_disconnect
        self.assertTrue(ntgcalls_compat.ensure_on_disconnect_compat(module))
        self.assertIs(AlreadyCompatibleNTgCalls.on_disconnect, original)

    def test_returns_false_when_neither_callback_api_is_available(self):
        module = type("FakeNtgcalls", (), {"NTgCalls": object})
        self.assertFalse(ntgcalls_compat.ensure_on_disconnect_compat(module))


if __name__ == "__main__":
    unittest.main()
