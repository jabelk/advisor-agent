# Implementation Plan: Salesforce-Native List Views & Reports

**Branch**: `021-sfdc-native-lists` | **Date**: 2026-03-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/021-sfdc-native-lists/spec.md`

## Summary

Replace local JSON-based saved lists (020) with Salesforce-native List Views and Reports. Translate CompoundFilter definitions into Metadata API ListView filters and Analytics REST API Report filters. Jordan sees his filtered client lists directly in the Salesforce browser UI, learning how these native CRM objects work.

## Technical Context

**Language/Version**: Python 3.12+ with type hints
**Primary Dependencies**: simple_salesforce (existing — sf.mdapi for ListViews, sf.restful for Reports), pydantic (existing — CompoundFilter model), anthropic (existing — NL translation)
**Storage**: Salesforce platform (ListViews via Metadata API, Reports via Analytics REST API) — no local storage for this feature
**Testing**: pytest with MagicMock for Salesforce API calls (existing pattern from 020)
**Target Platform**: CLI (macOS), Salesforce developer sandbox
**Project Type**: Single project (existing structure)
**Performance Goals**: List View/Report creation completes within 10 seconds (SC-001 from spec)
**Constraints**: ListView max 10 filters, no relative date/sort/limit support in ListViews; Report API more expressive
**Scale/Scope**: Single user (Jordan), developer sandbox, ~100 synthetic contacts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Client Data Isolation | PASS | Developer sandbox with synthetic data only. No production Salesforce connection. |
| Research-Driven Decisions | PASS | Research completed (research.md) — Metadata API and Analytics REST API evaluated with alternatives. |
| Advisor Productivity | PASS | Core value: Jordan learns Salesforce List Views and Reports by having the tool create them. |
| Salesforce-Native First | PASS | This feature explicitly replaces local JSON with Salesforce-native objects. Direct alignment with constitution principle. |
| Safety First | N/A | No trading operations involved. |
| Security by Design | PASS | Salesforce credentials via existing env vars (SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN). No new secrets. |

## Project Structure

### Documentation (this feature)

```text
specs/021-sfdc-native-lists/
├── plan.md              # This file
├── research.md          # Phase 0 output — API research findings
├── data-model.md        # Phase 1 output — entity definitions
├── quickstart.md        # Phase 1 output — integration scenarios
└── contracts/           # Phase 1 output — API contracts
    ├── listview-service.md
    └── report-service.md
```

### Source Code (repository root)

```text
src/finance_agent/sandbox/
├── models.py            # CompoundFilter, SavedList (existing — minimal changes)
├── storage.py           # Client CRUD, field mappings (existing — reuse mappings)
├── list_builder.py      # REFACTOR: Replace local JSON with Salesforce ListView/Report CRUD
├── sfdc_listview.py     # NEW: ListView translation + Metadata API operations
└── sfdc_report.py       # NEW: Report translation + Analytics REST API operations

src/finance_agent/
├── cli.py               # UPDATE: sandbox lists/reports/ask commands target Salesforce
└── mcp/research_server.py  # UPDATE: MCP tools use Salesforce-backed operations

tests/unit/
├── test_sfdc_listview.py   # NEW: ListView translation + API mock tests
├── test_sfdc_report.py     # NEW: Report translation + API mock tests
└── test_list_builder.py    # UPDATE: Tests for refactored Salesforce-backed list_builder
```

**Structure Decision**: Existing single-project structure. Two new service modules (`sfdc_listview.py`, `sfdc_report.py`) handle the Salesforce API interactions. The existing `list_builder.py` is refactored to delegate to these services instead of local JSON. This keeps the translation logic (CompoundFilter → Salesforce filters) separate from the CRUD operations.

## Complexity Tracking

No constitution violations to justify. The design uses existing dependencies and follows established patterns.
