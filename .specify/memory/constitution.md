<!-- Sync Impact Report
  Version change: 1.2.0 → 1.3.0 (Minor - architecture pivot to research-first, human-decides system)
  Modified sections:
    - Core Principles: Updated II (Research-Driven) to emphasize conversational analysis and human decisions
    - Core Principles: Updated III (Modular Architecture) to reflect MCP-based execution and n8n orchestration
    - Technology Stack: Added n8n, Claude Agent SDK, FRED, Tiingo, Reddit/PRAW, StockTwits, sqlite-vec, ntfy.sh, FastMCP
    - Technology Stack: Marked Alpaca MCP as primary execution path alongside alpaca-py
  Templates requiring updates: None
  Follow-up TODOs: None
-->

# Finance Agent Constitution

## Core Principles

### I. Safety First (NON-NEGOTIABLE)

All trading operations MUST default to paper trading mode. Live trading MUST require explicit human approval for every order until the operator explicitly enables auto-execution for a narrowly scoped strategy class. The system MUST enforce hard limits at the execution layer:

- Maximum position size: configurable per-symbol and as percentage of portfolio (default 10%)
- Maximum daily loss: configurable dollar amount and percentage (default 5% of portfolio)
- Maximum trades per day: configurable cap (default 20)
- Kill switch: a single flag MUST immediately halt all order placement and cancel open orders
- Only limit orders by default; market orders MUST require explicit opt-in

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

- **Data Ingestion**: Fetches and stores market data, filings, transcripts, news, social sentiment, macro indicators
- **Research/Analysis**: LLM-powered analysis of ingested data, produces structured signals and multi-level summaries
- **Decision Support**: Presents synthesized research to human via Claude Desktop/MCP; human decides
- **Execution**: Broker API calls via Alpaca MCP server (interactive) or alpaca-py SDK (programmatic)
- **Orchestration**: n8n schedules ingestion, triggers analysis, sends notifications
- **Logging/Audit**: Records everything across all layers

Each layer communicates through well-defined interfaces. Swapping the broker (Alpaca to IBKR), the LLM (Claude to another model), or the data source MUST NOT require changes to other layers.

**Don't build what exists**: Use MCP servers, n8n workflows, and existing tools. Only write custom code for what's truly unique to this project. Every line of plumbing code maintained is context that Claude Code can't use for research innovation.

Rationale: This is an evolving experiment run by a solo developer coding through Claude Code. Context window is a real constraint — minimizing custom code maximizes the budget for research and analysis innovation.

### IV. Audit Everything

Every signal, decision, order intent, order response, and position change MUST be logged with timestamps to an append-only local store. Logs MUST include:

- Data source references (which filing, which transcript, which price bar)
- LLM prompts and responses that informed the decision
- Risk check results (pass/fail with parameter values)
- Order details (symbol, side, qty, type, time-in-force, status)
- Execution results (fill price, fill qty, rejection reason if applicable)

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
- **Broker**: Alpaca Markets (paper + live), accessed via Alpaca MCP server (interactive) and alpaca-py SDK (programmatic)
- **LLM**: Claude (via Anthropic API, MCP, or Claude Agent SDK), with support for swapping providers
- **Agent Framework**: Claude Agent SDK (Python) for autonomous research agents
- **Data Sources**: SEC EDGAR (edgartools — filings, Form 4, 13F), Finnhub (market signals, news), Tiingo (ticker-tagged news), FRED (macro indicators via fredapi), RSS feeds (feedparser), Reddit (PRAW), StockTwits (REST API), Alpaca market data
- **LLM SDK**: anthropic (Python SDK) for structured analysis with Pydantic output models; prompt caching for token efficiency
- **MCP Servers**: Alpaca (trading), custom research DB (FastMCP), QuantConnect (backtesting), sec-edgar-mcp (filings)
- **Storage**: SQLite for structured data (research signals, audit log, macro data, social sentiment), sqlite-vec for vector search, filesystem for research artifacts
- **Orchestration**: n8n (self-hosted Docker on NUC) for scheduling, triggers, and notifications
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
- All tests MUST pass (including paper trading integration tests if execution layer is touched)
- No security warnings from static analysis
- Changes to risk controls or execution layer MUST have explicit approval

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

**Version**: 1.3.0 | **Ratified**: 2026-02-16 | **Last Amended**: 2026-02-17
