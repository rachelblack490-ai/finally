"""SQLite schema, seed, and user_id column tests."""

from __future__ import annotations

from app.config import DEFAULT_WATCHLIST, STARTING_CASH
from app.db import DEFAULT_USER, create_database


def test_seed_creates_profile_and_watchlist(db):
    profile = db.query_one("SELECT * FROM users_profile WHERE id = ?", (DEFAULT_USER,))
    assert profile is not None
    assert profile["cash_balance"] == STARTING_CASH

    rows = db.query_all("SELECT ticker FROM watchlist WHERE user_id = ?", (DEFAULT_USER,))
    tickers = {r["ticker"] for r in rows}
    assert tickers == set(DEFAULT_WATCHLIST)


def test_seed_is_idempotent(tmp_path):
    path = tmp_path / "idem.db"
    d1 = create_database(path)
    d1.ensure_seed(DEFAULT_WATCHLIST, STARTING_CASH)  # run seed again
    count = d1.query_one("SELECT COUNT(*) AS n FROM watchlist")["n"]
    assert count == len(DEFAULT_WATCHLIST)
    d1.close()


def test_all_tables_have_user_id(db):
    for table in ("watchlist", "positions", "trades", "portfolio_snapshots", "chat_messages"):
        cols = {row["name"] for row in db.query_all(f"PRAGMA table_info({table})")}
        assert "user_id" in cols, f"{table} missing user_id"


def test_default_watchlist_order_preserved(db):
    rows = db.query_all(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at ASC, rowid ASC",
        (DEFAULT_USER,),
    )
    assert [r["ticker"] for r in rows] == DEFAULT_WATCHLIST
