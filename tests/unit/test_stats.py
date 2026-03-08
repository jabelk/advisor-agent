"""Unit tests for statistical significance functions in patterns.stats."""

from __future__ import annotations

from finance_agent.patterns.models import (
    AggregatedBacktestReport,
    BacktestReport,
)
from finance_agent.patterns.stats import (
    fisher_exact_test,
    format_significance,
    generate_sample_size_warnings,
    welch_ttest,
)


def _make_report(pattern_id: int, trade_count: int, win_count: int = 0) -> AggregatedBacktestReport:
    """Build a minimal AggregatedBacktestReport for testing."""
    return AggregatedBacktestReport(
        pattern_id=pattern_id,
        date_range_start="2024-01-01",
        date_range_end="2024-12-31",
        tickers=["ABBV"],
        combined_report=BacktestReport(
            pattern_id=pattern_id,
            date_range_start="2024-01-01",
            date_range_end="2024-12-31",
            trigger_count=trade_count,
            trade_count=trade_count,
            win_count=win_count,
            total_return_pct=0.0,
            avg_return_pct=0.0,
            max_drawdown_pct=0.0,
        ),
    )


class TestFisherExactTest:
    """Tests for fisher_exact_test()."""

    def test_equal_win_rates_not_significant(self) -> None:
        """Equal win rates should produce a large p-value (not significant)."""
        p = fisher_exact_test(wins_a=5, losses_a=5, wins_b=5, losses_b=5)
        assert p > 0.05

    def test_very_different_win_rates_significant(self) -> None:
        """Very different win rates should produce a small p-value."""
        p = fisher_exact_test(wins_a=20, losses_a=0, wins_b=0, losses_b=20)
        assert p < 0.01

    def test_zero_wins_one_variant(self) -> None:
        """One variant has zero wins; should still compute a valid p-value."""
        p = fisher_exact_test(wins_a=0, losses_a=10, wins_b=5, losses_b=5)
        assert 0.0 <= p <= 1.0

    def test_all_wins_both_variants(self) -> None:
        """Both variants have all wins, zero losses — identical performance."""
        p = fisher_exact_test(wins_a=10, losses_a=0, wins_b=10, losses_b=0)
        assert p > 0.05

    def test_zero_trades_one_variant(self) -> None:
        """One variant has 0 wins and 0 losses (no trades) — should not error."""
        p = fisher_exact_test(wins_a=0, losses_a=0, wins_b=5, losses_b=5)
        assert 0.0 <= p <= 1.0


class TestWelchTtest:
    """Tests for welch_ttest()."""

    def test_identical_returns_high_p_value(self) -> None:
        """Identical return lists should yield p-value = 1.0."""
        returns = [1.0, 2.0, 3.0, 4.0, 5.0]
        p = welch_ttest(returns, list(returns))
        assert p == 1.0

    def test_very_different_returns_small_p_value(self) -> None:
        """Very different distributions should produce a small p-value."""
        returns_a = [10.0, 11.0, 12.0, 13.0, 14.0]
        returns_b = [-10.0, -11.0, -12.0, -13.0, -14.0]
        p = welch_ttest(returns_a, returns_b)
        assert p < 0.01

    def test_single_trade_one_group(self) -> None:
        """Single trade in one group (< 2 values) should return p-value = 1.0."""
        p = welch_ttest([5.0], [1.0, 2.0, 3.0])
        assert p == 1.0

    def test_empty_list(self) -> None:
        """Empty list for one group should return p-value = 1.0."""
        p = welch_ttest([], [1.0, 2.0, 3.0])
        assert p == 1.0

    def test_both_empty(self) -> None:
        """Both groups empty should return p-value = 1.0."""
        p = welch_ttest([], [])
        assert p == 1.0


