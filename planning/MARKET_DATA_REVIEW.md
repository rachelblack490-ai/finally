# Market Data Backend — Code Review

**Date:** 2026-09-28  
**Scope:** `backend/app/market/` (8 source modules + `__init__.py`) and `backend/tests/market/` (6 test modules)  
**Docs read:** `planning/PLAN.md`, `CURSOR_PLAN.md`, `MARKET_DATA_SUMMARY.md`, `MARKET_INTERFACE.md`, `MARKET_SIMULATOR.md`, `MASSIVE_API.md`, and `planning/archive/MARKET_DATA_REVIEW.md`

---

## 1. Test results

**73 tests collected, 73 passed.** Ruff: all checks passed on `app/market` and `tests/market`.

```text
cd backend
uv sync --extra dev
uv run pytest tests/market -q
uv run ruff check app/market tests/market
```

**Coverage:** 91% overall (`pytest --cov=app/market`).

| Module | Cover | Notes |
|---|---|---|
| `__init__.py` | 100% | |
| `models.py` | 100% | |
| `cache.py` | 100% | |
| `factory.py` | 100% | |
| `interface.py` | 100% | |
| `seed_prices.py` | 100% | |
| `simulator.py` | 98% | Miss: `_add_ticker_internal` duplicate guard; `_run_loop` exception log |
| `massive_client.py` | 94% | Miss: `_poll_loop` sleep path; `_fetch_snapshots` real client call |
| `stream.py` | 33% | No dedicated SSE tests — largest remaining gap |

An earlier review (2026-02-10) reported 68 passed / 5 failed because `massive` was lazy-imported and tests patched a missing name. That is **fixed**: `RESTClient` is imported at module top, `massive` is a core dependency, and Massive tests set `source._client` and patch `_fetch_snapshots`.

---

## 2. Architecture

The package matches the planning contract. Downstream code should only read `PriceCache`; it should not talk to Massive or GBM math.

```
create_market_data_source(cache)
        │
        ├─ MASSIVE_API_KEY set  →  MassiveDataSource
        └─ otherwise            →  SimulatorDataSource
                        │
                        ▼
                   PriceCache
        ┌───────────┼────────────┐
        ▼           ▼            ▼
   SSE /prices   fills/marks   chat context
```

**What is solid**

- Strategy pattern via `MarketDataSource`; factory is the only place that reads `MASSIVE_API_KEY`.
- Frozen `PriceUpdate` (`slots=True`) is the only price object that leaves the package.
- Thread-safe cache with a version counter for SSE change detection.
- GBM formula is correct: `S * exp((μ − ½σ²)dt + σ√dt Z)` with Cholesky-correlated Z.
- Sector correlations (tech 0.6, finance 0.5, TSLA/cross 0.3) and ~0.1% shock events match the spec.
- Simulator seeds the cache on `start` / `add_ticker` so SSE is not empty.
- Massive first-polls in `start()`, runs the sync client in `asyncio.to_thread`, skips bad snapshots, and does not crash the loop on API errors.
- `stop()` on both sources is cancellable and idempotent.
- Hatch wheel config is present (`[tool.hatch.build.targets.wheel] packages = ["app"]`) — the old `uv sync` blocker is gone.
- SSE return type is `AsyncGenerator[str, None]`; `GBMSimulator.get_tickers()` is public; unused `DEFAULT_CORR` was removed.

---

## 3. Remaining issues

### 3.1 No SSE tests (medium)

`stream.py` is the frontend contract and is only 33% covered. There is no ASGI test that a client receives `retry: 1000` and a `data:` JSON map of all tickers. Add one `httpx`/`TestClient` test before wiring the rest of the app.

### 3.2 `remove_ticker` drops the mark for open positions (medium — product)

Both sources call `cache.remove(ticker)`. `CURSOR_PLAN.md` / `MARKET_INTERFACE.md` say: keep the source subscription (and cache row) while qty > 0; only unsubscribe at zero. The market package cannot know positions. The future FastAPI trade/watchlist layer must not call `remove_ticker` for a name still held.

### 3.3 Massive `add_ticker` is delayed (medium — product)

Simulator seeds immediately. Massive only appends the symbol and waits for the next ~15s poll. A market order on a newly added ticker must wait/retry with a bound, then reject — never fill on a cache miss. Documented; not enforced in this package (no trade route yet).

### 3.4 `PriceCache.version` is unlocked (low)

`version` reads `_version` without `_lock`. Fine under CPython GIL; inconsistent with the rest of the class. Lock it if you ever run free-threaded Python.

### 3.5 `remove()` does not bump `version` (low)

SSE change detection is version-based. Removing a ticker does not increment `_version`, so a connected client can keep emitting the old map until some other update happens. Bump version on remove (or include removals in the payload).

### 3.6 Module-level SSE `router` (low)

`create_stream_router()` registers `/prices` on a module-level `APIRouter`. A second call (tests, accidental double include) would register the route twice. Create the router inside the factory.

### 3.7 Simulator `start()` is not guarded (low)

Docs say calling `start()` twice is undefined. A second call would replace `_sim` and leak the old task. Guard with “already started” or call `stop()` first.

### 3.8 Massive snapshot plan vs Stocks Basic (docs, not code)

`MASSIVE_API.md`: Stocks Basic does not include the all-tickers snapshot used here. Empty key → simulator is the supported demo path. Do not treat a Basic key as a live tape.

---

## 4. Missing tests (nice to have)

- SSE integration (`stream.py`).
- Concurrent writers on `PriceCache`.
- Full default 10-ticker Cholesky (tests use 1–2 names).
- `remove()` causing an SSE version bump (once that behavior is defined).

---

## 5. Verdict

The market data backend is **complete, tested, and ready to extend**. Do **not** rewrite `backend/app/market/`. Wire FastAPI lifespan, portfolio, and watchlist to `PriceCache` + `create_market_data_source()`.

**Blockers for this package:** none.

**Do before the rest of the app ships**

1. One SSE integration test.
2. Watchlist/position rules so `remove_ticker` cannot blank an open mark.
3. Bounded wait on Massive `add_ticker` before a first fill.

**Optional polish:** lock `version`, bump version on `remove`, instantiate the SSE router inside the factory, guard double `start()`.
