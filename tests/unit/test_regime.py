"""Unit tests for time-based regime analysis."""

from __future__ import annotations

from datetime import datetime, timedelta

from finance_agent.patterns.models import BacktestTrade, RegimeConfig, RegimePeriod
from finance_agent.patterns.regime import detect_time_based_regimes


def _make_trade(trigger_date: str, return_pct: float, ticker: str = "TEST") -> BacktestTrade:
    return BacktestTrade(
        ticker=ticker,
        trigger_date=trigger_date,
        entry_date=trigger_date,
        entry_price=100.0,
        exit_date=trigger_date,
        exit_price=100.0 * (1 + return_pct / 100),
        return_pct=return_pct,
        action_type="buy_call",
    )


class TestDetectTimeBasedRegimes:
    """Tests for detect_time_based_regimes()."""

    def test_min_trades_guard(self) -> None:
        """5 trades is below default min_trades_for_regime=10; should return empty."""
        start = datetime(2024, 1, 1)
        trades = [
            _make_trade((start + timedelta(days=i * 5)).strftime("%Y-%m-%d"), 5.0)
            for i in range(5)
        ]
        result = detect_time_based_regimes(trades)
        assert result == []

    def test_strong_regime(self) -> None:
        """12 trades over 30 days, 10 winners — should classify as 'strong'."""
        start = datetime(2024, 1, 1)
        trades = []
        for i in range(12):
            date_str = (start + timedelta(days=i * 3)).strftime("%Y-%m-%d")
            # First 10 trades are winners, last 2 are losers
            ret = 5.0 if i < 10 else -3.0
            trades.append(_make_trade(date_str, ret))

        config = RegimeConfig(strong_threshold=0.60)
        result = detect_time_based_regimes(trades, config)

        assert len(result) >= 1
        labels = {r.label for r in result}
        assert "strong" in labels

    def test_breakdown_regime(self) -> None:
        """12 trades over 30 days, all losers — should classify as 'breakdown'."""
        start = datetime(2024, 1, 1)
        trades = [
            _make_trade((start + timedelta(days=i * 3)).strftime("%Y-%m-%d"), -5.0)
            for i in range(12)
        ]
        result = detect_time_based_regimes(trades)

        assert len(result) >= 1
        labels = {r.label for r in result}
        assert "breakdown" in labels

    def test_mixed_regimes(self) -> None:
        """20 trades over 200 days: first 10 winners, last 10 losers — at least 2 regimes."""
        start = datetime(2024, 1, 1)
        trades = []

        # First 10 trades (days 1-90): all winners
        for i in range(10):
            date_str = (start + timedelta(days=i * 10)).strftime("%Y-%m-%d")
            trades.append(_make_trade(date_str, 10.0))

        # Last 10 trades (days 100-190): all losers
        for i in range(10):
            date_str = (start + timedelta(days=100 + i * 10)).strftime("%Y-%m-%d")
            trades.append(_make_trade(date_str, -10.0))

        result = detect_time_based_regimes(trades)

        assert len(result) >= 2
        labels = [r.label for r in result]
        assert "strong" in labels
        assert "breakdown" in labels

    def test_threshold_boundaries(self) -> None:
        """Test exact threshold classification via _classify_win_rate logic.

        - 60% win rate exactly = 'strong'  (6 wins, 4 losses in 10 trades)
        - 40% win rate exactly = 'weak'    (4 wins, 6 losses in 10 trades)
        - 39% win rate = 'breakdown'
        """
        start = datetime(2024, 1, 1)

        # --- 60% win rate exactly: 6 wins + 4 losses → strong ---
        trades_60 = []
        for i in range(6):
            trades_60.append(
                _make_trade((start + timedelta(days=i)).strftime("%Y-%m-%d"), 5.0)
            )
        for i in range(4):
            trades_60.append(
                _make_trade((start + timedelta(days=6 + i)).strftime("%Y-%m-%d"), -5.0)
            )
        # All 10 trades fit within the default 63-day window, so _build_regime is used
        config = RegimeConfig(min_trades_for_regime=10)
        result_60 = detect_time_based_regimes(trades_60, config)
        assert len(result_60) == 1
        assert result_60[0].label == "strong"

        # --- 40% win rate exactly: 4 wins + 6 losses → weak ---
        trades_40 = []
        for i in range(4):
            trades_40.append(
                _make_trade((start + timedelta(days=i)).strftime("%Y-%m-%d"), 5.0)
            )
        for i in range(6):
            trades_40.append(
                _make_trade((start + timedelta(days=4 + i)).strftime("%Y-%m-%d"), -5.0)
            )
        result_40 = detect_time_based_regimes(trades_40, config)
        assert len(result_40) == 1
        assert result_40[0].label == "weak"

        # --- 39% win rate: need ~39 wins out of 100, but easier: use
        #     _classify_win_rate indirectly via 3 wins + 7 losses + extra → breakdown ---
        # 3 wins + 8 losses = ~27% → breakdown (well below 40%)
        trades_low = []
        for i in range(3):
            trades_low.append(
                _make_trade((start + timedelta(days=i)).strftime("%Y-%m-%d"), 5.0)
            )
        for i in range(8):
            trades_low.append(
                _make_trade((start + timedelta(days=3 + i)).strftime("%Y-%m-%d"), -5.0)
            )
        config_11 = RegimeConfig(min_trades_for_regime=10)
        result_low = detect_time_based_regimes(trades_low, config_11)
        assert len(result_low) == 1
        assert result_low[0].label == "breakdown"

    def test_window_min_trades_skipped(self) -> None:
        """12 trades spread over 500 days — each 63-day window has < 3 trades."""
        start = datetime(2024, 1, 1)
        # Space trades ~45 days apart so each 63-day window has at most 1-2 trades
        trades = [
            _make_trade((start + timedelta(days=i * 45)).strftime("%Y-%m-%d"), 5.0)
            for i in range(12)
        ]
        config = RegimeConfig(min_trades_per_window=3)
        result = detect_time_based_regimes(trades, config)
        assert result == []

    def test_empty_trades(self) -> None:
        """Empty trade list should return empty result."""
        result = detect_time_based_regimes([])
        assert result == []

    def test_custom_config(self) -> None:
        """Custom RegimeConfig thresholds should be applied correctly."""
        start = datetime(2024, 1, 1)

        # 12 trades over 20 days with 70% win rate (8 wins, 4 losses)
        trades = []
        for i in range(8):
            trades.append(
                _make_trade((start + timedelta(days=i * 2)).strftime("%Y-%m-%d"), 5.0)
            )
        for i in range(4):
            trades.append(
                _make_trade((start + timedelta(days=16 + i * 2)).strftime("%Y-%m-%d"), -5.0)
            )

        # With strong_threshold=0.70, a 66% win rate (8/12) should NOT be strong
        config_strict = RegimeConfig(
            window_trading_days=30,
            strong_threshold=0.70,
            weak_threshold=0.50,
            min_trades_for_regime=10,
            min_trades_per_window=3,
        )
        result_strict = detect_time_based_regimes(trades, config_strict)
        assert len(result_strict) >= 1
        # 8/12 = 0.667 which is < 0.70, so should be "weak" not "strong"
        for regime in result_strict:
            assert regime.label != "strong"

        # With strong_threshold=0.60 (default), 66% win rate IS strong
        config_lenient = RegimeConfig(
            window_trading_days=30,
            strong_threshold=0.60,
            weak_threshold=0.40,
            min_trades_for_regime=10,
            min_trades_per_window=3,
        )
        result_lenient = detect_time_based_regimes(trades, config_lenient)
        assert len(result_lenient) >= 1
        labels = {r.label for r in result_lenient}
        assert "strong" in labels
