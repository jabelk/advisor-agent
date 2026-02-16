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
Database: OK (finance_agent.db, schema version 2)
Broker API: OK (account ACTIVE, buying power: $X,XXX.XX)
```

## Research Pipeline

The research layer ingests data from multiple sources, analyzes documents with Claude, and produces structured research signals.

```bash
# Add companies to your watchlist
uv run finance-agent watchlist add NVDA
uv run finance-agent watchlist add AAPL

# Add notable investors to track
uv run finance-agent investors add "Berkshire Hathaway" 0001067983

# Run research ingestion and analysis
uv run finance-agent research run

# Run for a specific ticker or source
uv run finance-agent research run --ticker NVDA --source sec

# Query research signals
uv run finance-agent signals NVDA --type sentiment
uv run finance-agent signals NVDA --source sec_filing --since 2025-01-01

# View company research profile
uv run finance-agent profile NVDA
```

### Data Sources

| Source | API Key Required | What it ingests |
|--------|-----------------|-----------------|
| SEC EDGAR | `EDGAR_IDENTITY` | 10-K, 10-Q, 8-K filings |
| EarningsCall.biz | `EARNINGSCALL_API_KEY` | Earnings call transcripts with speaker attribution |
| Finnhub | `FINNHUB_API_KEY` | Analyst ratings, earnings history, insider activity, news |
| Acquired Podcast | None (RSS) | Episode metadata and notes |
| Stratechery | `STRATECHERY_FEED_URL` | Analysis articles and daily updates |
| 13F Holdings | `EDGAR_IDENTITY` | Institutional investor filings |

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
| `RESEARCH_DATA_DIR` | No | `research_data` | Research artifact storage path |
| `ANTHROPIC_API_KEY` | No | - | Claude API key for LLM analysis |
| `EDGAR_IDENTITY` | No | - | SEC EDGAR identity (`Name email@example.com`) |
| `FINNHUB_API_KEY` | No | - | Finnhub API key for market signals (free tier) |
| `EARNINGSCALL_API_KEY` | No | - | EarningsCall.biz API key for transcripts |
| `STRATECHERY_FEED_URL` | No | - | Stratechery premium RSS feed URL |
| `ASSEMBLYAI_API_KEY` | No | - | AssemblyAI key for podcast transcription |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Architecture

The codebase follows a modular layered architecture:

- **data/** - Market data, filings, transcripts ingestion
- **research/** - LLM-powered analysis and signal generation
- **engine/** - Decision rules and trade proposal generation
- **execution/** - Broker API integration (Alpaca)
- **audit/** - Append-only event logging

See the [project constitution](.specify/memory/constitution.md) for guiding principles.
