"""Technical indicator computation and persistence (SMA, RSI, VWAP)."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


def compute_sma(closes: list[float], period: int) -> float | None:
    """Compute Simple Moving Average over the last `period` closing prices.

    Returns None if insufficient data.
    """
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """Compute Relative Strength Index using Wilder's smoothing.

    Returns None if insufficient data (needs period + 1 prices).
    """
    if len(closes) < period + 1:
        return None

    # Calculate price changes
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Initial average gain/loss over first `period` changes
    gains = [max(c, 0) for c in changes[:period]]
    losses = [max(-c, 0) for c in changes[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Wilder's smoothing for remaining changes
    for change in changes[period:]:
        gain = max(change, 0)
        loss = max(-change, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_vwap(bars: list[dict[str, float]]) -> float | None:
    """Compute VWAP from bar data (typical price * volume / total volume).

    Each bar dict must have keys: high, low, close, volume.
    Returns None if no bars or zero total volume.
    """
    if not bars:
        return None

    total_tpv = 0.0  # sum of typical_price * volume
    total_vol = 0.0

    for bar in bars:
        typical_price = (bar["high"] + bar["low"] + bar["close"]) / 3
        total_tpv += typical_price * bar["volume"]
        total_vol += bar["volume"]

    if total_vol == 0:
        return None

    return total_tpv / total_vol


def compute_and_persist_indicators(
    conn: sqlite3.Connection,
    ticker: str,
    company_id: int,
    timeframe: str,
) -> dict[str, float]:
    """Compute all indicators from stored bars and upsert into DB.

    Returns dict of indicator_type -> value for successfully computed indicators.
    """
    # Get closing prices ordered by timestamp
    rows = conn.execute(
        "SELECT close, high, low, volume, bar_timestamp FROM price_bar "
        "WHERE ticker = ? AND timeframe = ? ORDER BY bar_timestamp ASC",
        (ticker, timeframe),
    ).fetchall()

    if not rows:
        logger.debug("%s: no bars for %s, skipping indicators", ticker, timeframe)
        return {}

    closes = [float(row["close"]) for row in rows]
    bars_for_vwap = [
        {
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for row in rows
    ]
    last_bar_date = str(rows[-1]["bar_timestamp"])[:10]
    now_str = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    results: dict[str, float] = {}

    # SMA-20
    sma20 = compute_sma(closes, 20)
    if sma20 is not None:
        _upsert_indicator(
            conn, company_id, ticker, "sma_20", timeframe,
            sma20, now_str, last_bar_date,
        )
        results["sma_20"] = round(sma20, 2)
    else:
        logger.info(
            "%s: only %d bars, need 20 for SMA-20 — skipped",
            ticker, len(closes),
        )

    # SMA-50
    sma50 = compute_sma(closes, 50)
    if sma50 is not None:
        _upsert_indicator(
            conn, company_id, ticker, "sma_50", timeframe,
            sma50, now_str, last_bar_date,
        )
        results["sma_50"] = round(sma50, 2)
    else:
        logger.info(
            "%s: only %d bars, need 50 for SMA-50 — skipped",
            ticker, len(closes),
        )

    # RSI-14
    rsi14 = compute_rsi(closes, 14)
    if rsi14 is not None:
        _upsert_indicator(
            conn, company_id, ticker, "rsi_14", timeframe,
            rsi14, now_str, last_bar_date,
        )
        results["rsi_14"] = round(rsi14, 1)

    # VWAP (computed from recent bars — last 20 for daily)
    recent_bars = bars_for_vwap[-20:] if len(bars_for_vwap) >= 20 else bars_for_vwap
    vwap = compute_vwap(recent_bars)
    if vwap is not None:
        _upsert_indicator(
            conn, company_id, ticker, "vwap", timeframe,
            vwap, now_str, last_bar_date,
        )
        results["vwap"] = round(vwap, 2)

    conn.commit()
    return results


def _upsert_indicator(
    conn: sqlite3.Connection,
    company_id: int,
    ticker: str,
    indicator_type: str,
    timeframe: str,
    value: float,
    computed_at: str,
    bar_date: str,
) -> None:
    """Insert or update an indicator value."""
    conn.execute(
        "INSERT INTO technical_indicator "
        "(company_id, ticker, indicator_type, timeframe, value, "
        "computed_at, bar_date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(ticker, indicator_type, timeframe) "
        "DO UPDATE SET value=excluded.value, "
        "computed_at=excluded.computed_at, "
        "bar_date=excluded.bar_date, "
        "company_id=excluded.company_id",
        (company_id, ticker, indicator_type, timeframe, value,
         computed_at, bar_date),
    )
