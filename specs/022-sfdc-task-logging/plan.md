# Implementation Plan: Tasks & Activity Logging

**Branch**: `022-sfdc-task-logging` | **Date**: 2026-03-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/022-sfdc-task-logging/spec.md`

## Summary

Add Salesforce-native task management and activity logging to the advisor CLI and MCP tools. Extends the existing sandbox infrastructure (019) with Task CRUD operations: create follow-up tasks, view/filter/complete tasks, log completed activities, and generate outreach queues. All data stored in Salesforce Task objects — no local storage. Builds on existing `add_interaction()` and Task SOQL patterns already in `storage.py`.

## Technical Context

**Language/Version**: Python 3.12+ with type hints
**Primary Dependencies**: simple_salesforce (SFDC API), pydantic (models), fastmcp (MCP tools), anthropic (not needed for this feature)
**Storage**: Salesforce Task standard object (no local SQLite)
**Testing**: pytest with unittest.mock (mocking `sf.Task.create`, `sf.query`, etc.)
**Target Platform**: macOS CLI + Claude Desktop (MCP)
**Project Type**: Single project (extending existing src/finance_agent/)
**Performance Goals**: Task creation < 10 seconds (Salesforce API round-trip)
**Constraints**: Salesforce API rate limits (standard developer sandbox limits), max SOQL query length
**Scale/Scope**: Single-user sandbox with ~50 synthetic contacts and ~200 tasks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Client Data Isolation | PASS | Developer sandbox with synthetic data only. No client PII. |
| II. Research-Driven | N/A | Not a trading feature. |
| III. Advisor Productivity | PASS | Reduces friction for task management. Salesforce-native first — all data in SFDC Task objects. |
| IV. Safety First | N/A | Not a trading feature. |
| V. Security by Design | PASS | SFDC credentials via environment variables. SOQL inputs escaped via `_soql_escape()`. |

All gates pass. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/022-sfdc-task-logging/
├── plan.md              # This file
├── research.md          # Phase 0 output (minimal — no unknowns)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI + MCP contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/finance_agent/
├── sandbox/
│   ├── models.py           # Add TaskCreate, TaskSummary models
│   ├── storage.py          # Extend with task CRUD (already has add_interaction)
│   └── sfdc_tasks.py       # NEW: Task management + outreach queue logic
├── mcp/
│   └── research_server.py  # Add 5 MCP tools (task create/show/complete, log, outreach)
└── cli.py                  # Add sandbox tasks/log/outreach subcommands

tests/unit/
├── test_sfdc_tasks.py      # NEW: Unit tests for sfdc_tasks.py
└── test_sandbox_storage.py # Extend with task-specific test cases (if needed)
```

**Structure Decision**: Follows existing pattern — new `sfdc_tasks.py` module in sandbox/ (like `sfdc_listview.py`, `sfdc_report.py`). Task-specific business logic (fuzzy matching, outreach queue computation, duplicate detection) goes in the new module. Low-level SFDC CRUD stays in `storage.py` where `add_interaction` already lives.

## Key Design Decisions

### 1. New module vs extending storage.py

**Decision**: Create `sfdc_tasks.py` for business logic; extend `storage.py` for raw CRUD.

**Rationale**: `storage.py` handles Contact CRUD and basic Task creation (`add_interaction`). The new feature adds task-specific business logic (fuzzy subject matching, outreach queue computation, duplicate detection, [advisor-agent] tagging) which is better isolated in its own module — same pattern as `sfdc_listview.py` and `sfdc_report.py`.

### 2. Contact name resolution

**Decision**: Reuse `_soql_escape()` from `storage.py` and query with `LIKE '%name%'` on FirstName + LastName.

**Rationale**: Consistent with FR-002. Already proven pattern in `list_clients()`.

### 3. Task completion by subject match

**Decision**: Query open [advisor-agent]-tagged tasks, fuzzy match subject via SOQL `LIKE`, disambiguate if multiple matches.

**Rationale**: Per clarification session — subject-based matching is more natural than typing 18-char Salesforce IDs.

### 4. Outreach queue — all activities count

**Decision**: Query last activity across ALL Task records (not just [advisor-agent]-tagged), using Contact's `LastActivityDate` standard field or Task subquery.

**Rationale**: Per clarification — the goal is finding genuinely uncontacted clients regardless of how the contact was logged.

### 5. Activity logging vs task creation

**Decision**: Activity logging creates a Task with `Status = 'Completed'` and appropriate `TaskSubtype`. Task creation creates with `Status = 'Not Started'`.

**Rationale**: This matches Salesforce's standard model — both are Task objects, differentiated by Status and TaskSubtype.
