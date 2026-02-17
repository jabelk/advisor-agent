# Tasks: MCP Integration

**Input**: Design documents from `/specs/010-mcp-integration/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/mcp-tools.md, quickstart.md

**Tests**: Included — unit tests for all 7 tools + integration test for server lifecycle.

**Organization**: Tasks grouped by user story. US1 and US2 are both P1 but US2 depends on the server skeleton from US1. US3 and US4 are P2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Add FastMCP dependency and create the mcp/ package skeleton.

- [x] T001 Add `fastmcp>=2.14,<3` to dependencies in pyproject.toml and add `fastmcp` to mypy overrides ignore list, then run `uv sync`
- [x] T002 Create mcp package directory with `src/finance_agent/mcp/__init__.py` (empty, docstring only)

---

## Phase 2: Foundational (Server Skeleton + Test Fixtures)

**Purpose**: Create the FastMCP server instance, read-only DB helper, and shared test fixtures. MUST complete before any tool implementation.

- [x] T003 Create server skeleton with FastMCP instance, `_get_readonly_conn()` helper (read-only SQLite via `?mode=ro` URI with 5s busy timeout), and `__main__` entry point (stdio default, `--http` flag for HTTP transport) in `src/finance_agent/mcp/research_server.py`
- [x] T004 [P] Extend `tests/conftest.py` with MCP test fixtures: `mcp_db` fixture that creates a populated test database (sample company, source_document, research_signal, safety_state rows, audit_log entries, and an ingestion_run record), and `mcp_db_path` fixture returning its file path as a string

**Checkpoint**: Server skeleton starts in stdio mode (`uv run python -m finance_agent.mcp.research_server`), no tools yet.

---

## Phase 3: User Story 1 — Query Research Signals from Claude Desktop (Priority: P1) MVP

**Goal**: Expose research signals, documents, and watchlist via 3 MCP tools so Claude Desktop can answer conversational questions about research data.

**Independent Test**: `uv run pytest tests/unit/test_mcp_server.py -k "signals or documents or watchlist" -v`

### Implementation for User Story 1

- [x] T005 [US1] Implement `get_signals` tool in `src/finance_agent/mcp/research_server.py` — JOIN research_signal + company + source_document, parameters: ticker (required), limit=20, signal_type="", days=30. Return list[dict] per contracts/mcp-tools.md Tool 1
- [x] T006 [US1] Implement `list_documents` tool in `src/finance_agent/mcp/research_server.py` — JOIN source_document + company, parameters: ticker="", content_type="", limit=20, days=90. Return list[dict] per contracts/mcp-tools.md Tool 2
- [x] T007 [US1] Implement `get_watchlist` tool in `src/finance_agent/mcp/research_server.py` — SELECT from company WHERE active=1, no parameters. Return list[dict] per contracts/mcp-tools.md Tool 4

### Tests for User Story 1

- [x] T008 [US1] Write unit tests for `get_signals`, `list_documents`, and `get_watchlist` in `tests/unit/test_mcp_server.py` — test happy path with populated DB, empty results for unknown ticker, date filtering, signal_type filtering, content_type filtering. Use `mcp_db` fixture.

**Checkpoint**: US1 tools work. `uv run pytest tests/unit/test_mcp_server.py -v` passes for 3 tools.

---

## Phase 4: User Story 2 — Check Safety State Before Trading (Priority: P1)

**Goal**: Expose safety state, audit log, and pipeline status via 3 MCP tools so Claude can check guardrails before any trade.

**Independent Test**: `uv run pytest tests/unit/test_mcp_server.py -k "safety or audit or pipeline" -v`

### Implementation for User Story 2

- [x] T009 [US2] Implement `get_safety_state` tool in `src/finance_agent/mcp/research_server.py` — SELECT from safety_state, parse JSON values for kill_switch and risk_settings. Return dict per contracts/mcp-tools.md Tool 5. Handle missing rows with error message.
- [x] T010 [US2] Implement `get_audit_log` tool in `src/finance_agent/mcp/research_server.py` — SELECT from audit_log with event_type filter and days filter, parameters: event_type="", limit=50, days=7. Parse payload JSON. Return list[dict] per contracts/mcp-tools.md Tool 6
- [x] T011 [US2] Implement `get_pipeline_status` tool in `src/finance_agent/mcp/research_server.py` — SELECT most recent ingestion_run (ORDER BY started_at DESC LIMIT 1), parse errors_json and sources_json. Return dict per contracts/mcp-tools.md Tool 7. Handle no-runs case.

### Tests for User Story 2

- [x] T012 [US2] Write unit tests for `get_safety_state`, `get_audit_log`, and `get_pipeline_status` in `tests/unit/test_mcp_server.py` — test happy path, empty audit log, event_type filter, no pipeline runs, kill switch active state. Use `mcp_db` fixture.

**Checkpoint**: US1 + US2 tools work (6 of 7 tools). All unit tests pass.

---

## Phase 5: User Story 3 — Configure Claude Desktop with All MCP Servers (Priority: P2)

**Goal**: Provide documented example configuration connecting Claude Desktop to all three MCP servers (research DB, Alpaca, SEC EDGAR).

**Independent Test**: Validate the JSON example file is syntactically valid and contains all three server entries.

### Implementation for User Story 3

- [x] T013 [US3] Create `docs/claude-desktop-config.json.example` with all 3 MCP server configs per plan.md: finance-research (uv run, stdio), alpaca (uvx, stdio), sec-edgar (docker, stdio). Include env var placeholders and inline comments as JSON

**Checkpoint**: Config example file exists and is valid JSON with all 3 servers.

---

## Phase 6: User Story 4 — Read Research Documents (Priority: P2)

**Goal**: Expose full document content via MCP tool with 50K char truncation, filesystem access, and graceful missing-file handling.

**Independent Test**: `uv run pytest tests/unit/test_mcp_server.py -k "read_document" -v`

### Implementation for User Story 4

- [x] T014 [US4] Implement `read_document` tool in `src/finance_agent/mcp/research_server.py` — SELECT source_document by ID + JOIN company, read content from filesystem (RESEARCH_DATA_DIR / local_path), truncate at 50K chars (FR-010). Handle: document not found (error string), file missing from disk (metadata only + note), content truncation with message. Return dict per contracts/mcp-tools.md Tool 3

### Tests for User Story 4

- [x] T015 [US4] Write unit tests for `read_document` in `tests/unit/test_mcp_server.py` — test: valid document with content on disk, document not found (invalid ID), file deleted from disk (metadata only), content truncation at 50K chars. Use `mcp_db` fixture + tmp_path for content files.

**Checkpoint**: All 7 tools implemented and unit tested.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration test, CLI extension, linting, type-checking, full validation.

- [x] T016 [P] Write integration test in `tests/integration/test_mcp_integration.py` — test server startup, tools/list response contains all 7 tools, call each tool via FastMCP test client, verify read-only enforcement (attempt write should fail)
- [x] T017 [P] Add `mcp` subcommand to CLI in `src/finance_agent/cli.py` — `finance-agent mcp start` (runs server in stdio mode), `finance-agent mcp start --http` (HTTP mode on 0.0.0.0:8000). Simple wrapper that imports and runs the server.
- [x] T018 Run `uv run ruff check src/ tests/` and fix any linting issues
- [x] T019 Run `uv run mypy src/finance_agent/` and fix any type errors
- [x] T020 Run `uv run pytest tests/ -v` and verify all tests pass (existing + new)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (fastmcp installed)
- **US1 (Phase 3)**: Depends on Phase 2 (server skeleton + fixtures)
- **US2 (Phase 4)**: Depends on Phase 2 (server skeleton + fixtures); independent of US1
- **US3 (Phase 5)**: No code dependencies (docs only); independent of other stories
- **US4 (Phase 6)**: Depends on Phase 2 (server skeleton + fixtures); independent of US1/US2
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Server skeleton → 3 tools → tests. First to implement.
- **US2 (P1)**: Server skeleton → 3 tools → tests. Can run in parallel with US1 (different tools, same file but no conflicts).
- **US3 (P2)**: Docs only. Can start anytime after Phase 1.
- **US4 (P2)**: Server skeleton → 1 tool → tests. Can run in parallel with US1/US2.

### Within Each User Story

- Implementation tasks before test tasks (tests validate the implementation)
- All tools within a story are in the same file but operate on different DB tables

### Parallel Opportunities

- T003 and T004 can run in parallel (different files)
- T005, T006, T007 are sequential within US1 (same file) but US1/US2/US3/US4 phases can overlap
- T013 (US3, docs) can run in parallel with any implementation phase
- T016 and T017 can run in parallel (different files)

---

## Parallel Example: After Phase 2

```bash
# All user stories can start after Phase 2 completes:
# Stream 1: US1 — T005, T006, T007, T008 (signals, documents, watchlist tools)
# Stream 2: US2 — T009, T010, T011, T012 (safety, audit, pipeline tools)
# Stream 3: US3 — T013 (Claude Desktop config docs)
# Stream 4: US4 — T014, T015 (read_document tool)
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (fastmcp dependency)
2. Complete Phase 2: Server skeleton + fixtures
3. Complete Phase 3: US1 — get_signals, list_documents, get_watchlist
4. **STOP and VALIDATE**: Run unit tests, manually test with `uv run python -m finance_agent.mcp.research_server`
5. User can already query research data from Claude Desktop

### Incremental Delivery

1. Setup + Foundational → Server starts, no tools
2. US1 → Query signals/documents/watchlist (MVP!)
3. US2 → Safety checks before trading
4. US3 → Claude Desktop config documentation
5. US4 → Full document content reading
6. Polish → Integration tests, CLI command, lint/type checks

---

## Notes

- All 7 tools live in a single file (`research_server.py`), ~150 LOC total
- No new DB tables — all tools read from existing schema (migrations 001, 002, 006)
- Config uses existing `DB_PATH` and `RESEARCH_DATA_DIR` env vars (already in config.py)
- Tests use populated in-memory SQLite databases via conftest fixtures
- Server entry point: `python -m finance_agent.mcp.research_server` (stdio) or `--http` (HTTP)
