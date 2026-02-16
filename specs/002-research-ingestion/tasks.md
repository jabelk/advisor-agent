# Tasks: Research Data Ingestion & Analysis

**Input**: Design documents from `/specs/002-research-ingestion/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: Included — the constitution mandates quality gates (ruff + pytest), and the spec defines testable acceptance scenarios per user story.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Project Updates)

**Purpose**: Add new dependencies, environment variables, and gitignore entries to the existing project.

- [x] T001 Add new dependencies to pyproject.toml (edgartools>=5.16, finnhub-python>=2.4, anthropic>=0.45, feedparser>=6.0, beautifulsoup4>=4.12, pydantic>=2.0) and run `uv sync` in pyproject.toml
- [x] T002 [P] Update .env.example with new environment variables (ANTHROPIC_API_KEY, FINNHUB_API_KEY, EDGAR_IDENTITY, STRATECHERY_FEED_URL, ASSEMBLYAI_API_KEY, RESEARCH_DATA_DIR) and update .gitignore to add research_data/ directory in .env.example and .gitignore
- [x] T003 [P] Extend Settings dataclass in config.py to load new env vars (ANTHROPIC_API_KEY, FINNHUB_API_KEY, EDGAR_IDENTITY, STRATECHERY_FEED_URL, ASSEMBLYAI_API_KEY, RESEARCH_DATA_DIR with default "research_data/"), add validation for required research keys, and add source-availability detection methods in src/finance_agent/config.py

**Checkpoint**: `uv sync` succeeds with new dependencies; `uv run python -c "import edgartools, finnhub, anthropic, feedparser, bs4, pydantic"` works

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema, core models, storage infrastructure, and CRUD operations that ALL user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Create migration 002_research.sql with 5 tables (company, source_document, research_signal, notable_investor, ingestion_run) in STRICT mode per data-model.md, with all indexes, foreign keys, unique constraints, and `PRAGMA user_version = 2` at end in migrations/002_research.sql
- [x] T005 Create Pydantic models for research signals: SignalType enum, EvidenceType enum (fact/inference), FinancialMetric model, ResearchSignalOutput model, DocumentAnalysis model (with company_ticker, overall_sentiment, signals list, key_takeaways), SourceDocumentMeta model, and ContentClassification enum in src/finance_agent/data/models.py
- [x] T006 [P] Create filesystem storage manager with methods: persist_document(source_type, ticker, content, metadata) → local_path, retrieve_document(local_path) → content, compute_hash(content) → sha256, ensure_directory_structure() that creates research_data/ hierarchy per research.md Decision 6 in src/finance_agent/data/storage.py
- [x] T007 [P] Create source base class with abstract ingest(watchlist, since_date) → list[SourceDocumentMeta] interface, and SourceResult dataclass for tracking per-source stats (documents_ingested, errors) in src/finance_agent/data/sources/__init__.py
- [x] T008 Create watchlist CRUD functions: add_company(conn, ticker, name, cik, sector), remove_company(conn, ticker) (soft delete active=0), list_companies(conn, active_only=True), get_company_by_ticker(conn, ticker), reactivate_company(conn, ticker) in src/finance_agent/data/watchlist.py
- [x] T009 [P] Create notable investor CRUD functions: add_investor(conn, name, cik), remove_investor(conn, name) (soft delete), list_investors(conn, active_only=True) in src/finance_agent/data/investors.py
- [x] T010 Create signal storage and query: save_signals(conn, document_id, company_id, signals), query_signals(conn, company_id, signal_type, since, until, source_type) → list, get_signal_counts(conn, company_id) → dict, check_document_exists(conn, source_type, source_id) → bool in src/finance_agent/research/signals.py
- [x] T011 Create ingestion run tracking: start_run(conn) → run_id, complete_run(conn, run_id, docs_count, signals_count, sources_stats), fail_run(conn, run_id, errors) and document status helpers: set_document_status(conn, doc_id, status, error=None) in src/finance_agent/research/pipeline.py
- [x] T012 Update test fixtures in tests/conftest.py: add research_db fixture (temp SQLite with 001+002 migrations applied), add sample_company fixture (NVDA in watchlist), add mock_anthropic_client fixture

**Checkpoint**: Migration applies cleanly on top of 001; Pydantic models validate; storage manager creates directory structure; watchlist and signal CRUD work against test DB

---

## Phase 3: User Story 1 — SEC Filings & Earnings Transcript Analysis (Priority: P1) MVP

**Goal**: User adds companies to watchlist, runs `finance-agent research --source sec --source transcripts`, and gets AI-analyzed structured signals from SEC filings and earnings transcripts with fact-vs-inference classification.

**Independent Test**: `finance-agent watchlist add NVDA && finance-agent research --source sec && finance-agent signals NVDA` shows analyzed signals.

### Implementation for User Story 1

- [x] T013 [US1] Implement watchlist CLI subcommands: `watchlist add <TICKER>` (resolve name/CIK via edgartools Company(), insert, audit log), `watchlist remove <TICKER>` (soft delete, audit log), `watchlist list` (display with signal counts) per contracts/cli.md in src/finance_agent/cli.py
- [x] T014 [US1] Implement SEC EDGAR source: fetch recent 10-K, 10-Q, 8-K filings for each watchlist company using edgartools Company.get_filings(), export as markdown via filing.markdown(), persist to filesystem via storage manager, detect new filings by checking source_document table, return SourceDocumentMeta list in src/finance_agent/data/sources/sec_edgar.py
- [x] T015 [US1] Implement Finnhub transcript source: list available transcripts via finnhub_client.transcripts_list(symbol), fetch full transcript via finnhub_client.transcripts(id), persist as JSON with speaker/session structure, detect new transcripts by checking source_document table in src/finance_agent/data/sources/finnhub.py
- [x] T016 [US1] Implement section-specific analysis prompts: system prompt with financial analyst role and fact-vs-inference requirement, section prompts for risk_factors (classify types, detect new/changed risks), mda (extract metrics, tone, guidance changes), financial_statements (key metrics with YoY/QoQ), earnings_transcript (separate management vs Q&A, sentiment), and general document prompt in src/finance_agent/research/prompts.py
- [x] T017 [US1] Implement LLM analyzer: create Anthropic client, analyze_document() using messages.parse() with DocumentAnalysis Pydantic model, section-based map-reduce for large 10-Ks (split by filing.obj() sections, analyze each with section prompt, synthesize), prompt caching via cache_control on system prompt, handle API errors with retry in src/finance_agent/research/analyzer.py
- [x] T018 [US1] Implement research pipeline orchestrator: load watchlist, iterate enabled sources, for each source call ingest() → persist documents → analyze with LLM → save_signals(), track ingestion run, audit log all activity, handle per-source errors independently (one source failing doesn't block others), print progress per contracts/cli.md output format in src/finance_agent/research/pipeline.py (extend T011)
- [x] T019 [US1] Implement `research` CLI command with argparse: `research [--source SOURCE] [--ticker TICKER] [--full]` that calls pipeline orchestrator (CLI --source values map to modules: sec→sec_edgar.py, transcripts→finnhub.py, acquired→acquired.py, stratechery→stratechery.py, investors→investor_13f.py), and `research status` that shows last run stats, document counts, per-source status, and failed documents per contracts/cli.md in src/finance_agent/cli.py
- [x] T020 [US1] Implement `signals` CLI command with argparse: `signals <TICKER> [--type TYPE] [--since DATE] [--until DATE] [--source SOURCE]` that queries signals and displays in formatted output with date, signal_type, evidence_type, confidence, summary, and source reference per contracts/cli.md in src/finance_agent/cli.py

### Tests for User Story 1

- [x] T021 [P] [US1] Write unit tests for watchlist CRUD: add company, remove (soft delete), list active only, reactivate, duplicate handling, and watchlist CLI output format in tests/unit/test_watchlist.py
- [x] T022 [P] [US1] Write unit tests for Pydantic models: SignalType enum values, EvidenceType validation, ResearchSignalOutput required fields, DocumentAnalysis structure, FinancialMetric optional fields in tests/unit/test_models.py
- [x] T023 [P] [US1] Write unit tests for SEC EDGAR source (mock edgartools Company/Filing) and Finnhub source (mock finnhub client): verify filing download, markdown export, dedup detection, transcript parsing with speaker/session structure in tests/unit/test_sources.py
- [x] T024 [P] [US1] Write unit tests for LLM analyzer (mock Anthropic client): verify messages.parse() called with correct Pydantic model, section-based splitting for large docs, prompt caching headers, error retry, fact-vs-inference in output in tests/unit/test_analyzer.py
- [x] T025 [P] [US1] Write unit tests for signal storage: save_signals, query by company/type/date/source, get_signal_counts, document dedup check in tests/unit/test_signals.py
- [x] T026 [US1] Write integration test for SEC EDGAR: real API call to fetch AAPL 10-K metadata (skip if EDGAR_IDENTITY not set), verify filing object returned in tests/integration/test_sec_edgar.py
- [x] T027 [US1] Write integration test for Finnhub: real API call to list AAPL transcripts (skip if FINNHUB_API_KEY not set), verify transcript list returned in tests/integration/test_finnhub.py

**Checkpoint**: `finance-agent watchlist add NVDA && finance-agent research --source sec && finance-agent signals NVDA` works end-to-end; `uv run pytest tests/unit/` all pass

---

## Phase 4: User Story 2 — Acquired Podcast Research Mining (Priority: P2)

**Goal**: System ingests Acquired podcast episodes, classifies by type (deep-dive vs interview), and produces investment-relevant signals linked to companies.

**Independent Test**: `finance-agent research --source acquired && finance-agent signals NVDA --source podcast_episode` shows podcast-derived signals.

**Dependencies**: Requires Phase 2 + Phase 3 US1 (pipeline infrastructure, analyzer, signal storage)

### Implementation for User Story 2

- [x] T028 [US2] Implement Acquired podcast source: on first run, download Kaggle dataset (harrywang/acquired-podcast-transcripts-and-rag-evaluation, CC0 license, 200 episodes) and load historical transcripts into research_data/podcasts/acquired/; parse RSS feed (https://feeds.transistor.fm/acquired) via feedparser for episode metadata (title, date, description, audio URL); for episodes not in Kaggle dataset, transcribe via AssemblyAI API if ASSEMBLYAI_API_KEY set (skip with warning if not); classify episodes by type (deep-dive if title contains company name, interview if "Interview" in title, ACQ2 for season tag); persist transcripts as JSON; detect new episodes by source_document dedup in src/finance_agent/data/sources/acquired.py
- [x] T029 [US2] Add podcast-specific analysis prompts: deep-dive prompt (extract competitive advantages, growth catalysts, risk factors, investment thesis, referenced sources), interview prompt (extract leadership insights, industry perspectives, company mentions), map company names in analysis to watchlist tickers in src/finance_agent/research/prompts.py (extend)
- [x] T030 [US2] Register Acquired source in research pipeline: add "acquired" to source registry, add --source acquired option to CLI, handle graceful skip when no transcription service configured in src/finance_agent/research/pipeline.py and src/finance_agent/cli.py

### Tests for User Story 2

- [x] T031 [P] [US2] Write unit tests for Acquired source: mock RSS feed parsing, episode classification logic (deep-dive vs interview vs ACQ2), transcript retrieval, dedup detection in tests/unit/test_sources.py (extend)

**Checkpoint**: `finance-agent research --source acquired` ingests and analyzes episodes; signals linked to watchlist companies

---

## Phase 5: User Story 3 — Stratechery Analysis Integration (Priority: P2)

**Goal**: System ingests Stratechery articles/updates via authenticated RSS, classifies content, and maps insights to watchlist companies.

**Independent Test**: `finance-agent research --source stratechery && finance-agent signals NVDA --source article` shows Stratechery-derived signals.

**Dependencies**: Requires Phase 2 + Phase 3 US1 (pipeline infrastructure, analyzer, signal storage)

### Implementation for User Story 3

- [x] T032 [US3] Implement Stratechery RSS source: parse authenticated RSS feed (STRATECHERY_FEED_URL) via feedparser with User-Agent header for Cloudflare, extract articles and daily updates, convert HTML content to plain text via beautifulsoup4, classify by type (analysis_article, daily_update, interview), persist as HTML files, handle auth failure gracefully (log warning, skip source) in src/finance_agent/data/sources/stratechery.py
- [x] T033 [US3] Add article-specific analysis prompts: strategic analysis prompt (company direction, competitive positioning, market structure, technology trends), interview prompt (leadership insights), multi-company extraction (identify all companies mentioned, generate separate signal per company) in src/finance_agent/research/prompts.py (extend)
- [x] T034 [US3] Register Stratechery source in research pipeline: add "stratechery" to source registry, add --source stratechery option to CLI, skip if STRATECHERY_FEED_URL not configured in src/finance_agent/research/pipeline.py and src/finance_agent/cli.py

### Tests for User Story 3

- [x] T035 [P] [US3] Write unit tests for Stratechery source: mock RSS feed parsing, HTML-to-text conversion, content classification, auth failure handling, multi-company signal generation in tests/unit/test_sources.py (extend)

**Checkpoint**: `finance-agent research --source stratechery` ingests articles and produces company-mapped signals; graceful skip when credentials missing

---

## Phase 6: User Story 4 — Leadership & Investor Intelligence (Priority: P3)

**Goal**: System detects leadership changes from 8-K filings and tracks notable investor positions via 13F holdings disclosures.

**Independent Test**: `finance-agent investors add "Berkshire Hathaway" 0001067983 && finance-agent research --source investors && finance-agent signals NVDA --type investor_activity` shows position change signals.

**Dependencies**: Requires US1 (SEC filing ingestion for 8-K leadership detection, edgartools for 13F)

### Implementation for User Story 4

- [x] T036 [US4] Add leadership change detection to 8-K analysis: extend 8-K analysis prompt to detect executive appointments/departures (CEO, CTO, CFO, key product leaders), generate leadership_change signal type with executive name, role, and appointment/departure classification in src/finance_agent/research/prompts.py (extend) and src/finance_agent/research/analyzer.py (extend)
- [x] T037 [US4] Implement 13F investor source: fetch 13F-HR filings for tracked notable investors via edgartools Company.get_filings(form="13F-HR"), extract holdings via filing.obj().holdings DataFrame, compare to previous quarter via compare_holdings(), generate investor_activity signals for significant changes (new positions, exits, >25% size changes) in watchlist companies in src/finance_agent/data/sources/investor_13f.py
- [x] T038 [US4] Implement investors CLI subcommands: `investors add <NAME> <CIK>` (insert notable_investor), `investors remove <NAME>` (soft delete), `investors list` (display with last 13F date) per contracts/cli.md in src/finance_agent/cli.py
- [x] T039 [US4] Register 13F investor source in research pipeline: add "investors" to source registry, add --source investors option to CLI in src/finance_agent/research/pipeline.py and src/finance_agent/cli.py

### Tests for User Story 4

- [x] T040 [P] [US4] Write unit tests for 13F investor source (mock edgartools 13F), leadership change detection (mock 8-K content), investor CRUD in tests/unit/test_sources.py (extend) and tests/unit/test_watchlist.py (extend with investor tests)

**Checkpoint**: Leadership changes detected from 8-K filings; 13F position changes generate investor_activity signals; investor CLI works

---

## Phase 7: User Story 5 — Research Signal History & Cross-Source Comparison (Priority: P3)

**Goal**: Unified company profile aggregating all signals across sources. Query by time range. Research pipeline status dashboard.

**Independent Test**: After ingesting from 2+ sources for NVDA, `finance-agent profile NVDA` shows unified view with signals from all sources.

**Dependencies**: Requires US1 at minimum; more valuable with US2-US4 contributing signals

### Implementation for User Story 5

- [x] T041 [US5] Implement `profile` CLI command: display unified company research profile with overall sentiment (computed from recent signals), latest signals from all sources, signal summary by type, source coverage stats, and data coverage period per contracts/cli.md in src/finance_agent/cli.py
- [x] T042 [US5] Implement `research status` display: show last ingestion run details, total document/signal counts, per-source status (OK/DISABLED/last date), and list failed documents with error messages per contracts/cli.md in src/finance_agent/cli.py (extend T019)
- [x] T043 [US5] Implement cross-source comparison in research/signals.py: aggregate_by_source(conn, company_id) → source breakdown, compare_periods(conn, company_id, period1, period2) → signal diffs, compute_overall_sentiment(conn, company_id) → sentiment summary in src/finance_agent/research/signals.py (extend T010)

### Tests for User Story 5

- [x] T044 [P] [US5] Write unit tests for profile output, cross-source aggregation, period comparison, and overall sentiment computation in tests/unit/test_signals.py (extend)
- [x] T045 [US5] Write integration test for end-to-end research pipeline: add ticker to watchlist, run research, query signals, verify profile output (requires EDGAR_IDENTITY + ANTHROPIC_API_KEY) in tests/integration/test_research_pipeline.py

**Checkpoint**: `finance-agent profile NVDA` shows unified multi-source view; `finance-agent research status` shows pipeline health; period comparison works

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates, container updates, documentation, and end-to-end validation.

- [X] T046 [P] Run ruff linting (`uv run ruff check src/ tests/`) and fix all issues
- [X] T047 [P] Run mypy type checking (`uv run mypy src/`) and fix all issues
- [X] T048 [P] Update Dockerfile to install new dependencies and add research_data/ volume mount point in Dockerfile
- [X] T049 [P] Update docker-compose.yml with new env vars (ANTHROPIC_API_KEY, FINNHUB_API_KEY, EDGAR_IDENTITY, STRATECHERY_FEED_URL), research_data volume mount, and updated secrets in docker-compose.yml
- [X] T050 [P] Update README.md with new CLI commands (watchlist, investors, research, signals, profile), new env vars table, research quickstart instructions, and cron/systemd example for scheduled runs on NUC in README.md
- [X] T051 [P] Update CHANGELOG.md with v0.2.0 entry documenting research ingestion feature in CHANGELOG.md
- [X] T052 Validate quickstart.md end-to-end: verify watchlist add, research run, signals query, and profile display all work per quickstart.md scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001 must complete for imports)
- **US1 (Phase 3)**: Depends on Phase 2 — this is the MVP
- **US2 (Phase 4)**: Depends on US1 (needs pipeline, analyzer, signal storage)
- **US3 (Phase 5)**: Depends on US1 (needs pipeline, analyzer, signal storage)
- **US4 (Phase 6)**: Depends on US1 (needs SEC source for 8-K, edgartools for 13F)
- **US5 (Phase 7)**: Depends on US1 at minimum (needs signals to display)
- **Polish (Phase 8)**: Depends on all implementation phases
- **US2 and US3** can run in parallel after US1 (different source modules, no file overlap)
- **US4** can start once US1 is complete (extends analyzer + adds 13F source)

### User Story Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1 MVP)
                                                ├── Phase 4 (US2) ──┐
                                                ├── Phase 5 (US3) ──┼── Phase 7 (US5) → Phase 8 (Polish)
                                                └── Phase 6 (US4) ──┘
```

