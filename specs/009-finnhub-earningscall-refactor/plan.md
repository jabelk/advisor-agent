# Implementation Plan: Finnhub Free-Tier Refactor & EarningsCall Transcript Source

**Branch**: `009-finnhub-earningscall-refactor` | **Date**: 2026-02-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-finnhub-earningscall-refactor/spec.md`

## Summary

Refactor the Finnhub data source from a broken transcript fetcher ($3K/mo premium) to a market signals source using 5 free-tier endpoints (analyst ratings, earnings history, insider transactions, insider sentiment, company news). Add EarningsCall.biz as the dedicated transcript source with speaker attribution. Each new content type gets a tailored analysis prompt. All existing tests must pass, plus new tests for the refactored and new sources.

## Technical Context

**Language/Version**: Python 3.12+ (existing codebase)
**Primary Dependencies**: finnhub-python>=2.4 (existing), earningscall>=1.4 (new), anthropic (existing), pydantic (existing)
**Storage**: SQLite (existing tables — no schema changes) + filesystem for raw documents
**Testing**: pytest (unit + integration)
**Target Platform**: Intel NUC (Linux), development on macOS
**Project Type**: Single Python package (existing)
**Performance Goals**: 5 endpoints x N companies within Finnhub's 60 calls/min free-tier limit
**Constraints**: Finnhub free tier (60 calls/min); EarningsCall.biz demo mode (AAPL/MSFT only without paid key)
**Scale/Scope**: ~10-20 watchlist companies, 5 Finnhub endpoints + 1 transcript source

## Constitution Check

*GATE: All gates pass.*

| Gate | Status | Notes |
|------|--------|-------|
| Safety First | PASS | No trading functionality changed |
| Research-Driven | PASS | Adds 5 new data sources for richer research |
| Modular Architecture | PASS | Each source is an independent module; follows BaseSource pattern |
| Audit Everything | PASS | All ingested documents logged via existing pipeline |
| Security by Design | PASS | API keys in env vars, no secrets in code |
| Less Code More Context | PASS | Reuses existing BaseSource, storage, orchestrator patterns |

## Project Structure

### Documentation (this feature)

```text
specs/009-finnhub-earningscall-refactor/
├── plan.md              # This file
├── research.md          # Phase 0 research (earningscall lib + Finnhub endpoints)
├── data-model.md        # Content type mappings
├── quickstart.md        # Testing guide
├── contracts/
│   └── cli.md           # CLI source options
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (files modified/created)

```text
# Modified files
pyproject.toml                                    # Add earningscall>=1.4
src/finance_agent/config.py                       # Add earningscall_api_key + property
src/finance_agent/data/sources/finnhub.py         # Rewrite: FinnhubMarketSource (5 endpoints)
src/finance_agent/data/storage.py                 # Add finnhub_data subdir mapping
src/finance_agent/research/prompts.py             # Add 5 new content type prompts
src/finance_agent/research/orchestrator.py        # Update source registry
src/finance_agent/cli.py                          # Update --source help text + status
.env.example                                      # Add EARNINGSCALL_API_KEY
tests/unit/test_sources.py                        # Rewrite Finnhub tests, add EarningsCall tests
tests/integration/test_finnhub.py                 # Rewrite for free-tier endpoints

# New files
src/finance_agent/data/sources/earningscall_source.py  # EarningsCallSource class
tests/integration/test_earningscall.py                  # EarningsCall integration test
```

**Structure Decision**: Follows existing single-package layout. No new directories — sources go in `data/sources/`, tests in existing test directories.

## Finnhub Market Source Design (US1)

### Class: `FinnhubMarketSource(BaseSource)`

Replaces the old transcript-fetching Finnhub source with a market signals source.

**Endpoints ingested per company**:

| Endpoint | SDK Method | Content Type | Source ID Format |
|----------|-----------|--------------|------------------|
| Analyst Consensus | `recommendation_trends(symbol)` | `analyst_ratings` | `finnhub:{ticker}:recommendation_trends:{date}` |
| Earnings History | `company_earnings(symbol, limit=8)` | `earnings_history` | `finnhub:{ticker}:company_earnings:{date}` |
| Insider Transactions | `stock_insider_transactions(symbol)` | `insider_activity` | `finnhub:{ticker}:insider_transactions:{date}` |
| Insider Sentiment | `stock_insider_sentiment(symbol, _from, to)` | `insider_sentiment` | `finnhub:{ticker}:insider_sentiment:{date}` |
| Company News | `company_news(symbol, _from, to)` | `company_news` | `finnhub:{ticker}:company_news:{date}` |

**Error handling**: Each endpoint is fetched in a try/except. If one endpoint fails (rate limit, empty data, API error), the others continue. Errors are logged and included in `SourceResult.errors`.

**Dedup strategy**: `source_id` includes today's date for snapshot endpoints. `check_document_exists()` prevents re-ingestion on same day.

**Rate limiting**: Sequential calls. 5 endpoints x 10 companies = 50 calls, well within 60/min free tier.

## EarningsCall Source Design (US2)

### Class: `EarningsCallSource(BaseSource)`

**Name**: `"transcripts"` (reuses existing CLI source name — drop-in replacement for Finnhub transcripts).

**Ingestion flow**:
1. For each watchlist company, get the `Company` object via `get_company(ticker)`
2. Generate candidate `(year, quarter)` tuples via `_recent_quarters(now, MAX_QUARTERS)`
3. For each quarter, check dedup: `check_document_exists(conn, "earnings_transcript", source_id)`
4. Try `get_transcript(year, quarter, level=2)` for speaker attribution
5. On `InsufficientApiAccessError`, fall back to `get_transcript(year, quarter, level=1)`
6. Format as markdown (speaker sections for level=2, plain text for level=1)
7. Persist via storage manager, return `SourceDocumentMeta`

**Source ID format**: `"earningscall:{ticker}:{year}:Q{quarter}"`
**Content type**: `"earnings_call"` (reuses existing analysis prompt)

**Markdown format (level=2)**:
```markdown
# Earnings Call Transcript: AAPL Q3 2024

## Speakers
- Tim Cook (Chief Executive Officer)
- Luca Maestri (Chief Financial Officer)

## Transcript

### Tim Cook (Chief Executive Officer)
[spoken text...]

### Luca Maestri (Chief Financial Officer)
[spoken text...]
```

**Markdown format (level=1 fallback)**:
```markdown
# Earnings Call Transcript: AAPL Q3 2024

[full transcript text]
```

## Analysis Prompts Design (US3)

5 new prompts added to `CONTENT_TYPE_PROMPTS`:

| Content Type | Prompt Focus | Key Extractions |
|-------------|-------------|-----------------|
| `analyst_ratings` | Consensus direction and momentum | Rating distribution shifts, upgrade/downgrade trends, price target movement |
| `earnings_history` | Beat/miss patterns | Consecutive beats/misses, surprise magnitude trends, estimate accuracy |
| `insider_activity` | Trading signals | Net buying/selling by role, cluster activity, transaction codes (P/S vs M/A) |
| `insider_sentiment` | MSPR trends | Monthly sentiment direction, sustained buying/selling periods, reversal signals |
| `company_news` | Theme extraction | Key themes, sentiment, material events, catalysts |

All prompts require fact-vs-inference classification per constitution Principle II.

## Complexity Tracking

No constitution violations. All changes follow existing patterns (BaseSource, content types, prompts dict).
