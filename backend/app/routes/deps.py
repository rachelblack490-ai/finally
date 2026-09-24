"""Shared FastAPI dependencies that pull the app's singletons off app.state."""

from __future__ import annotations

from fastapi import Request

from ..db import Database
from ..market import MarketDataSource, PriceCache


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_cache(request: Request) -> PriceCache:
    return request.app.state.cache


def get_source(request: Request) -> MarketDataSource:
    return request.app.state.source
