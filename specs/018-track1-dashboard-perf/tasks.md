# Tasks: Track 1 Completion — Dashboard, Performance & Scheduled Scanning

**Input**: Design documents from `/specs/018-track1-dashboard-perf/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new module directories and package structure

- [X] T001 Create scheduling package directory and `__init__.py` at `src/finance_agent/scheduling/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blocking tasks — this feature uses existing tables and infrastructure. All new code is story-specific.

**Checkpoint**: Setup complete — user story implementation can begin

---

## Phase 3: User Story 1 — Portfolio Dashboard (Priority: P1)

**Goal**: Single `pattern dashboard` command showing pattern status counts, aggregate paper trade P&L, recent alert counts, and per-pattern active summaries.

**Independent Test**: Run `finance-agent pattern dashboard` with patterns in various statuses and verify aggregated output displays pattern counts, P&L, alerts, and per-pattern table.

### Implementation for User Story 1

- [X] T002 [US1] Implement `get_dashboard_data(conn)` function in `src/finance_agent/patterns/dashboard.py` — queries trading_pattern GROUP BY status, aggregates paper_trade P&L (closed + open counts), aggregates pattern_alert for last 7 days by status, builds per-pattern summaries for paper_trading patterns (joining backtest_result, paper_trade, pattern_alert), computes divergence_warning (>10pp diff). Returns DashboardSummary dict per data-model.md
- [X] T003 [US1] Implement `format_dashboard(data)` helper in `src/finance_agent/patterns/dashboard.py` — formats DashboardSummary dict into the CLI display output matching quickstart.md Scenario 1 (pattern counts, P&L summary, alert summary, active patterns table). Handle empty-state message when no patterns exist.
- [X] T004 [US1] Add `pattern dashboard` subcommand to `src/finance_agent/cli.py` — calls `get_dashboard_data(conn)` and `format_dashboard(data)`, prints formatted output
- [X] T005 [US1] Add `get_dashboard_summary` MCP tool to `src/finance_agent/mcp/research_server.py` — `@mcp.tool()` decorator, readonly connection via `_get_readonly_conn()`, calls `get_dashboard_data(conn)`, returns dict per MCP contract, try/finally with conn.close()
- [X] T006 [US1] Write unit tests for `get_dashboard_data` in `tests/unit/test_dashboard.py` — test pattern count aggregation, paper trade P&L aggregation, alert count aggregation, per-pattern summaries with divergence_warning, empty database case

**Checkpoint**: `finance-agent pattern dashboard` displays aggregated portfolio view

---

## Phase 4: User Story 2 — Performance Tracking (Priority: P2)

**Goal**: `pattern perf [ID]` command showing side-by-side backtest vs paper trade metrics with divergence warnings.

**Independent Test**: Run `finance-agent pattern perf <id>` for a pattern with both backtest and closed paper trades, verify backtest/paper metrics displayed side-by-side with divergence indicator.

### Implementation for User Story 2

- [X] T007 [US2] Implement `get_performance_comparison(conn, pattern_id=None)` function in `src/finance_agent/patterns/dashboard.py` — for each pattern (or specific one): fetch most recent backtest_result (win_rate, avg_return_pct, trade_count, total_return_pct, max_drawdown_pct, sharpe_ratio), aggregate closed paper_trades (wins, total, pnl, avg_return), compute divergence (win_rate_diff_pp, avg_return_diff_pp, warning if >10pp), add notes for no-trades or 30+ days with 0 alerts. Returns list[PerformanceComparison] per data-model.md
- [X] T008 [US2] Implement `format_performance(comparisons, single=False)` helper in `src/finance_agent/patterns/dashboard.py` — formats single-pattern detailed view (matching quickstart.md Scenario 2 single output) and all-patterns ranking table (matching quickstart.md Scenario 2 all output) with divergence warnings and notes
- [X] T009 [US2] Add `pattern perf [PATTERN_ID]` subcommand to `src/finance_agent/cli.py` — calls `get_performance_comparison(conn, pattern_id)` and `format_performance(comparisons, single)`, prints formatted output
- [X] T010 [US2] Add `get_performance_comparison` MCP tool to `src/finance_agent/mcp/research_server.py` — `@mcp.tool()` decorator, readonly connection, takes optional pattern_id (int, default 0 means all), calls `get_performance_comparison(conn, pattern_id or None)`, returns dict per MCP contract
- [X] T011 [US2] Write unit tests for `get_performance_comparison` in `tests/unit/test_dashboard.py` — test single pattern with both backtest and paper trades, pattern with backtest but no paper trades, divergence warning at >10pp, 30+ days with 0 alerts note, all-patterns ranking

**Checkpoint**: `finance-agent pattern perf` shows backtest vs paper trade comparison with divergence warnings

---

## Phase 5: User Story 3 — Scheduled Scanning (Priority: P3)

**Goal**: Install/manage a launchd (macOS) or cron (Linux) schedule so the pattern scanner runs automatically during market hours.

**Independent Test**: Run `finance-agent pattern schedule install --interval 15`, verify plist is created, then list/pause/resume/remove the schedule.

### Implementation for User Story 3

