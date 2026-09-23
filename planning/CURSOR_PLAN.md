# FinAlly — Cursor Desktop Plan

Active implementation spec for Cursor. The original course document
(`planning/PLAN.md`) stays as an archive (Docker, browser on `:8000`, OpenRouter).

**Desktop shell:** pywebview (no Tauri, no Electron).
**In-app assistant:** OpenCode Zen free models, not OpenRouter/Cerebras.
**Build-time agents:** Cursor rules, commands, subagents, and hooks.

Market data is **done**. See `planning/MARKET_DATA_SUMMARY.md`.
Do not reimplement `backend/app/market/`.

---

## 1. Product

FinAlly is a dark, Bloomberg-style AI trading workstation. The user
**opens a desktop window** — they do not open a browser to localhost.

- Theme: backgrounds `#0d1117` / `#1a1a2e`, muted gray borders, no pure black
- Accents: yellow `#ecad0a`, blue `#209dd7`, purple `#753991` (submit buttons)
- Default watchlist: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX
- $10,000 virtual cash; market orders only; no fees; no confirm dialog
- Live prices flash green (uptick) / red (downtick) (~500ms CSS fade)
- Watchlist **session** change % vs seed/session-open price (not vs the last 500ms tick)
- Sparklines and the main ticker chart use **ticks since launch** only (no history API)
- Portfolio heatmap (treemap by weight, color by P&L), P&L line chart, positions table
- Watchlist add/remove from the UI or via chat
- Chat assistant analyzes the book and can auto-execute trades / watchlist changes
- Header: total value, cash, connection-status dot (green / yellow / red)

Desktop-first, wide-screen layout. Functional on a laptop.

---

## 2. How the user launches it

**Not:** `docker run -p 8000:8000` and open `http://localhost:8000`.

**Yes:** a start script (or `python -m` entry) that:

1. Starts FastAPI bound to **`127.0.0.1` only** (port 8000, or 8001–8010 if busy)
2. Opens a **pywebview** window pointed at that loopback origin
3. On window close, stops the sidecar

`scripts/start_mac.sh` / `scripts/start_windows.ps1` wrap that flow.
`scripts/stop_*.` stop the sidecar if it is still running. **Implement macOS first**; keep the Windows scripts in the repo (WebView2 is required on Windows).

**Product launch** is the pywebview window. **Dev** may hit the same loopback origin in a browser tab (`uvicorn` + static UI) — that is a shortcut, not the graded UX.

Port 8000 is an internal bind, not the product UX. Never load the UI from `file://`.

---

## 3. Architecture

```
┌──────────────────────────────────────────────┐
│  FinAlly desktop window  (pywebview)         │
│                                              │
│  WebView  ←── Next.js static export          │
│     │      (served by FastAPI, one origin)   │
│     │  http://127.0.0.1:8000/api/*           │
│     │  EventSource /api/stream/prices        │
│     ▼                                        │
│  Sidecar: FastAPI + uv  (loopback only)      │
│  ├── app/market/     (DONE)                  │
│  ├── portfolio, watchlist, trades, chat      │
│  ├── SQLite in OS app-data (not Docker vol)  │
│  └── LLM → OpenCode Zen  (or LLM_MOCK)       │
└──────────────────────────────────────────────┘
```

| Piece | Choice |
|---|---|
| Desktop shell | **pywebview** wrapping the local UI |
| UI | Next.js + TypeScript + Tailwind, **static export** served by FastAPI |
| API | FastAPI / uv on `127.0.0.1` (same origin as the UI) |
| Realtime | SSE `GET /api/stream/prices` (already implemented) |
| DB | SQLite, lazy init, schema in **this file §8** (`user_id` on every table) |
| In-app LLM | OpenCode Zen OpenAI-compatible HTTP API |
| Coding agents | Cursor (`.cursor/`), optional OpenCode CLI |

### Why these choices

- **pywebview over Tauri/Electron** — one Python window, no Rust/Node desktop toolchain this week
- **Loopback FastAPI** — reuse the existing market package and SSE router
- **SSE over WebSockets** — one-way push; native `EventSource`
- **SQLite** — single user, zero config; file lives in app-data
- **Zen over OpenRouter** — free coding models; no Anthropic/OpenRouter bill
- **Market orders only** — simple portfolio math

Do **not** wire the trading chat to OpenCode-the-coding-agent (file/bash tools).
Zen is a chat/completions API. “Buy AAPL” must become structured JSON, not a repo edit.

---

## 4. Directory structure

