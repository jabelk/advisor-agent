# Tasks: Salesforce-Native List Views & Reports

**Input**: Design documents from `/specs/021-sfdc-native-lists/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup & Foundational

**Purpose**: Create new service modules with shared translation logic that all user stories depend on

- [X] T001 Create sfdc_listview.py with _sanitize_developer_name(), translate_filters_to_listview(), and DEFAULT_LISTVIEW_COLUMNS constant in src/finance_agent/sandbox/sfdc_listview.py — translate CompoundFilter fields (min_age, max_age, min_value, max_value, risk_tolerances, life_stages, contacted_after, contacted_before) to ListView filter format per data-model.md translation rules; return (filters_list, warnings_list) tuple; warn and omit not_contacted_days, search, sort_by/sort_dir (non-default), limit (non-default); enforce max 10 filters
- [X] T002 [P] Create sfdc_report.py with translate_filters_to_report(), ensure_report_folder(), and DEFAULT_REPORT_COLUMNS constant in src/finance_agent/sandbox/sfdc_report.py — translate all CompoundFilter fields to Report filter format per data-model.md; handle not_contacted_days via LAST_N_DAYS relative date; warn for sort_by/sort_dir/limit non-defaults; ensure_report_folder() queries for existing "Client Lists" folder or creates one via POST /analytics/report-folders

**Checkpoint**: Translation functions ready — user story implementation can begin

---

## Phase 2: User Story 1 — Create List Views from Compound Filters (Priority: P1) MVP

**Goal**: Jordan runs a compound filter from CLI and saves it as a native Salesforce List View visible in the Contacts tab

**Independent Test**: Run `uv run finance-agent sandbox lists save --name "Top 50 Under 50" --max-age 50 --sort-by account_value --limit 50`, then open the printed Salesforce URL and verify the List View appears in the Contacts tab with AA: prefix and matching filters

### Implementation for User Story 1

- [X] T003 [US1] Implement create_listview() with upsert behavior in src/finance_agent/sandbox/sfdc_listview.py — prefix label with "AA: ", generate DeveloperName as "AA_" + _sanitize_developer_name(name), query existing ListView by DeveloperName (SOQL on ListView sObject), update via sf.mdapi.ListView.update() if exists or create via sf.mdapi.ListView.create() if new, build Salesforce URL as {instance_url}/lightning/o/Contact/list?filterName={id}, return dict with id/name/developer_name/url/warnings/filters_applied
- [X] T004 [US1] Update CLI `sandbox lists save` command to call create_listview() instead of local JSON save_list() in src/finance_agent/cli.py — pass Salesforce connection (sf) and CompoundFilter built from CLI args, print created ListView name/filters/warnings/URL, remove dependency on list_builder.save_list() for the save path

**Checkpoint**: User Story 1 complete — List Views can be created from CLI and opened in Salesforce browser

---

## Phase 3: User Story 2 — Manage Salesforce List Views from CLI (Priority: P2)

**Goal**: Jordan can list all tool-created List Views and delete ones he no longer needs, entirely from the CLI

**Independent Test**: Create two List Views via US1, run `uv run finance-agent sandbox lists show` to see both listed with names/URLs, run `uv run finance-agent sandbox lists delete "name"` on one, verify it disappears from both CLI listing and Salesforce Contacts tab

### Implementation for User Story 2

- [X] T005 [P] [US2] Implement list_listviews() in src/finance_agent/sandbox/sfdc_listview.py — query `SELECT Id, DeveloperName, Name FROM ListView WHERE SobjectType = 'Contact' AND DeveloperName LIKE 'AA_%'`, strip "AA: " prefix from Name for display, build URL for each, return sorted list of dicts
- [X] T006 [P] [US2] Implement delete_listview() in src/finance_agent/sandbox/sfdc_listview.py — find ListView by matching AA_ + _sanitize_developer_name(name) in DeveloperName, delete via sf.mdapi.ListView.delete("Contact.{developer_name}"), case-insensitive matching, return True if deleted / False if not found
- [X] T007 [US2] Update CLI `sandbox lists show` to call list_listviews() and `sandbox lists delete` to call delete_listview() in src/finance_agent/cli.py — show command prints table with Name/Type/URL columns, delete command prints confirmation or "not found" message, remove dependency on list_builder.get_saved_lists() and list_builder.delete_saved_list()

**Checkpoint**: User Stories 1 AND 2 complete — full List View lifecycle (create, list, delete) works from CLI

---

## Phase 4: User Story 3 — Create Reports from Compound Filters (Priority: P3)

**Goal**: Jordan saves compound filter queries as Salesforce Reports in a "Client Lists" folder, visible in the Reports tab

**Independent Test**: Run `uv run finance-agent sandbox reports save --name "Growth Clients Under 40" --risk growth --max-age 40`, then open the printed Salesforce URL and verify the report appears in the Reports tab under "Client Lists" folder with matching data

### Implementation for User Story 3

- [X] T008 [US3] Implement create_report() with upsert behavior in src/finance_agent/sandbox/sfdc_report.py — prefix name with "AA: ", set description to "[advisor-agent] {filters.describe()}", use TABULAR format with ContactList report type, call ensure_report_folder() for folder ID, query existing report by matching AA: name among [advisor-agent]-tagged reports (SOQL), update via PATCH /analytics/reports/{id} or create via POST /analytics/reports, build URL as {instance_url}/lightning/r/Report/{id}/view, return dict with id/name/url/warnings/filters_applied/folder
- [X] T009 [P] [US3] Implement list_reports() in src/finance_agent/sandbox/sfdc_report.py — query `SELECT Id, Name, Description, LastRunDate FROM Report WHERE Description LIKE '%[advisor-agent]%'`, strip "AA: " prefix for display, build URL for each, return sorted list of dicts
- [X] T010 [P] [US3] Implement delete_report() in src/finance_agent/sandbox/sfdc_report.py — find report by matching "AA: {name}" in Name among [advisor-agent]-tagged reports, delete via DELETE /analytics/reports/{id}, case-insensitive, return True/False
- [X] T011 [US3] Add `sandbox reports` subcommand group (save, show, delete) to CLI in src/finance_agent/cli.py — reports save accepts --name and all compound filter flags, reports show prints table with Name/Folder/URL columns, reports delete accepts name argument, all commands use _build_compound_filter() helper and Salesforce connection

**Checkpoint**: User Stories 1, 2, AND 3 complete — both List Views and Reports can be created and managed

---

## Phase 5: User Story 4 — NL Query to List View (Priority: P4)

**Goal**: Jordan can save NL-interpreted filters as a Salesforce List View in one step using --save-as

**Independent Test**: Run `uv run finance-agent sandbox ask "growth clients under 40" --save-as "Young Growth Clients"`, verify a List View is created in Salesforce with the NL-interpreted filters and URL is printed

### Implementation for User Story 4

- [X] T012 [US4] Add --save-as flag to `sandbox ask` command in src/finance_agent/cli.py — when --save-as is provided with a name, call create_listview() with the NL-interpreted CompoundFilter after displaying results; for low-confidence queries, show interpreted filters and require --yes confirmation before creating; print ListView URL alongside query results

**Checkpoint**: All user stories complete — full Salesforce-native list and report workflow operational

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Clean up deprecated code, update MCP tools, add tests

- [X] T013 Remove local JSON persistence code from src/finance_agent/sandbox/list_builder.py — remove _get_data_dir, _lists_path, _load_lists, _save_lists, save_list, get_saved_lists, get_saved_list, update_saved_list, delete_saved_list functions; keep translate_nl_query() and execute_nl_query() (still needed for NL translation); remove run_saved_list() (replaced by Salesforce URLs)
- [X] T014 [P] Update MCP tools in src/finance_agent/mcp/research_server.py — replace sandbox_save_list, sandbox_show_lists, sandbox_run_list, sandbox_delete_list MCP tools with Salesforce-backed versions that call sfdc_listview and sfdc_report functions; add sandbox_save_report, sandbox_show_reports, sandbox_delete_report tools
- [X] T015 [P] Write unit tests for sfdc_listview.py in tests/unit/test_sfdc_listview.py — test _sanitize_developer_name (spaces, special chars, truncation), translate_filters_to_listview (all supported fields, unsupported field warnings, max 10 filter truncation, multi-value CSV), create_listview (create vs update upsert, URL construction), list_listviews (AA_ prefix filtering, name stripping), delete_listview (found/not-found, case-insensitive) using MagicMock for sf/sf.mdapi
- [X] T016 [P] Write unit tests for sfdc_report.py in tests/unit/test_sfdc_report.py — test translate_filters_to_report (all fields including not_contacted_days LAST_N_DAYS, search partial), ensure_report_folder (existing vs create), create_report (create vs update upsert, description tag, URL), list_reports (description tag filtering), delete_report using MagicMock for sf.restful/sf.query
- [X] T017 Update tests/unit/test_list_builder.py — remove tests for deleted local JSON functions (save_list, get_saved_lists, etc.); keep NL translation tests (translate_nl_query, execute_nl_query); update imports

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup & Foundational (Phase 1)**: No dependencies — can start immediately
- **User Story 1 (Phase 2)**: Depends on Phase 1 (translate_filters_to_listview, _sanitize_developer_name)
- **User Story 2 (Phase 3)**: Depends on Phase 1 — can run in parallel with US1 (different functions in same file)
- **User Story 3 (Phase 4)**: Depends on Phase 1 (translate_filters_to_report, ensure_report_folder)
- **User Story 4 (Phase 5)**: Depends on US1 (reuses create_listview)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends on foundational translation — MVP target
- **US2 (P2)**: Independent of US1 implementation (different functions), but logically follows US1
- **US3 (P3)**: Independent of US1/US2 (different module: sfdc_report.py), can run in parallel
- **US4 (P4)**: Depends on US1 create_listview() — must come after US1

### Within Each User Story

- Service functions before CLI integration
- Create/upsert before list/delete
- Core implementation before error handling

### Parallel Opportunities

- T001 and T002 can run in parallel (different files)
- T005 and T006 can run in parallel (different functions, no dependency)
- T009 and T010 can run in parallel (different functions, no dependency)
- T015, T016, and T017 can run in parallel (different test files)
- US1/US2 and US3 can proceed in parallel (different modules: sfdc_listview vs sfdc_report)
- T013 and T014 can run in parallel (different files)

---

## Parallel Example: User Story 2

```bash
# Launch list and delete implementations together:
Task: "Implement list_listviews() in src/finance_agent/sandbox/sfdc_listview.py"
Task: "Implement delete_listview() in src/finance_agent/sandbox/sfdc_listview.py"

