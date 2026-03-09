# Implementation Plan: Live Pattern Alerts & Paper Trade Execution

**Branch**: `017-live-pattern-alerts` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-live-pattern-alerts/spec.md`

## Summary

Add a pattern scanner that evaluates all `paper_trading` patterns against recent market data, generates persistent alerts when trigger conditions are met, and optionally auto-executes paper trades. The scanner reuses existing trigger detection logic from the backtest engine and existing paper trade submission from the executor. Alerts are stored in a new `pattern_alert` table and exposed via CLI commands and an MCP tool.

## Technical Context

**Language/Version**: Python 3.12+ with type hints
**Primary Dependencies**: alpaca-py 0.43+ (StockHistoricalDataClient for market data), pydantic (models), fastmcp (MCP tool exposure)
**Storage**: SQLite (WAL mode) — new `pattern_alert` table via migration 010, add `auto_execute` column to `trading_pattern`
**Testing**: pytest
**Target Platform**: macOS/Linux, CLI + Claude Desktop via MCP
**Project Type**: Single project (existing codebase extension)
**Performance Goals**: Scanner completes evaluation of 20 patterns x 10 tickers within 60 seconds (most time is network I/O for bar fetching, mitigated by existing cache)
**Constraints**: Alpaca API rate limits; scanner must not interfere with existing paper-trade monitoring
**Scale/Scope**: ~5-20 active patterns, ~5-50 tickers per scan; 1 new module, 1 migration, modifications to 3 existing files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| I. Client Data Isolation | PASS | Uses only public market data (stock prices, volumes). No client PII involved. |
| II. Research-Driven | PASS | Alerts are based on quantitative trigger rules evaluated against real market data, not LLM intuition. |
| III. Advisor Productivity | PASS | Automates pattern monitoring so Jordan doesn't need to manually check charts or run backtests to spot opportunities. |
| IV. Safety First | PASS | Auto-execution is opt-in per pattern, defaults to off. Kill switch and daily trade limits checked before every auto-execution. Paper trading only. |
| V. Security by Design | PASS | Alpaca keys read from environment, not exposed. Alert data stored locally. |

All 5 gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/017-live-pattern-alerts/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── scanner-alerts.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/finance_agent/
├── patterns/
│   ├── scanner.py            # NEW: Pattern scanner — evaluates triggers, generates alerts
│   ├── alert_storage.py      # NEW: Alert CRUD — create, list, filter, acknowledge, dismiss
│   ├── executor.py           # EXISTING: Reuse _evaluate_trigger logic; add auto-execute support
│   ├── backtest.py           # EXISTING: Reuse _check_trigger for bar-based evaluation
│   └── storage.py            # EXISTING: Add auto_execute flag to pattern queries
├── mcp/
│   └── research_server.py    # MODIFY: Add get_pattern_alerts MCP tool
├── cli.py                    # MODIFY: Add scan, alerts subcommands

migrations/
└── 010_pattern_alerts.sql    # NEW: pattern_alert table + auto_execute column

tests/
├── unit/
│   ├── test_scanner.py       # NEW: Scanner logic tests
│   └── test_alert_storage.py # NEW: Alert CRUD tests
```

**Structure Decision**: Follows existing single-project pattern. New `scanner.py` handles scan orchestration (which patterns, which tickers, trigger evaluation, alert generation). New `alert_storage.py` handles alert persistence. The scanner imports trigger evaluation from existing modules rather than duplicating logic.
