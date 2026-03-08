# Advisor Agent

AI-powered productivity and research tools for financial advisors. Forked from [finance-agent](https://github.com/jabelk/finance-agent).

See [Project Constitution](.specify/memory/constitution.md) for core principles, technology stack, and development workflow.

## Target User

**Jordan McElroy** — Financial Consultant at Charles Schwab, Truckee CA office (aiming for Reno office). Generalist advisor who manages client relationships and pulls in specialists. Series 7/63/65 licensed. US Army veteran (Blackhawk crew chief, Afghanistan). Currently uses AI for basic productivity (equations, simple tasks). Wants to level up with AI for both personal investing and professional productivity.

## Key Principles (from Constitution v1.0.0)

1. **Client Data Isolation** — Personal investing tools are completely separated from any client-related work. No client PII ever touches this system.
2. **Research-Driven** — Every analysis must cite data sources; bull/bear perspectives before any signal; human decides
3. **Advisor Productivity** — Plain language interfaces for report generation, data queries, pattern testing. Reduce friction, increase knowledge.
4. **Safety First** — Paper trading by default for pattern testing. Human approves all trades.
5. **Security by Design** — No secrets in code/logs, separate paper/live keys

## Tracks

### Track 1: Personal Investing & Pattern Lab
- Alpaca Markets paper trading (inherited from finance-agent)
- Pattern description → rule codification → backtesting
- Options strategy testing
- Market research pipeline (inherited from finance-agent)

### Track 2: Advisor Productivity (Future)
- Salesforce developer sandbox for experimentation
- Plain language → reports, SOQL queries, workflow automation
- Dual approach: Salesforce Agentforce/Einstein + Claude-based agents
- Meeting prep, client briefing generation
- Market commentary and talking points

## Development

- Python 3.12+, uv for packages, pytest for testing
- Alpaca Markets: MCP server for interactive trading, alpaca-py SDK for market data API
- Data: SEC EDGAR (edgartools), Finnhub (market signals), RSS feeds
- Storage: SQLite (WAL mode) + filesystem
- All features via spec-kit: specify → plan → tasks → implement
- Feature branches merged to `main` via PR

## Inherited from finance-agent

This project started as a copy of finance-agent and inherits:
- Market data ingestion pipeline (SEC EDGAR, Finnhub)
- SQLite storage patterns (WAL mode, migrations)
- MCP server setup for Claude Desktop
- Safety module (kill switch, risk limits)
- Research/analysis framework
- spec-kit workflow and commands

## What's New (Planned)

- Pattern Lab: describe trading patterns in plain text → codify → test via Alpaca paper trading
- Options support via Alpaca
- Salesforce integration (developer sandbox)
- Advisor-specific research tools (client meeting prep, market commentary)
- A/B testing framework for pattern strategies
