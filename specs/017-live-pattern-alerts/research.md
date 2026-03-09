# Research: Live Pattern Alerts & Paper Trade Execution

**Feature**: 017-live-pattern-alerts
**Date**: 2026-03-08

## R1: Scanner Architecture — Reuse vs. New Trigger Evaluation

**Decision**: Reuse the existing `_evaluate_trigger()` logic from executor.py for live market data evaluation, and `_check_trigger()` from backtest.py for cached bar evaluation. The scanner orchestrates which approach to use based on data availability.

**Rationale**: Two trigger evaluation implementations already exist:
1. `executor._evaluate_trigger(ticker)` — fetches last 7 days of bars from Alpaca, evaluates price_change_pct and volume_spike conditions against latest vs. previous bar.
2. `backtest._check_trigger(rule_set, bars, idx)` — evaluates the same conditions against a historical bar array with 20-bar volume lookback.

The scanner needs to:
1. Fetch recent bars for each ticker (using existing `fetch_and_cache_bars`)
2. Evaluate trigger conditions against the latest bars
3. This is functionally equivalent to what the backtest engine does with `_check_trigger`

The cleanest approach: extract the trigger evaluation logic into a standalone function in scanner.py that works with bar arrays (like the backtest version), and feed it recently-fetched bars. This avoids importing private methods and keeps the scanner self-contained.

**Alternatives considered**:
- **Import executor._evaluate_trigger directly**: It's tightly coupled to the PatternMonitor class (uses self.rule_set, self.alpaca_client). Would need refactoring. Rejected.
- **Import backtest._check_trigger directly**: It's a module-level function but considered private (underscore prefix). Could work, but the scanner has slightly different needs (needs to return trigger details, not just bool). Rejected for direct import, but the logic will be replicated with enhancements.

## R2: Alert Deduplication Strategy

**Decision**: Use a composite key of (pattern_id, ticker, trigger_date) with a configurable cooldown period (default 24 hours). Before creating an alert, check if one already exists for the same pattern+ticker within the cooldown window.

**Rationale**: The same trigger conditions can persist across multiple scans (e.g., MRNA stays up 7% for several hours). Without deduplication, each scan would generate a new alert. The cooldown approach is simple and matches how market events work — a spike on Monday is a different event from a spike on Wednesday, but multiple scans within the same day seeing the same spike should produce only one alert.

**Alternatives considered**:
- **Hash-based deduplication** (hash trigger details): Fragile — small price changes between scans would produce different hashes even for the "same" event. Rejected.
- **Event fingerprinting** (exact match on all trigger values): Too strict — volumes and prices change slightly between scans. Rejected.
- **No deduplication** (user filters manually): Creates alert fatigue. Rejected.

## R3: Alert Storage — New Table vs. Audit Log

**Decision**: Create a dedicated `pattern_alert` table with its own lifecycle (new → acknowledged → acted_on → dismissed). Keep audit_log for event recording (scanner_run, alert_created, trade_auto_executed).

**Rationale**: The audit_log table is append-only and designed for accountability, not user interaction. Alerts need a mutable lifecycle (Jordan acknowledges, acts on, or dismisses them). A separate table allows efficient querying (list new alerts, filter by pattern/ticker, count by status) without scanning the entire audit log.

**Alternatives considered**:
- **Use audit_log with status tracking**: Would require breaking the append-only pattern. Complicates queries. Rejected.
- **File-based alerts** (JSON/markdown): Harder to query, no atomic updates. Rejected.

## R4: Auto-Execution Safety Architecture

**Decision**: Auto-execution is a per-pattern flag (`auto_execute` boolean column on `trading_pattern`). When a trigger fires for an auto-execute pattern, the scanner: (1) checks kill switch, (2) checks daily trade count, (3) creates paper trade via existing `create_paper_trade()`, (4) submits order via Alpaca paper trading API, (5) records result in alert. If any safety check fails, the alert is still created with a `blocked` reason.

**Rationale**: This reuses the existing safety infrastructure (kill switch, risk settings) and paper trade flow (create_paper_trade → submit order → update status). The per-pattern flag ensures explicit opt-in. The safety checks happen at execution time, not configuration time, so they respond to real-time conditions (e.g., daily trade limit reached mid-day).

**Alternatives considered**:
- **Global auto-execute flag**: Too coarse — some patterns are high-confidence, others are experimental. Rejected.
- **Separate auto-execution service**: Over-engineered for a single-user CLI tool. Rejected.
- **Queue-based execution** (alert → queue → executor): Adds complexity without benefit for a single-user synchronous tool. Rejected.

## R5: Scanner Scheduling — One-Shot vs. Recurring

**Decision**: Support both modes via the same CLI command. Default is one-shot (scan once, print results, exit). With `--watch N` flag, the scanner loops: scan, sleep N minutes, repeat. Uses the same simple polling pattern as the existing paper-trade monitor (`while True: scan(); time.sleep(interval)`).

**Rationale**: One-shot is useful for ad-hoc checks ("what's triggering right now?"). Recurring is useful for continuous monitoring during market hours. The existing executor.py already uses this pattern successfully, and Jordan is familiar with it.

**Alternatives considered**:
- **Cron/launchd integration**: Adds OS-level complexity, harder to debug. Can be added later. Rejected for MVP.
- **Background daemon**: Requires process management, PID files, signal handling. Over-engineered for single-user. Rejected.
- **MCP-only scanning** (Claude Desktop polls): Depends on Claude Desktop being open. Not reliable for monitoring. Rejected as primary approach (MCP tool added for alert retrieval, not scanning).
