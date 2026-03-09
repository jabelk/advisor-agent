-- Migration 010: Pattern alerts and auto-execution support
-- Adds pattern_alert table for scanner-generated alerts
-- Adds auto_execute column to trading_pattern for per-pattern auto-execution

CREATE TABLE IF NOT EXISTS pattern_alert (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id      INTEGER NOT NULL REFERENCES trading_pattern(id),
    pattern_name    TEXT    NOT NULL,
    ticker          TEXT    NOT NULL,
    trigger_date    TEXT    NOT NULL,
    trigger_details_json TEXT NOT NULL,
    recommended_action   TEXT NOT NULL,
    pattern_win_rate     REAL,
    status          TEXT    NOT NULL DEFAULT 'new'
                    CHECK (status IN ('new', 'acknowledged', 'acted_on', 'dismissed')),
    auto_executed   INTEGER NOT NULL DEFAULT 0,
    auto_execute_result  TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_pattern_alert_dedup
    ON pattern_alert(pattern_id, ticker, trigger_date);

CREATE INDEX IF NOT EXISTS idx_pattern_alert_status
    ON pattern_alert(status);

CREATE INDEX IF NOT EXISTS idx_pattern_alert_created
    ON pattern_alert(created_at);

-- Add auto_execute flag to trading_pattern (defaults to off)
ALTER TABLE trading_pattern ADD COLUMN auto_execute INTEGER NOT NULL DEFAULT 0;

PRAGMA user_version = 10;
