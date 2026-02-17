<!-- Sync Impact Report
  Version change: 1.4.0 → 1.5.0 (Minor - align constitution with 008-system-architecture decisions)
  Modified sections:
    - Technology Stack: Updated Data Sources (removed Reddit/StockTwits, added EarningsCall.biz, clarified Finnhub free tier)
    - Technology Stack: Updated LLM SDK (added Pydantic AI)
    - Technology Stack: Updated MCP Servers (removed QuantConnect)
    - Technology Stack: Updated Storage (removed sqlite-vec)
    - Technology Stack: Updated Orchestration (replaced n8n with systemd timers + NATS)
    - Core Principles III: Updated to reflect architecture decision against n8n
  Templates requiring updates: None
  Follow-up TODOs: None
-->

# Finance Agent Constitution

## Core Principles

### I. Safety First (NON-NEGOTIABLE)

All trading operations MUST default to paper trading mode. Live trading MUST require explicit human approval for every order. The system MUST persist safety guardrails in the database:

- Kill switch: a single flag that, when active, signals that all trading should be halted
- Maximum position size: configurable as percentage of portfolio (default 10%)
- Maximum daily loss: configurable as percentage of portfolio (default 5%)
- Maximum trades per day: configurable cap (default 20)
- Maximum positions per symbol: configurable cap (default 2)

These limits are stored in the `safety_state` table and enforced at the point of execution (currently via human review; future execution layers MUST check these before placing orders).

Rationale: This is a learning/experimentation platform with real money. Catastrophic loss prevention is more important than capturing every opportunity.

### II. Research-Driven Decisions

Every trade decision MUST be grounded in data: SEC filings, earnings transcripts, price history, news, macro indicators, insider activity, or social sentiment. The LLM MUST NOT generate trade ideas from "intuition" or training data alone. Each analysis MUST cite the specific data sources that informed it.

- Research artifacts (filings, transcripts, analysis summaries) MUST be persisted locally before being used in decisions
- The system MUST distinguish between facts (from data sources) and inferences (from LLM analysis)
- Analysis SHOULD consider both bullish and bearish perspectives before producing a signal
- The human makes the final trading decision — the system provides research and analysis, not automated execution
- Conversational analysis (Claude examining nuance, narrative, tone) is preferred over deterministic scoring formulas
- Backtesting or paper-trading validation SHOULD precede any strategy going live

Rationale: LLMs hallucinate. Financial decisions based on hallucinated data lose real money. Conversational analysis captures nuance that scoring formulas cannot.

### III. Modular Architecture — Less Code, More Context

The system MUST be composed of independent, swappable layers:

- **Data Ingestion**: Fetches and stores filings, transcripts, news, market signals from multiple sources
- **Research/Analysis**: LLM-powered analysis of ingested data, produces structured signals
- **Safety**: Kill switch and risk limit storage (guardrails for any future execution layer)
- **Logging/Audit**: Records everything across all layers

Decision support and execution are handled externally — the human reviews research via Claude Desktop/MCP and places trades via Alpaca's interface or MCP server. Autonomous agents (monitoring, scanning, briefing) run as Python scripts on the NUC triggered by systemd timers, communicating via NATS. Future layers (automated execution) can be added without modifying existing code.

Each layer communicates through well-defined interfaces. Swapping the LLM (Claude to another model) or the data source MUST NOT require changes to other layers.

**Don't build what exists**: Use MCP servers, systemd timers, and existing tools. Only write custom code for what's truly unique to this project. Every line of plumbing code maintained is context that Claude Code can't use for research innovation.

Rationale: This is an evolving experiment run by a solo developer coding through Claude Code. Context window is a real constraint — minimizing custom code maximizes the budget for research and analysis innovation.

### IV. Audit Everything

Every signal, decision, and safety state change MUST be logged with timestamps to an append-only local store. Logs MUST include:

- Data source references (which filing, which transcript, which market signal)
- LLM prompts and responses that informed the analysis
- Safety state changes (kill switch toggles, risk setting updates)
- Research pipeline runs (sources ingested, signals generated, errors)

When an execution layer is added in the future, it MUST also log: order details, risk check results, and execution results.

