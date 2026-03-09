# Feature Specification: Client List Builder

**Feature Branch**: `020-client-list-builder`
**Created**: 2026-03-09
**Status**: Draft
**Input**: User description: "Advanced client segmentation — compound filters, age-based queries, custom sorting, saved/named lists, and natural language queries for advisor CRM workflow training."

## User Scenarios & Testing

### User Story 1 - Compound Filters & Custom Sorting (Priority: P1)

Jordan wants to build targeted client lists using multiple filters combined together — for example, "clients under age 50 with account value over $200K and growth risk tolerance, sorted by account value." The existing sandbox supports only single-dimension filtering (one risk tolerance, one life stage, one value range, or one name search). Advisors need to combine these freely: age ranges, account value ranges, risk tolerance, life stage, last interaction date — all in a single query, with control over how results are sorted and how many to return.

This is the fundamental skill behind every advisor list-building exercise: "Top 50 under 50," "pre-retirees with aggressive allocation," "high-value clients I haven't contacted in 3 months." Without compound filtering and flexible sorting, Jordan can't practice the segmentation workflows that are central to CRM productivity.

**Why this priority**: Compound filtering is the foundation for all other list-building features. Saved lists (US2) and natural language queries (US3) both depend on having a powerful underlying query capability. This also has the highest immediate value — Jordan can start building real advisor lists the moment compound filters work.

**Independent Test**: With seed data loaded, run a compound query like "age under 50, account value over $200K, risk tolerance growth, sorted by account value descending, limit 50" and verify the results match all criteria simultaneously.

**Acceptance Scenarios**:

1. **Given** seed data exists in Salesforce, **When** Jordan queries for clients under age 50 with account value over $200K, **Then** only clients matching both criteria are returned.
2. **Given** seed data exists, **When** Jordan queries for growth-risk clients in the accumulation life stage with account value between $100K and $500K, **Then** all three filters are applied simultaneously and only matching clients are returned.
3. **Given** seed data exists, **When** Jordan requests results sorted by age ascending, **Then** results are sorted by age (not the default account value descending).
4. **Given** seed data exists, **When** Jordan requests results sorted by last interaction date, **Then** results are sorted by the most recent Task activity date.
5. **Given** seed data exists, **When** Jordan sets a result limit of 20, **Then** no more than 20 clients are returned, and the limit is applied after filtering and sorting.
6. **Given** seed data exists, **When** Jordan applies filters that match no clients, **Then** the system returns an empty result set with a message showing which filters were applied.
7. **Given** seed data exists, **When** Jordan queries with age range "40 to 55", **Then** only clients with age between 40 and 55 (inclusive) are returned.
8. **Given** seed data exists, **When** Jordan queries for clients with risk tolerance "growth" or "aggressive" and age under 50, **Then** clients matching either risk tolerance AND the age filter are returned.
9. **Given** seed data exists, **When** Jordan queries for clients not contacted in the last 90 days, **Then** only clients whose most recent interaction is older than 90 days (or who have no interactions) are returned.
10. **Given** seed data exists, **When** Jordan queries for clients last contacted between January 1 and March 1, **Then** only clients whose most recent interaction falls within that date range are returned.

---

### User Story 2 - Saved Lists (Priority: P2)

Jordan wants to save frequently-used filter combinations as named lists — for example, save the compound query "age under 50, account value over $200K, growth risk, sorted by account value, limit 50" as "Top 50 Under 50." He can then re-run that list at any time to get fresh results based on current Salesforce data. This mirrors how advisors work in real CRMs: they create saved searches, smart lists, or dynamic segments that they revisit regularly for outreach campaigns, review scheduling, and book-of-business analysis.

Saved lists are definitions (filter criteria), not snapshots — every time Jordan runs a saved list, it queries Salesforce with the saved filters and returns current results.

**Why this priority**: Saved lists build directly on compound filters (US1) and add the "reuse" dimension that makes list-building practical. Advisors don't re-type their filters every day — they save them and re-run them. This is lower priority than US1 because the filters must work first.

