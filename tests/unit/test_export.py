"""Tests for finance_agent.patterns.export — markdown report generation."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

from finance_agent.patterns.export import (
    export_ab_test_markdown,
    export_backtest_markdown,
    generate_export_path,
)
from finance_agent.patterns.models import (
    ABTestResult,
    AggregatedBacktestReport,
    BacktestReport,
    PairwiseComparison,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pattern(
    *,
    id: int = 1,
    name: str = "Test Pattern",
    description: str = "Buy on dip after spike.",
) -> dict:
    return {"id": id, "name": name, "description": description}


def _make_backtest(
    *,
    trigger_count: int = 10,
    trade_count: int = 5,
    win_count: int = 3,
    total_return_pct: float = 12.5,
    avg_return_pct: float = 2.5,
    max_drawdown_pct: float = 4.2,
    sharpe_ratio: float | None = 1.35,
    date_range_start: str = "2024-01-01",
    date_range_end: str = "2024-12-31",
) -> dict:
    return {
        "trigger_count": trigger_count,
        "trade_count": trade_count,
        "win_count": win_count,
        "total_return_pct": total_return_pct,
        "avg_return_pct": avg_return_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "sharpe_ratio": sharpe_ratio,
        "date_range_start": date_range_start,
        "date_range_end": date_range_end,
    }


def _make_trade(
    *,
    ticker: str = "AAPL",
    trigger_date: str = "2024-03-01",
    entry_date: str = "2024-03-03",
    entry_price: float = 170.00,
    exit_date: str = "2024-03-15",
    exit_price: float = 180.50,
    return_pct: float = 6.2,
) -> dict:
    return {
        "ticker": ticker,
        "trigger_date": trigger_date,
        "entry_date": entry_date,
        "entry_price": entry_price,
        "exit_date": exit_date,
        "exit_price": exit_price,
        "return_pct": return_pct,
    }


def _make_ab_result(
    *,
    significant: bool = True,
) -> ABTestResult:
    """Build a minimal ABTestResult with two variants and one comparison."""
    report_a = BacktestReport(
        pattern_id=1,
        date_range_start="2024-01-01",
        date_range_end="2024-12-31",
        trigger_count=20,
        trade_count=10,
        win_count=7,
        total_return_pct=15.0,
        avg_return_pct=1.5,
        max_drawdown_pct=3.0,
        sharpe_ratio=1.2,
    )
    report_b = BacktestReport(
        pattern_id=2,
        date_range_start="2024-01-01",
        date_range_end="2024-12-31",
        trigger_count=18,
        trade_count=8,
        win_count=3,
        total_return_pct=4.0,
        avg_return_pct=0.5,
        max_drawdown_pct=5.0,
        sharpe_ratio=0.6,
    )
    variant_a = AggregatedBacktestReport(
        pattern_id=1,
        date_range_start="2024-01-01",
        date_range_end="2024-12-31",
        tickers=["AAPL", "MSFT"],
        combined_report=report_a,
    )
    variant_b = AggregatedBacktestReport(
        pattern_id=2,
        date_range_start="2024-01-01",
        date_range_end="2024-12-31",
        tickers=["AAPL", "MSFT"],
        combined_report=report_b,
    )
    comparison = PairwiseComparison(
        variant_a_id=1,
        variant_b_id=2,
        win_rate_p_value=0.03 if significant else 0.45,
        win_rate_significant=significant,
        avg_return_p_value=0.02 if significant else 0.60,
        avg_return_significant=significant,
    )
    return ABTestResult(
        pattern_ids=[1, 2],
        tickers=["AAPL", "MSFT"],
        date_range_start="2024-01-01",
        date_range_end="2024-12-31",
        variant_reports=[variant_a, variant_b],
        comparisons=[comparison],
        best_variant_id=1,
        best_is_significant=significant,
        sample_size_warnings=["Pattern #2 has fewer than 30 trades."] if not significant else [],
    )


# ---------------------------------------------------------------------------
# export_backtest_markdown
# ---------------------------------------------------------------------------

class TestExportBacktestMarkdown:
    """Tests for export_backtest_markdown."""

    def test_header_contains_pattern_name_and_id(self):
        pattern = _make_pattern(id=42, name="Pharma Spike Dip")
        result = export_backtest_markdown(pattern, _make_backtest(), [])
        assert "# Backtest Report: Pattern #42 -- Pharma Spike Dip" in result

    def test_contains_generated_date(self):
        today = date.today().isoformat()
        result = export_backtest_markdown(_make_pattern(), _make_backtest(), [])
        assert f"**Generated**: {today}" in result

    def test_contains_date_range(self):
        bt = _make_backtest(date_range_start="2023-06-01", date_range_end="2024-06-01")
        result = export_backtest_markdown(_make_pattern(), bt, [])
        assert "2023-06-01 to 2024-06-01" in result

    def test_pattern_description_section(self):
        pattern = _make_pattern(description="Buy the dip after earnings spike.")
        result = export_backtest_markdown(pattern, _make_backtest(), [])
        assert "## Pattern Description" in result
        assert "Buy the dip after earnings spike." in result

    def test_no_description_section_when_empty(self):
        pattern = _make_pattern(description="")
        result = export_backtest_markdown(pattern, _make_backtest(), [])
        assert "## Pattern Description" not in result

    def test_aggregate_results_table_present(self):
        bt = _make_backtest(
            trigger_count=10,
            trade_count=5,
            win_count=3,
            avg_return_pct=2.5,
            total_return_pct=12.5,
            max_drawdown_pct=4.2,
            sharpe_ratio=1.35,
        )
        result = export_backtest_markdown(_make_pattern(), bt, [])
        assert "## Aggregate Results" in result
        assert "| Total Events | 10 |" in result
        assert "| Total Trades | 5 |" in result
        assert "60.0% (3/5)" in result  # win rate
        assert "+2.5%" in result  # avg return
        assert "+12.5%" in result  # total return
        assert "-4.2%" in result  # drawdown
        assert "1.35" in result  # sharpe

    def test_negative_avg_return_no_plus_sign(self):
        bt = _make_backtest(avg_return_pct=-1.3, total_return_pct=-5.0)
        result = export_backtest_markdown(_make_pattern(), bt, [])
        assert "| Avg Return | -1.3% |" in result
        assert "| Total Return | -5.0% |" in result

    def test_sharpe_omitted_when_none(self):
        bt = _make_backtest(sharpe_ratio=None)
        result = export_backtest_markdown(_make_pattern(), bt, [])
        assert "Sharpe" not in result

    def test_trade_log_with_trades(self):
        trades = [
            _make_trade(
                ticker="AAPL",
                trigger_date="2024-03-01",
                entry_date="2024-03-03",
                entry_price=170.00,
                exit_date="2024-03-15",
                exit_price=180.50,
                return_pct=6.2,
            ),
            _make_trade(
                ticker="MSFT",
                trigger_date="2024-04-10",
                entry_date="2024-04-12",
                entry_price=400.00,
                exit_date="2024-04-20",
                exit_price=390.00,
                return_pct=-2.5,
            ),
        ]
        result = export_backtest_markdown(_make_pattern(), _make_backtest(), trades)
        assert "## Trade Log" in result
        assert "| 1 | AAPL |" in result
        assert "| 2 | MSFT |" in result
        assert "+6.2%" in result
        assert "-2.5%" in result
        assert "$170.00" in result
        assert "$180.50" in result

    def test_zero_trade_case_no_trade_log(self):
        bt = _make_backtest(trade_count=0, win_count=0)
        result = export_backtest_markdown(_make_pattern(), bt, [])
        assert "## Trade Log" not in result
        # Win rate / avg return rows should also be absent when trade_count=0
        assert "Win Rate" not in result

    def test_pattern_fallback_name(self):
        """When name is absent, falls back to 'Pattern #<id>'."""
        pattern = {"id": 7}
        result = export_backtest_markdown(pattern, _make_backtest(), [])
        assert "Pattern #7" in result


# ---------------------------------------------------------------------------
# export_ab_test_markdown
# ---------------------------------------------------------------------------

class TestExportABTestMarkdown:
    """Tests for export_ab_test_markdown."""

    def test_header_lists_pattern_ids(self):
        ab = _make_ab_result()
        result = export_ab_test_markdown(ab, {1: "Alpha", 2: "Beta"})
        assert "# A/B Test Report: Patterns #1, #2" in result

    def test_variant_metrics_table(self):
        ab = _make_ab_result()
        result = export_ab_test_markdown(ab, {1: "Alpha", 2: "Beta"})
        assert "## Variant Metrics" in result
        assert "| 1 | Alpha |" in result
        assert "| 2 | Beta |" in result
        # Variant A: 7/10 = 70.0%
        assert "70.0%" in result
        # Variant B: 3/8 = 37.5%
        assert "37.5%" in result

    def test_statistical_significance_table(self):
        ab = _make_ab_result(significant=True)
        result = export_ab_test_markdown(ab, {1: "Alpha", 2: "Beta"})
        assert "## Statistical Significance" in result
        assert "#1 vs #2" in result
        # p=0.03 should get (*) marker
        assert "(*)" in result

    def test_result_section_best_variant(self):
        ab = _make_ab_result(significant=True)
        result = export_ab_test_markdown(ab, {1: "Alpha", 2: "Beta"})
        assert "## Result" in result
        assert "**Best variant**: #1 (Alpha)" in result

    def test_significant_result_wording(self):
        ab = _make_ab_result(significant=True)
        result = export_ab_test_markdown(ab, {1: "Alpha", 2: "Beta"})
        assert "Statistically significant (p < 0.05)" in result

    def test_not_significant_result_wording(self):
        ab = _make_ab_result(significant=False)
        result = export_ab_test_markdown(ab, {1: "Alpha", 2: "Beta"})
        assert "Not statistically significant (p > 0.05)" in result

    def test_sample_size_warnings_included(self):
        ab = _make_ab_result(significant=False)
        result = export_ab_test_markdown(ab, {1: "Alpha", 2: "Beta"})
        assert "Pattern #2 has fewer than 30 trades." in result

    def test_no_warnings_when_empty(self):
        ab = _make_ab_result(significant=True)
        assert ab.sample_size_warnings == []
        result = export_ab_test_markdown(ab, {1: "Alpha", 2: "Beta"})
        # There should be no warning lines (lines starting with "- ")
        # after the Result section when warnings list is empty
        assert "fewer than 30 trades" not in result

    def test_tickers_in_header(self):
        ab = _make_ab_result()
        result = export_ab_test_markdown(ab, {1: "Alpha", 2: "Beta"})
        assert "**Tickers**: AAPL, MSFT" in result

    def test_ns_marker_for_high_p_value(self):
        ab = _make_ab_result(significant=False)
        result = export_ab_test_markdown(ab, {1: "Alpha", 2: "Beta"})
        assert "(NS)" in result


# ---------------------------------------------------------------------------
# generate_export_path
# ---------------------------------------------------------------------------

class TestGenerateExportPath:
    """Tests for generate_export_path."""

    @patch("finance_agent.patterns.export.date")
    def test_default_path_includes_pattern_id_and_date(self, mock_date, tmp_path):
        mock_date.today.return_value = date(2025, 3, 15)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        result = generate_export_path(42, output_dir=str(tmp_path))
        assert "pattern-42-backtest-2025-03-15.md" in result

    @patch("finance_agent.patterns.export.date")
    def test_custom_output_dir(self, mock_date, tmp_path):
        mock_date.today.return_value = date(2025, 3, 15)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        result = generate_export_path(1, output_dir=str(tmp_path))
        assert result.startswith(str(tmp_path))

    @patch("finance_agent.patterns.export.date")
    def test_numeric_suffix_when_file_exists(self, mock_date, tmp_path):
        mock_date.today.return_value = date(2025, 3, 15)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        # Create the base file so it collides
        base = tmp_path / "pattern-7-backtest-2025-03-15.md"
        base.write_text("existing")

        result = generate_export_path(7, output_dir=str(tmp_path))
        assert result.endswith("pattern-7-backtest-2025-03-15-1.md")

    @patch("finance_agent.patterns.export.date")
    def test_multiple_collisions(self, mock_date, tmp_path):
        mock_date.today.return_value = date(2025, 3, 15)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        # Create base and first two suffixed files
        (tmp_path / "pattern-5-backtest-2025-03-15.md").write_text("x")
        (tmp_path / "pattern-5-backtest-2025-03-15-1.md").write_text("x")
        (tmp_path / "pattern-5-backtest-2025-03-15-2.md").write_text("x")

        result = generate_export_path(5, output_dir=str(tmp_path))
        assert result.endswith("pattern-5-backtest-2025-03-15-3.md")

    @patch("finance_agent.patterns.export.date")
    def test_ab_test_report_type(self, mock_date, tmp_path):
        mock_date.today.return_value = date(2025, 3, 15)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        result = generate_export_path(10, report_type="ab-test", output_dir=str(tmp_path))
        assert "pattern-10-ab-test-2025-03-15.md" in result
