# Tasks: Decision Engine

**Input**: Design documents from `/specs/004-decision-engine/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: Unit tests (mocked Alpaca + Anthropic clients) and integration tests (live Alpaca API) are included per project convention.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module structure, migration file, and shared engine components (account wrapper, state persistence)

- [x] T001 Update engine module `__init__.py` with docstring at src/finance_agent/engine/__init__.py
- [x] T002 [P] Create migration file `004_decision_engine.sql` at migrations/004_decision_engine.sql with trade_proposal, proposal_source, risk_check_result, and engine_state tables per data-model.md (copy SQL verbatim); insert default kill_switch and risk_settings rows
- [x] T003 [P] Implement Alpaca TradingClient wrapper in src/finance_agent/engine/account.py — functions: `create_trading_client(api_key, secret_key, paper)` returning TradingClient; `get_account_summary(client)` returning dict with equity, buying_power, cash, last_equity; `get_positions(client)` returning list of position dicts; `get_daily_orders(client)` returning today's filled order count; `get_daily_pnl(client)` returning dict with total_change, unrealized, realized_estimate. All numeric fields cast from Optional[str] to float with None guards.
- [x] T004 [P] Implement engine state persistence in src/finance_agent/engine/state.py — functions: `get_kill_switch(conn)` returning bool; `set_kill_switch(conn, active, toggled_by)` with audit logging; `get_risk_settings(conn)` returning dict; `update_risk_setting(conn, key, value, updated_by)` with validation and audit logging. State stored as JSON in engine_state table.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Unit test scaffolding and migration verification — MUST complete before any user story

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create unit test file for engine module at tests/unit/test_engine.py with test class scaffolding and shared fixtures (mock Alpaca TradingClient, mock Anthropic client, in-memory SQLite with all migrations applied through 004)
- [x] T006 Create integration test file at tests/integration/test_engine.py with shared fixtures (real Alpaca TradingClient, temp SQLite DB) and skip-if-no-keys decorator
- [x] T007 Verify migration applies cleanly: add a unit test in tests/unit/test_engine.py that runs 004_decision_engine.sql on a fresh DB (with prior migrations) and asserts all 4 tables, indexes, and default engine_state rows exist

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Generate Trade Proposals (Priority: P1) MVP

**Goal**: Operator can generate trade proposals for watchlist companies using research signals and market data, with hybrid confidence scoring, position sizing, and limit price derivation.

**Independent Test**: Add a company to watchlist with research signals and market data, run `engine generate`, verify proposals appear with scores, sizes, cited sources, and risk check results.

### Implementation for User Story 1

- [x] T008 [US1] Implement signal scoring in src/finance_agent/engine/scoring.py — functions: `classify_signal_direction(signal_dict)` returning -1/0/+1 based on signal_type and summary keywords; `recency_weight(created_at)` using exponential decay with 7-day half-life; `compute_signal_score(signals)` aggregating signals with type weights (sentiment 0.20, guidance_change 0.25, financial_metric 0.20, risk_factor 0.15, competitive_insight 0.10, leadership_change 0.05, investor_activity 0.05), confidence multipliers (high 1.0, medium 0.6, low 0.3), evidence multipliers (fact 1.0, inference 0.7), and recency weighting. Returns float -1.0 to +1.0.
- [x] T009 [US1] Implement indicator and momentum scoring in src/finance_agent/engine/scoring.py — functions: `compute_indicator_score(last_close, sma_20, sma_50, rsi_14, vwap)` scoring SMA alignment (0.30 weight), RSI momentum (0.35 weight), VWAP positioning (0.35 weight); `compute_momentum_score(daily_bars)` using 5-day return (0.50 weight), 20-day return (0.30 weight), volume confirmation (0.20 weight). Both return float -1.0 to +1.0.
- [x] T010 [US1] Implement ATR computation and limit price derivation in src/finance_agent/engine/scoring.py — functions: `compute_atr(daily_bars, period=14)` returning average true range; `compute_limit_price(side, last_close, atr_14, final_score)` using ATR-based offset scaled inversely with confidence (0.3x-0.7x ATR), floor 0.1%, cap 2.0%. Round to 2 decimal places.
- [x] T011 [US1] Implement base score composition and LLM adjustment in src/finance_agent/engine/scoring.py — functions: `compute_base_score(signal_score, indicator_score, momentum_score)` applying weights (0.50, 0.30, 0.20); `get_llm_adjustment(anthropic_client, ticker, base_score, components, signals, indicators)` calling Claude with the confidence adjustment prompt from research.md, parsing JSON response, clamping to +/-0.15; `compute_final_score(base_score, llm_adjustment)` clamping result to -1.0/+1.0. Include LLM prompt constants (system + user template).
- [x] T012 [US1] Implement proposal data validation and safety gates in src/finance_agent/engine/scoring.py — function: `should_generate_proposal(final_score, signals, threshold=0.45)` checking minimum signal count (3), minimum fact signals (1), minimum signal types (2), max signal age (14 days), and confidence threshold. Returns (bool, reason_string).
- [x] T013 [US1] Implement position sizing in src/finance_agent/engine/proposals.py — function: `compute_position_size(final_score, limit_price, equity, max_position_pct)` returning integer quantity = floor(abs(score) * max_position_pct * equity / limit_price), minimum 1 share if above threshold.
- [x] T014 [US1] Implement proposal generation orchestrator in src/finance_agent/engine/proposals.py — function: `generate_proposals(conn, trading_client, anthropic_client, risk_settings, ticker=None)` that iterates watchlist companies, queries signals + indicators + bars from DB, calls scoring pipeline, determines direction (positive=buy, negative=sell if position held), computes limit price and size, sets `expires_at` to today's 16:00 ET (market close) per FR-018, runs risk checks, saves proposal + sources + risk results to DB. Returns list of proposal dicts. Supports `dry_run` flag to skip DB writes.
- [x] T015 [US1] Implement proposal persistence and source citations in src/finance_agent/engine/proposals.py — functions: `save_proposal(conn, proposal_dict)` inserting into trade_proposal table and returning ID; `save_proposal_sources(conn, proposal_id, cited_signals, cited_indicators, cited_bars)` inserting into proposal_source table; `get_proposal(conn, proposal_id)` returning proposal with joined sources and risk checks.
- [x] T016 [US1] Implement `engine generate` CLI subcommand in src/finance_agent/cli.py — add `engine` parser group with `generate` subcommand accepting `--ticker` and `--dry-run` flags; check kill switch first, fetch account data, call `generate_proposals`, print formatted summary per contracts/cli.md; handle errors (kill switch active, no watchlist, broker unreachable, no API key for LLM)
- [x] T017 [US1] Add unit tests for scoring in tests/unit/test_engine.py — TestSignalScoring class: test `classify_signal_direction` for each signal type, test `recency_weight` at 0/7/14 days, test `compute_signal_score` with known signals, test empty signals returns 0.0. TestIndicatorScoring: test `compute_indicator_score` for bullish/bearish/neutral cases, test `compute_momentum_score` with known bars. TestLimitPrice: test `compute_atr` against hand-calculated values, test `compute_limit_price` for buy/sell at various confidence levels, verify floor/cap.
- [x] T018 [US1] Add unit tests for proposal generation in tests/unit/test_engine.py — TestProposalGeneration class: test `should_generate_proposal` with threshold edge cases, test `compute_position_size`, test `generate_proposals` with mocked trading client + mocked signals/indicators in DB, verify proposal saved with correct scores and cited sources, test dry run does not write to DB, test LLM graceful degradation (no API key → base score only)
- [x] T019 [US1] Add integration test for proposal generation in tests/integration/test_engine.py — test fetching real account data from Alpaca, verify account summary returns valid equity/positions/orders (skip if no API keys)

**Checkpoint**: User Story 1 is fully functional — `engine generate` works end-to-end

---

## Phase 4: User Story 4 — Kill Switch (Priority: P1)

**Goal**: Operator can activate/deactivate a kill switch that halts all proposal generation and approval. Persists across restarts.

**Independent Test**: Activate kill switch, attempt to generate proposals, verify blocked. Deactivate, verify operations resume.

### Implementation for User Story 4

- [x] T020 [US4] Implement `engine killswitch` CLI subcommand in src/finance_agent/cli.py — add `killswitch` subcommand accepting positional `on`/`off` argument; call `set_kill_switch` from state.py, print confirmation per contracts/cli.md, handle already-in-requested-state case
- [x] T021 [US4] Wire kill switch check into `engine generate` — at the top of the generate handler (T016), call `get_kill_switch(conn)` and abort with clear message if active
- [x] T022 [P] [US4] Add unit tests for kill switch in tests/unit/test_engine.py — TestKillSwitch class: test `get_kill_switch` returns False by default, test `set_kill_switch` toggles state and updates timestamp, test `set_kill_switch` is idempotent, test generate command aborts when kill switch active
- [x] T023 [US4] Add integration test for kill switch in tests/integration/test_engine.py — test toggling kill switch on/off with real DB, verify state persists across new connection

**Checkpoint**: User Stories 1 AND 4 both work — kill switch blocks proposal generation

---

## Phase 5: User Story 3 — Enforce Risk Controls (Priority: P2)

**Goal**: System enforces configurable risk controls on every proposal. Operator can view and update settings via CLI.

**Independent Test**: Configure risk limits, generate proposals that would violate them, verify proposals are rejected with specific failed rules.

### Implementation for User Story 3

- [x] T024 [US3] Implement risk check engine in src/finance_agent/engine/risk.py — functions: `check_position_size(proposal, account, risk_settings)` checking both dollar amount and portfolio percentage; `check_daily_loss(account, risk_settings)` checking current P&L against limit; `check_trade_count(daily_order_count, risk_settings)` checking against max; `check_concentration(proposal, positions, risk_settings)` checking existing positions in same symbol. Each returns a RiskCheckResult dict (rule_name, passed, limit_value, actual_value, details).
- [x] T025 [US3] Implement risk check orchestrator in src/finance_agent/engine/risk.py — function: `run_all_risk_checks(proposal, account, positions, daily_orders, risk_settings)` running all 4 checks, saving results to risk_check_result table, setting proposal.risk_passed = 0 and proposal.status = 'rejected' if any check fails. Returns list of RiskCheckResult dicts. Function `adjust_position_for_risk(proposal, account, risk_settings)` that reduces quantity to fit within position size limit rather than rejecting outright.
- [x] T026 [US3] Wire risk checks into proposal generation (T014) — after computing position size and before saving, call `run_all_risk_checks`; if any fail and position cannot be adjusted, set status to 'rejected' with decision_reason listing all failed rules
- [x] T027 [US3] Implement `engine risk` CLI subcommand in src/finance_agent/cli.py — add `risk` subcommand with no args to display current settings and today's usage; add `risk set <key> <value>` subcommand with validation per contracts/cli.md (max_position_pct 0.01-0.50, max_daily_loss_pct 0.01-0.20, max_trades_per_day 1-100, max_positions_per_symbol 1-10, min_confidence_threshold 0.1-0.9)
- [x] T028 [P] [US3] Add unit tests for risk checks in tests/unit/test_engine.py — TestRiskChecks class: test each check function individually (position_size pass/fail, daily_loss pass/fail, trade_count pass/fail, concentration pass/fail); test `run_all_risk_checks` with multiple failures reports all; test `adjust_position_for_risk` reduces quantity correctly; test risk settings validation (rejects invalid values)
- [x] T029 [US3] Add unit tests for risk settings management in tests/unit/test_engine.py — TestRiskSettings class: test `get_risk_settings` returns defaults, test `update_risk_setting` changes value and logs, test validation rejects out-of-range values

**Checkpoint**: User Stories 1, 3, AND 4 all work — proposals are risk-checked and configurable

---

## Phase 6: User Story 2 — Review and Approve Proposals (Priority: P2)

**Goal**: Operator reviews pending proposals via interactive CLI, can approve/reject each, decisions are audit-logged.

**Independent Test**: Generate proposals, run review command, approve/reject, verify status changes and audit log entries.

### Implementation for User Story 2

- [x] T030 [US2] Implement proposal lifecycle management in src/finance_agent/engine/proposals.py — functions: `get_pending_proposals(conn, ticker=None)` querying pending proposals with lazy expiration check (mark expired if expires_at < now); `approve_proposal(conn, proposal_id, reason=None)` updating status to 'approved' with decided_at timestamp and audit log entry; `reject_proposal(conn, proposal_id, reason=None)` updating status to 'rejected' with decided_at and reason; `format_proposal_detail(proposal)` returning formatted string per contracts/cli.md review format
- [x] T031 [US2] Implement `engine review` CLI subcommand in src/finance_agent/cli.py — add `review` subcommand accepting `--ticker` flag; query pending proposals, display each with full details (direction, size, confidence breakdown, cited sources, risk results), prompt for action [a]pprove/[r]eject/[s]kip with optional reason; check kill switch before allowing approval; handle no pending proposals
- [x] T032 [US2] Wire kill switch check into proposal approval — in the review handler, when operator selects 'approve', check `get_kill_switch(conn)` and refuse with clear message if active; rejection and viewing remain allowed
- [x] T033 [P] [US2] Add unit tests for proposal lifecycle in tests/unit/test_engine.py — TestProposalLifecycle class: test `get_pending_proposals` returns only pending (not expired), test lazy expiration marks old proposals, test `approve_proposal` changes status and creates audit entry, test `reject_proposal` records reason, test approval blocked when kill switch active

**Checkpoint**: User Stories 1, 2, 3, AND 4 all work — full generate/review/approve workflow

---

## Phase 7: User Story 5 — Proposal History and Engine Status (Priority: P3)

**Goal**: Operator can view proposal history with filters and engine status summary.

**Independent Test**: Generate and process proposals, query history with filters, verify results match. View engine status and verify it reflects current state.

### Implementation for User Story 5

- [x] T034 [US5] Implement proposal history queries in src/finance_agent/engine/proposals.py — function: `query_proposal_history(conn, ticker=None, status=None, since=None, limit=20)` returning list of proposal dicts ordered by created_at DESC; function: `get_engine_status(conn, trading_client)` returning dict with kill_switch state, account info, today's trade count vs limit, daily P&L vs loss limit, pending proposal count, today's generation/approval/rejection counts
- [x] T035 [US5] Implement `engine history` CLI subcommand in src/finance_agent/cli.py — add `history` subcommand accepting `--ticker`, `--status`, `--since`, `--limit` flags; print formatted table per contracts/cli.md
- [x] T036 [US5] Implement `engine status` CLI subcommand in src/finance_agent/cli.py — add `status` subcommand with no args; call `get_engine_status`, print formatted summary per contracts/cli.md
- [x] T037 [P] [US5] Add unit tests for history and status in tests/unit/test_engine.py — TestProposalHistory: test query with ticker filter, status filter, since filter, limit; test empty results. TestEngineStatus: test status returns correct counts and kill switch state with pre-populated DB

**Checkpoint**: All 5 user stories work — complete decision engine feature

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Audit logging, health check update, linting, and documentation

- [x] T038 [P] Add proposal lifecycle audit logging — ensure all proposal generation, risk check evaluation, approval/rejection, and kill switch toggle events are logged to the audit_log table via the existing audit module; verify via unit test
- [x] T039 [P] Update `finance-agent health` command to include engine status — add decision engine status check showing kill switch state and migration version 4; update expected health output format
- [x] T040 Run `uv run ruff check src/finance_agent/engine/ tests/unit/test_engine.py tests/integration/test_engine.py` and fix any linting errors
- [x] T041 Run `uv run pytest tests/unit/test_engine.py -v` and verify all unit tests pass
- [x] T042 Update test_db.py migration assertion — update `test_applies_initial_migration` to expect `applied == 4` and `version == 4` to account for the new migration
- [x] T043 Run quickstart.md validation — execute each command from quickstart.md and verify output matches expected format

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T004 complete) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP, must complete first
- **US4 (Phase 4)**: Depends on Foundational — can run in parallel with US1 (separate files: state.py already done in T004, CLI addition is independent)
- **US3 (Phase 5)**: Depends on US1 (needs proposal generation to have something to risk-check)
- **US2 (Phase 6)**: Depends on US1 (needs generated proposals to review); depends on US4 (kill switch must block approval)
- **US5 (Phase 7)**: Depends on US1 + US2 (needs proposals with various statuses for history)
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **User Story 4 (P1)**: Can start after Phase 2 — mostly independent (state.py done in setup), but wires into US1's generate handler
- **User Story 3 (P2)**: Depends on US1 — risk checks evaluate proposals from generate_proposals
- **User Story 2 (P2)**: Depends on US1 + US4 — reviews proposals, kill switch blocks approval
- **User Story 5 (P3)**: Depends on US1 + US2 — needs proposals with various lifecycle statuses

### Within Each User Story

- Core logic (scoring.py/risk.py/proposals.py) before CLI integration
- CLI integration before unit tests (tests verify the full pipeline)
- Unit tests before integration tests

### Parallel Opportunities

- T001, T002, T003, T004 can all run in parallel (different files)
- T005, T006 can run in parallel (different test files)
- T008, T009, T010 can run in parallel (all in scoring.py but independent functions; or write sequentially since same file)
- US1 and US4 can overlap (US4 wires into US1 at the end)
- T022, T028, T033, T037 are unit test tasks that can run in parallel with other test tasks
- T038, T039 can run in parallel (audit vs health check)

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 4)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T007)
3. Complete Phase 3: User Story 1 (T008-T019)
4. Complete Phase 4: User Story 4 (T020-T023)
5. **STOP and VALIDATE**: `uv run finance-agent engine generate --ticker NVDA` works
6. Proposals generated with scores, sources, risk checks. Kill switch blocks generation.

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (generate) + US4 (kill switch) → `engine generate` + `engine killswitch` work → MVP!
3. Add US3 (risk controls) → `engine risk` works, proposals are risk-checked
4. Add US2 (review) → `engine review` works, full approval workflow
5. Add US5 (history/status) → `engine history` + `engine status` show full data
6. Polish → audit logging, health check, linting, final validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All scoring math is pure Python (no numpy/pandas) — consistent with features 002/003
- LLM adjustment is optional — degrades gracefully without ANTHROPIC_API_KEY
- Kill switch and risk settings persist in engine_state table as JSON — no new config env vars needed
- Migration SQL is fully specified in data-model.md — copy verbatim for T002
- Account data comes from Alpaca TradingClient (existing dependency, paper=True by default)
- Proposal expiration is lazy (checked at query time, no background job)
- `git add -f` may be needed for migrations/*.sql if global gitignore blocks *.sql files
