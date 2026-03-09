"""Markdown report generation for backtest and A/B test results."""

from __future__ import annotations

from datetime import date
from pathlib import Path


def export_backtest_markdown(
    pattern: dict,
    backtest: dict,
    trades: list[dict],
) -> str:
    """Generate a markdown report for backtest results.

    Args:
        pattern: Pattern row dict (name, description, rule_set_json)
        backtest: Backtest result row dict
        trades: List of trade row dicts

    Returns:
        Formatted markdown string
    """
    lines: list[str] = []

    pattern_name = pattern.get("name", f"Pattern #{pattern.get('id', '?')}")
    pattern_id = pattern.get("id", "?")
    today = date.today().isoformat()

    lines.append(f"# Backtest Report: Pattern #{pattern_id} -- {pattern_name}")
    lines.append("")
    lines.append(f"**Generated**: {today}")
    lines.append(f"**Pattern**: {pattern_name} (#{pattern_id})")
    lines.append(
        f"**Date Range**: {backtest.get('date_range_start', '')} to {backtest.get('date_range_end', '')}"
    )
    lines.append("")

    # Pattern description
    description = pattern.get("description", "")
    if description:
        lines.append("## Pattern Description")
        lines.append("")
        lines.append(description)
        lines.append("")

    # Aggregate results
    lines.append("## Aggregate Results")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")

    trigger_count = backtest.get("trigger_count", 0)
    trade_count = backtest.get("trade_count", 0)
    win_count = backtest.get("win_count", 0)
    total_return = backtest.get("total_return_pct", 0.0)
    avg_return = backtest.get("avg_return_pct", 0.0)
    max_drawdown = backtest.get("max_drawdown_pct", 0.0)
    sharpe = backtest.get("sharpe_ratio")

    lines.append(f"| Total Events | {trigger_count} |")
    lines.append(f"| Total Trades | {trade_count} |")
    if trade_count > 0:
        wr = f"{win_count / trade_count * 100:.1f}% ({win_count}/{trade_count})"
        lines.append(f"| Win Rate | {wr} |")
        sign = "+" if avg_return >= 0 else ""
        lines.append(f"| Avg Return | {sign}{avg_return:.1f}% |")
        total_sign = "+" if total_return >= 0 else ""
        lines.append(f"| Total Return | {total_sign}{total_return:.1f}% |")
        lines.append(f"| Max Drawdown | -{max_drawdown:.1f}% |")
        if sharpe is not None:
            lines.append(f"| Sharpe Ratio | {sharpe:.2f} |")
    lines.append("")

    # Trade log
    if trades:
        lines.append("## Trade Log")
        lines.append("")
        lines.append("| # | Ticker | Trigger | Entry | Exit | Return |")
        lines.append("|---|--------|---------|-------|------|--------|")
        for i, trade in enumerate(trades, 1):
            ticker = trade.get("ticker", "")
            trigger = trade.get("trigger_date", "")
            entry = trade.get("entry_date", "")
            entry_price = trade.get("entry_price", 0)
            exit_d = trade.get("exit_date", "")
            exit_price = trade.get("exit_price", 0)
            ret = trade.get("return_pct", 0)
            ret_sign = "+" if ret >= 0 else ""
            lines.append(
                f"| {i} | {ticker} | {trigger} | {entry} @ ${entry_price:.2f} "
                f"| {exit_d} @ ${exit_price:.2f} | {ret_sign}{ret:.1f}% |"
            )
        lines.append("")

    return "\n".join(lines)


def export_ab_test_markdown(
    ab_result,
    pattern_names: dict[int, str],
) -> str:
    """Generate a markdown report for A/B test results.

    Args:
        ab_result: ABTestResult object
        pattern_names: Mapping of pattern_id -> name

    Returns:
        Formatted markdown string
    """
    from finance_agent.patterns.stats import format_significance

    lines: list[str] = []
    today = date.today().isoformat()

    ids_str = ", ".join(f"#{pid}" for pid in ab_result.pattern_ids)
    lines.append(f"# A/B Test Report: Patterns {ids_str}")
    lines.append("")
    lines.append(f"**Generated**: {today}")
    lines.append(f"**Date Range**: {ab_result.date_range_start} to {ab_result.date_range_end}")
    lines.append(f"**Tickers**: {', '.join(ab_result.tickers)}")
    lines.append("")

    # Variant metrics
    lines.append("## Variant Metrics")
    lines.append("")
    lines.append("| ID | Name | Events | Trades | Win Rate | Avg Return |")
    lines.append("|----|------|--------|--------|----------|------------|")
    for vr in ab_result.variant_reports:
        cr = vr.combined_report
        name = pattern_names.get(vr.pattern_id, "")
        wr = f"{cr.win_count / cr.trade_count * 100:.1f}%" if cr.trade_count > 0 else "—"
        sign = "+" if cr.avg_return_pct >= 0 else ""
        ar = f"{sign}{cr.avg_return_pct:.1f}%" if cr.trade_count > 0 else "—"
        lines.append(
            f"| {vr.pattern_id} | {name} | {cr.trigger_count} | {cr.trade_count} | {wr} | {ar} |"
        )
    lines.append("")

    # Statistical significance
    lines.append("## Statistical Significance")
    lines.append("")
    lines.append("| Comparison | Win Rate | Avg Return |")
    lines.append("|------------|----------|------------|")
    for comp in ab_result.comparisons:
        label = f"#{comp.variant_a_id} vs #{comp.variant_b_id}"
        wr_str = f"p={comp.win_rate_p_value:.2f} {format_significance(comp.win_rate_p_value)}"
        ar_str = f"p={comp.avg_return_p_value:.2f} {format_significance(comp.avg_return_p_value)}"
        lines.append(f"| {label} | {wr_str} | {ar_str} |")
    lines.append("")

    # Result
    lines.append("## Result")
    lines.append("")
    best_name = pattern_names.get(ab_result.best_variant_id, "")
    lines.append(f"**Best variant**: #{ab_result.best_variant_id} ({best_name})")
    if ab_result.best_is_significant:
        lines.append("**Advantage**: Statistically significant (p < 0.05)")
    else:
        lines.append("**Advantage**: Not statistically significant (p > 0.05)")
    lines.append("")

    # Warnings
    if ab_result.sample_size_warnings:
        for w in ab_result.sample_size_warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def generate_export_path(
    pattern_id: int,
    report_type: str = "backtest",
    output_dir: str | None = None,
) -> str:
    """Generate an export file path with overwrite protection.

    Args:
        pattern_id: Pattern ID
        report_type: 'backtest' or 'ab-test'
        output_dir: Directory for output (default: current directory)

    Returns:
        File path string with numeric suffix if needed to avoid overwriting
    """
    today = date.today().isoformat()
    base_name = f"pattern-{pattern_id}-{report_type}-{today}"
    directory = Path(output_dir) if output_dir else Path.cwd()

    candidate = directory / f"{base_name}.md"
    if not candidate.exists():
        return str(candidate)

    # Append numeric suffix
    suffix = 1
    while True:
        candidate = directory / f"{base_name}-{suffix}.md"
        if not candidate.exists():
            return str(candidate)
        suffix += 1
