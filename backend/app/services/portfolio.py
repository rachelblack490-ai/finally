"""Portfolio valuation, trade execution, and snapshots.

Reuses the existing market package: prices come from the shared ``PriceCache``
and unknown tickers are registered with the ``MarketDataSource`` (which also
seeds the cache) before a fill.
"""

from __future__ import annotations

import asyncio

from ..db import DEFAULT_USER, Database, new_id, now_iso
from ..market import MarketDataSource, PriceCache
from ..schemas import PortfolioOut, PositionOut, TradeResult

# Quantities at or below this are treated as a fully-closed position.
ZERO_QTY_EPSILON = 1e-9


class TradeError(Exception):
    """Raised when a trade cannot be executed (bad input, funds, shares)."""


def get_cash(db: Database, user_id: str = DEFAULT_USER) -> float:
    row = db.query_one("SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,))
    return float(row["cash_balance"]) if row else 0.0


def _positions_rows(db: Database, user_id: str = DEFAULT_USER):
    return db.query_all(
        "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ? ORDER BY ticker",
        (user_id,),
    )


def build_portfolio(db: Database, cache: PriceCache, user_id: str = DEFAULT_USER) -> PortfolioOut:
    cash = get_cash(db, user_id)
    positions: list[PositionOut] = []
    positions_value = 0.0
    unrealized_pl = 0.0
    for row in _positions_rows(db, user_id):
        ticker = row["ticker"]
        qty = float(row["quantity"])
        avg_cost = float(row["avg_cost"])
        price = cache.get_price(ticker)
        if price is None:
            price = avg_cost  # Fall back to cost basis if no live tick yet.
        market_value = qty * price
        pl = qty * (price - avg_cost)
        pl_pct = ((price - avg_cost) / avg_cost * 100.0) if avg_cost else 0.0
        positions_value += market_value
        unrealized_pl += pl
        positions.append(
            PositionOut(
                ticker=ticker,
                quantity=round(qty, 6),
                avg_cost=round(avg_cost, 4),
                price=round(price, 2),
                market_value=round(market_value, 2),
                unrealized_pl=round(pl, 2),
                unrealized_pl_percent=round(pl_pct, 2),
            )
        )
    total = cash + positions_value
    return PortfolioOut(
        cash=round(cash, 2),
        positions_value=round(positions_value, 2),
        total_value=round(total, 2),
        unrealized_pl=round(unrealized_pl, 2),
        positions=positions,
    )


def total_value(db: Database, cache: PriceCache, user_id: str = DEFAULT_USER) -> float:
    return build_portfolio(db, cache, user_id).total_value


def record_snapshot(db: Database, cache: PriceCache, user_id: str = DEFAULT_USER) -> float:
    value = total_value(db, cache, user_id)
    db.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
        (new_id(), user_id, value, now_iso()),
    )
    return value


async def _ensure_price(
    cache: PriceCache,
    source: MarketDataSource,
    db: Database,
    ticker: str,
    user_id: str = DEFAULT_USER,
) -> float:
    """Ensure ``ticker`` has a cache price, auto-adding it to the watchlist and
    the market source if unknown. Returns the current price.
    """
    price = cache.get_price(ticker)
    if price is not None:
        return price

    # Unknown ticker: auto-add to watchlist + market source, then wait for a tick.
    exists = db.query_one(
        "SELECT id FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
    )
    if exists is None:
        db.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (new_id(), user_id, ticker, now_iso()),
        )
    await source.add_ticker(ticker)

    # The simulator seeds the cache synchronously; Massive needs a poll cycle.
    for _ in range(50):  # up to ~5s
        price = cache.get_price(ticker)
        if price is not None:
            return price
        await asyncio.sleep(0.1)
    raise TradeError(f"No price available for {ticker} yet; try again shortly.")


async def execute_trade(
    db: Database,
    cache: PriceCache,
    source: MarketDataSource,
    ticker: str,
    side: str,
    quantity: float,
    user_id: str = DEFAULT_USER,
) -> TradeResult:
    """Execute a market order at the current cache price.

    Rules: reject insufficient cash/shares; fractional allowed; sell-to-zero
    deletes the position row; unknown ticker auto-adds to watchlist + source.
    """
    ticker = ticker.upper().strip()
    if not ticker:
        raise TradeError("Ticker is required.")
    if quantity <= 0:
        raise TradeError("Quantity must be positive.")
    if side not in ("buy", "sell"):
        raise TradeError("Side must be 'buy' or 'sell'.")

    price = await _ensure_price(cache, source, db, ticker, user_id)
    cost = quantity * price

    with db.transaction() as conn:
        prof = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        ).fetchone()
        cash = float(prof["cash_balance"]) if prof else 0.0
        pos = conn.execute(
            "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
        cur_qty = float(pos["quantity"]) if pos else 0.0
        cur_avg = float(pos["avg_cost"]) if pos else 0.0

        if side == "buy":
            if cost > cash + 1e-9:
                raise TradeError(
                    f"Insufficient cash: need ${cost:,.2f}, have ${cash:,.2f}."
                )
            new_cash = cash - cost
            new_qty = cur_qty + quantity
            new_avg = (cur_qty * cur_avg + quantity * price) / new_qty if new_qty else price
            conn.execute(
                "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                (new_cash, user_id),
            )
            if pos:
                conn.execute(
                    "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? "
                    "WHERE user_id = ? AND ticker = ?",
                    (new_qty, new_avg, now_iso(), user_id, ticker),
                )
            else:
                conn.execute(
                    "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (new_id(), user_id, ticker, new_qty, new_avg, now_iso()),
                )
        else:  # sell
            if quantity > cur_qty + 1e-9:
                raise TradeError(
                    f"Insufficient shares: trying to sell {quantity} but hold {cur_qty}."
                )
            new_cash = cash + cost
            new_qty = cur_qty - quantity
            conn.execute(
                "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                (new_cash, user_id),
            )
            if new_qty <= ZERO_QTY_EPSILON:
                conn.execute(
                    "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
                    (user_id, ticker),
                )
            else:
                conn.execute(
                    "UPDATE positions SET quantity = ?, updated_at = ? "
                    "WHERE user_id = ? AND ticker = ?",
                    (new_qty, now_iso(), user_id, ticker),
                )

        conn.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id(), user_id, ticker, side, quantity, price, now_iso()),
        )

    # Snapshot immediately after each trade so the P&L chart reflects it.
    record_snapshot(db, cache, user_id)

    return TradeResult(
        ok=True,
        ticker=ticker,
        side=side,
        quantity=round(quantity, 6),
        price=round(price, 2),
        cash=round(new_cash, 2),
        message=f"{side.capitalize()} {quantity:g} {ticker} @ ${price:,.2f}",
    )


def get_history(db: Database, user_id: str = DEFAULT_USER) -> list[dict]:
    rows = db.query_all(
        "SELECT total_value, recorded_at FROM portfolio_snapshots "
        "WHERE user_id = ? ORDER BY recorded_at ASC",
        (user_id,),
    )
    return [
        {"total_value": round(float(r["total_value"]), 2), "recorded_at": r["recorded_at"]}
        for r in rows
    ]
