# CLI Contracts: Decision Engine

**Feature**: 004-decision-engine

All commands are subcommands of the `engine` group under `finance-agent`.

## `finance-agent engine generate`

Generate trade proposals for watchlist companies.

**Arguments**:
- `--ticker TICKER` (optional): Generate for a specific ticker only
- `--dry-run` (optional): Show what would be proposed without saving to database

**Behavior**:
1. Check kill switch — abort if active
2. Fetch account info from Alpaca (equity, positions, orders, P&L)
3. For each watchlist company (or specified ticker):
   a. Query recent research signals
   b. Query technical indicators and price bars
   c. Validate minimum data requirements (3+ signals, 1+ fact, 2+ signal types, freshness)
   d. Compute base score (signal + indicator + momentum)
   e. Call LLM for adjustment (if ANTHROPIC_API_KEY available; skip if not, use base score)
   f. Check confidence threshold (|score| >= 0.45)
   g. Determine direction (positive = buy, negative = sell-to-close if position held)
   h. Compute position size and limit price
   i. Run all risk checks
   j. Save proposal with status and risk results
4. Print summary table

**Output format**:
```
[PAPER MODE] Decision Engine — Generating proposals...

Account: $987.65 equity | $234.56 buying power | 2 positions | 3/20 trades today | P&L: -$12.34

NVDA: score +0.72 (base +0.65, LLM +0.07) → BUY 2 shares @ $127.62 limit ($255.24)
  Sources: 5 signals (3 fact, 2 inference) | SMA bullish | RSI 58.2 | Momentum +3.2%
  Risk: ✓ position_size (25.8% < 10% cap → ADJUSTED to 1 share @ $127.62)
  Risk: ✓ daily_loss (1.2% < 5.0%)
  Risk: ✓ trade_count (4 < 20)
  Risk: ✓ concentration (0 existing NVDA positions < 2)
  Status: PENDING (awaiting review)

AAPL: score +0.31 → SKIPPED (below threshold 0.45)
  Reason: Confidence insufficient (3 signals, mixed sentiment)

TSLA: score -0.52 → SELL 5 shares @ $178.90 limit ($894.50)
  Sources: 4 signals (2 fact, 2 inference) | SMA bearish | RSI 38.1 | Momentum -4.8%
  Risk: ✗ daily_loss_limit_reached (4.8% >= 5.0%)
  Status: REJECTED (risk check failed)

Summary: 2 proposals generated (1 pending, 0 approved, 1 rejected), 1 skipped
```

**Error cases**:
- Kill switch active: `[KILL SWITCH ACTIVE] Engine halted. Run 'engine killswitch off' to resume.`
- No watchlist companies: `No companies in watchlist. Run 'watchlist add <TICKER>' first.`
- Broker unreachable: `ERROR: Cannot reach Alpaca account API. Portfolio data required for risk checks.`
- No API key for LLM: `Note: ANTHROPIC_API_KEY not set. Using base score only (no LLM adjustment).`

## `finance-agent engine review`

Review and act on pending trade proposals.

**Arguments**:
- `--ticker TICKER` (optional): Review proposals for a specific ticker only

**Behavior**:
1. Check kill switch — warn if active (can view but not approve)
2. Query pending proposals (exclude expired)
3. For each proposal, display full details and prompt for action
4. Record decision in database and audit log

**Interactive flow**:
```
[PAPER MODE] Decision Engine — Review Proposals

Proposal #42: BUY NVDA
  Direction:   BUY (open new position)
  Quantity:    2 shares
  Limit Price: $127.62
  Est. Cost:   $255.24
  Confidence:  +0.72 (base +0.65, LLM +0.07)
    LLM note: "Strong earnings beat with raised guidance aligns with bullish technicals. +0.07 warranted."

  Score Breakdown:
    Signal:    +0.68 (5 signals, 7d half-life weighted)
    Indicator: +0.55 (SMA golden cross, RSI 58.2, above VWAP)
    Momentum:  +0.42 (5d +3.2%, 20d +8.1%, volume confirming)

  Cited Sources:
    [1] research_signal #234: sentiment/fact/high — "NVDA Q4 revenue beat by 12%..." (2d ago)
    [2] research_signal #231: guidance_change/fact/high — "Raised FY26 guidance..." (3d ago)
    [3] research_signal #228: financial_metric/fact/medium — "Data center revenue +40%..." (5d ago)
    [4] technical_indicator: SMA-20 ($125.40) > SMA-50 ($121.80) — golden cross
    [5] technical_indicator: RSI-14 = 58.2 — healthy bullish momentum

  Risk Checks:
    ✓ position_size: $255.24 = 25.8% of portfolio (limit: 10%) → ADJUSTED qty to 1
    ✓ daily_loss: -$12.34 = 1.2% (limit: 5.0%)
    ✓ trade_count: 3 today (limit: 20)
    ✓ concentration: 0 existing NVDA (limit: 2)

  Action [a]pprove / [r]eject / [s]kip: a
  Reason (optional, press Enter to skip): Earnings thesis looks solid

  ✓ Proposal #42 APPROVED — recorded in audit log.

---
No more pending proposals.
```

