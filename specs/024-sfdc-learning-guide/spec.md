# Feature Specification: Salesforce Learning Guide

**Feature Branch**: `024-sfdc-learning-guide`
**Created**: 2026-03-09
**Status**: Draft
**Input**: User description: "Build an interactive Salesforce learning guide for Jordan McElroy (financial consultant, new to Salesforce) as a series of markdown lessons in the repo. Each lesson teaches a Salesforce concept by having Jordan do it manually in the sandbox first, then verify using advisor-agent MCP tools in Claude Desktop."

## Context

Jordan McElroy is a Financial Consultant at Charles Schwab who uses Schwab's proprietary tools day-to-day but wants to build transferable CRM skills. The Salesforce developer sandbox provides a safe learning environment with 50 synthetic client profiles. The advisor-agent MCP tools in Claude Desktop serve as an interactive "answer key" — Jordan performs actions manually in Salesforce, then asks Claude to verify the results or compare approaches.

This is a **content feature** — the deliverable is a set of structured lesson files and a custom Claude prompt, not application code.

## Clarifications

### Session 2026-03-09

- Q: How should Jordan load the tutor prompt into Claude Desktop? → A: A Claude Desktop Project with a CLAUDE.md that auto-loads the tutor instructions

## User Scenarios & Testing

### User Story 1 - Self-Paced Lesson Walkthrough (Priority: P1)

Jordan opens a lesson file in the repo, reads the objective, performs the described task manually in the Salesforce sandbox, then asks Claude Desktop to verify his work using the MCP tools.

**Why this priority**: The core learning loop — manual practice with AI verification — is the fundamental value proposition. Without this, no other feature matters.

**Independent Test**: Jordan can open Lesson 1 (Navigating Contacts), find a specific client in Salesforce, then ask Claude "Show me the details for client Janet Morales" and compare the results to what he sees on screen.

**Acceptance Scenarios**:

1. **Given** Jordan opens a lesson markdown file, **When** he reads the lesson objective and instructions, **Then** each step is clear enough to follow without additional explanation
2. **Given** Jordan completes a manual task in Salesforce (e.g., creates a task for a contact), **When** he asks Claude Desktop to verify (e.g., "Show me open tasks for Janet Morales"), **Then** the MCP tool output confirms his manual action succeeded
3. **Given** Jordan makes an error in Salesforce (e.g., sets wrong priority on a task), **When** he asks Claude to check his work, **Then** the discrepancy is visible in the MCP tool output so he can correct it

---

### User Story 2 - Custom Claude Tutor Prompt (Priority: P2)

Jordan opens a Claude Desktop Project that has a CLAUDE.md file with tutor instructions. The project auto-loads the Salesforce curriculum context and connects to the advisor-agent MCP tools. He can ask questions like "What should I do next in Lesson 3?" or "How do I create a report in Salesforce?" and get contextual guidance without pasting any prompts.

**Why this priority**: The Claude Desktop Project turns Claude from a generic assistant into a personalized Salesforce coach with persistent context. It adds significant value but depends on the lessons (US1) existing first.

**Independent Test**: Jordan opens the Claude Desktop Project, asks "What lessons are available?" and gets an accurate list. He asks "Help me with Lesson 2" and gets step-by-step guidance referencing the actual sandbox data.

**Acceptance Scenarios**:

1. **Given** Jordan has the tutor prompt loaded in Claude Desktop, **When** he asks "What lessons are available?", **Then** Claude lists all lessons with brief descriptions
2. **Given** Jordan is working on a lesson, **When** he asks "Can you check if I did this right?", **Then** Claude uses the appropriate MCP tool to verify and provides feedback
3. **Given** Jordan is stuck on a Salesforce concept, **When** he asks a question like "How do list views work?", **Then** Claude explains the concept and ties it back to the current lesson's exercise

---

### User Story 3 - Progressive Skill Building (Priority: P3)

Jordan works through lessons in order, building from basic navigation to advanced concepts like reports and list views. Each lesson builds on skills from previous lessons and introduces one new Salesforce concept.

**Why this priority**: Lesson sequencing and progressive difficulty make the guide a coherent curriculum rather than a random collection of exercises. Important for long-term retention but the individual lessons (US1) work standalone.

