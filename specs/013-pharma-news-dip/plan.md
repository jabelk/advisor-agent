# Implementation Plan: Pharma News Dip Pattern

**Branch**: `013-pharma-news-dip` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-pharma-news-dip/spec.md`

## Summary

Extend Pattern Lab to support news-driven qualitative patterns: detect "significant pharma news" events via price-action proxy (5%+ single-day spike on 1.5x average volume), simulate buying calls on the subsequent dip, and analyze performance regimes to show when/why the pattern works and breaks down. Builds entirely on existing Pattern Lab infrastructure (011) and options pricing (012) — no new external services.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: alpaca-py (market data), anthropic (pattern parsing), pydantic (models)
**Storage**: SQLite (WAL mode) — no new tables needed, extends existing backtest/trade models
**Testing**: pytest (unit + integration)
**Target Platform**: macOS/Linux CLI
**Project Type**: Single project (CLI tool)
**Performance Goals**: 2-year backtest in <60s, paper trade spike detection within 5min poll cycle
**Constraints**: No new external services; uses existing Alpaca market data for price/volume
**Scale/Scope**: Single user (Jordan), single stock per backtest run

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Client Data Isolation | PASS | Personal investing only — no client data involved |
| II. Research-Driven | PASS | Uses historical price data; backtesting validates before trading |
| III. Advisor Productivity | PASS | Plain language description → structured pattern → backtest results |
| IV. Safety First | PASS | Paper trading default; qualitative triggers require human confirmation (FR-008) |
| V. Security by Design | PASS | No new secrets; uses existing Alpaca API keys |

All gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/013-pharma-news-dip/
├── plan.md              # This file
├── research.md          # Phase 0: technical research decisions
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: test scenarios
├── contracts/
│   └── cli.md           # Phase 1: CLI command contracts
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/finance_agent/
├── patterns/
│   ├── models.py            # Extend: no changes needed (BacktestTrade, RegimePeriod already exist)
│   ├── parser.py            # Extend: add _apply_news_dip_defaults() post-processor
│   ├── backtest.py          # Extend: add run_news_dip_backtest() with event detection
│   ├── executor.py          # Extend: add NewsPatternMonitor with human confirmation
│   ├── event_detection.py   # NEW: spike detection, cooldown, manual event parsing
│   ├── regime.py            # NEW: regime analysis with 60/40 thresholds
│   ├── storage.py           # Extend: save/load detected events metadata
│   ├── market_data.py       # No changes — existing fetch_and_cache_bars() sufficient
│   └── option_pricing.py    # No changes — existing estimate_call_premium() sufficient
├── cli.py                   # Extend: --events/--events-file flags, news dip backtest routing
└── mcp/
    └── research_server.py   # No changes — existing tools sufficient

tests/
├── unit/
│   ├── test_event_detection.py   # NEW: spike detection, cooldown, event parsing
│   ├── test_regime.py            # NEW: regime labeling with 60/40 thresholds
│   └── test_backtest.py          # Extend: news dip backtest tests
└── integration/
    └── test_news_dip_cli.py      # NEW: end-to-end CLI tests
```

**Structure Decision**: Extends existing single-project structure. Two new modules (`event_detection.py`, `regime.py`) extract focused logic from what would otherwise bloat `backtest.py`. All other changes are extensions to existing files.

## Complexity Tracking

No violations — no tracking needed.
