"""Statistical significance tests for A/B pattern comparison."""

from __future__ import annotations

import sqlite3

from scipy.stats import fisher_exact, ttest_ind

from finance_agent.patterns.models import (
    ABTestResult,
    AggregatedBacktestReport,
    EventDetectionConfig,
    PairwiseComparison,
    RuleSet,
)


def fisher_exact_test(
    wins_a: int, losses_a: int, wins_b: int, losses_b: int,
) -> float:
    """Compare win rates using Fisher's exact test.

    Args:
        wins_a: Number of winning trades for variant A
        losses_a: Number of losing trades for variant A
        wins_b: Number of winning trades for variant B
        losses_b: Number of losing trades for variant B

    Returns:
        Two-sided p-value
    """
    table = [[wins_a, losses_a], [wins_b, losses_b]]
    _, p_value = fisher_exact(table, alternative="two-sided")
    return float(p_value)


def welch_ttest(returns_a: list[float], returns_b: list[float]) -> float:
    """Compare average returns using Welch's t-test (unequal variance).

    Args:
        returns_a: Per-trade returns for variant A
        returns_b: Per-trade returns for variant B

    Returns:
        Two-sided p-value. Returns 1.0 if either sample has fewer than 2 values.
    """
    if len(returns_a) < 2 or len(returns_b) < 2:
        return 1.0
    _, p_value = ttest_ind(returns_a, returns_b, equal_var=False)
    return float(p_value)


def format_significance(p_value: float) -> str:
    """Format a p-value with significance notation.

    Returns:
        '(**)' for p < 0.01, '(*)' for p < 0.05, '(NS)' otherwise.
    """
    if p_value < 0.01:
        return "(**)"
    elif p_value < 0.05:
        return "(*)"
    return "(NS)"


def generate_sample_size_warnings(
    variant_reports: list[AggregatedBacktestReport],
) -> list[str]:
    """Generate warnings for variants with insufficient trade counts.

    Args:
        variant_reports: List of aggregated backtest reports, one per variant

    Returns:
        List of warning strings
    """
    warnings: list[str] = []
    trade_counts = []

    for vr in variant_reports:
        tc = vr.combined_report.trade_count
        trade_counts.append(tc)
        if tc < 10:
            warnings.append(
                f"! Pattern #{vr.pattern_id} has only {tc} trades. "
                "Results may not be statistically reliable."
            )

    # Check for unbalanced samples
    if len(trade_counts) >= 2 and max(trade_counts) > 0:
        ratio = max(trade_counts) / max(min(trade_counts), 1)
        if ratio > 3.0:
            warnings.append(
                f"! Trade counts differ significantly across variants "
                f"({min(trade_counts)} vs {max(trade_counts)}). "
                "Comparisons may be unreliable."
            )

    return warnings


def run_ab_test(
    conn: sqlite3.Connection,
    pattern_ids: list[int],
    tickers: list[str],
    start_date: str,
    end_date: str,
    all_bars: dict[str, list[dict]],
    event_configs: dict[int, tuple[RuleSet, EventDetectionConfig]],
) -> ABTestResult:
    """Run an A/B test comparing multiple pattern variants on identical data.

    Args:
        conn: Database connection
        pattern_ids: List of pattern IDs to compare (2+)
        tickers: Tickers to test against
        start_date: Backtest period start
        end_date: Backtest period end
        all_bars: Pre-fetched price bars keyed by ticker
        event_configs: Mapping of pattern_id -> (rule_set, event_config)

    Returns:
        ABTestResult with variant reports, pairwise comparisons, and best variant
    """
    from finance_agent.patterns.backtest import run_multi_ticker_news_dip_backtest

    # Run multi-ticker backtest for each variant
    variant_reports: list[AggregatedBacktestReport] = []
    for pid in pattern_ids:
        rule_set, event_config = event_configs[pid]
        agg_report = run_multi_ticker_news_dip_backtest(
            pattern_id=pid,
            rule_set=rule_set,
            all_bars=all_bars,
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            event_config=event_config,
        )
        variant_reports.append(agg_report)

    # Compute all pairwise comparisons
    comparisons: list[PairwiseComparison] = []
    for i in range(len(variant_reports)):
        for j in range(i + 1, len(variant_reports)):
            a = variant_reports[i]
            b = variant_reports[j]

            a_report = a.combined_report
            b_report = b.combined_report

            # Fisher's exact test on win rates
            wins_a = a_report.win_count
            losses_a = a_report.trade_count - wins_a
            wins_b = b_report.win_count
            losses_b = b_report.trade_count - wins_b

            wr_p = fisher_exact_test(wins_a, losses_a, wins_b, losses_b)

            # Welch's t-test on per-trade returns
            returns_a = [t.return_pct for t in a_report.trades]
            returns_b = [t.return_pct for t in b_report.trades]
            ar_p = welch_ttest(returns_a, returns_b)

            comparisons.append(PairwiseComparison(
                variant_a_id=a.pattern_id,
                variant_b_id=b.pattern_id,
                win_rate_p_value=wr_p,
                win_rate_significant=wr_p < 0.05,
                avg_return_p_value=ar_p,
                avg_return_significant=ar_p < 0.05,
            ))

    # Determine best variant by win rate, tie-break by avg return
    best_idx = 0
    for i, vr in enumerate(variant_reports):
        best = variant_reports[best_idx]
        cr = vr.combined_report
        br = best.combined_report
        best_wr = br.win_count / br.trade_count if br.trade_count > 0 else 0
        curr_wr = cr.win_count / cr.trade_count if cr.trade_count > 0 else 0
        if curr_wr > best_wr or (curr_wr == best_wr and cr.avg_return_pct > br.avg_return_pct):
            best_idx = i

    best_id = pattern_ids[best_idx]

    # Check if best is significantly better than second-best
    best_is_significant = False
    if len(variant_reports) >= 2:
        # Find the comparison between best and next-best
        for comp in comparisons:
            if best_id in (comp.variant_a_id, comp.variant_b_id):
                if comp.win_rate_significant or comp.avg_return_significant:
                    best_is_significant = True
                    break

    warnings = generate_sample_size_warnings(variant_reports)

    return ABTestResult(
        pattern_ids=pattern_ids,
        tickers=tickers,
        date_range_start=start_date,
        date_range_end=end_date,
        variant_reports=variant_reports,
        comparisons=comparisons,
        best_variant_id=best_id,
        best_is_significant=best_is_significant,
        sample_size_warnings=warnings,
    )
