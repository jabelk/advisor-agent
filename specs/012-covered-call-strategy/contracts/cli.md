# CLI Contract: Covered Call Income Strategy

All covered call commands extend the existing `finance-agent pattern` command group. No new top-level commands.

## Extended Commands

### `finance-agent pattern describe`

**Existing command** — extended to recognize covered call descriptions.

**Covered call detection**: When the description mentions "covered call", "sell calls", "write calls", or "sell call against shares", the parser should:
1. Set `action_type` to `sell_call`
2. Require or assume stock ownership
3. Apply covered call defaults (5% OTM, 30-day expiration, 50% profit target, 21-day roll)

**Naked call warning**: If the description says "sell call" without mentioning owning shares, display:
```
Warning: Naked calls carry unlimited risk. This system only supports covered calls
(selling calls against shares you own). Treating this as a covered call.
```

**Example output** (covered call specific):
```
Pattern: Monthly ABBV Covered Call
Status: draft

Trigger:
  Type: calendar
  Condition: Monthly cycle (sell on first trading day after prior expiration)

Stock Position:
  Ticker: ABBV
  Shares: 500 (5 contracts)

Call Sale:
  Strike: 5% OTM ($189.00 at current $180.00)
  Expiration: 30 days (monthly)

Exit Criteria:
  Close at 50% premium profit
  Roll at 21 DTE
  Accept assignment if ITM at expiration

Defaults applied:
  - Strike distance: 5% OTM (not specified)
  - Roll threshold: 21 DTE (not specified)
```

### `finance-agent pattern backtest <pattern_id>`

**Existing command** — extended with covered call-specific report output.

**Additional flags**:
- `--shares <N>` — Number of shares owned (default: 100). Used for total dollar income calculation.

**Covered call backtest report format**:
```
Backtest Results (saved as #N):
  Period: 2024-01-01 to 2025-12-31
  Ticker: ABBV
  Shares: 500

  Monthly Cycles: 24
  Avg Premium/Month: $1,425 ($2.85/share)
  Total Premium Collected: $34,200
  Annualized Income Yield: 7.9%

  Assignment Events: 5 of 24 cycles (20.8%)
  Avg Days Held Per Cycle: 28.3
  Cycles Closed Early (50% profit): 8
  Cycles Rolled: 6
  Cycles Expired Worthless: 5

  Buy-and-Hold Return: +22.4%
  Covered Call Return: +18.1% (stock gain + premium - capped upside)
  Capped Upside Cost: -$4,800 (forfeited gains from assignment)

  Month-by-Month:
    2024-01  | Premium: $1,350 | Stock: +1.2% | Outcome: expired | Net: +$1,350
    2024-02  | Premium: $1,500 | Stock: +3.8% | Outcome: assigned | Net: +$2,100
    ...

  WARNING: Premium estimates use historical volatility approximation (not actual option prices)
```

### `finance-agent pattern paper-trade <pattern_id>`

**Existing command** — extended for covered call order flow.

**Covered call paper trade flow**:
1. Validate pattern is `sell_call` action type and status is "backtested"
2. Look up real option chain via Alpaca to find matching strike/expiration
3. Display proposed trade:
   ```
   PROPOSE: Sell 5x ABBV 2026-04-18 $189 Call @ $2.85
   Estimated premium: $1,425
   Max profit: $6,425 (premium + stock gain to strike)
   Approve? [Y/n]:
   ```
4. Submit sell-to-open order via Alpaca MLEG API
5. Monitor position; at roll threshold, propose roll or let expire

### `finance-agent pattern compare <id1> <id2> [<id3>...]`

**Existing command** — extended with covered call metrics.

**Covered call comparison columns**:
```
  Metric                Conservative (5% OTM)  Moderate (3% OTM)    Aggressive (ATM)
  ────────────────────  ─────────────────────  ──────────────────   ─────────────────
  Annualized Yield      5.2%                    7.9%                  12.1%
  Assignment Freq       12.5%                   20.8%                 41.7%
  Avg Premium/Mo        $950                    $1,425                $2,200
  Capped Upside Cost    -$1,200                 -$4,800               -$12,600
  Total Return          +20.1%                  +18.1%                +14.2%
  Buy-and-Hold          +22.4%                  +22.4%                +22.4%
```

## MCP Tool Extensions

The existing Pattern Lab MCP tools (`list_patterns`, `get_pattern_detail`, `get_backtest_results`, `get_paper_trade_summary`) already handle covered call patterns through the standard pattern storage. No new MCP tools needed — covered call data is accessible through existing tools via `option_details_json` fields.
