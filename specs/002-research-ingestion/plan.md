# Implementation Plan: Research Data Ingestion & Analysis

**Branch**: `002-research-ingestion` | **Date**: 2026-02-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-research-ingestion/spec.md`

## Summary

Build the research data ingestion and LLM analysis layer: ingest SEC filings (10-K, 10-Q, 8-K) via edgartools, earnings call transcripts via Finnhub, Acquired podcast transcripts, Stratechery articles via authenticated RSS, and 13F institutional holdings. Analyze all documents with Claude (Anthropic SDK) using section-specific prompts and structured Pydantic output to produce research signals with fact-vs-inference classification. Store signals in SQLite, raw documents on filesystem. Expose via CLI commands: `watchlist`, `investors`, `research`, `signals`, `profile`.

## Technical Context

**Language/Version**: Python 3.12+ (existing project)
**Primary Dependencies**: edgartools>=5.16, finnhub-python>=2.4, anthropic>=0.45, feedparser>=6.0, beautifulsoup4>=4.12, pydantic>=2.0 (new); alpaca-py, httpx (existing)
**Storage**: SQLite (extends existing DB with 5 new tables) + filesystem for raw documents (`research_data/`)
**Testing**: pytest (existing), with mocked API clients for unit tests, real API integration tests
**Target Platform**: Intel NUC (Ubuntu 24.04), Docker deployment, macOS for development
**Project Type**: Single project (extends existing `src/finance_agent/` package)
**Performance Goals**: 20-company watchlist incremental ingestion in <30 minutes
**Constraints**: SEC EDGAR rate limit 10 req/s (edgartools handles at 9 req/s), Finnhub 60 calls/min free tier, Anthropic token costs ~$40-80/year
**Scale/Scope**: 10-20 companies, ~150 documents/quarter, ~500 signals/quarter

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Safety First | PASS | Research layer produces signals only — no trade execution. Signals feed into decision engine (future feature). |
| II. Research-Driven Decisions | PASS (core) | Raw documents persisted locally before analysis (NFR-002). Fact-vs-inference classification on every signal (FR-016). Source references on all signals (NFR-003). |
| III. Modular Architecture | PASS | Each data source is a pluggable ingestion module with consistent interface. Source failure doesn't block other sources (FR-015). |
| IV. Audit Everything | PASS | All ingestion and analysis activity logged to audit trail (FR-014). Source document references preserved. |
| V. Security by Design | PASS | API keys in env vars only. Stratechery RSS URL treated as secret. No keys in code or logs. EDGAR_IDENTITY is non-secret (required by SEC). |

**Post-design re-check**: PASS — no violations introduced during design phase.

## Project Structure

### Documentation (this feature)

```text
specs/002-research-ingestion/
├── plan.md              # This file
├── research.md          # Phase 0 output — technology decisions
├── data-model.md        # Phase 1 output — entities and relationships
├── quickstart.md        # Phase 1 output — integration scenarios
├── contracts/
│   └── cli.md           # Phase 1 output — CLI command contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/finance_agent/
├── __init__.py                    # (existing) version
├── cli.py                         # (extend) add watchlist, investors, research, signals, profile subcommands
├── config.py                      # (extend) add new env vars (ANTHROPIC_API_KEY, FINNHUB_API_KEY, etc.)
├── db.py                          # (existing) get_connection, run_migrations
├── audit/
│   ├── __init__.py                # (existing)
│   └── logger.py                  # (existing) AuditLogger
├── data/
│   ├── __init__.py                # (existing stub)
│   ├── sources/
│   │   ├── __init__.py            # Source base class / interface
│   │   ├── sec_edgar.py           # SEC filing ingestion via edgartools
│   │   ├── finnhub.py             # Earnings transcript ingestion via finnhub-python
│   │   ├── acquired.py            # Acquired podcast RSS + transcript ingestion
│   │   ├── stratechery.py         # Stratechery RSS feed ingestion
│   │   └── investor_13f.py        # 13F institutional holdings via edgartools
│   ├── models.py                  # Pydantic models: SourceDocument, ResearchSignal, DocumentAnalysis
│   └── storage.py                 # Filesystem storage manager (persist/retrieve documents)
├── research/
│   ├── __init__.py                # (existing stub)
│   ├── analyzer.py                # LLM analysis orchestrator (map-reduce for large docs)
│   ├── pipeline.py                # Research pipeline orchestrator + ingestion run tracking
│   ├── prompts.py                 # Section-specific analysis prompts
│   └── signals.py                 # Signal storage and query (SQLite CRUD)
├── engine/
│   └── __init__.py                # (existing stub, untouched)
└── execution/
    └── __init__.py                # (existing stub, untouched)

migrations/
├── 001_init.sql                   # (existing) audit_log table
└── 002_research.sql               # NEW: company, source_document, research_signal, notable_investor, ingestion_run tables

research_data/                     # NEW: filesystem storage for raw documents (gitignored)
├── filings/{ticker}/{type}/
├── transcripts/{ticker}/
├── podcasts/acquired/
└── articles/stratechery/

tests/
├── unit/
│   ├── test_config.py             # (existing, extend)
│   ├── test_db.py                 # (existing, extend)
│   ├── test_audit.py              # (existing)
│   ├── test_watchlist.py          # NEW: watchlist CRUD operations
│   ├── test_sources.py            # NEW: each source module (mocked API calls)
│   ├── test_analyzer.py           # NEW: LLM analysis (mocked Anthropic client)
│   ├── test_signals.py            # NEW: signal storage and query
│   └── test_models.py             # NEW: Pydantic model validation
└── integration/
    ├── test_health.py             # (existing)
    ├── test_sec_edgar.py          # NEW: real EDGAR API calls
    ├── test_finnhub.py            # NEW: real Finnhub API calls
    └── test_research_pipeline.py  # NEW: end-to-end research run
```

**Structure Decision**: Extends the existing `src/finance_agent/` package established in 001-project-scaffolding. New modules go in `data/sources/` (one per ingestion source), `research/` (analysis and signal storage), and a new migration for the research schema. This follows the modular architecture from the constitution — each source is independently swappable.
