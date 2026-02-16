# Quickstart: Research Data Ingestion & Analysis

**Feature Branch**: `002-research-ingestion`
**Date**: 2026-02-16

## Prerequisites

- Completed 001-project-scaffolding (`finance-agent health` passes)
- Alpaca paper trading configured (from scaffolding)
- **New**: Anthropic API key (for Claude analysis)
- **New**: Finnhub API key (for earnings transcripts — free tier)
- **New**: SEC EDGAR identity string (name + email, required by SEC)
- **Optional**: Stratechery Plus subscription (for Stratechery content)
- **Optional**: AssemblyAI API key (for podcast transcription)

## Setup

### 1. Install Updated Dependencies

```bash
uv sync
```

### 2. Configure New Environment Variables

Add to your `.env` file:

```bash
# Required for research
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxx
FINNHUB_API_KEY=xxxxxxxxxx
EDGAR_IDENTITY="Jason Belk jason@example.com"

# Optional sources
STRATECHERY_FEED_URL=https://stratechery.passport.online/feed/rss/YOUR_ID
ASSEMBLYAI_API_KEY=xxxxxxxxxx
RESEARCH_DATA_DIR=research_data/
```

### 3. Verify Health Check Still Passes

```bash
uv run finance-agent health
```

Should show all green plus new "Research Sources" section.

## Scenario 1: Build a Watchlist (US1 Foundation)

```bash
# Add companies to track
uv run finance-agent watchlist add NVDA
uv run finance-agent watchlist add AAPL
uv run finance-agent watchlist add MSFT

# Verify
uv run finance-agent watchlist list
```

Expected output:
```
Research Watchlist (3 companies):

  NVDA  NVIDIA Corporation        0 signals  (never)
  AAPL  Apple Inc                 0 signals  (never)
  MSFT  Microsoft Corporation     0 signals  (never)
```

## Scenario 2: First Research Run — SEC Filings (US1 MVP)

```bash
# Run research for SEC filings only
uv run finance-agent research --source sec
```

Expected behavior:
- Downloads recent 10-K, 10-Q, 8-K filings from SEC EDGAR
- Persists raw filings to `research_data/filings/{ticker}/`
- Analyzes each filing with Claude, producing structured signals
- Stores signals in SQLite database

Expected output:
```
Research Ingestion — 2026-02-16T10:30:00Z
Watchlist: 3 companies | Sources: sec

SEC Filings:
  NVDA: 3 filings ingested (1 10-K, 1 10-Q, 1 8-K), 12 signals generated
  AAPL: 2 filings ingested (1 10-K, 1 10-Q), 8 signals generated
  MSFT: 2 filings ingested (1 10-K, 1 10-Q), 9 signals generated

Summary:
  Documents: 7 new
  Signals: 29 new
  Errors: 0
  Duration: 8m 15s
```

## Scenario 3: View Research Signals (US1 + US5)

```bash
# View all signals for NVDA
uv run finance-agent signals NVDA

# Filter by type
uv run finance-agent signals NVDA --type guidance_change

# Filter by date range
uv run finance-agent signals NVDA --since 2025-10-01 --until 2025-12-31

# View unified profile
uv run finance-agent profile NVDA
```

## Scenario 4: Earnings Transcripts (US1 Extension)

```bash
# Run with transcripts source
uv run finance-agent research --source transcripts

# Or run all enabled sources
uv run finance-agent research
```

Requires `FINNHUB_API_KEY` in `.env`. System fetches available transcripts for each watchlist company, downloads them, and produces signals with speaker attribution and session type (management discussion vs Q&A).

## Scenario 5: Acquired Podcast Analysis (US2)

```bash
# Run Acquired source
uv run finance-agent research --source acquired
```

First run: Downloads Kaggle dataset for historical episodes, fetches RSS feed for recent episodes. Classifies episodes by type (deep-dive vs interview). Analyzes with Claude to produce investment signals linked to companies.

Subsequent runs: Only processes new episodes since last run.

## Scenario 6: Stratechery Analysis (US3)

```bash
# Run Stratechery source (requires STRATECHERY_FEED_URL)
uv run finance-agent research --source stratechery
```

Fetches articles/updates from authenticated RSS feed. Classifies content type. Maps insights to watchlist companies.

## Scenario 7: Investor Tracking (US4)

```bash
# Add investors to track
uv run finance-agent investors add "Berkshire Hathaway" 0001067983
uv run finance-agent investors add "ARK Investment Management" 0001803994

# Run 13F analysis
uv run finance-agent research --source investors
```

## Scenario 8: Check Pipeline Status

```bash
uv run finance-agent research status
```

Shows last run, document counts, per-source status, and any failed documents.

## Scenario 9: Scheduled Runs on NUC

Add to crontab on the Intel NUC:

```bash
# Run research daily at 6 AM Pacific
0 6 * * * cd /path/to/finance-agent && uv run finance-agent research >> /var/log/finance-agent-research.log 2>&1
```

Or via Docker Compose:

```bash
docker compose exec app finance-agent research
```

## Testing

```bash
# Unit tests (no API keys needed — mocked)
uv run pytest tests/unit/

# Integration tests (requires API keys in .env)
uv run pytest tests/integration/

# Full quality check
make check
```

## Common Issues

### "EDGAR_IDENTITY not set"
SEC requires identifying automated clients. Set `EDGAR_IDENTITY="Your Name your@email.com"` in `.env`.

### "Finnhub API returned 403"
Free tier may restrict transcript access. Check Finnhub dashboard for plan limits. Consider upgrading to $50/mo fundamental-1 plan.

### "Stratechery feed returned empty"
Verify your Stratechery Plus subscription is active and the RSS URL is correct. Check for Cloudflare bot detection — the system sets a browser User-Agent header to avoid this.

### "LLM analysis timeout"
Large 10-K filings may take 60+ seconds to analyze. The system will retry once. If persistent, check your Anthropic API key has sufficient credits.
