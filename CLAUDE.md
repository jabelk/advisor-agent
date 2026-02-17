# Finance Agent

AI-powered day trading agent. See [Project Constitution](.specify/memory/constitution.md) for core principles, technology stack, and development workflow.

## Key Principles (from Constitution v1.1.0)

1. **Safety First** — Paper trading by default, hard limits on position size/daily loss/trade count, kill switch mandatory
2. **Research-Driven** — Every trade proposal must cite data sources (SEC filings, transcripts, price data)
3. **Modular Architecture** — Independent layers: Data Ingestion → Research/Analysis → Decision Engine → Execution → Logging
4. **Audit Everything** — Append-only logging of all signals, decisions, orders, and fills
5. **Security by Design** — No secrets in code/logs, separate paper/live keys, restricted container networking

## Development

- Python 3.12+, uv for packages, pytest for testing
- Broker: Alpaca Markets (alpaca-py SDK + Alpaca MCP server)
- Data: SEC EDGAR (edgartools), EarningsCall.biz (transcripts), Finnhub (market signals), Alpaca market data
- Storage: SQLite + filesystem
- All features via spec-kit: specify → plan → tasks → implement
- Feature branches merged to `main` via PR
- See [Quality Gates](.specify/memory/constitution.md#quality-gates) in constitution

## Active Technologies
- Python 3.12+ with type hints throughou + alpaca-py (>=0.43), httpx, python-dotenv (local dev only) (001-project-scaffolding)
- SQLite (WAL mode, PRAGMA user_version migrations) (001-project-scaffolding)
- Python 3.12+ (existing project) + edgartools>=5.16, finnhub-python>=2.4, earningscall>=1.4, anthropic>=0.45, feedparser>=6.0, beautifulsoup4>=4.12, pydantic>=2.0 (new); alpaca-py, httpx (existing) (002-research-ingestion)
- SQLite (extends existing DB with 5 new tables) + filesystem for raw documents (`research_data/`) (002-research-ingestion)
- Python 3.12+ (existing project) + alpaca-py >=0.43 (existing) — `StockHistoricalDataClient`, `StockBarsRequest`, `StockSnapshotRequest` (003-market-data)
- SQLite (extends existing DB with 3 new tables: `price_bar`, `technical_indicator`, `market_data_fetch`), schema version 2 → 3 (003-market-data)
- Python 3.12+ (existing project) + alpaca-py (existing, TradingClient for account/positions), anthropic (existing, for LLM confidence adjustment), pydantic (existing, for structured models) (004-decision-engine)
- SQLite (extends existing DB with 4 new tables via migration 004) (004-decision-engine)

## Recent Changes
- 003-market-data: Added Alpaca historical OHLCV bars, real-time snapshots, technical indicators (SMA, RSI, VWAP), 4 CLI commands under `market` group
- 002-research-ingestion: Refactored Finnhub to free-tier market signals source; added EarningsCall.biz for transcripts
- 001-project-scaffolding: Added Python 3.12+ with type hints throughou + alpaca-py (>=0.43), httpx, python-dotenv (local dev only)
