# Data Model: Covered Call Income Strategy

## New Entities

### CoveredCallCycle

Represents one complete cycle of a covered call: selling a call, tracking through expiration, and recording the outcome. Multiple cycles form a campaign on a single stock holding.

| Field | Type | Description |
|-------|------|-------------|
| id | integer (PK) | Auto-increment |
| pattern_id | integer (FK → trading_pattern) | Which pattern this cycle belongs to |
| backtest_result_id | integer (FK → backtest_result, nullable) | If from a backtest |
| ticker | text | Underlying stock symbol |
| cycle_number | integer | Sequential cycle number within the campaign (1, 2, 3...) |
| stock_entry_price | real | Price of underlying shares at cycle start |
| call_strike | real | Strike price of the sold call |
| call_premium | real | Premium collected per share |
| call_expiration_date | text | Option expiration date (YYYY-MM-DD) |
| cycle_start_date | text | Date call was sold |
| cycle_end_date | text | Date cycle concluded (expiration, early close, or assignment) |
| stock_price_at_exit | real | Stock price when cycle ended |
| outcome | text | One of: "expired_worthless", "rolled", "assigned", "closed_early" |
| premium_return_pct | real | Premium collected / stock entry price * 100 |
| total_return_pct | real | (Premium + stock P&L capped at strike) / stock entry price * 100 |
| capped_upside_pct | real (nullable) | Gain forfeited if assigned (stock went above strike) |
| historical_volatility | real | 20-day annualized volatility used for premium estimation |
| created_at | text | ISO 8601 timestamp |

**Constraints**:
- outcome must be one of: "expired_worthless", "rolled", "assigned", "closed_early"
- call_strike > 0
- call_premium >= 0
- cycle_number >= 1

**Indexes**:
- (pattern_id, cycle_number)
- (ticker, cycle_start_date)

### State Transitions

```
CYCLE LIFECYCLE:

  [sell_call] → OPEN
       │
       ├── stock < strike at expiry → EXPIRED_WORTHLESS → [start next cycle]
       │
       ├── premium profit target hit → CLOSED_EARLY → [start next cycle]
       │
       ├── DTE reaches roll threshold → ROLLED → [start next cycle with new call]
       │
       └── stock > strike at expiry → ASSIGNED → [campaign ends or repurchase]
```

## Extended Entities

### PremiumEstimate (embedded in CoveredCallCycle, not a separate table)

Used during backtesting to record how the premium was estimated.

| Field | Type | Description |
|-------|------|-------------|
| spot_price | real | Stock price when premium was estimated |
| strike_price | real | Call strike price |
| days_to_expiration | integer | DTE at time of estimation |
| historical_volatility | real | 20-day annualized vol |
| estimated_premium | real | Calculated premium per share |
| calculation_method | text | "black_scholes_hv" (historical vol Black-Scholes) |

This is stored as JSON in the `option_details_json` field of `backtest_trade` (existing column).

## Existing Entities Used (No Changes)

### trading_pattern
Covered call patterns stored like any other pattern. The `rule_set_json` field contains `ActionType.SELL_CALL` and covered call-specific exit criteria (profit target on premium, roll threshold).

### backtest_result
Aggregate backtest metrics. For covered calls, includes total premium income, assignment frequency, and annualized yield.

### paper_trade
Individual paper trades. For covered calls, the `option_details_json` stores the call contract details, premium collected, and expiration date.

## Migration: 008_covered_call.sql

```sql
CREATE TABLE IF NOT EXISTS covered_call_cycle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL REFERENCES trading_pattern(id),
    backtest_result_id INTEGER REFERENCES backtest_result(id),
    ticker TEXT NOT NULL,
    cycle_number INTEGER NOT NULL CHECK(cycle_number >= 1),
    stock_entry_price REAL NOT NULL CHECK(stock_entry_price > 0),
    call_strike REAL NOT NULL CHECK(call_strike > 0),
    call_premium REAL NOT NULL CHECK(call_premium >= 0),
    call_expiration_date TEXT NOT NULL,
    cycle_start_date TEXT NOT NULL,
    cycle_end_date TEXT,
    stock_price_at_exit REAL,
    outcome TEXT CHECK(outcome IN ('expired_worthless', 'rolled', 'assigned', 'closed_early')),
    premium_return_pct REAL,
    total_return_pct REAL,
    capped_upside_pct REAL,
    historical_volatility REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cc_cycle_pattern ON covered_call_cycle(pattern_id, cycle_number);
CREATE INDEX IF NOT EXISTS idx_cc_cycle_ticker ON covered_call_cycle(ticker, cycle_start_date);

PRAGMA user_version = 8;
```
