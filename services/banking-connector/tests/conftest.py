"""Isolate connection counter file per test run (must load before app imports)."""

import os
import tempfile

_fd, _banking_store = tempfile.mkstemp(suffix="_banking_connections.json")
os.close(_fd)
os.environ["BANKING_CONNECTIONS_STORE_PATH"] = _banking_store
