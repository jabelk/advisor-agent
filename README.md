# Advisor Agent

AI-powered productivity and research tools for financial advisors. Forked from [finance-agent](https://github.com/jabelk/finance-agent).

## Overview

Two-track system for a Charles Schwab financial consultant:

1. **Personal Investing & Pattern Lab** — Describe market patterns in plain text, codify them into rules, and test them via Alpaca paper trading. Includes options strategy testing and the full research pipeline from finance-agent.

2. **Advisor Productivity** (future) — Salesforce developer sandbox integration, plain language report generation, meeting prep tools, market commentary generation.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Astral package manager)
- An [Alpaca Markets](https://alpaca.markets/) account with paper trading API keys

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/jabelk/advisor-agent.git
cd advisor-agent
uv sync

# 2. Configure environment
cp .env.example .env
chmod 600 .env
# Edit .env with your Alpaca paper trading API keys

# 3. Run health check
uv run finance-agent health
```

## Research Pipeline (Inherited)

See [finance-agent](https://github.com/jabelk/finance-agent) for the full research pipeline documentation. This project inherits all data ingestion, analysis, and signal generation capabilities.

## Development

```bash
# Run unit tests
uv run pytest tests/unit/

# Run integration tests (requires API keys in .env)
uv run pytest tests/integration/

# Lint and type check
uv run ruff check src/ tests/
uv run mypy src/
```

## Architecture

See the [project constitution](.specify/memory/constitution.md) for guiding principles.

**Important**: This system is for personal investing research and advisor productivity experimentation only. No client PII is stored or processed. See Constitution Principle I (Client Data Isolation).
