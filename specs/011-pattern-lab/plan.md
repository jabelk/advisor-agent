# Implementation Plan: Pattern Lab

**Branch**: `011-pattern-lab` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-pattern-lab/spec.md`

## Summary

Pattern Lab enables a financial advisor to describe trading patterns in plain English, have them parsed into structured rules via Claude, backtest them against historical market data, and run them forward as paper trades through Alpaca. The system emphasizes regime detection — understanding *when* patterns work and when they stop — and supports options-based strategies alongside equity trades. All trading defaults to paper mode with human approval.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: alpaca-py (broker + market data), anthropic (Claude for pattern parsing), pydantic (structured models), fastmcp (MCP tool exposure)
**Storage**: SQLite (WAL mode) — new migration 007 adds pattern tables alongside existing schema
**Testing**: pytest (unit + integration), Alpaca paper trading for integration tests
**Target Platform**: macOS/Linux CLI tool (single-user, local execution)
**Project Type**: Single project (extends existing `src/finance_agent/` package)
**Performance Goals**: Backtest 1 year of daily data in under 2 minutes; trigger detection within 5 minutes of market event
**Constraints**: Single user, local SQLite, Alpaca free-tier rate limits, no real money without explicit opt-in
**Scale/Scope**: Single advisor managing 5-20 concurrent patterns, backtesting against 1-5 years of data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Client Data Isolation | PASS | Pattern Lab uses only public market data and Jordan's personal pattern descriptions. No client PII involved. No connection to Schwab production systems. |
| II. Research-Driven | PASS | Backtesting is the core feature — every pattern must be validated against historical data before paper trading. Regime detection surfaces when/why patterns fail. Human makes final trade decision. |
| III. Advisor Productivity | PASS | Plain-text pattern description is the primary interface. Reduces friction from "I notice a pattern" to "let me test that" dramatically. |
| IV. Safety First | PASS | Paper trading by default. Kill switch integration. Position size and daily loss limits enforced. Human approval required for each trade by default. Options must be paper-traded. |
| V. Security by Design | PASS | Alpaca API keys from env vars (existing config.py). Anthropic key from env vars. No new secrets introduced. No secrets in pattern definitions or backtest results. |

**Post-design re-check**: All principles still satisfied. Pattern storage is local SQLite only. MCP exposure is read-only. No new external services beyond existing Alpaca + Anthropic integrations.

## Project Structure

### Documentation (this feature)

```text
specs/011-pattern-lab/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: technical decisions
├── data-model.md        # Phase 1: entity definitions
├── quickstart.md        # Phase 1: developer quick reference
├── contracts/
│   └── cli.md           # Phase 1: CLI command contracts
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
src/finance_agent/
├── patterns/                    # NEW: Pattern Lab module
│   ├── __init__.py
│   ├── models.py               # Pydantic: PatternDefinition, RuleSet, TriggerCondition, etc.
│   ├── parser.py               # Plain text → RuleSet via Claude structured output
│   ├── backtest.py             # Simulation engine: pattern rules × historical data → results
│   ├── market_data.py          # Fetch + cache historical bars from Alpaca
│   ├── executor.py             # Real-time trigger detection + paper trade proposal
│   └── storage.py              # Pattern/backtest/trade CRUD (SQLite)
├── cli.py                      # EXTEND: add `pattern` subcommand group
├── mcp/
│   └── research_server.py      # EXTEND: add pattern-related MCP tools
└── safety/
    └── guards.py               # EXISTING: kill switch + risk limits (consumed, not modified)

migrations/
└── 007_pattern_lab.sql          # NEW: pattern, backtest_result, backtest_trade, paper_trade, price_cache tables

tests/
├── unit/
│   ├── test_pattern_models.py   # Rule set validation, status transitions
│   ├── test_pattern_parser.py   # LLM parsing with mocked responses
│   ├── test_backtest.py         # Simulation logic with synthetic price data
│   └── test_pattern_storage.py  # CRUD operations
└── integration/
    ├── test_pattern_backtest.py  # End-to-end backtest with real Alpaca historical data
    └── test_pattern_paper.py    # Paper trade lifecycle with Alpaca sandbox
```

**Structure Decision**: Extends the existing single-project layout with a new `patterns/` subpackage under `src/finance_agent/`. This follows the same pattern as `research/`, `data/`, `safety/`, and `mcp/` — domain-specific modules with their own models, storage, and logic. No new top-level directories needed.

## Key Integration Points

1. **CLI** (`cli.py`): Add `pattern` command group with subcommands: describe, backtest, paper-trade, list, show, compare, retire. Follows existing subcommand pattern (watchlist, research, signals).

2. **Database** (`db.py`): Migration 007 adds 5 new tables. Uses existing `run_migrations()` and `get_connection()` — no changes to db.py itself.

3. **Safety** (`safety/guards.py`): Pattern executor checks `get_kill_switch()` before proposing trades and validates against `get_risk_settings()` for position sizing. Read-only integration — no modifications to safety module.

4. **LLM** (`research/analyzer.py`): Pattern parser reuses the Analyzer pattern — Claude API with Pydantic structured output. New prompts specific to pattern rule extraction.

5. **Alpaca** (`config.py`): Reuse existing `Settings.active_api_key` for paper/live mode selection. alpaca-py SDK for historical bars (backtest) and order submission (paper trade).

6. **MCP** (`mcp/research_server.py`): Add 4 new read-only tools: list_patterns, get_pattern_detail, get_backtest_results, get_paper_trade_summary.

7. **Audit** (`audit/logger.py`): All pattern creation, backtest runs, and trade executions logged via existing AuditLogger.

## Complexity Tracking

> No constitution violations. No complexity justifications needed.
