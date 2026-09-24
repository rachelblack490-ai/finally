"""Fixtures for the FinAlly application (DB + market cache/source)."""

from __future__ import annotations

import pytest
import pytest_asyncio

from app.config import DEFAULT_WATCHLIST
from app.db import create_database
from app.market import PriceCache
from app.market.simulator import SimulatorDataSource


@pytest.fixture
def db(tmp_path):
    database = create_database(tmp_path / "test.db")
    yield database
    database.close()


@pytest.fixture
def cache() -> PriceCache:
    c = PriceCache()
    for ticker in DEFAULT_WATCHLIST:
        c.update(ticker, 100.0)
    return c


@pytest_asyncio.fixture
async def source(cache: PriceCache):
    src = SimulatorDataSource(price_cache=cache, update_interval=0.05)
    await src.start(DEFAULT_WATCHLIST)
    yield src
    await src.stop()
