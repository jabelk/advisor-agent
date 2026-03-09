# Feature Specification: Tasks & Activity Logging

**Feature Branch**: `022-sfdc-task-logging`
**Created**: 2026-03-09
**Status**: Draft
**Input**: User description: "#1 (Tasks & Activity Logging)"

## Overview

Financial consultants lose significant revenue from inconsistent client follow-ups. Jordan needs a way to create follow-up tasks, log completed activities (calls, meetings, emails), view upcoming and overdue tasks, and generate an outreach queue of high-value clients who haven't been contacted recently — all using Salesforce-native Task objects in his developer sandbox.

This feature builds on the existing Salesforce sandbox infrastructure (019) and client list/report capabilities (020/021) by adding activity tracking through Salesforce's standard Task object. All data lives in Salesforce — no local storage.

## Clarifications

### Session 2026-03-09

- Q: How should Jordan identify a task to mark it complete? → A: Subject-based fuzzy match (case-insensitive partial match on task subject text)
- Q: Should task/activity operations be exposed as MCP tools for Claude Desktop? → A: Yes — expose all operations (create, show, complete, log, outreach) as MCP tools
- Q: What activities count when determining "last contacted" for outreach queue? → A: All activities — any Task/Event on the Contact, regardless of creation source

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create Follow-Up Tasks (Priority: P1)

As a financial consultant, Jordan wants to quickly create follow-up tasks for specific clients so he never forgets to reach out after meetings, market events, or life changes.

**Why this priority**: Task creation is the foundational action — without it, nothing else in this feature works. A single CLI command to create a Salesforce Task eliminates the friction of navigating the Salesforce UI for routine follow-ups.

**Independent Test**: Can be fully tested by creating a task for a sandbox contact and verifying it appears in Salesforce. Delivers immediate value as a standalone productivity shortcut.

**Acceptance Scenarios**:

1. **Given** a valid sandbox contact, **When** Jordan runs `sandbox tasks create --client "Jane Doe" --subject "Review portfolio allocation" --due 2026-03-15`, **Then** a Salesforce Task is created linked to that contact with status "Not Started", the specified subject, and due date.
2. **Given** a valid sandbox contact, **When** Jordan runs `sandbox tasks create --client "Jane Doe" --subject "Quick check-in" --due 2026-03-20 --priority High`, **Then** a Salesforce Task is created with High priority.
3. **Given** a contact name that matches multiple contacts, **When** Jordan runs the create command, **Then** the system displays matching contacts and asks for clarification.
4. **Given** a contact name that matches no contacts, **When** Jordan runs the create command, **Then** the system displays a clear "not found" message.
5. **Given** no --due flag is provided, **When** Jordan runs the create command, **Then** the task is created with a default due date of 7 days from today.

---

### User Story 2 - View and Manage Tasks (Priority: P2)

As a financial consultant, Jordan wants to see his upcoming and overdue tasks, filter by client or status, and mark tasks complete — so he can manage his daily workflow from the CLI without switching to the Salesforce UI.

**Why this priority**: Viewing and completing tasks is the natural follow-on to creating them. Without this, Jordan would still need to open Salesforce to check his task list, reducing the value of task creation.

**Independent Test**: Can be tested by creating several tasks (via US1), then listing/filtering/completing them. Delivers value as a personal task dashboard.

**Acceptance Scenarios**:

1. **Given** Jordan has open tasks in Salesforce, **When** he runs `sandbox tasks show`, **Then** he sees a table of all open tasks sorted by due date with columns: Subject, Client, Due Date, Priority, Status.
2. **Given** Jordan has overdue tasks, **When** he runs `sandbox tasks show --overdue`, **Then** only tasks with due dates before today are shown.
3. **Given** Jordan wants tasks for a specific client, **When** he runs `sandbox tasks show --client "Jane Doe"`, **Then** only tasks linked to that contact are shown.
4. **Given** Jordan has completed a follow-up, **When** he runs `sandbox tasks complete "Review portfolio"`, **Then** the system fuzzy-matches the subject (case-insensitive partial match), updates the matching Salesforce Task status to "Completed", and sets the completion date. If multiple tasks match, the system displays them and asks for clarification.
5. **Given** Jordan wants a quick summary, **When** he runs `sandbox tasks show --summary`, **Then** he sees counts: total open, overdue, due this week, due today.

---

### User Story 3 - Log Completed Activities (Priority: P3)

As a financial consultant, Jordan wants to log activities he has already completed (phone calls, meetings, emails) so his Salesforce activity history stays current and he can demonstrate consistent client engagement.

**Why this priority**: Activity logging is backward-looking (recording what happened) vs. task creation which is forward-looking (planning what to do). Both are essential for a complete activity picture, but creating future tasks is more immediately actionable.

**Independent Test**: Can be tested by logging an activity for a sandbox contact and verifying it appears in the contact's Salesforce activity history. Delivers value as a quick activity recorder.

**Acceptance Scenarios**:

1. **Given** a valid sandbox contact, **When** Jordan runs `sandbox log --client "Jane Doe" --subject "Discussed retirement timeline" --type call`, **Then** a completed Salesforce Task is created linked to that contact with the appropriate TaskSubtype and today's date.
2. **Given** a valid contact, **When** Jordan runs `sandbox log --client "Jane Doe" --subject "Annual review" --type meeting --date 2026-03-07`, **Then** the activity is logged with the specified past date.
3. **Given** an invalid --type value, **When** Jordan runs the log command, **Then** the system displays valid type options: call, meeting, email, other.

