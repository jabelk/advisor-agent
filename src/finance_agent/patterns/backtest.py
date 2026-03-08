"""Backtest engine: evaluate pattern rules against historical price data."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta

from finance_agent.patterns.models import (
    BacktestReport,
    BacktestTrade,
    CoveredCallCycle,
    CoveredCallReport,
    DetectedEvent,
    EventDetectionConfig,
    RegimeConfig,
    RegimePeriod,
    RuleSet,
)

logger = logging.getLogger(__name__)

# Minimum trades for statistical significance
MIN_SAMPLE_SIZE = 30

# Minimum monthly cycles for covered call significance
MIN_CC_CYCLES = 6

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


def run_covered_call_backtest(
    pattern_id: int,
    rule_set: RuleSet,
    bars: list[dict],
    ticker: str,
    start_date: str,
    end_date: str,
    shares: int = 100,
) -> CoveredCallReport:
    """Run a covered call backtest: simulate monthly sell-call cycles over historical data.

    Iterates through monthly cycles:
    1. At cycle start, calculate strike from OTM percentage
    2. Estimate premium via Black-Scholes with historical volatility
    3. Simulate through expiration checking for assignment, early close, or roll

    Args:
        pattern_id: ID of the pattern being backtested
        rule_set: Parsed trading rules (must be sell_call action type)
        bars: Historical price bars for the ticker (list of dicts with close, high, low, bar_timestamp)
        ticker: Stock ticker symbol
        start_date: Backtest start date (YYYY-MM-DD)
        end_date: Backtest end date (YYYY-MM-DD)
        shares: Number of shares owned (default: 100)

    Returns:
        CoveredCallReport with cycle-by-cycle results and aggregate metrics
    """
    from finance_agent.patterns.option_pricing import (
        calculate_historical_volatility,
        estimate_call_premium,
        estimate_premium_at_age,
    )

    if not bars:
        return _empty_cc_report(pattern_id, ticker, shares, start_date, end_date)

    # Extract parameters from rule_set
    action = rule_set.action
    exit_criteria = rule_set.exit_criteria

    # Strike distance: derive from strike_strategy
    strike_pct_otm = _get_otm_pct(action)
    expiration_days = action.expiration_days  # typically 30
    premium_profit_target = exit_criteria.profit_target_pct / 100.0  # e.g., 0.50 for 50%
    roll_threshold_dte = expiration_days - (exit_criteria.max_hold_days or expiration_days)
    if roll_threshold_dte <= 0:
        roll_threshold_dte = 21  # default

    contracts = shares // 100

    # Filter bars to date range
    filtered_bars = [
        b for b in bars
        if start_date <= b["bar_timestamp"][:10] <= end_date
    ]

    if len(filtered_bars) < 22:  # Need at least ~1 month of data
        return _empty_cc_report(pattern_id, ticker, shares, start_date, end_date)

    cycles: list[CoveredCallCycle] = []
    cycle_number = 0
    i = 0  # Index into filtered_bars

    while i < len(filtered_bars) - 1:
        cycle_number += 1
        cycle_start_idx = i
        cycle_start_bar = filtered_bars[i]
        stock_entry_price = cycle_start_bar["close"]
        cycle_start_date = cycle_start_bar["bar_timestamp"][:10]

        # Calculate historical volatility from bars up to this point
        # Use all available bars (not just filtered) for volatility calculation
        bars_up_to_now = [
            b for b in bars
            if b["bar_timestamp"][:10] <= cycle_start_date
        ]
        hist_vol = calculate_historical_volatility(bars_up_to_now, lookback_days=20)

        # Calculate strike price
        call_strike = stock_entry_price * (1 + strike_pct_otm)

        # Estimate premium
        call_premium_per_share = estimate_call_premium(
            spot_price=stock_entry_price,
            strike_price=call_strike,
            days_to_expiration=expiration_days,
            historical_volatility=hist_vol,
        )

        # Calculate expiration date
        exp_date = datetime.strptime(cycle_start_date, "%Y-%m-%d") + timedelta(days=expiration_days)
        call_expiration_date = exp_date.strftime("%Y-%m-%d")

        # Simulate through the cycle
        outcome = None
        cycle_end_idx = cycle_start_idx
        stock_price_at_exit = stock_entry_price
        days_in_cycle = 0

        for j in range(cycle_start_idx + 1, len(filtered_bars)):
            bar = filtered_bars[j]
            bar_date = bar["bar_timestamp"][:10]
            days_in_cycle += 1
            stock_price_at_exit = bar["close"]

            # Days to expiration
            bar_dt = datetime.strptime(bar_date, "%Y-%m-%d")
            dte = (exp_date - bar_dt).days

            # Check early close: premium profit target
            # Estimate current premium value using time decay
            current_premium = estimate_premium_at_age(
                initial_premium=call_premium_per_share,
                days_elapsed=days_in_cycle,
                total_days=expiration_days,
            )
            # Also factor in how far stock moved from strike (if stock dropped, premium drops more)
            if stock_price_at_exit < call_strike:
                # OTM — premium decays faster
                moneyness_factor = max(0.0, 1.0 - (call_strike - stock_price_at_exit) / call_strike)
                current_premium *= moneyness_factor

            premium_decay_pct = 1.0 - (current_premium / call_premium_per_share) if call_premium_per_share > 0 else 0
            if premium_decay_pct >= premium_profit_target:
                outcome = "closed_early"
                cycle_end_idx = j
                break

            # Check roll threshold
            if 0 < dte <= roll_threshold_dte:
                outcome = "rolled"
                cycle_end_idx = j
                break

            # Check expiration
            if dte <= 0 or bar_date >= call_expiration_date:
                if stock_price_at_exit >= call_strike:
                    outcome = "assigned"
                else:
                    outcome = "expired_worthless"
                cycle_end_idx = j
                break

            cycle_end_idx = j

        # If we ran out of bars without reaching expiration
        if outcome is None:
            if stock_price_at_exit >= call_strike:
                outcome = "assigned"
            else:
                outcome = "expired_worthless"

        cycle_end_date = filtered_bars[cycle_end_idx]["bar_timestamp"][:10]

        # Calculate returns
        premium_return_pct = (call_premium_per_share / stock_entry_price) * 100.0

        # Stock gain/loss
        stock_return = stock_price_at_exit - stock_entry_price
        if outcome == "assigned":
            # Cap stock gain at strike
            stock_return = min(stock_return, call_strike - stock_entry_price)

        total_return_per_share = call_premium_per_share + stock_return
        total_return_pct = (total_return_per_share / stock_entry_price) * 100.0

        # Capped upside: gains forfeited due to assignment
        capped_upside_pct = 0.0
        if outcome == "assigned" and stock_price_at_exit > call_strike:
            forfeited = stock_price_at_exit - call_strike
            capped_upside_pct = (forfeited / stock_entry_price) * 100.0

        cycles.append(CoveredCallCycle(
            ticker=ticker,
            cycle_number=cycle_number,
            stock_entry_price=stock_entry_price,
            call_strike=round(call_strike, 2),
            call_premium=round(call_premium_per_share * contracts * 100, 2),
            call_expiration_date=call_expiration_date,
            cycle_start_date=cycle_start_date,
            cycle_end_date=cycle_end_date,
            stock_price_at_exit=round(stock_price_at_exit, 2),
            outcome=outcome,
            premium_return_pct=round(premium_return_pct, 4),
            total_return_pct=round(total_return_pct, 4),
            capped_upside_pct=round(capped_upside_pct, 4),
            historical_volatility=round(hist_vol, 4),
        ))

        # Advance to next cycle start (day after cycle end)
        i = cycle_end_idx + 1

    # Aggregate metrics
    total_premium = sum(c.call_premium for c in cycles)
    avg_premium = total_premium / len(cycles) if cycles else 0.0
    assignment_count = sum(1 for c in cycles if c.outcome == "assigned")
    closed_early_count = sum(1 for c in cycles if c.outcome == "closed_early")
    rolled_count = sum(1 for c in cycles if c.outcome == "rolled")
    expired_count = sum(1 for c in cycles if c.outcome == "expired_worthless")

    # Annualized income yield
    if cycles and cycles[0].stock_entry_price > 0:
        total_days = (
            datetime.strptime(end_date, "%Y-%m-%d")
            - datetime.strptime(start_date, "%Y-%m-%d")
        ).days
        years = total_days / 365.0 if total_days > 0 else 1.0
        total_premium_per_share = sum(c.call_premium for c in cycles) / shares if shares > 0 else 0
        annualized_yield = (total_premium_per_share / cycles[0].stock_entry_price) * (1 / years) * 100
    else:
        annualized_yield = 0.0

    # Buy-and-hold comparison
    if filtered_bars:
        bh_start_price = filtered_bars[0]["close"]
        bh_end_price = filtered_bars[-1]["close"]
        buy_and_hold_return = ((bh_end_price - bh_start_price) / bh_start_price) * 100 if bh_start_price > 0 else 0.0
    else:
        buy_and_hold_return = 0.0

    # Covered call total return: sum of all cycle total returns
    cc_total_return = sum(c.total_return_pct or 0.0 for c in cycles)
    capped_upside_cost = sum(c.capped_upside_pct or 0.0 for c in cycles)
    # Convert capped upside % to dollars
    capped_upside_dollars = 0.0
    for c in cycles:
        if c.capped_upside_pct and c.capped_upside_pct > 0:
            capped_upside_dollars += (c.capped_upside_pct / 100.0) * c.stock_entry_price * shares

    sample_size_warning = len(cycles) < MIN_CC_CYCLES

    return CoveredCallReport(
        pattern_id=pattern_id,
        ticker=ticker,
        shares=shares,
        date_range_start=start_date,
        date_range_end=end_date,
        cycle_count=len(cycles),
        total_premium_collected=round(total_premium, 2),
        avg_premium_per_cycle=round(avg_premium, 2),
        annualized_income_yield_pct=round(annualized_yield, 2),
        assignment_count=assignment_count,
        assignment_frequency_pct=round(assignment_count / len(cycles) * 100, 1) if cycles else 0.0,
        closed_early_count=closed_early_count,
        rolled_count=rolled_count,
        expired_worthless_count=expired_count,
        buy_and_hold_return_pct=round(buy_and_hold_return, 2),
        covered_call_return_pct=round(cc_total_return, 2),
        capped_upside_cost=round(capped_upside_dollars, 2),
        sample_size_warning=sample_size_warning,
        cycles=cycles,
    )


def _get_otm_pct(action) -> float:
    """Get OTM percentage from strike strategy."""
    if action.strike_strategy.value == "otm_5":
        return 0.05
    elif action.strike_strategy.value == "otm_10":
        return 0.10
    elif action.strike_strategy.value == "itm_5":
        return -0.05
    elif action.strike_strategy.value == "atm":
        return 0.0
    elif action.strike_strategy.value == "custom" and action.custom_strike_offset_pct is not None:
        return action.custom_strike_offset_pct / 100.0
    return 0.05  # default 5% OTM


def _empty_cc_report(
    pattern_id: int, ticker: str, shares: int, start_date: str, end_date: str,
) -> CoveredCallReport:
    """Return an empty covered call report when no data is available."""
    return CoveredCallReport(
        pattern_id=pattern_id,
        ticker=ticker,
        shares=shares,
        date_range_start=start_date,
        date_range_end=end_date,
        cycle_count=0,
        total_premium_collected=0.0,
        avg_premium_per_cycle=0.0,
        annualized_income_yield_pct=0.0,
        assignment_count=0,
        assignment_frequency_pct=0.0,
        closed_early_count=0,
        rolled_count=0,
        expired_worthless_count=0,
        buy_and_hold_return_pct=0.0,
        covered_call_return_pct=0.0,
        capped_upside_cost=0.0,
        sample_size_warning=True,
        cycles=[],
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


def run_news_dip_backtest(
    pattern_id: int,
    rule_set: RuleSet,
    bars: list[dict],
    ticker: str,
    start_date: str,
    end_date: str,
    event_config: EventDetectionConfig,
) -> tuple[BacktestReport, list[dict]]:
    """Run a news-dip backtest: detect spike events then look for pullback entries.

    Uses either manually-specified events or automatic spike detection to identify
    trigger dates, then applies the rule_set's entry/exit logic to simulate trades.

    Args:
        pattern_id: ID of the pattern being backtested
        rule_set: Parsed trading rules (entry signal, exit criteria, action)
        bars: Historical price bars for the ticker (list of dicts with close, high, low, volume, bar_timestamp)
        ticker: Stock ticker symbol
        start_date: Backtest start date (YYYY-MM-DD)
        end_date: Backtest end date (YYYY-MM-DD)
        event_config: Configuration for event detection (thresholds, manual events, etc.)

    Returns:
        Tuple of (BacktestReport, no_entry_events) where no_entry_events is a list of dicts
        with keys: date, spike_pct, volume_multiple, reason
    """
    from finance_agent.patterns.event_detection import (
        detect_spike_events,
        manual_events_to_detected,
    )

    # Detect events: manual overrides automatic detection
    if event_config.manual_events:
        events: list[DetectedEvent] = manual_events_to_detected(
            event_config.manual_events, bars, ticker,
        )
    else:
        events = detect_spike_events(bars, ticker, event_config)

    trades: list[BacktestTrade] = []
    no_entry_events: list[dict] = []

    for event in events:
        # Find bar index matching the event date
        trigger_idx = _find_bar_index_by_date(bars, event.date)
        if trigger_idx is None:
            continue

        # Look for a dip entry within the window
        entry_idx = _find_entry(rule_set, bars, trigger_idx)

        if entry_idx is not None:
            trade = _execute_simulated_trade(ticker, rule_set, bars, entry_idx)
            if trade:
                trades.append(trade)
        else:
            # Track as a no-entry event
            pullback_pct = rule_set.entry_signal.value
            window_days = rule_set.entry_signal.window_days
            no_entry_events.append({
                "date": event.date,
                "spike_pct": event.price_change_pct,
                "volume_multiple": event.volume_multiple,
                "reason": f"No {pullback_pct}% pullback within {window_days}-day window",
            })

    # Sort trades by trigger date
    trades.sort(key=lambda t: t.trigger_date)

    # Calculate aggregate metrics
    trigger_count = len(events)
    trade_count = len(trades)
    win_count = sum(1 for t in trades if t.return_pct > 0)
    total_return_pct = sum(t.return_pct for t in trades)
    avg_return_pct = total_return_pct / trade_count if trade_count > 0 else 0.0
    max_drawdown_pct = _calculate_max_drawdown(trades)
    sharpe_ratio = _calculate_sharpe(trades) if trade_count >= 2 else None

    # Regime analysis
    from finance_agent.patterns.regime import detect_time_based_regimes
    regimes = detect_time_based_regimes(trades) if trades else []

    report = BacktestReport(
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
        sample_size_warning=trade_count < 5,
        regimes=regimes,
        trades=trades,
    )

    return report, no_entry_events
