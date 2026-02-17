# Tasks: Finnhub Free-Tier Refactor & EarningsCall Transcript Source

**Input**: Design documents from `/specs/009-finnhub-earningscall-refactor/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/cli.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Add new dependency and configure environment

- [x] T001 Add `earningscall>=1.4` to dependencies in `pyproject.toml` and run `uv sync`
- [x] T002 [P] Add `EARNINGSCALL_API_KEY` entry to `.env.example` with comment explaining optional/demo mode
- [x] T003 [P] Add `earningscall_api_key` field, `earningscall_available` property, and env var loading to `src/finance_agent/config.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Storage and model infrastructure that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Ensure `finnhub_data` source type resolves to `market_data/finnhub/{ticker}/` in `src/finance_agent/data/storage.py` via `_resolve_subdir()`
- [x] T005 [P] Verify `ContentClassification` enum in `src/finance_agent/data/models.py` does not need new entries (new content types are string-based, not enum-constrained)
- [x] T006 [P] Add `market_data` directory to `_DIRECTORY_STRUCTURE` dict in `src/finance_agent/data/storage.py` if not already present

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Finnhub Market Signals via Free Tier (Priority: P1) 🎯 MVP

**Goal**: Ingest structured market signals from 5 Finnhub free-tier endpoints per watchlist company

**Independent Test**: Run `finance-agent research run --source finnhub --ticker AAPL` and verify 5 distinct document types are ingested

### Implementation for User Story 1

- [x] T007 [US1] Implement `FinnhubMarketSource(BaseSource)` class with `name = "finnhub"` in `src/finance_agent/data/sources/finnhub.py` — constructor takes `StorageManager` and `api_key`
- [x] T008 [US1] Implement `_fetch_endpoint()` method for 5 endpoints: `recommendation_trends`, `company_earnings(limit=8)`, `stock_insider_transactions(90d lookback)`, `stock_insider_sentiment(12mo lookback)`, `company_news(30d lookback)` in `src/finance_agent/data/sources/finnhub.py`
- [x] T009 [US1] Implement `ingest()` method that iterates watchlist × endpoints, checks dedup via `check_document_exists()`, calls `_fetch_endpoint()`, formats content, persists raw JSON, and returns `SourceDocumentMeta` list in `src/finance_agent/data/sources/finnhub.py`
- [x] T010 [P] [US1] Implement `_format_analyst_ratings()` formatter producing markdown table with consensus summary in `src/finance_agent/data/sources/finnhub.py`
- [x] T011 [P] [US1] Implement `_format_earnings_history()` formatter producing markdown table with beat/miss track record in `src/finance_agent/data/sources/finnhub.py`
- [x] T012 [P] [US1] Implement `_format_insider_activity()` formatter producing transaction table with buy/sell summary in `src/finance_agent/data/sources/finnhub.py`
- [x] T013 [P] [US1] Implement `_format_insider_sentiment()` formatter producing MSPR table with positive/negative month counts in `src/finance_agent/data/sources/finnhub.py`
- [x] T014 [P] [US1] Implement `_format_company_news()` formatter producing numbered news articles with headlines, sources, and summaries in `src/finance_agent/data/sources/finnhub.py`
- [x] T015 [US1] Register `"finnhub"` source in `_build_sources()` — instantiate `FinnhubMarketSource` when `settings.finnhub_available` is True in `src/finance_agent/research/orchestrator.py`
- [x] T016 [US1] Write unit tests for `FinnhubMarketSource`: test `name` property, all 5 format functions with sample data, dedup skip, and per-endpoint error isolation in `tests/unit/test_sources.py`
- [x] T017 [US1] Write integration test verifying all 5 free-tier endpoints return valid data for AAPL (skip if no `FINNHUB_API_KEY`) in `tests/integration/test_finnhub.py`

**Checkpoint**: `--source finnhub` ingests 5 document types per company

---

## Phase 4: User Story 2 — EarningsCall.biz Transcript Source (Priority: P1)

**Goal**: Ingest earnings call transcripts with speaker attribution via EarningsCall.biz

**Independent Test**: Run `finance-agent research run --source transcripts --ticker AAPL` and verify a transcript is ingested with `content_type=earnings_call`

### Implementation for User Story 2

- [x] T018 [US2] Implement `EarningsCallSource(BaseSource)` class with `name = "transcripts"` in `src/finance_agent/data/sources/earningscall_source.py` — constructor takes `StorageManager` and optional `api_key`
- [x] T019 [US2] Implement `_fetch_transcript()` static method: try `get_transcript(year, quarter, level=2)`, catch `InsufficientApiAccessError` or generic Exception, fall back to `level=1` in `src/finance_agent/data/sources/earningscall_source.py`
- [x] T020 [US2] Implement `_format_transcript()` static method: level=2 produces markdown with speaker sections (`**Name** (Title):`), level=1 produces plain text under heading in `src/finance_agent/data/sources/earningscall_source.py`
- [x] T021 [US2] Implement `ingest()` method: iterate watchlist × recent quarters, check dedup via `check_document_exists()`, call `_fetch_transcript()`, format, persist raw JSON, return `SourceDocumentMeta` list in `src/finance_agent/data/sources/earningscall_source.py`
- [x] T022 [US2] Implement `_recent_quarters()` helper that generates `(year, quarter)` tuples for the most recent N quarters in `src/finance_agent/data/sources/earningscall_source.py`
- [x] T023 [US2] Register `"transcripts"` source in `_build_sources()` — instantiate `EarningsCallSource` with `settings.earningscall_api_key` (works in demo mode if key is empty) in `src/finance_agent/research/orchestrator.py`
- [x] T024 [US2] Write unit tests for `EarningsCallSource`: test `name` property, speaker-attributed format, plain-text fallback, `_recent_quarters()`, dedup skip, level fallback, and transcript ingestion with mock in `tests/unit/test_sources.py`
- [x] T025 [US2] Write integration test: verify `get_company("AAPL")` returns a Company, fetch level=1 transcript, and optionally test level=2 with paid key — skip conditions based on `EARNINGSCALL_API_KEY` in `tests/integration/test_earningscall.py`

