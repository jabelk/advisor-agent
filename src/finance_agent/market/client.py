"""Alpaca data client wrapper with token-bucket rate limiting."""

from __future__ import annotations

import logging
import time

from alpaca.data.historical import StockHistoricalDataClient

logger = logging.getLogger(__name__)

# Rate limit: 180 req/min (90% of Alpaca free-tier 200 req/min)
_MAX_REQUESTS_PER_MINUTE = 180
_WINDOW_SECONDS = 60.0


class RateLimiter:
    """Simple token-bucket rate limiter."""

    def __init__(
        self,
        max_requests: int = _MAX_REQUESTS_PER_MINUTE,
        window: float = _WINDOW_SECONDS,
    ) -> None:
        self._max_requests = max_requests
        self._window = window
        self._timestamps: list[float] = []

    def acquire(self) -> None:
        """Block until a request slot is available."""
        now = time.monotonic()
        # Purge timestamps outside the window
        cutoff = now - self._window
        self._timestamps = [t for t in self._timestamps if t > cutoff]

        if len(self._timestamps) >= self._max_requests:
            # Wait until the oldest timestamp expires
            sleep_time = self._timestamps[0] - cutoff
            if sleep_time > 0:
                logger.debug("Rate limit: sleeping %.2fs", sleep_time)
                time.sleep(sleep_time)

        self._timestamps.append(time.monotonic())

    @property
    def remaining(self) -> int:
        """Return approximate remaining requests in current window."""
        now = time.monotonic()
        cutoff = now - self._window
        active = sum(1 for t in self._timestamps if t > cutoff)
        return max(0, self._max_requests - active)


def create_data_client(api_key: str, secret_key: str) -> StockHistoricalDataClient:
    """Create an Alpaca StockHistoricalDataClient."""
    return StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)
