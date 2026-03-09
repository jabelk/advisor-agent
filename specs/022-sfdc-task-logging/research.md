# Research: Tasks & Activity Logging

**Branch**: `022-sfdc-task-logging` | **Date**: 2026-03-09

## No Critical Unknowns

All technical questions were resolved by examining the existing codebase. No external research needed.

## Decisions

### 1. Salesforce Task Object Field Usage

**Decision**: Use standard Task fields — no custom fields needed.
**Rationale**: The Task standard object provides all required fields: Subject, WhoId, ActivityDate, Status, Priority, Description, TaskSubtype, CompletedDateTime. Unlike Contact (which needed custom fields like Age__c), Task's standard fields cover our use case completely.
**Alternatives considered**: Creating custom fields on Task (rejected — unnecessary complexity, standard fields sufficient).

### 2. Task Creation Pattern

**Decision**: Use `sf.Task.create(data)` via simple_salesforce (same as existing `add_interaction()`).
**Rationale**: Already proven in `storage.py:add_interaction()`. Returns `{"id": "00Txx..."}`.
**Alternatives considered**: Bulk API (rejected — we create tasks one at a time or in small batches for outreach).

### 3. Outreach Queue — Last Activity Detection

**Decision**: Use SOQL subquery `(SELECT ActivityDate FROM Tasks ORDER BY ActivityDate DESC LIMIT 1)` on Contact, same pattern as `list_clients()`.
**Rationale**: Already working in `storage.py:list_clients()` for `last_interaction_date`. Contact also has `LastActivityDate` standard field but the subquery gives more control.
**Alternatives considered**: Using Contact.LastActivityDate field directly (viable fallback, but subquery already works).

### 4. Contact Name Resolution

**Decision**: SOQL `WHERE FirstName LIKE '%name%' OR LastName LIKE '%name%'` with `_soql_escape()`.
**Rationale**: Consistent with existing fuzzy search patterns. Handles partial names and is case-insensitive in SOQL by default.
**Alternatives considered**: SOSL full-text search (rejected — overkill for name lookup in a sandbox with ~50 contacts).

### 5. [advisor-agent] Tag Placement

**Decision**: Prefix the Description field with `[advisor-agent]`, same pattern as Reports (FR-010).
**Rationale**: Description field is large (32,000 chars), rarely displayed in UI by default, and can hold both the tag and any user-provided notes. Consistent with `sfdc_report.py` which uses `ADVISOR_AGENT_TAG` in report descriptions.
**Alternatives considered**: Using a custom field (rejected — adds deployment complexity). Using Subject prefix (rejected — pollutes the user-facing field).
