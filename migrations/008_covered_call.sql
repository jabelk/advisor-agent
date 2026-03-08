-- Migration 008: Covered Call Income Strategy
-- Adds covered_call_cycle table for tracking monthly covered call cycles

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
