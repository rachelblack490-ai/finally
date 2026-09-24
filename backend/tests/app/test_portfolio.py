"""Trade execution and portfolio valuation tests."""

from __future__ import annotations

import pytest

from app.db import DEFAULT_USER
from app.services import portfolio as pf


def _set_price(cache, ticker, price):
    # Force a specific price by writing twice (previous == price after settle).
    cache.update(ticker, price)
    cache.update(ticker, price)


async def test_buy_updates_cash_and_position(db, cache, source):
    _set_price(cache, "AAPL", 200.0)
    res = await pf.execute_trade(db, cache, source, "AAPL", "buy", 5)
    assert res.ok
    assert res.price == 200.0
    assert res.cash == pytest.approx(10000.0 - 1000.0)

    port = pf.build_portfolio(db, cache)
    assert port.cash == pytest.approx(9000.0)
    pos = {p.ticker: p for p in port.positions}
    assert pos["AAPL"].quantity == pytest.approx(5)
    assert pos["AAPL"].avg_cost == pytest.approx(200.0)


async def test_avg_cost_blends_on_second_buy(db, cache, source):
    _set_price(cache, "MSFT", 100.0)
    await pf.execute_trade(db, cache, source, "MSFT", "buy", 10)
    _set_price(cache, "MSFT", 200.0)
    await pf.execute_trade(db, cache, source, "MSFT", "buy", 10)
    port = pf.build_portfolio(db, cache)
    pos = {p.ticker: p for p in port.positions}["MSFT"]
    assert pos.quantity == pytest.approx(20)
    assert pos.avg_cost == pytest.approx(150.0)


async def test_sell_reduces_position_and_adds_cash(db, cache, source):
    _set_price(cache, "NVDA", 100.0)
    await pf.execute_trade(db, cache, source, "NVDA", "buy", 10)
    await pf.execute_trade(db, cache, source, "NVDA", "sell", 4)
    port = pf.build_portfolio(db, cache)
    pos = {p.ticker: p for p in port.positions}["NVDA"]
    assert pos.quantity == pytest.approx(6)
    assert port.cash == pytest.approx(10000.0 - 10 * 100 + 4 * 100)


async def test_sell_to_zero_deletes_position(db, cache, source):
    _set_price(cache, "V", 50.0)
    await pf.execute_trade(db, cache, source, "V", "buy", 3)
    await pf.execute_trade(db, cache, source, "V", "sell", 3)
    port = pf.build_portfolio(db, cache)
    assert all(p.ticker != "V" for p in port.positions)
    row = db.query_one(
        "SELECT * FROM positions WHERE user_id = ? AND ticker = ?", (DEFAULT_USER, "V")
    )
    assert row is None


async def test_insufficient_cash_rejected(db, cache, source):
    _set_price(cache, "AAPL", 100.0)
    with pytest.raises(pf.TradeError):
        await pf.execute_trade(db, cache, source, "AAPL", "buy", 1000)  # $100k > $10k


async def test_insufficient_shares_rejected(db, cache, source):
    _set_price(cache, "AAPL", 100.0)
    await pf.execute_trade(db, cache, source, "AAPL", "buy", 2)
    with pytest.raises(pf.TradeError):
        await pf.execute_trade(db, cache, source, "AAPL", "sell", 5)


async def test_fractional_quantity_allowed(db, cache, source):
    _set_price(cache, "AMZN", 100.0)
    res = await pf.execute_trade(db, cache, source, "AMZN", "buy", 1.5)
    assert res.ok
    port = pf.build_portfolio(db, cache)
    pos = {p.ticker: p for p in port.positions}["AMZN"]
    assert pos.quantity == pytest.approx(1.5)


async def test_unknown_ticker_auto_adds_to_watchlist(db, cache, source):
    # PLTR is not in the seeded watchlist/cache; a buy should auto-add it.
    assert cache.get_price("PLTR") is None
    res = await pf.execute_trade(db, cache, source, "PLTR", "buy", 1)
    assert res.ok
    wl = db.query_one(
        "SELECT * FROM watchlist WHERE user_id = ? AND ticker = ?", (DEFAULT_USER, "PLTR")
    )
    assert wl is not None
    assert "PLTR" in source.get_tickers()


async def test_snapshot_recorded_after_trade(db, cache, source):
    before = len(pf.get_history(db))
    _set_price(cache, "AAPL", 100.0)
    await pf.execute_trade(db, cache, source, "AAPL", "buy", 1)
    after = len(pf.get_history(db))
    assert after == before + 1


async def test_total_value_conserved_immediately_after_buy(db, cache, source):
    _set_price(cache, "TSLA", 250.0)
    await pf.execute_trade(db, cache, source, "TSLA", "buy", 4)
    port = pf.build_portfolio(db, cache)
    # Right after a fill at market price, total value ~ unchanged (cost basis == price).
    assert port.total_value == pytest.approx(10000.0, abs=0.01)
