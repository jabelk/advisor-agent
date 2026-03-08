"""Backtest engine: evaluate pattern rules against historical price data."""

from __future__ import annotations

import logging
import math
from datetime import datetime

from finance_agent.patterns.models import (
    BacktestReport,
    BacktestTrade,
    RegimePeriod,
    RuleSet,
)

logger = logging.getLogger(__name__)

# Minimum trades for statistical significance
MIN_SAMPLE_SIZE = 30

# Rolling window size for regime detection (in trades)
REGIME_WINDOW_SIZE = 10


def run_backtest(
    pattern_id: int,
    rule_set: RuleSet,
    bars_by_ticker: dict[str, list[dict]],
    start_date: str,
    end_date: str,
) -> BacktestReport:
    """Run a backtest of the given rule set against historical price data.

    Args:
        pattern_id: ID of the pattern being backtested
        rule_set: Parsed trading rules
        bars_by_ticker: Historical bars keyed by ticker symbol
        start_date: Backtest start date (YYYY-MM-DD)
        end_date: Backtest end date (YYYY-MM-DD)

    Returns:
        BacktestReport with performance metrics and regime analysis
    """
    all_trades: list[BacktestTrade] = []

    for ticker, bars in bars_by_ticker.items():
        if not bars:
            continue

        # Filter to sector if specified
        if rule_set.sector_filter:
            # For now, rely on the caller to filter tickers by sector
            pass

        trades = _simulate_pattern(ticker, rule_set, bars)
        all_trades.extend(trades)

    # Sort trades by trigger date
    all_trades.sort(key=lambda t: t.trigger_date)

    # Calculate aggregate metrics
    trade_count = len(all_trades)
    trigger_count = trade_count  # Each trigger that meets entry = one trade
    win_count = sum(1 for t in all_trades if t.return_pct > 0)
    total_return_pct = sum(t.return_pct for t in all_trades)
    avg_return_pct = total_return_pct / trade_count if trade_count > 0 else 0.0
    max_drawdown_pct = _calculate_max_drawdown(all_trades)
    sharpe_ratio = _calculate_sharpe(all_trades) if trade_count >= 2 else None

    # Regime detection
    regimes = detect_regimes(all_trades) if trade_count >= REGIME_WINDOW_SIZE else []

    return BacktestReport(
        pattern_id=pattern_id,
        date_range_start=start_date,
        date_range_end=end_date,
        trigger_count=trigger_count,
        trade_count=trade_count,
        win_count=win_count,
        total_return_pct=total_return_pct,
        avg_return_pct=avg_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        sharpe_ratio=sharpe_ratio,
        sample_size_warning=trade_count < MIN_SAMPLE_SIZE,
        regimes=regimes,
        trades=all_trades,
    )


def _simulate_pattern(
    ticker: str,
    rule_set: RuleSet,
    bars: list[dict],
) -> list[BacktestTrade]:
    """Simulate a pattern against a single ticker's price history."""
    trades: list[BacktestTrade] = []
    i = 0

    while i < len(bars) - 1:
        bar = bars[i]

        # Check trigger conditions
        if _check_trigger(rule_set, bars, i):
            # Look for entry signal within the window
            entry_idx = _find_entry(rule_set, bars, i)
            if entry_idx is not None and entry_idx < len(bars):
                # Simulate the trade
                trade = _execute_simulated_trade(ticker, rule_set, bars, entry_idx)
                if trade:
                    trades.append(trade)
                    # Skip ahead past this trade
                    i = _find_bar_index_by_date(bars, trade.exit_date) or (i + 1)
                    continue

        i += 1

    return trades


def _check_trigger(
    rule_set: RuleSet,
    bars: list[dict],
    idx: int,
) -> bool:
    """Check if all trigger conditions are met at bar index."""
    if idx < 1:
        return False

    bar = bars[idx]
    prev_bar = bars[idx - 1]

    for condition in rule_set.trigger_conditions:
        if condition.field == "price_change_pct":
            if prev_bar["close"] == 0:
                return False
            change_pct = ((bar["close"] - prev_bar["close"]) / prev_bar["close"]) * 100

            threshold = float(condition.value)
            if condition.operator == "gte" and change_pct < threshold:
                return False
            elif condition.operator == "lte" and change_pct > threshold:
                return False

        elif condition.field == "volume_spike":
            # Compare to average volume over prior 20 bars
            lookback = max(0, idx - 20)
            avg_vol = sum(b["volume"] for b in bars[lookback:idx]) / max(1, idx - lookback)
            if avg_vol == 0:
                return False
            spike_ratio = bar["volume"] / avg_vol
            threshold = float(condition.value)
            if condition.operator == "gte" and spike_ratio < threshold:
                return False

        elif condition.field == "sector":
            # Sector filtering is handled at the caller level
            pass

        elif condition.field == "news_sentiment":
            # Qualitative triggers can't be evaluated in backtesting
            # For backtest purposes, we skip qualitative conditions
            # and note this in the report
            if rule_set.trigger_type == "qualitative":
                # In backtest, we only evaluate quantitative conditions
                pass

    return True


