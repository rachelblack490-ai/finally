---
description: Add or fix LLM_MOCK chat so FinAlly works without an OpenCode key
---

Implement or repair the mocked in-app assistant path (`LLM_MOCK=true`) per `planning/CURSOR_PLAN.md` §10.

Requirements:

- When `LLM_MOCK=true`, do not call OpenCode Zen or OpenRouter.
- Return deterministic structured JSON (stable message + a simple trade such as buy 1 AAPL when the prompt asks to trade).
- Still run the same trade/watchlist validation and persistence as the live path.
- When the Zen key is missing and mock is off, return a clear API error — do not crash the desktop window.
- Add pytest coverage for mock replies, validation failures, and persistence.

Use `.cursor/skills/zen-inference/SKILL.md` only as a contrast for the live path. Prefer `backend/` tests you can run offline.
