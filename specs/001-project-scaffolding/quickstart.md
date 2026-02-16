# Quickstart: Finance Agent

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Astral package manager)
- An [Alpaca Markets](https://alpaca.markets/) account with paper trading API keys
- Docker (optional, for containerized deployment)

## Local Development Setup

### 1. Clone and install

```bash
git clone https://github.com/jabelk/finance-agent.git
cd finance-agent
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
chmod 600 .env
# Edit .env with your Alpaca paper trading API keys
```

### 3. Run health check

```bash
uv run finance-agent health
```

Expected output:
```
[PAPER MODE] Finance Agent v0.1.0
Configuration: OK (all required settings present)
Database: OK (finance_agent.db, schema version 1)
Broker API: OK (account ACTIVE, buying power: $X,XXX.XX)
```

### 4. Run tests

```bash
# Unit tests (no API keys needed)
uv run pytest tests/unit/

# Integration tests (requires paper trading API keys in .env)
uv run pytest tests/integration/

# All tests with coverage
uv run pytest --cov=finance_agent
```

### 5. Lint and type check

```bash
uv run ruff check src/
uv run mypy src/
```

## Docker Deployment (Intel NUC)

### Manual deployment

```bash
# On the NUC (ssh warp-nuc)
cd /path/to/finance-agent
mkdir -p secrets data

# Write secrets (one value per file, no trailing newline)
echo -n "PKXXXXXXXX" > secrets/alpaca_api_key.txt
echo -n "XXXXXXXX" > secrets/alpaca_secret_key.txt
chmod 600 secrets/*

# Build and start
docker compose up -d --build

# Check status
docker compose ps
docker compose logs --tail=20
```

### Automated deployment via GitHub Actions

Push to `main` branch triggers the self-hosted runner on the NUC:

```bash
git push origin main
# GitHub Actions runs on NUC: docker compose build && docker compose up -d
```

## Environment Variables

See `.env.example` for the full list with descriptions. Key variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALPACA_PAPER_API_KEY` | Yes | — | Paper trading API key ID |
| `ALPACA_PAPER_SECRET_KEY` | Yes | — | Paper trading secret key |
| `TRADING_MODE` | No | `paper` | `paper` or `live` |
| `DB_PATH` | No | `data/finance_agent.db` | SQLite database path |
| `LOG_LEVEL` | No | `INFO` | Logging level |
