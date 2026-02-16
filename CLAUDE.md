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
- Data: SEC EDGAR (edgartools), Finnhub (transcripts), Alpaca market data
- Storage: SQLite + filesystem
- All features via spec-kit: specify → plan → tasks → implement
- Feature branches merged to `main` via PR
- See [Quality Gates](.specify/memory/constitution.md#quality-gates) in constitution

## Active Technologies
- Python 3.12+ with type hints throughou + alpaca-py (>=0.43), httpx, python-dotenv (local dev only) (001-project-scaffolding)
- SQLite (WAL mode, PRAGMA user_version migrations) (001-project-scaffolding)

## Recent Changes
- 001-project-scaffolding: Added Python 3.12+ with type hints throughou + alpaca-py (>=0.43), httpx, python-dotenv (local dev only)
