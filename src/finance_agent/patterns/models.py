"""Pydantic models for Pattern Lab: pattern definitions, rule sets, and results."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class TriggerType(StrEnum):
    """Whether a trigger is purely data-driven or requires human judgment."""

    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"


class PatternStatus(StrEnum):
    """Lifecycle states for a trading pattern."""

    DRAFT = "draft"
    BACKTESTED = "backtested"
    PAPER_TRADING = "paper_trading"
    RETIRED = "retired"


class ActionType(StrEnum):
    """What kind of position to take."""

    BUY_SHARES = "buy_shares"
    SELL_SHARES = "sell_shares"
    BUY_CALL = "buy_call"
    BUY_PUT = "buy_put"
    SELL_CALL = "sell_call"
    SELL_PUT = "sell_put"


class StrikeStrategy(StrEnum):
    """How to select option strike price."""

    ATM = "atm"
    OTM_5 = "otm_5"
    OTM_10 = "otm_10"
    ITM_5 = "itm_5"
    CUSTOM = "custom"


class TriggerCondition(BaseModel):
    """A single condition that must be met for a pattern to trigger."""

    field: str = Field(description="What to evaluate: 'price_change_pct', 'volume_spike', 'news_sentiment', 'sector'")
    operator: str = Field(description="Comparison: 'gte', 'lte', 'eq', 'contains'")
    value: str = Field(description="Threshold value as string (e.g., '5.0', 'healthcare', 'positive')")
    description: str = Field(description="Human-readable description of this condition")


class EntrySignal(BaseModel):
    """When to enter a position after the trigger fires."""

    condition: str = Field(description="What to watch for: 'pullback_pct', 'price_below', 'time_delay'")
    value: str = Field(description="Threshold (e.g., '2.0' for 2% pullback)")
    window_days: int = Field(default=2, description="How many trading days to wait for entry signal")
    description: str = Field(description="Human-readable description")


class TradeAction(BaseModel):
    """What to do when the entry signal fires."""

    action_type: ActionType = Field(description="Type of trade")
    strike_strategy: StrikeStrategy = Field(default=StrikeStrategy.ATM, description="Option strike selection")
    expiration_days: int = Field(default=30, description="Days to expiration for options")
    custom_strike_offset_pct: float | None = Field(default=None, description="Custom strike offset from current price")
    description: str = Field(description="Human-readable description")


class ExitCriteria(BaseModel):
    """When to close the position."""

    profit_target_pct: float = Field(default=20.0, description="Take profit at this % gain")
    stop_loss_pct: float = Field(default=10.0, description="Cut loss at this % decline")
    max_hold_days: int | None = Field(default=None, description="Close after N days regardless (None = hold until target/stop)")
    description: str = Field(description="Human-readable description")


class RuleSet(BaseModel):
    """The complete codified version of a trading pattern."""

    trigger_type: TriggerType = Field(description="Quantitative (fully automatable) or qualitative (needs human confirmation)")
    trigger_conditions: list[TriggerCondition] = Field(description="All conditions that must be met to trigger")
    entry_signal: EntrySignal = Field(description="When to enter after trigger")
    action: TradeAction = Field(description="What position to take")
    exit_criteria: ExitCriteria = Field(description="When to close the position")
    sector_filter: str | None = Field(default=None, description="Limit to specific sector (e.g., 'healthcare')")
    min_market_cap: float | None = Field(default=None, description="Minimum market cap in billions")
    min_avg_volume: int | None = Field(default=None, description="Minimum average daily volume")


class ClarifyingQuestion(BaseModel):
    """A question to ask the user when the pattern description is ambiguous."""

    question: str = Field(description="The question to ask")
    field: str = Field(description="Which RuleSet field this clarifies")
    suggestions: list[str] = Field(description="Suggested answers")


class PatternParseResult(BaseModel):
    """Result of parsing a plain-text pattern description."""

    is_complete: bool = Field(description="True if all required fields could be determined")
    rule_set: RuleSet | None = Field(default=None, description="Parsed rules (if complete)")
    suggested_name: str = Field(description="Auto-generated pattern name")
    clarifying_questions: list[ClarifyingQuestion] = Field(
        default_factory=list,
        description="Questions to ask if pattern is incomplete",
    )
    defaults_applied: list[str] = Field(
        default_factory=list,
        description="List of defaults that were applied (e.g., 'profit target: 20%')",
    )


class BacktestTrade(BaseModel):
    """A single simulated trade within a backtest."""

    ticker: str
    trigger_date: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    return_pct: float
    action_type: str
    option_details: dict[str, str | float] | None = None


class RegimePeriod(BaseModel):
    """A period where pattern performance significantly shifted."""

    start_date: str
    end_date: str
    win_rate: float
    avg_return_pct: float
    trade_count: int
    label: str = Field(description="e.g., 'strong', 'weak', 'breakdown'")
    explanation: str | None = Field(default=None, description="Possible reason for regime change")


class BacktestReport(BaseModel):
    """Complete backtest results for a pattern."""

    pattern_id: int
    date_range_start: str
    date_range_end: str
    trigger_count: int
    trade_count: int
    win_count: int
    total_return_pct: float
    avg_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float | None = None
    sample_size_warning: bool = False
    regimes: list[RegimePeriod] = Field(default_factory=list)
    trades: list[BacktestTrade] = Field(default_factory=list)


class CoveredCallCycle(BaseModel):
    """One complete cycle of a covered call: sell call → track → resolve."""

    ticker: str
    cycle_number: int = Field(ge=1)
    stock_entry_price: float = Field(gt=0)
    call_strike: float = Field(gt=0)
    call_premium: float = Field(ge=0)
    call_expiration_date: str
    cycle_start_date: str
    cycle_end_date: str | None = None
    stock_price_at_exit: float | None = None
    outcome: str | None = Field(
        default=None,
        description="expired_worthless, rolled, assigned, or closed_early",
    )
    premium_return_pct: float | None = None
    total_return_pct: float | None = None
    capped_upside_pct: float | None = None
    historical_volatility: float | None = None
    option_symbol: str | None = None
    pricing: str | None = Field(
        default=None,
        description="'real' if using historical option data, 'estimated' if Black-Scholes",
    )


class CoveredCallReport(BaseModel):
    """Complete covered call backtest results."""

    pattern_id: int
    ticker: str
    shares: int
    date_range_start: str
    date_range_end: str
    cycle_count: int
    total_premium_collected: float
    avg_premium_per_cycle: float
    annualized_income_yield_pct: float
    assignment_count: int
    assignment_frequency_pct: float
    closed_early_count: int
    rolled_count: int
    expired_worthless_count: int
    buy_and_hold_return_pct: float
    covered_call_return_pct: float
    capped_upside_cost: float
    sample_size_warning: bool = False
    cycles: list[CoveredCallCycle] = Field(default_factory=list)


class DetectedEvent(BaseModel):
    """A detected price spike used as a news event proxy during backtesting."""

    date: str = Field(description="Bar date when spike was detected (YYYY-MM-DD)")
    ticker: str = Field(description="Stock ticker symbol")
    price_change_pct: float = Field(description="Single-day price change percentage")
    volume_multiple: float = Field(description="Volume as multiple of 20-day average")
    close_price: float = Field(description="Closing price on spike day")
    high_price: float = Field(description="Intraday high on spike day")
    event_label: str | None = Field(default=None, description="Optional user-provided label (e.g., 'FDA approval')")
    source: str = Field(description="'proxy' (automatic detection) or 'manual' (user-provided date)")


class ManualEvent(BaseModel):
    """A user-provided event date for backtesting."""

    date: str = Field(description="Event date (YYYY-MM-DD)")
    label: str | None = Field(default=None, description="Optional description (e.g., 'MRNA FDA approval')")


class EventDetectionConfig(BaseModel):
    """Configuration for the event detection engine."""

    spike_threshold_pct: float = Field(default=5.0, description="Minimum single-day price increase %")
    volume_multiple_min: float = Field(default=1.5, description="Minimum volume vs 20-day average")
    volume_lookback_days: int = Field(default=20, description="Days for average volume calculation")
    cooldown_mode: str = Field(default="trade_lifecycle", description="How to handle consecutive spikes")
    entry_window_days: int = Field(default=2, description="Days to wait for entry after trigger")
    manual_events: list[ManualEvent] | None = Field(default=None, description="User-provided event dates")


class RegimeConfig(BaseModel):
    """Configuration for regime analysis."""

    window_trading_days: int = Field(default=63, description="Rolling window size (~3 months)")
    strong_threshold: float = Field(default=0.60, description="Win rate >= this = 'strong'")
    weak_threshold: float = Field(default=0.40, description="Win rate >= this but < strong = 'weak'; below = 'breakdown'")
    min_trades_for_regime: int = Field(default=10, description="Skip regime analysis if fewer trades")
    min_trades_per_window: int = Field(default=3, description="Skip windows with fewer trades")


class TickerBreakdown(BaseModel):
    """Per-ticker results within a multi-ticker backtest."""

    ticker: str
    events_detected: int = Field(default=0, description="Number of pattern trigger events for this ticker")
    trades_entered: int = Field(default=0, description="Number of trades that met entry criteria")
    win_count: int = Field(default=0, description="Trades with positive return")
    win_rate: float = Field(default=0.0, description="win_count / trades_entered (0.0 if no trades)")
    avg_return_pct: float = Field(default=0.0, description="Average per-trade return for this ticker")
    total_return_pct: float = Field(default=0.0, description="Cumulative return across all trades for this ticker")


class AggregatedBacktestReport(BaseModel):
    """Combined results across multiple tickers for a single pattern."""

    pattern_id: int
    date_range_start: str
    date_range_end: str
    tickers: list[str]
    ticker_breakdowns: list[TickerBreakdown] = Field(default_factory=list)
    combined_report: BacktestReport
    no_entry_events: list[dict] = Field(default_factory=list)


class PairwiseComparison(BaseModel):
    """Statistical comparison between two pattern variants."""

    variant_a_id: int
    variant_b_id: int
    win_rate_p_value: float
    win_rate_significant: bool
    avg_return_p_value: float
    avg_return_significant: bool
    confidence_level: float = Field(default=0.95)


class ABTestResult(BaseModel):
    """Complete A/B test output comparing 2+ pattern variants."""

    pattern_ids: list[int]
    tickers: list[str]
    date_range_start: str
    date_range_end: str
    variant_reports: list[AggregatedBacktestReport] = Field(default_factory=list)
    comparisons: list[PairwiseComparison] = Field(default_factory=list)
    best_variant_id: int
    best_is_significant: bool
    sample_size_warnings: list[str] = Field(default_factory=list)
