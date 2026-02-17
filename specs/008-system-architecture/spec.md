# Feature Specification: System Architecture Design

**Feature Branch**: `008-system-architecture`
**Created**: 2026-02-17
**Status**: Draft
**Input**: User description: "System architecture planning for research-powered investment system — design how MCP servers, n8n orchestration, autonomous research agents, and the existing Python codebase fit together."

## User Scenarios & Testing

### User Story 1 - Architecture Blueprint (Priority: P1)

The operator needs a clear, documented architecture that maps every component in the system: what runs where, how components communicate, and what is custom-built versus off-the-shelf. This blueprint becomes the single source of truth for all future feature work.

**Why this priority**: Without an agreed architecture, every future feature starts with "where does this go?" — leading to wasted effort, contradictory designs, and code that gets thrown away (as happened with features 003-005). The blueprint must exist before any new code is written.

**Independent Test**: Can be validated by reviewing the architecture document against these criteria: every component has a defined runtime location, every communication path has a defined protocol, and every capability is assigned to exactly one component (no overlaps, no gaps).

**Acceptance Scenarios**:

1. **Given** the current codebase (research pipeline, safety module, audit log), **When** the operator reviews the architecture document, **Then** every existing module is accounted for and has a clear role in the new system.
2. **Given** the list of desired capabilities (research ingestion, analysis, trading, notifications, scheduling), **When** the operator reviews the architecture document, **Then** each capability is assigned to a specific component with a rationale for build vs. buy.
3. **Given** the Intel NUC as the primary runtime, **When** the operator reviews the deployment map, **Then** all always-on services are assigned to the NUC and resource requirements are estimated.

---

### User Story 2 - Component Interaction Map (Priority: P1)

The operator needs to understand how data flows between components — from raw data sources through analysis to the human decision point. This includes what triggers each step (schedule, event, human request) and what format data takes at each boundary.

**Why this priority**: The system has multiple runtimes (NUC services, Claude Desktop, external APIs). Without a clear interaction map, integrations will be built ad-hoc and break when components change.

**Independent Test**: Can be validated by tracing a concrete scenario (e.g., "new SEC filing drops for a watchlist company") through the interaction map from trigger to human notification, confirming every handoff is defined.

**Acceptance Scenarios**:

1. **Given** a new SEC filing appears for a watchlist company, **When** traced through the interaction map, **Then** every step from detection to ingestion to analysis to notification to human review is defined with trigger mechanism and data format.
2. **Given** the operator opens Claude Desktop for an evening research session, **When** traced through the interaction map, **Then** the path from "ask about a company" to research DB query to synthesized answer is defined.
3. **Given** the operator decides to place a trade during conversation, **When** traced through the interaction map, **Then** the path from decision to safety check to order placement to confirmation is defined.

---

### User Story 3 - Build vs. Buy Decisions (Priority: P2)

The operator needs explicit, justified decisions on what to build as custom code versus what to use off-the-shelf (MCP servers, n8n workflows, existing services). Each decision must include rationale, alternatives considered, and estimated effort.

**Why this priority**: The core philosophy is "less code = more context." Every custom component has ongoing maintenance cost that competes with the context window budget. Getting build-vs-buy wrong means either reinventing wheels or depending on tools that don't fit.

**Independent Test**: Can be validated by reviewing each build-vs-buy decision against the criteria: does a suitable off-the-shelf option exist? If building custom, what unique value does it provide that no existing tool covers?

**Acceptance Scenarios**:

1. **Given** a capability that an existing MCP server or n8n node can handle, **When** the build-vs-buy decision is reviewed, **Then** the off-the-shelf option is chosen unless a documented limitation makes it unsuitable.
2. **Given** the existing Python research pipeline (~3,600 lines), **When** the build-vs-buy analysis is complete, **Then** each module has a verdict: keep as-is, refactor, replace with external tool, or remove.
3. **Given** the operator's willingness to pay for tools and data services, **When** evaluating options, **Then** cost is considered but not the primary constraint — capability and maintenance burden are weighted higher.

---

### User Story 4 - Phased Implementation Roadmap (Priority: P2)

The operator needs a sequenced plan for building out the architecture in phases, where each phase delivers usable value and doesn't require future phases to function. The roadmap should define what "done" looks like for each phase.

**Why this priority**: The system can't be built all at once. A phased plan prevents the mistake of features 003-005 (building an end-to-end pipeline that was discarded). Each phase must stand on its own.

**Independent Test**: Can be validated by confirming each phase has: a clear deliverable, a definition of "done," no hard dependency on later phases, and a rough scope estimate (small/medium/large).

**Acceptance Scenarios**:

1. **Given** the architecture blueprint, **When** the roadmap is reviewed, **Then** each phase delivers a working increment (not a partial, non-functional skeleton).
2. **Given** the operator's solo-developer constraint, **When** phase scope is reviewed, **Then** no single phase requires more than roughly 2 weeks of effort (accounting for AI-assisted development speed).
3. **Given** the existing research pipeline already works, **When** the roadmap is reviewed, **Then** Phase 1 builds on what exists rather than replacing it.

