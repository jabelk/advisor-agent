# Data Model: Tasks & Activity Logging

**Branch**: `022-sfdc-task-logging` | **Date**: 2026-03-09

## Entities

### Task (Salesforce Standard Object)

Used for both forward-looking follow-up tasks and backward-looking activity logs. No custom fields needed.

| Field | API Name | Type | Description | Used By |
|-------|----------|------|-------------|---------|
| ID | `Id` | String(18) | Salesforce record ID | All operations |
| Subject | `Subject` | String(255) | Task title / activity summary | US1, US2, US3 |
| Who | `WhoId` | Reference(Contact) | Link to Contact record | US1, US2, US3, US4 |
| Due Date | `ActivityDate` | Date | Due date (tasks) or activity date (logs) | US1, US2, US3 |
| Status | `Status` | Picklist | "Not Started" or "Completed" | US1, US2, US3 |
| Priority | `Priority` | Picklist | "High", "Normal", "Low" | US1, US2 |
| Description | `Description` | TextArea(32000) | "[advisor-agent]" tag + optional notes | All (tagging) |
| Subtype | `TaskSubtype` | Picklist | "Call", "Email", or null | US3 |
| Completed Date | `CompletedDateTime` | DateTime | Auto-set when Status → Completed | US2 |
| Owner | `OwnerId` | Reference(User) | Defaults to current user | US2, US4 |
| Created Date | `CreatedDate` | DateTime | System field (auto) | Display only |

### Contact (Existing — from 019-sfdc-sandbox)

No changes. Referenced by Task.WhoId.

| Field | API Name | Used By (this feature) |
|-------|----------|----------------------|
| ID | `Id` | Task.WhoId lookup |
| First Name | `FirstName` | Name resolution (FR-002) |
| Last Name | `LastName` | Name resolution (FR-002) |
| Account Value | `Account_Value__c` | Outreach queue sorting (US4) |
| Last Activity | `LastActivityDate` | Outreach queue filtering (US4) |

### Outreach Queue (Derived — not persisted)

Computed at query time. Result of cross-referencing Contact with Task activity history.

| Field | Source | Description |
|-------|--------|-------------|
| Contact ID | Contact.Id | Salesforce ID |
| Name | Contact.FirstName + LastName | Display name |
| Account Value | Contact.Account_Value__c | For sorting (highest first) |
| Last Activity Date | Task subquery or Contact.LastActivityDate | Most recent activity |
| Days Since Contact | Computed | Today - Last Activity Date |
| Has Open Task | Task subquery | Whether an open [advisor-agent] task exists (for dedup) |

## Relationships

```text
Contact (1) ──────< Task (many)
   │                    │
   │  WhoId             │  Status: "Not Started" → Follow-up task
   │                    │  Status: "Completed"   → Activity log
   │                    │
   └── LastActivityDate │  (auto-computed by Salesforce)
```

## State Transitions

### Task Lifecycle

```text
[Created] ──→ Not Started ──→ Completed
                 │                  │
                 │ (via CLI/MCP     │ (sets CompletedDateTime)
                 │  "complete")     │
                 └──────────────────┘
```

### Activity Log (no transitions)

```text
[Created] ──→ Completed (created in final state)
```

## Validation Rules

| Rule | Applies To | Description |
|------|-----------|-------------|
| WhoId required | Task create | Must link to a valid Contact |
| Subject required | Task create | Non-empty string |
| ActivityDate not future | Activity log | Reject if date > today |
| ActivityDate defaults | Task create | Today + 7 days if not specified |
| Priority defaults | Task create | "Normal" if not specified |
| Type must be valid | Activity log | One of: call, meeting, email, other |
| Description tagged | All creates | Must contain "[advisor-agent]" prefix |

## Type Mapping (Activity Log --type → TaskSubtype)

| CLI --type | Salesforce TaskSubtype | Notes |
|------------|----------------------|-------|
| call | "Call" | Standard Salesforce value |
| email | "Email" | Standard Salesforce value |
| meeting | null | Salesforce has no "Meeting" subtype; use null |
| other | null | Generic fallback |
