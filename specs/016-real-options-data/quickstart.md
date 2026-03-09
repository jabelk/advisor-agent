# Quickstart: Real Options Chain Data

**Feature**: 016-real-options-data

## What It Does

Replaces the synthetic options pricing model (fixed leverage multipliers) with real historical option prices from the broker. Backtests now show actual premiums paid/received for specific option contracts, with graceful fallback to synthetic pricing when historical data is unavailable.

## Prerequisites

- Pattern Lab (011) is set up with at least one options-based pattern (buy_call or sell_call action)
- Alpaca API keys configured in environment (same as backtest/A/B testing)
- Internet access for initial option data fetching (cached after first fetch)

## Scenario 1: Backtest with Real Option Prices

Run a backtest for an options pattern:

```bash
finance-agent pattern backtest 1 --tickers ABBV --start 2024-01-01 --end 2024-12-31
```

**Expected**: Each trade in the results shows:
- The specific option contract symbol (e.g., `ABBV240315C00170000`)
- Whether pricing is "real" or "estimated"
- For real-priced trades: actual entry/exit premiums and volume
- For estimated trades: the familiar synthetic leverage calculation with a flag

**Example output** (trade detail):
```
Trade #1: ABBV240315C00170000 (real pricing)
  Entry: 2024-03-13 @ $4.50 (vol: 1,523)
  Exit:  2024-04-01 @ $2.10 (vol: 892)
  Return: -53.3%

Trade #2: MRNA240621C00125000 (estimated — no market data)
  Entry: 2024-06-19 (synthetic)
  Exit:  2024-07-15 (synthetic)
  Return: -50.0% (5x leverage estimate)
```

## Scenario 2: Covered Call with Real Premiums

Run a covered call backtest:

```bash
finance-agent pattern backtest <covered_call_id> --tickers ABBV --start 2024-01-01 --end 2024-12-31
```

**Expected**: Each covered call cycle shows the actual premium that would have been collected (real market price) or the Black-Scholes estimate with a flag if real data is unavailable.

## Scenario 3: Option Chain Lookup via MCP

In Claude Desktop, ask:

> "What call options were available for ABBV around March 15, 2024 with strikes between $165 and $175?"

**Expected**: Claude calls `get_option_chain_history` and returns a structured list of contracts with their symbols, prices, and volume. Claude presents the results conversationally, e.g., "There were 3 ABBV call contracts trading near March 15: the $165 call at $7.20, the $170 call at $4.50, and the $175 call at $2.30."

## Key Files

| File | Purpose |
|------|---------|
| `src/finance_agent/patterns/option_data.py` | NEW: OCC symbol construction, contract selection, option bar fetching/caching |
| `src/finance_agent/patterns/backtest.py` | MODIFY: Inject real option pricing at trade execution |
| `src/finance_agent/patterns/market_data.py` | MODIFY: Add option bar cache read/write functions |
| `src/finance_agent/mcp/research_server.py` | MODIFY: Add get_option_chain_history MCP tool |
| `migrations/009_option_cache.sql` | NEW: option_price_cache table |
| `tests/unit/test_option_data.py` | NEW: Unit tests for option data functions |

## Safety

- No trading operations — all tools are analysis and reporting only.
- Option bar fetching writes to the local cache only (performance optimization).
- Alpaca API keys read from environment variables, never exposed through tool parameters.
- Graceful fallback ensures backtests never fail due to missing option data — they fall back to synthetic pricing.
