"""Market data fetching and caching for Pattern Lab backtesting."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_and_cache_bars(
    conn: sqlite3.Connection,
    ticker: str,
    start_date: str,
    end_date: str,
    timeframe: str = "day",
    api_key: str = "",
    secret_key: str = "",
) -> list[dict]:
    """Fetch historical bars from Alpaca and cache in price_cache table.

    Returns cached data if available, fetches from Alpaca API otherwise.
    Dates should be ISO 8601 format (YYYY-MM-DD).
    """
    # Check what's already cached
    cached = get_cached_bars(conn, ticker, start_date, end_date, timeframe)
    if cached:
        logger.debug("Using %d cached bars for %s", len(cached), ticker)
        return cached

    # Fetch from Alpaca
    bars = _fetch_from_alpaca(ticker, start_date, end_date, timeframe, api_key, secret_key)

    # Cache the results
    if bars:
        _cache_bars(conn, ticker, timeframe, bars)
        logger.info("Cached %d bars for %s (%s to %s)", len(bars), ticker, start_date, end_date)

    return bars


def get_cached_bars(
    conn: sqlite3.Connection,
    ticker: str,
    start_date: str,
    end_date: str,
    timeframe: str = "day",
) -> list[dict]:
    """Get cached price bars for a ticker within a date range."""
    rows = conn.execute(
        "SELECT * FROM price_cache "
        "WHERE ticker = ? AND timeframe = ? AND bar_timestamp >= ? AND bar_timestamp <= ? "
        "ORDER BY bar_timestamp",
        (ticker, timeframe, start_date, end_date),
    ).fetchall()
    return [dict(r) for r in rows]


def _fetch_from_alpaca(
    ticker: str,
    start_date: str,
    end_date: str,
    timeframe: str,
    api_key: str,
    secret_key: str,
) -> list[dict]:
    """Fetch historical bars from Alpaca Markets API."""
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
    except ImportError:
        logger.error("alpaca-py is required for market data. Install with: pip install alpaca-py")
        return []

    if not api_key or not secret_key:
        logger.error("Alpaca API keys required for market data fetch")
        return []

    client = StockHistoricalDataClient(api_key, secret_key)

    tf = TimeFrame.Day if timeframe == "day" else TimeFrame.Hour

    request = StockBarsRequest(
        symbol_or_symbols=ticker,
        timeframe=tf,
        start=datetime.fromisoformat(start_date),
        end=datetime.fromisoformat(end_date),
    )

    try:
        bars_response = client.get_stock_bars(request)
    except Exception as e:
        logger.error("Failed to fetch bars for %s: %s", ticker, e)
        return []

    bars = []
    if ticker in bars_response.data:
        for bar in bars_response.data[ticker]:
            bars.append({
                "ticker": ticker,
                "timeframe": timeframe,
                "bar_timestamp": bar.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume),
                "vwap": float(bar.vwap) if bar.vwap else None,
            })

    return bars


def _cache_bars(
    conn: sqlite3.Connection,
    ticker: str,
    timeframe: str,
    bars: list[dict],
) -> None:
    """Insert bars into price_cache, skipping duplicates."""
    now = _now()
    for bar in bars:
        conn.execute(
            "INSERT OR IGNORE INTO price_cache "
            "(ticker, timeframe, bar_timestamp, open, high, low, close, volume, vwap, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ticker,
                timeframe,
                bar["bar_timestamp"],
                bar["open"],
                bar["high"],
                bar["low"],
                bar["close"],
                bar["volume"],
                bar.get("vwap"),
                now,
            ),
        )
    conn.commit()
