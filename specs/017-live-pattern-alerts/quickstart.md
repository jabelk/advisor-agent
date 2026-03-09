# Quickstart: Live Pattern Alerts & Paper Trade Execution

**Feature**: 017-live-pattern-alerts

## What It Does

Adds a pattern scanner that evaluates all active (`paper_trading`) patterns against live market data and generates persistent alerts when trigger conditions are met. Alerts are viewable via CLI and Claude Desktop. Optionally, patterns can auto-execute paper trades when triggers fire.

## Prerequisites

- At least one pattern in `paper_trading` status (run `finance-agent pattern paper-trade <id>` first)
- Alpaca API keys configured in environment
- Internet access for market data fetching

## Scenario 1: One-Shot Pattern Scan

Scan all active patterns against current market data:

```bash
finance-agent pattern scan
```

**Expected**:
```
Pattern Scanner
  Patterns evaluated: 2
  Tickers scanned: 5
  Alerts generated: 1

  NEW ALERTS:
  #1  Pharma News Spike Dip  |  MRNA  |  2026-03-08
      Price: +7.2% ($42.26 → $45.30)  |  Volume: 2.1x avg
      Action: buy_call  |  Win rate: 50.0%
      Status: new
```

## Scenario 2: Review and Manage Alerts

List recent alerts:

```bash
finance-agent pattern alerts
finance-agent pattern alerts --status new
finance-agent pattern alerts --ticker MRNA
```

Acknowledge, act on, or dismiss:

```bash
finance-agent pattern alerts ack 1
finance-agent pattern alerts acted 1
finance-agent pattern alerts dismiss 2
```

## Scenario 3: Continuous Monitoring

Watch for triggers every 5 minutes during market hours:

```bash
finance-agent pattern scan --watch 5
```

**Expected**: Scanner runs every 5 minutes, printing new alerts as they appear. Ctrl+C to stop.

## Scenario 4: Auto-Execute Paper Trades

Enable auto-execution on a high-confidence pattern, then scan:

```bash
# Enable auto-execute (one-time setup)
finance-agent pattern auto-execute 1 --enable

# Scan — if pattern #1 triggers, paper trade is auto-submitted
finance-agent pattern scan
```

**Expected** (when trigger fires):
```
  NEW ALERTS:
  #3  Pharma News Spike Dip  |  MRNA  |  2026-03-08
      Price: +7.2% ($42.26 → $45.30)  |  Volume: 2.1x avg
      Action: buy_call  |  Win rate: 50.0%
      Status: new  |  AUTO-EXECUTED: paper trade #12 submitted
```

## Scenario 5: Alert Lookup via Claude Desktop

In Claude Desktop, ask:

> "What pattern alerts have fired in the last 3 days?"

**Expected**: Claude calls `get_pattern_alerts` and returns a summary like: "Your Pharma News Spike Dip pattern triggered on MRNA yesterday — MRNA spiked 7.2% on 2.1x volume. The pattern has a 50% win rate. You haven't acted on this alert yet."

## Key Files

| File | Purpose |
|------|---------|
| `src/finance_agent/patterns/scanner.py` | NEW: Scanner orchestration — evaluate triggers, generate alerts |
| `src/finance_agent/patterns/alert_storage.py` | NEW: Alert CRUD — create, list, filter, update status |
| `src/finance_agent/cli.py` | MODIFY: Add `scan`, `alerts`, `auto-execute` subcommands |
| `src/finance_agent/mcp/research_server.py` | MODIFY: Add `get_pattern_alerts` MCP tool |
| `migrations/010_pattern_alerts.sql` | NEW: pattern_alert table + auto_execute column |

## Safety

- Auto-execution defaults to OFF for all patterns. Must be explicitly enabled per pattern.
- Kill switch checked before every auto-execution. If active, trigger is still alerted but trade is blocked.
- Daily trade limit checked before every auto-execution.
- All auto-executions use paper trading only — never live.
- All scanner runs, alerts, and auto-executions are recorded in the audit log.
