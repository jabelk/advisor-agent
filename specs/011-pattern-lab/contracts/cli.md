# CLI Contract: Pattern Lab

**Feature**: 011-pattern-lab
**Date**: 2026-03-08

## Command Structure

All Pattern Lab commands live under `finance-agent pattern`.

### pattern describe

Parse a plain-text pattern description into structured rules.

```
finance-agent pattern describe "<description>"
```

**Arguments**:
- `description` (required): Plain-text pattern description in conversational language

**Output**: Structured rule summary showing trigger, entry signal, action, and exit criteria. Prompts for confirmation or editing.

**Example**:
```
$ finance-agent pattern describe "When a pharma company has major positive news, the stock spikes 5%+ in a day. Within 1-2 trading days it pulls back at least 2%. I buy call options on the pullback."

Pattern: Pharma News Dip (auto-named)
Status: draft

Trigger:
  Type: qualitative (news-based, requires confirmation)
  Sector: Healthcare/Pharma
  Condition: Major positive news event
  Price confirmation: 5%+ single-day gain

Entry Signal:
  Pullback: >= 2% from spike high
  Window: 1-2 trading days after spike

Action:
  Type: Buy call options
  Strike: ATM (default)
  Expiration: 30 days (default)

Exit Criteria:
  Profit target: not specified (default: 20%)
  Stop loss: not specified (default: 10%)
  Time exit: not specified (default: at expiration)

Confirm this pattern? [Y/edit/cancel]:
```

### pattern backtest

Run a pattern against historical data.

```
finance-agent pattern backtest <pattern_id> [--start DATE] [--end DATE] [--tickers TICKERS]
```

**Arguments**:
- `pattern_id` (required): ID of a confirmed pattern
- `--start` (optional): Start date for backtest (default: 1 year ago)
- `--end` (optional): End date for backtest (default: today)
- `--tickers` (optional): Comma-separated list of tickers to test against (default: all matching sector)

**Output**: Performance report with trigger count, win rate, returns, drawdown, and regime analysis.

### pattern paper-trade

Activate a pattern for live paper trading.

```
finance-agent pattern paper-trade <pattern_id> [--auto-approve] [--tickers TICKERS]
```

**Arguments**:
- `pattern_id` (required): ID of a backtested pattern
- `--auto-approve` (optional): Skip manual approval for each trade (default: require approval)
- `--tickers` (optional): Limit monitoring to specific tickers

**Output**: Starts monitoring. Logs trigger detections and trade proposals.

### pattern list

List all patterns with status and key metrics.

```
finance-agent pattern list [--status STATUS]
```

**Arguments**:
- `--status` (optional): Filter by status (draft, backtested, paper_trading, retired)

**Output**: Table of patterns with ID, name, status, win rate (if backtested), and P&L (if paper trading).

### pattern show

Show detailed information about a pattern.

```
finance-agent pattern show <pattern_id>
```

**Output**: Full pattern details including rules, backtest results, and paper trade history.

### pattern compare

Compare performance across patterns.

```
finance-agent pattern compare <pattern_id> <pattern_id> [<pattern_id>...]
```

**Output**: Side-by-side comparison table of win rate, avg return, max drawdown, regime sensitivity.

### pattern retire

Retire a pattern and stop any active monitoring.

```
finance-agent pattern retire <pattern_id>
```

**Output**: Confirmation of retirement. Closes any open paper positions.

## MCP Tools

New tools exposed via the existing FastMCP research server.

### list_patterns

```
list_patterns(status: str | None, limit: int = 20) -> list[dict]
```

Returns patterns with their status and summary metrics.

### get_pattern_detail

```
get_pattern_detail(pattern_id: int) -> dict
```

Returns full pattern info including rules, backtest results, and paper trades.

### get_backtest_results

```
get_backtest_results(pattern_id: int) -> dict
```

Returns detailed backtest report including regime analysis.

### get_paper_trade_summary

```
get_paper_trade_summary(pattern_id: int) -> dict
```

Returns paper trading performance summary for a pattern.