# Then CLI integration (depends on both):
Task: "Update CLI sandbox lists show and delete in src/finance_agent/cli.py"
```

## Parallel Example: Polish Phase

```bash
# Launch all test writing in parallel:
Task: "Write unit tests for sfdc_listview.py in tests/unit/test_sfdc_listview.py"
Task: "Write unit tests for sfdc_report.py in tests/unit/test_sfdc_report.py"
Task: "Update tests/unit/test_list_builder.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup & Foundational (T001, T002)
2. Complete Phase 2: User Story 1 — Create List Views (T003, T004)
3. **STOP and VALIDATE**: Create a List View, open URL in Salesforce, verify it works
4. Demo to Jordan if ready

### Incremental Delivery

1. Phase 1 → Translation functions ready
2. Add US1 (Create List Views) → Test → Demo (MVP!)
3. Add US2 (Manage List Views) → Test → Full List View lifecycle
4. Add US3 (Create Reports) → Test → Reports added
5. Add US4 (NL to List View) → Test → Convenience feature
6. Polish → Clean up, tests, MCP tools

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- CLI is registered as `finance-agent` (not `advisor-agent`) in pyproject.toml
- ListView has NO description field — use DeveloperName prefix AA_ for programmatic identification
- Reports DO have description field — use [advisor-agent] tag
- Existing list_builder.py NL translation code (translate_nl_query, execute_nl_query) is kept; only local JSON persistence is removed
- Commit after each task or logical group
