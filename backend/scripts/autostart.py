"""Started by Windows when the user signs in — only while the IDS is ON.

The "SecureNet Monitor" shortcut in the Startup folder (created when a user
turns the IDS on, removed when they turn it off) runs this with the venv's
pythonw.exe, so there is no window. It starts the SecureNet backend in the
background; the backend sees that the IDS was on, turns it back on and shows
one desktop notification. Output goes to backend/logs/autostart.log.
Does nothing when a SecureNet backend is already running.
"""

import os
import socket
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PORT = 8000
MAX_LOG_BYTES = 5 * 1024 * 1024

os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

logs = BACKEND / "logs"
logs.mkdir(exist_ok=True)
log_path = logs / "autostart.log"
if log_path.exists() and log_path.stat().st_size > MAX_LOG_BYTES:
    log_path.replace(logs / "autostart.old.log")
# pythonw has no console: everything (including the app's logger) goes to the file
sys.stdout = sys.stderr = open(log_path, "a", encoding="utf-8", buffering=1)


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


if port_in_use(PORT):
    print(f"SecureNet backend already running on port {PORT} - nothing to do.")
    sys.exit(0)

import uvicorn  # noqa: E402

print("Starting SecureNet backend at Windows sign-in (the IDS was on).")
uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, log_level="warning")