---

### User Story 5 - Data Source Expansion Plan (Priority: P3)

The operator needs a plan for which new data sources to add, in what order, and how they integrate into the architecture. The current 6 sources (SEC EDGAR, Finnhub, EarningsCall, 13F, Acquired, Stratechery) are a starting point — the system should grow to include social sentiment, macro indicators, alternative data, and autonomous web discovery.

**Why this priority**: Research quality is the system's differentiator. More and better data sources directly improve investment decisions. However, this is P3 because the architecture must be designed first (US1-US2) and build-vs-buy decisions made (US3) before adding sources.

**Independent Test**: Can be validated by reviewing the expansion plan and confirming each proposed source has: a data description, integration method, estimated value to research quality, and priority ranking.

**Acceptance Scenarios**:

1. **Given** the current 6 data sources, **When** the expansion plan is reviewed, **Then** at least 5 additional sources are identified and prioritized with rationale.
2. **Given** the "autonomous discovery" goal, **When** the expansion plan is reviewed, **Then** at least one source category involves proactive crawling or monitoring (not just scheduled API pulls).
3. **Given** the operator's willingness to pay for data, **When** evaluating paid sources, **Then** each includes estimated cost and expected value relative to free alternatives.

---

### Edge Cases

- What happens when the NUC is offline or rebooting? Which components need graceful recovery vs. which simply resume on next run?
- What if an MCP server is unavailable during a Claude Desktop session? How does the system degrade?
- How does the system handle conflicting research signals from different sources about the same company?
- What happens when a data source API changes its format or rate limits?
- How are research artifacts backed up? What is the disaster recovery plan for the SQLite database?

## Requirements

### Functional Requirements

- **FR-001**: The architecture document MUST define every component in the system with its runtime location (NUC, Claude Desktop, cloud service, external API).
- **FR-002**: The architecture document MUST define every communication path between components including protocol, data format, and trigger mechanism (schedule, event, request).
- **FR-003**: The architecture document MUST include a build-vs-buy decision for every capability, with rationale and alternatives considered.
- **FR-004**: The architecture MUST preserve existing working functionality (research pipeline, safety module, audit log) — no regressions.
- **FR-005**: The architecture MUST define how the human interacts with the system for both research review and trade execution.
- **FR-006**: The architecture MUST define how always-on services (scheduling, monitoring, notifications) run on the Intel NUC.
- **FR-007**: The architecture MUST define how safety guardrails (kill switch, risk limits) are enforced regardless of which component initiates a trade.
- **FR-008**: The architecture MUST include a phased implementation roadmap where each phase delivers standalone value.
- **FR-009**: The architecture MUST define the data source expansion strategy, including criteria for evaluating and prioritizing new sources.
- **FR-010**: The architecture MUST account for the "less code = more context" constraint — total custom code should not grow significantly beyond the current ~3,600 lines unless justified.

### Key Entities

- **Component**: A distinct piece of the system (service, tool, or module) with a defined responsibility, runtime location, and interfaces.
- **Communication Path**: A defined connection between two components, specifying protocol, data format, directionality, and trigger.
- **Data Source**: An external provider of financial information, with integration method, cost, rate limits, and data type.
- **Phase**: A sequenced unit of implementation work that delivers standalone value, with defined scope, deliverables, and completion criteria.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Architecture document covers 100% of system capabilities with no unassigned or overlapping responsibilities between components.
- **SC-002**: Every communication path can be traced end-to-end for at least 3 concrete scenarios (filing drops, evening research session, trade execution).
- **SC-003**: Build-vs-buy decisions reduce planned custom code to the minimum necessary — at least 60% of new capabilities use off-the-shelf tools.
- **SC-004**: Phased roadmap contains at least 3 phases, each independently deliverable within roughly 2 weeks.
- **SC-005**: Data source expansion plan identifies at least 5 new sources beyond the current 6, with priority rankings and integration approach.
- **SC-006**: Architecture document is complete enough that the next feature can begin implementation without additional architecture planning.

## Assumptions

- The Intel NUC (home server) is the primary always-on runtime. It already runs Docker and has a GitHub Actions runner.
- Claude Desktop (on the operator's workstation) is the primary human interaction point for research review and trade decisions.
- The operator works primarily through Claude Code for development, making context window efficiency a real constraint.
- The operator is willing to pay for tools, data services, and infrastructure — cost is not the primary constraint.
- The existing research pipeline (data ingestion, LLM analysis, signal generation) is working and should be preserved, not rewritten.
- n8n is available as a self-hosted orchestration option on the NUC but has not been evaluated yet — it may or may not be the right choice.
- NATS is already running on the NUC and available for messaging if needed.

## Out of Scope

- Writing implementation code — this feature produces architecture documents only, no source code changes.
- Evaluating or changing the core LLM (Claude) — the system is built around Claude and this is not up for debate.
- Changing the broker (Alpaca Markets) — this is a fixed constraint.
- Building a web UI — the primary interface is Claude Desktop via conversation.
