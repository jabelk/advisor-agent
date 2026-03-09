"""Unit tests for option data functions: OCC symbols, expirations, strikes, bar caching."""

from __future__ import annotations

import sqlite3
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from finance_agent.patterns.option_data import (
    build_occ_symbol,
    fetch_and_cache_option_bars,
    find_nearest_expiration,
    round_strike_price,
    select_option_contract,
    _third_friday,
    _strike_increment,
    _extract_underlying_ticker,
)


# ---------------------------------------------------------------------------
# build_occ_symbol
# ---------------------------------------------------------------------------


class TestBuildOccSymbol:
    def test_call_standard(self):
        result = build_occ_symbol("ABBV", date(2024, 3, 15), 170.0, "call")
        assert result == "ABBV240315C00170000"

    def test_put_standard(self):
        result = build_occ_symbol("MRNA", date(2024, 6, 21), 125.0, "put")
        assert result == "MRNA240621P00125000"

    def test_fractional_strike(self):
        result = build_occ_symbol("ABBV", date(2024, 3, 15), 125.50, "call")
        assert result == "ABBV240315C00125500"

    def test_low_price_strike(self):
        result = build_occ_symbol("F", date(2024, 1, 19), 12.0, "put")
        assert result == "F240119P00012000"

    def test_high_price_strike(self):
        result = build_occ_symbol("SPY", date(2025, 12, 19), 500.0, "call")
        assert result == "SPY251219C00500000"

    def test_case_insensitive_option_type(self):
        assert build_occ_symbol("AAPL", date(2024, 1, 19), 190.0, "Call") == "AAPL240119C00190000"
        assert build_occ_symbol("AAPL", date(2024, 1, 19), 190.0, "PUT") == "AAPL240119P00190000"

    def test_ticker_uppercased(self):
        result = build_occ_symbol("aapl", date(2024, 1, 19), 190.0, "call")
        assert result == "AAPL240119C00190000"


# ---------------------------------------------------------------------------
# find_nearest_expiration
# ---------------------------------------------------------------------------


class TestFindNearestExpiration:
    def test_exact_third_friday(self):
        # March 15, 2024 IS the 3rd Friday
        result = find_nearest_expiration(date(2024, 3, 15))
        assert result == date(2024, 3, 15)

    def test_near_third_friday(self):
        # March 13 should snap to March 15 (3rd Friday)
        result = find_nearest_expiration(date(2024, 3, 13))
        assert result == date(2024, 3, 15)

    def test_early_in_month(self):
        # March 1 is closer to Feb 16 (3rd Fri Feb) or March 15 (3rd Fri Mar)
        result = find_nearest_expiration(date(2024, 3, 1))
        # March 1 is 14 days before Mar 15 and 14 days after Feb 16
        assert result in (date(2024, 2, 16), date(2024, 3, 15))

    def test_late_in_month(self):
        # April 10 is closer to April 19 (3rd Fri Apr) than March 15
        result = find_nearest_expiration(date(2024, 4, 10))
        assert result == date(2024, 4, 19)

    def test_weekly_nearest_friday(self):
        # March 12 (Tuesday) → nearest Friday is March 15
        result = find_nearest_expiration(date(2024, 3, 12), prefer_monthly=False)
        assert result == date(2024, 3, 15)

    def test_weekly_saturday(self):
        # March 16 (Saturday) → nearest Friday is March 15 (yesterday)
        result = find_nearest_expiration(date(2024, 3, 16), prefer_monthly=False)
        assert result == date(2024, 3, 15)

    def test_year_boundary(self):
        # Jan 10, 2025 is closer to Jan 17 (3rd Fri Jan) than Dec 20 (3rd Fri Dec)
        result = find_nearest_expiration(date(2025, 1, 10))
        jan_3rd_fri = _third_friday(2025, 1)
        assert result == jan_3rd_fri


# ---------------------------------------------------------------------------
# round_strike_price
# ---------------------------------------------------------------------------


