-- Migration 006: Architecture Pivot Cleanup
-- Rename engine_state → safety_state, drop unused tables from features 003-005.

-- Create safety_state with same schema as engine_state (IF NOT EXISTS handles
-- the case where it was already created by a prior partial run).
CREATE TABLE IF NOT EXISTS safety_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_by TEXT NOT NULL DEFAULT 'system'
);

-- Seed default data (OR IGNORE preserves existing rows from engine_state or
-- a prior run that already populated safety_state).
INSERT OR IGNORE INTO safety_state (key, value, updated_by) VALUES
    ('kill_switch', '{"active": false, "toggled_at": null, "toggled_by": null}', 'migration'),
    ('risk_settings', '{"max_position_pct": 0.10, "max_daily_loss_pct": 0.05, "max_trades_per_day": 20, "max_positions_per_symbol": 2, "min_confidence_threshold": 0.45, "max_signal_age_days": 14, "min_signal_count": 3, "data_staleness_hours": 24}', 'migration');

-- Drop execution tables FIRST (broker_order has FK → trade_proposal)
DROP TABLE IF EXISTS broker_order;
DROP TABLE IF EXISTS position_snapshot;

-- Drop decision engine tables (migration 004) — replaced by safety_state above
DROP TABLE IF EXISTS risk_check_result;
DROP TABLE IF EXISTS proposal_source;
DROP TABLE IF EXISTS trade_proposal;

-- Drop market data tables (migration 003)
DROP TABLE IF EXISTS price_bar;
DROP TABLE IF EXISTS technical_indicator;
DROP TABLE IF EXISTS market_data_fetch;

-- Drop legacy engine_state (superseded by safety_state)
DROP TABLE IF EXISTS engine_state;

PRAGMA user_version = 6;
