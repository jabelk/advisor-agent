# Research: Client List Builder

**Feature**: 020-client-list-builder | **Date**: 2026-03-09

## R1: Compound SOQL Query Construction

**Decision**: Build SOQL WHERE clauses dynamically from a Pydantic `CompoundFilter` model. Each filter dimension appends a condition string. Multi-value dimensions (risk_tolerance, life_stage) use `IN ('val1','val2')` syntax.

**Rationale**: SOQL supports all the filter patterns we need natively: range comparisons (`Age__c < 50`), IN lists (`Risk_Tolerance__c IN ('growth','aggressive')`), LIKE for text search, and NULLS LAST for sort ordering. Building SOQL dynamically from a structured filter model is the same pattern already used in `list_clients()` — we're extending it, not replacing it.

**Key SOQL patterns**:
- Age range: `Age__c >= :min AND Age__c <= :max`
- Multi-value: `Risk_Tolerance__c IN ('growth','aggressive')`
- Recency: `LastActivityDate < :date OR LastActivityDate = null` (for "not contacted in N days")
- Absolute date range: `LastActivityDate >= :start AND LastActivityDate <= :end`
- Sort: `ORDER BY Age__c ASC NULLS LAST`
- Limit: `LIMIT 50`

**Alternatives considered**:
- **Post-query filtering in Python**: Unnecessary — SOQL can handle all these filters server-side. Would fetch more data than needed.
- **Salesforce Reports API**: Over-engineered for programmatic filtering. Reports are a UI feature.

## R2: Last Interaction Date — SOQL Approach

**Decision**: Use Salesforce's standard `LastActivityDate` field on Contact for interaction date filtering and sorting. Fall back to a relationship subquery if `LastActivityDate` is not available in the org.

**Rationale**: `LastActivityDate` is a standard Salesforce rollup field automatically maintained when Tasks (or Events) are associated with a Contact via `WhoId`. It's queryable in SOQL WHERE and ORDER BY clauses directly, which is far simpler than subquery-based approaches. The current `list_clients()` already uses a subquery for display purposes — for filtering, `LastActivityDate` is more efficient.

**Implementation**:
- Check if `LastActivityDate` is available via `Contact.describe()` (cache this check)
- If available: use directly in WHERE and ORDER BY clauses
- If not available: use two-step approach — query Tasks first to get matching Contact IDs, then query Contacts
- For display: continue using the existing subquery `(SELECT ActivityDate FROM Tasks ORDER BY ActivityDate DESC LIMIT 1)` since it provides the actual date value

**Alternatives considered**:
- **Custom formula field**: Would require deploying another custom field. Unnecessary since `LastActivityDate` is standard.
- **Always subquery**: SOQL doesn't support filtering on subquery results in WHERE clauses. Would require fetching all contacts then filtering in Python — inefficient.

## R3: Saved List Persistence

**Decision**: Local JSON file at a configurable path (default: `~/.advisor-agent/saved_lists.json`). Each saved list is a JSON object with name, description, filter criteria (serialized CompoundFilter), and metadata.

**Rationale**: Saved lists are a tool feature, not CRM data — they don't belong in Salesforce. A JSON file is the simplest persistence mechanism: no migrations, no schema, human-readable, easily backed up. The number of saved lists is small (<50), so performance isn't a concern. JSON serialization of Pydantic models is trivial.

**File format**:
```json
{
  "lists": {
    "Top 50 Under 50": {
      "name": "Top 50 Under 50",
      "description": "High-value clients under age 50",
      "filters": { "max_age": 50, "sort_by": "account_value", "sort_dir": "desc", "limit": 50 },
      "created_at": "2026-03-09T10:00:00",
      "last_run_at": "2026-03-09T14:30:00"
    }
  }
}
```

**Alternatives considered**:
- **SQLite table**: More infrastructure than needed for ~50 records. Would require a new migration. The research SQLite DB is for research signals, not tool config.
- **Salesforce custom object**: Over-engineered. Saved lists are local to this tool, not CRM data.
- **YAML/TOML**: No advantage over JSON for this use case. JSON has native Pydantic support.

## R4: Natural Language → Filter Translation

**Decision**: Single Claude API call per NL query. System prompt defines the CompoundFilter schema and valid field values. User message contains the natural language query. Claude returns structured JSON matching the filter schema. Pydantic validates the response.

**Rationale**: Follows the existing pattern in meeting_prep.py and commentary.py — structured system prompt + user message → JSON response. Claude is excellent at intent extraction from natural language. Using Pydantic's JSON schema as the response format ensures type safety and catches malformed responses.

**Implementation**:
- System prompt: defines all filter dimensions, valid values for enums (risk_tolerance, life_stage), sort fields, and provides 5-10 example translations
- User message: the raw natural language query
- Response: JSON matching CompoundFilter schema + a `filter_mapping` dict showing NL phrase → filter applied
- Model: claude-sonnet-4-5-20250929 (fast, cost-effective for structured extraction)
- Confidence: if Claude can't map a phrase, it includes it in an `unrecognized` list

**Alternatives considered**:
- **Regex/rule-based parsing**: Brittle — would need rules for every phrasing variant. "Under 50," "younger than 50," "below age 50," "not yet 50" all mean the same thing.
- **Fine-tuned model**: Over-engineered. General Claude with good prompting handles this well.
- **Multi-turn confirmation**: Only needed for ambiguous queries (FR-012). Most queries should resolve in a single call.

## R5: Backward Compatibility with Existing list_clients()

**Decision**: Extend the existing `list_clients()` signature with new optional parameters rather than creating a separate function. The existing parameters continue to work unchanged.

**Rationale**: The current `list_clients(sf, risk_tolerance, life_stage, min_value, max_value, search, limit, offset)` already handles basic filtering. Adding `min_age`, `max_age`, `risk_tolerances` (list), `life_stages` (list), `not_contacted_days`, `contacted_after`, `contacted_before`, `sort_by`, `sort_dir` as additional optional parameters preserves backward compatibility. Callers that pass single `risk_tolerance` still work. The function internally builds SOQL from whichever parameters are provided.

**Alternatives considered**:
- **New function `query_clients()`**: Creates confusion about which function to use. Existing callers would need updating.
- **Filter object parameter**: Could pass a CompoundFilter model directly, but this breaks the existing simple parameter interface. Better to have a helper that converts CompoundFilter → function kwargs.
