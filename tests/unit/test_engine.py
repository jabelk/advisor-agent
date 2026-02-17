"""Unit tests for the decision engine module."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from finance_agent.db import get_connection, get_schema_version, run_migrations

MIGRATIONS_DIR = str(Path(__file__).resolve().parent.parent.parent / "migrations")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine_db(tmp_path: Path) -> sqlite3.Connection:
    """In-memory SQLite with all migrations applied through 004."""
    db_path = str(tmp_path / "engine_test.db")
    conn = get_connection(db_path)
    run_migrations(conn, MIGRATIONS_DIR)
    yield conn
    conn.close()


@pytest.fixture
def mock_trading_client() -> MagicMock:
    """Mock Alpaca TradingClient with standard account/position responses."""
    client = MagicMock()

    # Mock account
    account = MagicMock()
    account.equity = "1000.00"
    account.buying_power = "500.00"
    account.cash = "500.00"
    account.last_equity = "990.00"
    account.status = "ACTIVE"
    client.get_account.return_value = account

    # Mock positions (empty by default)
    client.get_all_positions.return_value = []

    # Mock orders (empty by default)
    client.get_orders.return_value = []

    return client


@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Mock Anthropic client for LLM adjustment tests."""
    client = MagicMock()
    # Default: return a valid JSON response with +0.05 adjustment
    response = MagicMock()
    content_block = MagicMock()
    content_block.text = json.dumps({
        "adjustment": 0.05,
        "rationale": "Signals align with bullish technical momentum.",
    })
    response.content = [content_block]
    client.messages.create.return_value = response
    return client


@pytest.fixture
def sample_company_id(engine_db: sqlite3.Connection) -> int:
    """Add NVDA to watchlist and return company_id."""
    from finance_agent.data.watchlist import add_company

    return add_company(engine_db, "NVDA", "NVIDIA Corporation", "0001045810", "Technology")


# ---------------------------------------------------------------------------
# T007: Migration verification
# ---------------------------------------------------------------------------


class TestMigration004:
    """Verify migration 004 applies cleanly and creates expected schema."""

    def test_migration_applies_to_version_4(self, engine_db: sqlite3.Connection) -> None:
        assert get_schema_version(engine_db) == 4

    def test_trade_proposal_table_exists(self, engine_db: sqlite3.Connection) -> None:
        tables = engine_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='trade_proposal'"
        ).fetchall()
        assert len(tables) == 1

    def test_proposal_source_table_exists(self, engine_db: sqlite3.Connection) -> None:
        tables = engine_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='proposal_source'"
        ).fetchall()
        assert len(tables) == 1

    def test_risk_check_result_table_exists(self, engine_db: sqlite3.Connection) -> None:
        tables = engine_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='risk_check_result'"
        ).fetchall()
        assert len(tables) == 1

    def test_engine_state_table_exists(self, engine_db: sqlite3.Connection) -> None:
        tables = engine_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='engine_state'"
        ).fetchall()
        assert len(tables) == 1

    def test_indexes_exist(self, engine_db: sqlite3.Connection) -> None:
        indexes = engine_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name LIKE 'idx_proposal%' OR name LIKE 'idx_risk%'"
        ).fetchall()
        index_names = {row["name"] for row in indexes}
        expected = {
            "idx_proposal_status",
            "idx_proposal_ticker",
            "idx_proposal_created",
            "idx_proposal_source_unique",
            "idx_proposal_source_proposal",
            "idx_risk_check_proposal",
        }
        assert expected.issubset(index_names)

    def test_default_kill_switch_row(self, engine_db: sqlite3.Connection) -> None:
        row = engine_db.execute(
            "SELECT value FROM engine_state WHERE key = 'kill_switch'"
        ).fetchone()
        assert row is not None
        state = json.loads(row["value"])
        assert state["active"] is False

    def test_default_risk_settings_row(self, engine_db: sqlite3.Connection) -> None:
        row = engine_db.execute(
            "SELECT value FROM engine_state WHERE key = 'risk_settings'"
        ).fetchone()
        assert row is not None
        settings = json.loads(row["value"])
        assert settings["max_position_pct"] == 0.10
        assert settings["max_daily_loss_pct"] == 0.05
        assert settings["max_trades_per_day"] == 20
        assert settings["max_positions_per_symbol"] == 2
        assert settings["min_confidence_threshold"] == 0.45


# ---------------------------------------------------------------------------
# T017: Scoring unit tests
# ---------------------------------------------------------------------------


