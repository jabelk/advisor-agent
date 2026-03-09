# Tasks: Salesforce Learning Guide

**Input**: Design documents from `/specs/024-sfdc-learning-guide/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/lesson-template.md

**Tests**: No tests — this is a content feature (markdown files only).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create the `guide/` directory structure

- [x] T001 Create `guide/` directory at repository root

---

## Phase 2: Foundational (Getting Started)

**Purpose**: The Getting Started lesson is a prerequisite for ALL other lessons — Jordan needs sandbox access and Claude Desktop connected before any exercises work.

**CRITICAL**: No lesson tasks can begin until this phase is complete.

- [x] T002 Write Getting Started lesson in `guide/00-getting-started.md` — cover sandbox login at `orgfarm-561a3648a3-dev-ed.develop.my.salesforce.com`, Claude Desktop Project setup (point to `guide/` folder), seed data verification via `sandbox_seed_clients` / `sandbox_list_clients`, and Salesforce Lightning navigation basics. Follow lesson template from `specs/024-sfdc-learning-guide/contracts/lesson-template.md`.

**Checkpoint**: Jordan can log into Salesforce sandbox, connect Claude Desktop to the guide Project, and confirm seed data exists.

---

## Phase 3: User Story 1 — Self-Paced Lesson Walkthrough (Priority: P1) MVP

**Goal**: Jordan can open any lesson, perform manual exercises in Salesforce, and verify results with Claude Desktop MCP tools.

**Independent Test**: Jordan opens Lesson 1, finds Janet Morales in Salesforce, asks Claude "Show me details for Janet Morales", and the MCP output matches what he sees on screen.

### Implementation for User Story 1

- [x] T003 [P] [US1] Write Lesson 1: Navigating Contacts in `guide/01-contacts.md` — CRM concept: contact records and client profiles. Exercise: browse contacts list, open a specific client (Janet Morales), review fields (name, email, phone, description). Verify with Claude using `sandbox_get_client` and `sandbox_list_clients`. Challenge: find a different client and compare fields. Follow lesson template.
- [x] T004 [P] [US1] Write Lesson 2: Creating and Managing Tasks in `guide/02-tasks.md` — CRM concept: activity tracking and follow-ups. Exercise: create a follow-up task for Janet Morales (call, email, or meeting), set due date and priority. Verify with Claude using `sandbox_show_tasks` and `sandbox_create_task`. Challenge: create tasks for a different client with different priorities. Follow lesson template.
- [x] T005 [P] [US1] Write Lesson 3: Searching and Filtering Clients in `guide/03-search-filter.md` — CRM concept: finding clients by criteria. Exercise: use Salesforce search bar to find clients by name, use list view filters to narrow by criteria. Verify with Claude using `sandbox_search_clients` and `sandbox_query_clients`. Challenge: find all clients in a specific state or with a specific attribute. Follow lesson template.
- [x] T006 [P] [US1] Write Lesson 4: Creating List Views in `guide/04-list-views.md` — CRM concept: saved filters and custom views. Exercise: create a new list view filtering contacts by specific criteria, save it for reuse. Verify with Claude using `sandbox_show_listviews` and `sandbox_save_listview`. Challenge: create a second list view with different filters. Follow lesson template.
- [x] T007 [P] [US1] Write Lesson 5: Building Reports in `guide/05-reports.md` — CRM concept: data aggregation and insights. Exercise: build a simple contact report with filters, view results in Salesforce. Verify with Claude using `sandbox_show_reports` and `sandbox_save_report`. Challenge: build a report combining multiple filters. Follow lesson template.

**Checkpoint**: All 5 lessons are complete. Jordan can work through any lesson independently — each has manual exercises and MCP verification steps.

---

## Phase 4: User Story 2 — Claude Tutor Project (Priority: P2)

**Goal**: Jordan points Claude Desktop to the `guide/` folder as a Project and gets a persistent Salesforce tutor that knows the curriculum, uses MCP tools, and guides without giving away answers.

**Independent Test**: Jordan opens the Claude Desktop Project, asks "What lessons are available?" and gets an accurate list with descriptions. Asks "Help me with Lesson 2" and gets contextual guidance.

### Implementation for User Story 2

- [x] T008 [US2] Write Claude Desktop Project tutor prompt in `guide/CLAUDE.md` — role: Salesforce tutor for a financial advisor. Include: curriculum awareness (all 6 lessons with topics and MCP tools), teaching style (guide without giving away answers, verify work on request, explain CRM concepts in advisor-relevant terms), MCP tool usage instructions (proactively use sandbox tools when verifying), seed data awareness (50 synthetic clients, reference by name), lesson progression suggestions. Reference specific MCP tools: `sandbox_list_clients`, `sandbox_get_client`, `sandbox_search_clients`, `sandbox_query_clients`, `sandbox_show_tasks`, `sandbox_create_task`, `sandbox_show_listviews`, `sandbox_save_listview`, `sandbox_show_reports`, `sandbox_save_report`, `sandbox_seed_clients`.

**Checkpoint**: Claude Desktop loaded with the Project gives contextual lesson guidance and uses MCP tools for verification.

---

## Phase 5: User Story 3 — Progressive Skill Building (Priority: P3)

**Goal**: Lessons build on each other in a coherent progression — basic navigation → data entry → search → views → reports. Each lesson references prerequisite skills from earlier lessons.

**Independent Test**: Jordan completes Lessons 1–3 in order and can perform Lesson 3 exercises without referring back to Lesson 1 for basic navigation.

### Implementation for User Story 3

- [x] T009 [US3] Review and update all lesson files (`guide/01-contacts.md` through `guide/05-reports.md`) for progressive cross-references — ensure each lesson's Prerequisites section correctly lists prior lessons, exercise instructions build on previously learned skills (e.g., Lesson 4 assumes Jordan can already search from Lesson 3), and Key Takeaways reinforce cumulative learning. Verify no lesson assumes skills not yet taught.
- [x] T010 [US3] Update `guide/CLAUDE.md` to include progression guidance — add instructions for Claude to suggest the next lesson when one is completed, warn if Jordan skips ahead without prerequisites, and reference the dependency chain (Lesson 0 → 1 → 2/3 → 4 → 5).

**Checkpoint**: Lessons form a coherent curriculum with clear progression. Claude tutor guides Jordan through the sequence.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and consistency checks across all guide content.

- [x] T011 [P] Validate all lessons against lesson template contract in `specs/024-sfdc-learning-guide/contracts/lesson-template.md` — every lesson has: Objective (one sentence), CRM Concept (no Salesforce-specific UI elements), Prerequisites (checked), Exercise (3–6 steps with seed data names), Verify with Claude (exact copy-paste prompts), Key Takeaways (includes Advisor tip), Challenge (different data than main exercise)
- [x] T012 [P] Verify all MCP tool names referenced in lessons and CLAUDE.md match actual deployed tools — cross-reference against the 21 sandbox tools on Railway
- [ ] T013 Run quickstart.md validation scenarios from `specs/024-sfdc-learning-guide/quickstart.md` — test all 5 scenarios against live sandbox

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — create directory
- **Foundational (Phase 2)**: Depends on Phase 1 — Getting Started lesson must exist before other lessons
- **User Story 1 (Phase 3)**: Depends on Phase 2 — all 5 lessons can be written in parallel [P]
- **User Story 2 (Phase 4)**: Depends on Phase 3 — CLAUDE.md needs to reference lesson content
- **User Story 3 (Phase 5)**: Depends on Phase 3 and Phase 4 — cross-referencing requires all lessons and CLAUDE.md to exist
- **Polish (Phase 6)**: Depends on all previous phases

### Parallel Opportunities

- **Phase 3**: All 5 lesson files (T003–T007) can be written in parallel — they are independent files
- **Phase 5**: T009 and T010 must be sequential (T009 updates lessons, T010 updates CLAUDE.md to match)
- **Phase 6**: T011 and T012 can run in parallel; T013 requires live sandbox access

---

## Parallel Example: User Story 1

```bash
# Launch all 5 lessons in parallel (different files, no dependencies):
Task: "Write Lesson 1: Navigating Contacts in guide/01-contacts.md"
Task: "Write Lesson 2: Creating and Managing Tasks in guide/02-tasks.md"
Task: "Write Lesson 3: Searching and Filtering Clients in guide/03-search-filter.md"
Task: "Write Lesson 4: Creating List Views in guide/04-list-views.md"
Task: "Write Lesson 5: Building Reports in guide/05-reports.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Create `guide/` directory
2. Complete Phase 2: Write Getting Started lesson
3. Complete Phase 3: Write all 5 lessons (parallel)
4. **STOP and VALIDATE**: Jordan walks through Lesson 1 end-to-end
5. Deliver lessons as standalone markdown files

### Incremental Delivery

1. Phase 1 + 2 → Jordan can access sandbox and verify seed data
2. Add Phase 3 → Jordan has full lesson set with MCP verification (MVP!)
3. Add Phase 4 → Claude becomes a persistent tutor with curriculum awareness
4. Add Phase 5 → Lessons form a coherent progressive curriculum
5. Each phase adds value without breaking previous phases

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- This is a content feature — no application code changes
- All lessons must reference seed data clients by name for verifiable exercises
- Lesson template contract is the source of truth for lesson structure
- Total: 13 tasks across 6 phases