**Kill switch behavior**:
```
  Action [a]pprove / [r]eject / [s]kip: a
  ✗ Cannot approve: kill switch is active. Run 'engine killswitch off' first.
```

## `finance-agent engine killswitch <on|off>`

Toggle the kill switch.

**Arguments**:
- `on`: Activate kill switch (halt all generation and approval)
- `off`: Deactivate kill switch (resume normal operation)

**Output format**:
```
# Activating:
[KILL SWITCH ACTIVATED] All proposal generation and approval halted.
Logged: kill_switch toggled ON at 2026-02-16T14:30:00Z by operator

# Deactivating:
[KILL SWITCH DEACTIVATED] Normal operation resumed.
Logged: kill_switch toggled OFF at 2026-02-16T15:00:00Z by operator

# Already in requested state:
Kill switch is already OFF. No change.
```

## `finance-agent engine risk`

View current risk control settings.

**Arguments**: None

**Output format**:
```
[PAPER MODE] Risk Control Settings

  Max Position Size:     10.0% of portfolio ($98.77 at current equity)
  Max Daily Loss:        5.0% of portfolio ($49.38 at current equity)
  Max Trades/Day:        20
  Max Positions/Symbol:  2
  Min Confidence:        0.45
  Max Signal Age:        14 days
  Min Signal Count:      3
  Data Staleness:        24 hours

  Today's Usage:
    Trades: 3 / 20
    Daily P&L: -$12.34 / -$49.38 limit (24.9% of limit used)
    Positions: NVDA (1), AAPL (1)
```

## `finance-agent engine risk set <key> <value>`

Update a risk control setting.

**Arguments**:
- `key`: Setting name (max_position_pct, max_daily_loss_pct, max_trades_per_day, max_positions_per_symbol, min_confidence_threshold)
- `value`: New value (numeric)

**Output format**:
```
Updated max_position_pct: 0.10 → 0.08
Logged: risk_settings.max_position_pct changed from 0.10 to 0.08 by operator
```

**Validation**:
- `max_position_pct`: must be 0.01-0.50 (1%-50%)
- `max_daily_loss_pct`: must be 0.01-0.20 (1%-20%)
- `max_trades_per_day`: must be 1-100
- `max_positions_per_symbol`: must be 1-10
- `min_confidence_threshold`: must be 0.1-0.9

## `finance-agent engine history`

View proposal history.

**Arguments**:
- `--ticker TICKER` (optional): Filter by ticker
- `--status STATUS` (optional): Filter by status (pending, approved, rejected, expired)
- `--since DATE` (optional): Show proposals from this date (YYYY-MM-DD)
- `--limit N` (optional): Max results (default 20)

**Output format**:
```
[PAPER MODE] Proposal History (last 20)

  #42  2026-02-16 14:30  NVDA  BUY   2 @ $127.62  +0.72  APPROVED  "Earnings thesis"
  #41  2026-02-16 14:30  TSLA  SELL  5 @ $178.90  -0.52  REJECTED  "daily_loss_limit"
  #40  2026-02-15 10:00  AAPL  BUY   3 @ $185.20  +0.58  EXPIRED   —
  #39  2026-02-15 10:00  NVDA  BUY   1 @ $126.50  +0.61  APPROVED  —

Totals: 4 proposals (2 approved, 1 rejected, 1 expired)
```

## `finance-agent engine status`

Show engine status summary.

**Output format**:
```
[PAPER MODE] Decision Engine Status

  Kill Switch:    OFF
  Account:        $987.65 equity | $234.56 buying power
  Trades Today:   3 / 20 (15.0%)
  Daily P&L:      -$12.34 / -$49.38 limit (25.0% of limit used)
  Positions:      2 open (NVDA: 1 share, AAPL: 3 shares)

  Pending:        1 proposal awaiting review
  Today:          2 generated, 1 approved, 1 rejected

  Risk Settings:  10% position | 5% daily loss | 20 trades/day | 2 per symbol
```
