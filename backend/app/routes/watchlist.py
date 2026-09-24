"""Watchlist endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..db import Database
from ..market import MarketDataSource, PriceCache
from ..schemas import WatchlistAddRequest, WatchlistItem
from ..services import watchlist as svc
from .deps import get_cache, get_db, get_source

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItem])
async def get_watchlist(
    db: Database = Depends(get_db),
    cache: PriceCache = Depends(get_cache),
) -> list[WatchlistItem]:
    return svc.list_watchlist(db, cache)


@router.post("", response_model=WatchlistItem)
async def add_watchlist(
    body: WatchlistAddRequest,
    db: Database = Depends(get_db),
    cache: PriceCache = Depends(get_cache),
    source: MarketDataSource = Depends(get_source),
) -> WatchlistItem:
    try:
        return await svc.add_ticker(db, cache, source, body.ticker)
    except svc.WatchlistError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{ticker}", status_code=204)
async def delete_watchlist(
    ticker: str,
    db: Database = Depends(get_db),
    cache: PriceCache = Depends(get_cache),
    source: MarketDataSource = Depends(get_source),
) -> None:
    await svc.remove_ticker(db, cache, source, ticker)
