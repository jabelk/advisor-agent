# Tasks: Project Scaffolding

**Input**: Design documents from `/specs/001-project-scaffolding/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: Included — the plan explicitly defines test files and the constitution mandates quality gates (ruff + pytest).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create the bare project structure, dependencies, and configuration files.

- [x] T001 Initialize pyproject.toml with project metadata, dependencies (alpaca-py>=0.43, httpx), dev dependencies (pytest, pytest-cov, ruff, mypy, python-dotenv), `[project.scripts]` entry point `finance-agent = "finance_agent.cli:main"`, and tool config (ruff, mypy, pytest) per plan.md in pyproject.toml
- [x] T002 [P] Create .python-version with "3.12" and update .gitignore for Python, uv, SQLite (.db), secrets/, .env, __pycache__, .venv
- [x] T003 [P] Create src/finance_agent/__init__.py with `__version__ = "0.1.0"`
- [x] T004 [P] Create architecture layer stub packages with empty __init__.py: src/finance_agent/data/__init__.py, src/finance_agent/research/__init__.py, src/finance_agent/engine/__init__.py, src/finance_agent/execution/__init__.py, src/finance_agent/audit/__init__.py
- [x] T005 [P] Create .env.example documenting all environment variables (ALPACA_PAPER_API_KEY, ALPACA_PAPER_SECRET_KEY, ALPACA_LIVE_API_KEY, ALPACA_LIVE_SECRET_KEY, TRADING_MODE, DB_PATH, LOG_LEVEL) with descriptions and defaults per data-model.md configuration table
- [x] T006 [P] Create README.md with prerequisites (Python 3.12+, uv, Alpaca account), setup instructions (clone, uv sync, configure .env, run health check), test commands, and link to quickstart.md per SC-001

**Checkpoint**: `uv sync` runs successfully; `uv run python -c "import finance_agent; print(finance_agent.__version__)"` prints `0.1.0`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core modules that ALL user stories depend on — config loading, database, audit infrastructure, test fixtures

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Implement Settings dataclass with env var loading (python-dotenv for .env, os.environ override, defaults for optional settings), validation (required non-empty, TRADING_MODE in paper/live, LOG_LEVEL valid, DB_PATH parent writable), and mode detection logic (4 cases from data-model.md) in src/finance_agent/config.py — include validation of API key format and graceful error for invalid/expired credentials at startup
- [x] T008 Implement get_connection(db_path) returning sqlite3.Connection with PRAGMAs (journal_mode=WAL, synchronous=NORMAL, busy_timeout=5000, foreign_keys=ON, cache_size=-64000) and run_migrations(conn, migrations_dir) using PRAGMA user_version in src/finance_agent/db.py per research.md decisions 2-3 — include error handling for corrupted/inaccessible DB files, read-only filesystem detection, and safe concurrent access via busy_timeout
- [x] T009 [P] Create initial migration with audit_log table (STRICT mode), timestamp/event_type/source/payload columns, indexes on timestamp and event_type, and BEFORE UPDATE/DELETE triggers with RAISE(ABORT) in migrations/001_init.sql per data-model.md
- [x] T010 [P] Create migration conventions document (file naming, PRAGMA user_version at end, one transaction per migration) in migrations/README.md
- [x] T011 Implement AuditLogger class with log(event_type, source, payload) method that JSON-serializes payload and inserts into audit_log, and query(start, end, event_type) method returning matching events in chronological order per contracts/cli.md in src/finance_agent/audit/logger.py
- [x] T012 Create test infrastructure: tests/__init__.py, tests/unit/__init__.py, tests/integration/__init__.py, and tests/conftest.py with shared fixtures (tmp_db: temp SQLite with migrations applied, mock_settings: Settings with test values) per plan.md test structure

**Checkpoint**: Config loads from env, DB initializes with audit_log schema, AuditLogger writes and queries events — all verifiable via `uv run python -c "..."`

---

## Phase 3: User Story 1 — Developer Runs Agent First Time (Priority: P1) MVP

**Goal**: A developer can clone the repo, run `uv sync`, set paper API keys in `.env`, and run `finance-agent health` to confirm configuration, database, and broker connectivity.

**Independent Test**: `uv sync && uv run finance-agent health` displays `[PAPER MODE] Finance Agent v0.1.0`, config OK, DB OK, broker OK with account details.

### Implementation for User Story 1

- [x] T013 [US1] Implement CLI main() function with argument parsing for `health` and `version` subcommands (use argparse, no extra dependencies) in src/finance_agent/cli.py
- [x] T014 [US1] Implement `version` command printing "finance-agent {version}" and exiting with code 0 in src/finance_agent/cli.py
- [x] T015 [US1] Implement `health` command: load Settings, validate config, init DB + run migrations, check broker via TradingClient.get_account(), display status per contracts/cli.md output format in src/finance_agent/cli.py — on invalid/expired API keys, display "Broker API: FAIL (authentication error: {detail})" instead of crashing

### Tests for User Story 1

- [x] T016 [P] [US1] Write unit tests for config loading (env vars, .env file, defaults), validation (missing required keys, invalid TRADING_MODE, invalid LOG_LEVEL, invalid API key format), and Settings dataclass in tests/unit/test_config.py
- [x] T017 [P] [US1] Write unit tests for DB connection (PRAGMA verification), migration runner (applies pending, skips applied, PRAGMA user_version updates), and error handling (corrupted DB, read-only path, concurrent access) in tests/unit/test_db.py
- [x] T018 [US1] Write integration test for `finance-agent health` command against paper trading API (requires ALPACA_PAPER_API_KEY and ALPACA_PAPER_SECRET_KEY in env) in tests/integration/test_health.py

**Checkpoint**: `uv run finance-agent health` works end-to-end; `uv run pytest tests/unit/` all pass

---

## Phase 4: User Story 2 — Config Across Environments (Priority: P2)

**Goal**: Switching between paper and live trading requires only environment variable changes — zero code changes. Live mode displays a prominent warning that real money is at risk.

**Independent Test**: Set `TRADING_MODE=live` with live keys and verify health shows `[LIVE MODE]` with risk warning. Unset live keys and verify it defaults to paper mode.

**Dependencies**: Builds on config.py (Phase 2) and cli.py (US1 Phase 3)

### Implementation for User Story 2

- [x] T019 [US2] Add prominent live-mode warning banner ("WARNING: LIVE TRADING MODE — real money at risk") to health command output when TRADING_MODE=live in src/finance_agent/cli.py
- [x] T020 [US2] Write unit tests for all four mode-detection scenarios: paper default, explicit live with warning, dual-key fallback to paper with warning, live mode with missing live keys error in tests/unit/test_config.py

**Checkpoint**: All four mode-detection scenarios from data-model.md pass; health output shows correct mode prefix

---

## Phase 5: User Story 3 — Audit Database (Priority: P2)

**Goal**: The system records structured audit events for every significant startup action. Events are immutable — cannot be updated or deleted through the application layer. Events are queryable by time range.

**Independent Test**: Run health check, then query `audit_log` table to verify startup/config_validated/db_initialized/health_check events exist in chronological order. Attempt UPDATE/DELETE and verify rejection. Query by time range and verify correct filtering.

**Dependencies**: Builds on audit/logger.py (Phase 2) and cli.py (US1 Phase 3)

### Implementation for User Story 3

- [x] T021 [US3] Integrate audit logging into startup sequence: log "startup", "config_validated", "db_initialized", "migrations_applied" (with count), and "health_check" (with results) events per data-model.md state transitions in src/finance_agent/cli.py
- [x] T022 [US3] Write unit tests for AuditLogger: event creation with correct fields, time-range query filtering, event_type query filtering, append-only enforcement (UPDATE raises error, DELETE raises error) in tests/unit/test_audit.py

**Checkpoint**: `finance-agent health` writes audit trail; AuditLogger.query() returns chronological events; UPDATE/DELETE on audit_log raise errors

---

## Phase 6: User Story 4 — Container Isolation (Priority: P3)

**Goal**: The agent can be built and run as a Docker container with secrets injected via Docker Compose secrets (mounted at /run/secrets/), data persisted via volume mount, and deployment automated via GitHub Actions on the Intel NUC.

**Independent Test**: `docker compose up --build` starts container; health check succeeds inside container with paper trading keys.

**Dependencies**: Requires working project (US1 complete minimum)

### Implementation for User Story 4

- [x] T023 [P] [US4] Create multi-stage Dockerfile: builder stage with python:3.12-slim + COPY uv from ghcr.io/astral-sh/uv:latest, two-phase uv sync (deps then project), runtime stage with .venv only, UV_COMPILE_BYTECODE=1, UV_LINK_MODE=copy per research.md decision 5 in Dockerfile
- [x] T024 [P] [US4] Create docker-compose.yml with app service, data/ volume mount for SQLite, secrets config (alpaca_api_key.txt, alpaca_secret_key.txt at /run/secrets/), entrypoint script that reads secret files and exports as env vars (ALPACA_PAPER_API_KEY, ALPACA_PAPER_SECRET_KEY) before launching the app, and health check command in docker-compose.yml
- [x] T025 [US4] Create GitHub Actions workflow: trigger on push to main, runs-on self-hosted (NUC), steps: checkout, write secrets from GH secrets to ./secrets/, docker compose build, docker compose up -d, cleanup secrets in .github/workflows/deploy.yml per research.md decision 6

**Checkpoint**: `docker compose up --build && docker compose exec app finance-agent health` succeeds on NUC

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates, type safety, and end-to-end validation

- [x] T026 [P] Run ruff linting (`uv run ruff check src/ tests/`) and fix any issues
- [x] T027 [P] Run mypy type checking (`uv run mypy src/`) and fix any issues
- [x] T028 [P] Set up pre-commit hooks (ruff check + pytest) via a Makefile target or shell script, per constitution Quality Gates (pre-commit requirements)
- [x] T029 [P] Create CHANGELOG.md with initial v0.1.0 entry documenting project scaffolding per constitution Release Requirements
- [x] T030 Validate quickstart.md end-to-end: fresh clone, uv sync, configure .env, finance-agent health, pytest, ruff, mypy all succeed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion (T001 must complete for package imports)
- **US1 (Phase 3)**: Depends on Phase 2 — this is the MVP
- **US2 (Phase 4)**: Depends on US1 (extends config validation display and cli.py health output)
- **US3 (Phase 5)**: Depends on US1 (integrates audit events into startup sequence in cli.py)
- **US4 (Phase 6)**: Depends on US1 minimum (needs working project to containerize)
- **Polish (Phase 7)**: Depends on all implementation phases
- **US2 and US3** can run in parallel after US1 (different concerns, minimal file overlap)
- **US4** can start once US1 is complete (does not require US2 or US3)

### User Story Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1 MVP)
                                                ├── Phase 4 (US2) ──┐
                                                ├── Phase 5 (US3) ──┼── Phase 7 (Polish)
                                                └── Phase 6 (US4) ──┘
```

