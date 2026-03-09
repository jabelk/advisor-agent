# Implementation Plan: Real Options Chain Data

**Branch**: `016-real-options-data` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/016-real-options-data/spec.md`

## Summary

Replace the synthetic options pricing model (fixed leverage multipliers and simplified Black-Scholes) with real historical option prices from Alpaca. The system constructs OCC-format option symbols from pattern parameters, fetches historical bars via the broker's option data API, caches them locally, and uses actual premiums for backtest return calculations. Falls back to synthetic pricing when historical data is unavailable.

## Technical Context

**Language/Version**: Python 3.12+ with type hints
**Primary Dependencies**: alpaca-py 0.43+ (OptionHistoricalDataClient, OptionBarsRequest), pydantic (models)
**Storage**: SQLite (WAL mode) — new `option_price_cache` table via migration 009
**Testing**: pytest
**Target Platform**: macOS/Linux, CLI + Claude Desktop via MCP
**Project Type**: Single project (existing codebase extension)
**Performance Goals**: Option data fetching should not add more than 2x to backtest runtime (most time is network I/O, mitigated by caching)
**Constraints**: Alpaca API rate limits; option data availability limited to liquid contracts with trading activity
**Scale/Scope**: ~10-50 option contracts per backtest run; 1 new module, 1 migration, modifications to 3 existing files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| I. Client Data Isolation | PASS | Uses only public market data (option prices). No client PII involved. |
| II. Research-Driven | PASS | Replaces estimates with real data — directly improves research accuracy. |
| III. Advisor Productivity | PASS | More accurate backtest results help Jordan make better-informed decisions. |
| IV. Safety First | PASS | No trading operations — backtest analysis only. Existing safety controls unaffected. |
| V. Security by Design | PASS | Alpaca keys read from environment, not exposed. Option data cached locally. |

All 5 gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/016-real-options-data/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── option-data.md   # Internal function + MCP tool contracts
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/finance_agent/
├── patterns/
│   ├── option_data.py         # NEW: OCC symbols, contract selection, option bar fetching
│   ├── backtest.py            # MODIFY: inject real option pricing at trade execution
│   ├── market_data.py         # MODIFY: add option bar cache read/write helpers
│   └── option_pricing.py      # EXISTING: kept as fallback (synthetic Black-Scholes)
├── mcp/
│   └── research_server.py     # MODIFY: add get_option_chain_history MCP tool

migrations/
└── 009_option_cache.sql       # NEW: option_price_cache table

tests/
├── unit/
│   └── test_option_data.py    # NEW: unit tests for option data functions
```

**Structure Decision**: Follows existing single-project pattern. New `option_data.py` module handles all option-specific data logic (symbol construction, contract selection, bar fetching). The existing `option_pricing.py` (Black-Scholes) is preserved as the fallback when real data is unavailable.
