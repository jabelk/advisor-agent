# Tasks: Railway Deployment

**Input**: Design documents from `/specs/023-railway-deploy/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Not explicitly requested — omitting test-first tasks. Validation included in Polish phase.

**Organization**: Tasks grouped by user story (P1–P4) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Railway project creation and shared configuration files

- [x] T001 Create railway.toml with build (dockerfilePath), deploy (healthcheckPath=/health, healthcheckTimeout=60, restartPolicyType=ON_FAILURE, restartPolicyMaxRetries=3) in railway.toml
- [x] T002 Create Railway project via CLI (`railway login && railway init`), set required environment variables via Railway dashboard per data-model.md env var table (MCP_API_TOKEN, SFDC_*, ALPACA_*, ANTHROPIC_API_KEY, EDGAR_IDENTITY, DB_PATH, RESEARCH_DATA_DIR, PORT)
- [x] T003 Attach Railway persistent volumes via dashboard: /app/data (1 GB) and /app/research_data (1 GB)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: MCP server must support HTTP transport with auth and health check before any user story can be validated

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add /health endpoint to src/finance_agent/mcp/research_server.py — a separate HTTP route (not an MCP tool) that returns JSON with status (healthy/degraded/unhealthy), uptime_seconds, integrations dict (salesforce, anthropic, alpaca, finnhub, earningscall — each with required/configured/connected/error), and storage dict (db_exists, db_size_mb, research_dir_exists) per contracts/health-check.md. Return 503 if any required integration is unconfigured.
- [x] T005 Add FastMCP StaticTokenVerifier auth to src/finance_agent/mcp/research_server.py — read MCP_API_TOKEN from env, configure StaticTokenVerifier with that token, pass as `auth=` parameter to FastMCP constructor. Unauthenticated requests to /mcp must be rejected.
- [x] T006 Update the MCP server entry point in src/finance_agent/mcp/research_server.py — read PORT from env (default 8000), use it in mcp.run(transport="http", host="0.0.0.0", port=PORT). Ensure --http flag still works for backwards compatibility.

**Checkpoint**: MCP server runs locally with `--http`, exposes /health and /mcp with Bearer token auth

---

## Phase 3: User Story 1 — Cloud-Hosted MCP Server (Priority: P1) MVP

**Goal**: Deploy MCP server to Railway and connect Claude Desktop over HTTPS

**Independent Test**: `curl https://<app>.railway.app/health` returns healthy; Claude Desktop connects via mcp-remote and invokes `get_signals` tool successfully

### Implementation for User Story 1

- [x] T007 [US1] Update Dockerfile CMD from `["finance-agent", "health"]` to `["python", "-m", "finance_agent.mcp.research_server", "--http"]` in Dockerfile
- [x] T008 [US1] Update docker-entrypoint.sh to export MCP_API_TOKEN from env (add to the env var passthrough list alongside existing ALPACA/ANTHROPIC/FINNHUB vars)
- [x] T009 [US1] Deploy to Railway via `railway up --detach` and verify health check passes: `curl https://<app>.railway.app/health`
- [x] T010 [US1] Update Claude Desktop config at ~/Library/Application Support/Claude/claude_desktop_config.json — replace the `finance-research` SSH entry with mcp-remote bridge: `{"command": "npx", "args": ["mcp-remote", "https://<app>.railway.app/mcp", "--header", "Authorization: Bearer <MCP_API_TOKEN>"]}`
- [x] T011 [US1] Verify Claude Desktop connects and all 20+ MCP tools appear and respond (test get_signals, sandbox_show_tasks)

**Checkpoint**: US1 complete — MCP server live on Railway, Claude Desktop connected over HTTPS

---

## Phase 4: User Story 2 — Persistent Data Across Deploys (Priority: P2)

**Goal**: SQLite database and research data survive container restarts and redeployments

**Independent Test**: Create a Salesforce task via MCP, redeploy with `railway up`, query tasks and verify the task persists

### Implementation for User Story 2

- [x] T012 [US2] Verify Railway volumes are mounted correctly — check that DB_PATH=/app/data/finance_agent.db and RESEARCH_DATA_DIR=/app/research_data point to the mounted volumes by creating test data via MCP tools
- [ ] T013 [US2] Redeploy the service (`railway up --detach`) and verify previously created data persists — query via MCP tools to confirm zero data loss
- [x] T014 [US2] Verify /health storage metrics report correctly with Railway volumes mounted — confirm db_exists=true, db_size_mb > 0, research_dir_exists=true after creating test data (storage metrics already implemented in T004)

**Checkpoint**: US2 complete — data persists across redeploys, health check reports storage status

---

## Phase 5: User Story 3 — Secure Credential Management (Priority: P3)

**Goal**: All secrets configured via Railway env vars, auth rejects unauthenticated requests