**Independent Test**: Create a saved list named "Top 50 Under 50" with compound filters, then run it and verify it returns matching results. Update a client's age in Salesforce, re-run the list, and verify the results reflect the change.

**Acceptance Scenarios**:

1. **Given** compound filters are available, **When** Jordan saves a filter combination as "Top 50 Under 50," **Then** the list is persisted with a name, description, and the filter criteria.
2. **Given** a saved list exists, **When** Jordan runs the list by name, **Then** the system executes the saved filters against current Salesforce data and returns fresh results.
3. **Given** a saved list exists, **When** Jordan lists all saved lists, **Then** he sees each list's name, description, filter criteria summary, and when it was last run.
4. **Given** a saved list exists, **When** Jordan updates the list's filters or name, **Then** the changes are persisted and the next run uses the updated criteria.
5. **Given** a saved list exists, **When** Jordan deletes the list, **Then** it is removed and no longer appears in the saved lists inventory.
6. **Given** a saved list returns results, **When** Jordan exports the results, **Then** a summary table is displayed with the same columns as the standard client list view, plus a header showing the list name and filter criteria.

---

### User Story 3 - Natural Language List Queries (Priority: P3)

Jordan wants to describe the client list he needs in plain English — "show me my biggest clients under 50" or "clients I haven't talked to in 3 months with over $500K" — and have the system translate that into the appropriate compound filter query. This is the "AI assistant" experience: Jordan thinks in advisor language, and the system translates to structured CRM queries. It's also a learning tool — after executing the query, the system shows Jordan what filters were applied, helping him understand the mapping between advisor intent and CRM query structure.

**Why this priority**: Natural language is the most convenient interface but also the most complex to build. It depends on compound filters (US1) being solid. It's P3 because Jordan can accomplish everything with explicit filters (US1) and saved lists (US2) — natural language is a productivity accelerator, not a prerequisite.

**Independent Test**: Type "show me top 20 clients under 40 with growth risk tolerance" and verify the system translates it to the correct compound filters, executes the query, and returns matching results with a "filters applied" summary.

**Acceptance Scenarios**:

1. **Given** seed data exists, **When** Jordan types "top 50 clients under 50," **Then** the system interprets this as age < 50, sorted by account value descending, limit 50, and returns matching results.
2. **Given** seed data exists, **When** Jordan types "clients I haven't talked to in 3 months with over $500K," **Then** the system interprets this as last interaction date > 90 days ago AND account value > $500K, and returns matching results.
3. **Given** a natural language query is executed, **When** results are displayed, **Then** the system also shows a "Filters applied" summary that maps each part of the natural language query to the structured filter used (e.g., "under 50" → "age < 50").
4. **Given** an ambiguous natural language query, **When** the system cannot confidently interpret the intent, **Then** it shows its best interpretation and asks Jordan to confirm before executing.
5. **Given** a natural language query that doesn't match any known filter pattern, **When** Jordan submits it, **Then** the system explains which parts it understood and which it couldn't interpret, and suggests how to rephrase.

---

### Edge Cases

- What happens when Jordan sorts by "last interaction date" but some clients have no interactions? Clients with no interactions sort to the end (nulls last), regardless of sort direction.
- What happens when Jordan saves a list with the same name as an existing list? The system rejects the save and suggests either choosing a new name or updating the existing list.
- What happens when a saved list references a filter field that is no longer valid? The system reports the error when the list is run and suggests updating the list definition.
- What happens when a compound filter includes contradictory criteria (e.g., age under 20 AND life stage retirement)? The system runs the query as specified and returns zero results — it does not second-guess the user's intent.
- What happens when Jordan requests more results than exist (e.g., "top 100" but only 50 clients match)? The system returns all matching clients and notes "Showing 50 of 50 matching clients (requested 100)."
- What happens when a natural language query is in a language other than English? The system attempts to interpret it but falls back to asking for clarification if confidence is low.

## Requirements

### Functional Requirements

