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
