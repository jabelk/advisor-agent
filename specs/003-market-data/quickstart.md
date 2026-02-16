# Quickstart: Market Data Integration (003)

**Date**: 2026-02-16
**Feature**: 003-market-data

## Prerequisites

- Alpaca paper trading API keys configured in `.env` (same keys used for broker)
- At least one company on the watchlist: `finance-agent watchlist add AAPL`

No additional API keys required — market data uses the same Alpaca credentials as trading.

## Usage

### 1. Fetch historical price bars

```bash
# Fetch daily + hourly bars for all watchlist companies
uv run finance-agent market fetch

# Fetch for a specific ticker only
uv run finance-agent market fetch --ticker AAPL

# Fetch only daily bars
uv run finance-agent market fetch --timeframe day

# Force full re-fetch (2 years daily, 30 days hourly)
uv run finance-agent market fetch --full
```

### 2. Get real-time price snapshot

```bash
# Single ticker
uv run finance-agent market snapshot AAPL

# Multiple tickers
uv run finance-agent market snapshot AAPL NVDA MSFT
```

### 3. View stored data status

```bash
uv run finance-agent market status
```

### 4. Recompute technical indicators

```bash
# Recompute for all watchlist companies
uv run finance-agent market indicators

# Recompute for one ticker
uv run finance-agent market indicators --ticker AAPL
```

## Development

```bash
# Run unit tests (no API keys needed — all Alpaca calls are mocked)
uv run pytest tests/unit/test_market.py -v

# Run integration tests (requires Alpaca API keys in .env)
set -a && source .env && set +a
uv run pytest tests/integration/test_market_data.py -v

# Lint and type check
uv run ruff check src/finance_agent/market/ tests/unit/test_market.py
uv run mypy src/finance_agent/market/
```

## File Layout

```
src/finance_agent/market/
├── __init__.py           # Module init
├── client.py             # Alpaca data client wrapper + rate limiting
├── bars.py               # Bar fetch, storage, and query operations
├── indicators.py         # SMA, RSI, VWAP computation
└── snapshot.py           # Real-time price snapshot queries

migrations/
└── 003_market_data.sql   # price_bar + technical_indicator + market_data_fetch tables

tests/
├── unit/
│   └── test_market.py    # Unit tests (mocked Alpaca client)
└── integration/
    └── test_market_data.py  # Integration tests (live Alpaca API)
```

## Data Volume Estimates

| Scenario | Bars | SQLite Size (est.) |
|----------|------|--------------------|
| 1 ticker, 2yr daily | ~504 | ~50 KB |
| 1 ticker, 30d hourly | ~210 | ~20 KB |
| 20 tickers, both timeframes | ~14,280 | ~1.4 MB |
| 1 year of daily fetches (20 tickers) | ~100,800 | ~10 MB |

Storage is negligible. No cleanup/rotation needed for the foreseeable future.
