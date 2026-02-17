"""Integration tests for decision engine (live Alpaca API)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from finance_agent.db import get_connection, run_migrations

# Skip all tests if Alpaca keys are not set
pytestmark = pytest.mark.skipif(
    not os.environ.get("ALPACA_PAPER_API_KEY"),
    reason="ALPACA_PAPER_API_KEY not set",
)


@pytest.fixture
def integration_db(tmp_path: Path) -> sqlite3.Connection:
    """Temp DB with all migrations for integration tests."""
    db_path = str(tmp_path / "integration_engine.db")
    conn = get_connection(db_path)
    migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
    run_migrations(conn, migrations_dir)
    yield conn
    conn.close()


@pytest.fixture
def trading_client():  # type: ignore[no-untyped-def]
    """Create a real Alpaca TradingClient from env vars."""
    from finance_agent.engine.account import create_trading_client

    return create_trading_client(
        api_key=os.environ["ALPACA_PAPER_API_KEY"],
        secret_key=os.environ["ALPACA_PAPER_SECRET_KEY"],
        paper=True,
    )


# ---------------------------------------------------------------------------
# T019: Account data integration tests
# ---------------------------------------------------------------------------


class TestAccountIntegration:
    """Test fetching real account data from Alpaca."""

    def test_get_account_summary(self, trading_client) -> None:  # type: ignore[no-untyped-def]
        from finance_agent.engine.account import get_account_summary

        summary = get_account_summary(trading_client)
        assert "equity" in summary
        assert "buying_power" in summary
        assert "cash" in summary
        assert "last_equity" in summary
        assert isinstance(summary["equity"], float)
        assert summary["equity"] >= 0

    def test_get_positions(self, trading_client) -> None:  # type: ignore[no-untyped-def]
        from finance_agent.engine.account import get_positions

        positions = get_positions(trading_client)
        assert isinstance(positions, list)
        # Each position should have required keys
        for pos in positions:
            assert "symbol" in pos
            assert "qty" in pos
            assert "market_value" in pos

    def test_get_daily_orders(self, trading_client) -> None:  # type: ignore[no-untyped-def]
        from finance_agent.engine.account import get_daily_orders

        count = get_daily_orders(trading_client)
        assert isinstance(count, int)
        assert count >= 0

    def test_get_daily_pnl(self, trading_client) -> None:  # type: ignore[no-untyped-def]
        from finance_agent.engine.account import get_daily_pnl

        pnl = get_daily_pnl(trading_client)
        assert "total_change" in pnl
        assert "unrealized" in pnl
        assert "realized_estimate" in pnl
        assert isinstance(pnl["total_change"], float)


class TestKillSwitchIntegration:
    """Test kill switch persistence with real DB."""

    def test_kill_switch_persists_across_connections(
        self, integration_db: sqlite3.Connection, tmp_path: Path,
    ) -> None:
        from finance_agent.engine.state import get_kill_switch, set_kill_switch

        # Activate
        set_kill_switch(integration_db, True)
        assert get_kill_switch(integration_db) is True

        # Close and reopen
        db_path = str(tmp_path / "integration_engine.db")
        integration_db.close()
        conn2 = get_connection(db_path)
        assert get_kill_switch(conn2) is True

        # Deactivate
        set_kill_switch(conn2, False)
        assert get_kill_switch(conn2) is False
        conn2.close()
