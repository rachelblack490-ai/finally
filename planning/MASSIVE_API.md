# Massive API (formerly Polygon.io)

Research notes for retrieving **realtime (or delayed) last prices** and **end-of-day / previous-close** prices for **multiple US equity tickers**. This is the vendor API. FinAlly’s own Python surface is in [`MARKET_INTERFACE.md`](MARKET_INTERFACE.md).

Official docs: [massive.com/docs](https://massive.com/docs). Python SDK: [`massive-com/client-python`](https://github.com/massive-com/client-python) (`uv add massive`).

## Overview

| | |
|---|---|
| Vendor | Massive (rebrand of Polygon.io) |
| REST base | `https://api.massive.com` (legacy `https://api.polygon.io` still accepted) |
| Auth | API key as `Authorization: Bearer <key>` or `?apiKey=` |
| Env var in this repo | `MASSIVE_API_KEY` |
| Min Python | 3.9+ |
| What FinAlly uses | REST **multi-ticker snapshot** poll — not WebSockets |

The official client reads `MASSIVE_API_KEY` if you construct `RESTClient()` with no arguments.

```python
from massive import RESTClient

client = RESTClient()                    # env MASSIVE_API_KEY
client = RESTClient(api_key="YOUR_KEY")  # explicit
```

## What “realtime” and “EOD” mean on this vendor

Massive does **not** give every plan a live last print.

| Need | Best endpoint | Typical plan recency |
|---|---|---|
| Current last trade + today + previous day, many symbols, **one HTTP call** | `GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,MSFT,…` | Starter/Developer: **15-minute delayed**. Advanced/Business: **realtime**. **Stocks Basic: snapshot is not included.** |
| One symbol, same payload | `GET /v2/snapshot/locale/us/markets/stocks/tickers/{ticker}` | Same as above |
| Official previous session OHLC | `GET /v2/aggs/ticker/{ticker}/prev` | Available on Basic as **EOD** |
| Historical / EOD daily bars | `GET /v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}` | Basic: EOD, 2 years history |
| All names’ daily OHLC for a date | `GET /v2/aggs/grouped/locale/us/market/stocks/{date}` | One call, whole tape |

Snapshot payloads are **cleared ~03:30 America/New_York** and refill from ~04:00 as venues print. After the regular session, `lastTrade.p` is the last print (may be extended hours). `day` is the current session bar; `prevDay` is the prior regular session.

**FinAlly implication:** a key on **Stocks Basic** cannot drive the snapshot poller. Use the GBM simulator (`MASSIVE_API_KEY` empty) or a plan that includes snapshots (Starter+).

## Rate limits

| Plan class | Practical limit |
|---|---|
| Free / tight individual | **5 requests / minute** → poll **≥ 15 s** |
| Paid | High / “unlimited” — stay well under ~100 req/s |

Watchlist of ~10 names **must** use the **filtered full-market snapshot** (one request per poll), not N single-ticker calls. That is why `MassiveDataSource` calls `get_snapshot_all(..., tickers=watchlist)`.

---

## 1. Multi-ticker snapshot (primary — “realtime” last price)

**REST**

```http
GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,MSFT,AMZN,TSLA
Authorization: Bearer YOUR_KEY
```

Query:

| Param | Required | Notes |
|---|---|---|
| `tickers` | No | Comma-separated, **case-sensitive**. Empty / omitted = **entire** US tape (huge). Always pass the watchlist. |
| `include_otc` | No | Default `false` |

**Python (`massive` SDK)** — this is what `backend/app/market/massive_client.py` uses:

```python
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

client = RESTClient(api_key="YOUR_KEY")

snapshots = client.get_snapshot_all(
    market_type=SnapshotMarketType.STOCKS,
    tickers=["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"],
)

for snap in snapshots:
    last = snap.last_trade
    if last is None:
        continue
    ts_sec = last.timestamp / 1000.0  # vendor uses Unix ms
    print(snap.ticker, last.price, ts_sec)
    print("  session change %:", getattr(snap, "todays_change_percent", None))
    if snap.prev_day:
        print("  prev close:", snap.prev_day.close)
```

**curl**

```bash
curl -sS -H "Authorization: Bearer $MASSIVE_API_KEY" \
  "https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,MSFT,JPM"
```

**JSON shape** (one element of `tickers[]`; REST names are camelCase, SDK uses snake_case):

```json
{
  "ticker": "AAPL",
  "todaysChange": 0.98,
  "todaysChangePerc": 0.82,
  "updated": 1605195918306274000,
  "day": { "o": 119.62, "h": 120.53, "l": 118.81, "c": 120.42, "v": 28727868, "vw": 119.725 },
  "prevDay": { "o": 117.19, "h": 119.63, "l": 116.44, "c": 119.49, "v": 110597265, "vw": 118.4998 },
  "lastTrade": { "p": 120.47, "s": 236, "t": 1605195918306274000, "x": 10 },
  "lastQuote": { "p": 120.46, "P": 120.47, "s": 8, "S": 4, "t": 1605195918507251700 },
  "min": { "o": 120.435, "h": 120.468, "l": 120.37, "c": 120.4201, "v": 270796, "t": 1684428720000 }
}
```

| REST field | SDK | FinAlly use |
|---|---|---|
| `lastTrade.p` | `snap.last_trade.price` | Last price written to `PriceCache` |
| `lastTrade.t` | `snap.last_trade.timestamp` | Cache timestamp (ms → seconds) |
| `prevDay.c` | `snap.prev_day.close` | Session / “previous close” (UI session % — not last-tick %) |
| `todaysChangePerc` | `snap.todays_change_percent` | Vendor session % if we ever surface official daily change |
| `day.*` | `snap.day` | Optional OHLC for a detail panel |

`lastTrade` / `lastQuote` are omitted if the plan does not include trades/quotes. Always guard `AttributeError` / `None` (the poller already skips bad snapshots).

There is also **`GET /v3/snapshot`** (unified, mixed asset classes, `ticker.any_of` max 250). FinAlly stays on the **v2 stocks snapshot** so one `get_snapshot_all` matches the existing client and tests.

---

## 2. Single-ticker snapshot

```http
GET /v2/snapshot/locale/us/markets/stocks/tickers/AAPL
```

```python
from massive.rest.models import SnapshotMarketType

snap = client.get_snapshot_ticker(SnapshotMarketType.STOCKS, "AAPL")
print(snap.last_trade.price, snap.prev_day.close, snap.todays_change_percent)
```

Use this only for a one-off detail fetch. **Do not** poll 10 symbols this way on the free 5 req/min cap.

---

## 3. Previous close (EOD / official prior session)

```http
GET /v2/aggs/ticker/AAPL/prev?adjusted=true
```

```python
for bar in client.get_previous_close_agg(ticker="AAPL", adjusted=True):
    print(bar.open, bar.high, bar.low, bar.close, bar.volume, bar.timestamp)
```

Typical `results[]` item: `o`, `h`, `l`, `c`, `v`, `vw`, `t` (Unix ms).

One request **per ticker**. For ten names that is 10 calls — fine for a once-per-session seed, **not** for the live loop. Prefer `prevDay` on the snapshot you already fetched.

---

## 4. Daily bars (EOD history)

```http
GET /v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-01-31?adjusted=true&limit=50000
```

```python
closes = []
for bar in client.list_aggs(
    ticker="AAPL",
    multiplier=1,
    timespan="day",
    from_="2024-01-01",
    to="2024-01-31",
    adjusted=True,
    limit=50000,
):
    closes.append((bar.timestamp, bar.close))
```

On **Stocks Basic** this is **end-of-day** (not a live last). History depth is plan-limited (Basic ~2 years). FinAlly charts are **ticks since launch** ([`CURSOR_PLAN.md`](CURSOR_PLAN.md)); this endpoint is optional future history, not required for the poller.

**Whole tape, one date:**

```http
GET /v2/aggs/grouped/locale/us/market/stocks/2024-06-14?adjusted=true
```

---

## 5. Last trade (single symbol)

```python
trade = client.get_last_trade("AAPL")
print(trade.price, trade.size)
```

Same rate-limit problem as single snapshot. Not used in FinAlly.

---

## 6. WebSockets (not used)

Massive can push trades/quotes/aggregates on a socket. FinAlly **polls REST** and fans out over **our** SSE (`GET /api/stream/prices`):

- Works on snapshot-capable REST plans without a second protocol
- One process, easier tests (`asyncio.to_thread` around the sync SDK)
- Course spec: SSE over WebSockets for the product

Do not add a Massive WebSocket client unless a later spec says so.

---

## How FinAlly should call it

Implemented in `backend/app/market/massive_client.py`:

1. `RESTClient(api_key=…)`
2. Immediate `_poll_once()`, then loop every **15 s** (override if a paid key can go faster)
3. `get_snapshot_all(STOCKS, tickers=watchlist)` in a worker thread
4. For each snap: `cache.update(ticker, last_trade.price, timestamp=ms/1000)`
5. On 401 / 403 / 429 / network error: **log and retry next interval** — do not crash the desktop sidecar
6. `add_ticker` only appends the symbol; **the next poll** is when a price appears (Massive has no instant fill guarantee — see [`CURSOR_PLAN.md`](CURSOR_PLAN.md) / [`REVIEW.md`](REVIEW.md))

```python
import asyncio
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

async def poll_once(client: RESTClient, tickers: list[str], cache) -> None:
    if not tickers:
        return
    snapshots = await asyncio.to_thread(
        client.get_snapshot_all,
        SnapshotMarketType.STOCKS,
        tickers,
    )
    for snap in snapshots:
        try:
            cache.update(
                ticker=snap.ticker,
                price=snap.last_trade.price,
                timestamp=snap.last_trade.timestamp / 1000.0,
            )
        except (AttributeError, TypeError):
            continue
```

## Errors

| HTTP | Meaning | Poller |
|---|---|---|
| 401 | Bad key | Log; retry; user still has a window |
| 403 | Plan cannot use this endpoint (e.g. Basic + snapshot) | Same; prefer simulator |
| 429 | Rate limit | Sleep the configured interval (already ≥ 15 s on default) |
| 5xx | Vendor | SDK retries a few times; then we wait for the next loop |

## References

- [Full market snapshot](https://massive.com/docs/rest/stocks/snapshots/full-market-snapshot)
- [Single ticker snapshot](https://massive.com/docs/rest/stocks/snapshots/single-ticker-snapshot)
- [Custom bars (OHLC)](https://massive.com/docs/rest/stocks/aggregates/custom-bars)
- [Daily market summary](https://massive.com/docs/rest/stocks/aggregates/daily-market-summary)
- Implementation: `backend/app/market/massive_client.py`
- Tests: `backend/tests/market/test_massive.py`
