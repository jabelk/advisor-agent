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
