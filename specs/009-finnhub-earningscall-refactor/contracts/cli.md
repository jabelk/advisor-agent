# CLI Contract: Source Options

**Feature**: 009-finnhub-earningscall-refactor | **Date**: 2026-02-17

---

## `finance-agent research run`

### Source Selection

```
finance-agent research run [--source SOURCE] [--ticker TICKER] [--full]
```

| Option | Type | Description |
|--------|------|-------------|
| `--source` | repeatable | Limit to specific source(s). Can be specified multiple times. |
| `--ticker` | string | Limit to a specific watchlist ticker. |
| `--full` | flag | Force re-analysis of all documents (skip dedup). |

### Valid `--source` Values

| Source Name | Class | Description | Requires Key |
|------------|-------|-------------|-------------|
| `sec` | `SECEdgarSource` | SEC EDGAR filings (10-K, 10-Q, 8-K) | `EDGAR_IDENTITY` |
| `transcripts` | `EarningsCallSource` | Earnings call transcripts via EarningsCall.biz | Optional (`EARNINGSCALL_API_KEY`; demo mode without) |
| `finnhub` | `FinnhubMarketSource` | Market signals: analyst ratings, earnings history, insider activity, insider sentiment, company news | `FINNHUB_API_KEY` |
| `acquired` | `AcquiredPodcastSource` | Acquired podcast episodes (RSS) | None (RSS is free) |
| `stratechery` | `StratecherySource` | Stratechery articles (RSS) | `STRATECHERY_FEED_URL` |
| `investors` | `Investor13FSource` | 13F holdings filings | `EDGAR_IDENTITY` |

### Examples

```bash
# Run all available sources for all watchlist companies
finance-agent research run

# Run only Finnhub market signals
finance-agent research run --source finnhub

# Run Finnhub + transcripts for AAPL only
finance-agent research run --source finnhub --source transcripts --ticker AAPL

# Run transcripts in demo mode (AAPL/MSFT only, no API key needed)
finance-agent research run --source transcripts --ticker AAPL
```

---

## `finance-agent research status`

Displays source status including the new/refactored sources:

```
Sources:
  SEC EDGAR       OK (last: 2026-02-17, 42 documents)
  Transcripts     OK (last: 2026-02-17, 8 documents)
  Finnhub Mkt     OK (last: 2026-02-17, 25 documents)
  Acquired        OK (last: 2026-02-15, 3 documents)
  Stratechery     DISABLED
  13F Holdings    OK (last: 2026-02-10, 4 documents)
```

| Label | `source_type` in DB | Maps to CLI `--source` |
|-------|--------------------|-----------------------|
| SEC EDGAR | `sec_filing` | `sec` |
| Transcripts | `earnings_transcript` | `transcripts` |
| Finnhub Mkt | `finnhub_data` | `finnhub` |
| Acquired | `podcast_episode` | `acquired` |
| Stratechery | `article` | `stratechery` |
| 13F Holdings | `holdings_13f` | `investors` |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FINNHUB_API_KEY` | For finnhub source | `""` | Finnhub free-tier API key |
| `EARNINGSCALL_API_KEY` | No | `""` | EarningsCall.biz API key. If unset, operates in demo mode (AAPL/MSFT only, level=1 transcripts). |
