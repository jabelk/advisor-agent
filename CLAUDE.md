# Finance Agent

Research-powered investment system. See [Project Constitution](.specify/memory/constitution.md) for core principles, technology stack, and development workflow.

## Key Principles (from Constitution v1.4.0)

1. **Safety First** — Paper trading by default, kill switch + risk limits persisted in DB, human approves all trades
2. **Research-Driven** — Every analysis must cite data sources; bull/bear perspectives before any signal; human decides
3. **Modular Architecture — Less Code, More Context** — Use MCP servers, n8n, existing tools. Only build what's truly custom.
4. **Audit Everything** — Append-only logging of all signals, decisions, and safety state changes
5. **Security by Design** — No secrets in code/logs, separate paper/live keys, restricted container networking

## Development

- Python 3.12+, uv for packages, pytest for testing
- Alpaca Markets: MCP server for interactive trading, alpaca-py SDK for market data API
- Data: SEC EDGAR (edgartools), Finnhub (market signals), EarningsCall.biz (transcripts), RSS feeds
- Storage: SQLite (WAL mode) + filesystem
- All features via spec-kit: specify → plan → tasks → implement
- Feature branches merged to `main` via PR
- See [Quality Gates](.specify/memory/constitution.md#quality-gates) in constitution

## Architecture

```
Data Ingestion → Research/Analysis → Audit
      ↓                  ↓              ↓
  data/sources/     research/       audit/
                         ↓
                     safety/  (kill switch + risk limits)
```

- **data/** — Filings, transcripts, news ingestion from 6 sources
- **research/** — LLM-powered analysis, signal generation, pipeline orchestration
- **safety/** — Kill switch and risk limit storage (extracted from former engine)
- **audit/** — Append-only event logging

## Active Technologies
- Python 3.12+ with type hints throughout + alpaca-py (>=0.43), httpx (001-project-scaffolding)
- SQLite (WAL mode, PRAGMA user_version migrations, schema v6) (001-project-scaffolding, 007-architecture-cleanup)
- edgartools>=5.16, finnhub-python>=2.4, earningscall>=1.4, anthropic>=0.45, feedparser>=6.0, beautifulsoup4>=4.12, pydantic>=2.0 (002-research-ingestion)
- Filesystem for raw documents (`research_data/`) (002-research-ingestion)

## Recent Changes
- 007-architecture-cleanup: Removed execution/engine/market layers (~3,500 lines). Extracted safety module. Migration 006 drops 8 tables, renames engine_state → safety_state. CLI streamlined. Architecture pivot to research-first system.
- 006-architecture-research: Architecture pivot — research-first, human-decides system. Updated constitution to v1.3.0.
