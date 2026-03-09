# Tasks: Live Pattern Alerts & Paper Trade Execution

**Input**: Design documents from `/specs/017-live-pattern-alerts/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/scanner-alerts.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database migration and new module scaffolding

- [X] T001 Create migration file with pattern_alert table and auto_execute column in migrations/010_pattern_alerts.sql
- [X] T002 [P] Create scanner module scaffold in src/finance_agent/patterns/scanner.py
- [X] T003 [P] Create alert storage module scaffold in src/finance_agent/patterns/alert_storage.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core alert CRUD and trigger evaluation that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement evaluate_triggers function (price_change_pct, volume_spike conditions) in src/finance_agent/patterns/scanner.py
- [X] T005 [P] Implement create_alert with INSERT OR IGNORE deduplication in src/finance_agent/patterns/alert_storage.py
- [X] T006 [P] Implement list_alerts with status/pattern_id/ticker/days filtering in src/finance_agent/patterns/alert_storage.py
- [X] T007 [P] Implement update_alert_status (acknowledged, acted_on, dismissed) in src/finance_agent/patterns/alert_storage.py
- [X] T008 Add auto_execute column handling to pattern queries in src/finance_agent/patterns/storage.py

**Checkpoint**: Foundation ready — alert CRUD and trigger evaluation available for all user stories

---

## Phase 3: User Story 1 — Pattern Scanner with Alerts (Priority: P1) 🎯 MVP

**Goal**: Jordan can run a scan command that evaluates all paper_trading patterns against recent market data and generates persistent alerts when triggers fire.

**Independent Test**: Set a pattern to `paper_trading` status, run `finance-agent pattern scan`, verify triggers detected and alerts persisted with full context.

### Implementation for User Story 1

- [X] T009 [US1] Implement run_scan orchestrator (fetch paper_trading patterns, determine tickers, fetch bars, evaluate triggers, create alerts) in src/finance_agent/patterns/scanner.py
- [X] T010 [US1] Add cooldown-based deduplication check before alert creation in src/finance_agent/patterns/scanner.py
- [X] T011 [US1] Add audit log entries for scanner runs and alert creation in src/finance_agent/patterns/scanner.py
- [X] T012 [US1] Add `pattern scan` CLI subcommand (one-shot mode) in src/finance_agent/cli.py
- [X] T013 [US1] Add `--watch N` flag for recurring scan mode (loop with sleep) in src/finance_agent/cli.py
- [X] T014 [US1] Add `--cooldown N` flag for configurable deduplication window in src/finance_agent/cli.py

**Checkpoint**: Scanner runs, detects triggers, creates alerts, displays results — US1 fully functional

---

## Phase 4: User Story 2 — Alert Review and History (Priority: P2)

**Goal**: Jordan can review, filter, acknowledge, and dismiss alerts via CLI and Claude Desktop.

**Independent Test**: After scanner has generated alerts, run `finance-agent pattern alerts` and verify alerts displayed with full context, filterable, and status-updatable.

### Implementation for User Story 2

- [X] T015 [US2] Add `pattern alerts` CLI subcommand with --status, --pattern-id, --ticker, --days filters in src/finance_agent/cli.py
- [X] T016 [US2] Add `pattern alerts ack ID`, `pattern alerts dismiss ID`, `pattern alerts acted ID` subcommands in src/finance_agent/cli.py
- [X] T017 [US2] Add get_pattern_alerts MCP tool in src/finance_agent/mcp/research_server.py

**Checkpoint**: Alerts reviewable via CLI and Claude Desktop — US2 fully functional

---

## Phase 5: User Story 3 — Auto-Execute Paper Trades on Trigger (Priority: P3)

**Goal**: High-confidence patterns automatically submit paper trade orders when triggers fire, respecting all safety controls.

**Independent Test**: Enable auto-execute on a pattern, run the scanner when trigger conditions are met, verify paper trade submitted and alert records the auto-execution result.

### Implementation for User Story 3

- [X] T018 [US3] Add `pattern auto-execute ID --enable/--disable` CLI subcommand in src/finance_agent/cli.py
- [X] T019 [US3] Implement auto-execution logic in run_scan: check kill switch, check daily trade limit, submit paper trade via existing create_paper_trade flow in src/finance_agent/patterns/scanner.py
- [X] T020 [US3] Record auto_execute_result in alert (trade_id, order_id, blocked_reason, or error) in src/finance_agent/patterns/scanner.py
- [X] T021 [US3] Add audit log entries for auto-execution events (success and blocked) in src/finance_agent/patterns/scanner.py

**Checkpoint**: Auto-execution works with full safety checks — US3 fully functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Tests, validation, and regression checks

- [X] T022 [P] Add unit tests for evaluate_triggers in tests/unit/test_scanner.py
- [X] T023 [P] Add unit tests for alert CRUD (create, list, filter, update status, dedup) in tests/unit/test_alert_storage.py
- [X] T024 [P] Add unit tests for run_scan orchestration (mock bars + triggers) in tests/unit/test_scanner.py
- [X] T025 Update MCP integration test to include get_pattern_alerts in tests/integration/test_mcp_integration.py
- [X] T026 Update migration count and schema version assertions in tests/unit/test_db.py
- [X] T027 Run full test suite and fix any regressions
- [X] T028 Run quickstart.md scenario validation (manual live test)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on T001 (migration) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion (evaluate_triggers + alert CRUD)
- **US2 (Phase 4)**: Depends on Phase 2 completion (list_alerts + update_alert_status). Can run in parallel with US1 if alerts exist.
- **US3 (Phase 5)**: Depends on Phase 2 + Phase 3 (needs run_scan working to add auto-execute logic)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2. No dependency on other stories.
- **US2 (P2)**: Can start after Phase 2. Independent of US1 (only needs alert data in DB).
- **US3 (P3)**: Depends on US1 (extends run_scan with auto-execute path). Must wait for Phase 3 completion.

### Within Each User Story

- Scanner logic before CLI integration
- Core implementation before watch/recurring mode
- Alert storage before alert display

### Parallel Opportunities

- T002 and T003 (module scaffolds) can run in parallel
- T005, T006, T007 (alert CRUD functions) can run in parallel
- T022, T023, T024, T025 (tests) can run in parallel

---

## Parallel Example: Phase 2

```bash
# Launch all alert CRUD tasks together:
Task: "Implement create_alert in src/finance_agent/patterns/alert_storage.py"  [T005]
Task: "Implement list_alerts in src/finance_agent/patterns/alert_storage.py"   [T006]
Task: "Implement update_alert_status in src/finance_agent/patterns/alert_storage.py" [T007]
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (migration + scaffolds)
2. Complete Phase 2: Foundational (trigger eval + alert CRUD)
3. Complete Phase 3: User Story 1 (scanner + CLI scan command)
4. **STOP and VALIDATE**: Run `finance-agent pattern scan` with a paper_trading pattern
5. Verify alerts are created and displayed correctly

### Incremental Delivery

1. Setup + Foundational → Core infrastructure ready
2. Add US1 (Scanner) → Test with live data → MVP!
3. Add US2 (Alert Review) → Test filtering and status management
4. Add US3 (Auto-Execute) → Test with safety checks enabled
5. Polish → Full test suite, regression check

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Scanner reuses existing fetch_and_cache_bars for market data (research decision R1)
- Alert dedup uses (pattern_id, ticker, trigger_date) composite key with 24h cooldown (R2)
- Auto-execution reuses existing create_paper_trade + Alpaca paper trading flow (R4)
- Audit logging uses existing audit_log infrastructure
