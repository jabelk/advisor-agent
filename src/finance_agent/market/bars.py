"""Bar fetch, storage, and query operations for historical OHLCV data."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime, timedelta

from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from finance_agent.market.client import RateLimiter

logger = logging.getLogger(__name__)

# Default history windows
_DAILY_LOOKBACK_DAYS = 730  # ~2 years
_HOURLY_LOOKBACK_DAYS = 30

_TIMEFRAME_MAP = {
    "day": TimeFrame.Day,
    "hour": TimeFrame.Hour,
}


def get_latest_bar_timestamp(
    conn: sqlite3.Connection,
    ticker: str,
    timeframe: str,
) -> str | None:
    """Return the most recent bar_timestamp for a ticker/timeframe, or None."""
    row = conn.execute(
        "SELECT MAX(bar_timestamp) as latest FROM price_bar "
        "WHERE ticker = ? AND timeframe = ?",
        (ticker, timeframe),
    ).fetchone()
    return row["latest"] if row and row["latest"] else None


def fetch_bars(
    conn: sqlite3.Connection,
    client: StockHistoricalDataClient,
    ticker: str,
    company_id: int,
    timeframe: str,
    full: bool = False,
    rate_limiter: RateLimiter | None = None,
) -> int:
    """Fetch bars from Alpaca and store in price_bar table.

    Returns the number of new bars inserted.
    Uses INSERT OR IGNORE for dedup on incremental updates.
    """
    now = datetime.now(UTC)
    tf = _TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        raise ValueError(f"Invalid timeframe: {timeframe}")

    # Determine start date
    if full:
        lookback = (
            _DAILY_LOOKBACK_DAYS if timeframe == "day" else _HOURLY_LOOKBACK_DAYS
        )
        start = now - timedelta(days=lookback)
    else:
        latest = get_latest_bar_timestamp(conn, ticker, timeframe)
        if latest:
            start = datetime.fromisoformat(latest.replace("Z", "+00:00"))
        else:
            lookback = (
                _DAILY_LOOKBACK_DAYS if timeframe == "day"
                else _HOURLY_LOOKBACK_DAYS
            )
            start = now - timedelta(days=lookback)

    # End at 15 minutes ago to ensure SIP data availability on free tier
    end = now - timedelta(minutes=16)
    if start >= end:
        logger.debug("%s %s: already up to date", ticker, timeframe)
        return 0

    if rate_limiter:
        rate_limiter.acquire()

    request = StockBarsRequest(
        symbol_or_symbols=[ticker],
        timeframe=tf,
        start=start,
        end=end,
        adjustment=Adjustment.SPLIT,
        feed=DataFeed.SIP,
    )

    try:
        bars_response = client.get_stock_bars(request)
    except Exception as e:
        logger.error("Alpaca API error for %s %s: %s", ticker, timeframe, e)
        raise

    # Extract bars from response
    bars_data = bars_response.data.get(ticker, []) if bars_response.data else []

    if not bars_data:
        logger.debug("%s %s: no new bars from API", ticker, timeframe)
        return 0

    # Batch insert with INSERT OR IGNORE
    inserted = 0
    for bar in bars_data:
        ts = bar.timestamp.isoformat() if bar.timestamp else ""
        cursor = conn.execute(
            "INSERT OR IGNORE INTO price_bar "
            "(company_id, ticker, timeframe, bar_timestamp, "
            "open, high, low, close, volume, trade_count, vwap) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                company_id,
                ticker,
                timeframe,
                ts,
                float(bar.open),
                float(bar.high),
                float(bar.low),
                float(bar.close),
                float(bar.volume),
                float(bar.trade_count) if bar.trade_count else None,
                float(bar.vwap) if bar.vwap else None,
            ),
        )
        if cursor.rowcount > 0:
            inserted += 1

    conn.commit()
    logger.info("%s %s: inserted %d new bars", ticker, timeframe, inserted)
    return inserted


def query_bars(
    conn: sqlite3.Connection,
    ticker: str,
    timeframe: str,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> list[sqlite3.Row]:
    """Query stored bars by ticker, timeframe, and optional date range.

    Returns bars ordered by bar_timestamp ASC.
    """
    conditions = ["ticker = ?", "timeframe = ?"]
    params: list[str | int] = [ticker, timeframe]

    if start:
        conditions.append("bar_timestamp >= ?")
        params.append(start)
    if end:
        conditions.append("bar_timestamp <= ?")
        params.append(end)

    where = " AND ".join(conditions)
    sql = (
        f"SELECT * FROM price_bar WHERE {where} "
        "ORDER BY bar_timestamp ASC"
    )
    if limit:
        sql += f" LIMIT {limit}"

    return conn.execute(sql, params).fetchall()


def get_market_data_status(
    conn: sqlite3.Connection,
) -> list[dict[str, str | int | None]]:
    """Return per-ticker/timeframe summary of stored bars."""
    rows = conn.execute(
        "SELECT ticker, timeframe, COUNT(*) as bar_count, "
        "MIN(bar_timestamp) as from_date, MAX(bar_timestamp) as to_date "
        "FROM price_bar GROUP BY ticker, timeframe "
        "ORDER BY ticker, timeframe"
    ).fetchall()

    result = []
    for row in rows:
        # Get last fetch time
        fetch_row = conn.execute(
            "SELECT MAX(completed_at) as last_fetch "
            "FROM market_data_fetch "
            "WHERE ticker = ? AND timeframe = ? AND status = 'complete'",
            (row["ticker"], row["timeframe"]),
        ).fetchone()
        last_fetch = fetch_row["last_fetch"] if fetch_row else None

        result.append({
            "ticker": row["ticker"],
            "timeframe": row["timeframe"],
            "bar_count": row["bar_count"],
            "from_date": row["from_date"],
            "to_date": row["to_date"],
            "last_fetch": last_fetch,
        })

    return result


def get_latest_indicators(
    conn: sqlite3.Connection,
) -> list[dict[str, str | float | None]]:
    """Return latest indicator values per ticker."""
    rows = conn.execute(
        "SELECT ticker, indicator_type, timeframe, value, "
        "computed_at, bar_date "
        "FROM technical_indicator "
        "ORDER BY ticker, indicator_type"
    ).fetchall()
    return [dict(row) for row in rows]
