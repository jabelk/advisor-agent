# Research: Salesforce-Native List Views & Reports

**Feature**: 021-sfdc-native-lists | **Date**: 2026-03-09

## R1: Salesforce List View CRUD via Metadata API

**Decision**: Use `simple_salesforce` Metadata API (`sf.mdapi`) for ListView CRUD operations.

**Rationale**: The Metadata API provides full CRUD on ListView metadata. The existing `simple_salesforce` library already supports `sf.mdapi` — no new dependencies required. The Tooling API was also considered but it has read-only access for ListViews in most contexts.

**Alternatives considered**:
- Tooling API (`sf.restful("tooling/sobjects/ListView")`) — read-only for ListViews, not suitable for create/update
- REST API — no native ListView CRUD endpoint; only query via `/services/data/vXX.0/sobjects/ListView`

**Key findings**:

1. **ListView Metadata Structure** (Metadata API):
   ```python
   sf.mdapi.ListView.create({
       "fullName": "Contact.AA_My_List_Name",  # Object.DeveloperName
       "label": "AA: My List Name",             # Display name
       "filterScope": "Everything",
       "columns": ["FULL_NAME", "CONTACT_EMAIL", ...],
       "filters": [
           {"field": "Age__c", "operation": "greaterOrEqual", "value": "30"},
           {"field": "Risk_Tolerance__c", "operation": "equals", "value": "growth,aggressive"},
       ],
   })
   ```

2. **NO description field on ListView** — This contradicts the spec clarification that suggested using `[advisor-agent]` description tags for ListView identification. ListViews have only: `fullName`, `label`, `filterScope`, `columns`, `filters`, `language`, `queue`, `sharedTo`, `booleanFilter`.

3. **Identification strategy for ListViews**: Use `DeveloperName` prefix `AA_` as the sole programmatic identifier. The `label` gets `AA:` prefix for visual identification. Query: `sf.mdapi.ListView.read("Contact.AA_*")` or SOQL: `SELECT Id, DeveloperName, Name FROM ListView WHERE SobjectType = 'Contact' AND DeveloperName LIKE 'AA_%'`.

4. **Supported filter operations**:
   | Operation | SOQL equivalent | Use for |
   |-----------|----------------|---------|
   | `equals` | `=` | Single value match |
   | `notEqual` | `!=` | Exclusion |
   | `lessThan` | `<` | Range upper bound (exclusive) |
   | `greaterThan` | `>` | Range lower bound (exclusive) |
   | `lessOrEqual` | `<=` | Range upper bound (inclusive) |
   | `greaterOrEqual` | `>=` | Range lower bound (inclusive) |
   | `contains` | `LIKE '%x%'` | Text search |

5. **Multi-value filters**: For `IN` clauses (risk_tolerances, life_stages), use comma-separated values with `equals` operation: `{"field": "Risk_Tolerance__c", "operation": "equals", "value": "growth,aggressive"}`.

6. **URL format**: `https://{instance_url}/lightning/o/Contact/list?filterName={18_char_listview_id}`. Get the ID from the create response or via SOQL query on ListView sObject.

7. **Limitations**:
   - Max 10 filter conditions per ListView
   - No `sort` or `limit` in ListView metadata — Salesforce applies its own default sort
   - No relative date support (e.g., `LAST_N_DAYS`) — `not_contacted_days` cannot be directly translated
   - No cross-field text search — `search` filter dimension cannot be represented
   - `sort_by`, `sort_dir`, `limit` from CompoundFilter have no ListView equivalent

8. **Unsupported CompoundFilter dimensions for ListView**:
   - `not_contacted_days` — requires relative date formula, not available in ListView filters
   - `contacted_after` / `contacted_before` — absolute dates on LastActivityDate work IF the filter count stays under 10
   - `search` — no text search across multiple fields
   - `sort_by` / `sort_dir` — ListView doesn't support sort specification
   - `limit` — ListView doesn't support result limits

## R2: Salesforce Report CRUD via Analytics REST API

**Decision**: Use Analytics REST API via `sf.restful()` for Report CRUD operations.

**Rationale**: The Analytics REST API provides full CRUD on reports including filter management, folder placement, and metadata. It's more capable than ListView filters. The existing `simple_salesforce` library's `sf.restful()` method handles this.

**Alternatives considered**:
- Metadata API for Reports — possible but the Analytics REST API is more feature-rich for report operations
- Report Builder UI — not programmatic, doesn't serve the CLI use case

**Key findings**:

1. **Report creation** via `POST /analytics/reports`:
   ```python
   sf.restful(
       "analytics/reports",
       method="POST",
       json={
           "reportMetadata": {
               "name": "AA: My Report Name",
               "description": "[advisor-agent] Filters: age <= 50, risk: growth",
               "reportFormat": "TABULAR",
               "reportType": {"type": "ContactList"},  # Standard Contact report type
               "reportFilters": [...],
               "detailColumns": ["FIRST_NAME", "LAST_NAME", ...],
               "folderId": "<folder_id>",
           }
       },
   )
   ```

2. **Reports DO have a description field** — Can use `[advisor-agent]` tag in description for programmatic identification. This works as originally specified.

3. **Report folder management**: Need a "Client Lists" folder. Create via:
   ```python
   sf.restful(
       "analytics/report-folders",
       method="POST",
       json={"name": "Client Lists", "description": "[advisor-agent] Auto-created folder"},
   )
   ```
   Query existing folders: `sf.restful("analytics/report-folders")` and filter by name.