- [X] T012 [P] [US3] Implement `is_market_open(now=None)` function in `src/finance_agent/scheduling/scan_schedule.py` — checks if current time (or provided datetime) is within US market hours (9:30-16:00 ET, weekday, not a US 2026 holiday), uses `zoneinfo.ZoneInfo("America/New_York")` for timezone conversion, includes static 2026 US market holiday list
- [X] T013 [P] [US3] Implement `install_scan_schedule(interval_minutes, cooldown_hours=24)` function in `src/finance_agent/scheduling/scan_schedule.py` — generates launchd plist XML with StartInterval, command `finance-agent pattern scan --cooldown <N>`, environment variables for Alpaca keys from os.environ, writes to `~/Library/LaunchAgents/com.advisor-agent.scanner.plist`, runs `launchctl load`, returns dict with plist_path and status. On Linux: adds crontab entry via `crontab -l` + append
- [X] T014 [US3] Implement `get_scan_schedule()` function in `src/finance_agent/scheduling/scan_schedule.py` — checks if plist file exists, checks `launchctl list` for job, queries audit_log for most recent scanner_run event (last_run), returns ScanScheduleConfig dict or None
- [X] T015 [US3] Implement `pause_scan_schedule()` and `resume_scan_schedule()` functions in `src/finance_agent/scheduling/scan_schedule.py` — pause runs `launchctl unload` (plist stays on disk), resume runs `launchctl load`, returns bool for state changed
- [X] T016 [US3] Implement `remove_scan_schedule()` function in `src/finance_agent/scheduling/scan_schedule.py` — runs `launchctl unload` and deletes plist file, returns bool. On Linux: removes crontab entry
- [X] T017 [US3] Add `pattern schedule install|list|pause|resume|remove` subcommands to `src/finance_agent/cli.py` — install takes `--interval N` (required) and `--cooldown N` (optional, default 24), each subcommand calls corresponding function from scan_schedule.py and prints formatted output
- [X] T018 [US3] Write unit tests for `is_market_open` in `tests/unit/test_scan_schedule.py` — test weekday during market hours (True), before open (False), after close (False), weekend (False), US holiday (False), timezone conversion from non-ET system time
- [X] T019 [US3] Write unit tests for schedule management in `tests/unit/test_scan_schedule.py` — test plist XML generation with correct StartInterval and command, install/remove with mocked subprocess and filesystem, get_scan_schedule with existing/missing plist, pause/resume state changes

**Checkpoint**: `finance-agent pattern schedule install --interval 15` installs launchd schedule, list/pause/resume/remove all work

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Integration validation and final touches

- [X] T020 [P] Add `"get_dashboard_summary"` and `"get_performance_comparison"` to expected tools set in `tests/integration/test_mcp_integration.py`
- [X] T021 Run full test suite (`pytest`) and verify all existing + new tests pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: N/A — no blocking prerequisites
- **User Story 1 (Phase 3)**: Depends on Phase 1 only
- **User Story 2 (Phase 4)**: Depends on Phase 1 only (shares dashboard.py file with US1, so execute sequentially after US1)
- **User Story 3 (Phase 5)**: Depends on Phase 1 only (independent module, can run in parallel with US1/US2)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent — creates dashboard.py with `get_dashboard_data`
- **User Story 2 (P2)**: Adds to same file (dashboard.py) — execute after US1 to avoid merge conflicts
- **User Story 3 (P3)**: Fully independent module (scan_schedule.py) — can run in parallel with US1/US2

### Within Each User Story

- Core function before formatting helper
- Formatting helper before CLI command
- CLI command before MCP tool (follows same pattern)
- Tests can run after implementation (not TDD — no test-first requirement in spec)

### Parallel Opportunities

- T012 and T013 can run in parallel (different functions, same new file)
- T005 (MCP dashboard) and T006 (tests) can run in parallel after T004
- T010 (MCP perf) and T011 (tests) can run in parallel after T009
- US3 (Phase 5) can run in parallel with US1/US2 since it touches entirely different files

---

## Parallel Example: User Story 3

```bash
# Launch independent schedule functions together:
Task: "Implement is_market_open in src/finance_agent/scheduling/scan_schedule.py"
Task: "Implement install_scan_schedule in src/finance_agent/scheduling/scan_schedule.py"

# Launch tests together after implementation:
Task: "Write unit tests for is_market_open in tests/unit/test_scan_schedule.py"
Task: "Write unit tests for schedule management in tests/unit/test_scan_schedule.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (create scheduling package)
2. Complete Phase 3: User Story 1 (dashboard command + MCP tool)
3. **STOP and VALIDATE**: Run `finance-agent pattern dashboard` with real data
4. Continue to US2 and US3

### Incremental Delivery

1. Phase 1 → Setup complete
2. Phase 3 (US1) → Dashboard works → Validate
3. Phase 4 (US2) → Performance tracking works → Validate
4. Phase 5 (US3) → Scheduled scanning works → Validate
5. Phase 6 → All tests pass, MCP integration verified

---

## Notes

- No new database tables or migrations — all data from existing tables
- dashboard.py is shared between US1 and US2 (different functions, same file)
- scan_schedule.py is independent and can be developed in parallel
- MCP tools follow established pattern: `@mcp.tool()`, readonly conn, try/finally, return dict
- CLI commands follow established pattern in cli.py
- Market hours detection uses `zoneinfo` (stdlib) — no new dependencies