**Checkpoint**: `--source transcripts` ingests earnings call transcripts with speaker attribution

---

## Phase 5: User Story 3 — Analysis of New Market Signal Types (Priority: P2)

**Goal**: Provide tailored analysis prompts for each new Finnhub content type

**Independent Test**: After ingesting Finnhub signals, verify each content type produces structured signals with fact-vs-inference classification

### Implementation for User Story 3

- [x] T026 [P] [US3] Add `ANALYST_RATINGS_PROMPT` to `src/finance_agent/research/prompts.py` — extract consensus direction, upgrade/downgrade trends, price target movement
- [x] T027 [P] [US3] Add `EARNINGS_HISTORY_PROMPT` to `src/finance_agent/research/prompts.py` — extract beat/miss patterns, surprise magnitude trends, EPS trajectory
- [x] T028 [P] [US3] Add `INSIDER_ACTIVITY_PROMPT` to `src/finance_agent/research/prompts.py` — extract net buying/selling by role, cluster detection, transaction code signals
- [x] T029 [P] [US3] Add `INSIDER_SENTIMENT_PROMPT` to `src/finance_agent/research/prompts.py` — extract MSPR trends, conviction level, inflection points
- [x] T030 [P] [US3] Add `COMPANY_NEWS_PROMPT` to `src/finance_agent/research/prompts.py` — extract sentiment mix, material events, narrative themes
- [x] T031 [US3] Register all 5 new prompts in `CONTENT_TYPE_PROMPTS` dict in `src/finance_agent/research/prompts.py` — keys: `analyst_ratings`, `earnings_history`, `insider_activity`, `insider_sentiment`, `company_news`

**Checkpoint**: Each new content type has a tailored analysis prompt producing fact-vs-inference classified signals

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: CLI updates, validation, and final checks

- [x] T032 Update `--source` help text in `src/finance_agent/cli.py` to list `finnhub` as a valid source option
- [x] T033 [P] Update `_show_research_status()` source_configs in `src/finance_agent/cli.py` to include `Finnhub Mkt` with `finnhub_data` source type
- [x] T034 [P] Update `SOURCE_MODULES` dict in `src/finance_agent/research/orchestrator.py` to map `"finnhub"` → `"finance_agent.data.sources.finnhub"` and `"transcripts"` → `"finance_agent.data.sources.earningscall_source"`
- [x] T035 Run `uv run ruff check src/ tests/` and fix any lint errors
- [x] T036 Run `uv run mypy src/finance_agent/` and fix any type errors
- [x] T037 Run `uv run pytest tests/unit/ -q` and verify all unit tests pass
- [x] T038 Run quickstart.md verification checklist — confirm end-to-end pipeline works with `--source finnhub --source transcripts --ticker AAPL` (requires API keys — run manually with `set -a && source .env && set +a`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001 must complete for uv sync)
- **US1 (Phase 3)**: Depends on Foundational — Finnhub source implementation
- **US2 (Phase 4)**: Depends on Foundational — EarningsCall source implementation
- **US3 (Phase 5)**: No source dependencies, but analysis prompts are most useful after US1/US2 ingest data
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — No dependencies on other stories
- **US2 (P1)**: Can start after Phase 2 — Independent of US1 (different source module, different tests)
- **US3 (P2)**: Can start after Phase 2 — Independent of US1/US2 (only modifies prompts.py)
- **US1 and US2 can run in parallel** (different source files, different test classes)
- **US3 can run in parallel** with US1/US2 (prompts.py is independent of source modules)

### Within Each User Story

- Source class implementation before orchestrator registration
- Orchestrator registration before integration tests
- Unit tests can be written alongside implementation

### Parallel Opportunities

- T002 and T003 can run in parallel with each other (different files)
- T004, T005, T006 can run in parallel (different concerns)
- T010, T011, T012, T013, T014 can run in parallel (independent format functions)
- T026, T027, T028, T029, T030 can run in parallel (independent prompt constants)
- T032, T033, T034 can run in parallel (different files/sections)
- **US1, US2, and US3 can all run in parallel** after Phase 2

---

## Parallel Example: User Story 1

```bash
# Launch all format functions in parallel (independent, no shared state):
Task: "_format_analyst_ratings() in finnhub.py"
Task: "_format_earnings_history() in finnhub.py"
Task: "_format_insider_activity() in finnhub.py"
Task: "_format_insider_sentiment() in finnhub.py"
Task: "_format_company_news() in finnhub.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T006)
3. Complete Phase 3: User Story 1 — Finnhub Market Signals (T007-T017)
4. **STOP and VALIDATE**: `finance-agent research run --source finnhub --ticker AAPL`
5. Verify 5 documents ingested with correct content types

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Finnhub signals) → Test independently → 5 market signal types working
3. Add US2 (EarningsCall transcripts) → Test independently → Transcript ingestion working
4. Add US3 (Analysis prompts) → Test independently → All content types produce structured signals
5. Polish → Full validation → Ready for commit/PR

### Note on Existing Code

Much of this implementation already exists in the codebase from feature 002-research-ingestion. During implementation, verify each task against the existing code — if the implementation already satisfies the task requirements, validate it matches the spec and mark complete. Focus implementation effort on any gaps or refinements needed.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each phase or logical group
- Stop at any checkpoint to validate story independently
- Existing code from feature 002 should be verified against spec before marking tasks complete
