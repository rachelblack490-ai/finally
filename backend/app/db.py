"""SQLite persistence for FinAlly.

Lazy schema init on startup / first use. Every table carries a ``user_id``
(hardcoded ``"default"`` for the single-user product). The runtime DB file is
resolved from ``FINALLY_DB_PATH`` or OS app-data (see :mod:`app.config`).
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from threading import Lock

from . import config

DEFAULT_USER = "default"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users_profile (
    id           TEXT PRIMARY KEY,
    cash_balance REAL NOT NULL DEFAULT 10000.0,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
    id       TEXT PRIMARY KEY,
    user_id  TEXT NOT NULL DEFAULT 'default',
    ticker   TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
);

CREATE TABLE IF NOT EXISTS positions (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL DEFAULT 'default',
    ticker     TEXT NOT NULL,
    quantity   REAL NOT NULL,
    avg_cost   REAL NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
);

CREATE TABLE IF NOT EXISTS trades (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL DEFAULT 'default',
    ticker      TEXT NOT NULL,
    side        TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity    REAL NOT NULL,
    price       REAL NOT NULL,
    executed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL DEFAULT 'default',
    total_value REAL NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL DEFAULT 'default',
    role       TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT NOT NULL,
    actions    TEXT,
    created_at TEXT NOT NULL
);
"""


def new_id() -> str:
    return uuid.uuid4().hex


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Database:
    """Thread-safe SQLite wrapper.

    Uses a single connection guarded by a lock. The product is single-user with
    light concurrency (a few REST calls, one SSE loop, one snapshot task), so a
    serialized connection is simpler and safer than a pool.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self.init_schema()

    def init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    # --- Low-level helpers ---

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self._lock:
            self._conn.execute(sql, params)
            self._conn.commit()

    def query_all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchall()

    def query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchone()

    def transaction(self):
        """Return a context manager yielding the raw connection under the lock.

        Use for multi-statement atomic writes (e.g. trade execution).
        """
        return _Transaction(self._lock, self._conn)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- Seed ---

    def ensure_seed(self, default_watchlist: list[str], starting_cash: float) -> None:
        """Create the default profile and seed watchlist if missing."""
        profile = self.query_one(
            "SELECT id FROM users_profile WHERE id = ?", (DEFAULT_USER,)
        )
        if profile is None:
            self.execute(
                "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
                (DEFAULT_USER, starting_cash, now_iso()),
            )
        existing = {
            row["ticker"]
            for row in self.query_all(
                "SELECT ticker FROM watchlist WHERE user_id = ?", (DEFAULT_USER,)
            )
        }
        for ticker in default_watchlist:
            if ticker not in existing:
                self.execute(
                    "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                    (new_id(), DEFAULT_USER, ticker, now_iso()),
                )


class _Transaction:
    def __init__(self, lock: Lock, conn: sqlite3.Connection) -> None:
        self._lock = lock
        self._conn = conn

    def __enter__(self) -> sqlite3.Connection:
        self._lock.acquire()
        return self._conn

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self._lock.release()


def create_database(path: Path | None = None) -> Database:
    db_path = path or config.get_db_path()
    db = Database(db_path)
    db.ensure_seed(config.DEFAULT_WATCHLIST, config.STARTING_CASH)
    return db
