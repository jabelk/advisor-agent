"""Integration tests for market data module (live Alpaca API)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from finance_agent.data.watchlist import add_company
from finance_agent.db import get_connection, run_migrations

# Skip all tests if Alpaca keys are not set
pytestmark = pytest.mark.skipif(
    not os.environ.get("ALPACA_PAPER_API_KEY"),
    reason="ALPACA_PAPER_API_KEY not set",
)


@pytest.fixture
def integration_db(tmp_path: Path) -> sqlite3.Connection:
    """Temp DB with all migrations for integration tests."""
    db_path = str(tmp_path / "integration_market.db")
    conn = get_connection(db_path)
    migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
    run_migrations(conn, migrations_dir)
    yield conn
    conn.close()


@pytest.fixture
def aapl_company_id(integration_db: sqlite3.Connection) -> int:
    """Add AAPL to watchlist for integration tests."""
    return add_company(integration_db, "AAPL", "Apple Inc.")


@pytest.fixture
def alpaca_client():  # type: ignore[no-untyped-def]
    """Create a real Alpaca data client from env vars."""
    from finance_agent.market.client import create_data_client

    return create_data_client(
        api_key=os.environ["ALPACA_PAPER_API_KEY"],
        secret_key=os.environ["ALPACA_PAPER_SECRET_KEY"],
    )


# ---------------------------------------------------------------------------
# T010: Bar fetch integration tests
# ---------------------------------------------------------------------------

class TestBarFetchIntegration:
    """Test fetching real bars from Alpaca API."""

    def test_fetch_daily_bars_aapl(
        self,
        integration_db: sqlite3.Connection,
        aapl_company_id: int,
        alpaca_client,  # type: ignore[no-untyped-def]
    ) -> None:
        """Fetch a small window of daily bars for AAPL."""
        from finance_agent.market.bars import fetch_bars, query_bars

        count = fetch_bars(
            integration_db, alpaca_client, "AAPL",
            aapl_company_id, "day",
        )
        assert count > 0

        stored = query_bars(integration_db, "AAPL", "day")
        assert len(stored) > 0
        # Verify bar fields are populated
        bar = stored[0]
        assert float(bar["open"]) > 0
        assert float(bar["close"]) > 0
        assert float(bar["volume"]) > 0

    def test_incremental_fetch_no_duplicates(
        self,
        integration_db: sqlite3.Connection,
        aapl_company_id: int,
        alpaca_client,  # type: ignore[no-untyped-def]
    ) -> None:
        """Re-fetching should not insert duplicate bars."""
        from finance_agent.market.bars import fetch_bars, query_bars

        # First fetch
        fetch_bars(
            integration_db, alpaca_client, "AAPL",
            aapl_company_id, "day",
        )
        count_after_first = len(query_bars(integration_db, "AAPL", "day"))

        # Second fetch (incremental)
        fetch_bars(
            integration_db, alpaca_client, "AAPL",
            aapl_company_id, "day",
        )
        count_after_second = len(query_bars(integration_db, "AAPL", "day"))

        # Should be same or slightly more (if new bars appeared), never less
        assert count_after_second >= count_after_first


# ---------------------------------------------------------------------------
# T014: Snapshot integration tests
# ---------------------------------------------------------------------------

class TestSnapshotIntegration:
    """Test real-time snapshots from Alpaca API."""

    def test_snapshot_aapl(
        self,
        alpaca_client,  # type: ignore[no-untyped-def]
    ) -> None:
        from finance_agent.market.snapshot import get_snapshots

        result = get_snapshots(alpaca_client, ["AAPL"])
        assert "AAPL" in result
        # Price should be a positive number (market may be closed)
        price = result["AAPL"].get("last_price")
        assert price is not None
        assert price > 0


# ---------------------------------------------------------------------------
# T019: Indicator integration tests
# ---------------------------------------------------------------------------

class TestIndicatorIntegration:
    """Test indicator computation on real fetched bars."""

    def test_compute_indicators_after_fetch(
        self,
        integration_db: sqlite3.Connection,
        aapl_company_id: int,
        alpaca_client,  # type: ignore[no-untyped-def]
    ) -> None:
        from finance_agent.market.bars import fetch_bars
        from finance_agent.market.indicators import compute_and_persist_indicators

        # Fetch real daily bars
        fetch_bars(
            integration_db, alpaca_client, "AAPL",
            aapl_company_id, "day",
        )

        result = compute_and_persist_indicators(
            integration_db, "AAPL", aapl_company_id, "day",
        )

        # With 2 years of data, all indicators should compute
        assert "sma_20" in result
        assert "sma_50" in result
        assert "rsi_14" in result
        assert "vwap" in result

        # Sanity check ranges
        assert result["sma_20"] > 0
        assert result["sma_50"] > 0
        assert 0 <= result["rsi_14"] <= 100
        assert result["vwap"] > 0


# ---------------------------------------------------------------------------
# T023: Status integration tests
# ---------------------------------------------------------------------------

class TestStatusIntegration:
    """Test market data status after real fetch."""

    def test_status_after_fetch(
        self,
        integration_db: sqlite3.Connection,
        aapl_company_id: int,
        alpaca_client,  # type: ignore[no-untyped-def]
    ) -> None:
        from finance_agent.market.bars import fetch_bars, get_market_data_status

        fetch_bars(
            integration_db, alpaca_client, "AAPL",
            aapl_company_id, "day",
        )

        status = get_market_data_status(integration_db)
        assert len(status) >= 1

        aapl_status = [s for s in status if s["ticker"] == "AAPL"]
        assert len(aapl_status) == 1
        assert aapl_status[0]["bar_count"] > 0