class TestSignalScoring:
    """Test signal scoring functions."""

    def test_classify_bullish_sentiment(self) -> None:
        from finance_agent.engine.scoring import classify_signal_direction

        signal = {"signal_type": "sentiment", "summary": "Bullish outlook on growth"}
        assert classify_signal_direction(signal) == 1

    def test_classify_bearish_sentiment(self) -> None:
        from finance_agent.engine.scoring import classify_signal_direction

        signal = {"signal_type": "sentiment", "summary": "Revenue decline expected"}
        assert classify_signal_direction(signal) == -1

    def test_classify_risk_factor_always_bearish(self) -> None:
        from finance_agent.engine.scoring import classify_signal_direction

        signal = {"signal_type": "risk_factor", "summary": "Strong growth potential"}
        assert classify_signal_direction(signal) == -1

    def test_classify_guidance_raised(self) -> None:
        from finance_agent.engine.scoring import classify_signal_direction

        signal = {
            "signal_type": "guidance_change",
            "summary": "Company raised FY26 guidance",
        }
        assert classify_signal_direction(signal) == 1

    def test_classify_guidance_lowered(self) -> None:
        from finance_agent.engine.scoring import classify_signal_direction

        signal = {
            "signal_type": "guidance_change",
            "summary": "Company lowered outlook",
        }
        assert classify_signal_direction(signal) == -1

    def test_classify_neutral(self) -> None:
        from finance_agent.engine.scoring import classify_signal_direction

        signal = {
            "signal_type": "financial_metric",
            "summary": "Revenue was flat quarter over quarter",
        }
        assert classify_signal_direction(signal) == 0

    def test_recency_weight_today(self) -> None:
        from datetime import UTC, datetime

        from finance_agent.engine.scoring import recency_weight

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        weight = recency_weight(now)
        assert weight > 0.95  # Should be very close to 1.0

    def test_recency_weight_7_days(self) -> None:
        from datetime import UTC, datetime, timedelta

        from finance_agent.engine.scoring import recency_weight

        week_ago = (datetime.now(UTC) - timedelta(days=7)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        weight = recency_weight(week_ago)
        assert 0.45 < weight < 0.55  # Should be ~0.5 at half-life

    def test_recency_weight_14_days(self) -> None:
        from datetime import UTC, datetime, timedelta

        from finance_agent.engine.scoring import recency_weight

        two_weeks = (datetime.now(UTC) - timedelta(days=14)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        weight = recency_weight(two_weeks)
        assert 0.2 < weight < 0.3  # Should be ~0.25 at 2x half-life

    def test_compute_signal_score_bullish(self) -> None:
        from datetime import UTC, datetime

        from finance_agent.engine.scoring import compute_signal_score

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        signals = [
            {
                "signal_type": "sentiment",
                "evidence_type": "fact",
                "confidence": "high",
                "summary": "Strong revenue growth beat expectations",
                "created_at": now,
            },
            {
                "signal_type": "guidance_change",
                "evidence_type": "fact",
                "confidence": "high",
                "summary": "Company raised guidance above consensus",
                "created_at": now,
            },
            {
                "signal_type": "financial_metric",
                "evidence_type": "fact",
                "confidence": "medium",
                "summary": "EPS beat by 12%, strong growth",
                "created_at": now,
            },
        ]
        score = compute_signal_score(signals)
        assert score > 0.5  # Should be clearly bullish

    def test_compute_signal_score_empty(self) -> None:
        from finance_agent.engine.scoring import compute_signal_score

        assert compute_signal_score([]) == 0.0

    def test_signal_score_in_range(self) -> None:
        from datetime import UTC, datetime

        from finance_agent.engine.scoring import compute_signal_score

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        signals = [
            {
                "signal_type": "risk_factor",
                "evidence_type": "fact",
                "confidence": "high",
                "summary": "Major regulatory risk",
                "created_at": now,
            },
        ]
        score = compute_signal_score(signals)
        assert -1.0 <= score <= 1.0


class TestIndicatorScoring:
    """Test technical indicator scoring."""

    def test_bullish_indicators(self) -> None:
        from finance_agent.engine.scoring import compute_indicator_score

        # Golden cross, bullish RSI, above VWAP
        score = compute_indicator_score(
            last_close=130.0,
            sma_20=128.0,
            sma_50=125.0,
            rsi_14=58.0,
            vwap=127.0,
        )
        assert score > 0.3

    def test_bearish_indicators(self) -> None:
        from finance_agent.engine.scoring import compute_indicator_score

        # Death cross, bearish RSI, below VWAP
        score = compute_indicator_score(
            last_close=120.0,
            sma_20=125.0,
            sma_50=128.0,
            rsi_14=35.0,
            vwap=125.0,
        )
        assert score < -0.2

    def test_no_indicators(self) -> None:
        from finance_agent.engine.scoring import compute_indicator_score

        score = compute_indicator_score(100.0, None, None, None, None)
        assert score == 0.0

    def test_momentum_score_bullish(self) -> None:
        from finance_agent.engine.scoring import compute_momentum_score

        # Uptrending prices with increasing volume
        bars = []
        for i in range(25):
            bars.append({
                "close": 100 + i * 0.5,
                "volume": 1000000 + i * 50000,
                "high": 101 + i * 0.5,
                "low": 99 + i * 0.5,
            })
        score = compute_momentum_score(bars)
        assert score > 0.1

    def test_momentum_score_insufficient_data(self) -> None:
        from finance_agent.engine.scoring import compute_momentum_score

        bars = [{"close": 100, "volume": 1000, "high": 101, "low": 99}]
        assert compute_momentum_score(bars) == 0.0


class TestLimitPrice:
    """Test ATR computation and limit price derivation."""

    def test_compute_atr(self) -> None:
        from finance_agent.engine.scoring import compute_atr

        bars = []
        for i in range(20):
            bars.append({
                "high": 102 + i * 0.1,
                "low": 98 + i * 0.1,
                "close": 100 + i * 0.1,
            })
        atr = compute_atr(bars, period=14)
        assert atr is not None
        assert atr > 0

    def test_compute_atr_insufficient_data(self) -> None:
        from finance_agent.engine.scoring import compute_atr

        bars = [{"high": 102, "low": 98, "close": 100}]
        assert compute_atr(bars, period=14) is None

    def test_limit_price_buy(self) -> None:
        from finance_agent.engine.scoring import compute_limit_price

        # Buy should be below last close
        price = compute_limit_price("buy", 100.0, 4.0, 0.70)
        assert price < 100.0
        assert price > 95.0  # Not more than 5% below

    def test_limit_price_sell(self) -> None:
        from finance_agent.engine.scoring import compute_limit_price

        # Sell should be above last close
        price = compute_limit_price("sell", 100.0, 4.0, -0.70)
        assert price > 100.0
        assert price < 105.0  # Not more than 5% above

    def test_limit_price_floor(self) -> None:
        from finance_agent.engine.scoring import compute_limit_price

        # With tiny ATR, should still have minimum offset
        price = compute_limit_price("buy", 100.0, 0.01, 1.0)
        assert price < 100.0  # Must be below
        assert price >= 98.0  # Floor: 0.1% of 100 = $0.10

    def test_limit_price_cap(self) -> None:
        from finance_agent.engine.scoring import compute_limit_price

        # With huge ATR, should cap at 2%
        price = compute_limit_price("buy", 100.0, 50.0, 0.45)
        assert price >= 98.0  # Cap: 2% of 100 = $2.00

    def test_limit_price_no_atr(self) -> None:
        from finance_agent.engine.scoring import compute_limit_price

        # Fallback when no ATR available
        price = compute_limit_price("buy", 100.0, None, 0.60)
        assert price < 100.0
        assert price > 97.0


# ---------------------------------------------------------------------------
# T018: Proposal generation unit tests
# ---------------------------------------------------------------------------


class TestProposalGeneration:
    """Test proposal generation logic."""

    def test_should_generate_above_threshold(self) -> None:
        from datetime import UTC, datetime

        from finance_agent.engine.scoring import should_generate_proposal

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        signals = [
            {
                "signal_type": "sentiment",
                "evidence_type": "fact",
                "confidence": "high",
                "summary": "Bullish",
                "created_at": now,
            },
            {
                "signal_type": "guidance_change",
                "evidence_type": "fact",
                "confidence": "high",
                "summary": "Raised guidance",
                "created_at": now,
            },
            {
                "signal_type": "financial_metric",
                "evidence_type": "inference",
                "confidence": "medium",
                "summary": "Strong growth",
                "created_at": now,
            },
        ]
        ok, reason = should_generate_proposal(0.55, signals)
        assert ok is True

    def test_should_not_generate_below_threshold(self) -> None:
        from datetime import UTC, datetime

        from finance_agent.engine.scoring import should_generate_proposal

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        signals = [
            {
                "signal_type": "sentiment",
                "evidence_type": "fact",
                "confidence": "high",
                "summary": "Neutral",
                "created_at": now,
            },
            {
                "signal_type": "guidance_change",
                "evidence_type": "fact",
                "confidence": "high",
                "summary": "OK",
                "created_at": now,
            },
            {
                "signal_type": "financial_metric",
                "evidence_type": "fact",
                "confidence": "medium",
                "summary": "Flat",
                "created_at": now,
            },
        ]
        ok, reason = should_generate_proposal(0.30, signals)
        assert ok is False
        assert "Confidence insufficient" in reason

    def test_should_not_generate_few_signals(self) -> None:
        from datetime import UTC, datetime

        from finance_agent.engine.scoring import should_generate_proposal

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        signals = [
            {
                "signal_type": "sentiment",
                "evidence_type": "fact",
                "confidence": "high",
                "summary": "Bullish",
                "created_at": now,
            },
        ]
        ok, reason = should_generate_proposal(0.60, signals)
        assert ok is False
        assert "Insufficient signals" in reason

    def test_should_not_generate_no_facts(self) -> None:
        from datetime import UTC, datetime

        from finance_agent.engine.scoring import should_generate_proposal

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        signals = [
            {
                "signal_type": "sentiment",
                "evidence_type": "inference",
                "confidence": "high",
                "summary": "Bullish",
                "created_at": now,
            },
            {
                "signal_type": "guidance_change",
                "evidence_type": "inference",
                "confidence": "medium",
                "summary": "Raised",
                "created_at": now,
            },
            {
                "signal_type": "financial_metric",
                "evidence_type": "inference",
                "confidence": "medium",
                "summary": "Growth",
                "created_at": now,
            },
        ]
        ok, reason = should_generate_proposal(0.60, signals)
        assert ok is False
        assert "fact" in reason.lower()

    def test_compute_position_size(self) -> None:
        from finance_agent.engine.proposals import compute_position_size

        # score 0.80 * 10% * $10000 / $127 = 6.3 → floor = 6
        qty = compute_position_size(0.80, 127.0, 10000.0, 0.10)
        assert qty == 6  # noqa: PLR2004

    def test_compute_position_size_minimum(self) -> None:
        from finance_agent.engine.proposals import compute_position_size

        # Very small account → should get at least 1 share
        qty = compute_position_size(0.45, 500.0, 100.0, 0.10)
        assert qty == 1

    def test_compute_position_size_zero_equity(self) -> None:
        from finance_agent.engine.proposals import compute_position_size

        qty = compute_position_size(0.60, 127.0, 0.0, 0.10)
        assert qty == 0

    def test_base_score_composition(self) -> None:
        from finance_agent.engine.scoring import compute_base_score

        # 0.8 * 0.5 + 0.6 * 0.3 + 0.4 * 0.2 = 0.4 + 0.18 + 0.08 = 0.66
        score = compute_base_score(0.8, 0.6, 0.4)
        assert abs(score - 0.66) < 0.01

    def test_llm_graceful_degradation(self) -> None:
        from finance_agent.engine.scoring import get_llm_adjustment

        adj, rationale = get_llm_adjustment(
            None, "NVDA", 0.60, 0.70, 0.50, 0.30, [], {},
        )
        assert adj == 0.0
        assert "No API key" in rationale

    def test_llm_adjustment_clamped(
        self, mock_anthropic_client: MagicMock,
    ) -> None:
        from finance_agent.engine.scoring import get_llm_adjustment

        # Override to return a value exceeding bounds
        content_block = MagicMock()
        content_block.text = json.dumps({
            "adjustment": 0.50,
            "rationale": "Extremely bullish",
        })
        response = MagicMock()
        response.content = [content_block]
        mock_anthropic_client.messages.create.return_value = response

        adj, _ = get_llm_adjustment(
            mock_anthropic_client, "NVDA", 0.60,
            0.70, 0.50, 0.30, [], {},
        )
        assert adj == 0.15  # Clamped to max

    def test_final_score_clamped(self) -> None:
        from finance_agent.engine.scoring import compute_final_score

        assert compute_final_score(0.95, 0.15) == 1.0
        assert compute_final_score(-0.95, -0.15) == -1.0

    def test_generate_proposals_dry_run(
        self,
        engine_db: sqlite3.Connection,
        sample_company_id: int,
    ) -> None:
        """Test dry run doesn't write to DB."""
        from finance_agent.engine.proposals import generate_proposals

        # Insert sample signals
        _insert_sample_signals(engine_db, sample_company_id)
        _insert_sample_bars(engine_db, sample_company_id)
        _insert_sample_indicators(engine_db, sample_company_id)

        account = {
            "equity": 1000.0,
            "buying_power": 500.0,
            "cash": 500.0,
            "last_equity": 990.0,
        }

        proposals = generate_proposals(
            engine_db, None, None,
            account, [],
            ticker="NVDA",
            dry_run=True,
        )

        # Should generate at least a result (either proposal or skip)
        assert len(proposals) >= 1

        # No proposals should be in DB
        count = engine_db.execute(
            "SELECT COUNT(*) as cnt FROM trade_proposal"
        ).fetchone()["cnt"]
        assert count == 0


# ---------------------------------------------------------------------------
# T022: Kill switch unit tests
# ---------------------------------------------------------------------------


class TestKillSwitch:
    """Test kill switch state management."""

    def test_kill_switch_default_off(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.state import get_kill_switch

        assert get_kill_switch(engine_db) is False

    def test_set_kill_switch_on(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.state import get_kill_switch, set_kill_switch

        changed = set_kill_switch(engine_db, True)
        assert changed is True
        assert get_kill_switch(engine_db) is True

    def test_set_kill_switch_off(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.state import get_kill_switch, set_kill_switch

        set_kill_switch(engine_db, True)
        changed = set_kill_switch(engine_db, False)
        assert changed is True
        assert get_kill_switch(engine_db) is False

    def test_set_kill_switch_idempotent(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.state import set_kill_switch

        # Already off by default, setting off again should return False
        changed = set_kill_switch(engine_db, False)
        assert changed is False

    def test_set_kill_switch_with_audit(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.audit.logger import AuditLogger
        from finance_agent.engine.state import set_kill_switch

        audit = AuditLogger(engine_db)
        set_kill_switch(engine_db, True, toggled_by="test", audit=audit)

        events = audit.query(event_type="kill_switch_toggle")
        assert len(events) == 1
        assert events[0]["payload"]["active"] is True
        assert events[0]["payload"]["toggled_by"] == "test"


# ---------------------------------------------------------------------------
# T028: Risk check unit tests
# ---------------------------------------------------------------------------


class TestRiskChecks:
    """Test individual risk check functions."""

    def test_position_size_pass(self) -> None:
        from finance_agent.engine.risk import check_position_size

        proposal = {"estimated_cost": 80.0, "ticker": "NVDA"}
        account = {"equity": 1000.0}
        settings = {"max_position_pct": 0.10}
        result = check_position_size(proposal, account, settings)
        assert result["passed"] is True

    def test_position_size_fail(self) -> None:
        from finance_agent.engine.risk import check_position_size

        proposal = {"estimated_cost": 200.0, "ticker": "NVDA"}
        account = {"equity": 1000.0}
        settings = {"max_position_pct": 0.10}
        result = check_position_size(proposal, account, settings)
        assert result["passed"] is False

    def test_daily_loss_pass(self) -> None:
        from finance_agent.engine.risk import check_daily_loss

        pnl = {"total_change": -20.0}
        account = {"equity": 1000.0}
        settings = {"max_daily_loss_pct": 0.05}
        result = check_daily_loss(pnl, account, settings)
        assert result["passed"] is True

    def test_daily_loss_fail(self) -> None:
        from finance_agent.engine.risk import check_daily_loss

        pnl = {"total_change": -60.0}
        account = {"equity": 1000.0}
        settings = {"max_daily_loss_pct": 0.05}
        result = check_daily_loss(pnl, account, settings)
        assert result["passed"] is False

    def test_trade_count_pass(self) -> None:
        from finance_agent.engine.risk import check_trade_count

        result = check_trade_count(5, {"max_trades_per_day": 20})
        assert result["passed"] is True

    def test_trade_count_fail(self) -> None:
        from finance_agent.engine.risk import check_trade_count

        result = check_trade_count(20, {"max_trades_per_day": 20})
        assert result["passed"] is False

    def test_concentration_pass(self) -> None:
        from finance_agent.engine.risk import check_concentration

        proposal = {"ticker": "NVDA", "direction": "buy"}
        positions: list[dict] = []
        settings = {"max_positions_per_symbol": 2}
        result = check_concentration(proposal, positions, settings)
        assert result["passed"] is True

    def test_concentration_fail(self) -> None:
        from finance_agent.engine.risk import check_concentration

        proposal = {"ticker": "NVDA", "direction": "buy"}
        positions = [
            {"symbol": "NVDA", "qty": 5},
            {"symbol": "NVDA", "qty": 3},
        ]
        settings = {"max_positions_per_symbol": 2}
        result = check_concentration(proposal, positions, settings)
        assert result["passed"] is False

    def test_concentration_sell_always_passes(self) -> None:
        from finance_agent.engine.risk import check_concentration

        proposal = {"ticker": "NVDA", "direction": "sell"}
        positions = [
            {"symbol": "NVDA", "qty": 5},
            {"symbol": "NVDA", "qty": 3},
        ]
        settings = {"max_positions_per_symbol": 2}
        result = check_concentration(proposal, positions, settings)
        assert result["passed"] is True

    def test_adjust_position_for_risk(self) -> None:
        from finance_agent.engine.risk import adjust_position_for_risk

        proposal = {
            "quantity": 10,
            "limit_price": 127.0,
            "estimated_cost": 1270.0,
        }
        account = {"equity": 1000.0}
        settings = {"max_position_pct": 0.10}
        adjusted = adjust_position_for_risk(proposal, account, settings)
        assert adjusted["quantity"] < 10  # noqa: PLR2004

    def test_run_all_risk_checks_all_pass(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.risk import run_all_risk_checks

        engine_db.execute(
            "INSERT INTO company (ticker, name) VALUES ('TEST', 'Test Co')"
        )
        engine_db.execute(
            "INSERT INTO trade_proposal "
            "(company_id, ticker, direction, quantity, limit_price, "
            "estimated_cost, confidence_score, base_score, signal_score, "
            "indicator_score, momentum_score, expires_at) "
            "VALUES (1, 'TEST', 'buy', 1, 50.0, 50.0, 0.55, 0.50, "
            "0.60, 0.40, 0.30, '2099-12-31T21:00:00Z')"
        )
        engine_db.commit()

        proposal = {
            "id": 1, "ticker": "TEST", "direction": "buy",
            "quantity": 1, "limit_price": 50.0, "estimated_cost": 50.0,
        }
        account = {"equity": 1000.0}
        positions: list[dict] = []
        pnl = {"total_change": -10.0}
        settings = {
            "max_position_pct": 0.10,
            "max_daily_loss_pct": 0.05,
            "max_trades_per_day": 20,
            "max_positions_per_symbol": 2,
        }

        results = run_all_risk_checks(
            engine_db, proposal, account, positions, 3, pnl, settings,
        )
        assert len(results) == 4  # noqa: PLR2004
        assert all(r["passed"] for r in results)

    def test_run_all_risk_checks_reports_all_failures(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.risk import run_all_risk_checks

        engine_db.execute(
            "INSERT INTO company (ticker, name) VALUES ('FAIL', 'Fail Co')"
        )
        engine_db.execute(
            "INSERT INTO trade_proposal "
            "(company_id, ticker, direction, quantity, limit_price, "
            "estimated_cost, confidence_score, base_score, signal_score, "
            "indicator_score, momentum_score, expires_at) "
            "VALUES (1, 'FAIL', 'buy', 100, 500.0, 50000.0, 0.55, "
            "0.50, 0.60, 0.40, 0.30, '2099-12-31T21:00:00Z')"
        )
        engine_db.commit()

        proposal = {
            "id": 1, "ticker": "FAIL", "direction": "buy",
            "quantity": 100, "limit_price": 500.0,
            "estimated_cost": 50000.0,
        }
        account = {"equity": 1000.0}
        positions = [
            {"symbol": "FAIL", "qty": 5},
            {"symbol": "FAIL", "qty": 5},
        ]
        pnl = {"total_change": -100.0}
        settings = {
            "max_position_pct": 0.10,
            "max_daily_loss_pct": 0.05,
            "max_trades_per_day": 20,
            "max_positions_per_symbol": 2,
        }

        results = run_all_risk_checks(
            engine_db, proposal, account, positions, 25, pnl, settings,
        )
        failed = [r for r in results if not r["passed"]]
        assert len(failed) >= 2  # noqa: PLR2004


# ---------------------------------------------------------------------------
# T029: Risk settings unit tests
# ---------------------------------------------------------------------------


class TestRiskSettings:
    """Test risk settings management."""

    def test_get_default_settings(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.state import get_risk_settings

        settings = get_risk_settings(engine_db)
        assert settings["max_position_pct"] == 0.10
        assert settings["max_daily_loss_pct"] == 0.05
        assert settings["max_trades_per_day"] == 20

    def test_update_setting(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.state import (
            get_risk_settings,
            update_risk_setting,
        )

        old, new = update_risk_setting(engine_db, "max_position_pct", 0.08)
        assert old == 0.10
        assert new == 0.08

        settings = get_risk_settings(engine_db)
        assert settings["max_position_pct"] == 0.08

    def test_update_setting_with_audit(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.audit.logger import AuditLogger
        from finance_agent.engine.state import update_risk_setting

        audit = AuditLogger(engine_db)
        update_risk_setting(
            engine_db, "max_trades_per_day", 30,
            updated_by="test", audit=audit,
        )

        events = audit.query(event_type="risk_setting_update")
        assert len(events) == 1
        assert events[0]["payload"]["key"] == "max_trades_per_day"

    def test_update_invalid_key(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.state import update_risk_setting

        with pytest.raises(ValueError, match="Unknown risk setting"):
            update_risk_setting(engine_db, "nonexistent_key", 0.5)

    def test_update_out_of_range(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.state import update_risk_setting

        with pytest.raises(ValueError, match="out of range"):
            update_risk_setting(engine_db, "max_position_pct", 0.99)

    def test_update_below_range(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.state import update_risk_setting

        with pytest.raises(ValueError, match="out of range"):
            update_risk_setting(engine_db, "max_daily_loss_pct", 0.001)


# ---------------------------------------------------------------------------
# T033: Proposal lifecycle unit tests
# ---------------------------------------------------------------------------


class TestProposalLifecycle:
    """Test proposal lifecycle management."""

    def _insert_test_proposal(
        self, conn: sqlite3.Connection, status: str = "pending",
        expires_at: str = "2099-12-31T21:00:00Z",
    ) -> int:
        """Helper to insert a test proposal."""
        # Only insert company if not exists
        existing = conn.execute(
            "SELECT id FROM company WHERE ticker = 'LIFE'"
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO company (ticker, name) "
                "VALUES ('LIFE', 'Lifecycle Co')"
            )
        cursor = conn.execute(
            "INSERT INTO trade_proposal "
            "(company_id, ticker, direction, quantity, limit_price, "
            "estimated_cost, confidence_score, base_score, signal_score, "
            "indicator_score, momentum_score, status, expires_at) "
            "VALUES (1, 'LIFE', 'buy', 2, 100.0, 200.0, 0.60, 0.55, "
            "0.70, 0.50, 0.30, ?, ?)",
            (status, expires_at),
        )
        conn.commit()
        assert cursor.lastrowid is not None
        return cursor.lastrowid

    def test_get_pending_proposals(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.proposals import get_pending_proposals

        pid = self._insert_test_proposal(engine_db)
        proposals = get_pending_proposals(engine_db)
        assert len(proposals) == 1
        assert proposals[0]["id"] == pid

    def test_get_pending_excludes_expired(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.proposals import get_pending_proposals

        self._insert_test_proposal(
            engine_db, expires_at="2020-01-01T21:00:00Z",
        )
        proposals = get_pending_proposals(engine_db)
        assert len(proposals) == 0

    def test_lazy_expiration(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.proposals import get_pending_proposals

        pid = self._insert_test_proposal(
            engine_db, expires_at="2020-01-01T21:00:00Z",
        )
        get_pending_proposals(engine_db)

        row = engine_db.execute(
            "SELECT status FROM trade_proposal WHERE id = ?", (pid,),
        ).fetchone()
        assert row["status"] == "expired"

    def test_approve_proposal(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.proposals import approve_proposal

        pid = self._insert_test_proposal(engine_db)
        result = approve_proposal(engine_db, pid, reason="Looks good")
        assert result is True

        row = engine_db.execute(
            "SELECT status, decision_reason FROM trade_proposal "
            "WHERE id = ?", (pid,),
        ).fetchone()
        assert row["status"] == "approved"
        assert row["decision_reason"] == "Looks good"

    def test_approve_with_audit(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.audit.logger import AuditLogger
        from finance_agent.engine.proposals import approve_proposal

        pid = self._insert_test_proposal(engine_db)
        audit = AuditLogger(engine_db)
        approve_proposal(engine_db, pid, audit=audit)

        events = audit.query(event_type="proposal_approved")
        assert len(events) == 1

    def test_reject_proposal(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.proposals import reject_proposal

        pid = self._insert_test_proposal(engine_db)
        result = reject_proposal(engine_db, pid, reason="Too risky")
        assert result is True

        row = engine_db.execute(
            "SELECT status, decision_reason FROM trade_proposal "
            "WHERE id = ?", (pid,),
        ).fetchone()
        assert row["status"] == "rejected"
        assert row["decision_reason"] == "Too risky"

    def test_approve_non_pending_fails(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.proposals import approve_proposal

        pid = self._insert_test_proposal(engine_db, status="rejected")
        result = approve_proposal(engine_db, pid)
        assert result is False


# ---------------------------------------------------------------------------
# T037: History and status unit tests
# ---------------------------------------------------------------------------


class TestProposalHistory:
    """Test proposal history queries."""

    def _populate_proposals(
        self, conn: sqlite3.Connection,
    ) -> None:
        """Insert several proposals with different statuses."""
        conn.execute(
            "INSERT INTO company (ticker, name) "
            "VALUES ('HIST', 'Hist Co')"
        )
        conn.execute(
            "INSERT INTO company (ticker, name) "
            "VALUES ('OTH', 'Other Co')"
        )
        for ticker, cid, status in [
            ("HIST", 1, "approved"),
            ("HIST", 1, "rejected"),
            ("HIST", 1, "pending"),
            ("OTH", 2, "approved"),
        ]:
            conn.execute(
                "INSERT INTO trade_proposal "
                "(company_id, ticker, direction, quantity, limit_price, "
                "estimated_cost, confidence_score, base_score, "
                "signal_score, indicator_score, momentum_score, "
                "status, expires_at) "
                "VALUES (?, ?, 'buy', 1, 100.0, 100.0, 0.55, 0.50, "
                "0.60, 0.40, 0.30, ?, '2099-12-31T21:00:00Z')",
                (cid, ticker, status),
            )
        conn.commit()

    def test_query_all(self, engine_db: sqlite3.Connection) -> None:
        from finance_agent.engine.proposals import query_proposal_history

        self._populate_proposals(engine_db)
        results = query_proposal_history(engine_db)
        assert len(results) == 4  # noqa: PLR2004

    def test_query_by_ticker(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.proposals import query_proposal_history

        self._populate_proposals(engine_db)
        results = query_proposal_history(engine_db, ticker="HIST")
        assert len(results) == 3  # noqa: PLR2004

    def test_query_by_status(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.proposals import query_proposal_history

        self._populate_proposals(engine_db)
        results = query_proposal_history(engine_db, status="approved")
        assert len(results) == 2  # noqa: PLR2004

    def test_query_with_limit(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.proposals import query_proposal_history

        self._populate_proposals(engine_db)
        results = query_proposal_history(engine_db, limit=2)
        assert len(results) == 2  # noqa: PLR2004

    def test_query_empty(self, engine_db: sqlite3.Connection) -> None:
        from finance_agent.engine.proposals import query_proposal_history

        results = query_proposal_history(engine_db, ticker="ZZZZ")
        assert len(results) == 0


class TestEngineStatus:
    """Test engine status summary."""

    def test_status_returns_expected_keys(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.proposals import get_engine_status

        account = {"equity": 1000.0, "buying_power": 500.0}
        pnl = {
            "total_change": -10.0, "unrealized": -5.0,
            "realized_estimate": -5.0,
        }

        status = get_engine_status(engine_db, account, 3, pnl)
        assert "kill_switch" in status
        assert "equity" in status
        assert "daily_order_count" in status
        assert "pending_proposals" in status
        assert "risk_settings" in status

    def test_status_reflects_kill_switch(
        self, engine_db: sqlite3.Connection,
    ) -> None:
        from finance_agent.engine.proposals import get_engine_status
        from finance_agent.engine.state import set_kill_switch

        set_kill_switch(engine_db, True)

        account = {"equity": 1000.0, "buying_power": 500.0}
        pnl = {
            "total_change": 0.0, "unrealized": 0.0,
            "realized_estimate": 0.0,
        }

        status = get_engine_status(engine_db, account, 0, pnl)
        assert status["kill_switch"] is True


# ---------------------------------------------------------------------------
# Helpers for test data
# ---------------------------------------------------------------------------


def _insert_sample_signals(
    conn: sqlite3.Connection, company_id: int,
) -> None:
    """Insert sample research signals for testing."""
    # Need a source document first
    conn.execute(
        "INSERT INTO source_document "
        "(company_id, source_type, content_type, source_id, title, "
        "published_at, ingested_at, content_hash, local_path, "
        "file_size_bytes, analysis_status) "
        "VALUES (?, 'sec_filing', '10-K', 'test-doc-1', "
        "'NVDA 10-K 2025', "
        "'2025-12-01T00:00:00Z', "
        "strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), "
        "'abc123', '/tmp/test', 1000, 'complete')",
        (company_id,),
    )
    doc_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    signals_data = [
        ("sentiment", "fact", "high", "Strong revenue growth beat"),
        ("guidance_change", "fact", "high", "Company raised guidance"),
        ("financial_metric", "fact", "medium", "EPS beat by 12%"),
        ("competitive_insight", "inference", "medium", "Market share grew"),
    ]
    for sig_type, evidence, confidence, summary in signals_data:
        conn.execute(
            "INSERT INTO research_signal "
            "(company_id, document_id, signal_type, evidence_type, "
            "confidence, summary) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (company_id, doc_id, sig_type, evidence, confidence, summary),
        )
    conn.commit()


def _insert_sample_bars(
    conn: sqlite3.Connection, company_id: int,
) -> None:
    """Insert 30 days of sample daily bars for testing."""
    from datetime import UTC, datetime, timedelta

    base_date = datetime.now(UTC) - timedelta(days=30)
    for i in range(30):
        bar_date = base_date + timedelta(days=i)
        ts = bar_date.strftime("%Y-%m-%dT00:00:00Z")
        close = 125.0 + i * 0.5
        conn.execute(
            "INSERT INTO price_bar "
            "(company_id, ticker, timeframe, bar_timestamp, "
            "open, high, low, close, volume) "
            "VALUES (?, 'NVDA', 'day', ?, ?, ?, ?, ?, ?)",
            (
                company_id, ts,
                close - 1, close + 2, close - 2, close,
                1000000 + i * 10000,
            ),
        )
    conn.commit()


def _insert_sample_indicators(
    conn: sqlite3.Connection, company_id: int,
) -> None:
    """Insert sample technical indicators."""
    from datetime import UTC, datetime

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    indicators = [
        ("sma_20", 137.0),
        ("sma_50", 133.0),
        ("rsi_14", 58.0),
        ("vwap", 136.0),
    ]
    for ind_type, value in indicators:
        conn.execute(
            "INSERT INTO technical_indicator "
            "(company_id, ticker, indicator_type, timeframe, value, "
            "computed_at, bar_date) "
            "VALUES (?, 'NVDA', ?, 'day', ?, ?, '2025-12-30')",
            (company_id, ind_type, value, now),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# T038: Audit Logging Verification
# ---------------------------------------------------------------------------


class TestAuditLogging:
    """Verify all engine operations produce audit log entries."""

    @staticmethod
    def _ensure_company(conn: sqlite3.Connection) -> int:
        """Insert a test company and return its ID."""
        cursor = conn.execute(
            "INSERT OR IGNORE INTO company (ticker, name) VALUES ('TEST', 'Test Co')"
        )
        conn.commit()
        if cursor.lastrowid and cursor.lastrowid > 0:
            return cursor.lastrowid
        row = conn.execute(
            "SELECT id FROM company WHERE ticker = 'TEST'"
        ).fetchone()
        return int(row["id"])

    def test_kill_switch_toggle_audited(self, engine_db: sqlite3.Connection) -> None:
        from finance_agent.audit.logger import AuditLogger
        from finance_agent.engine.state import set_kill_switch

        audit = AuditLogger(engine_db)
        set_kill_switch(engine_db, True, toggled_by="test", audit=audit)

        events = audit.query(event_type="kill_switch_toggle")
        assert len(events) == 1
        assert events[0]["payload"]["active"] is True

    def test_risk_setting_update_audited(self, engine_db: sqlite3.Connection) -> None:
        from finance_agent.audit.logger import AuditLogger
        from finance_agent.engine.state import update_risk_setting

        audit = AuditLogger(engine_db)
        update_risk_setting(engine_db, "max_position_pct", 0.15, audit=audit)

        events = audit.query(event_type="risk_setting_update")
        assert len(events) == 1
        assert events[0]["payload"]["key"] == "max_position_pct"
        assert events[0]["payload"]["new_value"] == 0.15

    def test_proposal_approve_audited(self, engine_db: sqlite3.Connection) -> None:
        from finance_agent.audit.logger import AuditLogger
        from finance_agent.engine.proposals import approve_proposal, save_proposal

        audit = AuditLogger(engine_db)
        cid = self._ensure_company(engine_db)
        pid = save_proposal(engine_db, {
            "company_id": cid, "ticker": "TEST", "direction": "buy",
            "quantity": 1, "limit_price": 10.0, "estimated_cost": 10.0,
            "confidence_score": 0.6, "base_score": 0.6, "llm_adjustment": 0.0,
            "signal_score": 0.5, "indicator_score": 0.4, "momentum_score": 0.3,
            "expires_at": "2099-12-31T21:00:00Z",
        })
        approve_proposal(engine_db, pid, reason="test approval", audit=audit)

        events = audit.query(event_type="proposal_approved")
        assert len(events) == 1
        assert events[0]["payload"]["proposal_id"] == pid

    def test_proposal_reject_audited(self, engine_db: sqlite3.Connection) -> None:
        from finance_agent.audit.logger import AuditLogger
        from finance_agent.engine.proposals import reject_proposal, save_proposal

        audit = AuditLogger(engine_db)
        cid = self._ensure_company(engine_db)
        pid = save_proposal(engine_db, {
            "company_id": cid, "ticker": "TEST", "direction": "buy",
            "quantity": 1, "limit_price": 10.0, "estimated_cost": 10.0,
            "confidence_score": 0.6, "base_score": 0.6, "llm_adjustment": 0.0,
            "signal_score": 0.5, "indicator_score": 0.4, "momentum_score": 0.3,
            "expires_at": "2099-12-31T21:00:00Z",
        })
        reject_proposal(engine_db, pid, reason="test rejection", audit=audit)

        events = audit.query(event_type="proposal_rejected")
        assert len(events) == 1
        assert events[0]["payload"]["reason"] == "test rejection"

    def test_risk_checks_audited(self, engine_db: sqlite3.Connection) -> None:
        from finance_agent.audit.logger import AuditLogger
        from finance_agent.engine.proposals import save_proposal
        from finance_agent.engine.risk import run_all_risk_checks

        audit = AuditLogger(engine_db)
        cid = self._ensure_company(engine_db)
        pid = save_proposal(engine_db, {
            "company_id": cid, "ticker": "TEST", "direction": "buy",
            "quantity": 1, "limit_price": 10.0, "estimated_cost": 10.0,
            "confidence_score": 0.6, "base_score": 0.6, "llm_adjustment": 0.0,
            "signal_score": 0.5, "indicator_score": 0.4, "momentum_score": 0.3,
            "expires_at": "2099-12-31T21:00:00Z",
        })
        proposal = {"id": pid, "ticker": "TEST", "direction": "buy",
                     "quantity": 1, "estimated_cost": 10.0}
        account = {"equity": "10000.0"}
        run_all_risk_checks(
            engine_db, proposal, account, [], 0,
            {"total_change": 0}, {"max_position_pct": 0.10}, audit=audit,
        )

        events = audit.query(event_type="risk_checks_evaluated")
        assert len(events) == 1
        assert events[0]["payload"]["proposal_id"] == pid
        assert events[0]["payload"]["all_passed"] is True
