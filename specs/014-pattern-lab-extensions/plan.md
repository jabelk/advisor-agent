# Implementation Plan: Pattern Lab Extensions

**Branch**: `014-pattern-lab-extensions` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-pattern-lab-extensions/spec.md`

## Summary

Extend Pattern Lab with three capabilities: (1) multi-ticker aggregation to produce combined backtest reports across stock baskets, (2) A/B testing framework with statistical significance testing (Fisher's exact test for win rates, Welch's t-test for returns) to compare pattern variants, and (3) markdown export for persistent, shareable reports.

## Technical Context

**Language/Version**: Python 3.12+ with type hints
**Primary Dependencies**: alpaca-py (market data), pydantic (models), scipy (statistical tests — Fisher's exact, Welch's t-test)
**Storage**: SQLite (WAL mode) — extends existing backtest_result table, no new tables
**Testing**: pytest
**Target Platform**: macOS/Linux CLI tool
**Project Type**: Single project (existing Pattern Lab CLI)
**Performance Goals**: Multi-ticker aggregation within 2x single-ticker time
**Constraints**: All new entities in-memory (Pydantic models); results saved via existing `save_backtest_result()`
**Scale/Scope**: Typical basket of 4-8 tickers; A/B tests with 2-5 variants

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| I. Client Data Isolation | PASS | Feature uses only public market data (price bars). No client PII involved. |
| II. Research-Driven | PASS | Multi-ticker aggregation and A/B testing directly support data-driven pattern validation. Statistical significance testing prevents decisions based on noise. |
| III. Advisor Productivity | PASS | Combined reports reduce manual comparison work. Export creates persistent records. |
| IV. Safety First | PASS | No trading operations — backtest and analysis only. Paper trading unchanged. |
| V. Security by Design | PASS | No new secrets or credentials. Exports contain only backtest results. |

All 5 gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/014-pattern-lab-extensions/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── cli.md           # CLI contract extensions
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/finance_agent/
├── cli.py                           # MODIFY: add ab-test and export subcommands, update backtest display
├── patterns/
│   ├── backtest.py                  # MODIFY: update run_news_dip_backtest for multi-ticker aggregation
│   ├── stats.py                     # NEW: statistical significance tests (Fisher's exact, Welch's t-test)
│   ├── export.py                    # NEW: markdown report generation
│   └── models.py                    # MODIFY: add AggregatedBacktestReport, ABTestResult models

tests/
├── unit/
│   ├── test_stats.py                # NEW: statistical significance test coverage
│   └── test_export.py               # NEW: markdown export test coverage
└── integration/
    └── test_ab_test_cli.py          # NEW: end-to-end A/B test + export flow
```

**Structure Decision**: Follows existing single-project pattern. Two new modules (`stats.py`, `export.py`) keep responsibilities separated. Statistical logic is isolated in its own module for testability.
