# Data Model: Architecture Pivot Cleanup

## Entities

### safety_state (renamed from engine_state)

Key-value store for safety guardrail configuration. Renamed from `engine_state` in migration 006.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| key | TEXT | PRIMARY KEY | Setting identifier |
| value | TEXT | NOT NULL | JSON-encoded value |
| updated_at | TEXT | NOT NULL, default now | ISO 8601 timestamp |
| updated_by | TEXT | NOT NULL, default 'system' | Who made the change |

**Rows**:
- `kill_switch`: `{"active": false, "toggled_at": null, "toggled_by": null}`
- `risk_settings`: `{"max_position_pct": 0.10, "max_daily_loss_pct": 0.05, "max_trades_per_day": 20, "max_positions_per_symbol": 2}`

### Tables PRESERVED (no changes)

| Table | Migration | Purpose |
|-------|-----------|---------|
| audit_log | 001 | Append-only audit trail |
| company | 002 | Watchlist companies |
| source_document | 002 | Ingested research documents |
| research_signal | 002 | Analysis signals with citations |
| notable_investor | 002 | Tracked institutional investors |
| ingestion_run | 002 | Pipeline execution tracking |

### Tables DROPPED (migration 006)

| Table | Was In | Replaced By |
|-------|--------|-------------|
| price_bar | 003 | Alpaca MCP stock data tools |
| technical_indicator | 003 | MaverickMCP / QuantConnect MCP |
| market_data_fetch | 003 | N/A (tracking no longer needed) |
| trade_proposal | 004 | Human decision in conversation |
| proposal_source | 004 | N/A (no proposal system) |
| risk_check_result | 004 | N/A (utilization tracking deferred) |
| broker_order | 005 | Alpaca MCP order tools |
| position_snapshot | 005 | Alpaca MCP position tools |

Note: `engine_state` from migration 004 is renamed to `safety_state`, not dropped.

## State Transitions

### Kill Switch

```
OFF (normal) ←→ ON (all trading halted)
```

Toggled by: operator (programmatic call or future MCP tool)

### Risk Settings

Static configuration — no state transitions. Values are updated by the operator and read by future execution-layer components.

## Validation Rules

| Setting | Type | Min | Max | Default |
|---------|------|-----|-----|---------|
| max_position_pct | float | 0.01 | 0.50 | 0.10 |
| max_daily_loss_pct | float | 0.01 | 0.20 | 0.05 |
| max_trades_per_day | int | 1 | 100 | 20 |
| max_positions_per_symbol | int | 1 | 10 | 2 |
