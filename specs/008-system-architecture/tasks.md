# Tasks: System Architecture Design

**Input**: Design documents from `/specs/008-system-architecture/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Note**: This is a docs-only feature. No source code changes. The "implementation" is producing, validating, and finalizing architecture documents. Each task verifies a section of plan.md against spec.md acceptance scenarios and functional requirements, then updates project-level artifacts (constitution, CLAUDE.md).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Document Structure Validation)

**Purpose**: Ensure all architecture artifacts are in place and structurally complete

- [x] T001 Verify all required documents exist in specs/008-system-architecture/ (plan.md, spec.md, research.md, data-model.md, quickstart.md, checklists/requirements.md)
- [x] T002 Verify plan.md contains all mandatory sections: Technical Context, Constitution Check, Project Structure, Architecture Blueprint, Component Interaction Map, Build vs Buy, Phased Roadmap, Data Source Expansion, Edge Cases
- [x] T003 [P] Verify research.md contains consolidated findings from all 6 research areas (MCP, n8n/orchestration, agent frameworks, data sources, architecture patterns, FastMCP design) with decisions and rationale in specs/008-system-architecture/research.md

---

## Phase 2: Foundational (Cross-Document Consistency)

**Purpose**: Ensure spec, plan, and research documents are internally consistent — MUST complete before per-story validation

**CRITICAL**: No user story validation can begin until this phase is complete

- [x] T004 Verify all 10 functional requirements (FR-001 through FR-010) from specs/008-system-architecture/spec.md have corresponding sections in specs/008-system-architecture/plan.md — flag any FR without coverage
- [x] T005 [P] Verify all 6 success criteria (SC-001 through SC-006) from specs/008-system-architecture/spec.md are measurably addressed in specs/008-system-architecture/plan.md — flag any SC without evidence
- [x] T006 [P] Verify research.md decisions in specs/008-system-architecture/research.md are reflected in plan.md architecture choices — no contradictions between research conclusions and plan decisions
- [x] T007 Validate plan.md constitution check against .specify/memory/constitution.md — verify all 5 principles are addressed and no MUST statements are violated

**Checkpoint**: All documents are structurally complete and internally consistent

---

## Phase 3: User Story 1 — Architecture Blueprint (Priority: P1) MVP

**Goal**: Validate that the Architecture Blueprint section covers every component with runtime location, responsibility, and no gaps/overlaps (FR-001, FR-006)

**Independent Test**: Every component has a defined runtime location, every communication path has a defined protocol, and every capability is assigned to exactly one component

### Validation for User Story 1

- [x] T008 [US1] Validate Component Catalog table in specs/008-system-architecture/plan.md covers all existing modules (research pipeline, safety module, audit log) — acceptance scenario 1 from spec.md
- [x] T009 [US1] Validate Component Catalog assigns every desired capability (research ingestion, analysis, trading, notifications, scheduling) to exactly one component with build/buy rationale — acceptance scenario 2 from spec.md
- [x] T010 [US1] Validate Runtime Locations diagram in specs/008-system-architecture/plan.md assigns all always-on services to NUC with resource estimates — acceptance scenario 3 from spec.md
- [x] T011 [US1] Verify no capability gaps (unassigned) or overlaps (assigned to multiple components) in Component Catalog — SC-001 validation in specs/008-system-architecture/plan.md

**Checkpoint**: Architecture Blueprint is complete and meets all US1 acceptance scenarios

---

## Phase 4: User Story 2 — Component Interaction Map (Priority: P1)

**Goal**: Validate that the Component Interaction Map traces data flow end-to-end for 3 concrete scenarios with triggers, protocols, and data formats (FR-002, FR-005, FR-007)

**Independent Test**: Each scenario can be traced from trigger to human notification, confirming every handoff is defined

### Validation for User Story 2

- [x] T012 [US2] Validate Scenario 1 (SEC filing drops) traces complete path from RSS detection → ingestion → analysis → notification → human review with trigger mechanism and data format at each step — acceptance scenario 1 from spec.md in specs/008-system-architecture/plan.md
- [x] T013 [US2] Validate Scenario 2 (evening research session) traces complete path from Claude Desktop query → MCP tool call → research DB → synthesized answer — acceptance scenario 2 from spec.md in specs/008-system-architecture/plan.md
- [x] T014 [US2] Validate Scenario 3 (trade execution) traces complete path from human decision → safety check → order placement → confirmation with safety guardrail enforcement defined (FR-007) — acceptance scenario 3 from spec.md in specs/008-system-architecture/plan.md
- [x] T015 [US2] Verify all communication paths in the 3 scenarios have defined protocol, data format, and trigger — SC-002 validation in specs/008-system-architecture/plan.md

**Checkpoint**: Interaction Map is complete and meets all US2 acceptance scenarios

---

## Phase 5: User Story 3 — Build vs. Buy Decisions (Priority: P2)

**Goal**: Validate that every capability has a documented build-vs-buy decision with rationale and alternatives (FR-003, FR-010)

**Independent Test**: Off-the-shelf options are chosen where suitable; custom builds are justified; 60%+ capabilities use off-the-shelf tools

### Validation for User Story 3

- [x] T016 [US3] Validate Build vs Buy table in specs/008-system-architecture/plan.md — each off-the-shelf option preferred unless documented limitation makes it unsuitable — acceptance scenario 1 from spec.md
- [x] T017 [US3] Validate Existing Python Pipeline Verdict table in specs/008-system-architecture/plan.md — every module has a verdict (keep as-is, refactor, replace, remove) with rationale — acceptance scenario 2 from spec.md
- [x] T018 [US3] Verify build-vs-buy score: at least 60% of capabilities use off-the-shelf tools — SC-003 validation in specs/008-system-architecture/plan.md
- [x] T019 [P] [US3] Verify custom code estimate in specs/008-system-architecture/plan.md stays within "less code, more context" constraint — total custom code growth is justified (FR-010)

**Checkpoint**: Build vs Buy section is complete and meets all US3 acceptance scenarios

---

## Phase 6: User Story 4 — Phased Implementation Roadmap (Priority: P2)

**Goal**: Validate that the roadmap has 3+ phases, each independently deliverable within ~2 weeks, building on existing code (FR-008)

**Independent Test**: Each phase has a clear deliverable, definition of done, no hard dependency on later phases, and rough scope estimate

### Validation for User Story 4

- [x] T020 [US4] Validate each phase in specs/008-system-architecture/plan.md delivers a working increment (not a partial skeleton) — acceptance scenario 1 from spec.md
- [x] T021 [US4] Validate no single phase requires more than ~2 weeks of effort — acceptance scenario 2 from spec.md in specs/008-system-architecture/plan.md
- [x] T022 [US4] Validate Phase 1 builds on existing research pipeline rather than replacing it — acceptance scenario 3 from spec.md in specs/008-system-architecture/plan.md
- [x] T023 [US4] Verify roadmap contains at least 3 phases, each independently deliverable — SC-004 validation in specs/008-system-architecture/plan.md

**Checkpoint**: Phased Roadmap is complete and meets all US4 acceptance scenarios

---

## Phase 7: User Story 5 — Data Source Expansion Plan (Priority: P3)

**Goal**: Validate that the expansion plan identifies 5+ new sources with priorities, costs, and at least one autonomous discovery mechanism (FR-009)

**Independent Test**: Each proposed source has data description, integration method, estimated value, and priority ranking

### Validation for User Story 5

- [x] T024 [US5] Validate Data Source Expansion Plan in specs/008-system-architecture/plan.md identifies at least 5 new sources beyond current 6 with rationale — acceptance scenario 1 from spec.md
- [x] T025 [US5] Validate at least one source category involves proactive crawling/monitoring (autonomous discovery) — acceptance scenario 2 from spec.md in specs/008-system-architecture/plan.md
- [x] T026 [US5] Validate paid sources include estimated cost and expected value relative to free alternatives — acceptance scenario 3 from spec.md in specs/008-system-architecture/plan.md
- [x] T027 [US5] Verify evaluation criteria exist for assessing new sources — FR-009 validation in specs/008-system-architecture/plan.md

**Checkpoint**: Data Source Expansion Plan is complete and meets all US5 acceptance scenarios

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Update project-level artifacts and perform final validation

- [x] T028 Verify constitution technology stack in .specify/memory/constitution.md reflects architecture decisions (Claude Agent SDK, FastMCP, fredapi, Tiingo, ntfy.sh, systemd timers — not n8n for core orchestration)
- [x] T029 [P] Verify CLAUDE.md reflects current architecture decisions and new technologies from specs/008-system-architecture/plan.md
- [x] T030 [P] Validate all 5 edge cases from specs/008-system-architecture/spec.md have mitigations defined in specs/008-system-architecture/plan.md
- [x] T031 Verify architecture document completeness — SC-006: next feature can begin without additional architecture planning (review specs/008-system-architecture/plan.md holistically)
- [x] T032 Run final cross-document consistency check: spec.md requirements ↔ plan.md sections ↔ research.md decisions — no contradictions across specs/008-system-architecture/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user story validation
- **US1 + US2 (Phase 3-4)**: Both P1, can run in parallel after Phase 2
- **US3 + US4 (Phase 5-6)**: Both P2, can run in parallel after Phase 2
- **US5 (Phase 7)**: P3, can run after Phase 2 (no dependency on US1-US4)
- **Polish (Phase 8)**: Depends on all user story phases being complete

### User Story Dependencies

- **US1 (Architecture Blueprint)**: Independent — no dependencies on other stories
- **US2 (Interaction Map)**: Independent — references components from US1 but can be validated independently
- **US3 (Build vs Buy)**: Independent — references components from US1 but own section
- **US4 (Phased Roadmap)**: Independent — references all other stories but validates roadmap structure
- **US5 (Data Source Expansion)**: Independent — own section in plan.md

### Parallel Opportunities

```bash
# After Phase 2 completes, all user stories can be validated in parallel:
# Batch 1 (P1 stories):
Task: T008-T011 [US1] Architecture Blueprint validation
Task: T012-T015 [US2] Interaction Map validation

# Batch 2 (P2 stories):
Task: T016-T019 [US3] Build vs Buy validation
Task: T020-T023 [US4] Phased Roadmap validation

# Batch 3 (P3 stories):
Task: T024-T027 [US5] Data Source Expansion validation
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup (verify documents exist)
2. Complete Phase 2: Foundational (cross-document consistency)
3. Complete Phase 3: US1 — Architecture Blueprint validation
4. Complete Phase 4: US2 — Interaction Map validation
5. **STOP and VALIDATE**: P1 stories cover the core architecture

### Incremental Delivery

1. Setup + Foundational → Documents verified consistent
2. US1 + US2 → Core architecture validated (MVP)
3. US3 + US4 → Build/buy and roadmap validated
4. US5 → Data expansion plan validated
5. Polish → Project artifacts updated, final consistency check

---

## Notes

- This is a **docs-only feature** — all tasks validate or update documents, no source code changes
- Validation tasks should flag specific issues (line numbers, missing items) for remediation
- If validation reveals gaps, the document should be updated before marking the task complete
- The plan.md IS the architecture document — it was produced during /speckit.plan
- Constitution and CLAUDE.md were already partially updated during /speckit.plan — Phase 8 verifies they are fully current