- **FR-001**: System MUST support compound filtering — combining any number of the following filter dimensions in a single query: age range (min/max), account value range (min/max), risk tolerance (single or multiple values), life stage (single or multiple values), last interaction date (both recency-based — "not contacted in N days" — and absolute date range — "last contacted between date A and date B"), and free-text search. Multiple values within a single dimension (e.g., risk tolerance = growth OR aggressive) are combined with OR; dimensions are combined with AND.
- **FR-002**: System MUST support custom sort order on any sortable field: account value, age, last name, last interaction date. Both ascending and descending. Default remains account value descending.
- **FR-003**: System MUST support configurable result limits (e.g., "top 50") applied after filtering and sorting.
- **FR-004**: System MUST allow saving a filter + sort + limit combination as a named list with a user-provided name and optional description.
- **FR-005**: Saved lists MUST be dynamic — running a saved list always queries current data, not a cached snapshot.
- **FR-006**: System MUST support listing, running, updating, and deleting saved lists.
- **FR-007**: System MUST accept natural language descriptions of client lists and translate them into structured compound filter queries.
- **FR-008**: After executing a natural language query, the system MUST display a "Filters applied" summary showing how the natural language was interpreted.
- **FR-009**: System MUST display query results in a formatted table showing: name, age, account value, risk tolerance, life stage, and last interaction date.
- **FR-010**: All list builder capabilities MUST be available via both CLI and MCP tools.
- **FR-011**: Saved list definitions MUST persist across sessions.
- **FR-012**: When a natural language query is ambiguous, the system MUST show its interpretation and ask for confirmation before executing.

### Key Entities

- **Compound Filter**: A set of zero or more filter criteria (age range, value range, risk tolerance, life stage, interaction date via recency or absolute date range, text search) combined with AND logic across dimensions (multiple values within a single dimension use OR logic), plus a sort field, sort direction, and result limit.
- **Saved List**: A named, persisted compound filter definition with a user-provided name, optional description, filter criteria, and metadata (created date, last run date). Running a saved list executes its filters against current Salesforce data.
- **Query Interpretation**: The result of translating a natural language string into a compound filter, including a confidence assessment and a human-readable mapping of each natural language phrase to its corresponding filter.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Jordan can build any compound filter query (combining 2+ filter dimensions) and receive results in under 5 seconds.
- **SC-002**: Jordan can save a named list, close the application, reopen it, and run the saved list — getting fresh results each time.
- **SC-003**: Jordan can type a natural language list description and receive correctly-filtered results at least 80% of the time for common advisor queries (e.g., "top 50 under 50," "high-value clients I haven't contacted recently," "pre-retirees with growth risk").
- **SC-004**: Every query result shows the filters that were applied, so Jordan learns the mapping between advisor language and CRM query structure.
- **SC-005**: The "Top 50 Under 50" query — age under 50, sorted by account value descending, limit 50 — works end-to-end via compound filter, saved list, and natural language.

## Clarifications

### Session 2026-03-09

- Q: Can Jordan filter for multiple values within a single dimension (e.g., risk tolerance = growth OR aggressive)? → A: Yes — multi-value within a dimension is allowed (OR within dimension, AND across dimensions).
- Q: Should interaction date filter support recency ("not contacted in N days"), absolute date range, or both? → A: Both — recency-based and absolute date range filtering are supported.

## Assumptions

- This feature extends the existing Salesforce sandbox (019-sfdc-sandbox). All client data lives in Salesforce (Contact + Task objects). Compound filters translate to SOQL queries.
- Saved lists are persisted locally (not in Salesforce) since they are a tool feature, not CRM data. Storage mechanism is an implementation detail.
- Natural language interpretation uses an AI model for translation. The system does not need to handle every possible phrasing — common advisor patterns (age filters, value thresholds, risk/stage categories, recency-based interaction filters) are the priority.
- "Last interaction date" refers to the most recent Task.ActivityDate associated with a Contact.
- Filter dimensions are combined with AND logic. Within a single dimension (risk tolerance, life stage), multiple values are combined with OR logic (e.g., "growth or aggressive"). Cross-dimension OR (e.g., "growth risk OR retirement stage") is out of scope.
- The existing `list_clients()` function will be enhanced (not replaced) to support compound filters. Current single-filter CLI usage continues to work unchanged.
- All data remains synthetic. No production CRM connections.
