"""Historical option data: OCC symbol construction, contract selection, and bar fetching.

Provides real historical option prices for backtesting by:
1. Constructing OCC-format option symbols from pattern parameters
2. Fetching historical bars from Alpaca's OptionHistoricalDataClient
3. Caching results in the option_price_cache table
4. Falling back to synthetic pricing when no data is available
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# T003: OCC symbol construction
# ---------------------------------------------------------------------------


def build_occ_symbol(
    ticker: str,
    expiration_date: date,
    strike_price: float,
    option_type: str,
) -> str:
    """Construct an OCC-format option symbol from components.

    Format: {TICKER}{YYMMDD}{C|P}{STRIKE*1000:08d}
    Example: ABBV, 2024-03-15, 170.0, "call" → "ABBV240315C00170000"
    """
    type_char = "C" if option_type.lower() == "call" else "P"
    date_str = expiration_date.strftime("%y%m%d")
    strike_int = int(round(strike_price * 1000))
    return f"{ticker.upper()}{date_str}{type_char}{strike_int:08d}"


# ---------------------------------------------------------------------------
# T004: Nearest standard expiration
# ---------------------------------------------------------------------------


def find_nearest_expiration(target_date: date, prefer_monthly: bool = True) -> date:
    """Find the nearest standard option expiration date to a target date.

    Monthly expirations fall on the 3rd Friday of each month.
    If prefer_monthly is False, returns the nearest Friday.
    """
    if not prefer_monthly:
        # Nearest Friday: weekday 4 = Friday
        days_ahead = (4 - target_date.weekday()) % 7
        nearest_fri = target_date + timedelta(days=days_ahead)
        # If target is Saturday (5) or Sunday (6), days_ahead goes forward.
        # Also check the previous Friday.
        prev_fri = nearest_fri - timedelta(days=7)
        if abs((nearest_fri - target_date).days) <= abs((prev_fri - target_date).days):
            return nearest_fri
        return prev_fri

    # Find 3rd Fridays of the target month and neighboring months
    candidates: list[date] = []
    for month_offset in (-1, 0, 1, 2):
        year = target_date.year
        month = target_date.month + month_offset
        if month < 1:
            month += 12
            year -= 1
        elif month > 12:
            month -= 12
            year += 1
        candidates.append(_third_friday(year, month))

    # Return the candidate closest to the target date
    return min(candidates, key=lambda d: abs((d - target_date).days))


def _third_friday(year: int, month: int) -> date:
    """Return the 3rd Friday of the given month."""
    # First day of month
    first = date(year, month, 1)
    # Find the first Friday: weekday 4 = Friday
    days_to_friday = (4 - first.weekday()) % 7
    first_friday = first + timedelta(days=days_to_friday)
    # 3rd Friday = first Friday + 14 days
    return first_friday + timedelta(days=14)


# ---------------------------------------------------------------------------
# T005: Strike price rounding
# ---------------------------------------------------------------------------


def round_strike_price(
    underlying_price: float,
    strike_strategy: str,
    custom_offset_pct: float | None = None,
    option_type: str = "call",
) -> float:
    """Calculate and round a target strike price based on strategy.

    Strategies:
      atm     — at the money (nearest strike to underlying price)
      otm_5   — 5% out of the money
      otm_10  — 10% out of the money
      itm_5   — 5% in the money
      custom  — custom_offset_pct out of the money

    Strike increments: $5 for stocks >$100, $2.50 for $25-100, $1 for <$25.
    """
    # Calculate raw target price based on strategy
    if strike_strategy == "atm":
        raw = underlying_price
    elif strike_strategy == "otm_5":
        raw = _apply_otm_offset(underlying_price, 0.05, option_type)
    elif strike_strategy == "otm_10":
        raw = _apply_otm_offset(underlying_price, 0.10, option_type)
    elif strike_strategy == "itm_5":
        raw = _apply_itm_offset(underlying_price, 0.05, option_type)
    elif strike_strategy == "custom":
        pct = custom_offset_pct or 0.0
        raw = _apply_otm_offset(underlying_price, pct, option_type)
    else:
        raw = underlying_price

    # Round to nearest standard strike increment
    increment = _strike_increment(underlying_price)
    return round(round(raw / increment) * increment, 2)


def _apply_otm_offset(price: float, pct: float, option_type: str) -> float:
    """Out-of-the-money: calls go higher, puts go lower."""
    if option_type.lower() == "call":
        return price * (1 + pct)
    return price * (1 - pct)


def _apply_itm_offset(price: float, pct: float, option_type: str) -> float:
    """In-the-money: calls go lower, puts go higher."""
    if option_type.lower() == "call":
        return price * (1 - pct)
    return price * (1 + pct)


def _strike_increment(underlying_price: float) -> float:
    """Standard strike price increment based on underlying price."""
    if underlying_price > 100:
        return 5.0
    elif underlying_price >= 25:
        return 2.5
    return 1.0


# ---------------------------------------------------------------------------
# T006: Fetch and cache option bars
# ---------------------------------------------------------------------------


def fetch_and_cache_option_bars(
    conn: sqlite3.Connection,
    option_symbol: str,
    start_date: str,
    end_date: str,
    api_key: str,
    secret_key: str,
) -> list[dict]:
    """Fetch historical bars for an option symbol and cache them.

    Checks the option_price_cache first; fetches from Alpaca's
    OptionHistoricalDataClient for uncached ranges. Returns empty list
    if the broker has no data for this symbol.
    """
    # Check cache first
    cached = _get_cached_option_bars(conn, option_symbol, start_date, end_date)
    if cached:
        logger.debug("Using %d cached option bars for %s", len(cached), option_symbol)
        return cached

    # Fetch from Alpaca
    bars = _fetch_option_bars_from_alpaca(
        option_symbol, start_date, end_date, api_key, secret_key
    )

    # Cache results
    if bars:
        _cache_option_bars(conn, bars)
        logger.info(
            "Cached %d option bars for %s (%s to %s)",
            len(bars), option_symbol, start_date, end_date,
        )

    return bars


def _get_cached_option_bars(
    conn: sqlite3.Connection,
    option_symbol: str,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Get cached option bars from option_price_cache."""
    rows = conn.execute(
        "SELECT * FROM option_price_cache "
        "WHERE option_symbol = ? AND timeframe = 'day' "
        "AND bar_timestamp >= ? AND bar_timestamp <= ? "
        "ORDER BY bar_timestamp",
        (option_symbol, start_date, end_date),
    ).fetchall()
    return [dict(r) for r in rows]


