# Quickstart: Portfolio Dashboard, Performance Tracking & Scheduled Scanning

**Feature**: 018-track1-dashboard-perf

## What It Does

Adds a portfolio dashboard for at-a-glance Pattern Lab status, performance tracking that compares backtest predictions against paper trade actuals, and scheduled scanning so the pattern scanner runs automatically during market hours.

## Prerequisites

- At least one pattern with backtest results (run `finance-agent pattern backtest <id>` first)
- For performance tracking: at least one pattern with closed paper trades
- For scheduling: macOS (launchd) or Linux (cron)
- Alpaca API keys configured in environment

## Scenario 1: Portfolio Dashboard

View the big picture across all patterns:

```bash
finance-agent pattern dashboard
```

**Expected**:
```
Portfolio Dashboard
═══════════════════

  Patterns:  5 total (1 draft, 1 backtested, 2 paper_trading, 1 retired)

  Paper Trades (all patterns):
    Closed: 12 trades  |  Win rate: 58.3%  |  P&L: +$342.50
    Open: 2 trades

  Alerts (last 7 days):  3 total (2 new, 1 acknowledged)

  Active Patterns:
  ID   Name                    BT Win%   PT Win%   Trades   P&L        Alerts
  ─────────────────────────────────────────────────────────────────────────────
  1    Pharma Spike Dip        50.0%     60.0%     5        +$200.00   2
  3    Biotech Pullback        38.0%     —         0        $0.00      1 ⚠️
```

## Scenario 2: Performance Comparison

Compare backtest predictions vs. paper trade actuals:

```bash
# Single pattern
finance-agent pattern perf 1

# All patterns
finance-agent pattern perf
```

**Expected** (single pattern):
```
Performance: Pharma Spike Dip (#1)
═══════════════════════════════════

                    Backtest        Paper Trading     Divergence
  Win rate:         50.0%           60.0%             +10.0pp ⚠️
  Avg return:       +2.5%           +3.1%             +0.6pp
  Trade count:      20              5
  Total return:     +50.0%          +15.5%
  Max drawdown:     -8.2%           —

  ⚠️ Paper trade win rate exceeds backtest by 10pp — monitor for reversion.
```

**Expected** (all patterns):
```
Performance Ranking
═══════════════════

  #   Pattern                  BT Win%   PT Win%   Divergence   PT P&L
  ────────────────────────────────────────────────────────────────────────
  1   Pharma Spike Dip         50.0%     60.0%     +10.0pp ⚠️   +$200.00
  3   Biotech Pullback         38.0%     —         No trades    $0.00
      └─ Note: In paper_trading for 45 days with 0 triggers. Consider adjusting thresholds.
```

## Scenario 3: Install Scan Schedule

Set up automatic scanning every 15 minutes during market hours:

```bash
finance-agent pattern schedule install --interval 15
```

**Expected**:
```
Scan schedule installed:
  Interval: every 15 minutes
  Market hours: 9:30 AM – 4:00 PM ET (weekdays only)
  Plist: ~/Library/LaunchAgents/com.advisor-agent.scanner.plist
  Status: active
```

## Scenario 4: Manage Scan Schedule

```bash
# Check schedule status
finance-agent pattern schedule list

# Pause scanning (e.g., going on vacation)
finance-agent pattern schedule pause

# Resume scanning
finance-agent pattern schedule resume

# Remove schedule entirely
finance-agent pattern schedule remove
```

**Expected** (list):
```
Scan Schedule:
  Interval: every 15 minutes
  Market hours: 9:30 AM – 4:00 PM ET
  Status: active
  Last run: 2026-03-08 14:30:00 ET
  Next run: ~2026-03-08 14:45:00 ET
```

## Scenario 5: Dashboard via Claude Desktop

In Claude Desktop, ask:

> "How are my patterns doing?"

**Expected**: Claude calls `get_dashboard_summary` and returns: "You have 2 active patterns. Overall paper trade win rate is 58.3% across 12 closed trades with +$342.50 P&L. Your Pharma Spike Dip pattern is outperforming its backtest (60% vs 50% win rate). You have 2 new alerts to review."

> "Is my biotech pattern working?"

**Expected**: Claude calls `get_performance_comparison` with pattern_id and returns: "Your Biotech Pullback pattern has been in paper trading for 45 days but hasn't triggered yet. The backtest showed a 38% win rate across 16 trades. You might want to broaden the ticker list or lower the trigger thresholds."

## Key Files

| File | Purpose |
|------|---------|
| `src/finance_agent/patterns/dashboard.py` | NEW: Dashboard aggregation + performance comparison queries |
| `src/finance_agent/scheduling/scan_schedule.py` | NEW: launchd/cron schedule management |
| `src/finance_agent/cli.py` | MODIFY: Add dashboard, perf, schedule subcommands |
| `src/finance_agent/mcp/research_server.py` | MODIFY: Add get_dashboard_summary, get_performance_comparison MCP tools |
