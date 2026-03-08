# Implementation Plan: Covered Call Income Strategy

**Branch**: `012-covered-call-strategy` | **Date**: 2026-03-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-covered-call-strategy/spec.md`

## Summary

Extend Pattern Lab to support covered call income strategies — a two-leg position (long stock + short call) that generates monthly premium income. This requires a new option pricing module for premium estimation in backtests, modifications to the backtest engine for sell-side options and assignment logic, and updates to the paper trading executor to submit multi-leg orders via Alpaca's options API.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: alpaca-py 0.43.2 (options trading via PositionIntent.SELL_TO_OPEN, OptionLegRequest, OptionHistoricalDataClient), anthropic (Claude API for pattern parsing), pydantic 2.0+ (structured models)
**Storage**: SQLite (WAL mode) — extends existing Pattern Lab tables, adds covered_call_cycle table
**Testing**: pytest
**Target Platform**: macOS / Linux CLI
**Project Type**: Single project (extends existing src/finance_agent/patterns/ module)
**Performance Goals**: Backtest 2 years of monthly cycles in under 60 seconds; premium estimation within 5% of Black-Scholes for ATM options
**Constraints**: No historical option chain data available — must estimate premiums from historical stock volatility
**Scale/Scope**: Single user (Jordan), 1-10 active covered call patterns

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Client Data Isolation | PASS | Personal investing only (Track 1). No client data involved. |
| II. Research-Driven | PASS | Backtest validates strategy before paper trading. Premium estimation uses historical price data. |
| III. Advisor Productivity | PASS | Plain text description → structured covered call rules. Reduces friction for testing income strategies. |
| IV. Safety First | PASS | Paper trading only. Kill switch and risk limits checked on every trade. Options paper-traded extensively before live consideration. |
| V. Security by Design | PASS | No new secrets. Uses existing Alpaca paper trading credentials from .env. |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/012-covered-call-strategy/
├── plan.md              # This file
├── research.md          # Phase 0: premium estimation, Alpaca options API
├── data-model.md        # Phase 1: CoveredCallCycle, PremiumEstimate entities
├── quickstart.md        # Phase 1: developer reference
├── contracts/
│   └── cli.md           # CLI extensions for covered calls
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/finance_agent/patterns/
├── __init__.py
├── models.py              # + CoveredCallCycle, PremiumEstimate models
├── option_pricing.py      # NEW: Black-Scholes estimation, historical vol
├── parser.py              # + covered call recognition, naked call warning
├── backtest.py            # + covered call cycle simulation, assignment logic
├── executor.py            # + multi-leg MLEG orders, sell-to-open, roll detection
├── market_data.py         # unchanged
└── storage.py             # + covered_call_cycle CRUD

migrations/
└── 008_covered_call.sql   # covered_call_cycle table
```

**Structure Decision**: Extends existing `src/finance_agent/patterns/` module. One new file (`option_pricing.py`) for premium estimation math. All other changes are additions to existing files. No new top-level modules needed.
