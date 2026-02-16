# Finance Agent

AI-powered day trading agent using Alpaca Markets.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Astral package manager)
- An [Alpaca Markets](https://alpaca.markets/) account with paper trading API keys

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/jabelk/finance-agent.git
cd finance-agent
uv sync

# 2. Configure environment
cp .env.example .env
chmod 600 .env
# Edit .env with your Alpaca paper trading API keys

# 3. Run health check
uv run finance-agent health
```

Expected output:
```
[PAPER MODE] Finance Agent v0.1.0
Configuration: OK (all required settings present)
Database: OK (finance_agent.db, schema version 1)
Broker API: OK (account ACTIVE, buying power: $X,XXX.XX)
```

## Development

```bash
# Run unit tests (no API keys needed)
uv run pytest tests/unit/

# Run integration tests (requires paper trading API keys in .env)
uv run pytest tests/integration/

# All tests with coverage
uv run pytest --cov=finance_agent

# Lint and type check
uv run ruff check src/ tests/
uv run mypy src/
```

## Docker Deployment

See [quickstart.md](specs/001-project-scaffolding/quickstart.md) for Docker and Intel NUC deployment instructions.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALPACA_PAPER_API_KEY` | Yes | - | Paper trading API key ID |
| `ALPACA_PAPER_SECRET_KEY` | Yes | - | Paper trading secret key |
| `ALPACA_LIVE_API_KEY` | No | - | Live trading API key ID |
| `ALPACA_LIVE_SECRET_KEY` | No | - | Live trading secret key |
| `TRADING_MODE` | No | `paper` | `paper` or `live` |
| `DB_PATH` | No | `data/finance_agent.db` | SQLite database path |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Architecture

The codebase follows a modular layered architecture:

- **data/** - Market data, filings, transcripts ingestion
- **research/** - LLM-powered analysis and signal generation
- **engine/** - Decision rules and trade proposal generation
- **execution/** - Broker API integration (Alpaca)
- **audit/** - Append-only event logging

See the [project constitution](.specify/memory/constitution.md) for guiding principles.
