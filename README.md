# FinAlly

Desktop AI trading workstation: live prices, a simulated portfolio, and a chat assistant that can trade by structured JSON.

The product is a **pywebview** window over FastAPI on `127.0.0.1`. Opening a browser on port 8000 is a dev shortcut, not the app.

> [!NOTE]
> Active spec: [`planning/CURSOR_PLAN.md`](planning/CURSOR_PLAN.md). Market data in `backend/app/market/` is done. The rest of the desktop shell, UI, and portfolio APIs are still to be built.

## Features

- Live SSE prices (green/red flash), watchlist, sparklines, main chart
- $10,000 virtual cash; market orders only; no fees
- Heatmap, P&L chart, positions table
- Chat via **OpenCode Zen** (or `LLM_MOCK=true`) — auto-executes trades and watchlist changes
- Simulator by default; **Massive** when `MASSIVE_API_KEY` is set

## Stack

| Layer | Choice |
|---|---|
| Window | pywebview |
| UI | Next.js + TypeScript + Tailwind (static export, served by FastAPI) |
| API | FastAPI / uv on loopback |
| DB | SQLite (`FINALLY_DB_PATH` or OS app-data) |
| Chat | LiteLLM → OpenCode Zen |
| Market | GBM simulator or Massive REST |

## Setup

```bash
cp .env.example .env
# Set OPENCODE_API_KEY, or LLM_MOCK=true
# Optional: MASSIVE_API_KEY for live quotes
```

### Run the desktop app (macOS)

```bash
./scripts/start_mac.sh      # builds the UI, syncs deps, opens the FinAlly window
./scripts/stop_mac.sh       # stops the sidecar if still running
```

On Windows use `scripts/start_windows.ps1` / `scripts/stop_windows.ps1` (requires the Edge WebView2 runtime). The window loads a single loopback origin (`http://127.0.0.1:8000`, or the next free port through 8010): FastAPI serves the Next.js static export and the `/api/*` routes on that same origin. Never binds `0.0.0.0`; never loads `file://`.

### Dev shortcut (browser)

```bash
cd frontend && npm install && npm run build   # produces frontend/out
cd ../backend && uv sync --extra dev
LLM_MOCK=true uv run python -m app             # http://127.0.0.1:8000
```

### Tests

```bash
cd backend && uv run pytest         # backend + 73 market unit tests
cd frontend && npm test             # component unit tests (Vitest)
cd test && npx playwright test      # end-to-end (LLM_MOCK, static UI via FastAPI)
```

### Market demo (terminal)

```bash
cd backend && uv run market_data_demo.py
```

## Environment

| Variable | Role |
|---|---|
| `OPENCODE_API_KEY` | Zen key for in-app chat |
| `OPENCODE_MODEL` | Default `openai/mimo-v2.5-free` |
| `OPENCODE_API_BASE` | Default `https://opencode.ai/zen/v1` |
| `MASSIVE_API_KEY` | Real market data; empty = simulator |
| `LLM_MOCK` | `true` = offline deterministic chat |
| `FINALLY_HOST` / `FINALLY_PORT` | Loopback bind (`127.0.0.1:8000`) |
| `FINALLY_DB_PATH` | SQLite file; empty = `FinAlly/finally.db` in app-data |

## Layout

```
.cursor/     rules, agents, commands, hooks, zen-inference skill
backend/    FastAPI; market/ complete
desktop/    pywebview + sidecar launcher
frontend/   Next.js static export
planning/   CURSOR_PLAN.md (active), PLAN.md (archive)
test/       Playwright E2E
```

Agents should read [`AGENTS.md`](AGENTS.md) and [`planning/CURSOR_PLAN.md`](planning/CURSOR_PLAN.md).
