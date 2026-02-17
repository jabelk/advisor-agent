# Data Model: Decision Engine

**Feature**: 004-decision-engine
**Date**: 2026-02-16

## New Tables (Migration 004)

### trade_proposal

Stores generated trade proposals with their full lifecycle.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique proposal ID |
| company_id | INTEGER | NOT NULL, FK → company(id) | Target company |
| ticker | TEXT | NOT NULL | Ticker symbol (denormalized for queries) |
| direction | TEXT | NOT NULL, CHECK(direction IN ('buy','sell')) | Buy-to-open or sell-to-close |
| quantity | INTEGER | NOT NULL, CHECK(quantity > 0) | Recommended share quantity |
| limit_price | REAL | NOT NULL, CHECK(limit_price > 0) | Recommended limit order price |
| estimated_cost | REAL | NOT NULL | quantity * limit_price |
| confidence_score | REAL | NOT NULL, CHECK(confidence_score >= -1.0 AND confidence_score <= 1.0) | Final hybrid confidence score |
| base_score | REAL | NOT NULL | Deterministic base score (before LLM adjustment) |
| llm_adjustment | REAL | NOT NULL DEFAULT 0.0 | LLM adjustment amount (-0.15 to +0.15) |
| llm_rationale | TEXT | | LLM explanation for adjustment |
| signal_score | REAL | NOT NULL | Research signal sub-score |
| indicator_score | REAL | NOT NULL | Technical indicator sub-score |
| momentum_score | REAL | NOT NULL | Price momentum sub-score |
| status | TEXT | NOT NULL DEFAULT 'pending', CHECK(status IN ('pending','approved','rejected','expired')) | Proposal lifecycle status |
| risk_passed | INTEGER | NOT NULL DEFAULT 1, CHECK(risk_passed IN (0,1)) | Whether all risk checks passed |
| staleness_warning | INTEGER | NOT NULL DEFAULT 0, CHECK(staleness_warning IN (0,1)) | Market data staleness flag |
| decision_reason | TEXT | | Operator's reason for approve/reject |
| decided_at | TEXT | | ISO 8601 timestamp of operator decision |
| expires_at | TEXT | NOT NULL | ISO 8601 timestamp when proposal expires (16:00 ET) |
| created_at | TEXT | NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) | Generation timestamp |

**Indexes**:
- `idx_proposal_status` ON (status) — for querying pending proposals
- `idx_proposal_ticker` ON (ticker, created_at DESC) — for history by ticker
- `idx_proposal_created` ON (created_at DESC) — for chronological listing

### proposal_source

Links proposals to their cited research signals and market data points (many-to-many).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| proposal_id | INTEGER | NOT NULL, FK → trade_proposal(id) | Parent proposal |
| source_type | TEXT | NOT NULL, CHECK(source_type IN ('research_signal','technical_indicator','price_bar')) | Type of cited source |
| source_id | INTEGER | NOT NULL | ID in the source table (research_signal.id, technical_indicator.id, or price_bar.id) |
| contribution | TEXT | | How this source contributed (e.g., "bullish sentiment", "SMA golden cross") |

**Indexes**:
- `idx_proposal_source_proposal` ON (proposal_id) — for retrieving all sources for a proposal
- UNIQUE(proposal_id, source_type, source_id) — prevent duplicate citations

### risk_check_result

Records every risk check evaluation for every proposal.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| proposal_id | INTEGER | NOT NULL, FK → trade_proposal(id) | Evaluated proposal |
| rule_name | TEXT | NOT NULL | Risk rule identifier (e.g., 'position_size_pct', 'daily_loss_limit') |
| passed | INTEGER | NOT NULL, CHECK(passed IN (0,1)) | Whether the check passed |
| limit_value | TEXT | NOT NULL | The configured limit (e.g., '10%', '$50') |
| actual_value | TEXT | NOT NULL | The actual measured value (e.g., '12.5%', '$62') |
| details | TEXT | | Additional context |
| created_at | TEXT | NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) | |

**Indexes**:
- `idx_risk_check_proposal` ON (proposal_id) — for retrieving all checks for a proposal

### engine_state

Persistent key-value store for engine runtime state (kill switch, risk settings).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| key | TEXT | PRIMARY KEY | State key name |
| value | TEXT | NOT NULL | JSON-encoded value |
| updated_at | TEXT | NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) | Last update timestamp |
| updated_by | TEXT | NOT NULL DEFAULT 'system' | Who changed it (operator action or system) |

**Pre-populated rows** (inserted by migration):

