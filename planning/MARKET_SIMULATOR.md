# Market simulator

Approach and code structure for **simulated** US equity prices when `MASSIVE_API_KEY` is unset. Real tape: [`MASSIVE_API.md`](MASSIVE_API.md). Shared API: [`MARKET_INTERFACE.md`](MARKET_INTERFACE.md).

Implementation: `backend/app/market/simulator.py` + `seed_prices.py`. Do not replace it.

## Why simulate

- Default course / desktop demo with **no vendor key**
- Stocks Basic keys **cannot** call snapshots anyway
- Deterministic-enough visuals: live flashes, correlated tape, occasional shocks
- Same `MarketDataSource` + `PriceCache` path as Massive, so UI and fills do not care

## Model: geometric Brownian motion

Standard Black–Scholes spot process. Prices stay positive and are lognormal.

```
S(t + dt) = S(t) * exp( (μ − σ²/2) * dt  +  σ * √dt * Z )
```

| Symbol | Meaning | Code |
|---|---|---|
| `S` | Spot | `GBMSimulator._prices[ticker]` |
| `μ` | Annualized drift | `TICKER_PARAMS[t]["mu"]` (e.g. 0.05) |
| `σ` | Annualized vol | `TICKER_PARAMS[t]["sigma"]` (e.g. 0.22) |
| `dt` | Step as a **fraction of a trading year** | `0.5 / (252 * 6.5 * 3600)` ≈ `8.48e-8` |
| `Z` | **Correlated** standard normal | Cholesky × i.i.d. `N(0,1)` |

`dt` uses 252 sessions × 6.5 hours × 3600 s, not wall-clock 365×24. A 500 ms tick is then a tiny fraction of a trading year, so per-step moves are sub-cent and accumulate.

```python
TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600  # 5_896_800
DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR
```

Hot path (`GBMSimulator.step`):

```python
z = np.random.standard_normal(n)
z = self._cholesky @ z if self._cholesky is not None else z

for i, ticker in enumerate(self._tickers):
    mu, sigma = self._params[ticker]["mu"], self._params[ticker]["sigma"]
    drift = (mu - 0.5 * sigma**2) * self._dt
    diffusion = sigma * math.sqrt(self._dt) * z[i]
    self._prices[ticker] *= math.exp(drift + diffusion)
    # optional shock (below)
    result[ticker] = round(self._prices[ticker], 2)
```

## Correlation (Cholesky)

Independent `Z` would make every name twitch alone. Real tech names move together.

Build a correlation matrix `C` (`C_ii = 1`, `C_ij = ρ(i,j)`), then `L = chol(C)` so `Z_corr = L @ Z_iid`.

| Pair | ρ |
|---|---|
| Both in tech (`AAPL, GOOGL, MSFT, AMZN, META, NVDA, NFLX`) | `0.6` (`INTRA_TECH_CORR`) |
| Both in finance (`JPM, V`) | `0.5` (`INTRA_FINANCE_CORR`) |
| Either name is `TSLA` | `0.3` (`TSLA_CORR`) — in the tech set but treated independently |
| Cross-sector / unknown | `0.3` (`CROSS_GROUP_CORR`) |

Rebuild `L` on add/remove (`O(n²)`, `n` is watchlist-sized). `n ≤ 1` → skip Cholesky, use raw normals.

Unknown tickers get `DEFAULT_PARAMS` (`σ=0.25`, `μ=0.05`) and a random seed in `[50, 300]` if not in `SEED_PRICES`.

## Random shocks

Each ticker, each step: probability `0.001` of a **2–5%** jump, sign random.

With 10 names at 2 Hz that is roughly one shock every ~50 s — enough for green/red flashes without wrecking the book.

```python
if random.random() < self._event_prob:
    mag = random.uniform(0.02, 0.05)
    self._prices[ticker] *= 1 + mag * random.choice([-1, 1])
```

## Seed tape

`backend/app/market/seed_prices.py` (illustrative levels, not live marks):

| Ticker | Seed | σ | μ |
|---|---:|---:|---:|
| AAPL | 190 | 0.22 | 0.05 |
| GOOGL | 175 | 0.25 | 0.05 |
| MSFT | 420 | 0.20 | 0.05 |
| AMZN | 185 | 0.28 | 0.05 |
| TSLA | 250 | 0.50 | 0.03 |
| NVDA | 800 | 0.40 | 0.08 |
| META | 500 | 0.30 | 0.05 |
| JPM | 195 | 0.18 | 0.04 |
| V | 280 | 0.17 | 0.04 |
| NFLX | 600 | 0.35 | 0.05 |

These seeds are the natural **session open** for watchlist session-change % when Massive is off.

## Code structure

Two classes in one module — keep that split.

```
GBMSimulator            # pure math, sync, no asyncio, no cache
  __init__(tickers, dt, event_probability)
  step() -> dict[str, float]
  add_ticker / remove_ticker / get_price / get_tickers
  _rebuild_cholesky()
  _pairwise_correlation()

SimulatorDataSource     # MarketDataSource adapter
  start(tickers)        # construct GBM, seed cache, spawn loop
  stop()
  add_ticker            # GBM + immediate cache seed
  remove_ticker         # GBM + cache.remove
  _run_loop()           # step → cache.update → sleep 0.5s
```

```python
from app.market import PriceCache
from app.market.simulator import SimulatorDataSource

cache = PriceCache()
source = SimulatorDataSource(price_cache=cache, update_interval=0.5)
await source.start(["AAPL", "MSFT", "JPM"])
# cache now has seeds; ~500 ms later, GBM ticks
await source.add_ticker("NVDA")   # price available immediately
await source.stop()
```

Factory (`factory.py`) picks this class when `MASSIVE_API_KEY` is blank. Callers still only see `MarketDataSource`.

## Timing vs Massive

| | Simulator | Massive |
|---|---|---|
| Interval | **0.5 s** | **15 s** (free snapshot budget) |
| First price | Immediate seed | First successful poll |
| `add_ticker` | Immediate seed | Next poll (may be empty until then) |

SSE still wakes on `PriceCache.version`. Faster simulator ticks mean a livelier tape in the default demo.

## What we do not simulate

- Limit book, spreads, halts, auctions
- True session calendar (no overnight jump model)
- Official OHLC bars (charts = in-process ticks)
- Vendor 15-minute delay

Fills are last cache print, same as Massive.

## Tests and demo

- `backend/tests/market/test_simulator.py` — GBM math, shocks, add/remove
- `backend/tests/market/test_simulator_source.py` — `MarketDataSource` adapter
- Terminal demo: `cd backend && uv run market_data_demo.py`

Keep those tests green. New product code should not fork a second RNG loop.
