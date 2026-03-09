-- Migration 009: Option price cache for real historical option data (016-real-options-data)
-- Stores historical OHLCV bars for option contracts, keyed by OCC symbol.

CREATE TABLE IF NOT EXISTS option_price_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    option_symbol   TEXT    NOT NULL,
    underlying_ticker TEXT  NOT NULL,
    timeframe       TEXT    NOT NULL DEFAULT 'day',
    bar_timestamp   TEXT    NOT NULL,
    open            REAL,
    high            REAL,
    low             REAL,
    close           REAL,
    volume          INTEGER,
    trade_count     INTEGER,
    fetched_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_option_price_unique
    ON option_price_cache(option_symbol, timeframe, bar_timestamp);

CREATE INDEX IF NOT EXISTS idx_option_underlying
    ON option_price_cache(underlying_ticker);

CREATE INDEX IF NOT EXISTS idx_option_symbol
    ON option_price_cache(option_symbol);

PRAGMA user_version = 9;
