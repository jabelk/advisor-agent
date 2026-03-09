# Implementation Plan: Client List Builder

**Branch**: `020-client-list-builder` | **Date**: 2026-03-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/020-client-list-builder/spec.md`

## Summary

Enhance the Salesforce sandbox with advanced client segmentation: compound filtering (age, value, risk, stage, interaction date — with multi-value OR within dimensions), custom sort order, configurable limits, saved/named list definitions (persisted locally as JSON), and natural language → structured filter translation via Claude API. Extends existing `list_clients()` in storage.py and adds new CLI subcommands and MCP tools. All queries execute against the live Salesforce Developer Edition org via SOQL.

## Technical Context

**Language/Version**: Python 3.12+ with type hints
**Primary Dependencies**: anthropic (Claude API for NL→filter translation), simple-salesforce (Salesforce SOQL queries), pydantic (filter models + validation), fastmcp (MCP tools)
**Storage**: Salesforce (client data, unchanged from 019); local JSON file (saved list definitions — lightweight, no migration needed)
**Testing**: pytest (Salesforce mocked via MagicMock; NL translation mocked; saved list storage uses tmp_path)
**Target Platform**: macOS (primary), Linux
**Project Type**: Single project (existing codebase extension)
**Performance Goals**: Compound filter queries <5s (single SOQL round-trip); NL translation <10s (includes Claude API call); saved list CRUD <1s (local JSON)
**Constraints**: All data synthetic; extends 019 sandbox; no new Salesforce custom objects or fields
**Scale/Scope**: ~50-200 synthetic clients; <50 saved lists; extends sandbox/ module, cli.py, research_server.py

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| I. Client Data Isolation | PASS | All data is synthetic in Salesforce developer sandbox. Saved lists are local filter definitions — no client PII. |
| II. Research-Driven | PASS | NL queries translate advisor language into structured SOQL — teaches real CRM query skills. |
| III. Advisor Productivity | PASS | Core purpose: list-building skills (segmentation, targeting, outreach planning) — central to advisor CRM workflow. |
| IV. Safety First | PASS | No trading functionality. Read-only Salesforce queries for client segmentation. |
| V. Security by Design | PASS | SFDC credentials via .env (existing). ANTHROPIC_API_KEY via env var (existing). No new secrets. |

All 5 gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/020-client-list-builder/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── list-builder-contracts.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/finance_agent/
├── sandbox/
│   ├── storage.py          # MODIFY: enhance list_clients() with compound filter support
│   ├── models.py           # MODIFY: add CompoundFilter, SavedList pydantic models
│   ├── list_builder.py     # NEW: saved list CRUD + NL query translation
│   └── (existing files unchanged)
├── mcp/
│   └── research_server.py  # MODIFY: add list builder MCP tools
├── cli.py                  # MODIFY: add list builder subcommands

tests/
├── unit/
│   ├── test_sandbox_storage.py    # MODIFY: add compound filter tests
│   ├── test_list_builder.py       # NEW: saved list + NL translation tests
```

**Structure Decision**: Follows existing single-project pattern. New `list_builder.py` in sandbox/ handles saved list persistence and NL translation. Compound filtering is an enhancement to the existing `storage.py` (same module, extended function signature). No new migrations — saved lists use a local JSON file.

## Phase Status

| Phase | Artifact | Status |
|-------|----------|--------|
| Phase 0 | research.md | COMPLETE |
| Phase 1 | data-model.md | COMPLETE |
| Phase 1 | contracts/list-builder-contracts.md | COMPLETE |
| Phase 1 | quickstart.md | COMPLETE |
| Phase 1 | Agent context update | COMPLETE |
| Phase 2 | tasks.md | PENDING (`/speckit.tasks`) |

## Constitution Re-Check (Post Phase 1 Design)

| Gate | Status | Notes |
|------|--------|-------|
| I. Client Data Isolation | PASS | Compound filters query synthetic Salesforce data only. Saved lists store filter criteria, not client data. NL translation sends filter intent to Claude, never client records. |
| II. Research-Driven | PASS | "Filters applied" display teaches SOQL/CRM query mapping. NL→filter translation shows the structured interpretation. |
| III. Advisor Productivity | PASS | Direct CRM segmentation skills: "Top 50 Under 50," re-engagement lists, outreach targeting — all core advisor workflows. |
| IV. Safety First | PASS | No trading. Read-only Salesforce queries. |
| V. Security by Design | PASS | No new credentials. Claude API call sends only filter intent text, never client data. |

All 5 gates pass post-design. No violations introduced.
