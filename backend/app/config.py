"""Runtime configuration for the FinAlly sidecar.

All values come from environment variables (optionally loaded from a project
root ``.env``). The sidecar always binds loopback; port 8000 is an internal
bind, not the product UX.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "FinAlly"

DEFAULT_WATCHLIST: list[str] = [
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "JPM",
    "V",
    "NFLX",
]

STARTING_CASH = 10_000.0

# Portfolio snapshot cadence (seconds) for the P&L chart.
SNAPSHOT_INTERVAL_SECONDS = 30.0


def _project_root() -> Path:
    # backend/app/config.py -> repo root is two parents up from app/.
    return Path(__file__).resolve().parents[2]


def load_dotenv() -> None:
    """Load the project root ``.env`` into ``os.environ`` if present.

    Uses python-dotenv when available; otherwise falls back to a tiny parser so
    the sidecar never hard-depends on it at import time.
    """
    env_path = _project_root() / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv as _ld

        _ld(env_path, override=False)
        return
    except Exception:
        pass
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_host() -> str:
    return os.environ.get("FINALLY_HOST", "127.0.0.1")


def get_port() -> int:
    try:
        return int(os.environ.get("FINALLY_PORT", "8000"))
    except ValueError:
        return 8000


def app_data_dir() -> Path:
    """OS-appropriate application data directory for FinAlly."""
    if os.name == "nt":  # Windows
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    home = Path.home()
    if os.uname().sysname == "Darwin":  # macOS
        return home / "Library" / "Application Support" / APP_NAME
    # Linux / other: XDG data home
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else home / ".local" / "share"
    return base / APP_NAME


def get_db_path() -> Path:
    """Resolve the SQLite file path.

    ``FINALLY_DB_PATH`` wins; otherwise the OS app-data ``FinAlly/finally.db``.
    """
    override = os.environ.get("FINALLY_DB_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return app_data_dir() / "finally.db"


def llm_mock_enabled() -> bool:
    return os.environ.get("LLM_MOCK", "false").strip().lower() in {"1", "true", "yes"}


def opencode_api_key() -> str:
    return os.environ.get("OPENCODE_API_KEY", "").strip()


def opencode_model() -> str:
    return os.environ.get("OPENCODE_MODEL", "openai/mimo-v2.5-free")


def opencode_api_base() -> str:
    return os.environ.get("OPENCODE_API_BASE", "https://opencode.ai/zen/v1")
