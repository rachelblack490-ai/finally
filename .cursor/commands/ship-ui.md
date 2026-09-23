---
description: Implement FinAlly Next.js trading-terminal UI against CURSOR_PLAN.md
---

Implement the frontend work described in the current conversation, following `planning/CURSOR_PLAN.md` §§1, 9, and 11.

Requirements:

- Next.js + TypeScript + Tailwind in `frontend/`, `output: 'export'`
- `EventSource` on `/api/stream/prices` (all-tickers dict); price flash; sparklines + main chart from ticks since load
- Session change % vs seed/open (not “daily”). Recharts only.
- Watchlist, heatmap, P&L chart, positions, trade bar, chat, header status dot
- Colors: `#0d1117` / `#1a1a2e`, `#ecad0a`, `#209dd7`, `#753991`
- Same-origin relative `/api/*` only. Keep frontend unit tests.

Do not add Docker or “open localhost:8000” as the launch path. Summarize screens touched and how to verify in the desktop window.
