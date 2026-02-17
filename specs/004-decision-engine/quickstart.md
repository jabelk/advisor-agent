# Quickstart: Decision Engine

**Feature**: 004-decision-engine

## Prerequisites

1. Features 001-003 complete (project scaffolding, research ingestion, market data)
2. Alpaca paper trading API keys configured in `.env`
3. At least one company in the watchlist with research signals and market data

## Setup

```bash
# Ensure dependencies are installed
uv sync

# Verify prerequisites
uv run finance-agent health
# Expected: Config OK, Database OK (schema version 4), Broker API OK, Market Data API OK

# Ensure you have data to work with
uv run finance-agent watchlist list
# Should show at least one company

uv run finance-agent market status
# Should show bars fetched for watchlist companies
```

## Scenario 1: Generate and Review Proposals (Happy Path)

```bash
# Step 1: Generate proposals for all watchlist companies
uv run finance-agent engine generate
# Expected: Proposals generated with confidence scores, risk checks, and cited sources
# Each proposal shows: ticker, direction, quantity, limit price, confidence, sources, risk results

# Step 2: Review pending proposals
uv run finance-agent engine review
# Expected: Interactive prompt showing each proposal with full details
# Approve or reject each proposal

# Step 3: View proposal history
uv run finance-agent engine history
# Expected: Table of all proposals with status
```

## Scenario 2: Generate for Specific Ticker

```bash
uv run finance-agent engine generate --ticker NVDA
# Expected: Proposal generated for NVDA only (if sufficient data exists)
# Skips other watchlist companies
```

## Scenario 3: Kill Switch

```bash
# Activate kill switch
uv run finance-agent engine killswitch on
# Expected: "KILL SWITCH ACTIVATED" confirmation

# Try to generate — should be blocked
uv run finance-agent engine generate
# Expected: "KILL SWITCH ACTIVE" error, no proposals generated

# Try to approve — should be blocked
uv run finance-agent engine review
# Expected: Can view proposals but cannot approve

# Deactivate kill switch
uv run finance-agent engine killswitch off
# Expected: "KILL SWITCH DEACTIVATED" confirmation, normal operation resumes
```

## Scenario 4: Risk Controls

```bash
# View current risk settings
uv run finance-agent engine risk
# Expected: All risk limits with current values and today's usage

# Update a risk setting
uv run finance-agent engine risk set max_position_pct 0.08
# Expected: Setting updated from 0.10 to 0.08, logged

# Generate with tighter limits
uv run finance-agent engine generate
# Expected: Position sizes respect new 8% limit
```

## Scenario 5: Engine Status

```bash
uv run finance-agent engine status
# Expected: Kill switch state, account info, trade count, daily P&L, pending proposals, risk settings
```

## Scenario 6: Dry Run (No Side Effects)

```bash
uv run finance-agent engine generate --dry-run
# Expected: Shows what proposals would be generated without saving to database
# Useful for testing scoring logic without creating proposals
```

## Scenario 7: Insufficient Data

```bash
# Add a new company with no research or market data
uv run finance-agent watchlist add ZZZZ

uv run finance-agent engine generate --ticker ZZZZ
# Expected: Skipped — insufficient data (no research signals / no market data)
```

## Scenario 8: No LLM Key (Base Score Only)

```bash
# Unset Anthropic key temporarily
ANTHROPIC_API_KEY= uv run finance-agent engine generate
# Expected: Proposals generated using base score only
# Output includes: "Note: ANTHROPIC_API_KEY not set. Using base score only."
# LLM adjustment shows 0.0 for all proposals
```

## Expected Database State After Scenarios

After running scenarios 1-4:
- `trade_proposal` table has proposals with various statuses
- `proposal_source` table has citations linking proposals to signals/indicators
- `risk_check_result` table has pass/fail results for each risk rule per proposal
- `engine_state` table has kill_switch and risk_settings rows
- `audit_log` table has entries for all proposal lifecycle events

## Validation Commands

```bash
# Unit tests (no API keys needed)
uv run pytest tests/unit/test_engine.py -v

# Integration tests (requires paper trading API keys in .env)
uv run pytest tests/integration/test_engine.py -v

# All tests with coverage
uv run pytest --cov=finance_agent

# Lint check
uv run ruff check src/finance_agent/engine/ tests/unit/test_engine.py tests/integration/test_engine.py
```