def _find_entry(
    rule_set: RuleSet,
    bars: list[dict],
    trigger_idx: int,
) -> int | None:
    """Find the entry point within the window after a trigger."""
    entry = rule_set.entry_signal
    window_end = min(trigger_idx + entry.window_days + 1, len(bars))
    trigger_high = bars[trigger_idx]["high"]

    for j in range(trigger_idx + 1, window_end):
        bar = bars[j]

        if entry.condition == "pullback_pct":
            pullback_pct = ((trigger_high - bar["low"]) / trigger_high) * 100
            threshold = float(entry.value)
            if pullback_pct >= threshold:
                return j

        elif entry.condition == "price_below":
            threshold = float(entry.value)
            if bar["low"] <= threshold:
                return j

        elif entry.condition == "time_delay":
            delay_days = int(entry.value)
            if (j - trigger_idx) >= delay_days:
                return j

    return None


def _execute_simulated_trade(
    ticker: str,
    rule_set: RuleSet,
    bars: list[dict],
    entry_idx: int,
) -> BacktestTrade | None:
    """Simulate a trade from entry to exit."""
    entry_bar = bars[entry_idx]
    entry_price = entry_bar["close"]

    if entry_price <= 0:
        return None

    exit_criteria = rule_set.exit_criteria
    action = rule_set.action

    # Find exit
    exit_price = entry_price
    exit_idx = entry_idx

    max_hold = exit_criteria.max_hold_days or 252  # Default to 1 year

    for k in range(entry_idx + 1, min(entry_idx + max_hold + 1, len(bars))):
        bar = bars[k]

        # Check profit target
        change_pct = ((bar["high"] - entry_price) / entry_price) * 100
        if change_pct >= exit_criteria.profit_target_pct:
            exit_price = entry_price * (1 + exit_criteria.profit_target_pct / 100)
            exit_idx = k
            break

        # Check stop loss
        loss_pct = ((entry_price - bar["low"]) / entry_price) * 100
        if loss_pct >= exit_criteria.stop_loss_pct:
            exit_price = entry_price * (1 - exit_criteria.stop_loss_pct / 100)
            exit_idx = k
            break

        # Update exit to current close (in case we hit max hold)
        exit_price = bar["close"]
        exit_idx = k

    # Calculate return
    raw_return_pct = ((exit_price - entry_price) / entry_price) * 100

    # For options, apply leverage approximation
    is_options = "call" in action.action_type.value or "put" in action.action_type.value
    if is_options:
        return_pct = _estimate_options_return(
            raw_return_pct, action.action_type.value, action.expiration_days
        )
        option_details = {
            "type": action.action_type.value,
            "strike_strategy": action.strike_strategy.value,
            "expiration_days": action.expiration_days,
            "underlying_return_pct": raw_return_pct,
        }
    else:
        return_pct = raw_return_pct
        option_details = None

    return BacktestTrade(
        ticker=ticker,
        trigger_date=bars[max(0, entry_idx - 1)]["bar_timestamp"][:10],
        entry_date=entry_bar["bar_timestamp"][:10],
        entry_price=entry_price,
        exit_date=bars[exit_idx]["bar_timestamp"][:10],
        exit_price=exit_price,
        return_pct=return_pct,
        action_type=action.action_type.value,
        option_details=option_details,
    )


