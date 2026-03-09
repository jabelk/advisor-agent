# Tasks: Tasks & Activity Logging

**Input**: Design documents from `/specs/022-sfdc-task-logging/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested — omitting test-first tasks. Unit tests included in Polish phase.

**Organization**: Tasks grouped by user story (P1–P4) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Shared constants, models, and the new sfdc_tasks module skeleton

- [X] T001 Add TaskCreate and TaskSummary Pydantic models plus ADVISOR_AGENT_TAG constant and ActivityType literal to src/finance_agent/sandbox/models.py
- [X] T002 Create src/finance_agent/sandbox/sfdc_tasks.py with module docstring, imports (simple_salesforce, models, storage._soql_escape), and ADVISOR_AGENT_TAG re-export

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Task CRUD functions in sfdc_tasks.py that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Implement resolve_contact(sf, name) in src/finance_agent/sandbox/sfdc_tasks.py — fuzzy name match via SOQL LIKE on FirstName/LastName, returns list of {id, name} dicts, uses _soql_escape
- [X] T004 Implement create_task(sf, client_id, subject, due_date, priority, description_tag) in src/finance_agent/sandbox/sfdc_tasks.py — creates SFDC Task with [advisor-agent] tag in Description, defaults due_date to today+7, priority to "Normal"

**Checkpoint**: Foundation ready — resolve_contact and create_task are the building blocks for all stories

---

## Phase 3: User Story 1 — Create Follow-Up Tasks (Priority: P1) MVP

**Goal**: Jordan can create a follow-up task for any sandbox client via a single CLI command

**Independent Test**: Run `finance-agent sandbox tasks create --client "Jane Doe" --subject "Review portfolio" --due 2026-03-15` and verify Task appears in Salesforce

### Implementation for User Story 1

- [X] T005 [US1] Add argparse subparser for `sandbox tasks` with sub-subcommand `create` (args: --client, --subject, --due, --priority) in src/finance_agent/cli.py
- [X] T006 [US1] Implement _sandbox_tasks() dispatch and _sandbox_tasks_create() handler in src/finance_agent/cli.py — calls resolve_contact (handle ambiguous/not-found), then create_task, prints confirmation with client name, due date, priority, status

**Checkpoint**: US1 complete — `sandbox tasks create` works end-to-end

---

## Phase 4: User Story 2 — View and Manage Tasks (Priority: P2)

**Goal**: Jordan can list open tasks with filters and mark tasks complete without opening Salesforce UI

**Independent Test**: Create several tasks via US1, then run `sandbox tasks show`, `sandbox tasks show --overdue`, `sandbox tasks complete "Review portfolio"`

### Implementation for User Story 2

- [X] T007 [US2] Implement list_tasks(sf, client_name, overdue_only) in src/finance_agent/sandbox/sfdc_tasks.py — SOQL query for open [advisor-agent]-tagged Tasks with optional WhoId/overdue filters, returns list of task dicts with client name resolved via WhoId
- [X] T008 [US2] Implement complete_task(sf, subject) in src/finance_agent/sandbox/sfdc_tasks.py — fuzzy match subject via SOQL LIKE on open [advisor-agent]-tagged Tasks, return matched task or list of ambiguous matches, update Status to "Completed"
- [X] T009 [US2] Implement get_task_summary(sf) in src/finance_agent/sandbox/sfdc_tasks.py — returns dict with total_open, overdue, due_today, due_this_week counts
- [X] T010 [US2] Add argparse sub-subcommands `show` (args: --overdue, --client, --summary) and `complete` (positional: subject) to sandbox tasks parser in src/finance_agent/cli.py
- [X] T011 [US2] Implement _sandbox_tasks_show() and _sandbox_tasks_complete() handlers in src/finance_agent/cli.py — table output for show (Subject, Client, Due Date, Priority, Status with OVERDUE marker), summary output for --summary, disambiguation for complete

**Checkpoint**: US2 complete — `sandbox tasks show` and `sandbox tasks complete` work end-to-end

---

## Phase 5: User Story 3 — Log Completed Activities (Priority: P3)

**Goal**: Jordan can log calls, meetings, and emails as completed Salesforce Tasks

**Independent Test**: Run `sandbox log --client "Jane Doe" --subject "Discussed retirement" --type call` and verify activity appears in Contact's Salesforce activity timeline

### Implementation for User Story 3

- [X] T012 [US3] Implement log_activity(sf, client_id, subject, activity_type, activity_date) in src/finance_agent/sandbox/sfdc_tasks.py — creates Task with Status="Completed", maps activity_type to TaskSubtype (call→"Call", email→"Email", meeting/other→null), validates date not in future, tags with [advisor-agent]
- [X] T013 [US3] Add argparse subparser for `sandbox log` (args: --client, --subject, --type with choices, --date) in src/finance_agent/cli.py
- [X] T014 [US3] Implement _sandbox_log() handler in src/finance_agent/cli.py — calls resolve_contact, then log_activity, prints confirmation with activity type, client, date

**Checkpoint**: US3 complete — `sandbox log` works end-to-end

---

## Phase 6: User Story 4 — Outreach Queue (Priority: P4)

**Goal**: Jordan can generate a prioritized list of high-value clients not contacted recently, and optionally auto-create follow-up tasks

**Independent Test**: Run `sandbox outreach --days 90 --min-value 250000` to see stale high-value contacts, then `--create-tasks` to auto-create tasks

### Implementation for User Story 4

- [X] T015 [US4] Implement get_outreach_queue(sf, days, min_value) in src/finance_agent/sandbox/sfdc_tasks.py — SOQL query joining Contact with Task subquery to find contacts with last activity older than N days (or no activity), filtered by min Account_Value__c, sorted by account value desc, returns list of dicts with days_since_contact computed
- [X] T016 [US4] Implement create_outreach_tasks(sf, contacts, days) in src/finance_agent/sandbox/sfdc_tasks.py — for each contact, check for existing open [advisor-agent]-tagged Task, skip if found, otherwise create_task with subject "Follow-up: No contact in N days", returns created/skipped counts
- [X] T017 [US4] Add argparse subparser for `sandbox outreach` (args: --days, --min-value, --create-tasks) in src/finance_agent/cli.py
- [X] T018 [US4] Implement _sandbox_outreach() handler in src/finance_agent/cli.py — calls get_outreach_queue, prints table (Name, Account Value, Last Contact, Days Ago), if --create-tasks also calls create_outreach_tasks and prints created/skipped summary

**Checkpoint**: US4 complete — `sandbox outreach` works end-to-end

---

## Phase 7: MCP Tools

**Purpose**: Expose all operations as MCP tools for Claude Desktop

- [X] T019 [P] Add sandbox_create_task MCP tool in src/finance_agent/mcp/research_server.py — params: client_name, subject, due_date, priority; calls resolve_contact + create_task; returns dict per contracts/mcp-tools.md
- [X] T020 [P] Add sandbox_show_tasks MCP tool in src/finance_agent/mcp/research_server.py — params: client_name, overdue_only, include_summary; calls list_tasks + get_task_summary; returns dict per contracts/mcp-tools.md
- [X] T021 [P] Add sandbox_complete_task MCP tool in src/finance_agent/mcp/research_server.py — params: subject; calls complete_task; returns dict per contracts/mcp-tools.md
- [X] T022 [P] Add sandbox_log_activity MCP tool in src/finance_agent/mcp/research_server.py — params: client_name, subject, activity_type, activity_date; calls resolve_contact + log_activity; returns dict per contracts/mcp-tools.md
- [X] T023 [P] Add sandbox_outreach_queue MCP tool in src/finance_agent/mcp/research_server.py — params: days, min_value, create_tasks; calls get_outreach_queue + create_outreach_tasks; returns dict per contracts/mcp-tools.md

**Checkpoint**: All 5 MCP tools registered and returning JSON per contract specs

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Unit tests, cleanup, and validation

- [X] T024 [P] Create unit tests for sfdc_tasks.py in tests/unit/test_sfdc_tasks.py — test resolve_contact (found, not found, ambiguous), create_task (defaults, custom args, tag), list_tasks (filters, empty), complete_task (found, ambiguous, not found, already completed), log_activity (types, future date rejection), get_outreach_queue (filtering, sorting), create_outreach_tasks (dedup)
- [X] T025 [P] Create unit tests for CLI handlers in tests/unit/test_cli_sandbox_tasks.py — test argparse wiring for tasks create/show/complete, log, outreach subcommands
- [X] T026 Run full test suite (pytest) and fix any failures
- [X] T027 Run quickstart.md validation against live Salesforce sandbox

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (models + module skeleton)
- **US1 (Phase 3)**: Depends on Phase 2 (resolve_contact, create_task)
- **US2 (Phase 4)**: Depends on Phase 2 (resolve_contact) — can run parallel with US1 but benefits from US1 being done for test data
- **US3 (Phase 5)**: Depends on Phase 2 (resolve_contact, create_task pattern) — independent of US1/US2
- **US4 (Phase 6)**: Depends on Phase 2 (create_task for --create-tasks) — independent of US1-US3
- **MCP (Phase 7)**: Depends on Phases 3–6 (all business logic functions must exist)
- **Polish (Phase 8)**: Depends on all prior phases

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational — no story dependencies
- **US2 (P2)**: Depends only on Foundational — independent of US1 (but US1 useful for creating test tasks)
- **US3 (P3)**: Depends only on Foundational — fully independent
- **US4 (P4)**: Depends only on Foundational — uses create_task internally but that's from Phase 2

### Parallel Opportunities

- T001 and T002 are sequential (T002 imports from T001)
- T003 and T004 can run in parallel (different functions, no overlap)
- T007, T008, T009 are in the same file but sequential (T008 may reuse T007 patterns)
- T019–T023 are all [P] — different tool registrations in the same file, can be batched
- T024 and T025 are [P] — different test files

---

## Parallel Example: Phase 7 (MCP Tools)

```bash
# All 5 MCP tools can be implemented in parallel (different function registrations):
T019: sandbox_create_task in research_server.py
T020: sandbox_show_tasks in research_server.py
T021: sandbox_complete_task in research_server.py
T022: sandbox_log_activity in research_server.py
T023: sandbox_outreach_queue in research_server.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: User Story 1 (T005–T006)
4. **STOP and VALIDATE**: `sandbox tasks create` works against live sandbox
5. Demo: Jordan can create tasks from CLI

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test → MVP (task creation)
3. Add US2 → Test → Task management (show/complete)
4. Add US3 → Test → Activity logging
5. Add US4 → Test → Outreach automation
6. Add MCP → Test → Claude Desktop integration
7. Polish → Unit tests + live validation

---

## Notes

- All SFDC data operations go through sfdc_tasks.py (business logic) which calls sf.Task.create/sf.query directly
- resolve_contact is the shared building block — used by US1, US3, US4, and all MCP tools
- [advisor-agent] tag in Description field is the namespace — all queries filter by it
- CLI follows existing dispatch pattern: cmd_sandbox → _sandbox_tasks/_sandbox_log/_sandbox_outreach
- MCP tools follow existing sandbox_* naming convention in research_server.py
