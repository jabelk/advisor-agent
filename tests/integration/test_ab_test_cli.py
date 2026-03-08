"""Integration tests for A/B test, multi-ticker, and export CLI flows."""

import json
import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

from finance_agent.db import run_migrations

# Minimal valid rule_set_json for inserting test patterns.
_RULE_SET_JSON = json.dumps({
    "trigger_type": "qualitative",
    "trigger_conditions": [
        {"field": "price_change_pct", "operator": "gte", "value": "5.0", "description": "5% spike"},
        {"field": "volume_spike", "operator": "gte", "value": "1.5", "description": "1.5x volume"},
    ],
    "entry_signal": {"condition": "pullback_pct", "value": "2.0", "window_days": 2, "description": "2% dip"},
    "action": {"action_type": "buy_call", "strike_strategy": "atm", "expiration_days": 30, "description": "ATM call"},
    "exit_criteria": {"profit_target_pct": 20.0, "stop_loss_pct": 10.0, "description": "20/10"},
})

MIGRATIONS_DIR = str(Path(__file__).resolve().parent.parent.parent / "migrations")


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database with schema."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    run_migrations(conn, MIGRATIONS_DIR)
    conn.close()
    return str(db)


def _cli_env(db_path: str) -> dict[str, str]:
    """Return minimal env vars for running the CLI without real API calls."""
    env = os.environ.copy()
    env.update({
        "DB_PATH": db_path,
        "ALPACA_API_KEY_PAPER": "fake-key",
        "ALPACA_SECRET_KEY_PAPER": "fake-secret",
    })
    return env


def _run_cli(*args: str, db_path: str) -> subprocess.CompletedProcess:
    """Run the finance-agent CLI via subprocess."""
    return subprocess.run(
        ["uv", "run", "finance-agent", *args],
        capture_output=True,
        text=True,
        env=_cli_env(db_path),
    )


class TestABTestCLI:
    """Tests for the pattern ab-test CLI subcommand."""

    def test_ab_test_requires_two_patterns(self, db_path):
        """Providing fewer than 2 pattern IDs results in an error."""
        result = _run_cli(
            "pattern", "ab-test", "1", "--tickers", "ABBV",
            db_path=db_path,
        )
        assert result.returncode != 0
        assert "at least 2 pattern IDs" in result.stdout or "at least 2 pattern IDs" in result.stderr

    def test_ab_test_requires_tickers(self, db_path):
        """Calling ab-test without --tickers fails via argparse."""
        result = _run_cli(
            "pattern", "ab-test", "1", "2",
            db_path=db_path,
        )
        assert result.returncode != 0
        assert "--tickers" in result.stderr


class TestExportCLI:
    """Tests for the pattern export CLI subcommand."""

    def test_export_no_results(self, db_path):
        """Exporting a pattern with no backtest results shows an error."""
        # Insert a pattern but do NOT run a backtest.
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO trading_pattern (name, description, rule_set_json, status) VALUES (?, ?, ?, ?)",
            ("Test Pattern", "test desc", _RULE_SET_JSON, "backtested"),
        )
        conn.commit()
        conn.close()

        result = _run_cli(
            "pattern", "export", "1",
            db_path=db_path,
        )
        assert result.returncode != 0
        assert "No backtest results found" in result.stdout or "No backtest results found" in result.stderr

    def test_export_unsupported_format(self, db_path):
        """Requesting an unsupported export format shows an error."""
        result = _run_cli(
            "pattern", "export", "1", "--format", "pdf",
            db_path=db_path,
        )
        assert result.returncode != 0
        assert "Unsupported format" in result.stdout or "Unsupported format" in result.stderr

    def test_export_pattern_not_found(self, db_path):
        """Exporting a non-existent pattern shows a not-found error."""
        result = _run_cli(
            "pattern", "export", "9999",
            db_path=db_path,
        )
        assert result.returncode != 0
        assert "not found" in result.stdout or "not found" in result.stderr
