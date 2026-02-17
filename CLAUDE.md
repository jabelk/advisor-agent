# Finance Agent

Research-powered investment system. Autonomous agents discover and analyze information, Claude synthesizes research, human makes trading decisions. See [Project Constitution](.specify/memory/constitution.md) for core principles, technology stack, and development workflow.

## Key Principles (from Constitution v1.3.0)

1. **Safety First** — Paper trading by default, hard limits on position size/daily loss/trade count, kill switch mandatory
2. **Research-Driven** — Every analysis must cite data sources; bull/bear perspectives before any signal; human decides
3. **Modular Architecture — Less Code, More Context** — Use MCP servers, n8n, existing tools. Only build what's truly custom. Every line of plumbing is context Claude Code can't use for innovation.
4. **Audit Everything** — Append-only logging of all signals, decisions, orders, and fills
5. **Security by Design** — No secrets in code/logs, separate paper/live keys, restricted container networking

## Architecture

```
n8n (schedules/triggers) → Python app (ingestion/analysis) → SQLite + files
                                                                    ↓
Claude Desktop ← MCP servers (research DB, Alpaca, QuantConnect) ← Custom MCP
                                                                    ↓
                                                              ntfy.sh (alerts)
```

- **Orchestration**: n8n (Docker on Intel NUC) — RSS monitoring, scheduled research, notifications
- **Execution**: Alpaca MCP server (interactive), alpaca-py SDK (programmatic)
- **Agent framework**: Claude Agent SDK (Python) for autonomous research
- **Interface**: Claude Desktop + MCP servers (conversational, not CLI)

## Development

- Python 3.12+, uv for packages, pytest for testing
- Broker: Alpaca Markets (Alpaca MCP server + alpaca-py SDK)
- Data: SEC EDGAR (edgartools), Finnhub (market signals), Tiingo (news), FRED (macro), RSS feeds, Reddit (PRAW), StockTwits
- Storage: SQLite (WAL mode) + sqlite-vec (embeddings) + filesystem
- MCP: Custom research DB server (FastMCP), Alpaca MCP, QuantConnect MCP
- Notifications: ntfy.sh (self-hosted on NUC)
- All features via spec-kit: specify → plan → tasks → implement
- Feature branches merged to `main` via PR
- See [Quality Gates](.specify/memory/constitution.md#quality-gates) in constitution

## Active Technologies
- Python 3.12+ with type hints throughout + alpaca-py (>=0.43), httpx, python-dotenv (local dev only) (001-project-scaffolding)
- SQLite (WAL mode, PRAGMA user_version migrations) (001-project-scaffolding)
- edgartools>=5.16, finnhub-python>=2.4, earningscall>=1.4, anthropic>=0.45, feedparser>=6.0, beautifulsoup4>=4.12, pydantic>=2.0; alpaca-py, httpx (002-research-ingestion)
- SQLite (extends existing DB with 5 new tables) + filesystem for raw documents (`research_data/`) (002-research-ingestion)

## Architecture Pivot (006)
Features 001-005 built a working end-to-end pipeline (~5,000 lines). The 006 research sprint identified that ~3,500 lines of execution/scoring/CLI code should be replaced with MCP servers + conversational Claude. The research core (~1,500 lines) is kept and enhanced. See `specs/006-architecture-research/` for full findings, architecture proposal, and migration notes.

## Recent Changes
- 006-architecture-research: Architecture pivot — research-first, human-decides system. Comprehensive research across MCP ecosystem, workflow automation (n8n), autonomous agents, AI frameworks, data sources, and architecture patterns. Updated constitution to v1.3.0.
- 004-decision-engine: Hybrid confidence scoring, risk controls, kill switch, proposal lifecycle
- 003-market-data: Alpaca historical OHLCV bars, real-time snapshots, technical indicators
- 002-research-ingestion: Finnhub free-tier market signals; EarningsCall.biz transcripts
- 001-project-scaffolding: Python 3.12+ project structure, SQLite, Alpaca SDK