**Independent Test**: Jordan completes Lessons 1-3 in order and can perform Lesson 3's exercises (creating filtered list views) without referring back to earlier lessons for basic navigation steps.

**Acceptance Scenarios**:

1. **Given** Jordan has completed Lesson 1 (Contacts), **When** he starts Lesson 2 (Tasks), **Then** the lesson references skills from Lesson 1 but focuses on the new concept
2. **Given** Jordan has completed all lessons, **When** he encounters a new CRM platform, **Then** the concepts learned (contacts, tasks, reports, list views, dashboards) transfer directly because the guide teaches CRM thinking, not just Salesforce button-clicking

---

### Edge Cases

- What happens when sandbox data has been modified or deleted since the lessons were written? Lessons should reference the seed data tool so Jordan can reset if needed.
- What happens when Jordan skips ahead to a later lesson? Each lesson should list prerequisites and be self-contained enough to attempt independently.
- What happens when Salesforce UI changes? Lessons should describe actions by concept ("find the contact's activity timeline") rather than exact UI element locations.

## Requirements

### Functional Requirements

- **FR-001**: The guide MUST include at least 5 progressive lessons covering: contact navigation, task management, client search/filtering, list views, and reports
- **FR-002**: Each lesson MUST follow a consistent structure: objective, prerequisite skills, manual exercise steps, MCP verification steps, and key takeaways
- **FR-003**: Each lesson MUST include at least one "do it manually, then verify with Claude" exercise that uses a specific MCP tool
- **FR-004**: The guide MUST include a Claude Desktop Project with a CLAUDE.md file that auto-loads Salesforce tutoring context and lesson curriculum awareness
- **FR-005**: The CLAUDE.md MUST instruct Claude to use MCP tools proactively when verifying Jordan's work or demonstrating concepts
- **FR-006**: Lessons MUST reference the existing sandbox seed data (50 synthetic clients) by name so exercises produce predictable, verifiable results
- **FR-007**: The guide MUST include a "Getting Started" section explaining how to access the Salesforce sandbox, connect Claude Desktop, and reset seed data if needed
- **FR-008**: Lessons MUST teach transferable CRM concepts (not just Salesforce-specific UI steps) by explaining the "why" behind each action
- **FR-009**: Each lesson MUST include a "Challenge" section with an unguided exercise for Jordan to attempt independently before checking with Claude
- **FR-010**: The guide MUST be organized as markdown files in a dedicated directory within the repository

### Key Entities

- **Lesson**: A structured markdown document teaching one Salesforce concept, with manual exercises and MCP verification steps
- **Tutor Project**: A Claude Desktop Project with a CLAUDE.md file that provides persistent Salesforce tutoring context across conversations
- **Sandbox Data**: The 50 synthetic client profiles and their interaction history used as exercise data

## Success Criteria

### Measurable Outcomes

- **SC-001**: Jordan can complete each lesson's core exercise in under 15 minutes (excluding the first lesson which includes setup)
- **SC-002**: 100% of lesson exercises have a corresponding MCP verification step that confirms success or reveals errors
- **SC-003**: The guide covers at least 5 distinct Salesforce concepts in progressive difficulty order
- **SC-004**: Jordan can explain what a Contact, Task, List View, and Report are and when to use each after completing the guide
- **SC-005**: The custom tutor prompt enables Jordan to get contextual help without leaving Claude Desktop

## Assumptions

- Jordan has access to the Salesforce developer sandbox and Claude Desktop with the advisor-agent MCP server connected
- The sandbox contains seed data (50 synthetic clients with interaction history) or can be re-seeded via the MCP tool
- Jordan has basic computer literacy and can follow markdown-formatted instructions
- The Salesforce Lightning UI is the target interface (not Classic)
- Lessons are written for self-paced individual learning, not instructor-led training

## Out of Scope

- Video tutorials or screen recordings
- Salesforce admin/developer concepts (Apex, Flows, custom objects)
- Schwab-specific tool training (Schwab Advisor Center, StreetSmart Edge)
- Automated lesson progress tracking or quizzing
- Mobile Salesforce app instructions
