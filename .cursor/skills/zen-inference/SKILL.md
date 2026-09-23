---
name: zen-inference
description: Writes LiteLLM calls to OpenCode Zen (OpenAI-compatible) for FinAlly in-app chat and structured trade/watchlist output. Use when implementing POST /api/chat, LLM helpers, or replacing OpenRouter/Cerebras.
---

# OpenCode Zen inference

Use this when writing FinAlly backend code that calls an LLM. Do **not** use the archived Cerebras/OpenRouter skill for new chat code.

## Setup

Env (project root `.env`):

- `OPENCODE_API_KEY` — Zen key
- `OPENCODE_MODEL` — default `openai/mimo-v2.5-free` (or the current Zen free model id)
- `OPENCODE_API_BASE` — default `https://opencode.ai/zen/v1`
- `LLM_MOCK` — `true` skips the network and returns deterministic structured JSON

```bash
cd backend
uv add litellm pydantic
```

## Imports and constants

```python
import os
from litellm import completion

MODEL = os.environ.get("OPENCODE_MODEL", "openai/mimo-v2.5-free")
API_BASE = os.environ.get("OPENCODE_API_BASE", "https://opencode.ai/zen/v1")
API_KEY = os.environ.get("OPENCODE_API_KEY", "")
```

## Text completion

```python
response = completion(
    model=MODEL,
    messages=messages,
    api_key=API_KEY,
    api_base=API_BASE,
)
result = response.choices[0].message.content
```

## Structured output

```python
response = completion(
    model=MODEL,
    messages=messages,
    api_key=API_KEY,
    api_base=API_BASE,
    response_format=MyBaseModelSubclass,
)
result = response.choices[0].message.content
result_as_object = MyBaseModelSubclass.model_validate_json(result)
```

Expected FinAlly schema fields: `message` (str), `trades` (list of ticker/side/quantity), `watchlist_changes` (list of ticker/action).

## Rules

- If `LLM_MOCK` is true, do not call LiteLLM.
- If the key is missing and mock is off, raise/return a handled error — do not crash the app.
- Do not send the trading chat through OpenCode coding-agent tools (edit/bash).
- Do not default new code to `openrouter/` or Cerebras `extra_body`.
