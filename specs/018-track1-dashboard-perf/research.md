# Research: Track 1 Completion — Dashboard, Performance & Scheduled Scanning

**Feature**: 018-track1-dashboard-perf
**Date**: 2026-03-08

## R1: Dashboard Data Aggregation — New Queries vs. Existing Functions

**Decision**: Create a new `dashboard.py` module with dedicated aggregation functions that combine data from multiple tables in single queries, rather than calling existing per-pattern functions in a loop.

**Rationale**: The existing `get_paper_trade_summary(conn, pattern_id)` in storage.py works per-pattern, which would require N+1 queries for N patterns. A dashboard needs cross-pattern aggregation (total P&L across all patterns, alert counts by status) which is more efficiently done with single SQL queries that GROUP BY pattern_id. The new module can still reuse the same table schema and query patterns.

**Alternatives considered**:
- **Call existing storage.py functions in a loop**: Simple but O(N) queries. Rejected for performance with many patterns, though acceptable for MVP scale (~20 patterns).
- **Materialized views / summary tables**: Over-engineered for SQLite single-user workload. Rejected.
- **Cache dashboard results**: Unnecessary — all queries hit local SQLite with indexes, should be <100ms even with 1000 rows.

## R2: Performance Comparison — Backtest vs. Paper Trade Metrics

**Decision**: Compare the most recent backtest result's win_count/trade_count against paper_trade closed trades for the same pattern. Divergence threshold of 10 percentage points (from spec) flags a warning. Comparison returns both raw metrics and a divergence indicator.

**Rationale**: The backtest_result table stores win_count and trade_count per backtest run. Paper trades are in paper_trade table with status='closed' and a pnl column. The comparison is a straightforward join/aggregation. Using the most recent backtest (ORDER BY created_at DESC LIMIT 1) matches the spec assumption.

**Alternatives considered**:
- **Average across all backtests**: Could dilute recent improvements. Rejected — most recent backtest is the most relevant baseline.
- **Weighted average by recency**: Over-engineered for current needs. Rejected.
- **Include open trades in comparison**: Skews win rate since open trades don't have P&L yet. Rejected — only closed trades are comparable to backtest predictions.

## R3: Scheduled Scanning — launchd vs. cron vs. Custom Daemon

**Decision**: Use launchd on macOS (primary platform) with a generated plist file in `~/Library/LaunchAgents/`. Provide a cron fallback for Linux. The CLI generates, installs, and manages the plist/crontab entries. The plist runs the existing `finance-agent pattern scan` command at the configured interval.

**Rationale**: Jordan uses macOS. launchd is the native macOS scheduler — it survives reboots, handles logging, and is simpler than running a background daemon. The plist specifies `StartInterval` (seconds between runs) and the scanner command. Market hours gating is done inside the scan command itself (check current time in US/Eastern, skip if outside 9:30-16:00 or weekend/holiday) rather than in the plist schedule, because launchd's `StartCalendarInterval` doesn't support timezone-aware conditional execution.

**Alternatives considered**:
- **Custom background daemon**: Requires PID management, signal handling, process supervision. Over-engineered for single-user CLI. Rejected.
- **Pure cron**: Not native on macOS (requires homebrew cron or launchd wrapper). Rejected as primary but kept as Linux fallback.
- **launchd StartCalendarInterval**: Only supports fixed times, not "every N minutes during a window." Would need multiple entries. Rejected in favor of StartInterval + in-process market hours check.
- **systemd timer (Linux)**: Good for Linux but Jordan is on macOS. Could add later for Linux support. Deferred.

## R4: Market Hours Detection

**Decision**: Implement a simple `is_market_open()` function that checks the current time against US Eastern market hours (9:30 AM - 4:00 PM ET, Monday-Friday). Uses a static list of 2026 US market holidays. The scheduled scanner calls this before each scan and skips silently if the market is closed.

**Rationale**: Using a static holiday list is simpler and more reliable than calling an external API. The list only needs updating once per year. The `zoneinfo` module (stdlib since Python 3.9) handles US/Eastern timezone conversion without third-party dependencies.

**Alternatives considered**:
- **External holiday API (e.g., Alpaca calendar endpoint)**: Adds network dependency for a simple check. Rejected for MVP — can add later.
- **No holiday detection (just weekdays)**: Would trigger scans on market holidays, wasting API calls. Acceptable but slightly wasteful. Rejected.
- **pandas_market_calendars**: Heavy dependency for a simple check. Rejected.

## R5: MCP Tool Design — Dashboard vs. Individual Queries

**Decision**: Add two new MCP tools: `get_dashboard_summary` (returns the full dashboard data structure) and `get_performance_comparison` (returns backtest vs. paper trade comparison for a pattern or all patterns). These complement the existing `get_paper_trade_summary` and `get_pattern_alerts` tools.

**Rationale**: Claude Desktop users ask questions like "how are my patterns doing?" — a single dashboard tool returns everything needed for a comprehensive answer. The performance comparison tool enables questions like "is my pharma pattern working in practice?" Both tools are read-only and follow the existing MCP tool pattern (readonly connection, try/finally, return dict).

**Alternatives considered**:
- **Single mega-tool**: Combines dashboard + performance + alerts. Too much data in one response — Claude may not surface it well. Rejected.
- **Reuse existing tools only**: Claude would need to call 4+ tools and aggregate itself. Slower and less reliable. Rejected.
