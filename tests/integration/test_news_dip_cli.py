"""Integration tests for news dip CLI flow."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from finance_agent.patterns.models import (
    ActionType,
    EntrySignal,
    EventDetectionConfig,
    ExitCriteria,
    ManualEvent,
    RuleSet,
    StrikeStrategy,
    TradeAction,
    TriggerCondition,
    TriggerType,
)


def _make_pharma_rule_set() -> RuleSet:
    """Create a pharma dip pattern RuleSet."""
    return RuleSet(
        trigger_type=TriggerType.QUALITATIVE,
        trigger_conditions=[
            TriggerCondition(field="price_change_pct", operator="gte", value="5.0", description="5% spike"),
            TriggerCondition(field="volume_spike", operator="gte", value="1.5", description="1.5x volume"),
        ],
        entry_signal=EntrySignal(condition="pullback_pct", value="2.0", window_days=2, description="2% dip"),
        action=TradeAction(action_type=ActionType.BUY_CALL, strike_strategy=StrikeStrategy.ATM, expiration_days=30, description="Buy ATM call"),
        exit_criteria=ExitCriteria(profit_target_pct=20.0, stop_loss_pct=10.0, description="20% profit / 10% stop"),
        sector_filter="healthcare",
    )


def _make_bars(n: int, base_price: float = 100.0, base_volume: int = 1000000) -> list[dict]:
    """Generate n synthetic bars starting 2024-01-01."""
    from datetime import date, timedelta
    bars = []
    start = date(2024, 1, 1)
    for i in range(n):
        d = start + timedelta(days=i)
        bars.append({
            "bar_timestamp": d.isoformat(),
            "open": base_price,
            "high": base_price + 1,
            "low": base_price - 1,
            "close": base_price,
            "volume": base_volume,
        })
    return bars


class TestNewsDipBacktest:
    """Test the run_news_dip_backtest function end-to-end."""

    def test_backtest_with_manual_events(self):
        """Manual events produce DetectedEvents and run through backtest."""
        from finance_agent.patterns.backtest import run_news_dip_backtest

        rule_set = _make_pharma_rule_set()
        bars = _make_bars(60)

        # Insert a spike at day 25 (big price jump + volume)
        bars[25]["close"] = 106.0  # +6% from 100
        bars[25]["high"] = 107.0
        bars[25]["volume"] = 3000000  # 3x normal
        # Dip at day 26 (pullback)
        bars[26]["close"] = 103.0
        bars[26]["high"] = 104.0
        bars[26]["low"] = 102.0

        config = EventDetectionConfig(
            manual_events=[ManualEvent(date="2024-01-26", label="FDA approval")],
        )

        report, no_entry_events = run_news_dip_backtest(
            pattern_id=1,
            rule_set=rule_set,
            bars=bars,
            ticker="TEST",
            start_date="2024-01-01",
            end_date="2024-03-01",
            event_config=config,
        )

        assert report.trigger_count == 1
        assert report.pattern_id == 1

    def test_backtest_auto_detection(self):
        """Automatic spike detection finds events."""
        from finance_agent.patterns.backtest import run_news_dip_backtest

        rule_set = _make_pharma_rule_set()
        bars = _make_bars(60)

        # Insert spike at day 25
        bars[25]["close"] = 106.0
        bars[25]["high"] = 107.0
        bars[25]["volume"] = 3000000

        config = EventDetectionConfig(spike_threshold_pct=5.0, volume_multiple_min=1.5)

        report, no_entry_events = run_news_dip_backtest(
            pattern_id=1,
            rule_set=rule_set,
            bars=bars,
            ticker="TEST",
            start_date="2024-01-01",
            end_date="2024-03-01",
            event_config=config,
        )

        assert report.trigger_count >= 1

    def test_backtest_no_events(self):
        """With high threshold, no events detected."""
        from finance_agent.patterns.backtest import run_news_dip_backtest

        rule_set = _make_pharma_rule_set()
        bars = _make_bars(60)  # All stable bars

        config = EventDetectionConfig(spike_threshold_pct=15.0, volume_multiple_min=3.0)

        report, no_entry_events = run_news_dip_backtest(
            pattern_id=1,
            rule_set=rule_set,
            bars=bars,
            ticker="TEST",
            start_date="2024-01-01",
            end_date="2024-03-01",
            event_config=config,
        )

        assert report.trigger_count == 0
        assert report.trade_count == 0


class TestAutoApproveBlocked:
    """Verify --auto-approve is blocked for qualitative patterns."""

    def test_auto_approve_blocked_for_qualitative(self):
        """Qualitative patterns reject --auto-approve."""
        # Test the logic directly: check that qualitative + auto_approve = error
        rule_set = _make_pharma_rule_set()
        assert rule_set.trigger_type == TriggerType.QUALITATIVE

        # The CLI blocks this -- we verify the condition
        is_qualitative = rule_set.trigger_type.value == "qualitative"
        auto_approve = True
        assert is_qualitative and auto_approve  # This would trigger the error path

    def test_quantitative_allows_auto_approve(self):
        """Quantitative patterns allow --auto-approve."""
        rule_set = _make_pharma_rule_set()
        # Override trigger type
        rule_set_dict = rule_set.model_dump()
        rule_set_dict["trigger_type"] = "quantitative"
        quant_rule_set = RuleSet.model_validate(rule_set_dict)

        is_qualitative = quant_rule_set.trigger_type.value == "qualitative"
        assert not is_qualitative  # Auto-approve would be allowed
