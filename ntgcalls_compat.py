"""Compatibility adapter for PyTgCalls and ntgcalls callback APIs."""


def ensure_on_disconnect_compat(ntgcalls_module) -> bool:
    """Ensure NTgCalls exposes the disconnect callback PyTgCalls 1.2.9 expects.

    Some ntgcalls 1.x releases expose ``on_connection_change`` but not
    ``on_disconnect``. PyTgCalls uses the latter only to clear per-call cache
    after a call closes, so bridge that callback to the CLOSED state.
    """
    client_type = getattr(ntgcalls_module, "NTgCalls", None)
    if client_type is None:
        return False
    if callable(getattr(client_type, "on_disconnect", None)):
        return True

    on_connection_change = getattr(client_type, "on_connection_change", None)
    connection_state = getattr(ntgcalls_module, "ConnectionState", None)
    closed_state = getattr(connection_state, "CLOSED", None)
    if not callable(on_connection_change) or closed_state is None:
        return False

    def on_disconnect(self, callback):
        def handle_connection_change(chat_id, state):
            if state == closed_state or getattr(state, "name", None) == "CLOSED":
                callback(chat_id)

        return on_connection_change(self, handle_connection_change)

    client_type.on_disconnect = on_disconnect
    return callable(getattr(client_type, "on_disconnect", None))