class TestRoundStrikePrice:
    def test_atm_high_price(self):
        # ATM at $172.34, increment $5 → $170 or $175
        result = round_strike_price(172.34, "atm")
        assert result == 170.0

    def test_atm_near_round(self):
        result = round_strike_price(170.0, "atm")
        assert result == 170.0

    def test_otm_5_call(self):
        # 5% OTM call at $100 → $105, round to $105
        result = round_strike_price(100.0, "otm_5", option_type="call")
        assert result == 105.0

    def test_otm_5_put(self):
        # 5% OTM put at $100 → $95, round to $95
        result = round_strike_price(100.0, "otm_5", option_type="put")
        assert result == 95.0

    def test_otm_10_call(self):
        result = round_strike_price(150.0, "otm_10", option_type="call")
        assert result == 165.0  # 150 * 1.10 = 165

    def test_itm_5_call(self):
        # 5% ITM call at $200 → $190, round to $190
        result = round_strike_price(200.0, "itm_5", option_type="call")
        assert result == 190.0

    def test_itm_5_put(self):
        # 5% ITM put at $200 → $210, round to $210
        result = round_strike_price(200.0, "itm_5", option_type="put")
        assert result == 210.0

    def test_custom_offset(self):
        result = round_strike_price(100.0, "custom", custom_offset_pct=0.03, option_type="call")
        assert result == 102.5  # 103 rounded to nearest 2.5

    def test_increment_low_price(self):
        # Under $25, $1 increments
        result = round_strike_price(12.50, "atm")
        assert result == 12.0

    def test_increment_mid_price(self):
        # $25-100, $2.50 increments
        result = round_strike_price(50.0, "atm")
        assert result == 50.0

    def test_increment_high_price(self):
        # Over $100, $5 increments
        result = round_strike_price(152.0, "atm")
        assert result == 150.0


# ---------------------------------------------------------------------------
# _strike_increment
# ---------------------------------------------------------------------------


class TestStrikeIncrement:
    def test_low(self):
        assert _strike_increment(10.0) == 1.0

    def test_mid(self):
        assert _strike_increment(50.0) == 2.5

    def test_high(self):
        assert _strike_increment(150.0) == 5.0

    def test_boundary_25(self):
        assert _strike_increment(25.0) == 2.5

    def test_boundary_100(self):
        assert _strike_increment(100.0) == 2.5

    def test_just_over_100(self):
        assert _strike_increment(100.01) == 5.0


# ---------------------------------------------------------------------------
# _extract_underlying_ticker
# ---------------------------------------------------------------------------


class TestExtractUnderlyingTicker:
    def test_abbv(self):
        assert _extract_underlying_ticker("ABBV240315C00170000") == "ABBV"

    def test_single_char(self):
        assert _extract_underlying_ticker("F240119P00012000") == "F"

    def test_spy(self):
        assert _extract_underlying_ticker("SPY251219C00500000") == "SPY"


# ---------------------------------------------------------------------------
# _third_friday
# ---------------------------------------------------------------------------


class TestThirdFriday:
    def test_march_2024(self):
        assert _third_friday(2024, 3) == date(2024, 3, 15)

    def test_january_2025(self):
        assert _third_friday(2025, 1) == date(2025, 1, 17)

    def test_april_2024(self):
        assert _third_friday(2024, 4) == date(2024, 4, 19)


# ---------------------------------------------------------------------------
# fetch_and_cache_option_bars (mocked API)
# ---------------------------------------------------------------------------


@pytest.fixture
def option_db():
    """In-memory SQLite DB with option_price_cache table."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE option_price_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            option_symbol TEXT NOT NULL,
            underlying_ticker TEXT NOT NULL,
            timeframe TEXT NOT NULL DEFAULT 'day',
            bar_timestamp TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL,
            volume INTEGER, trade_count INTEGER,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE UNIQUE INDEX idx_option_price_unique
            ON option_price_cache(option_symbol, timeframe, bar_timestamp);
    """)
    yield conn
    conn.close()


class TestFetchAndCacheOptionBars:
    def test_returns_cached_data(self, option_db):
        # Pre-populate cache
        option_db.execute(
            "INSERT INTO option_price_cache "
            "(option_symbol, underlying_ticker, timeframe, bar_timestamp, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("ABBV240315C00170000", "ABBV", "day", "2024-03-13T00:00:00Z", 4.0, 5.0, 3.5, 4.5, 1500),
        )
        option_db.commit()

        result = fetch_and_cache_option_bars(
            option_db, "ABBV240315C00170000", "2024-03-10", "2024-03-15", "key", "secret",
        )
        assert len(result) == 1
        assert result[0]["close"] == 4.5

    @patch("finance_agent.patterns.option_data._fetch_option_bars_from_alpaca")
    def test_fetches_and_caches_on_miss(self, mock_fetch, option_db):
        mock_fetch.return_value = [
            {
                "option_symbol": "ABBV240315C00170000",
                "underlying_ticker": "ABBV",
                "timeframe": "day",
                "bar_timestamp": "2024-03-13T00:00:00Z",
                "open": 4.0, "high": 5.0, "low": 3.5, "close": 4.5,
                "volume": 1500, "trade_count": 200,
            }
        ]

        result = fetch_and_cache_option_bars(
            option_db, "ABBV240315C00170000", "2024-03-10", "2024-03-15", "key", "secret",
        )
        assert len(result) == 1
        mock_fetch.assert_called_once()

        # Verify it was cached
        rows = option_db.execute("SELECT * FROM option_price_cache").fetchall()
        assert len(rows) == 1

    @patch("finance_agent.patterns.option_data._fetch_option_bars_from_alpaca")
    def test_returns_empty_on_no_data(self, mock_fetch, option_db):
        mock_fetch.return_value = []
        result = fetch_and_cache_option_bars(
            option_db, "NODATA240315C00999000", "2024-03-10", "2024-03-15", "key", "secret",
        )
        assert result == []


