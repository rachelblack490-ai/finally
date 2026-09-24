"""FinAlly desktop shell (pywebview).

Runs the FastAPI sidecar bound to loopback in a background thread, waits for
health, then opens a pywebview window at that same-origin URL. The sidecar and
window share one process, so closing the window stops the sidecar.

Run (from repo root, with the backend venv):
    cd backend && uv run --extra desktop python ../desktop/main.py

Use ``--headless`` to start + health-check the sidecar without opening a window
(useful for CI / smoke tests on machines without a WebView runtime).
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
from pathlib import Path

from launcher import find_free_port, wait_for_health

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
STATIC_DIR = REPO_ROOT / "frontend" / "out"

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
BG_COLOR = "#0d1117"


def _ensure_backend_importable() -> None:
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))


def _make_server(host: str, port: int):
    """Build a uvicorn Server for the FinAlly app (import kept local)."""
    import uvicorn

    from app.main import create_app

    config = uvicorn.Config(create_app(), host=host, port=port, log_level="info")
    return uvicorn.Server(config)


def run(headless: bool = False) -> int:
    _ensure_backend_importable()

    host = os.environ.get("FINALLY_HOST", "127.0.0.1")
    port = int(os.environ.get("FINALLY_PORT", "0")) or find_free_port(8000)

    # Serve the built static UI from the same origin.
    if STATIC_DIR.is_dir():
        os.environ.setdefault("FINALLY_STATIC_DIR", str(STATIC_DIR))
    os.environ["FINALLY_HOST"] = host
    os.environ["FINALLY_PORT"] = str(port)

    server = _make_server(host, port)
    thread = threading.Thread(target=server.run, name="finally-sidecar", daemon=True)
    thread.start()

    url = f"http://{host}:{port}/"
    if not wait_for_health(f"{url}api/health", timeout=30):
        print("Sidecar failed to become healthy", file=sys.stderr)
        server.should_exit = True
        return 1

    print(f"FinAlly sidecar healthy at {url}")

    if headless:
        # Non-GUI smoke mode: prove the sidecar came up, then shut down.
        server.should_exit = True
        thread.join(timeout=5)
        return 0

    try:
        import webview

        webview.create_window(
            "FinAlly",
            url,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            background_color=BG_COLOR,
        )
        webview.start()
    finally:
        # Window closed → stop the sidecar so both die together.
        server.should_exit = True
        thread.join(timeout=5)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="FinAlly desktop shell")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Start + health-check the sidecar without opening a window.",
    )
    args = parser.parse_args()
    raise SystemExit(run(headless=args.headless))


if __name__ == "__main__":
    main()
