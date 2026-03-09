# Tasks: Client List Builder

**Input**: Design documents from `/specs/020-client-list-builder/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/list-builder-contracts.md, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new project structure needed — extends existing sandbox module from 019-sfdc-sandbox

- [X] T001 Verify sandbox module and Salesforce connection work by running `uv run advisor-agent sandbox list` and confirming seed data is present

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: CompoundFilter model and enhanced list_clients() that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Add `CompoundFilter` Pydantic model to `src/finance_agent/sandbox/models.py` per data-model.md: fields min_age, max_age, min_value, max_value, risk_tolerances (list[str]), life_stages (list[str]), not_contacted_days, contacted_after, contacted_before, search, sort_by (Literal["account_value","age","last_name","last_interaction_date"] default "account_value"), sort_dir (Literal["asc","desc"] default "desc"), limit (int default 50). Add validators: min_age <= max_age, min_value <= max_value, contacted_after <= contacted_before, not_contacted_days mutually exclusive with contacted_after/contacted_before. Add `describe()` method returning human-readable filter summary string
- [X] T003 [P] Enhance `list_clients()` in `src/finance_agent/sandbox/storage.py` with new optional parameters per contracts: min_age, max_age, risk_tolerances (list), life_stages (list), not_contacted_days, contacted_after, contacted_before, sort_by, sort_dir. Build SOQL WHERE clauses dynamically: Age__c range, IN clause for multi-value risk/stage (overrides single risk_tolerance/life_stage if both provided), LastActivityDate for recency and absolute date filters per research R2. Support ORDER BY on account_value (Account_Value__c), age (Age__c), last_name (LastName), last_interaction_date (LastActivityDate) with NULLS LAST. Add `age` to _SUMMARY_FIELDS. Add `format_query_results(clients, filters)` helper returning dict with clients, count, requested_limit, filters_applied. Preserve full backward compatibility with existing callers

**Checkpoint**: Foundation ready — compound filtering and custom sorting available for all user stories

---

## Phase 3: User Story 1 — Compound Filters & Custom Sorting (Priority: P1) 🎯 MVP

**Goal**: Build targeted client lists using multiple filters, custom sorting, and configurable limits via CLI

**Independent Test**: Run `sandbox list --max-age 50 --risk growth aggressive --min-value 200000 --sort-by account_value --limit 50` and verify only matching clients returned

### Tests for User Story 1

- [X] T004 [P] [US1] Write unit tests for compound filtering in `tests/unit/test_sandbox_storage.py` (append to existing file): test age range filter (min_age, max_age), test multi-value risk_tolerances IN query, test multi-value life_stages IN query, test not_contacted_days filter (recency), test contacted_after/contacted_before absolute date range filter, test combined compound filter (age + risk + value), test sort_by age ascending, test sort_by last_name, test sort_by last_interaction_date with NULLS LAST, test backward compatibility (existing single risk_tolerance param still works), test format_query_results returns correct structure with filters_applied string. Use MagicMock for Salesforce client, verify SOQL contains expected clauses

### Implementation for User Story 1

- [X] T005 [US1] Enhance `sandbox list` CLI subcommand in `src/finance_agent/cli.py` with new argparse flags: `--min-age N`, `--max-age N`, `--risk RISK [RISK...]` (nargs="+"), `--stage STAGE [STAGE...]` (nargs="+"), `--not-contacted-days N`, `--contacted-after DATE`, `--contacted-before DATE`, `--sort-by {account_value,age,last_name,last_interaction_date}`, `--sort-dir {asc,desc}`. Construct CompoundFilter from args and pass to list_clients(). Display results table with age column added, plus "Filters applied" summary line and "Showing N clients" count. Preserve backward compatibility — existing --risk and --stage single-value usage still works

**Checkpoint**: US1 complete — compound filters, custom sorting, and age-based queries all work via CLI

---

## Phase 4: User Story 2 — Saved Lists (Priority: P2)

**Goal**: Save named filter combinations and re-run them to get fresh Salesforce results each time

**Independent Test**: `sandbox lists save --name "Top 50 Under 50" --max-age 50 --limit 50`, then `sandbox lists run "Top 50 Under 50"` returns matching clients

**Depends on**: Phase 2 (CompoundFilter model and list_clients)

### Tests for User Story 2

- [X] T006 [P] [US2] Write unit tests for saved list CRUD in `tests/unit/test_list_builder.py` (new file): test save_list creates JSON file with correct structure, test save_list rejects duplicate name (case-insensitive), test get_saved_lists returns all lists sorted by name, test get_saved_list by name (case-insensitive lookup), test get_saved_list returns None for missing name, test run_saved_list executes filters against Salesforce mock and updates last_run_at, test run_saved_list raises ValueError for missing list, test update_saved_list changes name/description/filters, test update_saved_list rejects rename to existing name, test delete_saved_list removes entry, test delete_saved_list returns False for missing name, test saved lists persist across separate function calls (read back from JSON). Use tmp_path fixture for JSON file location, MagicMock for Salesforce

### Implementation for User Story 2

- [X] T007 [P] [US2] Add `SavedList` Pydantic model to `src/finance_agent/sandbox/models.py` per data-model.md: name (str), description (str default ""), filters (CompoundFilter), created_at (str, ISO 8601), last_run_at (str or None). Name is unique key (case-insensitive)
- [X] T008 [US2] Implement saved list CRUD in `src/finance_agent/sandbox/list_builder.py` (new file) per contracts: `_get_data_dir() -> Path` (configurable via ADVISOR_AGENT_DATA_DIR env var, default ~/.advisor-agent), `_load_lists(path) -> dict`, `_save_lists(path, data)`, `save_list(name, description, filters, data_dir=None) -> SavedList`, `get_saved_lists(data_dir=None) -> list[SavedList]`, `get_saved_list(name, data_dir=None) -> SavedList | None`, `run_saved_list(sf, name, data_dir=None) -> dict`, `update_saved_list(name, updates, data_dir=None) -> SavedList`, `delete_saved_list(name, data_dir=None) -> bool`. JSON file at `{data_dir}/saved_lists.json` per research R3
- [X] T009 [US2] Add `sandbox lists` CLI subcommand group to `src/finance_agent/cli.py` with subcommands: `save --name NAME [--desc TEXT] [FILTER_FLAGS...]` (constructs CompoundFilter from args, calls save_list), `show` (calls get_saved_lists, displays table with name, description, filter summary, last run date), `run NAME` (calls run_saved_list, displays results table + filter summary), `update NAME [--name NEW] [--desc TEXT] [FILTER_FLAGS...]` (calls update_saved_list), `delete NAME` (calls delete_saved_list with confirmation). FILTER_FLAGS are same as enhanced `sandbox list`

**Checkpoint**: US2 complete — saved lists save, persist, and return fresh Salesforce results when run

---

## Phase 5: User Story 3 — Natural Language List Queries (Priority: P3)

**Goal**: Type advisor queries in plain English and get correctly-filtered results with a "Filters applied" translation display

**Independent Test**: `sandbox ask "top 50 clients under 50"` translates to max_age=50, sort_by=account_value, sort_dir=desc, limit=50 and returns results

**Depends on**: Phase 2 (CompoundFilter and list_clients)

### Tests for User Story 3

- [X] T010 [P] [US3] Write unit tests for NL query translation in `tests/unit/test_list_builder.py` (append to existing file): test translate_nl_query returns QueryInterpretation with correct filters for "top 50 under 50", test translate_nl_query maps "clients not contacted in 3 months" to not_contacted_days=90, test translate_nl_query returns filter_mapping dict with NL phrase → filter entries, test translate_nl_query returns confidence="high" when all phrases mapped, test translate_nl_query returns confidence="low" for ambiguous input with unrecognized list, test execute_nl_query with high confidence executes query and returns results, test execute_nl_query with low confidence and confirmed=False returns interpretation without executing, test execute_nl_query with low confidence and confirmed=True executes query. Mock anthropic client to return predetermined JSON responses

### Implementation for User Story 3

- [X] T011 [P] [US3] Add `QueryInterpretation` Pydantic model to `src/finance_agent/sandbox/models.py` per data-model.md: original_query (str), filters (CompoundFilter), filter_mapping (dict[str,str]), unrecognized (list[str] default []), confidence (Literal["high","medium","low"])
- [X] T012 [US3] Implement NL query translation in `src/finance_agent/sandbox/list_builder.py` per contracts: `translate_nl_query(query, anthropic_client=None) -> QueryInterpretation` — builds system prompt defining CompoundFilter schema, valid enum values, and 5-10 example translations (e.g., "top 50 under 50" → {max_age:50, sort_by:"account_value", limit:50}); sends NL query as user message; calls Claude API (claude-sonnet-4-5-20250929, max_tokens 1024); parses JSON response into QueryInterpretation via Pydantic. Also implement `execute_nl_query(sf, query, anthropic_client=None, confirmed=False) -> dict` per contracts: translates query, skips execution if confidence="low" and not confirmed, otherwise executes list_clients with parsed filters and returns format_query_results + filter_mapping + original_query
- [X] T013 [US3] Add `sandbox ask` CLI subcommand to `src/finance_agent/cli.py`: positional query arg (string), optional `--yes` flag to skip confirmation. Calls execute_nl_query(). If low confidence and not --yes, displays interpretation and filter mapping, asks user to confirm. If confirmed or high/medium confidence, displays results table + "Filters applied" mapping showing each NL phrase → filter used. Handle case where NL service unavailable with helpful error

**Checkpoint**: US3 complete — natural language queries translate to compound filters and display filter mapping

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: MCP tool exposure, integration testing, final validation

- [X] T014 Add 6 new MCP tools to `src/finance_agent/mcp/research_server.py` per contracts: `sandbox_query_clients` (all CompoundFilter params, calls list_clients with compound filters), `sandbox_save_list` (name, description, filter params — calls save_list), `sandbox_show_lists` (no params — calls get_saved_lists), `sandbox_run_list` (name — calls run_saved_list), `sandbox_delete_list` (name — calls delete_saved_list), `sandbox_ask_clients` (query string — calls execute_nl_query with confirmed=True since MCP context is non-interactive). Also update existing `sandbox_list_clients` tool with compound filter params for backward compatibility. Follow existing @mcp.tool() pattern with try/finally
- [X] T015 Update MCP integration test in `tests/integration/test_mcp_integration.py` to include the 6 new sandbox tools in the expected tools set
- [X] T016 Run full test suite (`pytest`) and validate quickstart scenarios from quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verification only
- **Foundational (Phase 2)**: Depends on Phase 1 — CompoundFilter model + enhanced list_clients() BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 (uses compound filters in CLI)
- **US2 (Phase 4)**: Depends on Phase 2 (SavedList wraps CompoundFilter, runs via list_clients). Independent of US1
- **US3 (Phase 5)**: Depends on Phase 2 (NL produces CompoundFilter, executes via list_clients). Independent of US1 and US2
- **Polish (Phase 6)**: Depends on all user stories complete

### Within Each User Story

- Tests written alongside implementation (tests and models can parallelize)
- Models before service logic
- Service logic before CLI integration
- Story complete before moving to next priority

### Parallel Opportunities

- T002 + T003 can run in parallel (models.py and storage.py — CompoundFilter model is used by storage but can be built concurrently since storage just needs the field names)
- T004 + T005 can run in parallel within US1 (tests in test_sandbox_storage.py, CLI in cli.py — different files)
- T006 + T007 can run in parallel within US2 (tests and SavedList model — different files)
- T010 + T011 can run in parallel within US3 (tests and QueryInterpretation model — different files)
- US2 and US3 can theoretically start in parallel after Phase 2 (different files: list_builder.py sections)

---

## Parallel Example: User Story 1

```bash
# Phase 2 completes (T002 + T003) — foundation ready

