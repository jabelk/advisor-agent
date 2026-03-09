# Dashboard, Performance & Schedule Contracts

**Feature**: 018-track1-dashboard-perf
**Date**: 2026-03-08

## Internal Functions

### get_dashboard_data

Aggregate all dashboard data in a single call.

**Parameters**:
- `conn` (db connection, required)

**Returns**: `DashboardSummary` dict with patterns (total, by_status), paper_trades (aggregate P&L), alerts (last 7 days by status), active_patterns (list of per-pattern summaries).

**Behavior**:
- Queries trading_pattern GROUP BY status for pattern counts
- Queries paper_trade WHERE status='closed' for aggregate P&L
- Queries paper_trade WHERE status='executed' for open trade count
- Queries pattern_alert WHERE created_at >= 7 days ago GROUP BY status
- For each paper_trading pattern: joins backtest_result (most recent) + paper_trade + pattern_alert for per-pattern summary
- Computes divergence_warning for each active pattern

---

### get_performance_comparison

Compare backtest predictions vs. paper trade actuals for one or all patterns.

**Parameters**:
- `conn` (db connection, required)
- `pattern_id` (int, optional): Specific pattern. Default: all patterns with backtest data.

**Returns**: `list[PerformanceComparison]` — one per pattern.

**Behavior**:
- For each pattern: fetches most recent backtest_result (win_count, trade_count, avg_return_pct, etc.)
- Fetches paper_trade WHERE status='closed' aggregated (wins, total, pnl)
- Computes divergence (win_rate_diff_pp, warning if >10pp)
- If no closed paper trades: note="No closed trades yet"
- If paper_trading for 30+ days with 0 alerts: note="No triggers in 30+ days — consider adjusting thresholds"

---

### is_market_open

Check if US stock market is currently open.

**Parameters**: None (uses current system time)

**Returns**: `bool` — True if within market hours (9:30-16:00 ET, weekday, not a holiday).

---

### install_scan_schedule

Install a launchd plist (macOS) or crontab entry (Linux) for recurring scans.

**Parameters**:
- `interval_minutes` (int, required): Scan interval (e.g., 15)
- `cooldown_hours` (int, optional): Alert deduplication window. Default: 24.

**Returns**: `dict` with plist_path and status.

**Behavior**:
- Generates launchd plist with StartInterval = interval_minutes * 60
- Command: `finance-agent pattern scan --cooldown <N>`
- Includes market hours check inside the scan (scanner skips if market closed)
- Writes to ~/Library/LaunchAgents/com.advisor-agent.scanner.plist
- Runs `launchctl load` to activate
- On Linux: adds crontab entry instead

---

### get_scan_schedule

Get current schedule status.

**Parameters**: None

**Returns**: `ScanScheduleConfig` dict or None if no schedule installed.

**Behavior**:
- Checks if plist file exists at expected path
- Checks launchctl list for the job
- Queries audit_log for most recent scanner_run event (last_run)

---

### remove_scan_schedule

Remove the scan schedule.

**Parameters**: None

**Returns**: `bool` — True if removed.

**Behavior**:
- Runs `launchctl unload` and deletes plist file
- On Linux: removes crontab entry

---

### pause_scan_schedule / resume_scan_schedule

Pause or resume the schedule without deleting it.

**Parameters**: None

**Returns**: `bool` — True if state changed.

**Behavior**:
- Pause: `launchctl unload` (plist remains on disk)
- Resume: `launchctl load` (re-activates existing plist)

---

## CLI Commands

### `finance-agent pattern dashboard`

Display the portfolio dashboard.

**Arguments**: None

**Output**: Formatted dashboard with pattern status summary, aggregate P&L, alert counts, and per-pattern active pattern table.

---

### `finance-agent pattern perf [PATTERN_ID]`

Show performance comparison.

**Arguments**:
- `pattern_id` (optional): Specific pattern ID. Default: all patterns with backtest data.

**Output**: Side-by-side backtest vs. paper trade metrics with divergence warnings.

---

### `finance-agent pattern schedule install`

Install the scan schedule.

**Arguments**:
- `--interval N` (required): Scan interval in minutes.
- `--cooldown N` (optional): Deduplication cooldown hours. Default: 24.

---

### `finance-agent pattern schedule list`

Show current schedule status.

---

### `finance-agent pattern schedule pause`

Pause the scan schedule.

### `finance-agent pattern schedule resume`

Resume a paused scan schedule.

### `finance-agent pattern schedule remove`

Remove the scan schedule entirely.

---

## MCP Tool Contracts

### get_dashboard_summary

Retrieve the full portfolio dashboard for Claude Desktop.

**Parameters**: None

**Returns** (success):
```json
{
  "patterns": {"total": 5, "by_status": {"draft": 1, "backtested": 1, "paper_trading": 2, "retired": 1}},
  "paper_trades": {"total_trades": 12, "wins": 7, "losses": 5, "win_rate": 0.583, "total_pnl": 342.50},
  "alerts": {"last_7_days": 3, "by_status": {"new": 2, "acknowledged": 1}},
  "active_patterns": [
    {"pattern_id": 1, "pattern_name": "Pharma Spike Dip", "backtest_win_rate": 0.50, "paper_trade_win_rate": 0.60, "paper_trade_pnl": 200.0, "divergence_warning": false}
  ]
}
```

---

### get_performance_comparison

Retrieve backtest vs. paper trade comparison.

**Parameters**:
- `pattern_id` (int, optional): Specific pattern. Default: 0 (all patterns).

**Returns** (success):
```json
{
  "comparisons": [
    {
      "pattern_id": 1,
      "pattern_name": "Pharma Spike Dip",
      "backtest": {"win_rate": 0.50, "avg_return_pct": 2.5, "trade_count": 20},
      "paper_trading": {"win_rate": 0.60, "avg_return_pct": 3.1, "trade_count": 5},
      "divergence": {"win_rate_diff_pp": 10.0, "warning": true}
    }
  ],
  "total": 1
}
```
