# Data Model: Client List Builder

**Feature**: 020-client-list-builder | **Date**: 2026-03-09

## Entities

### CompoundFilter

A structured representation of a multi-dimensional client query. Used by all three user stories.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| min_age | int or null | No | Minimum age (inclusive) |
| max_age | int or null | No | Maximum age (inclusive) |
| min_value | float or null | No | Minimum account value (inclusive) |
| max_value | float or null | No | Maximum account value (inclusive) |
| risk_tolerances | list of string | No | One or more values from: conservative, moderate, growth, aggressive. OR within dimension. |
| life_stages | list of string | No | One or more values from: accumulation, pre-retirement, retirement, legacy. OR within dimension. |
| not_contacted_days | int or null | No | Recency filter: clients whose last interaction was more than N days ago (or never contacted) |
| contacted_after | date string or null | No | Absolute date range start: last interaction on or after this date |
| contacted_before | date string or null | No | Absolute date range end: last interaction on or before this date |
| search | string or null | No | Free-text search across name and notes |
| sort_by | string | No | Sort field. One of: account_value (default), age, last_name, last_interaction_date |
| sort_dir | string | No | Sort direction: desc (default) or asc |
| limit | int | No | Maximum results to return. Default: 50 |

**Validation rules**:
- `min_age` must be >= 0 and <= 120 if provided
- `max_age` must be >= `min_age` if both provided
- `min_value` must be >= 0 if provided
- `max_value` must be >= `min_value` if both provided
- `risk_tolerances` values must be from the allowed set
- `life_stages` values must be from the allowed set
- `not_contacted_days` must be > 0 if provided
- `contacted_after` and `contacted_before`: `contacted_after` must be <= `contacted_before` if both provided
- `not_contacted_days` and `contacted_after`/`contacted_before` are mutually exclusive (recency vs absolute range)
- `sort_by` must be from the allowed set
- `sort_dir` must be "asc" or "desc"
- `limit` must be > 0

### SavedList

A named, persisted filter definition. Stored locally as JSON.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Unique identifier for the list. Case-insensitive uniqueness. |
| description | string | No | Human-readable description of the list's purpose |
| filters | CompoundFilter | Yes | The filter criteria to execute when the list is run |
| created_at | datetime string | Yes | ISO 8601 timestamp of when the list was created |
| last_run_at | datetime string or null | No | ISO 8601 timestamp of when the list was last executed |

**Identity**: Name is the unique key (case-insensitive). Two lists cannot have the same name (ignoring case).

**Lifecycle**: Created → (Run)* → Updated? → Deleted. No complex state machine.

### QueryInterpretation

The result of translating a natural language string into a CompoundFilter.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| original_query | string | Yes | The raw natural language input from the user |
| filters | CompoundFilter | Yes | The parsed filter criteria |
| filter_mapping | dict (string → string) | Yes | Maps each NL phrase to the filter it produced (e.g., "under 50" → "max_age: 50") |
| unrecognized | list of string | No | Parts of the NL query that couldn't be mapped to filters |
| confidence | string | Yes | "high" (all phrases mapped), "medium" (some unmapped), "low" (significant ambiguity) |

## Relationships

```
CompoundFilter ──(embedded in)──> SavedList.filters
CompoundFilter ──(produced by)──> QueryInterpretation.filters
QueryInterpretation ──(translates)──> natural language string
SavedList ──(executes against)──> Salesforce Contact + Task objects
```

## No New Salesforce Objects or Fields

This feature does NOT modify the Salesforce schema. It uses the existing Contact fields (including `LastActivityDate` standard field) and Task objects deployed in 019-sfdc-sandbox. All new data structures (CompoundFilter, SavedList, QueryInterpretation) are local to the tool.