# Launch tests and CLI in parallel:
Task T004: "Write compound filter tests in tests/unit/test_sandbox_storage.py"
Task T005: "Enhance sandbox list CLI in src/finance_agent/cli.py"

# Both can proceed since tests use mocks and CLI uses list_clients()
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup verification (T001)
2. Complete Phase 2: Foundational (T002-T003)
3. Complete Phase 3: User Story 1 (T004-T005)
4. **STOP and VALIDATE**: `sandbox list --max-age 50 --risk growth aggressive --min-value 200000 --sort-by account_value --limit 50`
5. Demo "Top 50 Under 50" via compound filters

### Incremental Delivery

1. Setup + Foundational → CompoundFilter model and enhanced list_clients() ready
2. Add US1 → Compound filters via CLI (MVP!)
3. Add US2 → Saved named lists → Reusable segments
4. Add US3 → Natural language queries → "Show me my biggest clients under 50"
5. Polish → MCP tools → Claude Desktop integration
6. Each story adds advisor list-building value independently

---

## Notes

- CompoundFilter model is shared across all 3 user stories — it's in Phase 2 (foundational)
- Saved list JSON storage uses tmp_path in tests — no real filesystem side effects
- NL translation tests mock anthropic client — no real API calls in unit tests
- list_clients() enhancement preserves backward compatibility — existing callers unchanged
- MCP tools in Phase 6 mirror CLI functionality — same underlying functions
- `age` field added to _SUMMARY_FIELDS in storage.py (Phase 2) — needed for display in all stories