### Within Each User Story

- Implementation tasks before test tasks (tests validate the implementation)
- CLI commands: main → version → health (sequential, same file)
- Core functionality before integration with other components
- Story complete and tested before moving to next priority

### Parallel Opportunities

**Phase 1** (5 tasks in parallel after T001):
```
T001 (pyproject.toml)
  ├── T002 (.python-version, .gitignore)
  ├── T003 (__init__.py)
  ├── T004 (layer stubs)
  ├── T005 (.env.example)
  └── T006 (README.md)
```

**Phase 2** (T009, T010 in parallel with sequential chain):
```
T007 (config) → T008 (db) → T011 (audit logger) → T012 (test fixtures)
T009 (001_init.sql) ─┐
T010 (README.md) ────┘ parallel, no dependencies
```

**Phase 3 US1** (unit tests in parallel after implementation):
```
T013 → T014 → T015 (CLI: main → version → health, same file)
  then:
  T016 (test_config.py) ─┐
  T017 (test_db.py) ─────┘ parallel
  T018 (test_health.py) after T015
```

**Phase 6 US4** (Dockerfile and docker-compose in parallel):
```
T023 (Dockerfile) ──────┐
T024 (docker-compose) ──┘ parallel → T025 (deploy workflow)
```

**Phase 7** (4 tasks in parallel, then final validation):
```
T026 (ruff) ────────────┐
T027 (mypy) ────────────┤
T028 (pre-commit hooks) ┤ parallel → T030 (quickstart validation)
T029 (CHANGELOG) ───────┘
```

