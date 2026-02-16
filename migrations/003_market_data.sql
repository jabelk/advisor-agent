-- Price bars table
CREATE TABLE IF NOT EXISTS price_bar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES company(id),
    ticker TEXT NOT NULL,
    timeframe TEXT NOT NULL CHECK (timeframe IN ('day', 'hour')),
    bar_timestamp TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    trade_count REAL,
    vwap REAL,
    fetched_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(ticker, timeframe, bar_timestamp)
) STRICT;

CREATE INDEX IF NOT EXISTS idx_price_bar_ticker_tf_ts
    ON price_bar(ticker, timeframe, bar_timestamp);
CREATE INDEX IF NOT EXISTS idx_price_bar_company
    ON price_bar(company_id);

-- Technical indicators (latest values only)
CREATE TABLE IF NOT EXISTS technical_indicator (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES company(id),
    ticker TEXT NOT NULL,
    indicator_type TEXT NOT NULL,
    timeframe TEXT NOT NULL CHECK (timeframe IN ('day', 'hour')),
    value REAL NOT NULL,
    computed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    bar_date TEXT NOT NULL,
    UNIQUE(ticker, indicator_type, timeframe)
) STRICT;

-- Market data fetch tracking
CREATE TABLE IF NOT EXISTS market_data_fetch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    timeframe TEXT NOT NULL CHECK (timeframe IN ('day', 'hour')),
    started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'complete', 'failed')),
    bars_fetched INTEGER NOT NULL DEFAULT 0,
    from_date TEXT,
    to_date TEXT,
    error_message TEXT
) STRICT;

CREATE INDEX IF NOT EXISTS idx_fetch_ticker_tf
    ON market_data_fetch(ticker, timeframe, completed_at);

PRAGMA user_version = 3;
