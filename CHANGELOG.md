# Changelog

All notable changes to the finance-agent project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.3.0] - 2026-02-16

### Added

- Market data integration via Alpaca Data API (historical OHLCV bars + real-time snapshots)
- Historical daily bars (2yr lookback) and hourly bars (30d lookback) with incremental fetch
- Technical indicators: SMA-20, SMA-50, RSI-14, VWAP — pure Python, latest values persisted
- Token-bucket rate limiter at 180 req/min (90% of Alpaca free-tier limit)
- `finance-agent market fetch` — fetch bars for watchlist companies with auto-indicator computation
- `finance-agent market snapshot` — real-time price/bid/ask/volume for any ticker
- `finance-agent market status` — summary of stored data coverage and latest indicators
- `finance-agent market indicators` — recompute technical indicators on demand
- Market Data API connectivity check in `finance-agent health`
- SQLite schema v3 with 3 new tables: price_bar, technical_indicator, market_data_fetch
- Audit logging for all fetch operations via market_data_fetch table
- 27 unit tests for market module, 5 integration tests against live Alpaca API (163 total)

## [0.2.0] - 2026-02-16

### Added

- Research data ingestion pipeline with 5 configurable sources
- SEC EDGAR filing ingestion (10-K, 10-Q, 8-K) via edgartools
- EarningsCall.biz transcript ingestion with speaker attribution (replaces Finnhub transcripts)
- Finnhub free-tier market signals: analyst ratings, earnings history, insider activity, insider sentiment, company news
- Acquired podcast RSS feed ingestion with episode classification (deep-dive, interview, acq2)
- Stratechery article ingestion with HTML-to-text conversion and content classification
- 13F institutional holdings tracking for notable investors
- LLM-powered document analysis using Claude API with structured signal output
- Section-based map-reduce analysis for large documents (>80K chars)
- Company watchlist management (`finance-agent watchlist add/remove/list`)
- Notable investor tracking (`finance-agent investors add/remove/list`)
- Research signal query and filtering (`finance-agent signals <TICKER>`)
- Company research profile view (`finance-agent profile <TICKER>`)
- Research pipeline orchestrator with per-source ingestion and analysis
- Pydantic models for structured signal types (sentiment, risk, guidance, metrics, leadership)
- Fact vs. inference evidence classification for all research signals
- Document deduplication via source_id and content_hash
- SQLite schema v2 with 5 new tables: company, source_document, research_signal, notable_investor, ingestion_run
- 5 new LLM analysis prompts for Finnhub market signal content types
- 136 unit tests covering all new modules

## [0.1.0] - 2026-02-16

### Added

- Project scaffolding with `src/` layout and modular architecture layers
- Configuration management via environment variables with paper/live mode detection
- SQLite database with WAL mode, automatic schema migrations via `PRAGMA user_version`
- Append-only audit log with `BEFORE UPDATE/DELETE` trigger enforcement
- `finance-agent health` command validating config, database, and Alpaca broker connectivity
- `finance-agent version` command
- Docker multi-stage build with uv and Docker Compose secrets support
- GitHub Actions deployment workflow for Intel NUC self-hosted runner
- Unit tests for config, database, and audit modules (42 tests)
- Integration test for health check against paper trading API
