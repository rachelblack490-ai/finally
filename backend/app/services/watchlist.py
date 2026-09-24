"""Watchlist CRUD. POST/DELETE always sync the market source so new symbols
get SSE ticks (and can be traded)."""

from __future__ import annotations

from ..db import DEFAULT_USER, Database, new_id, now_iso
from ..market import MarketDataSource, PriceCache
from ..schemas import WatchlistItem


class WatchlistError(Exception):
    pass


def list_watchlist(db: Database, cache: PriceCache, user_id: str = DEFAULT_USER) -> list[WatchlistItem]:
    rows = db.query_all(
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at ASC, rowid ASC",
        (user_id,),
    )
    items: list[WatchlistItem] = []
    for row in rows:
        ticker = row["ticker"]
        update = cache.get(ticker)
        if update is not None:
            items.append(
                WatchlistItem(
                    ticker=ticker,
                    price=update.price,
                    previous_price=update.previous_price,
                    change=update.change,
                    change_percent=update.change_percent,
                    direction=update.direction,
                )
            )
        else:
            items.append(WatchlistItem(ticker=ticker))
    return items


async def add_ticker(
    db: Database,
    cache: PriceCache,
    source: MarketDataSource,
    ticker: str,
    user_id: str = DEFAULT_USER,
) -> WatchlistItem:
    ticker = ticker.upper().strip()
    if not ticker or not ticker.isalnum():
        raise WatchlistError("Invalid ticker symbol.")
    exists = db.query_one(
        "SELECT id FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
    )
    if exists is None:
        db.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (new_id(), user_id, ticker, now_iso()),
        )
    # Always register with the market source (idempotent) so it gets ticks.
    await source.add_ticker(ticker)
    update = cache.get(ticker)
    if update is not None:
        return WatchlistItem(
            ticker=ticker,
            price=update.price,
            previous_price=update.previous_price,
            change=update.change,
            change_percent=update.change_percent,
            direction=update.direction,
        )
    return WatchlistItem(ticker=ticker)


async def remove_ticker(
    db: Database,
    cache: PriceCache,
    source: MarketDataSource,
    ticker: str,
    user_id: str = DEFAULT_USER,
) -> None:
    ticker = ticker.upper().strip()
    db.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
    )
    await source.remove_ticker(ticker)
