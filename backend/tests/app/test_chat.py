"""Chat LLM structured-output, mock, and error-handling tests."""

from __future__ import annotations

import pytest

from app.schemas import ChatResponse
from app.services import chat_llm


def test_mock_parses_buy_and_watchlist(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    resp = chat_llm.generate("buy 2 NVDA and add SNOW", "ctx", [])
    assert isinstance(resp, ChatResponse)
    assert any(t.ticker == "NVDA" and t.side == "buy" and t.quantity == 2 for t in resp.trades)
    assert any(c.ticker == "SNOW" and c.action == "add" for c in resp.watchlist_changes)


def test_mock_default_quantity_is_one(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    resp = chat_llm.generate("sell AAPL", "ctx", [])
    trade = next(t for t in resp.trades if t.ticker == "AAPL")
    assert trade.side == "sell"
    assert trade.quantity == 1


def test_mock_no_intent_returns_message_only(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    resp = chat_llm.generate("how is my portfolio doing?", "ctx", [])
    assert resp.message
    assert resp.trades == []
    assert resp.watchlist_changes == []


def test_missing_key_without_mock_raises(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "false")
    monkeypatch.setenv("OPENCODE_API_KEY", "")
    with pytest.raises(chat_llm.ChatLLMError):
        chat_llm.generate("hello", "ctx", [])


def test_parse_structured_from_clean_json():
    raw = '{"message": "hi", "trades": [], "watchlist_changes": []}'
    resp = chat_llm._parse_structured(raw)
    assert resp.message == "hi"


def test_parse_structured_extracts_json_from_prose():
    raw = 'Sure! Here is the plan:\n{"message": "buying", "trades": ' \
          '[{"ticker": "AAPL", "side": "buy", "quantity": 3}]}\nThanks.'
    resp = chat_llm._parse_structured(raw)
    assert resp.message == "buying"
    assert resp.trades[0].ticker == "AAPL"
    assert resp.trades[0].quantity == 3


def test_parse_structured_plain_text_becomes_message():
    resp = chat_llm._parse_structured("no json here at all")
    assert resp.message == "no json here at all"
    assert resp.trades == []


def test_build_context_message_includes_cash():
    ctx = chat_llm.build_context_message(
        {"cash": 9000.0, "total_value": 10000.0, "unrealized_pl": 0.0, "positions": []},
        [{"ticker": "AAPL", "price": 190.0}],
    )
    assert "$9,000.00" in ctx
    assert "AAPL" in ctx
