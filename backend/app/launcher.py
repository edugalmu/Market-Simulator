from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn


HOST = "127.0.0.1"
PORT = 8000
APP_URL = f"http://{HOST}:{PORT}/"
HEALTH_URL = f"{APP_URL}api/v1/health"


def _resolve_frontend_dist() -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    bundled_dist = bundle_root / "frontend" / "dist"
    if bundled_dist.exists():
        return bundled_dist

    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


def _open_browser(delay_seconds: float = 1.2) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)
    webbrowser.open(APP_URL)


def _is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False

    return True


def _is_market_simulator_running() -> bool:
    try:
        with urlopen(HEALTH_URL, timeout=1.0) as response:
            if response.status != 200:
                return False

            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, URLError, ValueError, json.JSONDecodeError):
        return False

    return isinstance(payload, dict) and str(payload.get("name", "")).startswith(
        "Market Simulator"
    )


def main() -> None:
    os.environ.setdefault("MARKET_SIMULATOR_GPU_ENABLED", "false")
    os.environ.setdefault(
        "MARKET_SIMULATOR_FRONTEND_DIST_DIR",
        str(_resolve_frontend_dist()),
    )

    if not _is_port_available(HOST, PORT):
        if _is_market_simulator_running():
            print(f"Market Simulator ya esta ejecutandose en {APP_URL}")
            _open_browser(delay_seconds=0)
            return

        raise SystemExit(
            f"No se puede iniciar Market Simulator porque {APP_URL} ya esta ocupado por otro proceso."
        )

    from app.main import app

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()