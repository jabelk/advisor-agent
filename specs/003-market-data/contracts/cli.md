# CLI Contract: Market Data Integration (003)

**Date**: 2026-02-16
**Feature**: 003-market-data

## New Commands

### `finance-agent market fetch`

Fetch historical OHLCV bars for watchlist companies from Alpaca.

```
finance-agent market fetch [--ticker TICKER] [--timeframe {day,hour}] [--full]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--ticker` | No | all watchlist | Limit to a specific ticker |
| `--timeframe` | No | both | Limit to 'day' or 'hour' (fetches both if omitted) |
| `--full` | No | false | Force full re-fetch instead of incremental |

**Behavior**:
- Without `--ticker`: fetches bars for all active watchlist companies
- Incremental by default: only fetches bars newer than the latest stored bar
- `--full`: re-fetches the full window (2 years daily, 30 days hourly)
- Computes and persists latest technical indicators after fetching
- Logs each fetch to audit trail

**Example output**:
```
Market Data Fetch — 2026-02-16T14:30:00Z
Watchlist: 3 companies (AAPL, NVDA, MSFT) | Timeframes: day, hour

AAPL:
  day: 5 new bars (2026-02-10 to 2026-02-14)
  hour: 35 new bars (2026-02-10 to 2026-02-14)
  Indicators: SMA-20=234.50 SMA-50=228.30 RSI-14=62.1 VWAP=233.80
NVDA:
  day: 5 new bars (2026-02-10 to 2026-02-14)
  hour: 35 new bars (2026-02-10 to 2026-02-14)
  Indicators: SMA-20=142.10 SMA-50=138.50 RSI-14=55.3 VWAP=141.90
MSFT:
  day: 5 new bars (2026-02-10 to 2026-02-14)
  hour: 35 new bars (2026-02-10 to 2026-02-14)
  Indicators: SMA-20=415.20 SMA-50=408.90 RSI-14=48.7 VWAP=414.50

Summary:
  Bars: 15 daily, 105 hourly (120 total new)
  Indicators: 12 updated
  Errors: 0
  Duration: 8s
```

**Exit codes**:
- 0: success (even if some tickers had no new bars)
- 1: all tickers failed or no watchlist

### `finance-agent market snapshot`

Get real-time price snapshot for a ticker.

```
finance-agent market snapshot TICKER [TICKER ...]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `TICKER` | Yes | — | One or more ticker symbols |

**Behavior**:
- Queries Alpaca snapshot endpoint (IEX feed on free tier)
- Works for any ticker, not limited to watchlist
- Shows market status (open/closed)

**Example output**:
```
AAPL  $234.56  bid $234.55 × 200  ask $234.57 × 100  vol 45.2M  vwap $233.80
NVDA  $142.30  bid $142.28 × 500  ask $142.32 × 300  vol 28.7M  vwap $141.90

Market: OPEN (as of 2026-02-16 14:30 ET)
```

**Exit codes**:
- 0: success
- 1: API error or invalid ticker

### `finance-agent market status`

Show stored market data coverage summary.

```
finance-agent market status
```

**Behavior**:
- Shows per-ticker: date range of stored bars, bar count, last fetch time
- Shows latest indicator values
- Shows overall summary

**Example output**:
```
Market Data Status:

  Ticker   Timeframe   Bars   From         To           Last Fetch
  AAPL     day         504    2024-02-16   2026-02-14   2026-02-16 14:30
  AAPL     hour        210    2026-01-17   2026-02-14   2026-02-16 14:30
  NVDA     day         504    2024-02-16   2026-02-14   2026-02-16 14:30
  NVDA     hour        210    2026-01-17   2026-02-14   2026-02-16 14:30

Latest Indicators:
  Ticker   SMA-20    SMA-50    RSI-14   VWAP      As Of
  AAPL     234.50    228.30    62.1     233.80    2026-02-14
  NVDA     142.10    138.50    55.3     141.90    2026-02-14

Total: 1,428 bars across 2 tickers
```

**Exit codes**:
- 0: success
- 1: database error

### `finance-agent market indicators`

Compute (or recompute) technical indicators for watchlist companies.

```
finance-agent market indicators [--ticker TICKER]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--ticker` | No | all watchlist | Limit to a specific ticker |

**Behavior**:
- Computes SMA-20, SMA-50, RSI-14, VWAP from stored daily bars
- Persists latest values (upserts technical_indicator table)
- Skips indicators that don't have enough bars (with message)
- Normally called automatically by `market fetch`, but available for manual recomputation

**Example output**:
```
Technical Indicators:

  AAPL: SMA-20=234.50 SMA-50=228.30 RSI-14=62.1 VWAP=233.80
  NVDA: SMA-20=142.10 SMA-50=138.50 RSI-14=55.3 VWAP=141.90
  MSFT: SMA-20=415.20 SMA-50=408.90 RSI-14=48.7 VWAP=414.50 (SMA-50: only 42 bars, skipped)
```

## Modified Commands

### `finance-agent health` (existing)

Add market data connectivity check after broker API check:
```
Market Data API: OK (IEX feed, 195/200 requests remaining)
```

## Argument Integration with Existing CLI

The `market` command group follows the same pattern as `research` and `watchlist`:

```python
# Parser structure
market_parser = subparsers.add_parser("market", help="Market data operations")
market_sub = market_parser.add_subparsers(dest="market_command")

fetch_parser = market_sub.add_parser("fetch", help="Fetch historical bars")
fetch_parser.add_argument("--ticker", help="Limit to specific ticker")
fetch_parser.add_argument("--timeframe", choices=["day", "hour"])
fetch_parser.add_argument("--full", action="store_true")

snapshot_parser = market_sub.add_parser("snapshot", help="Get real-time snapshot")
snapshot_parser.add_argument("tickers", nargs="+", help="Ticker symbols")

market_sub.add_parser("status", help="Show market data status")

indicators_parser = market_sub.add_parser("indicators", help="Compute indicators")
indicators_parser.add_argument("--ticker", help="Limit to specific ticker")
```
