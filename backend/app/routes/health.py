"""Liveness endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..market import MarketDataSource
from .deps import get_source

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health(source: MarketDataSource = Depends(get_source)) -> dict:
    return {
        "status": "ok",
        "tickers": source.get_tickers(),
        "source": type(source).__name__,
    }
