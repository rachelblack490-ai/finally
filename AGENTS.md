# FinAlly — agent entry

Active spec: [`planning/CURSOR_PLAN.md`](planning/CURSOR_PLAN.md)

- Desktop app via **pywebview** + FastAPI on `127.0.0.1` (not a public `:8000` browser app)
- In-app chat: **OpenCode Zen** or `LLM_MOCK=true`
- Market data in `backend/app/market/` is complete — do not rewrite it
- Archived course spec: [`planning/PLAN.md`](planning/PLAN.md)

Cursor extras live under `.cursor/` (rules, agents, commands, hooks, `zen-inference` skill).
