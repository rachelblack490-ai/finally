"""SSE stream tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI

from app.market.cache import PriceCache
from app.market.stream import _generate_events, create_stream_router


@pytest.mark.asyncio
async def test_sse_retry_and_price_payload():
    cache = PriceCache()
    cache.update("AAPL", 190.50)
    request = MagicMock()
    request.client.host = "test"
    request.is_disconnected = AsyncMock(side_effect=[False, False, True])

    chunks: list[str] = []
    async for chunk in _generate_events(cache, request, interval=0.01):
        chunks.append(chunk)

    body = "".join(chunks)
    assert "retry: 1000" in body
    assert "data: " in body
    assert "AAPL" in body
    assert "190.5" in body


def test_factory_creates_independent_routers():
    cache = PriceCache()
    first = create_stream_router(cache)
    second = create_stream_router(cache)
    assert first is not second
    app = FastAPI()
    app.include_router(first)
    app.include_router(second, prefix="/alt")
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/api/stream/prices" in paths
    assert "/alt/api/stream/prices" in paths
