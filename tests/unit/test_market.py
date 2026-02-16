"""Unit tests for the market data module (mocked Alpaca client)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from finance_agent.data.watchlist import add_company
from finance_agent.db import get_connection, get_schema_version, run_migrations
from finance_agent.market.bars import fetch_bars, get_latest_bar_timestamp, query_bars
from finance_agent.market.client import RateLimiter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def market_db(tmp_path: Path) -> sqlite3.Connection:
    """In-memory-like temp DB with all migrations applied (including 003)."""
    db_path = str(tmp_path / "market_test.db")
    conn = get_connection(db_path)
    migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
    run_migrations(conn, migrations_dir)
    yield conn
    conn.close()


@pytest.fixture
def sample_company_id(market_db: sqlite3.Connection) -> int:
    """Add AAPL to watchlist and return company_id."""
    return add_company(market_db, "AAPL", "Apple Inc.", cik="0000320193")


@pytest.fixture
def mock_alpaca_client() -> MagicMock:
    """Provide a mocked StockHistoricalDataClient."""
    return MagicMock()


# ---------------------------------------------------------------------------
# T006: Migration verification
# ---------------------------------------------------------------------------

class TestMigration:
    """Verify 003_market_data.sql applies cleanly."""

    def test_schema_version_is_3(self, market_db: sqlite3.Connection) -> None:
        version = get_schema_version(market_db)
        assert version == 3

    def test_price_bar_table_exists(self, market_db: sqlite3.Connection) -> None:
        row = market_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='price_bar'"
        ).fetchone()
        assert row is not None

    def test_technical_indicator_table_exists(self, market_db: sqlite3.Connection) -> None:
        row = market_db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='technical_indicator'"
        ).fetchone()
        assert row is not None

    def test_market_data_fetch_table_exists(self, market_db: sqlite3.Connection) -> None:
        row = market_db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='market_data_fetch'"
        ).fetchone()
        assert row is not None

    def test_price_bar_indexes_exist(self, market_db: sqlite3.Connection) -> None:
        indexes = market_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND tbl_name='price_bar' AND name LIKE 'idx_%'"
        ).fetchall()
        names = {row["name"] for row in indexes}
        assert "idx_price_bar_ticker_tf_ts" in names
        assert "idx_price_bar_company" in names

    def test_fetch_index_exists(self, market_db: sqlite3.Connection) -> None:
        row = market_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name='idx_fetch_ticker_tf'"
        ).fetchone()
        assert row is not None


# ---------------------------------------------------------------------------
# Helpers: mock Alpaca bar objects
# ---------------------------------------------------------------------------

def _make_mock_bar(
    ts: str, o: float, h: float, lo: float, c: float,
    v: float, tc: float = 100, vwap: float | None = None,
) -> MagicMock:
    """Create a mock Bar object matching Alpaca SDK shape."""
    bar = MagicMock()
    bar.timestamp = datetime.fromisoformat(ts)
    bar.open = o
    bar.high = h
    bar.low = lo
    bar.close = c
    bar.volume = v
    bar.trade_count = tc
    bar.vwap = vwap or (h + lo + c) / 3
    return bar


def _make_bars_response(ticker: str, bars: list[MagicMock]) -> MagicMock:
    """Wrap mock bars in a response object."""
    response = MagicMock()
    response.data = {ticker: bars}
    return response


# ---------------------------------------------------------------------------
# T009: Bar fetch unit tests
# ---------------------------------------------------------------------------

class TestBarFetch:
    """Test bar fetch, storage, and incremental logic."""

    def test_fetch_bars_inserts_new_bars(
        self,
        market_db: sqlite3.Connection,
        sample_company_id: int,
        mock_alpaca_client: MagicMock,
    ) -> None:
        bars = [
            _make_mock_bar("2026-02-10T00:00:00+00:00", 230, 235, 228, 233, 50000),
            _make_mock_bar("2026-02-11T00:00:00+00:00", 233, 237, 231, 236, 55000),
            _make_mock_bar("2026-02-12T00:00:00+00:00", 236, 240, 234, 238, 48000),
        ]
        mock_alpaca_client.get_stock_bars.return_value = _make_bars_response(
            "AAPL", bars,
        )
        count = fetch_bars(
            market_db, mock_alpaca_client, "AAPL", sample_company_id, "day",
        )
        assert count == 3
        stored = query_bars(market_db, "AAPL", "day")
        assert len(stored) == 3

    def test_insert_or_ignore_dedup(
        self,
        market_db: sqlite3.Connection,
        sample_company_id: int,
        mock_alpaca_client: MagicMock,
    ) -> None:
        bars = [
            _make_mock_bar("2026-02-10T00:00:00+00:00", 230, 235, 228, 233, 50000),
        ]
        mock_alpaca_client.get_stock_bars.return_value = _make_bars_response(
            "AAPL", bars,
        )
        # First fetch
        fetch_bars(
            market_db, mock_alpaca_client, "AAPL", sample_company_id, "day",
        )
        # Second fetch — same bar should be ignored
        count = fetch_bars(
            market_db, mock_alpaca_client, "AAPL", sample_company_id, "day",
        )
        assert count == 0
        stored = query_bars(market_db, "AAPL", "day")
        assert len(stored) == 1

    def test_incremental_start_date(
        self,
        market_db: sqlite3.Connection,
        sample_company_id: int,
    ) -> None:
        # Insert a bar directly
        market_db.execute(
            "INSERT INTO price_bar "
            "(company_id, ticker, timeframe, bar_timestamp, "
            "open, high, low, close, volume) "
            "VALUES (?, 'AAPL', 'day', '2026-02-10T00:00:00+00:00', "
            "230, 235, 228, 233, 50000)",
            (sample_company_id,),
        )
        market_db.commit()
        latest = get_latest_bar_timestamp(market_db, "AAPL", "day")
        assert latest == "2026-02-10T00:00:00+00:00"

    def test_fetch_bars_api_error_raises(
        self,
        market_db: sqlite3.Connection,
        sample_company_id: int,
        mock_alpaca_client: MagicMock,
    ) -> None:
        mock_alpaca_client.get_stock_bars.side_effect = RuntimeError("API down")
        with pytest.raises(RuntimeError, match="API down"):
            fetch_bars(
                market_db, mock_alpaca_client, "AAPL",
                sample_company_id, "day",
            )

    def test_fetch_bars_empty_response(
        self,
        market_db: sqlite3.Connection,
        sample_company_id: int,
        mock_alpaca_client: MagicMock,
    ) -> None:
        response = MagicMock()
        response.data = {"AAPL": []}
        mock_alpaca_client.get_stock_bars.return_value = response
        count = fetch_bars(
            market_db, mock_alpaca_client, "AAPL", sample_company_id, "day",
        )
        assert count == 0

    def test_query_bars_date_range(
        self,
        market_db: sqlite3.Connection,
        sample_company_id: int,
    ) -> None:
        for day in range(10, 15):
            market_db.execute(
                "INSERT INTO price_bar "
                "(company_id, ticker, timeframe, bar_timestamp, "
                "open, high, low, close, volume) "
                "VALUES (?, 'AAPL', 'day', ?, 230, 235, 228, 233, 50000)",
                (sample_company_id, f"2026-02-{day}T00:00:00+00:00"),
            )
        market_db.commit()
        bars = query_bars(
            market_db, "AAPL", "day",
            start="2026-02-11T00:00:00+00:00",
            end="2026-02-13T00:00:00+00:00",
        )
        assert len(bars) == 3


# ---------------------------------------------------------------------------
# Rate limiter tests
# ---------------------------------------------------------------------------

class TestRateLimiter:
    """Test token-bucket rate limiter."""

    def test_remaining_decreases(self) -> None:
        rl = RateLimiter(max_requests=5, window=60.0)
        assert rl.remaining == 5
        rl.acquire()
        assert rl.remaining == 4


# ---------------------------------------------------------------------------
# T013: Snapshot unit tests
# ---------------------------------------------------------------------------

class TestSnapshot:
    """Test snapshot query logic with mocked Alpaca client."""

    def test_get_snapshots_returns_prices(
        self, mock_alpaca_client: MagicMock,
    ) -> None:
        from finance_agent.market.snapshot import get_snapshots

        # Build mock snapshot
        snap = MagicMock()
        snap.latest_trade.price = 234.56
        snap.latest_quote.bid_price = 234.55
        snap.latest_quote.bid_size = 200
        snap.latest_quote.ask_price = 234.57
        snap.latest_quote.ask_size = 100
        snap.daily_bar.volume = 45_200_000
        snap.daily_bar.vwap = 233.80

        mock_alpaca_client.get_stock_snapshot.return_value = {"AAPL": snap}

        result = get_snapshots(mock_alpaca_client, ["AAPL"])
        assert "AAPL" in result
        assert result["AAPL"]["last_price"] == 234.56
        assert result["AAPL"]["bid_price"] == 234.55
        assert result["AAPL"]["ask_price"] == 234.57
        assert result["AAPL"]["volume"] == 45_200_000

    def test_get_snapshots_api_error(
        self, mock_alpaca_client: MagicMock,
    ) -> None:
        from finance_agent.market.snapshot import get_snapshots

        mock_alpaca_client.get_stock_snapshot.side_effect = RuntimeError(
            "API error",
        )
        with pytest.raises(RuntimeError, match="API error"):
            get_snapshots(mock_alpaca_client, ["INVALID"])


# ---------------------------------------------------------------------------
# T018: Indicator computation unit tests
# ---------------------------------------------------------------------------

class TestIndicators:
    """Test SMA, RSI, VWAP computation and persistence."""

    def test_compute_sma_known_values(self) -> None:
        from finance_agent.market.indicators import compute_sma

        # SMA-5 of [10, 20, 30, 40, 50] = 30
        assert compute_sma([10, 20, 30, 40, 50], 5) == 30.0
        # SMA-3 of [1, 2, 3, 4, 5] = (3+4+5)/3 = 4
        assert compute_sma([1, 2, 3, 4, 5], 3) == 4.0

    def test_compute_sma_insufficient_data(self) -> None:
        from finance_agent.market.indicators import compute_sma

        assert compute_sma([10, 20], 5) is None
        assert compute_sma([], 1) is None

    def test_compute_rsi_known_values(self) -> None:
        from finance_agent.market.indicators import compute_rsi

        # Create prices that go up then down
        # 15 prices (need period + 1 = 15 for period=14)
        prices = [
            44, 44.34, 44.09, 43.61, 44.33,
            44.83, 45.10, 45.42, 45.84, 46.08,
            45.89, 46.03, 45.61, 46.28, 46.28,
        ]
        rsi = compute_rsi(prices, 14)
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_compute_rsi_insufficient_data(self) -> None:
        from finance_agent.market.indicators import compute_rsi

        assert compute_rsi([10, 20, 30], 14) is None

    def test_compute_rsi_all_gains(self) -> None:
        from finance_agent.market.indicators import compute_rsi

        # Monotonically increasing → RSI should be 100
        prices = list(range(1, 20))
        rsi = compute_rsi(prices, 14)
        assert rsi is not None
        assert rsi == 100.0

    def test_compute_vwap(self) -> None:
        from finance_agent.market.indicators import compute_vwap

        bars = [
            {"high": 105.0, "low": 95.0, "close": 100.0, "volume": 1000},
            {"high": 110.0, "low": 100.0, "close": 105.0, "volume": 2000},
        ]
        vwap = compute_vwap(bars)
        assert vwap is not None
        # TP1 = (105+95+100)/3 = 100, TP2 = (110+100+105)/3 = 105
        # VWAP = (100*1000 + 105*2000) / 3000 = 310000/3000 = 103.333
        assert abs(vwap - 103.333) < 0.01

    def test_compute_vwap_empty(self) -> None:
        from finance_agent.market.indicators import compute_vwap

        assert compute_vwap([]) is None

    def test_persist_and_upsert_indicators(
        self,
        market_db: sqlite3.Connection,
        sample_company_id: int,
    ) -> None:
        from finance_agent.market.indicators import compute_and_persist_indicators

        # Insert 60 daily bars to enable SMA-20, SMA-50, RSI-14
        for i in range(60):
            day = f"2026-01-{(i % 28) + 1:02d}T00:00:00+00:00"
            if i >= 28:
                day = f"2026-02-{(i - 28) + 1:02d}T00:00:00+00:00"
            market_db.execute(
                "INSERT OR IGNORE INTO price_bar "
                "(company_id, ticker, timeframe, bar_timestamp, "
                "open, high, low, close, volume) "
                "VALUES (?, 'AAPL', 'day', ?, ?, ?, ?, ?, ?)",
                (
                    sample_company_id, day,
                    100 + i, 105 + i, 95 + i, 100 + i + 1,
                    50000 + i * 100,
                ),
            )
        market_db.commit()

        result = compute_and_persist_indicators(
            market_db, "AAPL", sample_company_id, "day",
        )
        assert "sma_20" in result
        assert "sma_50" in result
        assert "rsi_14" in result
        assert "vwap" in result

        # Verify persisted in DB
        rows = market_db.execute(
            "SELECT indicator_type, value FROM technical_indicator "
            "WHERE ticker = 'AAPL'"
        ).fetchall()
        types = {row["indicator_type"] for row in rows}
        assert {"sma_20", "sma_50", "rsi_14", "vwap"} == types

        # Upsert: run again, should update not duplicate
        result2 = compute_and_persist_indicators(
            market_db, "AAPL", sample_company_id, "day",
        )
        assert result2["sma_20"] == result["sma_20"]
        count = market_db.execute(
            "SELECT COUNT(*) as cnt FROM technical_indicator "
            "WHERE ticker = 'AAPL'"
        ).fetchone()["cnt"]
        assert count == 4  # Not 8

    def test_skip_insufficient_bars(
        self,
        market_db: sqlite3.Connection,
        sample_company_id: int,
    ) -> None:
        from finance_agent.market.indicators import compute_and_persist_indicators

        # Insert only 10 bars (not enough for SMA-20 or SMA-50)
        for i in range(10):
            market_db.execute(
                "INSERT INTO price_bar "
                "(company_id, ticker, timeframe, bar_timestamp, "
                "open, high, low, close, volume) "
                "VALUES (?, 'AAPL', 'day', ?, 100, 105, 95, 101, 50000)",
                (sample_company_id, f"2026-02-{i + 1:02d}T00:00:00+00:00"),
            )
        market_db.commit()

        result = compute_and_persist_indicators(
            market_db, "AAPL", sample_company_id, "day",
        )
        # SMA-20 and SMA-50 should be missing, but VWAP and possibly RSI
        assert "sma_20" not in result
        assert "sma_50" not in result
        assert "vwap" in result


# ---------------------------------------------------------------------------
# T022: Market data status unit tests
# ---------------------------------------------------------------------------

class TestMarketDataStatus:
    """Test market data status queries."""

    def test_status_with_data(
        self,
        market_db: sqlite3.Connection,
        sample_company_id: int,
    ) -> None:
        from finance_agent.market.bars import get_market_data_status

        # Insert some bars
        for i in range(5):
            market_db.execute(
                "INSERT INTO price_bar "
                "(company_id, ticker, timeframe, bar_timestamp, "
                "open, high, low, close, volume) "
                "VALUES (?, 'AAPL', 'day', ?, 100, 105, 95, 101, 50000)",
                (sample_company_id, f"2026-02-{i + 10:02d}T00:00:00+00:00"),
            )
        market_db.commit()

        status = get_market_data_status(market_db)
        assert len(status) == 1
        assert status[0]["ticker"] == "AAPL"
        assert status[0]["timeframe"] == "day"
        assert status[0]["bar_count"] == 5
        assert status[0]["from_date"] is not None
        assert status[0]["to_date"] is not None

    def test_status_empty_db(
        self,
        market_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.market.bars import get_market_data_status

        status = get_market_data_status(market_db)
        assert status == []

    def test_latest_indicators(
        self,
        market_db: sqlite3.Connection,
        sample_company_id: int,
    ) -> None:
        from finance_agent.market.bars import get_latest_indicators

        # Insert an indicator
        market_db.execute(
            "INSERT INTO technical_indicator "
            "(company_id, ticker, indicator_type, timeframe, "
            "value, bar_date) "
            "VALUES (?, 'AAPL', 'sma_20', 'day', 234.50, '2026-02-14')",
            (sample_company_id,),
        )
        market_db.commit()

        indicators = get_latest_indicators(market_db)
        assert len(indicators) == 1
        assert indicators[0]["ticker"] == "AAPL"
        assert indicators[0]["indicator_type"] == "sma_20"
        assert float(indicators[0]["value"]) == 234.50
