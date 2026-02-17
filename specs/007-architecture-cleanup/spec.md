# Feature Specification: Architecture Pivot Cleanup

**Feature Branch**: `007-architecture-cleanup`
**Created**: 2026-02-17
**Status**: Draft
**Input**: User description: "cleanup code and docs for architecture pivot"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove Obsolete Code Modules (Priority: P1)

As a developer, I want to remove the execution, engine, and market data layers from the codebase so that only code relevant to the research-first architecture remains, reducing maintenance burden and freeing context window budget for innovation.

The system was originally built as an end-to-end automated trading bot (features 001-005, ~6,700 lines). The architecture pivot (006) decided that ~3,500 lines of execution, decision engine, and market data code should be replaced by MCP servers and conversational Claude. This dead code must be removed cleanly.

**Why this priority**: Dead code is the highest-impact cleanup target. It confuses contributors, wastes context window when the AI reads the codebase, and creates false import dependencies. Removing it is a prerequisite for all future features.

**Independent Test**: Can be verified by confirming the three module directories no longer exist, all remaining code compiles without import errors, and all remaining tests pass.

**Acceptance Scenarios**:

1. **Given** the execution layer exists, **When** cleanup is complete, **Then** the `execution/` directory and all its contents are removed
2. **Given** the engine layer exists (scoring, proposals, account, state), **When** cleanup is complete, **Then** the `engine/` directory and all its contents are removed
3. **Given** the market data layer exists (bars, indicators, snapshot, client), **When** cleanup is complete, **Then** the `market/` directory and all its contents are removed
4. **Given** the removed modules had associated tests, **When** cleanup is complete, **Then** the corresponding test files are removed (engine tests, market tests)
5. **Given** other modules import from removed layers, **When** cleanup is complete, **Then** all import references to removed modules are eliminated and the remaining code has zero import errors

---

### User Story 2 - Preserve Safety Guardrails (Priority: P1)

As an operator managing real money, I need the safety guardrails (kill switch, position size limits, daily loss limits, trade count limits) to survive the engine removal as an independent safety module, so that Constitution Principle I (Safety First) continues to be enforced at the execution boundary regardless of how trades are initiated.

The current safety logic lives inside the engine layer that is being removed. These guardrails are non-negotiable per the project constitution and must be extracted before the engine is deleted.

**Why this priority**: Same priority as US1 because removing the engine without preserving safety guardrails would violate the project constitution. This must happen as part of (or before) the engine removal.

**Independent Test**: Can be verified by confirming the safety module exists, the kill switch can be toggled, risk limits can be queried and set, and the module has no dependencies on removed layers.

**Acceptance Scenarios**:

1. **Given** the kill switch logic exists in the engine layer, **When** cleanup is complete, **Then** a standalone safety module provides kill switch functionality (enable, disable, query status)
2. **Given** position size limits exist in the engine layer, **When** cleanup is complete, **Then** the safety module enforces maximum position size as a percentage of portfolio
3. **Given** daily loss limits exist in the engine layer, **When** cleanup is complete, **Then** the safety module enforces maximum daily loss as a percentage of portfolio
4. **Given** trade count limits exist in the engine layer, **When** cleanup is complete, **Then** the safety module enforces maximum trades per day
5. **Given** the safety module is independent, **When** any component queries safety status, **Then** the response includes all configured limits and kill switch state without depending on engine or market modules. Utilization tracking (counting trades, tracking daily P&L) is deferred to a future feature when the MCP execution flow is designed.

---

### User Story 3 - Streamline the Command-Line Interface (Priority: P2)

As a developer, I want the CLI to only contain commands relevant to the research-first system so that the help output is clean, commands match the current architecture, and there is no confusion about removed capabilities.

The current CLI is 1,620 lines with 9 command groups and 20+ subcommands. The engine (7 subcommands) and market (4 subcommands) command groups are being removed. The remaining commands (version, health, watchlist, investors, research, signals, profile) should be kept and updated to remove any references to the deleted layers. No new CLI commands are added for the safety module — safety state is accessible only programmatically or via a future MCP server tool.

**Why this priority**: P2 because the CLI is the user-facing interface and should be accurate, but the system functions correctly even if the CLI still has dead commands (they would just error on import).

**Independent Test**: Can be verified by running the CLI help output and confirming only active commands appear, and each remaining command executes without error.

**Acceptance Scenarios**:

1. **Given** the engine command group exists in the CLI, **When** cleanup is complete, **Then** no engine-related commands appear in help output or are callable
2. **Given** the market command group exists in the CLI, **When** cleanup is complete, **Then** no market-related commands appear in help output or are callable
3. **Given** the health check references engine and market components, **When** cleanup is complete, **Then** the health check only validates active components (database, data sources, research pipeline)
4. **Given** a user runs any remaining CLI command, **When** the command executes, **Then** it completes successfully without import errors from removed modules

---

### User Story 4 - Clean Database Schema (Priority: P2)

As a developer, I want unused database tables removed from the schema so that the database reflects only the active system, migrations are clean, and there is no confusion about which data is live.

Nine database tables created by features 003-005 (market data, decision engine, order execution) are no longer used. They should be dropped via a new migration.

**Why this priority**: P2 because the unused tables do not cause runtime errors but add confusion and waste storage. Must happen before any new features add tables.

**Independent Test**: Can be verified by running the migration and confirming the removed tables no longer exist while all kept tables and their data remain intact.

**Acceptance Scenarios**:

