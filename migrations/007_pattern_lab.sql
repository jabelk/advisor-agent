-- Pattern Lab: trading patterns, backtests, paper trades, and price cache
-- Migration 007

-- Trading patterns defined by the user
CREATE TABLE IF NOT EXISTS trading_pattern (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT    NOT NULL,
    rule_set_json TEXT  NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'backtested', 'paper_trading', 'retired')),
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    retired_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_pattern_status ON trading_pattern(status);
CREATE INDEX IF NOT EXISTS idx_pattern_created ON trading_pattern(created_at);

-- Backtest results for a pattern
CREATE TABLE IF NOT EXISTS backtest_result (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id          INTEGER NOT NULL REFERENCES trading_pattern(id),
    date_range_start    TEXT    NOT NULL,
    date_range_end      TEXT    NOT NULL,
    trigger_count       INTEGER NOT NULL DEFAULT 0,
    trade_count         INTEGER NOT NULL DEFAULT 0,
    win_count           INTEGER NOT NULL DEFAULT 0,
    total_return_pct    REAL    NOT NULL DEFAULT 0.0,
    avg_return_pct      REAL    NOT NULL DEFAULT 0.0,
    max_drawdown_pct    REAL    NOT NULL DEFAULT 0.0,
    sharpe_ratio        REAL,
    regime_analysis_json TEXT,
    sample_size_warning INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_backtest_pattern ON backtest_result(pattern_id);
CREATE INDEX IF NOT EXISTS idx_backtest_created ON backtest_result(created_at);

-- Individual trades within a backtest
CREATE TABLE IF NOT EXISTS backtest_trade (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_id     INTEGER NOT NULL REFERENCES backtest_result(id),
    ticker          TEXT    NOT NULL,
    trigger_date    TEXT    NOT NULL,
    entry_date      TEXT    NOT NULL,
    entry_price     REAL    NOT NULL,
    exit_date       TEXT    NOT NULL,
    exit_price      REAL    NOT NULL,
    return_pct      REAL    NOT NULL,
    action_type     TEXT    NOT NULL,
    option_details_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_bt_trade_backtest ON backtest_trade(backtest_id);
CREATE INDEX IF NOT EXISTS idx_bt_trade_ticker ON backtest_trade(ticker, trigger_date);

-- Paper trades executed via Alpaca
CREATE TABLE IF NOT EXISTS paper_trade (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id          INTEGER NOT NULL REFERENCES trading_pattern(id),
    alpaca_order_id     TEXT,
    ticker              TEXT    NOT NULL,
    direction           TEXT    NOT NULL CHECK (direction IN ('buy', 'sell')),
    action_type         TEXT    NOT NULL,
    quantity            INTEGER NOT NULL,
    entry_price         REAL,
    exit_price          REAL,
    pnl                 REAL,
    status              TEXT    NOT NULL DEFAULT 'proposed'
                        CHECK (status IN ('proposed', 'approved', 'executed', 'closed', 'cancelled')),
    option_details_json TEXT,
    proposed_at         TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    executed_at         TEXT,
    closed_at           TEXT
);

CREATE INDEX IF NOT EXISTS idx_paper_pattern ON paper_trade(pattern_id);
CREATE INDEX IF NOT EXISTS idx_paper_status ON paper_trade(status);
CREATE INDEX IF NOT EXISTS idx_paper_ticker ON paper_trade(ticker);

-- Cached historical price data from Alpaca
CREATE TABLE IF NOT EXISTS price_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT    NOT NULL,
    timeframe       TEXT    NOT NULL CHECK (timeframe IN ('day', 'hour')),
    bar_timestamp   TEXT    NOT NULL,
    open            REAL    NOT NULL,
    high            REAL    NOT NULL,
    low             REAL    NOT NULL,
    close           REAL    NOT NULL,
    volume          INTEGER NOT NULL,
    vwap            REAL,
    fetched_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_price_unique ON price_cache(ticker, timeframe, bar_timestamp);

PRAGMA user_version = 7;