---

### User Story 4 - Outreach Queue (Priority: P4)

As a financial consultant, Jordan wants to generate a prioritized outreach list of high-value clients who haven't been contacted recently, and optionally auto-create follow-up tasks for them — so he can proactively maintain client relationships.

**Why this priority**: This is the most advanced story, combining list-building logic (from 020/021) with task creation (US1). It delivers high value but depends on the other stories being solid first.

**Independent Test**: Can be tested by running the outreach command against sandbox contacts with varying last activity dates. Delivers value as an automated "who should I call?" generator.

**Acceptance Scenarios**:

1. **Given** sandbox contacts with varying last activity dates, **When** Jordan runs `sandbox outreach --days 90`, **Then** he sees a list of contacts not contacted in 90+ days, sorted by account value (highest first).
2. **Given** an outreach list, **When** Jordan runs `sandbox outreach --days 90 --min-value 250000`, **Then** only contacts with account value >= $250,000 and no activity in 90+ days are shown.
3. **Given** an outreach list, **When** Jordan runs `sandbox outreach --days 90 --create-tasks`, **Then** a follow-up task is created for each contact in the list with subject "Follow-up: No contact in 90+ days" and due date of today.
4. **Given** a contact already has an open task, **When** --create-tasks would create a duplicate, **Then** the system skips that contact and notes it was skipped.

---

### Edge Cases

- What happens when a task is created for a contact that is subsequently deleted from Salesforce? The task remains orphaned — show gracefully in listings (display "Unknown Contact" if WhoId lookup fails).
- How does the system handle Salesforce API rate limits? Display a clear error message with retry guidance; do not silently fail.
- What happens when --days 0 is passed to outreach? Treat as "all contacts regardless of last activity" — equivalent to no activity filter.
- What happens when a task ID passed to `complete` doesn't exist or is already completed? Display appropriate message: "Task not found" or "Task already completed."
- What happens when --date is in the future for activity logging? Reject with message: "Activity date cannot be in the future."

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create Salesforce Task objects linked to Contact records via the WhoId field.
- **FR-002**: System MUST resolve client names to Contact IDs using fuzzy matching (case-insensitive, partial name match via SOQL LIKE).
- **FR-003**: System MUST support task priorities: High, Normal (default), Low — mapped to Salesforce Task.Priority values.
- **FR-004**: System MUST default new task due dates to 7 calendar days from creation when --due is not specified.
- **FR-005**: System MUST resolve task subjects using fuzzy matching (case-insensitive partial match via SOQL LIKE) when marking tasks complete, displaying disambiguation options when multiple tasks match. System MUST then update Task.Status to "Completed" and set CompletedDateTime.
- **FR-006**: System MUST create completed Task records for activity logging with appropriate TaskSubtype values (Call, Email, or null for meeting/other).
- **FR-007**: System MUST query open tasks using SOQL filtered by OwnerId (current user), with optional filters for WhoId (client), Status, and ActivityDate.
- **FR-008**: System MUST generate outreach queues by cross-referencing Contact.Account_Value__c with the last activity date from ALL Task and Event records on the Contact (regardless of creation source), not just [advisor-agent]-tagged tasks.
- **FR-009**: System MUST prevent duplicate task creation in outreach mode by checking for existing open tasks on each contact before creating new ones.
- **FR-010**: System MUST tag all tool-created tasks with a description prefix "[advisor-agent]" to distinguish them from manually-created tasks.
- **FR-011**: System MUST expose all task and activity operations (create task, show tasks, complete task, log activity, outreach queue) as MCP tools for Claude Desktop, following the pattern established in features 019 and 021.

### Key Entities

- **Task (Salesforce Standard Object)**: Represents a follow-up action or logged activity. Key fields: Subject, WhoId (Contact link), ActivityDate (due date), Status (Not Started, Completed), Priority (High, Normal, Low), Description, TaskSubtype (Call, Email, null), CompletedDateTime.
- **Contact (Existing)**: The client the task is associated with. Already exists from 019-sfdc-sandbox. Linked via WhoId on Task.
- **Outreach Queue (Derived)**: Not a persisted entity — computed at query time by joining Contact data with Task activity history.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Jordan can create a follow-up task for any sandbox client in under 10 seconds via a single CLI command.
- **SC-002**: Jordan can view all overdue tasks and complete them without opening the Salesforce UI.
- **SC-003**: Activity logs created via CLI appear correctly in the Salesforce contact activity timeline.
- **SC-004**: Outreach queue accurately identifies clients with no activity in the specified timeframe, with zero false negatives.
- **SC-005**: All tool-created tasks are identifiable via the [advisor-agent] tag and do not interfere with manually-created tasks.

## Assumptions

- Jordan's Salesforce developer sandbox has the standard Task object available (it is a standard object, so this is guaranteed).
- The existing Salesforce connection infrastructure from 019-sfdc-sandbox provides authenticated access.
- Custom fields on Contact (Age__c, Account_Value__c, Risk_Tolerance__c, Life_Stage__c) are already deployed from previous features.
- Task.OwnerId defaults to the connected user — no multi-user support needed for the sandbox.
- The CLI subcommand structure follows the existing `sandbox` command pattern established in 020/021.