class TestFormatSignificance:
    """Tests for format_significance()."""

    def test_highly_significant(self) -> None:
        """p < 0.01 should return '(**)'."""
        assert format_significance(0.001) == "(**)"

    def test_significant(self) -> None:
        """0.01 <= p < 0.05 should return '(*)'."""
        assert format_significance(0.03) == "(*)"

    def test_not_significant(self) -> None:
        """p >= 0.05 should return '(NS)'."""
        assert format_significance(0.10) == "(NS)"

    def test_boundary_0_01(self) -> None:
        """Exactly 0.01 is NOT < 0.01, so should return '(*)'."""
        assert format_significance(0.01) == "(*)"

    def test_boundary_0_05(self) -> None:
        """Exactly 0.05 is NOT < 0.05, so should return '(NS)'."""
        assert format_significance(0.05) == "(NS)"

    def test_zero_p_value(self) -> None:
        """p = 0.0 should return '(**)'."""
        assert format_significance(0.0) == "(**)"


class TestGenerateSampleSizeWarnings:
    """Tests for generate_sample_size_warnings()."""

    def test_low_trade_count_warning(self) -> None:
        """Variant with < 10 trades should produce a warning."""
        reports = [_make_report(pattern_id=1, trade_count=5)]
        warnings = generate_sample_size_warnings(reports)
        assert len(warnings) == 1
        assert "only 5 trades" in warnings[0]
        assert "#1" in warnings[0]

    def test_sufficient_trade_count_no_warning(self) -> None:
        """Variant with >= 10 trades should not produce a low-trade warning."""
        reports = [_make_report(pattern_id=1, trade_count=20)]
        warnings = generate_sample_size_warnings(reports)
        assert len(warnings) == 0

    def test_exactly_10_trades_no_warning(self) -> None:
        """Exactly 10 trades is not < 10, so no low-trade warning."""
        reports = [_make_report(pattern_id=1, trade_count=10)]
        warnings = generate_sample_size_warnings(reports)
        assert len(warnings) == 0

    def test_unbalanced_samples_warning(self) -> None:
        """Trade counts differing by > 3x should produce a ratio warning."""
        reports = [
            _make_report(pattern_id=1, trade_count=50),
            _make_report(pattern_id=2, trade_count=10),
        ]
        warnings = generate_sample_size_warnings(reports)
        assert any("differ significantly" in w for w in warnings)

    def test_balanced_and_sufficient_no_warnings(self) -> None:
        """Balanced, sufficient trade counts should produce no warnings."""
        reports = [
            _make_report(pattern_id=1, trade_count=20),
            _make_report(pattern_id=2, trade_count=25),
        ]
        warnings = generate_sample_size_warnings(reports)
        assert warnings == []

    def test_ratio_exactly_3x_no_warning(self) -> None:
        """Ratio of exactly 3.0 is not > 3.0, so no unbalanced warning."""
        reports = [
            _make_report(pattern_id=1, trade_count=30),
            _make_report(pattern_id=2, trade_count=10),
        ]
        warnings = generate_sample_size_warnings(reports)
        assert not any("differ significantly" in w for w in warnings)

    def test_multiple_low_trade_warnings(self) -> None:
        """Multiple variants with < 10 trades should each get a warning."""
        reports = [
            _make_report(pattern_id=1, trade_count=3),
            _make_report(pattern_id=2, trade_count=7),
        ]
        warnings = generate_sample_size_warnings(reports)
        low_trade_warnings = [w for w in warnings if "only" in w]
        assert len(low_trade_warnings) == 2

    def test_zero_trades_variant(self) -> None:
        """Variant with 0 trades should produce a low-trade warning and handle ratio safely."""
        reports = [
            _make_report(pattern_id=1, trade_count=0),
            _make_report(pattern_id=2, trade_count=20),
        ]
        warnings = generate_sample_size_warnings(reports)
        assert any("only 0 trades" in w for w in warnings)
        # Ratio is 20/max(0,1)=20 > 3, so unbalanced warning too
        assert any("differ significantly" in w for w in warnings)
