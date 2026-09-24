"""Pydantic request/response models and the structured chat schema."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --- Portfolio / trading ---


class TradeRequest(BaseModel):
    ticker: str
    quantity: float = Field(gt=0)
    side: Literal["buy", "sell"]


class PositionOut(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    price: float
    market_value: float
    unrealized_pl: float
    unrealized_pl_percent: float


class PortfolioOut(BaseModel):
    cash: float
    positions_value: float
    total_value: float
    unrealized_pl: float
    positions: list[PositionOut]


class TradeResult(BaseModel):
    ok: bool
    ticker: str
    side: str
    quantity: float
    price: float
    cash: float
    message: str


class SnapshotOut(BaseModel):
    total_value: float
    recorded_at: str


# --- Watchlist ---


class WatchlistItem(BaseModel):
    ticker: str
    price: float | None = None
    previous_price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    direction: str | None = None


class WatchlistAddRequest(BaseModel):
    ticker: str


# --- Chat (structured LLM output) ---


class ChatTrade(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class WatchlistChange(BaseModel):
    ticker: str
    action: Literal["add", "remove"]


class ChatResponse(BaseModel):
    """Structured output contract for the trading assistant."""

    message: str
    trades: list[ChatTrade] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str


class ChatMessageOut(BaseModel):
    role: str
    content: str
    actions: dict | None = None
    created_at: str


class ChatReply(BaseModel):
    message: str
    trades: list[dict] = Field(default_factory=list)
    watchlist_changes: list[dict] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
