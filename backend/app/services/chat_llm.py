"""In-app trading assistant backed by OpenCode Zen (LiteLLM) or a deterministic
mock (``LLM_MOCK=true``).

The assistant returns structured JSON only (message / trades /
watchlist_changes). A missing key (mock off) or a Zen 429 / network / timeout
is surfaced as a handled error — never a silent mock, never a crash.
"""

from __future__ import annotations

import re

from .. import config
from ..schemas import ChatResponse, ChatTrade, WatchlistChange

MAX_HISTORY_TURNS = 10

SYSTEM_PROMPT = (
    "You are FinAlly, a concise, data-driven trading assistant for a simulated "
    "$10,000 portfolio. Analyze concentration and P&L, suggest trades with brief "
    "reasons, execute trades when asked, and manage the watchlist. You MUST reply "
    "with valid JSON only, matching this schema: "
    '{"message": string, "trades": [{"ticker": string, "side": "buy"|"sell", '
    '"quantity": number}], "watchlist_changes": [{"ticker": string, '
    '"action": "add"|"remove"}]}. "message" is required; "trades" and '
    '"watchlist_changes" are optional and default to empty lists. Market orders '
    "only; quantities are share counts (fractional allowed)."
)


class ChatLLMError(Exception):
    """Raised on missing key (mock off) or an upstream Zen failure."""


def build_context_message(portfolio: dict, watchlist: list[dict]) -> str:
    lines = ["Current account state:"]
    lines.append(f"- Cash: ${portfolio['cash']:,.2f}")
    lines.append(f"- Total value: ${portfolio['total_value']:,.2f}")
    lines.append(f"- Unrealized P&L: ${portfolio['unrealized_pl']:,.2f}")
    if portfolio["positions"]:
        lines.append("- Positions:")
        for p in portfolio["positions"]:
            lines.append(
                f"    {p['ticker']}: {p['quantity']:g} @ avg ${p['avg_cost']:.2f}, "
                f"last ${p['price']:.2f}, P&L ${p['unrealized_pl']:.2f}"
            )
    else:
        lines.append("- Positions: none")
    if watchlist:
        wl = ", ".join(
            f"{w['ticker']}(${w['price']:.2f})" if w.get("price") is not None else w["ticker"]
            for w in watchlist
        )
        lines.append(f"- Watchlist: {wl}")
    return "\n".join(lines)


def _parse_structured(raw: str) -> ChatResponse:
    """Parse the model output into ChatResponse, tolerating extra prose.

    Free models often ignore ``response_format``; fall back to extracting the
    first JSON object from the text.
    """
    raw = (raw or "").strip()
    try:
        return ChatResponse.model_validate_json(raw)
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return ChatResponse.model_validate_json(match.group(0))
        except Exception:
            pass
    # Could not extract structure: treat the whole text as a plain message.
    return ChatResponse(message=raw or "I couldn't produce a structured response.")


# --- Mock ---

_BUY_SELL_RE = re.compile(r"\b(buy|sell)\b\s+(\d+(?:\.\d+)?)?\s*([A-Za-z]{1,5})", re.IGNORECASE)
_WATCH_RE = re.compile(r"\b(add|watch|remove|unwatch|drop)\b\s+([A-Za-z]{1,5})", re.IGNORECASE)


def _mock_response(user_message: str) -> ChatResponse:
    """Deterministic structured reply for offline/dev/test use."""
    trades = []
    changes = []
    text = user_message or ""

    for verb, qty, ticker in _BUY_SELL_RE.findall(text):
        side = "buy" if verb.lower() == "buy" else "sell"
        quantity = float(qty) if qty else 1.0
        trades.append({"ticker": ticker.upper(), "side": side, "quantity": quantity})

    for verb, ticker in _WATCH_RE.findall(text):
        action = "add" if verb.lower() in {"add", "watch"} else "remove"
        changes.append({"ticker": ticker.upper(), "action": action})

    if trades or changes:
        parts = []
        if trades:
            parts.append(
                "executing " + ", ".join(f"{t['side']} {t['quantity']:g} {t['ticker']}" for t in trades)
            )
        if changes:
            parts.append(
                "updating watchlist (" + ", ".join(f"{c['action']} {c['ticker']}" for c in changes) + ")"
            )
        message = "[mock] " + " and ".join(parts) + "."
    else:
        message = (
            "[mock] I'm running in offline mode. Ask me to buy/sell a ticker "
            "(e.g. 'buy 2 AAPL') or add/remove one from the watchlist."
        )
    return ChatResponse(
        message=message,
        trades=[ChatTrade(**t) for t in trades],
        watchlist_changes=[WatchlistChange(**c) for c in changes],
    )


def generate(user_message: str, context_message: str, history: list[dict]) -> ChatResponse:
    """Produce a structured assistant response.

    Raises ChatLLMError when the key is missing (mock off) or Zen fails.
    """
    if config.llm_mock_enabled():
        return _mock_response(user_message)

    api_key = config.opencode_api_key()
    if not api_key:
        raise ChatLLMError(
            "OpenCode Zen key is not set. Set OPENCODE_API_KEY or LLM_MOCK=true."
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history[-MAX_HISTORY_TURNS:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": f"{context_message}\n\nUser: {user_message}"})

    try:
        from litellm import completion

        response = completion(
            model=config.opencode_model(),
            messages=messages,
            api_key=api_key,
            api_base=config.opencode_api_base(),
            response_format=ChatResponse,
            timeout=30,
        )
        raw = response.choices[0].message.content
    except Exception as exc:  # noqa: BLE001 - surface any upstream failure cleanly
        raise ChatLLMError(f"OpenCode Zen request failed: {exc}") from exc

    return _parse_structured(raw)