```
finally/
├── .cursor/
│   ├── rules/              # always-on + scoped rules
│   ├── agents/             # frontend, backend, desktop, reviewer
│   ├── commands/           # /ship-api /ship-ui /mock-chat /doc-review
│   ├── skills/zen-inference/
│   ├── hooks/              # shell guard; no lockfile formatters
│   └── hooks.json
├── frontend/               # Next.js TypeScript UI
├── desktop/                # pywebview window + sidecar launcher
├── backend/                # FastAPI uv project — market/ is DONE
│   └── db/                 # schema SQL + seed logic
├── planning/
│   ├── CURSOR_PLAN.md      # this file (active)
│   ├── PLAN.md             # archived course spec
│   └── MARKET_DATA_SUMMARY.md
├── scripts/                # start/stop desktop (not Docker)
├── test/                   # Playwright E2E
├── .env                    # gitignored
└── .env.example
```

### Boundaries

- **`frontend/`** knows nothing about Python. It calls relative `/api/*` and `/api/stream/*` (same origin). `output: 'export'`.
- **`backend/`** owns DB init, routes, SSE, market data, LLM, and serving the exported UI from a static directory. Reuse `app/market/` (simulator **and** Massive).
- **`desktop/`** owns window lifecycle, picking a free loopback port, killing the sidecar on close, and passing `FINALLY_DB_PATH` into the sidecar.
- **`planning/`** is the shared contract. Prefer this file over `PLAN.md`.
- **`backend/db/`** = schema/seed. Runtime DB file is **`FINALLY_DB_PATH`** (default OS app-data, e.g. `~/Library/Application Support/FinAlly/finally.db` on macOS).

---

## 5. Environment

```bash
# In-app assistant (OpenCode Zen). Free models work with no Zen balance.
OPENCODE_API_KEY=
OPENCODE_MODEL=openai/mimo-v2.5-free
OPENCODE_API_BASE=https://opencode.ai/zen/v1

# Optional real market data; empty = GBM simulator (recommended)
MASSIVE_API_KEY=

# Tests / offline chat
LLM_MOCK=false

# Sidecar bind (loopback only)
FINALLY_HOST=127.0.0.1
FINALLY_PORT=8000

# SQLite file. Empty = OS app-data FinAlly/finally.db
FINALLY_DB_PATH=
```

- No `OPENROUTER_API_KEY` on the default path.
- If the Zen key is missing and `LLM_MOCK` is not true, `POST /api/chat` returns a clear error. Do not crash the window.
- Zen **429 / network failure** → the same clear error. Do **not** silently switch to mock.
- Backend reads `.env` from the project root (and desktop may pass the same env into the sidecar).

Market source: non-empty `MASSIVE_API_KEY` → Massive REST poller; otherwise simulator. **Keep both.** Do not remove Massive.

---

## 6. Already built — do not redo

`backend/app/market/` (~500 lines, 73 tests):

- `PriceUpdate`, `PriceCache`, `MarketDataSource`
- `SimulatorDataSource` (GBM + correlated shocks)
- `MassiveDataSource` (Polygon REST poller)
- `create_market_data_source(cache)`
- `create_stream_router(cache)` → `GET /api/stream/prices`

Wire new routes to the existing cache/stream. Extend, don’t replace.

```python
from app.market import PriceCache, create_market_data_source, create_stream_router
```

---

## 7. Build order

1. FastAPI app shell: lifespan start/stop market source, lazy SQLite, `GET /api/health`
2. SQLite schema + seed (tables below)
3. Portfolio + trade + watchlist REST
4. Chat route: structured output + auto-execute (Zen or mock)
5. Next.js terminal UI (watchlist, chart, heatmap, P&L, positions, trade bar, chat) + frontend unit tests
6. `desktop/` pywebview: spawn sidecar, open window, pass `FINALLY_DB_PATH`, die together
7. Start/stop scripts (macOS first, Windows scripts still required) + Playwright E2E with `LLM_MOCK=true`

---

## 8. Database

Lazy init on startup / first request. If the file or tables are missing, create schema and seed.

All tables include **`user_id`** defaulting to `"default"` (single user now). **Required** — do not drop the column. Do not build user switching.

**users_profile** — `id` TEXT PK (default `"default"`), `cash_balance` REAL default `10000.0`, `created_at` TEXT

**watchlist** — `id` TEXT PK, `user_id`, `ticker`, `added_at`; UNIQUE `(user_id, ticker)`

**positions** — `id` TEXT PK, `user_id`, `ticker`, `quantity` REAL, `avg_cost` REAL, `updated_at`; UNIQUE `(user_id, ticker)`

**trades** — append-only: `id`, `user_id`, `ticker`, `side` (`buy`|`sell`), `quantity`, `price`, `executed_at`

**portfolio_snapshots** — `id`, `user_id`, `total_value`, `recorded_at`  
Record on sidecar start, every 30s, and immediately after each trade (so the P&L chart is not empty).

