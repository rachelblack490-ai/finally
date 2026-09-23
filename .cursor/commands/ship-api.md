---
description: Implement or extend FinAlly FastAPI routes against CURSOR_PLAN.md
---

Implement the backend API work described in the current conversation, following `planning/CURSOR_PLAN.md`.

Requirements:

- Reuse `backend/app/market/` (PriceCache, factory, SSE router). Do not rewrite market data. Keep Massive + simulator.
- Bind `127.0.0.1` only. Serve the Next.js static export (same origin). Keep REST shapes in plan §9. Keep `user_id`.
- Trades: market fill at cache price; cash/share checks; sell-to-zero deletes the row; unknown ticker auto-adds + `add_ticker`.
- Watchlist POST/DELETE must call `source.add_ticker` / `source.remove_ticker`.
- Chat: last 10 turns; `zen-inference` or `LLM_MOCK=true`; JSON-parse fallback; 429 is an error.
- Add or update pytest coverage. Run `uv run --extra dev pytest` from `backend/` when the change is testable.

Stay in `backend/` unless a tiny shared env/schema file is required. Afterward, summarize endpoints touched and how to verify.
