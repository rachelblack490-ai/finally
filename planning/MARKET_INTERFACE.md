# Market data interface

Unified Python API for stock prices in FinAlly. **One abstract source**, two implementations:

| `MASSIVE_API_KEY` | Implementation | Module |
|---|---|---|
| Set and non-empty | Massive REST poller | `MassiveDataSource` |
| Missing or empty | GBM simulator | `SimulatorDataSource` |

Downstream code (SSE, portfolio marks, trade fills, chat context) **never** talks to Massive or the GBM math. It reads a shared `PriceCache`.

This is the contract already implemented under `backend/app/market/`. Do not invent a second cache or a second source factory.

Vendor HTTP details: [`MASSIVE_API.md`](MASSIVE_API.md). Simulator math: [`MARKET_SIMULATOR.md`](MARKET_SIMULATOR.md).

## Architecture

```
create_market_data_source(cache)
        │
        ├─ MASSIVE_API_KEY set  →  MassiveDataSource  ──┐
        └─ otherwise            →  SimulatorDataSource ─┤
                                                        │
                                                        ▼
                                                 PriceCache
                                           (thread-safe, versioned)
                                                        │
                    ┌───────────────┬───────────────────┼────────────────┐
                    ▼               ▼                   ▼                ▼
            SSE /prices      trade fill         portfolio mark      chat context
```

Strategy pattern: both sources implement `MarketDataSource` and **push** into the cache on their own schedule. Readers **pull** from the cache.

## Core types

### `PriceUpdate`

Frozen dataclass (`backend/app/market/models.py`). The only price object that leaves the market package.

```python
from dataclasses import dataclass, field
import time

@dataclass(frozen=True, slots=True)
class PriceUpdate:
    ticker: str
    price: float
    previous_price: float
    timestamp: float = field(default_factory=time.time)  # Unix seconds

    @property
    def change(self) -> float: ...          # price - previous_price (last tick)

    @property
    def change_percent(self) -> float: ...  # vs last tick, not vs session open

    @property
    def direction(self) -> str: ...         # "up" | "down" | "flat"

    def to_dict(self) -> dict: ...
```

**UI note ([`CURSOR_PLAN.md`](CURSOR_PLAN.md)):** `change_percent` is **tick-to-tick**. Watchlist “session %” must be computed vs seed / session-open (or Massive `prev_day.close`), not this field labeled as “daily”.

### `PriceCache`

Thread-safe store (`backend/app/market/cache.py`). One writer (the active source), many readers.

```python
from app.market import PriceCache, PriceUpdate

cache = PriceCache()
upd: PriceUpdate = cache.update("AAPL", 190.12, timestamp=None)
cache.get("AAPL")          # PriceUpdate | None
cache.get_price("AAPL")    # float | None
cache.get_all()            # dict[str, PriceUpdate]
cache.remove("AAPL")
cache.version              # int, +1 on every update (SSE change detection)
```

First update for a ticker sets `previous_price == price` (`direction="flat"`). Prices are rounded to 2 decimal places.

## Abstract source

```python
from abc import ABC, abstractmethod

class MarketDataSource(ABC):
    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Start the background producer. Call exactly once."""

    @abstractmethod
    async def stop(self) -> None:
        """Cancel the background task. Idempotent."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Watch a new symbol (normalized uppercase). No-op if present."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Stop watching and drop the cache row. No-op if absent."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Currently tracked symbols."""
```

Implemented by:

- `SimulatorDataSource` — steps GBM every ~500 ms; seeds cache immediately on `start` / `add_ticker`
- `MassiveDataSource` — polls snapshot every ~15 s; first poll in `start()`; `add_ticker` waits until the **next** poll for a price

### Watchlist vs positions

`remove_ticker` **deletes the cached price**. If the user still holds the name, portfolio/heatmap/P&L lose a mark. Product rule ([`CURSOR_PLAN.md`](CURSOR_PLAN.md)): keep the **source subscription** for any open position even if the watchlist row is gone; only unsubscribe when qty is zero.

`add_ticker` on Massive does **not** guarantee an immediate price. A trade on an unknown ticker must **wait/retry with a bound**, then reject — never fill on a missing or stale cache miss.

## Factory

```python
# backend/app/market/factory.py
import os
from app.market import PriceCache, MarketDataSource
from app.market.massive_client import MassiveDataSource
from app.market.simulator import SimulatorDataSource

def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if key:
        return MassiveDataSource(api_key=key, price_cache=price_cache)
    return SimulatorDataSource(price_cache=price_cache)
```

Returned source is **unstarted**. Caller must `await source.start(tickers)`.

Public import surface (`backend/app/market/__init__.py`):

```python
from app.market import (
    PriceCache,
    PriceUpdate,
    MarketDataSource,
    create_market_data_source,
    create_stream_router,
)
```

## App lifecycle (FastAPI)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.market import PriceCache, create_market_data_source, create_stream_router

DEFAULT_TICKERS = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "NVDA", "META", "JPM", "V", "NFLX",
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = PriceCache()
    source = create_market_data_source(cache)
    await source.start(DEFAULT_TICKERS)  # or DB watchlist + open positions
    app.state.price_cache = cache
    app.state.market_source = source
    yield
    await source.stop()

app = FastAPI(lifespan=lifespan)
app.include_router(create_stream_router(cache))  # GET /api/stream/prices
```

SSE already emits **one event = dict of all cached tickers**, not one event per symbol. Bind FastAPI to `127.0.0.1` only.

## Downstream rules

| Consumer | How it gets a price |
|---|---|
| SSE | `cache.get_all()` when `cache.version` changes (~500 ms check) |
| `POST /api/portfolio/trade` | `cache.get_price(ticker)` — reject if `None` |
| Portfolio / heatmap / P&L | `cache.get` for each position |
| Chat system prompt | same as portfolio + watchlist |

No second HTTP client in routes. No reading `MASSIVE_API_KEY` outside `factory.py`.

## Why this shape

- **Swap sources with one env var** — demo without a paid snapshot plan; optional real tape when a key exists
- **One cache** — SSE, fills, and marks stay consistent
- **Async start/stop** — fits FastAPI lifespan and pywebview sidecar shutdown
- **REST poll, not vendor WebSocket** — one request for the whole watchlist; see [`MASSIVE_API.md`](MASSIVE_API.md)

## Tests

Keep `backend/tests/market/` green (73 tests). New API routes should mock `PriceCache` / inject a started source — do not re-test GBM or Massive HTTP in the portfolio layer.