**chat_messages** — `id`, `user_id`, `role` (`user`|`assistant`), `content`, `actions` TEXT JSON (null for user), `created_at`

Seed: one profile `$10,000`; ten default tickers listed above.

---

## 9. API

Same contracts as the archived plan.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE live prices |
| GET | `/api/portfolio` | Positions, cash, total value, unrealized P&L |
| POST | `/api/portfolio/trade` | `{ticker, quantity, side}` market fill |
| GET | `/api/portfolio/history` | Snapshots for the P&L chart |
| GET | `/api/watchlist` | Tickers + latest prices |
| POST | `/api/watchlist` | `{ticker}` |
| DELETE | `/api/watchlist/{ticker}` | Remove ticker |
| POST | `/api/chat` | Full JSON reply (no token stream) |
| GET | `/api/health` | Sidecar liveness |

Frontend uses the **same origin** as FastAPI (static export + `/api`). No CORS. No `NEXT_PUBLIC_API_URL`. Port fallback only changes the window URL.

Trade rules: instant fill at current cache price; reject insufficient cash / shares; fractional qty allowed.

- **Sell-to-zero:** delete the `positions` row when quantity hits 0.
- **Unknown ticker:** a trade auto-adds that ticker to the watchlist **and** calls `MarketDataSource.add_ticker` before fill (need a price in cache).
- **Watchlist POST/DELETE** must call `source.add_ticker` / `source.remove_ticker`. New symbols have no SSE ticks and cannot fill until the source knows them.

SSE events are already a **dict of all cached tickers** (`data: {"AAPL": {...}, ...}`), not one event per symbol.

---

## 10. In-app LLM (OpenCode Zen)

When writing LLM call code, use `.cursor/skills/zen-inference/SKILL.md`.

On `POST /api/chat`:

1. Load cash, positions + P&L, watchlist + live prices, last **10** `chat_messages`
2. Call Zen (or mock) with structured output
3. Auto-execute trades / watchlist changes (same validation as manual, including auto-add + market-source wiring)
4. Persist messages + actions
5. Return `{ message, trades, watchlist_changes, errors? }`

```json
{
  "message": "conversational reply",
  "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],
  "watchlist_changes": [{"ticker": "PYPL", "action": "add"}]
}
```

- `message` required. `trades` / `watchlist_changes` optional.
- Failed validations go in `errors` so the assistant can tell the user. Never silently no-op a bad payload.
- Auto-execute is intentional (sim money, agentic demo).
- No token-by-token streaming; a loading indicator is enough.
- If `response_format` is ignored (common on free models), parse JSON from the text. Do not crash the route.
- Zen 429 / timeout / missing key → HTTP error + user-visible message. **Not** a silent mock.

System prompt: FinAlly, concise, data-driven, valid structured JSON only.
Analyze concentration and P&L; suggest trades with reasons; execute when asked; manage the watchlist.

`LLM_MOCK=true` → deterministic replies (e.g. buy 1 AAPL) for tests and key-free dev.

---

## 11. Frontend

Single-page terminal. Must include:

- Watchlist: symbol, price (flash), **session** change % vs seed/open, sparkline (ticks since launch)
- Main chart for the selected ticker (same in-session ticks)
- Portfolio treemap (size = weight, color = P&L)
- P&L line chart from `portfolio_snapshots`
- Positions table: ticker, qty, avg cost, price, unrealized P&L, %
- Trade bar: ticker, quantity, Buy, Sell
- Collapsible chat: history, input, loading state, inline trade/watchlist confirmations
- Header: total value, cash, status dot

`EventSource` → `/api/stream/prices` (parse the all-tickers dict). Charts: **Recharts only**. Tailwind dark theme. Next.js `output: 'export'` so FastAPI can serve the files.

---

## 12. Desktop shell (pywebview)

- Window ~1400×900, dark background, title `FinAlly`
- Bind API to `127.0.0.1` only — never `0.0.0.0`. Never `file://`.
- If `FINALLY_PORT` is busy, try the next ports through 8010 and load **that** origin in the webview (UI is same-origin, so no rebuilt env var)
- Sidecar process dies when the window closes (and vice versa)
- SQLite path: `FINALLY_DB_PATH` or OS app-data (`FinAlly/finally.db`)
- Status dot: green = sidecar + SSE, yellow = reconnecting, red = down
- Implement **macOS first**; Windows start/stop scripts stay in the spec (Edge WebView2)

No Docker, no Tauri, no cloud deploy in the core build.

---

## 13. Testing

**Backend (pytest)** — keep the existing 73 market tests. Add: trade math, cash/share rejects, watchlist CRUD, chat mock, structured-parse + validation in the chat flow, API status codes.