def _estimate_options_return(
    underlying_return_pct: float,
    option_type: str,
    expiration_days: int,
) -> float:
    """Estimate options return from underlying price movement.

    Uses a simplified delta approximation:
    - ATM calls/puts have ~0.5 delta
    - Options leverage is roughly 3-5x for ATM with 30-day expiration
    - Longer expirations have less time decay impact
    """
    # Approximate leverage based on expiration
    if expiration_days <= 7:
        leverage = 8.0  # Weekly options, high leverage but high decay
    elif expiration_days <= 30:
        leverage = 5.0  # Monthly options
    elif expiration_days <= 60:
        leverage = 3.5
    else:
        leverage = 2.5

    if "call" in option_type:
        return underlying_return_pct * leverage
    elif "put" in option_type:
        return -underlying_return_pct * leverage
    return underlying_return_pct


def _calculate_max_drawdown(trades: list[BacktestTrade]) -> float:
    """Calculate maximum drawdown from a series of trades."""
    if not trades:
        return 0.0

    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0

    for trade in trades:
        cumulative += trade.return_pct
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd

    return max_dd


def _calculate_sharpe(trades: list[BacktestTrade], risk_free_rate: float = 0.0) -> float | None:
    """Calculate Sharpe ratio from trade returns."""
    if len(trades) < 2:
        return None

    returns = [t.return_pct for t in trades]
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
    std_dev = math.sqrt(variance) if variance > 0 else 0

    if std_dev == 0:
        return None

    return (mean_return - risk_free_rate) / std_dev


def detect_regimes(trades: list[BacktestTrade]) -> list[RegimePeriod]:
    """Detect regime changes in pattern performance using rolling window analysis.

    Identifies periods where win rate or average return shifted >50% from overall average.
    """
    if len(trades) < REGIME_WINDOW_SIZE:
        return []

    overall_win_rate = sum(1 for t in trades if t.return_pct > 0) / len(trades)
    overall_avg_return = sum(t.return_pct for t in trades) / len(trades)

    regimes: list[RegimePeriod] = []
    current_regime_start = 0
    current_label = _classify_regime(trades[:REGIME_WINDOW_SIZE], overall_win_rate, overall_avg_return)

    for i in range(1, len(trades) - REGIME_WINDOW_SIZE + 1):
        window = trades[i:i + REGIME_WINDOW_SIZE]
        label = _classify_regime(window, overall_win_rate, overall_avg_return)

        if label != current_label:
            # Regime changed — save the previous regime
            regime_trades = trades[current_regime_start:i]
            if regime_trades:
                regime_wr = sum(1 for t in regime_trades if t.return_pct > 0) / len(regime_trades)
                regime_avg = sum(t.return_pct for t in regime_trades) / len(regime_trades)
                regimes.append(RegimePeriod(
                    start_date=regime_trades[0].trigger_date,
                    end_date=regime_trades[-1].trigger_date,
                    win_rate=regime_wr,
                    avg_return_pct=regime_avg,
                    trade_count=len(regime_trades),
                    label=current_label,
                ))
            current_regime_start = i
            current_label = label

    # Save the last regime
    regime_trades = trades[current_regime_start:]
    if regime_trades:
        regime_wr = sum(1 for t in regime_trades if t.return_pct > 0) / len(regime_trades)
        regime_avg = sum(t.return_pct for t in regime_trades) / len(regime_trades)
        regimes.append(RegimePeriod(
            start_date=regime_trades[0].trigger_date,
            end_date=regime_trades[-1].trigger_date,
            win_rate=regime_wr,
            avg_return_pct=regime_avg,
            trade_count=len(regime_trades),
            label=current_label,
        ))

    return regimes


def _classify_regime(
    window_trades: list[BacktestTrade],
    overall_win_rate: float,
    overall_avg_return: float,
) -> str:
    """Classify a window of trades as strong, normal, weak, or breakdown."""
    if not window_trades:
        return "normal"

    win_rate = sum(1 for t in window_trades if t.return_pct > 0) / len(window_trades)
    avg_return = sum(t.return_pct for t in window_trades) / len(window_trades)

    # Compare to overall averages
    wr_delta = (win_rate - overall_win_rate) / max(overall_win_rate, 0.01)
    ret_delta = (avg_return - overall_avg_return) / max(abs(overall_avg_return), 0.01)

    if wr_delta > 0.5 or ret_delta > 0.5:
        return "strong"
    elif wr_delta < -0.5 or ret_delta < -0.5:
        if avg_return < 0:
            return "breakdown"
        return "weak"
    return "normal"


def _find_bar_index_by_date(bars: list[dict], date_str: str) -> int | None:
    """Find the index of a bar by its date."""
    for i, bar in enumerate(bars):
        if bar["bar_timestamp"][:10] >= date_str:
            return i
    return None