### Within Each User Story

- Implementation tasks before test tasks (tests validate the implementation)
- Models/CRUD before source modules (sources depend on storage layer)
- Source modules before analyzer integration (analyzer processes source output)
- Pipeline before CLI (CLI calls pipeline)
- Core functionality before integration with other components

### Parallel Opportunities

**Phase 1** (2 tasks in parallel after T001):
```
T001 (pyproject.toml + uv sync)
  ├── T002 (.env.example, .gitignore)
  └── T003 (config.py)
```

**Phase 2** (3 parallel groups):
```
T004 (migration) → T005 (models) → T008 (watchlist CRUD) → T010 (signals CRUD) → T011 (pipeline) → T012 (fixtures)
T006 (storage manager) ─────────┐ parallel with T004 chain
T007 (source base class) ───────┘
T009 (investor CRUD) ──────────── parallel with T008
```

**Phase 3 US1** (unit tests in parallel after implementation):
```
T013 (watchlist CLI) → T014 (SEC source) → T015 (Finnhub source)
  → T016 (prompts) → T017 (analyzer) → T018 (pipeline) → T019 (research CLI) → T020 (signals CLI)
  then:
  T021 (test_watchlist) ──┐
  T022 (test_models) ─────┤
  T023 (test_sources) ────┤ parallel
  T024 (test_analyzer) ───┤
  T025 (test_signals) ────┘
  T026 (integration SEC) ─┐
  T027 (integration Finn) ┘ after unit tests
```

