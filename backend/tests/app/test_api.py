"""API status-code and contract tests via FastAPI TestClient (runs lifespan)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    monkeypatch.setenv("MASSIVE_API_KEY", "")  # force simulator
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "api.db"))
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["source"] == "SimulatorDataSource"
    assert len(body["tickers"]) == 10


def test_portfolio_initial_state(client):
    r = client.get("/api/portfolio")
    assert r.status_code == 200
    body = r.json()
    assert body["cash"] == 10000.0
    assert body["positions"] == []


def test_trade_buy_then_portfolio(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    port = client.get("/api/portfolio").json()
    assert any(p["ticker"] == "AAPL" for p in port["positions"])
    assert port["cash"] < 10000.0


def test_trade_insufficient_cash_returns_400(client):
    r = client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 100000, "side": "buy"}
    )
    assert r.status_code == 400


def test_trade_bad_payload_returns_422(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": -1, "side": "buy"})
    assert r.status_code == 422


def test_watchlist_add_and_delete(client):
    r = client.post("/api/watchlist", json={"ticker": "SNOW"})
    assert r.status_code == 200
    assert r.json()["ticker"] == "SNOW"

    wl = client.get("/api/watchlist").json()
    assert any(i["ticker"] == "SNOW" for i in wl)

    r = client.delete("/api/watchlist/SNOW")
    assert r.status_code == 204
    wl = client.get("/api/watchlist").json()
    assert all(i["ticker"] != "SNOW" for i in wl)


def test_chat_mock_executes_trade(client):
    r = client.post("/api/chat", json={"message": "buy 1 AAPL"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["message"]
    assert len(body["trades"]) == 1
    assert body["trades"][0]["ticker"] == "AAPL"

    # The user + assistant turns are persisted.
    hist = client.get("/api/chat/history").json()
    assert len(hist) == 2
    assert hist[0]["role"] == "user"
    assert hist[1]["role"] == "assistant"


def test_chat_empty_message_returns_400(client):
    r = client.post("/api/chat", json={"message": "   "})
    assert r.status_code == 400


def test_history_has_startup_snapshot(client):
    hist = client.get("/api/portfolio/history").json()
    assert len(hist) >= 1
    assert hist[0]["total_value"] == pytest.approx(10000.0, abs=1.0)
