# Research: Salesforce Learning Guide

## Decision 1: Lesson Content Depth

**Decision**: Each lesson teaches one CRM concept with a 15-minute target completion time, using a "do it manually, then verify with Claude" pattern.

**Rationale**: Jordan is an experienced professional learning a new tool, not a student in a classroom. Short, focused lessons respect his time while building skills progressively. The MCP verification loop provides immediate feedback without requiring an instructor.

**Alternatives considered**:
- Long-form tutorial (30+ minutes per lesson): Too much for busy advisor schedule
- Video-based learning: Out of scope, harder to maintain, can't leverage MCP tools
- Quiz-based assessment: Over-engineered for a single learner

## Decision 2: Claude Desktop Project vs Paste-In Prompt

**Decision**: Use a Claude Desktop Project with CLAUDE.md in the `guide/` directory. Jordan points Claude Desktop to the `guide/` folder as a Project.

**Rationale**: Projects persist context across conversations, auto-load the CLAUDE.md, and can read the lesson files directly. This means Claude can reference lesson content when Jordan asks questions. A paste-in prompt would lose context between conversations and can't reference files.

**Alternatives considered**:
- Paste-in system prompt: Fragile, loses context, can't read lesson files
- Embedded per-lesson prompts: Redundant, no cross-lesson awareness
- MCP-based prompt delivery: Over-engineered, adds code complexity

## Decision 3: Seed Data as Exercise Anchor

**Decision**: Lessons reference specific seed data clients by name (e.g., "Find Janet Morales") so exercises produce predictable, verifiable results.

**Rationale**: Using named clients from the seed data means the MCP verification step returns expected results. If Jordan searches for "Janet Morales" and Claude confirms she exists with specific attributes, Jordan knows his manual search worked correctly.

**Alternatives considered**:
- Generic exercises ("find any client"): Can't verify specific results
- Jordan creates his own test data: Unpredictable, harder to write verification steps
- Randomized exercises: Adds code complexity, defeats the content-only goal

## Decision 4: Transferable CRM Concepts

**Decision**: Each lesson starts with a "CRM Concept" section explaining the universal idea before the Salesforce-specific steps.

**Rationale**: Jordan works at Schwab, which uses proprietary tools. The goal is transferable CRM thinking — understanding what Contacts, Tasks, List Views, and Reports are conceptually — not just Salesforce muscle memory. This makes the guide valuable even if Jordan never uses Salesforce professionally.

**Alternatives considered**:
- Salesforce-only instructions: Limits transferability
- Multi-CRM comparison: Too broad, adds complexity without clear benefit for single learner

## Decision 5: Guide Directory Location

**Decision**: Place lessons in a top-level `guide/` directory at the repository root.

**Rationale**: Keeps content separate from `src/` (application code) and `specs/` (feature specifications). The `guide/` directory doubles as the Claude Desktop Project root — Jordan points Claude Desktop here and gets both the CLAUDE.md tutor context and access to all lesson files.

**Alternatives considered**:
- `docs/guide/`: Extra nesting, less discoverable
- `specs/024-sfdc-learning-guide/lessons/`: Mixes ephemeral spec artifacts with permanent content
- Repository root (flat): Clutters the root with 7+ markdown files
