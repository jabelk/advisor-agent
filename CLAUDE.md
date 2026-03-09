# Advisor Agent

AI-powered productivity and research tools for financial advisors. Forked from [finance-agent](https://github.com/jabelk/finance-agent).

See [Project Constitution](.specify/memory/constitution.md) for core principles, technology stack, and development workflow.

## Target User

**Jordan McElroy** — Financial Consultant at Charles Schwab, Truckee CA office (aiming for Reno office). Generalist advisor who manages client relationships and pulls in specialists. Series 7/63/65 licensed. US Army veteran (Blackhawk crew chief, Afghanistan, Operation Freedom's Sentinel — Personnel Recovery Team). Currently uses AI for basic productivity (equations, simple tasks). Wants to level up with AI for both personal investing and professional productivity.

LinkedIn reference docs (gitignored, not committed):
- `reference/Jordan McElroy _ LinkedIn.pdf` — Full profile
- `reference/Experience _ Jordan McElroy _ LinkedIn.pdf` — Detailed experience
- `reference/Activity _ Jordan McElroy _ LinkedIn.pdf` — Posts and activity
- `reference/Activity _ Jordan McElroy _ LinkedIn-comments.pdf` — Comments

**Schwab career progression** (4 yrs 9 mos total):
- Client Service Specialist (Jun 2021 – Aug 2024)
- Associate Financial Consultant (Aug 2024 – Oct 2025) — earned Series 65, Series 63
- Financial Consultant (Jul 2025 – present)

**Other background**: Kaplan University (2014–2016). Biathlete — US Biathlon team, 2013 US Junior World Championship, CISM team 2014–2015, competed across 3 continents. Ski coach at Auburn Ski Club (biathlon/racing). Heavy equipment operator.

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
- **Note**: Jordan works at Charles Schwab, which uses its own proprietary platforms (Schwab Advisor Center, StreetSmart Edge, Schwab Advisor Services). Schwab does NOT use Salesforce as its primary CRM — confirm with Jordan what tools he actually uses day-to-day.
- Salesforce developer sandbox as a **learning/experimentation platform** — not mirroring his Schwab work environment, but building transferable CRM automation skills
- Dual approach: Salesforce Agentforce/Einstein + Claude-based agents (portable patterns that could apply to any CRM)
- Plain language → reports, SOQL queries, workflow automation (sandbox with synthetic data only)
- Meeting prep, client briefing generation (using public market data, never client data)
- Market commentary and talking points
- Schwab-specific tools research: understand what Jordan can actually automate within Schwab's ecosystem vs. what needs to be built externally

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
  - Example: "pharma company has big news → stock spikes → buy options on the dip within 2 days" — Jordan observed this working for ~3 months in 2025, then it stopped. Pattern Lab should help test why/when patterns work and when they break down.
- Options support via Alpaca (Jordan is actively trading options personally)
- Salesforce developer sandbox (learning platform, not mirroring Schwab tools)
- Schwab ecosystem research: what can be automated within Schwab's actual advisor tools?
- Advisor-specific research tools (meeting prep, market commentary)
- A/B testing framework for pattern strategies

## Active Technologies
- Python 3.12+ + alpaca-py (broker + market data), anthropic (Claude for pattern parsing), pydantic (structured models), fastmcp (MCP tool exposure) (011-pattern-lab)
- SQLite (WAL mode) — new migration 007 adds pattern tables alongside existing schema (011-pattern-lab)
- Python 3.12+ + alpaca-py 0.43.2 (options trading via PositionIntent.SELL_TO_OPEN, OptionLegRequest, OptionHistoricalDataClient), anthropic (Claude API for pattern parsing), pydantic 2.0+ (structured models) (012-covered-call-strategy)
- SQLite (WAL mode) — extends existing Pattern Lab tables, adds covered_call_cycle table (012-covered-call-strategy)
- Python 3.12+ + alpaca-py (market data), anthropic (pattern parsing), pydantic (models) (013-pharma-news-dip)
- SQLite (WAL mode) — no new tables needed, extends existing backtest/trade models (013-pharma-news-dip)
- Python 3.12+ with type hints + alpaca-py (market data), pydantic (models), scipy (statistical tests — Fisher's exact, Welch's t-test) (014-pattern-lab-extensions)
- SQLite (WAL mode) — extends existing backtest_result table, no new tables (014-pattern-lab-extensions)
- Python 3.12+ with type hints + fastmcp (MCP tool exposure), alpaca-py (market data), scipy (stats), pydantic (models) (015-mcp-pattern-tools)
- SQLite (WAL mode) — read-only for pattern queries, read-write for market data cache (015-mcp-pattern-tools)
- Python 3.12+ with type hints + alpaca-py 0.43+ (OptionHistoricalDataClient, OptionBarsRequest), pydantic (models) (016-real-options-data)
- SQLite (WAL mode) — new `option_price_cache` table via migration 009 (016-real-options-data)
- Python 3.12+ with type hints + alpaca-py 0.43+ (StockHistoricalDataClient for market data), pydantic (models), fastmcp (MCP tool exposure) (017-live-pattern-alerts)
- SQLite (WAL mode) — new `pattern_alert` table via migration 010, add `auto_execute` column to `trading_pattern` (017-live-pattern-alerts)
- Python 3.12+ with type hints + alpaca-py 0.43+ (market data), pydantic (models), fastmcp (MCP tools) (018-track1-dashboard-perf)
- SQLite (WAL mode) — no new tables; all dashboard/performance data is derived from existing tables. Schedule config stored as a launchd plist file. (018-track1-dashboard-perf)
- Python 3.12+ with type hints + anthropic (Claude API for brief/commentary generation), pydantic (models), fastmcp (MCP tools) (019-sfdc-sandbox)
- SQLite (WAL mode) — new migration for sandbox_client table; meeting briefs and commentary generated on-the-fly (not persisted) (019-sfdc-sandbox)
- Python 3.12+ with type hints + anthropic (Claude API for NL→filter translation), simple-salesforce (Salesforce SOQL queries), pydantic (filter models + validation), fastmcp (MCP tools) (020-client-list-builder)
- Salesforce (client data, unchanged from 019); local JSON file (saved list definitions — lightweight, no migration needed) (020-client-list-builder)
- Python 3.12+ with type hints + simple_salesforce (existing — sf.mdapi for ListViews, sf.restful for Reports), pydantic (existing — CompoundFilter model), anthropic (existing — NL translation) (021-sfdc-native-lists)
- Salesforce platform (ListViews via Metadata API, Reports via Analytics REST API) — no local storage for this feature (021-sfdc-native-lists)
- Python 3.12+ with type hints + simple_salesforce (SFDC API), pydantic (models), fastmcp (MCP tools), anthropic (not needed for this feature) (022-sfdc-task-logging)
- Salesforce Task standard object (no local SQLite) (022-sfdc-task-logging)

## Recent Changes
- 011-pattern-lab: Added Python 3.12+ + alpaca-py (broker + market data), anthropic (Claude for pattern parsing), pydantic (structured models), fastmcp (MCP tool exposure)
