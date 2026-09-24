"""Portfolio, trade, and history endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..db import Database
from ..market import MarketDataSource, PriceCache
from ..schemas import PortfolioOut, SnapshotOut, TradeRequest, TradeResult
from ..services import portfolio as svc
from .deps import get_cache, get_db, get_source

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioOut)
async def get_portfolio(
    db: Database = Depends(get_db),
    cache: PriceCache = Depends(get_cache),
) -> PortfolioOut:
    return svc.build_portfolio(db, cache)


@router.post("/trade", response_model=TradeResult)
async def post_trade(
    body: TradeRequest,
    db: Database = Depends(get_db),
    cache: PriceCache = Depends(get_cache),
    source: MarketDataSource = Depends(get_source),
) -> TradeResult:
    try:
        return await svc.execute_trade(
            db, cache, source, body.ticker, body.side, body.quantity
        )
    except svc.TradeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/history", response_model=list[SnapshotOut])
async def get_history(db: Database = Depends(get_db)) -> list[SnapshotOut]:
    return [SnapshotOut(**row) for row in svc.get_history(db)]