**Independent Test**: Invoke sandbox_show_tasks via Claude Desktop (proves Salesforce creds work); curl /mcp without Bearer token and verify rejection

### Implementation for User Story 3

- [x] T015 [US3] Verify Salesforce connectivity from Railway — invoke sandbox_show_tasks MCP tool from Claude Desktop and confirm it returns task data from the Salesforce sandbox
- [x] T016 [US3] Verify auth rejection — send unauthenticated request to https://<app>.railway.app/mcp via curl (no Authorization header) and confirm 401/403 response
- [ ] T017 [US3] Verify health check reports missing credentials correctly — temporarily unset a required env var (e.g., SFDC_CONSUMER_KEY) on Railway, redeploy, and confirm /health returns unhealthy with descriptive error (without exposing the secret value)

**Checkpoint**: US3 complete — credentials work, auth blocks unauthorized access, health reports missing creds

---

## Phase 6: User Story 4 — Automated Deployment Pipeline (Priority: P4)

**Goal**: GitHub Actions CI/CD pipeline that runs tests and deploys to Railway on merge to main

**Independent Test**: Push a minor change to main, verify GitHub Actions runs lint → test → deploy → health check

### Implementation for User Story 4

- [x] T018 [US4] Create .github/workflows/ci.yml with change detection job (dorny/paths-filter — skip if only docs/specs changed), lint job (ruff check + format), test job (pytest), security scan job (trivy filesystem CRITICAL/HIGH), gate job (aggregator), deploy-railway job (npm i -g @railway/cli, railway up --detach --service <name>, health check curl with 3 retries)
- [ ] T019 [US4] Add RAILWAY_TOKEN secret to GitHub repo settings (Settings > Secrets > Actions > New repository secret)
- [ ] T020 [US4] Test the pipeline — push a minor change to main branch, verify all jobs pass and Railway redeploys successfully with post-deploy health check

**Checkpoint**: US4 complete — automated CI/CD deploys on merge to main

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, cleanup, and documentation

- [x] T021 [P] Run full test suite (`uv run pytest`) to ensure no regressions from server changes
- [x] T022 [P] Update MCP integration test expected tool list in tests/integration/test_mcp_integration.py if health endpoint changes tool registration
- [ ] T023 Run quickstart.md validation — execute all 5 scenarios (basic MCP tool, health check, data persistence, auth rejection, CI/CD pipeline)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (railway.toml exists, Railway project created)
- **US1 (Phase 3)**: Depends on Phase 2 (health check + auth + HTTP transport working)
- **US2 (Phase 4)**: Depends on US1 (server deployed to Railway)
- **US3 (Phase 5)**: Depends on US1 (server deployed with env vars)
- **US4 (Phase 6)**: Depends on US1 (Railway project exists and deploys work)
- **Polish (Phase 7)**: Depends on all prior phases

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational — no story dependencies
- **US2 (P2)**: Depends on US1 (needs deployed server to test persistence)
- **US3 (P3)**: Depends on US1 (needs deployed server to test auth/creds)
- **US4 (P4)**: Depends on US1 (needs Railway project for CI/CD target)

### Parallel Opportunities

- T001, T002, T003 are sequential (T002 needs Railway account, T003 needs project)
- T004, T005, T006 can be implemented in parallel (different functions in same file, but no cross-dependencies)
- T007 and T008 can run in parallel (different files)
- T012, T013, T014 can run in parallel (all validation tasks)
- US3 tasks (T015–T017) are all validation — can run in parallel
- T021 and T022 are parallel (different test files)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003) — Railway project + config
2. Complete Phase 2: Foundational (T004–T006) — Health check + auth + HTTP
3. Complete Phase 3: User Story 1 (T007–T011) — Deploy + connect Claude Desktop
4. **STOP and VALIDATE**: MCP tools work from Claude Desktop over HTTPS
5. Demo: Jordan can use all advisor-agent tools from any network

### Incremental Delivery

1. Setup + Foundational → Server ready locally
2. Add US1 → Deploy → MVP (cloud-hosted MCP)
3. Add US2 → Verify persistence → Reliable data
4. Add US3 → Verify security → Production-ready auth
5. Add US4 → CI/CD → Automated deploys
6. Polish → Full validation

---

## Notes

- This is primarily an infrastructure feature — most "implementation" is config files and server entry point changes, not new business logic
- The Foundational phase (health check + auth) is the most code-heavy part
- US2 and US3 are mostly validation tasks — verifying that Railway config is correct
- US4 (CI/CD) is the largest single task (T018) — the GitHub Actions workflow file
- FastMCP's StaticTokenVerifier handles auth with zero external dependencies
- The mcp-remote npm bridge handles Claude Desktop's limitation of only supporting local process spawning
