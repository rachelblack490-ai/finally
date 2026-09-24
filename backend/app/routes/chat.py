"""Trading chat endpoint: structured LLM output + auto-execution."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from ..db import DEFAULT_USER, Database, new_id, now_iso
from ..market import MarketDataSource, PriceCache
from ..schemas import ChatMessageOut, ChatReply, ChatRequest
from ..services import chat_llm
from ..services import portfolio as pf
from ..services import watchlist as wl
from .deps import get_cache, get_db, get_source

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _load_history(db: Database) -> list[dict]:
    rows = db.query_all(
        "SELECT role, content, actions, created_at FROM chat_messages "
        "WHERE user_id = ? ORDER BY created_at ASC, rowid ASC",
        (DEFAULT_USER,),
    )
    return [
        {
            "role": r["role"],
            "content": r["content"],
            "actions": json.loads(r["actions"]) if r["actions"] else None,
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def _persist(db: Database, role: str, content: str, actions: dict | None) -> None:
    db.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            new_id(),
            DEFAULT_USER,
            role,
            content,
            json.dumps(actions) if actions is not None else None,
            now_iso(),
        ),
    )


@router.get("/history", response_model=list[ChatMessageOut])
async def chat_history(db: Database = Depends(get_db)) -> list[ChatMessageOut]:
    return [ChatMessageOut(**m) for m in _load_history(db)]


@router.post("", response_model=ChatReply)
async def post_chat(
    body: ChatRequest,
    db: Database = Depends(get_db),
    cache: PriceCache = Depends(get_cache),
    source: MarketDataSource = Depends(get_source),
) -> ChatReply:
    user_message = body.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required.")

    portfolio = pf.build_portfolio(db, cache).model_dump()
    watchlist = [w.model_dump() for w in wl.list_watchlist(db, cache)]
    history = _load_history(db)
    context = chat_llm.build_context_message(portfolio, watchlist)

    # Persist the user turn before calling the model.
    _persist(db, "user", user_message, None)

    try:
        result = chat_llm.generate(user_message, context, history)
    except chat_llm.ChatLLMError as exc:
        # Surface a visible error; do NOT silently fall back to mock.
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    executed_trades: list[dict] = []
    watchlist_changes: list[dict] = []
    errors: list[str] = []

    for trade in result.trades:
        try:
            res = await pf.execute_trade(
                db, cache, source, trade.ticker, trade.side, trade.quantity
            )
            executed_trades.append(res.model_dump())
        except pf.TradeError as exc:
            errors.append(f"Trade {trade.side} {trade.quantity:g} {trade.ticker}: {exc}")

    for change in result.watchlist_changes:
        try:
            if change.action == "add":
                await wl.add_ticker(db, cache, source, change.ticker)
            else:
                await wl.remove_ticker(db, cache, source, change.ticker)
            watchlist_changes.append({"ticker": change.ticker.upper(), "action": change.action})
        except wl.WatchlistError as exc:
            errors.append(f"Watchlist {change.action} {change.ticker}: {exc}")

    actions = {
        "trades": executed_trades,
        "watchlist_changes": watchlist_changes,
        "errors": errors,
    }
    _persist(db, "assistant", result.message, actions)

    return ChatReply(
        message=result.message,
        trades=executed_trades,
        watchlist_changes=watchlist_changes,
        errors=errors,
    )