---

## Parallel Example: User Story 1

```bash
# After Phase 2 foundational is complete:

# Step 1: Implement CLI (sequential - same file)
Task: "T013 - Implement CLI main() in src/finance_agent/cli.py"
Task: "T014 - Implement version command in src/finance_agent/cli.py"
Task: "T015 - Implement health command in src/finance_agent/cli.py"

# Step 2: Write unit tests (parallel - different files)
Task: "T016 - Unit tests for config in tests/unit/test_config.py"
Task: "T017 - Unit tests for db in tests/unit/test_db.py"
# These two can run simultaneously

# Step 3: Integration test (after health command exists)
Task: "T018 - Integration test for health in tests/integration/test_health.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup → `uv sync` works
2. Complete Phase 2: Foundational → config, DB, audit infra ready
3. Complete Phase 3: US1 → `finance-agent health` works end-to-end
4. **STOP and VALIDATE**: Run `uv run pytest` — all tests pass
5. Deploy health check to NUC via `git push` to validate deployment pipeline

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Health check works → Deploy to NUC (MVP!)
3. Add US2 → Paper/live switching tested → Deploy
4. Add US3 → Audit trail active → Deploy
5. Add US4 → Dockerized deployment → Deploy
6. Each story adds capability without breaking previous stories

### Solo Developer Strategy

Since this is a single-developer project:
1. Complete phases sequentially (Phase 1 → 2 → 3 → 4 → 5 → 6 → 7)
2. Use [P] markers within each phase to parallelize via agent sub-tasks
3. Commit after each phase completion
4. Test at each checkpoint before moving forward

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [US*] label maps task to specific user story for traceability
- Each user story is independently completable and testable at its checkpoint
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All file paths reference the project structure defined in plan.md
- Total: 30 tasks across 7 phases
