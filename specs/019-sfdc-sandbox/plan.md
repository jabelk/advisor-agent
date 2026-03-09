# Implementation Plan: Salesforce Sandbox Learning Playground

**Branch**: `019-sfdc-sandbox` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/019-sfdc-sandbox/spec.md`

## Summary

A Salesforce-connected CRM practice environment with synthetic client data for advisor workflow training. Includes: (1) a seed data generator that pushes 50+ realistic fictional client profiles to a Salesforce Developer Edition org, (2) client list management (CRUD, search, filter) via Salesforce REST API + SOQL, (3) meeting preparation brief generation combining Salesforce client profiles with local SQLite research signals, and (4) segment-targeted market commentary generation. All exposed via CLI and MCP tools. All data is synthetic — stored in a dedicated Salesforce sandbox, never connected to production CRM.

## Technical Context

**Language/Version**: Python 3.12+ with type hints
**Primary Dependencies**: anthropic (Claude API for brief/commentary generation), simple-salesforce (Salesforce REST API), requests (OAuth2 token acquisition), pydantic (models), fastmcp (MCP tools)
**Storage**: Hybrid — Client data in Salesforce (Contact + Task objects via REST API); research signals in local SQLite (WAL mode, unchanged). Meeting briefs and commentary generated on-the-fly (not persisted).
**Authentication**: OAuth2 Client Credentials flow against Salesforce Developer Edition org (see sfdc-setup-guide.md)
**Testing**: pytest (Salesforce mocked via unittest.mock.MagicMock; SQLite real via tmp_path)
**Target Platform**: macOS (primary), Linux
**Project Type**: Single project (existing codebase extension)
**Performance Goals**: Seed generation <60s for 50 clients (includes Salesforce API round-trips); brief generation <15s (single Claude API call); client lookup <3s (Salesforce SOQL query)
**Constraints**: All data must be synthetic; Salesforce org is a dedicated developer sandbox; no production CRM connections; Claude API required for brief/commentary generation
**Scale/Scope**: ~50-200 synthetic clients in Salesforce; 1 new module (sandbox/) with sfdc.py connection helper, modifications to cli.py and research_server.py. No new SQLite migrations.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| I. Client Data Isolation | PASS | All client data is synthetic (@example.com emails). Pushed to a dedicated Salesforce developer sandbox — no production CRM connections. No real PII. |
| II. Research-Driven | PASS | Meeting briefs cite research signals from the pipeline. Commentary references actual market data points. |
| III. Advisor Productivity | PASS | Core purpose: real Salesforce CRM workflow training (SOQL, objects, OAuth, Connected Apps), meeting prep practice, market commentary. |
| IV. Safety First | PASS | No trading functionality. Read-only access to research signals. |
| V. Security by Design | PASS | Salesforce credentials (consumer key/secret) managed via .env (gitignored). Anthropic API key already managed via environment variables. |

All 5 gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/019-sfdc-sandbox/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── sandbox-contracts.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/finance_agent/
├── sandbox/
│   ├── __init__.py
│   ├── sfdc.py             # NEW: Salesforce OAuth2 connection helper + custom field deployment
│   ├── models.py           # NEW: Pydantic models for client profiles
│   ├── storage.py          # NEW: Client CRUD via Salesforce REST API + SOQL
│   ├── seed.py             # NEW: Algorithmic seed data generator → pushes to Salesforce
│   ├── meeting_prep.py     # NEW: Meeting brief generation (Salesforce client data + SQLite signals + Claude API)
│   └── commentary.py       # NEW: Market commentary generation (SQLite signals + Claude API)
├── mcp/
│   └── research_server.py  # MODIFY: Add sandbox MCP tools (Salesforce-backed)
├── cli.py                  # MODIFY: Add sandbox subcommands

tests/
├── unit/
│   ├── test_sandbox_storage.py    # NEW: Client CRUD tests
│   ├── test_sandbox_seed.py       # NEW: Seed generator tests
│   └── test_sandbox_briefs.py     # NEW: Meeting brief + commentary tests
```

**Structure Decision**: Follows existing single-project pattern. New `sandbox/` module mirrors `patterns/` structure (models, storage, domain logic). Seed generation is algorithmic (no API dependency). Brief and commentary generation use Claude API following the same pattern as `research/analyzer.py`.

## Phase Status

| Phase | Artifact | Status |
|-------|----------|--------|
| Phase 0 | research.md | COMPLETE |
| Phase 1 | data-model.md | COMPLETE |
| Phase 1 | contracts/sandbox-contracts.md | COMPLETE |
| Phase 1 | quickstart.md | COMPLETE |
| Phase 1 | Agent context update | COMPLETE |
| Phase 2 | tasks.md | PENDING (`/speckit.tasks`) |

## Constitution Re-Check (Post Phase 1 Design)

| Gate | Status | Notes |
|------|--------|-------|
| I. Client Data Isolation | PASS | All data is synthetic (@example.com emails). Salesforce org is a dedicated developer sandbox — no production CRM connection. |
| II. Research-Driven | PASS | Meeting briefs query SQLite `research_signal` table for market context. Commentary cites specific data points. |
| III. Advisor Productivity | PASS | Real Salesforce API skills: OAuth2, SOQL, Contact/Task objects, custom fields, PermissionSets. CLI + MCP tools for full CRM workflow. |
| IV. Safety First | PASS | No trading, no portfolio modifications. Read-only research signal access from SQLite. |
| V. Security by Design | PASS | SFDC credentials via .env (gitignored). ANTHROPIC_API_KEY via env var. Synthetic data only. |

All 5 gates pass post-design. No violations introduced.