**Phase 4 + 5** (US2 and US3 in parallel):
```
Phase 4: T028 → T029 → T030 → T031
Phase 5: T032 → T033 → T034 → T035
These two phases can execute in parallel (different source files)
```

**Phase 8** (6 tasks in parallel, then final validation):
```
T046 (ruff) ──────────────┐
T047 (mypy) ──────────────┤
T048 (Dockerfile) ────────┤
T049 (docker-compose) ────┤ parallel → T052 (quickstart validation)
T050 (README) ────────────┤
T051 (CHANGELOG) ─────────┘
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup → `uv sync` works with new deps
2. Complete Phase 2: Foundational → schema, models, storage, CRUD ready
3. Complete Phase 3: US1 → `finance-agent research --source sec` works end-to-end
4. **STOP and VALIDATE**: Run `uv run pytest` — all tests pass
5. Deploy to NUC via `git push` and test research on real filings

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → SEC filings + earnings transcripts analyzed → Deploy to NUC (MVP!)
3. Add US2 → Acquired podcast signals → Deploy
4. Add US3 → Stratechery analysis signals → Deploy
5. Add US4 → Leadership + investor tracking → Deploy
6. Add US5 → Unified profiles + cross-source comparison → Deploy
7. Each story adds research capability without breaking previous stories

### Solo Developer Strategy

Since this is a single-developer project:
1. Complete phases sequentially (Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8)
2. Use [P] markers within each phase to parallelize via agent sub-tasks
3. Commit after each phase completion
4. Test at each checkpoint before moving forward

---

## Notes

- FR-010 (content classification) is distributed across source-specific prompt tasks: T016 (filings), T029 (podcasts), T033 (articles) — each implements type-appropriate analytical focus
- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [US*] label maps task to specific user story for traceability
- Each user story is independently completable and testable at its checkpoint
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All file paths reference the project structure defined in plan.md
- Total: 52 tasks across 8 phases