**Frontend** — component render, price flash on tick, watchlist CRUD, portfolio numbers, chat loading.

**E2E (`test/`)** — required. Start sidecar + exported UI with `LLM_MOCK=true`. Playwright hits the loopback origin (same as the desktop window). Scenarios:

- Fresh start: default watchlist, $10k, prices moving
- Add/remove ticker
- Buy / sell updates cash and positions
- Heatmap + P&L chart render
- Mock chat returns a reply; inline trade confirmation
- SSE reconnects after a drop

---

## 14. Out of scope

- Docker / App Runner / Terraform as the primary launch path
- Tauri or Electron
- Real brokerage, limit orders, auth, multi-user
- OpenRouter / Cerebras as the default LLM
- Using OpenCode file/bash tools from the trading chat

---

## 15. Cursor workflow

| Mechanism | Where | Use |
|---|---|---|
| Rules | `.cursor/rules/` | Always-on desktop + LLM policy; scoped backend/frontend/desktop |
| Subagents | `.cursor/agents/` | `@frontend` `@backend` `@desktop` `@reviewer` |
| Commands | `.cursor/commands/` | `/ship-api` `/ship-ui` `/mock-chat` `/doc-review` |
| Skill | `.cursor/skills/zen-inference/` | Writing in-app LLM calls |
| Hooks | `.cursor/hooks.json` | Ask on `docker` / `rm -rf`; do not format lockfiles |

Prefer this file when the archived `PLAN.md` disagrees (launch UX, LLM vendor, desktop shell).

---

## 16. Doc review — recheck and adopted decisions (2026-09-14)

Teacher-required (do **not** simplify away):

- **`user_id` on every table** (hardcode `"default"`; no user switching)
- **Massive** stays as the real-data path when `MASSIVE_API_KEY` is set
- **Frontend unit tests** (RTL or similar)
- **Playwright E2E** in `test/`
- **Backend pytest** including the existing 73 market tests
- **Start/stop scripts** for macOS **and** Windows
- **Next.js** — the course spec names it; switching to Vite was left in the simplify list only because it was unclear. **Rejected.** Keep Next.js static export.

### Leftover opportunities — what we did with them

| Leftover idea | Verdict | Why |
|---|---|---|
| Next.js → Vite | **Rejected** | Course `PLAN.md` requires Next.js. Teacher did not authorize dropping it. |
| One process: FastAPI serves the static UI | **Adopted** | Same as the course “single origin” idea, without Docker. |
| Ticks-since-launch charts (no history API) | **Adopted** | Honest with the existing SSE; no extra market table. |
| Session change % vs seed/open, not “daily” | **Adopted** | `PriceUpdate.change_percent` is last-tick; “daily” would be fake. |
| Recharts only | **Adopted** | Course said “Lightweight Charts or Recharts”; one lib is enough. |
| macOS scripts first; Windows later | **Adopted as order only** | Both script pairs stay in the spec. Build macOS first (this machine). |
| Cap chat at ~10 turns; Zen errors ≠ silent mock | **Adopted** | Protects free-model limits; `LLM_MOCK` stays explicit. |

Dropped from the simplify list (teacher): do not remove `user_id`, Massive, FE unit tests, Playwright E2E, or `stop_*` scripts.

### Adopted decisions (binding — folded into §§1–15)

1. **One origin.** Next.js `output: 'export'`; FastAPI serves those files; pywebview loads only `http://127.0.0.1:<port>`. No CORS, no `NEXT_PUBLIC_API_URL`, no `file://`.
2. **Next.js stays.** Do not replace it with Vite.
3. **Charts** = ticks since launch. Change % = vs session-open/seed, labeled **session**.
4. **Watchlist POST/DELETE** always calls `MarketDataSource.add_ticker` / `remove_ticker`.
5. **`FINALLY_DB_PATH`** in env; default OS app-data `FinAlly/finally.db`.
6. **Browser is a dev shortcut** against the same loopback origin. **Graded launch** is pywebview.
7. **Sell-to-zero** deletes the position row. **Unknown ticker** on a trade auto-adds to watchlist + market source, then fills.
8. Chat sends the last **10** turns. Parse JSON if `response_format` is ignored. Zen 429 / missing key → visible error, not mock.
9. **Recharts only.** Keep **pytest + frontend unit tests + Playwright E2E**. Implement **macOS first**; keep Windows scripts.
10. Snapshot portfolio **on start**, every 30s, and after each trade.
11. SSE payload is the existing all-tickers dict.
12. Confirm the live Zen model id when writing `.env.example`; default remains `openai/mimo-v2.5-free` until that check.
