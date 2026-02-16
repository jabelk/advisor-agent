# Data Model: Market Data Integration (003)

**Date**: 2026-02-16
**Feature**: 003-market-data
**Schema Version**: 2 → 3

## New Tables

### price_bar

Stores historical OHLCV bars (daily and hourly) for watchlist companies. All prices are split-adjusted.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Row ID |
| company_id | INTEGER | NOT NULL, FK → company(id) | Watchlist company reference |
| ticker | TEXT | NOT NULL | Ticker symbol (denormalized for query speed) |
| timeframe | TEXT | NOT NULL | 'day' or 'hour' |
| bar_timestamp | TEXT | NOT NULL | ISO 8601 UTC bar time |
| open | REAL | NOT NULL | Opening price (split-adjusted) |
| high | REAL | NOT NULL | High price (split-adjusted) |
| low | REAL | NOT NULL | Low price (split-adjusted) |
| close | REAL | NOT NULL | Closing price (split-adjusted) |
| volume | REAL | NOT NULL | Volume |
| trade_count | REAL | | Number of trades in bar |
| vwap | REAL | | Volume-weighted average price |
| fetched_at | TEXT | NOT NULL, DEFAULT now | When this bar was fetched |

**Unique constraint**: `UNIQUE(ticker, timeframe, bar_timestamp)` — enables `INSERT OR IGNORE` for incremental dedup.

**Indexes**:
- `idx_price_bar_ticker_tf_ts` on `(ticker, timeframe, bar_timestamp)` — primary query pattern
- `idx_price_bar_company` on `(company_id)` — join with company table

### technical_indicator

Stores the latest computed indicator values per ticker. Updated on each bar fetch or explicit recomputation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Row ID |
| company_id | INTEGER | NOT NULL, FK → company(id) | Watchlist company reference |
| ticker | TEXT | NOT NULL | Ticker symbol (denormalized) |
| indicator_type | TEXT | NOT NULL | 'sma_20', 'sma_50', 'rsi_14', 'vwap' |
| timeframe | TEXT | NOT NULL | 'day' or 'hour' |
| value | REAL | NOT NULL | Computed indicator value |
| computed_at | TEXT | NOT NULL | When this value was computed |
| bar_date | TEXT | NOT NULL | Date of the most recent bar used |

**Unique constraint**: `UNIQUE(ticker, indicator_type, timeframe)` — only latest value per indicator stored, upserted on recomputation.

### market_data_fetch

Tracks each data fetch operation for audit and incremental update logic.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Row ID |
| ticker | TEXT | NOT NULL | Ticker symbol |
| timeframe | TEXT | NOT NULL | 'day' or 'hour' |
| started_at | TEXT | NOT NULL | Fetch start time |
| completed_at | TEXT | | Fetch completion time |
| status | TEXT | NOT NULL, DEFAULT 'running' | 'running', 'complete', 'failed' |
| bars_fetched | INTEGER | NOT NULL, DEFAULT 0 | Number of new bars stored |
| from_date | TEXT | | Oldest bar date requested |
| to_date | TEXT | | Newest bar date requested |
| error_message | TEXT | | Error details if failed |

**Index**: `idx_fetch_ticker_tf` on `(ticker, timeframe, completed_at)` — for finding last successful fetch.

## Entity Relationships

```
company (existing)
  ├── price_bar (1:N) — via company_id
  ├── technical_indicator (1:N) — via company_id
  └── market_data_fetch (implicit via ticker)
```

## State Transitions

### market_data_fetch.status
```
running → complete  (normal completion)
running → failed    (API error, timeout, etc.)
```

### Incremental Update Logic
1. Query `price_bar` for MAX(bar_timestamp) WHERE ticker=X AND timeframe=Y
2. If no bars exist: fetch from (today - 2 years) for daily, (today - 30 days) for hourly
3. If bars exist: fetch from MAX(bar_timestamp) + 1 bar period to now
4. INSERT OR IGNORE new bars (unique constraint handles dedup)

## Migration SQL (003_market_data.sql)

```sql
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
```
