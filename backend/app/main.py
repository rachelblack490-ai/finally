"""FastAPI sidecar: one origin (API + static UI) bound to loopback.

Lifespan wires the existing market package (cache + source + SSE router),
lazily initializes SQLite, and records portfolio snapshots on start and every
30s. The Next.js static export is served from the same origin so the pywebview
window (and dev browser) load a single URL with no CORS.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .db import create_database
from .market import PriceCache, create_market_data_source
from .market.stream import _generate_events
from .routes import chat, health, portfolio, watchlist
from .services import portfolio as pf

logger = logging.getLogger(__name__)


def _static_dir() -> Path | None:
    override = os.environ.get("FINALLY_STATIC_DIR", "").strip()
    if override:
        p = Path(override).expanduser()
        return p if p.is_dir() else None
    # Default: the Next.js export at repo_root/frontend/out.
    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root / "frontend" / "out"
    return candidate if candidate.is_dir() else None


async def _snapshot_loop(app: FastAPI) -> None:
    """Record a portfolio snapshot every SNAPSHOT_INTERVAL_SECONDS."""
    while True:
        await asyncio.sleep(config.SNAPSHOT_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(pf.record_snapshot, app.state.db, app.state.cache)
        except Exception:
            logger.exception("Snapshot loop iteration failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.load_dotenv()

    db = create_database()
    cache = PriceCache()
    source = create_market_data_source(cache)

    # Track the seeded default watchlist from the DB (so restarts are honored).
    tickers = [row["ticker"] for row in db.query_all(
        "SELECT ticker FROM watchlist WHERE user_id = 'default' ORDER BY added_at ASC, rowid ASC"
    )]
    if not tickers:
        tickers = list(config.DEFAULT_WATCHLIST)

    await source.start(tickers)

    app.state.db = db
    app.state.cache = cache
    app.state.source = source

    # Baseline snapshot on start so the P&L chart is never empty.
    try:
        pf.record_snapshot(db, cache)
    except Exception:
        logger.exception("Initial snapshot failed")

    snapshot_task = asyncio.create_task(_snapshot_loop(app), name="snapshot-loop")

    try:
        yield
    finally:
        snapshot_task.cancel()
        try:
            await snapshot_task
        except asyncio.CancelledError:
            pass
        await source.stop()
        db.close()


def create_app() -> FastAPI:
    app = FastAPI(title="FinAlly", version="0.1.0", lifespan=lifespan)

    app.include_router(health.router)
    app.include_router(portfolio.router)
    app.include_router(watchlist.router)
    app.include_router(chat.router)

    # SSE price stream from the existing market package. Mount a placeholder
    # cache reference now; the real cache is created in lifespan, so we resolve
    # it lazily via a small shim router.
    app.include_router(_stream_router_proxy())

    static = _static_dir()
    if static is not None:
        app.mount("/", StaticFiles(directory=str(static), html=True), name="static")
        logger.info("Serving static UI from %s", static)
    else:
        logger.info("No static export found; API-only mode")

    return app


def _stream_router_proxy() -> APIRouter:
    """SSE router bound to the live cache via app.state at request time.

    ``create_stream_router`` needs a PriceCache, but the cache only exists after
    lifespan startup, so the endpoint reads ``request.app.state.cache`` and
    reuses the market package's event generator.
    """
    router = APIRouter(prefix="/api/stream", tags=["streaming"])

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        cache = request.app.state.cache
        return StreamingResponse(
            _generate_events(cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return router


app = create_app()
