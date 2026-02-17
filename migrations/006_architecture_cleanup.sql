-- Migration 006: Architecture Pivot Cleanup
-- Rename engine_state → safety_state, drop unused tables from features 003-005

-- Rename engine_state → safety_state (preserves kill switch + risk settings)
ALTER TABLE engine_state RENAME TO safety_state;

-- Drop market data tables (migration 003)
DROP TABLE IF EXISTS price_bar;
DROP TABLE IF EXISTS technical_indicator;
DROP TABLE IF EXISTS market_data_fetch;

-- Drop decision engine tables (migration 004) — except engine_state (now safety_state)
DROP TABLE IF EXISTS risk_check_result;
DROP TABLE IF EXISTS proposal_source;
DROP TABLE IF EXISTS trade_proposal;

-- Drop execution tables (migration 005)
DROP TABLE IF EXISTS position_snapshot;
DROP TABLE IF EXISTS broker_order;

PRAGMA user_version = 6;