| key | value | Description |
|-----|-------|-------------|
| kill_switch | `{"active": false, "toggled_at": null, "toggled_by": null}` | Kill switch state |
| risk_settings | `{"max_position_pct": 0.10, "max_daily_loss_pct": 0.05, "max_trades_per_day": 20, "max_positions_per_symbol": 2, "min_confidence_threshold": 0.45, "max_signal_age_days": 14, "min_signal_count": 3, "data_staleness_hours": 24}` | Default risk control settings |

## State Transitions

### Trade Proposal Lifecycle

```
[generated] → pending
                ├── operator approves → approved
                ├── operator rejects  → rejected
                └── expires_at passes → expired (checked at query time)
```

- `pending`: Generated and awaiting operator review. Risk checks have been run; risk_passed indicates result.
- `approved`: Operator approved. Ready for execution layer (feature 005).
- `rejected`: Operator rejected OR risk checks failed. decision_reason contains explanation.
- `expired`: Not acted upon before expires_at. Status updated lazily at query time.

### Kill Switch States

```
inactive ←→ active
```

Toggled via CLI. When active, blocks:
- Proposal generation (engine generate command)
- Proposal approval (engine review approve action)

Does NOT block:
- Viewing proposals, history, or status
- Updating risk settings
- Deactivating the kill switch itself

## Relationships to Existing Tables

```
company (existing, 002)
  └── trade_proposal (new, 004) — via company_id FK
        ├── proposal_source (new, 004) — via proposal_id FK
        │     └── references: research_signal.id, technical_indicator.id, price_bar.id
        └── risk_check_result (new, 004) — via proposal_id FK

research_signal (existing, 002) — queried for scoring, cited via proposal_source
technical_indicator (existing, 003) — queried for scoring, cited via proposal_source
price_bar (existing, 003) — queried for momentum scoring, cited via proposal_source
```

## Migration SQL (004_decision_engine.sql)

```sql
-- Migration 004: Decision Engine tables
-- trade_proposal, proposal_source, risk_check_result, engine_state

CREATE TABLE IF NOT EXISTS trade_proposal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES company(id),
    ticker TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('buy', 'sell')),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    limit_price REAL NOT NULL CHECK(limit_price > 0),
    estimated_cost REAL NOT NULL,
    confidence_score REAL NOT NULL CHECK(confidence_score >= -1.0 AND confidence_score <= 1.0),
    base_score REAL NOT NULL,
    llm_adjustment REAL NOT NULL DEFAULT 0.0,
    llm_rationale TEXT,
    signal_score REAL NOT NULL,
    indicator_score REAL NOT NULL,
    momentum_score REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'expired')),
    risk_passed INTEGER NOT NULL DEFAULT 1 CHECK(risk_passed IN (0, 1)),
    staleness_warning INTEGER NOT NULL DEFAULT 0 CHECK(staleness_warning IN (0, 1)),
    decision_reason TEXT,
    decided_at TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_proposal_status ON trade_proposal(status);
CREATE INDEX IF NOT EXISTS idx_proposal_ticker ON trade_proposal(ticker, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_proposal_created ON trade_proposal(created_at DESC);

CREATE TABLE IF NOT EXISTS proposal_source (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id INTEGER NOT NULL REFERENCES trade_proposal(id),
    source_type TEXT NOT NULL CHECK(source_type IN ('research_signal', 'technical_indicator', 'price_bar')),
    source_id INTEGER NOT NULL,
    contribution TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_proposal_source_unique ON proposal_source(proposal_id, source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_proposal_source_proposal ON proposal_source(proposal_id);

CREATE TABLE IF NOT EXISTS risk_check_result (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id INTEGER NOT NULL REFERENCES trade_proposal(id),
    rule_name TEXT NOT NULL,
    passed INTEGER NOT NULL CHECK(passed IN (0, 1)),
    limit_value TEXT NOT NULL,
    actual_value TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_risk_check_proposal ON risk_check_result(proposal_id);

CREATE TABLE IF NOT EXISTS engine_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_by TEXT NOT NULL DEFAULT 'system'
);

-- Insert default engine state
INSERT OR IGNORE INTO engine_state (key, value, updated_by) VALUES
    ('kill_switch', '{"active": false, "toggled_at": null, "toggled_by": null}', 'migration'),
    ('risk_settings', '{"max_position_pct": 0.10, "max_daily_loss_pct": 0.05, "max_trades_per_day": 20, "max_positions_per_symbol": 2, "min_confidence_threshold": 0.45, "max_signal_age_days": 14, "min_signal_count": 3, "data_staleness_hours": 24}', 'migration');

PRAGMA user_version = 4;
```
