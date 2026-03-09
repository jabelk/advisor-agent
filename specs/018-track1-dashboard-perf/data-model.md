# Data Model: Track 1 Completion — Dashboard, Performance & Scheduled Scanning

**Feature**: 018-track1-dashboard-perf
**Date**: 2026-03-08

## No New Tables

This feature does not create new database tables. All dashboard and performance data is derived from existing tables via aggregation queries:

- `trading_pattern` — pattern status counts, names, auto_execute flag
- `backtest_result` — win rate, avg return, trade count (baseline predictions)
- `paper_trade` — closed trade P&L, win rate (actual performance)
- `pattern_alert` — alert counts by status, recent alerts
- `covered_call_cycle` — covered call performance (for relevant patterns)

## In-Memory Models

### DashboardSummary (returned by dashboard command)

```text
patterns:
  total: int
  by_status: dict[str, int]  # {draft: 2, backtested: 1, paper_trading: 3, retired: 1}

paper_trades:
  total_trades: int
  closed_trades: int
  open_trades: int
  wins: int
  losses: int
  win_rate: float
  total_pnl: float
  avg_pnl: float

alerts:
  last_7_days: int
  by_status: dict[str, int]  # {new: 3, acknowledged: 1, acted_on: 2, dismissed: 0}

active_patterns: list[ActivePatternSummary]
```

### ActivePatternSummary (per paper_trading pattern in dashboard)

```text
pattern_id: int
pattern_name: str
backtest_win_rate: float | None
backtest_avg_return: float | None
paper_trade_win_rate: float | None
paper_trade_count: int
paper_trade_pnl: float
open_trades: int
alert_count_7d: int
auto_execute: bool
divergence_warning: bool  # True if |backtest_win_rate - paper_trade_win_rate| > 10pp
```

### PerformanceComparison (returned by perf command)

```text
pattern_id: int
pattern_name: str
pattern_status: str
days_in_paper_trading: int | None

backtest:
  win_rate: float
  avg_return_pct: float
  trade_count: int
  total_return_pct: float
  max_drawdown_pct: float
  sharpe_ratio: float | None
  backtest_date: str

paper_trading:
  win_rate: float | None
  avg_return_pct: float | None
  trade_count: int
  total_pnl: float
  open_trades: int

divergence:
  win_rate_diff_pp: float | None  # percentage points
  avg_return_diff_pp: float | None
  warning: bool  # True if win_rate divergence > 10pp
  note: str | None  # e.g., "No closed trades yet" or "0 triggers in 30+ days"
```

### ScanScheduleConfig (schedule management)

```text
interval_minutes: int  # how often to scan (e.g., 15)
market_hours_only: bool  # default True
plist_path: str  # ~/Library/LaunchAgents/com.advisor-agent.scanner.plist
active: bool  # True if schedule is installed and not paused
last_run: str | None  # ISO 8601 timestamp from audit log
```

## Relationships

- `DashboardSummary.active_patterns` aggregates data from `trading_pattern` + `backtest_result` + `paper_trade` + `pattern_alert` for each `paper_trading` pattern
- `PerformanceComparison.backtest` uses the most recent `backtest_result` row for the pattern
- `PerformanceComparison.paper_trading` aggregates from `paper_trade` WHERE status='closed'
- `ScanScheduleConfig` is derived from the filesystem (plist exists = installed) and audit_log (last scanner_run event)
