"""Abstract interface for market data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    """Contract for market data providers.

    Implementations push price updates into a shared PriceCache on their own
    schedule. Downstream code never calls the data source directly for prices —
    it reads from the cache.

    Lifecycle:
        source = create_market_data_source(cache)
        await source.start(["AAPL", "GOOGL", ...])
        # ... app runs ...
        await source.add_ticker("TSLA")
        await source.remove_ticker("GOOGL")
        # ... app shutting down ...
        await source.stop()
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates for the given tickers.

        Starts a background task that periodically writes to the PriceCache.
        Safe to call twice: a second start() is a no-op while the source is running.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background task and release resources.

        Safe to call multiple times. After stop(), the source will not write
        to the cache again.
        """

    @abstractmethod
    async def add_ticker(self, ticker: str, *, wait_timeout: float = 0.0) -> None:
        """Add a ticker to the active set. No-op if already present.

        The next update cycle will include this ticker.

        If ``wait_timeout`` > 0, block until a price is in the cache or the
        timeout elapses (Massive). Simulator always seeds immediately.
        Callers that will fill an order should wait, then reject on cache miss.
        """

    @abstractmethod
    async def remove_ticker(self, ticker: str, *, drop_cache: bool = True) -> None:
        """Remove a ticker from the active set. No-op if not present.

        If ``drop_cache`` is True (default), also deletes the PriceCache row.
        Pass ``drop_cache=False`` when the user still holds the name so marks stay.
        """

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of actively tracked tickers."""
