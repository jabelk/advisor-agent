"""Time-based regime analysis for event-driven patterns.

Uses rolling time windows (default 63 trading days / ~3 months) to detect
performance regime shifts. Labels: strong (>= 60% win rate), weak (40-59%),
breakdown (< 40%).
"""

from __future__ import annotations

import logging
from datetime import datetime

from finance_agent.patterns.models import BacktestTrade, RegimeConfig, RegimePeriod

logger = logging.getLogger(__name__)


def detect_time_based_regimes(
    trades: list[BacktestTrade],
    config: RegimeConfig | None = None,
) -> list[RegimePeriod]:
    """Detect performance regimes using time-based rolling windows.

    Unlike the existing trade-count-based detect_regimes() in backtest.py,
    this uses calendar-time windows which work better for event-driven patterns
    where trades may be sparse and unevenly spaced.

    Args:
        trades: List of backtest trades sorted by trigger_date
        config: Regime detection configuration (uses defaults if None)

    Returns:
        List of RegimePeriod objects with labels and metrics
    """
    if config is None:
        config = RegimeConfig()

    if len(trades) < config.min_trades_for_regime:
        logger.info(
            "Only %d trades (need %d) — skipping regime analysis",
            len(trades),
            config.min_trades_for_regime,
        )
        return []

    if not trades:
        return []

    # Sort trades by trigger date
    sorted_trades = sorted(trades, key=lambda t: t.trigger_date)

    # Get the full date range
    first_date = datetime.strptime(sorted_trades[0].trigger_date, "%Y-%m-%d")
    last_date = datetime.strptime(sorted_trades[-1].trigger_date, "%Y-%m-%d")

    total_days = (last_date - first_date).days
    if total_days < config.window_trading_days:
        # Not enough time span for even one window — treat as single regime
        return [_build_regime(sorted_trades, config)]

    # Slide window across the date range
    raw_regimes: list[tuple[str, str, str, list[BacktestTrade]]] = []  # (start, end, label, trades)

    # Use calendar days for window boundaries, step by half-window for overlap
    step_days = max(1, config.window_trading_days // 2)
    from datetime import timedelta

    window_start = first_date
    while window_start <= last_date:
        window_end = window_start + timedelta(days=config.window_trading_days)

        # Collect trades in this window
        window_trades = [
            t
            for t in sorted_trades
            if window_start <= datetime.strptime(t.trigger_date, "%Y-%m-%d") < window_end
        ]

        if len(window_trades) >= config.min_trades_per_window:
            win_rate = sum(1 for t in window_trades if t.return_pct > 0) / len(window_trades)
            label = _classify_win_rate(win_rate, config)
            raw_regimes.append(
                (
                    window_start.strftime("%Y-%m-%d"),
                    min(window_end, last_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                    label,
                    window_trades,
                )
            )

        window_start += timedelta(days=step_days)

    if not raw_regimes:
        return []

    # Merge adjacent windows with the same label
    merged: list[RegimePeriod] = []
    current_start = raw_regimes[0][0]
    current_end = raw_regimes[0][1]
    current_label = raw_regimes[0][2]
    current_trades: list[BacktestTrade] = list(raw_regimes[0][3])

    for i in range(1, len(raw_regimes)):
        _, w_end, w_label, w_trades = raw_regimes[i]

        if w_label == current_label:
            # Extend current regime
            current_end = w_end
            # Add new trades not already included
            existing_dates = {t.trigger_date for t in current_trades}
            for t in w_trades:
                if t.trigger_date not in existing_dates:
                    current_trades.append(t)
                    existing_dates.add(t.trigger_date)
        else:
            # Save current regime and start new one
            merged.append(
                _build_regime_from_window(
                    current_start,
                    current_end,
                    current_label,
                    current_trades,
                    config,
                )
            )
            current_start = raw_regimes[i][0]
            current_end = w_end
            current_label = w_label
            current_trades = list(w_trades)

    # Save last regime
    merged.append(
        _build_regime_from_window(
            current_start,
            current_end,
            current_label,
            current_trades,
            config,
        )
    )

    return merged


def _classify_win_rate(win_rate: float, config: RegimeConfig) -> str:
    """Classify a win rate into a regime label."""
    if win_rate >= config.strong_threshold:
        return "strong"
    elif win_rate >= config.weak_threshold:
        return "weak"
    else:
        return "breakdown"


def _build_regime(trades: list[BacktestTrade], config: RegimeConfig) -> RegimePeriod:
    """Build a single RegimePeriod from a list of trades."""
    win_rate = sum(1 for t in trades if t.return_pct > 0) / len(trades) if trades else 0.0
    avg_return = sum(t.return_pct for t in trades) / len(trades) if trades else 0.0
    label = _classify_win_rate(win_rate, config)
    return RegimePeriod(
        start_date=trades[0].trigger_date if trades else "",
        end_date=trades[-1].trigger_date if trades else "",
        win_rate=win_rate,
        avg_return_pct=avg_return,
        trade_count=len(trades),
        label=label,
    )


def _build_regime_from_window(
    start: str,
    end: str,
    label: str,
    trades: list[BacktestTrade],
    config: RegimeConfig,
) -> RegimePeriod:
    """Build a RegimePeriod from merged window data."""
    win_rate = sum(1 for t in trades if t.return_pct > 0) / len(trades) if trades else 0.0
    avg_return = sum(t.return_pct for t in trades) / len(trades) if trades else 0.0
    return RegimePeriod(
        start_date=start,
        end_date=end,
        win_rate=win_rate,
        avg_return_pct=avg_return,
        trade_count=len(trades),
        label=label,
    )