# ---------------------------------------------------------------------------
# select_option_contract (mocked bars)
# ---------------------------------------------------------------------------


class TestSelectOptionContract:
    @patch("finance_agent.patterns.option_data.fetch_and_cache_option_bars")
    def test_real_pricing_found(self, mock_fetch, option_db):
        mock_fetch.return_value = [
            {
                "option_symbol": "ABBV240315C00170000",
                "underlying_ticker": "ABBV",
                "timeframe": "day",
                "bar_timestamp": "2024-03-13T00:00:00Z",
                "open": 4.0, "high": 5.0, "low": 3.5, "close": 4.5,
                "volume": 1500, "trade_count": 200,
            },
            {
                "option_symbol": "ABBV240315C00170000",
                "underlying_ticker": "ABBV",
                "timeframe": "day",
                "bar_timestamp": "2024-04-01T00:00:00Z",
                "open": 2.0, "high": 2.5, "low": 1.8, "close": 2.1,
                "volume": 800, "trade_count": 100,
            },
        ]

        result = select_option_contract(
            conn=option_db,
            underlying_ticker="ABBV",
            underlying_price=170.0,
            entry_date=date(2024, 3, 13),
            exit_date=date(2024, 4, 1),
            strike_strategy="atm",
            custom_strike_offset_pct=None,
            expiration_days=30,
            option_type="call",
            api_key="key",
            secret_key="secret",
        )
        assert result["pricing"] == "real"
        assert result["entry_premium"] == 4.5
        assert result["exit_premium"] == 2.1
        assert result["volume_at_entry"] == 1500
        assert result["option_symbol"] is not None

    @patch("finance_agent.patterns.option_data.fetch_and_cache_option_bars")
    def test_fallback_when_no_data(self, mock_fetch, option_db):
        mock_fetch.return_value = []

        result = select_option_contract(
            conn=option_db,
            underlying_ticker="NODATA",
            underlying_price=100.0,
            entry_date=date(2024, 3, 13),
            exit_date=date(2024, 4, 1),
            strike_strategy="atm",
            custom_strike_offset_pct=None,
            expiration_days=30,
            option_type="call",
            api_key="key",
            secret_key="secret",
        )
        assert result["pricing"] == "estimated"
        assert result["option_symbol"] is None
        assert result["entry_premium"] is None

    @patch("finance_agent.patterns.option_data.fetch_and_cache_option_bars")
    def test_tries_alternate_strikes(self, mock_fetch, option_db):
        """If primary strike has no data, tries ±1 increment."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return []  # Primary strike: no data
            # First alternate strike: has data
            return [
                {
                    "option_symbol": "ABBV240315C00175000",
                    "underlying_ticker": "ABBV",
                    "timeframe": "day",
                    "bar_timestamp": "2024-03-13T00:00:00Z",
                    "open": 2.0, "high": 3.0, "low": 1.5, "close": 2.5,
                    "volume": 500, "trade_count": 50,
                },
            ]

        mock_fetch.side_effect = side_effect

        result = select_option_contract(
            conn=option_db,
            underlying_ticker="ABBV",
            underlying_price=170.0,
            entry_date=date(2024, 3, 13),
            exit_date=date(2024, 4, 1),
            strike_strategy="atm",
            custom_strike_offset_pct=None,
            expiration_days=30,
            option_type="call",
            api_key="key",
            secret_key="secret",
        )
        # Should have found data at alternate strike
        assert call_count >= 2
        # Pricing depends on whether entry AND exit premiums are available
        # With only one bar, exit_premium uses the same bar (nearest)
        assert result["entry_premium"] == 2.5