def _extract_underlying_ticker(option_symbol: str) -> str:
    """Extract the underlying ticker from an OCC option symbol.

    OCC format: {TICKER}{YYMMDD}{C|P}{STRIKE*1000:08d}
    The ticker is everything before the 6-digit date portion.
    """
    # Walk backwards from position 6+ to find where letters end and digits begin
    for i in range(len(option_symbol) - 15, 0, -1):
        if option_symbol[i:i + 6].isdigit():
            return option_symbol[:i]
    return option_symbol[:4]  # fallback


def _fetch_option_bars_from_alpaca(
    option_symbol: str,
    start_date: str,
    end_date: str,
    api_key: str,
    secret_key: str,
) -> list[dict]:
    """Fetch historical option bars from Alpaca Markets API."""
    try:
        from alpaca.data.historical.option import OptionHistoricalDataClient
        from alpaca.data.requests import OptionBarsRequest
        from alpaca.data.timeframe import TimeFrame
    except ImportError:
        logger.error("alpaca-py is required for option data. Install with: pip install alpaca-py")
        return []

    if not api_key or not secret_key:
        logger.error("Alpaca API keys required for option data fetch")
        return []

    client = OptionHistoricalDataClient(api_key, secret_key)

    request = OptionBarsRequest(
        symbol_or_symbols=option_symbol,
        timeframe=TimeFrame.Day,
        start=datetime.fromisoformat(start_date),
        end=datetime.fromisoformat(end_date),
    )

    try:
        bars_response = client.get_option_bars(request)
    except Exception as e:
        logger.error("Failed to fetch option bars for %s: %s", option_symbol, e)
        return []

    underlying = _extract_underlying_ticker(option_symbol)
    bars: list[dict] = []
    if option_symbol in bars_response.data:
        for bar in bars_response.data[option_symbol]:
            bars.append({
                "option_symbol": option_symbol,
                "underlying_ticker": underlying,
                "timeframe": "day",
                "bar_timestamp": bar.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume),
                "trade_count": int(bar.trade_count) if bar.trade_count else None,
            })

    return bars


# ---------------------------------------------------------------------------
# T007: Select option contract (orchestrator)
# ---------------------------------------------------------------------------


