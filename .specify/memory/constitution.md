# Advisor Agent Constitution

## Core Principles

### I. Client Data Isolation (NON-NEGOTIABLE)

This system MUST NEVER store, process, or transmit client personally identifiable information (PII). The system is for the advisor's personal investing education and productivity experimentation only. Any future Salesforce integration MUST use a developer sandbox with synthetic/test data only.

- No client names, account numbers, SSNs, or portfolio details
- No connection to production Schwab/Salesforce systems
- Clear separation between personal investing tools and professional tools
- If a feature could accidentally ingest client data, it MUST have explicit safeguards

Rationale: Financial advisors operate under strict regulatory requirements (SEC, FINRA). Mixing client data with personal tools creates compliance and legal risk.

### II. Research-Driven Decisions

Every trade decision MUST be grounded in data: SEC filings, earnings transcripts, price history, news, macro indicators. The LLM MUST NOT generate trade ideas from "intuition" or training data alone. Each analysis MUST cite the specific data sources that informed it.

- Research artifacts MUST be persisted locally before being used in decisions
- The system MUST distinguish between facts (from data sources) and inferences (from LLM analysis)
- Analysis SHOULD consider both bullish and bearish perspectives before producing a signal
- The human makes the final trading decision
- Backtesting or paper-trading validation SHOULD precede any strategy going live

Rationale: LLMs hallucinate. Financial decisions based on hallucinated data lose real money.

### III. Advisor Productivity

The system SHOULD reduce friction and increase the advisor's knowledge and efficiency:

- Plain language interfaces preferred — describe what you want, get structured output
- Pattern testing: describe a market pattern → system codifies it → tests against historical data
- Report generation: natural language queries → formatted reports
- Meeting prep: aggregate relevant market data and talking points
- Learning acceleration: help the advisor understand new concepts through interactive research

Rationale: The primary value is making the advisor more effective, not replacing their judgment.

### IV. Safety First

All trading operations MUST default to paper trading mode. Live trading MUST require explicit human approval.

- Kill switch: a single flag that halts all trading
- Maximum position size: configurable (default 10% of portfolio)
- Maximum daily loss: configurable (default 5% of portfolio)
- Options strategies MUST be paper-traded extensively before any live consideration
- Pattern strategies MUST show statistical significance across multiple market conditions

Rationale: This is a learning platform. Capital preservation is more important than capturing every opportunity.

### V. Security by Design

API keys and secrets MUST NEVER appear in source code, git history, or logs.

- All secrets stored in environment variables or encrypted secrets file
- `.env` files MUST be in `.gitignore` with restrictive permissions
- Paper trading keys and live trading keys stored separately
- Salesforce sandbox credentials stored separately from any production credentials

Rationale: Compromised API keys can drain accounts. Defense in depth is mandatory.

## Technology Stack

- **Language**: Python 3.12+ with type hints throughout
- **Package Manager**: uv (Astral)
- **Broker**: Alpaca Markets (paper + live), including options support
- **LLM**: Claude (via Anthropic API, MCP, or Claude Agent SDK)
- **Agent Framework**: Claude Agent SDK (Python)
- **Data Sources**: SEC EDGAR (edgartools), Finnhub (market signals — free tier), Alpaca market data, RSS feeds
- **LLM SDK**: anthropic (Python SDK) with Pydantic output models
- **MCP Servers**: Alpaca (trading), custom research DB (FastMCP)
- **Storage**: SQLite for structured data, filesystem for research artifacts
- **CRM (Future)**: Salesforce developer sandbox (Agentforce/Einstein + Claude agents)
- **Testing**: pytest, paper trading integration tests
- **CI**: GitHub Actions

## Development Workflow

- All work on feature branches, merged to `main` via PR
- Follow spec-kit workflow: specify → plan → tasks → implement
- Feature branches: `###-feature-name` convention
- One feature or fix per PR

## Quality Gates

### Pre-Commit
- Code passes linting
- All tests pass
- No secrets in staged files

### Pre-Merge
- PR reviewed
- All tests pass
- No security warnings
- Changes to safety module require explicit approval

**Version**: 1.0.0 | **Ratified**: 2026-03-08
