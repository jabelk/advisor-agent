# Data Model: System Architecture Design

**Feature**: 008-system-architecture | **Date**: 2026-02-17

This feature produces architecture documents, not source code. This data model describes the **entities and relationships in the target architecture** — the logical data structures that future implementation features will build.

---

## Core Entities

### Component

A distinct piece of the system with a defined responsibility and runtime location.

| Field | Type | Description |
|-------|------|-------------|
| name | string | Unique component identifier |
| runtime | enum | NUC, Claude Desktop, Cloud, External |
| responsibility | string | What this component does |
| build_or_buy | enum | Build (custom), Buy (off-the-shelf) |
| status | enum | Existing, New, Planned |
| estimated_loc | int | Lines of custom code (0 for Buy) |
| interfaces | list[Interface] | How this component connects to others |

### Interface

A defined connection between two components.

| Field | Type | Description |
|-------|------|-------------|
| from_component | string | Source component name |
| to_component | string | Target component name |
| protocol | enum | MCP/JSON-RPC, NATS, HTTPS, SQLite, Filesystem, Process Exec |
| data_format | enum | JSON, SQL, MCP Tool Call, CLI Args, Markdown |
| trigger | enum | Schedule, Event, Human Request |
| direction | enum | Unidirectional, Bidirectional |

### Data Source

An external provider of financial information.

| Field | Type | Description |
|-------|------|-------------|
| name | string | Source identifier |
| data_type | string | What kind of data it provides |
| library | string | Python library used for access |
| cost | string | Monthly cost ($0, $25, $149, etc.) |
| rate_limit | string | API rate limit description |
| priority | enum | P1 (immediate), P2 (next), P3 (future) |
| status | enum | Current, Planned, Evaluated-Skipped |

### Phase

A sequenced unit of implementation work.

| Field | Type | Description |
|-------|------|-------------|
| number | int | Phase sequence (1-4) |
| name | string | Phase title |
| scope | enum | Small (~1 week), Medium (~2 weeks) |
| deliverables | list[string] | What gets built |
| definition_of_done | string | How to verify completion |
| dependencies | list[int] | Phase numbers that must complete first |
| standalone_value | bool | Does this phase work independently? |

### Agent

An autonomous Python process that runs on the NUC.

| Field | Type | Description |
|-------|------|-------------|
| name | string | Agent identifier |
| trigger | enum | systemd timer, NATS event, CLI command |
| schedule | string | Cron expression or event pattern |
| llm_model | enum | None, Haiku, Sonnet, Opus |
| inputs | list[string] | Data sources this agent reads |
| outputs | list[string] | What this agent produces |
| estimated_loc | int | Lines of custom code |

---

## Relationships

```
Component 1───* Interface *───1 Component
    │
    └── build_or_buy determines LOC estimate

Data Source *───* Agent (agents consume data sources)
    │
    └── priority determines implementation Phase

Phase 1───* Component (each phase creates/modifies components)
    │
    └── dependencies create ordering constraints

Agent ──── Component (each agent IS a component on the NUC)
    │
    └── trigger + schedule determine systemd timer config
```

---

## State Transitions

### Research Signal Lifecycle

```
[Data Ingested] → [Analysis Queued] → [Analysis Running] → [Signal Produced] → [Human Reviewed]
                                           │
                                           └── [Analysis Failed] → (retry or skip)
```

### Filing Discovery Lifecycle

```
[RSS Polled] → [New Filing Detected] → [Download Queued] → [Downloaded] → [Stored] → [Analysis Triggered]
                    │
                    └── [Already Ingested] → (skip)
```

### Trade Execution Lifecycle (via Claude Desktop)

```
[Human Request] → [Safety Check] → [Confirmation Prompt] → [Order Placed] → [Order Confirmed]
                       │                    │
                       └── [Safety Blocked]  └── [Human Cancelled]
```

---

## Validation Rules

- Every component MUST have at least one interface (no orphan components)
- Every data source MUST be assigned to at least one agent
- Every phase MUST have `standalone_value = true`
- The sum of all `estimated_loc` for Build components MUST NOT exceed 2x current codebase (~7,000 LOC cap)
- Safety checks MUST occur before any trade-related MCP tool calls
- All agent outputs MUST be logged in the audit trail
