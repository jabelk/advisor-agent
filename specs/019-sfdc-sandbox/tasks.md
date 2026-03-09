# Tasks: Salesforce Sandbox Learning Playground

**Input**: Design documents from `/specs/019-sfdc-sandbox/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/sandbox-contracts.md, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create sandbox module structure and database migration

- [X] T001 [P] Create sandbox package with `__init__.py` in `src/finance_agent/sandbox/__init__.py`
- [X] T002 [P] Create migration `migrations/011_sandbox_crm.sql` with `sandbox_client` table (14 columns: id, first_name, last_name, age, occupation, email, phone, account_value, risk_tolerance, investment_goals, life_stage, household_members, notes, created_at, updated_at) and `sandbox_interaction` table (5 columns: id, client_id FK, interaction_date, interaction_type, summary, created_at) per data-model.md. Include CHECK constraints for risk_tolerance IN ('conservative','moderate','growth','aggressive'), life_stage IN ('accumulation','pre-retirement','retirement','legacy'), interaction_type IN ('call','meeting','email','review'), and indexes on risk_tolerance, life_stage, account_value, and client_id

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and storage CRUD that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Create Pydantic models in `src/finance_agent/sandbox/models.py`: `ClientCreate` (input validation for add/edit — fields: first_name, last_name, age 18-100, occupation, email, phone, account_value >=0, risk_tolerance literal, life_stage literal, optional investment_goals, household_members, notes), `ClientSummary` (list view — id, first_name, last_name, account_value, risk_tolerance, life_stage, last_interaction_date), `ClientProfile` (full view — all fields + interactions list). Use Literal types for risk_tolerance and life_stage enums
- [X] T004 [P] Implement client CRUD functions in `src/finance_agent/sandbox/storage.py` per contracts: `add_client(conn, client) -> int`, `get_client(conn, client_id) -> dict|None` (with interactions JOIN), `list_clients(conn, risk_tolerance, life_stage, min_value, max_value, search, limit, offset) -> list[dict]` (sorted by account_value DESC, search across first_name, last_name, notes via LIKE), `update_client(conn, client_id, updates) -> bool` (sets updated_at), `add_interaction(conn, client_id, interaction) -> int`, `client_count(conn) -> int`. Follow existing `patterns/storage.py` pattern: direct SQL with parameter binding, `conn.row_factory = sqlite3.Row`, return dicts

**Checkpoint**: Foundation ready — storage and models available for all user stories

---

## Phase 3: User Story 1 — Seed Data & Client List Management (Priority: P1) 🎯 MVP

**Goal**: Populate sandbox with 50 synthetic clients and provide full CRUD + search/filter via CLI

**Independent Test**: Run `sandbox seed`, then `sandbox list`, `sandbox list --risk growth`, `sandbox view 1`, `sandbox add`, `sandbox edit 1` — all should work end-to-end

### Tests for User Story 1

- [X] T005 [P] [US1] Write unit tests for storage CRUD in `tests/unit/test_sandbox_storage.py`: test add_client returns ID, test get_client with interactions, test get_client not found returns None, test list_clients default sort by account_value DESC, test list_clients filter by risk_tolerance, test list_clients filter by life_stage, test list_clients filter by min/max value, test list_clients search by name, test list_clients search by notes, test update_client changes fields and updated_at, test update_client nonexistent returns False, test add_interaction, test client_count. Use tmp_path fixture with fresh migrated DB (same pattern as test_dashboard.py)
- [X] T006 [P] [US1] Write unit tests for seed generator in `tests/unit/test_sandbox_seed.py`: test seed_clients creates correct count, test seed_clients default 50, test seed_clients with custom count, test seed_clients generates interactions for each client, test account values in $50K-$5M range, test risk_tolerance distribution roughly matches weights (15/35/35/15), test life_stage correlates with age, test seed with fixed random seed produces reproducible output, test reset_sandbox deletes all data, test seed_clients with seed=42 for determinism. Use same DB fixture pattern

### Implementation for User Story 1

- [X] T007 [US1] Implement algorithmic seed data generator in `src/finance_agent/sandbox/seed.py`: `seed_clients(conn, count=50, seed=None) -> int` and `reset_sandbox(conn)`. Include curated name pools (~100 first, ~100 last), occupation pool (~30 weighted toward professional/executive), account_value via `random.lognormvariate(mu=12.2, sigma=1.0)` clipped to 50000-5000000, risk_tolerance weighted (15% conservative, 35% moderate, 35% growth, 15% aggressive), life_stage age-correlated (accumulation 25-45, pre-retirement 46-60, retirement 61-75, legacy 76+), 1-5 interactions per client with realistic date spacing. Generate synthetic emails as `first.last@example.com` and phones as `555-XXX-XXXX`
- [X] T008 [US1] Add `sandbox` subcommand group to `src/finance_agent/cli.py` with subcommands: `seed [--count N] [--reset]` (calls seed_clients/reset_sandbox, handles existing data prompt), `list [--risk] [--stage] [--min-value] [--max-value] [--search]` (formatted table: Name | Account Value | Risk | Life Stage | Last Contact), `view CLIENT_ID` (full profile with all fields + interaction history), `add --first --last --age --occupation --account-value --risk --life-stage [--goals] [--notes]` (validates via Pydantic model, calls add_client), `edit CLIENT_ID [--account-value] [--risk] [--life-stage] [--goals] [--notes]` (calls update_client). Follow existing cli.py pattern for argparse subparsers and handler functions

**Checkpoint**: US1 complete — seed, list, search, view, add, edit all functional via CLI

---

## Phase 4: User Story 2 — Meeting Prep Briefs (Priority: P2)

**Goal**: Generate meeting preparation briefs combining client profile with research signals via Claude API

**Independent Test**: With seed data loaded, run `sandbox brief 1` — should produce structured brief with client summary, market context, and talking points

**Depends on**: US1 (client data must exist)

### Tests for User Story 2

- [X] T009 [P] [US2] Write unit tests for meeting brief generation in `tests/unit/test_sandbox_briefs.py`: test generate_meeting_brief returns expected dict structure (client_id, client_name, generated_at, client_summary, portfolio_context, market_conditions, talking_points list, market_data_available bool), test brief for nonexistent client raises ValueError, test brief with no research signals sets market_data_available=False and includes unavailable note, test brief with mocked research signals includes market context. Mock the anthropic client to return a predetermined response; mock query_signals for signal availability tests

### Implementation for User Story 2

- [X] T010 [US2] Implement meeting brief generation in `src/finance_agent/sandbox/meeting_prep.py`: `generate_meeting_brief(conn, client_id, anthropic_client=None) -> dict`. Steps: (1) fetch client via get_client(), raise ValueError if not found, (2) query research signals via `query_signals()` from `research.signals` filtered by investment_goals keywords, limit 10, (3) build system prompt as meeting prep assistant, (4) build user message with JSON client profile + signals, (5) call Claude API (model claude-sonnet-4-5-20250929, max_tokens 4096) following analyzer.py pattern, (6) parse response into MeetingBrief dict. Graceful degradation: if no signals, still generate with "market data unavailable" note
- [X] T011 [US2] Add `sandbox brief CLIENT_ID` subcommand to `src/finance_agent/cli.py`: parse client_id arg, call generate_meeting_brief(), format and print the brief as readable markdown output. Handle ValueError for missing client with helpful error message suggesting `sandbox list`

**Checkpoint**: US2 complete — meeting briefs generate with client context + market data

---

## Phase 5: User Story 3 — Market Commentary Generator (Priority: P3)

**Goal**: Generate segment-targeted market commentary using research signals via Claude API

**Independent Test**: Run `sandbox commentary --risk growth` — should produce 2-3 paragraphs referencing market data points

**Depends on**: Phase 2 (storage for segment queries). Independent of US1 seed data (works with any clients, or generates general commentary)

### Tests for User Story 3

- [X] T012 [P] [US3] Write unit tests for commentary generation in `tests/unit/test_sandbox_briefs.py` (append to existing file): test generate_commentary returns expected dict structure (segment, segment_criteria, generated_at, commentary, data_points_cited, market_data_available), test commentary with risk_tolerance filter, test commentary with life_stage filter, test commentary with no filters generates general overview, test commentary with no research signals sets market_data_available=False. Mock anthropic client and query_signals

### Implementation for User Story 3

- [X] T013 [US3] Implement market commentary generation in `src/finance_agent/sandbox/commentary.py`: `generate_commentary(conn, risk_tolerance=None, life_stage=None, anthropic_client=None) -> dict`. Steps: (1) define segment from filters (or "all clients" if no filters), (2) query last 20 research signals across all sources via query_signals(), (3) build system prompt as market commentary writer, (4) build user message with segment definition + signals, (5) call Claude API (model claude-sonnet-4-5-20250929, max_tokens 4096), (6) parse response into MarketCommentary dict. Count data_points_cited from signal references in output
- [X] T014 [US3] Add `sandbox commentary [--risk TOLERANCE] [--stage STAGE]` subcommand to `src/finance_agent/cli.py`: parse optional risk_tolerance and life_stage args, call generate_commentary(), print formatted commentary. Handle case where no market data available

**Checkpoint**: US3 complete — market commentary generates for any segment with market data

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: MCP tool exposure, integration testing, final validation

- [X] T015 Add 8 sandbox MCP tools to `src/finance_agent/mcp/research_server.py` per contracts: `sandbox_seed_clients` (write conn), `sandbox_list_clients` (readonly), `sandbox_search_clients` (readonly), `sandbox_get_client` (readonly), `sandbox_add_client` (write conn), `sandbox_edit_client` (write conn), `sandbox_meeting_brief` (readonly + Claude API), `sandbox_market_commentary` (readonly + Claude API). Follow existing `@mcp.tool()` pattern with try/finally conn.close()
- [X] T016 Update MCP integration test in `tests/integration/test_mcp_integration.py` to include the 8 new sandbox tools in the expected tools set
- [X] T017 Run full test suite (`pytest`) and validate all quickstart scenarios from quickstart.md pass end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (migration must exist before storage.py)
- **US1 (Phase 3)**: Depends on Phase 2 (storage.py for seed + CLI CRUD)
- **US2 (Phase 4)**: Depends on Phase 2 (storage.py for get_client). Depends on US1 for meaningful testing (need seed data)
- **US3 (Phase 5)**: Depends on Phase 2 (storage.py for segment queries). Can start after Phase 2 independently of US1/US2
- **Polish (Phase 6)**: Depends on all user stories complete

### Within Each User Story

- Tests written before or alongside implementation
- Models/storage before domain logic (seed, brief, commentary)
- Domain logic before CLI integration
- Story complete before moving to next priority

### Parallel Opportunities

- T001 + T002 can run in parallel (different files)
- T003 + T004 can run in parallel (models.py and storage.py are independent — storage uses plain dicts, models validate at boundaries)
- T005 + T006 + T007 can run in parallel within US1 (tests + seed impl are different files)
- T009 + T012 could theoretically run in parallel (both test files, but T012 appends to T009's file — run sequentially)
- T015 + T016 can run in parallel (different files)

---

## Parallel Example: User Story 1

```bash
# Launch tests and seed implementation in parallel:
Task T005: "Write storage CRUD tests in tests/unit/test_sandbox_storage.py"
Task T006: "Write seed generator tests in tests/unit/test_sandbox_seed.py"
Task T007: "Implement seed generator in src/finance_agent/sandbox/seed.py"

# Then sequential CLI integration:
Task T008: "Add sandbox subcommands to src/finance_agent/cli.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T004)
3. Complete Phase 3: User Story 1 (T005-T008)
4. **STOP and VALIDATE**: Seed 50 clients, list/search/view/add/edit via CLI
5. Demo sandbox CRM practice environment

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Seed + CRUD → CLI sandbox works (MVP!)
3. Add US2 → Meeting briefs → Client meeting prep practice
4. Add US3 → Market commentary → Segment-targeted communications
5. Polish → MCP tools → Claude Desktop integration
6. Each story adds advisor productivity value independently

---

## Notes

- Tests use same DB fixture pattern as existing test_dashboard.py (tmp_path + run_migrations)
- Claude API calls in US2/US3 tests are mocked — no real API calls in unit tests
- seed.py uses Python `random` module only — no external dependencies
- storage.py follows patterns/storage.py pattern: direct SQL, parameter binding, dict returns
- CLI follows existing cli.py argparse pattern for subcommand groups
- MCP tools follow existing @mcp.tool() pattern in research_server.py
