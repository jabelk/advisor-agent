# Quickstart: Covered Call Income Strategy

## Prerequisites
- Pattern Lab (011) must be installed and working
- Alpaca paper trading account with options enabled
- Historical price data accessible via Alpaca

## End-to-End Flow

### 1. Describe a covered call pattern
```bash
finance-agent pattern describe "I own 500 shares of ABBV. Sell monthly covered calls 5% out of the money, close at 50% profit or roll at 21 days to expiration"
```

### 2. Backtest against historical data
```bash
finance-agent pattern backtest <pattern_id> --start 2024-01-01 --end 2025-12-31 --shares 500
```

### 3. Compare conservative vs aggressive
```bash
# Create multiple variants with different strike distances
finance-agent pattern describe "Sell monthly covered calls on ABBV 3% OTM, close at 50% profit, roll at 21 DTE"
finance-agent pattern describe "Sell monthly covered calls on ABBV at-the-money, close at 50% profit, roll at 21 DTE"

# Backtest each, then compare
finance-agent pattern compare <id1> <id2> <id3>
```

### 4. Paper trade the winning strategy
```bash
finance-agent pattern paper-trade <pattern_id>
```

## Key Files

| File | Purpose |
|------|---------|
| `src/finance_agent/patterns/option_pricing.py` | Black-Scholes premium estimation, historical volatility |
| `src/finance_agent/patterns/backtest.py` | Covered call cycle simulation |
| `src/finance_agent/patterns/executor.py` | Alpaca multi-leg order execution |
| `src/finance_agent/patterns/models.py` | CoveredCallCycle model |
| `migrations/008_covered_call.sql` | covered_call_cycle table |