1. **Given** market data tables exist (price_bar, technical_indicator, market_data_fetch), **When** the cleanup migration runs, **Then** these tables are dropped
2. **Given** engine tables exist (trade_proposal, proposal_source, risk_check_result, engine_state), **When** the cleanup migration runs, **Then** these tables are dropped
3. **Given** execution tables exist (broker_order, position_snapshot), **When** the cleanup migration runs, **Then** these tables are dropped
4. **Given** research tables exist (company, source_document, research_signal, notable_investor, ingestion_run), **When** the cleanup migration runs, **Then** these tables remain intact with all existing data preserved
5. **Given** the audit log table exists, **When** the cleanup migration runs, **Then** the audit log remains intact with all existing data preserved

---

### User Story 5 - Update Documentation (Priority: P3)

As a developer or contributor, I want documentation to accurately describe the current system so that there is no confusion about what the system does, what components exist, and how they work together.

The README, CHANGELOG, and any other project documentation currently describe a five-layer automated trading system. After cleanup, the documentation should describe a research-first investment system with data ingestion, research/analysis, and audit layers.

**Why this priority**: P3 because documentation inaccuracy does not affect system behavior, but outdated docs waste developer time and cause confusion.

**Independent Test**: Can be verified by reading the README and confirming it describes only the active system with no references to removed components.

**Acceptance Scenarios**:

1. **Given** the README describes the decision engine, **When** cleanup is complete, **Then** the README describes the research-first architecture without engine/market/execution sections
2. **Given** the CHANGELOG tracks features 001-005, **When** cleanup is complete, **Then** the CHANGELOG preserves historical entries and adds a new entry documenting the architecture pivot cleanup
3. **Given** Dockerfile and docker-compose reference removed components, **When** cleanup is complete, **Then** container configuration reflects only the active system

---

### Edge Cases

- What happens if the safety module's database table (engine_state) is renamed or restructured during cleanup? The kill switch and risk limit state must be preserved or migrated, not lost.
- What happens if existing research signals reference documents that also have engine-generated signals? Research data must be fully preserved even if engine-generated metadata existed in the same tables.
- What happens if a user has an existing database with data in the removed tables? The migration must cleanly drop those tables without affecting kept tables, even if the removed tables contain data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST remove the `execution/` module directory and all its contents
- **FR-002**: System MUST remove the `engine/` module directory and all its contents
- **FR-003**: System MUST remove the `market/` module directory and all its contents
- **FR-004**: System MUST remove all test files that exclusively test removed modules (engine tests, market tests)
- **FR-005**: System MUST extract safety guardrail logic (kill switch, position limits, daily loss limits, trade count limits) into an independent safety module before removing the engine layer. The safety module stores configured limits and kill switch state only; utilization tracking (trade counting, daily P&L) is deferred to a future feature.
- **FR-006**: System MUST preserve all existing safety state (kill switch status, configured limits) through the migration
- **FR-007**: System MUST remove all engine and market CLI command groups from the command-line interface
- **FR-008**: System MUST update the health check to only validate active components
- **FR-009**: System MUST provide a database migration that drops all unused tables (9 tables from market, engine, and execution features)
- **FR-010**: System MUST preserve all research data (company, source_document, research_signal, notable_investor, ingestion_run tables) through the migration
- **FR-011**: System MUST preserve the audit log through the migration
- **FR-012**: System MUST update the README to describe the current research-first architecture
- **FR-013**: System MUST add a CHANGELOG entry documenting the architecture pivot cleanup
- **FR-014**: System MUST update Docker configuration files to reflect the active system
- **FR-015**: System MUST have zero import errors after all module removals — every remaining file compiles cleanly
- **FR-016**: System MUST have all remaining tests pass after cleanup

### Key Entities

- **Safety State**: Kill switch status (enabled/disabled), position size limit (percentage), daily loss limit (percentage), trade count limit (integer). Previously stored in the engine_state table; must survive cleanup in a new or renamed table.
- **Research Data**: Company watchlist, source documents, research signals, notable investors, ingestion runs. Must be fully preserved with no data loss.
- **Audit Log**: Append-only log of all system actions. Must be fully preserved.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Total source code line count decreases by at least 50% (from ~6,700 lines to ~3,300 or fewer)
- **SC-002**: 100% of remaining unit and integration tests pass after cleanup
- **SC-003**: Zero import errors across all remaining source files
- **SC-004**: CLI help output shows zero references to engine, market, or execution commands
- **SC-005**: Safety guardrails (kill switch, position limits, daily loss, trade count) remain functional and independently testable after cleanup
- **SC-006**: All research data (signals, documents, companies, investors) is fully preserved through the database migration with zero data loss
- **SC-007**: README accurately describes only the active system components with no references to removed layers

## Clarifications

### Session 2026-02-17

- Q: Should the safety module include utilization tracking (counting trades, tracking daily P&L), or only store limits and kill switch state? → A: Limits + kill switch only. Utilization tracking deferred to a future feature when MCP execution flow is designed.
- Q: Should the safety module get its own CLI command group, or be accessible only programmatically? → A: No safety CLI commands. Access safety state only programmatically or via a future MCP server tool.

## Assumptions

- Historical spec documents (specs/003-market-data/, specs/004-decision-engine/) are kept as-is for project history. They are not modified or deleted.
- No new dependencies need to be added for this cleanup. The safety module uses existing dependencies only.
- The safety module's database table can be a renamed/restructured version of the existing engine_state table, or a new table — either approach is acceptable as long as state is preserved.
- The CHANGELOG preserves all historical entries. Only a new entry is added; nothing is deleted from the log.