4. **Report filter format** (more expressive than ListView):
   ```python
   {
       "column": "Contact.Age__c",
       "operator": "lessOrEqual",
       "value": "50",
   }
   ```
   - Supports `LAST_N_DAYS:30` for relative dates (handles `not_contacted_days`)
   - Supports `AND`/`OR`/`NOT` boolean logic via `reportBooleanFilter`
   - No max filter count like ListView's 10-filter limit

5. **Supported filter operators**: `equals`, `notEqual`, `lessThan`, `greaterThan`, `lessOrEqual`, `greaterOrEqual`, `contains`, `startsWith`, `includes` (multi-value).

6. **Report columns**: Use API names like `FIRST_NAME`, `LAST_NAME`, `Contact.Age__c`, `Contact.Account_Value__c`, `Contact.Risk_Tolerance__c`, `Contact.Life_Stage__c`.

7. **URL format**: `{instance_url}/lightning/r/Report/{report_id}/view`

8. **Report CRUD operations**:
   - Create: `POST /analytics/reports`
   - Read: `GET /analytics/reports/{id}/describe`
   - Update: `PATCH /analytics/reports/{id}` with updated `reportMetadata`
   - Delete: `DELETE /analytics/reports/{id}`
   - List all: `GET /analytics/reports?q=[advisor-agent]` or query via SOQL `SELECT Id, Name, Description FROM Report WHERE Description LIKE '%[advisor-agent]%'`

9. **All CompoundFilter dimensions supported in Reports** — Unlike ListViews, Reports can represent every CompoundFilter dimension including `not_contacted_days` (via `LAST_N_DAYS`), `search` is partially supported (per-column contains), and while Reports don't have `sort_by`/`limit`, the report type inherently displays all matching records.

## R3: CompoundFilter → Salesforce Filter Translation

**Decision**: Build a translation layer that maps CompoundFilter fields to both ListView filter format and Report filter format, with explicit tracking of unsupported dimensions.

**Key mapping**:

| CompoundFilter field | ListView filter | Report filter | Notes |
|---------------------|----------------|---------------|-------|
| min_age / max_age | `Age__c` greaterOrEqual / lessOrEqual | `Contact.Age__c` | Fully supported both |
| min_value / max_value | `Account_Value__c` greaterOrEqual / lessOrEqual | `Contact.Account_Value__c` | Fully supported both |
| risk_tolerances | `Risk_Tolerance__c` equals (CSV) | `Contact.Risk_Tolerance__c` includes | Fully supported both |
| life_stages | `Life_Stage__c` equals (CSV) | `Contact.Life_Stage__c` includes | Fully supported both |
| not_contacted_days | **UNSUPPORTED** | `LastActivityDate` with `LAST_N_DAYS` | ListView limitation |
| contacted_after/before | `LastActivityDate` greaterOrEqual/lessOrEqual | `Contact.LastActivityDate` | Both support absolute dates |
| search | **UNSUPPORTED** | Partial (per-column `contains`) | ListView limitation |
| sort_by / sort_dir | **UNSUPPORTED** | N/A (report default sort) | Neither supports custom sort |
| limit | **UNSUPPORTED** | N/A (reports show all) | Neither supports limit |

## R4: Identification Strategy (Updated from Spec Clarification)

**Decision**: Dual identification with platform-appropriate mechanisms.

**For ListViews**:
- `DeveloperName` prefix: `AA_` (e.g., `AA_Top_50_Under_50`)
- `label` prefix: `AA:` (e.g., `AA: Top 50 Under 50`)
- Programmatic lookup: SOQL `SELECT Id, DeveloperName, Name FROM ListView WHERE SobjectType = 'Contact' AND DeveloperName LIKE 'AA_%'`
- No description field available

**For Reports**:
- `name` prefix: `AA:` (e.g., `AA: Top 50 Under 50`)
- `description` tag: `[advisor-agent]` (e.g., `[advisor-agent] age <= 50, risk: growth, aggressive`)
- Programmatic lookup: SOQL `SELECT Id, Name, Description FROM Report WHERE Description LIKE '%[advisor-agent]%'`

**Rationale**: ListView lacks a description field, so DeveloperName prefix is the only reliable programmatic identifier. Reports have description, so the `[advisor-agent]` tag works as originally specified. Both use the `AA:` visual prefix in their display name for user identification in the Salesforce UI.

## R5: Existing Code Integration Points

**Decision**: Extend existing modules rather than creating entirely new ones.

**Key integration points**:
- `src/finance_agent/sandbox/list_builder.py` — Currently handles local JSON saved lists. Will be refactored to use Salesforce APIs instead. The `save_list`, `get_saved_lists`, `delete_saved_list` functions will be replaced with Salesforce-backed versions.
- `src/finance_agent/sandbox/storage.py` — Contains `_CONTACT_FIELDS`, `_SORT_FIELD_MAP`, and SOQL helpers. The filter translation layer will reuse these mappings.
- `src/finance_agent/sandbox/models.py` — `CompoundFilter` model already has `describe()` method. Will remain unchanged.
- `src/finance_agent/cli.py` — `sandbox lists save/show/run/update/delete` and `sandbox ask` commands already exist. Will be updated to target Salesforce instead of local JSON.
- `src/finance_agent/mcp/research_server.py` — MCP tools for sandbox list operations. Will be updated.
- CLI is registered as `finance-agent` in pyproject.toml (not `advisor-agent`).
