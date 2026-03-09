# Implementation Plan: Track 1 Completion — Dashboard, Performance & Scheduled Scanning

**Branch**: `018-track1-dashboard-perf` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/018-track1-dashboard-perf/spec.md`

## Summary

Add a portfolio dashboard command that aggregates pattern status, paper trade P&L, and alert counts into a single view. Add performance tracking that compares backtest predictions against paper trade actuals with divergence warnings. Add scheduled scanning via OS-native task schedulers (launchd on macOS) so the pattern scanner runs automatically during market hours. All three capabilities are exposed via CLI and MCP tools.

## Technical Context

**Language/Version**: Python 3.12+ with type hints
**Primary Dependencies**: alpaca-py 0.43+ (market data), pydantic (models), fastmcp (MCP tools)
**Storage**: SQLite (WAL mode) — no new tables; all dashboard/performance data is derived from existing tables. Schedule config stored as a launchd plist file.
**Testing**: pytest
**Target Platform**: macOS (primary — launchd), Linux (cron fallback)
**Project Type**: Single project (existing codebase extension)
**Performance Goals**: Dashboard renders in <1 second from local SQLite queries (no network I/O)
**Constraints**: Scheduled scanning must work without a running terminal; market hours detection uses US Eastern Time
**Scale/Scope**: ~5-20 patterns, ~50-500 paper trades, ~100-1000 alerts; 2 new modules, modifications to 2 existing files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| I. Client Data Isolation | PASS | Uses only pattern/backtest/paper-trade data — all personal investing, no client PII. |
| II. Research-Driven | PASS | Dashboard displays data-backed metrics (win rates, P&L from actual trades). Performance tracking grounds strategy decisions in empirical results. |
| III. Advisor Productivity | PASS | Single dashboard replaces 3+ separate commands. Scheduled scanning removes manual polling. |
| IV. Safety First | PASS | No new trading functionality. Scheduled scanner uses existing safety controls (kill switch, daily limits). |
| V. Security by Design | PASS | Alpaca keys passed via environment variables in launchd plist (not stored in code). |

All 5 gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/018-track1-dashboard-perf/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── dashboard-perf-schedule.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/finance_agent/
├── patterns/
│   └── dashboard.py         # NEW: Dashboard aggregation + performance comparison queries
├── scheduling/
│   └── scan_schedule.py     # NEW: launchd/cron schedule management (install, list, pause, remove)
├── mcp/
│   └── research_server.py   # MODIFY: Add get_dashboard_summary, get_performance_comparison MCP tools
├── cli.py                   # MODIFY: Add dashboard, perf, schedule subcommands

tests/
├── unit/
│   ├── test_dashboard.py    # NEW: Dashboard aggregation + performance comparison tests
│   └── test_scan_schedule.py # NEW: Schedule management tests
```

**Structure Decision**: Follows existing single-project pattern. New `dashboard.py` handles all read-only aggregation queries. New `scheduling/scan_schedule.py` handles OS-level schedule management (launchd plist generation, install/remove). CLI and MCP modifications follow established patterns.
