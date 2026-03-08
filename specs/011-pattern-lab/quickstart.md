# Quickstart: Pattern Lab

**Feature**: 011-pattern-lab

## What It Does

Pattern Lab lets you describe a trading pattern in plain English, test it against historical data, and then run it forward as a paper trade through Alpaca — all without writing code.

## Workflow

```
Describe → Confirm Rules → Backtest → Paper Trade → Evaluate
```

1. **Describe**: Tell the system a pattern you've noticed in plain text
2. **Confirm**: Review the structured rules it generates, edit if needed
3. **Backtest**: See how the pattern performed historically, including when it worked and when it stopped
4. **Paper Trade**: Run the pattern in real-time with Alpaca paper trading (no real money)
5. **Evaluate**: Compare patterns, retire ones that don't work

## Quick Example

```bash
# Describe a pattern
finance-agent pattern describe "Pharma stocks spike on big news, then dip 2%+ within 2 days. Buy calls on the dip."

# Backtest it over the past year
finance-agent pattern backtest 1 --start 2025-03-01 --end 2026-03-01

# Start paper trading it
finance-agent pattern paper-trade 1

# Check how your patterns are doing
finance-agent pattern list
```

## Key Files

| File | Purpose |
|------|---------|
| `src/finance_agent/patterns/models.py` | Pattern, RuleSet, BacktestResult data models |
| `src/finance_agent/patterns/parser.py` | Plain text → structured rules (via Claude) |
| `src/finance_agent/patterns/backtest.py` | Historical pattern evaluation engine |
| `src/finance_agent/patterns/executor.py` | Real-time trigger detection + Alpaca paper trades |
| `src/finance_agent/patterns/storage.py` | Pattern CRUD operations (SQLite) |
| `migrations/007_pattern_lab.sql` | Database schema for patterns, backtests, trades |

## Safety

- All trades are paper trades by default (Constitution Principle IV)
- Kill switch from safety module halts all pattern monitoring
- Position size and daily loss limits enforced on every trade
- Human approval required by default for each paper trade
- Options-specific patterns must include strike and expiration parameters
