"""Watchlist CRUD tests (with market-source sync)."""

from __future__ import annotations

import pytest

from app.services import watchlist as wl


async def test_list_returns_seeded_tickers_with_prices(db, cache, source):
    items = wl.list_watchlist(db, cache)
    tickers = [i.ticker for i in items]
    assert "AAPL" in tickers
    aapl = next(i for i in items if i.ticker == "AAPL")
    assert aapl.price is not None


async def test_add_ticker_persists_and_registers_source(db, cache, source):
    item = await wl.add_ticker(db, cache, source, "snow")  # lowercase -> normalized
    assert item.ticker == "SNOW"
    assert "SNOW" in source.get_tickers()
    row = db.query_one(
        "SELECT * FROM watchlist WHERE user_id = 'default' AND ticker = 'SNOW'"
    )
    assert row is not None


async def test_add_ticker_is_idempotent(db, cache, source):
    await wl.add_ticker(db, cache, source, "SNOW")
    await wl.add_ticker(db, cache, source, "SNOW")
    rows = db.query_all(
        "SELECT * FROM watchlist WHERE user_id = 'default' AND ticker = 'SNOW'"
    )
    assert len(rows) == 1


async def test_remove_ticker_deletes_and_unregisters(db, cache, source):
    await wl.remove_ticker(db, cache, source, "TSLA")
    assert "TSLA" not in source.get_tickers()
    row = db.query_one(
        "SELECT * FROM watchlist WHERE user_id = 'default' AND ticker = 'TSLA'"
    )
    assert row is None


async def test_invalid_ticker_rejected(db, cache, source):
    with pytest.raises(wl.WatchlistError):
        await wl.add_ticker(db, cache, source, "!!bad!!")
