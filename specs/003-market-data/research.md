# Research: Market Data Integration (003)

**Date**: 2026-02-16
**Feature**: 003-market-data

## Decision 1: Alpaca Data Client for Historical Bars

**Decision**: Use `alpaca.data.historical.StockHistoricalDataClient` with `StockBarsRequest` for all bar fetching. SDK handles pagination automatically (10,000 bars per page internally).

**Rationale**: The alpaca-py SDK (already a project dependency at >=0.43) provides a unified `StockHistoricalDataClient` for both historical and latest data. No separate client needed. Pagination is handled internally — specify start/end dates and the SDK follows `next_page_token` automatically.

**Alternatives considered**:
- Raw REST API via httpx: More control but duplicates SDK functionality and requires manual pagination
- Third-party data providers (yfinance, polygon): Adds dependencies; Alpaca is already our broker

**Key code pattern**:
```python
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment, DataFeed

client = StockHistoricalDataClient(api_key=key, secret_key=secret)
request = StockBarsRequest(
    symbol_or_symbols=["AAPL"],
    timeframe=TimeFrame.Day,
    start=start_date,
    end=end_date,
    adjustment=Adjustment.SPLIT,
)
bars = client.get_stock_bars(request)
```

## Decision 2: Price Adjustment Strategy

**Decision**: Use `Adjustment.SPLIT` for all historical bar fetches (split-adjusted, not dividend-adjusted).

**Rationale**: Split adjustment prevents artificial price cliffs that corrupt SMA/RSI calculations (e.g., a 4:1 split making a $400 stock appear to drop to $100). Dividend adjustment (`Adjustment.ALL`) is unnecessary because we're computing price-based technical indicators, not total-return analysis.

**Alternatives considered**:
- `Adjustment.RAW`: Would corrupt indicator calculations across splits
- `Adjustment.ALL`: Over-adjusts for our use case (momentum/trend indicators)

## Decision 3: Data Feed Tier (IEX vs SIP)

**Decision**: Use SIP feed for historical bars (free tier allows this if end date is 15+ minutes old). Use IEX (default) for real-time snapshots.

**Rationale**: Free-tier Alpaca allows SIP historical data as long as the query end is at least 15 minutes in the past. This gives consolidated tape data (all exchanges) for stored bars at no cost. Real-time snapshots are limited to IEX on the free tier.

**Alternatives considered**:
- IEX-only for everything: Loses consolidated volume/price data from other exchanges
- Paid SIP plan ($99/mo): Unnecessary for current scale

## Decision 4: Rate Limit Handling

**Decision**: Implement a simple token-bucket rate limiter at 180 req/min (90% of 200 limit) with exponential backoff on 429 responses.

**Rationale**: The Alpaca free tier allows 200 req/min. Running at 90% capacity provides headroom. For a watchlist of 20 companies, daily bar fetch = ~20 requests (1 per ticker), well within limits. Hourly bars = ~20 more. Total ~40 requests per full refresh.

**Alternatives considered**:
- No rate limiting (rely on API errors): Fragile, wastes requests on retries
- Per-request sleep: Too conservative, unnecessarily slow

## Decision 5: Bar Storage in SQLite

**Decision**: Store bars in a `price_bar` table with a composite unique constraint on (ticker, timeframe, bar_timestamp). Use REAL columns for OHLCV values. Batch INSERT with `INSERT OR IGNORE` for dedup on incremental updates.

**Rationale**: SQLite handles the expected data volume easily (~500 daily bars/ticker × 20 tickers = 10,000 rows). Composite unique index enables efficient incremental inserts. REAL type matches float values from the API.

**Alternatives considered**:
- Separate tables per timeframe: Unnecessary complexity for 2 timeframes
- Parquet/CSV files: Loses query flexibility; harder to do incremental updates

## Decision 6: Technical Indicator Computation

**Decision**: Compute indicators in pure Python from stored bars (no numpy/pandas dependency). Persist latest values in a `technical_indicator` table.

**Rationale**: SMA, RSI, and VWAP are simple calculations that don't require heavy math libraries. Keeping dependencies minimal aligns with the project's approach. Latest values are persisted for the decision engine to query without recomputation.

**Alternatives considered**:
- pandas/ta-lib: Heavier dependencies for simple calculations
- Compute on every query (no persistence): Wasteful for the decision engine
- Full time series persistence: Out of scope per clarification

## Decision 7: Snapshot Approach

**Decision**: Use `StockSnapshotRequest` for real-time snapshots. Snapshots are ephemeral (not persisted) — displayed to CLI or consumed by the decision engine in-memory.

**Rationale**: Snapshots are point-in-time and only useful at query time. The `get_stock_snapshot` endpoint returns last trade, bid/ask, daily bar, and previous daily bar in a single call — everything needed for pre-trade checks.

**Key code pattern**:
```python
from alpaca.data.requests import StockSnapshotRequest

request = StockSnapshotRequest(symbol_or_symbols=["AAPL", "MSFT"])
snapshots = client.get_stock_snapshot(request)
# snapshots["AAPL"].latest_trade.price
# snapshots["AAPL"].latest_quote.bid_price / ask_price
# snapshots["AAPL"].daily_bar.volume / vwap
```

## Decision 8: Module Structure

**Decision**: Market data is NOT a BaseSource — it does not produce SourceDocumentMeta for LLM analysis. Instead, it gets its own module at `src/finance_agent/market/` with a `client.py` (API wrapper), `bars.py` (storage/query), `indicators.py` (computation), and `snapshot.py` (live quotes).

**Rationale**: Market data serves a different purpose than research sources. Research sources produce documents for LLM analysis. Market data produces structured numerical data for the decision engine. Forcing it through the BaseSource interface would be a poor fit.

**Alternatives considered**:
- Implement as a BaseSource: Bad fit — bars aren't documents to analyze
- Add to existing `data/` module: Conflates research data with market data
