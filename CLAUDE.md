# Finance Agent

Research-powered investment system. See [Project Constitution](.specify/memory/constitution.md) for core principles, technology stack, and development workflow.

## Key Principles (from Constitution v1.5.0)

1. **Safety First** — Paper trading by default, kill switch + risk limits persisted in DB, human approves all trades
2. **Research-Driven** — Every analysis must cite data sources; bull/bear perspectives before any signal; human decides
3. **Modular Architecture — Less Code, More Context** — Use MCP servers, systemd timers, existing tools. Only build what's truly custom.
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
Intel NUC (always-on):
  systemd timers → Python agents → SQLite + research_data/
  NATS (event messaging) | ntfy.sh (notifications) | FastMCP (research DB)

Claude Desktop (on-demand):
  Alpaca MCP (trading) | SEC EDGAR MCP (filings) | Research DB MCP (via mcp-remote)
```

- **data/** — Filings, transcripts, news, market signals from 6+ sources
- **research/** — LLM-powered analysis, signal generation, pipeline orchestration
- **safety/** — Kill switch and risk limit storage
- **mcp/** — Custom FastMCP server exposing research DB to Claude Desktop (planned)
- **agents/** — Monitor, scanner, research, briefing agents triggered by systemd (planned)

## Active Technologies
- Python 3.12+ with type hints throughout + alpaca-py (>=0.43), httpx (001-project-scaffolding)
- SQLite (WAL mode, PRAGMA user_version migrations, schema v6) (001-project-scaffolding, 007-architecture-cleanup)
- edgartools>=5.16, finnhub-python>=2.4, earningscall>=1.4, anthropic>=0.45, feedparser>=6.0, beautifulsoup4>=4.12, pydantic>=2.0 (002-research-ingestion)
- Filesystem for raw documents (`research_data/`) (002-research-ingestion)
- Orchestration: systemd timers + NATS (not n8n); notifications via ntfy.sh (008-system-architecture)
- MCP Servers: Alpaca (trading), sec-edgar-mcp (filings), custom FastMCP (research DB) (008-system-architecture)
- Agent Framework: Claude Agent SDK + Pydantic AI for structured outputs (008-system-architecture)
- New data sources planned: FRED, Tiingo, SEC RSS, 13F, Form 4, Quiver Quantitative (008-system-architecture)
- Python 3.12+ (existing codebase) + finnhub-python>=2.4 (existing), earningscall>=1.4 (new), anthropic (existing), pydantic (existing) (009-finnhub-earningscall-refactor)
- SQLite (existing tables — no schema changes) + filesystem for raw documents (009-finnhub-earningscall-refactor)
- Python 3.12+ (existing codebase) + `fastmcp>=2.14,<3` (new); sqlite3, pathlib (stdlib); existing `finance_agent` package (010-mcp-integration)
- SQLite read-only access (`file:{path}?mode=ro` URI), filesystem for document conten (010-mcp-integration)

## Recent Changes
- 007-architecture-cleanup: Removed execution/engine/market layers (~3,500 lines). Extracted safety module. Migration 006 drops 8 tables, renames engine_state → safety_state. CLI streamlined. Architecture pivot to research-first system.
- 006-architecture-research: Architecture pivot — research-first, human-decides system. Updated constitution to v1.3.0.