def select_option_contract(
    conn: sqlite3.Connection,
    underlying_ticker: str,
    underlying_price: float,
    entry_date: date,
    exit_date: date,
    strike_strategy: str,
    custom_strike_offset_pct: float | None,
    expiration_days: int,
    option_type: str,
    api_key: str,
    secret_key: str,
) -> dict[str, Any]:
    """Select the best-matching option contract and fetch its historical bars.

    Orchestrates: strike rounding → expiration finding → OCC symbol →
    bar fetching → fallback to ±1 strike if no data.

    Returns dict with option_symbol, strike, expiration, entry_premium,
    exit_premium, volume_at_entry, and pricing ("real" or "estimated").
    """
    # Calculate target strike
    strike = round_strike_price(
        underlying_price, strike_strategy, custom_strike_offset_pct, option_type
    )

    # Find nearest expiration
    target_exp = entry_date + timedelta(days=expiration_days)
    expiration = find_nearest_expiration(target_exp, prefer_monthly=True)

    # Build OCC symbol and fetch bars
    symbol = build_occ_symbol(underlying_ticker, expiration, strike, option_type)

    # Date range: from a few days before entry to a few days after exit
    fetch_start = (entry_date - timedelta(days=5)).isoformat()
    fetch_end = (exit_date + timedelta(days=5)).isoformat()

    bars = fetch_and_cache_option_bars(conn, symbol, fetch_start, fetch_end, api_key, secret_key)

    # If no data, try ±1 strike increment
    if not bars:
        increment = _strike_increment(underlying_price)
        for offset in (increment, -increment):
            alt_strike = round(strike + offset, 2)
            alt_symbol = build_occ_symbol(underlying_ticker, expiration, alt_strike, option_type)
            bars = fetch_and_cache_option_bars(
                conn, alt_symbol, fetch_start, fetch_end, api_key, secret_key
            )
            if bars:
                symbol = alt_symbol
                strike = alt_strike
                break

    if not bars:
        # Fallback: no real data available
        return {
            "option_symbol": None,
            "strike": strike,
            "expiration": expiration.isoformat(),
            "entry_premium": None,
            "exit_premium": None,
            "volume_at_entry": None,
            "pricing": "estimated",
        }

    # Find bars closest to entry and exit dates
    entry_bar = _find_nearest_bar(bars, entry_date.isoformat())
    exit_bar = _find_nearest_bar(bars, exit_date.isoformat())

    entry_premium = entry_bar["close"] if entry_bar else None
    exit_premium = exit_bar["close"] if exit_bar else None
    volume_at_entry = entry_bar["volume"] if entry_bar else None

    if entry_premium is None or exit_premium is None:
        return {
            "option_symbol": symbol,
            "strike": strike,
            "expiration": expiration.isoformat(),
            "entry_premium": entry_premium,
            "exit_premium": exit_premium,
            "volume_at_entry": volume_at_entry,
            "pricing": "estimated",
        }

    return {
        "option_symbol": symbol,
        "strike": strike,
        "expiration": expiration.isoformat(),
        "entry_premium": entry_premium,
        "exit_premium": exit_premium,
        "volume_at_entry": volume_at_entry,
        "pricing": "real",
    }


def _find_nearest_bar(bars: list[dict], target_date: str) -> dict | None:
    """Find the bar with timestamp closest to the target date."""
    if not bars:
        return None
    target = target_date[:10]  # YYYY-MM-DD
    best = None
    best_diff = float("inf")
    for bar in bars:
        bar_date = bar["bar_timestamp"][:10]
        diff = abs(
            (datetime.fromisoformat(bar_date) - datetime.fromisoformat(target)).days
        )
        if diff < best_diff:
            best_diff = diff
            best = bar
    return best


def _cache_option_bars(
    conn: sqlite3.Connection,
    bars: list[dict],
) -> None:
    """Insert option bars into option_price_cache, skipping duplicates."""
    now = _now()
    for bar in bars:
        conn.execute(
            "INSERT OR IGNORE INTO option_price_cache "
            "(option_symbol, underlying_ticker, timeframe, bar_timestamp, "
            "open, high, low, close, volume, trade_count, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                bar["option_symbol"],
                bar["underlying_ticker"],
                bar["timeframe"],
                bar["bar_timestamp"],
                bar["open"],
                bar["high"],
                bar["low"],
                bar["close"],
                bar["volume"],
                bar.get("trade_count"),
                now,
            ),
        )
    conn.commit()
