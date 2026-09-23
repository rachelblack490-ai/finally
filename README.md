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

Market demo (works today):

```bash
cd backend
uv sync --extra dev
uv run pytest
uv run market_data_demo.py
```

Desktop launch (once `desktop/` and start scripts exist): FastAPI on `127.0.0.1:8000` (or 8001–8010), then a FinAlly window. Never bind `0.0.0.0`. Never load `file://`.

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
