# Implementation Plan: Decision Engine

**Branch**: `004-decision-engine` | **Date**: 2026-02-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-decision-engine/spec.md`

## Summary

Build the decision engine layer that combines research signals (feature 002) and market data (feature 003) to generate trade proposals with risk controls. Uses a hybrid confidence scoring system (deterministic base score + bounded LLM adjustment), enforces configurable risk limits per the constitution, and provides a CLI workflow for proposal generation, review, and approval. All proposals cite their data sources and all risk evaluations are audit-logged.

## Technical Context

**Language/Version**: Python 3.12+ (existing project)
**Primary Dependencies**: alpaca-py (existing, TradingClient for account/positions), anthropic (existing, for LLM confidence adjustment), pydantic (existing, for structured models)
**Storage**: SQLite (extends existing DB with 4 new tables via migration 004)
**Testing**: pytest with mocked Alpaca client and mocked Anthropic client for unit tests; live Alpaca API for integration tests
**Target Platform**: Intel NUC (home server), CLI interface
**Project Type**: Single Python package (extends existing `src/finance_agent/`)
**Performance Goals**: Proposal generation for full watchlist in under 30 seconds
**Constraints**: Alpaca free-tier rate limits (handled by existing rate limiter), Anthropic API costs (1 LLM call per watchlist company per generation run)
**Scale/Scope**: Single user, ~5-10 watchlist companies, ~20 trades/day max

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Implementation |
|-----------|--------|----------------|
| I. Safety First | ✓ PASS | Kill switch (FR-008), position size limits (FR-004), daily loss limit (FR-005), trade count limit (FR-006), concentration limits (FR-007), limit orders only (FR-012) |
| II. Research-Driven | ✓ PASS | Every proposal cites data sources (FR-002), minimum signal requirements, fact/inference distinction in scoring |
| III. Modular Architecture | ✓ PASS | Engine is a separate `engine/` module, communicates with research/market layers via DB queries, no direct coupling |
| IV. Audit Everything | ✓ PASS | Risk check results logged (FR-011), operator decisions logged (FR-010), kill switch toggles logged, all in append-only audit |
| V. Security by Design | ✓ PASS | No new secrets introduced, uses existing Alpaca/Anthropic keys from config, no keys in logs |

**Post-design re-check**: All principles satisfied. The hybrid scoring approach adds an LLM call but with bounded adjustment (+/-0.15), maintaining research-driven primacy. Kill switch halts all proposal generation and approval immediately.

## Project Structure

### Documentation (this feature)

```text
specs/004-decision-engine/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research decisions
├── data-model.md        # 4 new tables, state transitions
├── quickstart.md        # Validation scenarios
├── contracts/
│   └── cli.md           # CLI command contracts
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/finance_agent/engine/
├── __init__.py          # Module docstring
├── scoring.py           # Hybrid confidence scoring (base + LLM adjustment)
├── risk.py              # Risk control checks and settings management
├── proposals.py         # Proposal generation, lifecycle management, queries
├── account.py           # Alpaca TradingClient wrapper for account/positions/orders
└── state.py             # Kill switch and engine_state persistence

migrations/
└── 004_decision_engine.sql  # 4 new tables

tests/unit/
└── test_engine.py       # Unit tests with mocked clients

tests/integration/
└── test_engine.py       # Integration tests with live Alpaca API
```

**Structure Decision**: Extends the existing `src/finance_agent/engine/` placeholder directory (currently just `__init__.py`). Follows the same pattern as `market/` (feature 003) with separate files per concern. The `account.py` wrapper isolates Alpaca TradingClient usage, making the rest of the engine testable with mocks.

## Key Design Decisions

1. **Scoring pipeline**: signal_score (0.50) + indicator_score (0.30) + momentum_score (0.20) = base_score. LLM adds +/-0.15 → final_score. All on -1.0 to +1.0 scale.

2. **Position sizing**: `abs(final_score) * max_position_pct * equity`. A score of 0.45 (minimum) → 4.5% of portfolio. Score of 1.0 → 10% (constitutional max). Rounded down to whole shares.

3. **Limit price**: ATR-14 based offset, scaled inversely with confidence (0.3x-0.7x ATR). Floor 0.1%, cap 2.0%.

4. **Kill switch**: Stored in `engine_state` table as JSON. Checked at the start of `generate` and `review approve`. Persists across restarts.

5. **Proposal expiration**: Checked lazily at query time. Proposals with `expires_at < now` are marked expired on read. No background job needed.

6. **LLM graceful degradation**: If `ANTHROPIC_API_KEY` is not set, skip LLM adjustment and use base score only. Log a note.

7. **Account data**: TradingClient wraps all Alpaca account API calls (get_account, get_all_positions, get_orders, get_portfolio_history). Creates client once per generation run, reuses for all risk checks.

## Complexity Tracking

No constitution violations to justify. All components are straightforward:
- 5 source files in engine/ (scoring, risk, proposals, account, state)
- 4 SQLite tables (simple schema, no complex joins)
- 7 CLI subcommands under `engine` group
- No new external dependencies
