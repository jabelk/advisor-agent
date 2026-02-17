# Testing Guide: Finnhub Free-Tier Refactor & EarningsCall Transcript Source

**Feature**: 009-finnhub-earningscall-refactor | **Date**: 2026-02-17

---

## Prerequisites

```bash
# Install dependencies (includes earningscall>=1.4, finnhub-python>=2.4)
uv sync

# Copy .env.example and set keys
cp .env.example .env
# Edit .env: set FINNHUB_API_KEY and optionally EARNINGSCALL_API_KEY
```

---

## Unit Tests (no API keys needed)

```bash
# Run all unit tests
uv run pytest tests/unit/ -q

# Run only source-related tests
uv run pytest tests/unit/test_sources.py -v

# Run specific test classes
uv run pytest tests/unit/test_sources.py -k "TestFinnhubMarketSource" -v
uv run pytest tests/unit/test_sources.py -k "TestEarningsCallSource" -v
```

**What to verify**:
- `FinnhubMarketSource.name == "finnhub"`
- 5 endpoints produce 5 documents with correct content types
- Dedup: already-ingested documents are skipped
- Per-endpoint error isolation: one failure doesn't stop others
- `EarningsCallSource.name == "transcripts"`
- Level=2 → level=1 fallback on `InsufficientApiAccessError`
- Transcript formatting includes speaker names/titles (level=2) or plain text (level=1)
- Dedup: already-ingested transcripts are skipped

---

## Integration Tests (require API keys)

```bash
# Load environment variables
set -a && source .env && set +a

# Run all integration tests
uv run pytest tests/integration/ -v

# Run Finnhub integration (requires FINNHUB_API_KEY)
uv run pytest tests/integration/test_finnhub.py -v

# Run EarningsCall integration (works in demo mode without key)
uv run pytest tests/integration/test_earningscall.py -v
```

**What to verify**:
- Finnhub: `recommendation_trends("AAPL")` returns non-empty list
- Finnhub: All 5 endpoints return structured data (may be empty for some tickers)
- EarningsCall demo: `get_company("aapl")` returns a Company object
- EarningsCall demo: AAPL transcript is fetchable at level=1

---

## End-to-End Pipeline Test

```bash
# Add AAPL to watchlist (if not already)
set -a && source .env && set +a
uv run finance-agent watchlist add AAPL

# Run Finnhub market signals
uv run finance-agent research run --source finnhub --ticker AAPL

# Expected: 5 documents ingested (analyst_ratings, earnings_history,
# insider_activity, insider_sentiment, company_news)

# Run EarningsCall transcripts (demo mode)
uv run finance-agent research run --source transcripts --ticker AAPL

# Expected: 1+ transcript(s) ingested with content_type=earnings_call

# Verify combined
uv run finance-agent research run --source finnhub --source transcripts --ticker AAPL

# Check status
uv run finance-agent research status

# View signals
uv run finance-agent signals AAPL
```

---

## Verification Checklist

- [ ] `uv run ruff check src/ tests/` — no lint errors
- [ ] `uv run mypy src/finance_agent/` — no type errors
- [ ] `uv run pytest tests/unit/ -q` — all pass
- [ ] `uv run pytest tests/integration/ -v` — all pass (with .env loaded)
- [ ] `--source finnhub` ingests 5 document types per company
- [ ] `--source transcripts` ingests earnings call transcripts
- [ ] Re-running same source doesn't create duplicates
- [ ] `research status` shows both Finnhub Mkt and Transcripts sources
- [ ] Analysis produces signals for each new content type