Rationale: Without an audit trail, you cannot debug bad trades, improve strategies, or understand what went wrong.

### V. Security by Design

API keys and secrets MUST NEVER appear in source code, git history, or logs. The system MUST enforce:

- All secrets stored in environment variables or an encrypted secrets file (e.g., `age`-encrypted)
- `.env` files MUST have restrictive file permissions (`chmod 600`) and MUST be in `.gitignore`
- Paper trading keys and live trading keys MUST be stored separately with distinct environment variable names
- The agent runtime SHOULD run in a Docker container with network access restricted to necessary API endpoints only
- Live trading keys MUST NOT be present in the development environment

Rationale: Compromised trading API keys can drain an account. Defense in depth is mandatory when real money is involved.

## Technology Stack

- **Language**: Python 3.12+ with type hints throughout
- **Package Manager**: uv (Astral)
- **Broker**: Alpaca Markets (paper + live), accessed via Alpaca MCP server (interactive trading); alpaca-py SDK for market data API
- **LLM**: Claude (via Anthropic API, MCP, or Claude Agent SDK), with support for swapping providers
- **Agent Framework**: Claude Agent SDK (Python) for autonomous research agents
- **Data Sources**: SEC EDGAR (edgartools — filings, Form 4, 13F), Finnhub (market signals, news — free tier), EarningsCall.biz (earnings transcripts), Tiingo (ticker-tagged news), FRED (macro indicators via fredapi), SEC RSS feeds (feedparser), Alpaca market data
- **LLM SDK**: anthropic (Python SDK) for structured analysis with Pydantic output models; Pydantic AI for type-safe structured outputs; prompt caching for token efficiency
- **MCP Servers**: Alpaca (trading), custom research DB (FastMCP), sec-edgar-mcp (filings)
- **Storage**: SQLite for structured data (research signals, audit log, macro data), filesystem for research artifacts
- **Orchestration**: systemd timers (scheduling on NUC) + NATS (event messaging between agents)
- **Notifications**: ntfy.sh (self-hosted on NUC) for mobile push alerts
- **Runtime**: Intel NUC (home server), Docker for isolation, NATS available for messaging if needed
- **CI**: GitHub Actions (private runner already available on NUC)
- **Testing**: pytest, with paper trading integration tests

## Development Workflow

- All work happens on feature branches, merged to `main` via pull request.
- Follow the spec-kit workflow: specify → plan → tasks → implement.
- Commit after each logical unit of work with a descriptive message.
- Keep PRs focused — one feature or fix per PR.
- Each feature branch follows the `###-feature-name` convention (e.g., `1-research-pipeline`).
- Configuration changes that affect trading behavior MUST be reviewed before deployment.
- The system MUST support running entirely in paper mode with no code changes — switching to live is purely a configuration change (different API keys + `TRADING_MODE=live`).
- Secrets MUST be validated at startup: if required secrets are missing, the system MUST fail fast with a clear error.

## Quality Gates

### Pre-Commit Requirements

- Code MUST pass linting without errors
- All existing tests MUST pass
- No secrets or API keys in staged files

### Pre-Merge Requirements

- Pull request MUST be reviewed (human or automated)
- PR MUST reference applicable constitution principles where relevant
- All tests MUST pass (including paper trading integration tests if broker-facing code is touched)
- No security warnings from static analysis
- Changes to safety module (kill switch, risk limits) MUST have explicit approval

### Release Requirements

- All quality gates satisfied
- Version incremented per semantic versioning
- CHANGELOG updated with user-facing changes

## Governance

This constitution governs all development on the finance-agent project. Amendments require:

1. A documented rationale for the change
2. Review of impact on existing features (especially safety and security principles)
3. Updated version number following semantic versioning

Principles I (Safety First) and V (Security by Design) are elevated constraints — relaxing them requires explicit justification and the operator MUST acknowledge the risk in writing (e.g., a signed-off config change, not just a code comment).

All PRs MUST verify compliance with these principles. Complexity MUST be justified — prefer simple, working solutions over elegant abstractions.

**Version**: 1.5.0 | **Ratified**: 2026-02-16 | **Last Amended**: 2026-02-17
