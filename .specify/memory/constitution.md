<!-- Sync Impact Report
  Version change: 1.0.0 → 1.1.0 (Minor - expanded Development Workflow, added Quality Gates)
  Modified sections:
    - Development Workflow: Added PR requirement, branch conventions, commit guidance
    - Added: Quality Gates (pre-commit, pre-merge, release)
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ (compatible)
    - .specify/templates/spec-template.md ✅ (compatible)
    - .specify/templates/tasks-template.md ✅ (compatible)
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

Every trade proposal MUST be grounded in data: SEC filings, earnings transcripts, price history, news, or fundamental metrics. The LLM MUST NOT generate trade ideas from "intuition" or training data alone. Each proposal MUST cite the specific data sources that informed it.

- Research artifacts (filings, transcripts, analysis summaries) MUST be persisted locally before being used in decisions
- The system MUST distinguish between facts (from data sources) and inferences (from LLM analysis)
- Backtesting or paper-trading validation SHOULD precede any strategy going live

Rationale: LLMs hallucinate. Financial decisions based on hallucinated data lose real money.

### III. Modular Architecture

The system MUST be composed of independent, swappable layers:

- **Data Ingestion**: Fetches and stores market data, filings, transcripts, news
- **Research/Analysis**: LLM-powered analysis of ingested data, produces structured signals
- **Decision Engine**: Applies rules + signals to generate trade proposals with risk checks
- **Execution**: Translates approved proposals into broker API calls (Alpaca)
- **Logging/Audit**: Records everything across all layers

Each layer communicates through well-defined interfaces. Swapping the broker (Alpaca to IBKR), the LLM (Claude to another model), or the data source MUST NOT require changes to other layers.

Rationale: This is an evolving experiment. The ability to swap components without rewriting the system is essential for rapid iteration.

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
- **Broker**: Alpaca Markets (paper + live), accessed via official alpaca-py SDK and Alpaca MCP server
- **LLM**: Claude (via Anthropic API or MCP), with support for swapping providers
- **Data Sources**: SEC EDGAR (free, via edgartools), Finnhub (earnings transcripts), Alpaca market data (included)
- **Storage**: SQLite for structured data (trades, positions, audit log), filesystem for research artifacts (filings, transcripts)
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
- The system MUST support running entirely in paper mode with no code changes — switching to live is purely a configuration change (different API keys + `ALPACA_PAPER_TRADE=False`).
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

**Version**: 1.1.0 | **Ratified**: 2026-02-16 | **Last Amended**: 2026-02-16
