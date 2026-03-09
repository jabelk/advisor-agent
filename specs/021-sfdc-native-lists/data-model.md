# Data Model: Salesforce-Native List Views & Reports

**Feature**: 021-sfdc-native-lists | **Date**: 2026-03-09

## Entities

### SalesforceListView (translation target, not a local model)

Represents a Salesforce ListView metadata object on the Contact sObject.

| Field | Salesforce API Name | Type | Description |
|-------|-------------------|------|-------------|
| fullName | `fullName` | string | `Contact.AA_{developer_name}` — Object.DeveloperName format |
| label | `label` | string | `AA: {display_name}` — visible name in Salesforce UI |
| filterScope | `filterScope` | string | Always `Everything` (all contacts visible to user) |
| columns | `columns` | list[string] | Column API names to display |
| filters | `filters` | list[dict] | Filter conditions (field, operation, value) |

**Identity**: `DeveloperName` with `AA_` prefix. No description field available on ListView.

**Lifecycle**:
- Created via `sf.mdapi.ListView.create()`
- Updated via `sf.mdapi.ListView.update()`
- Deleted via `sf.mdapi.ListView.delete()`
- Queried via SOQL: `SELECT Id, DeveloperName, Name FROM ListView WHERE SobjectType = 'Contact' AND DeveloperName LIKE 'AA_%'`

**Default columns**: `FULL_NAME`, `CONTACT_EMAIL`, `CONTACT_PHONE`, `Contact.Age__c`, `Contact.Account_Value__c`, `Contact.Risk_Tolerance__c`, `Contact.Life_Stage__c`

### SalesforceReport (translation target, not a local model)

Represents a Salesforce Report object via the Analytics REST API.

| Field | API Key | Type | Description |
|-------|---------|------|-------------|
| name | `name` | string | `AA: {display_name}` — visible name in Salesforce UI |
| description | `description` | string | `[advisor-agent] {filter_summary}` — for programmatic identification |
| reportFormat | `reportFormat` | string | Always `TABULAR` |
| reportType | `reportType.type` | string | `ContactList` — standard Contact report type |
| reportFilters | `reportFilters` | list[dict] | Filter conditions (column, operator, value) |
| detailColumns | `detailColumns` | list[string] | Column API names to display |
| folderId | `folderId` | string | ID of the "Client Lists" report folder |

**Identity**: `[advisor-agent]` tag in `description` field + `AA:` prefix in `name`.

**Lifecycle**:
- Created via `POST /analytics/reports`
- Updated via `PATCH /analytics/reports/{id}`
- Deleted via `DELETE /analytics/reports/{id}`
- Queried via SOQL: `SELECT Id, Name, Description FROM Report WHERE Description LIKE '%[advisor-agent]%'`

**Default columns**: `FIRST_NAME`, `LAST_NAME`, `Contact.Age__c`, `Contact.Account_Value__c`, `Contact.Risk_Tolerance__c`, `Contact.Life_Stage__c`, `LAST_ACTIVITY`

### ReportFolder (supporting entity)

| Field | API Key | Type | Description |
|-------|---------|------|-------------|
| name | `name` | string | `Client Lists` |
| description | `description` | string | `[advisor-agent] Auto-created folder` |
| id | `id` | string | 18-char Salesforce ID |

**Lifecycle**: Created on first report save if it doesn't exist. Not deleted by the tool.

### CompoundFilter (existing — unchanged)

From `src/finance_agent/sandbox/models.py`. No changes needed. Used as the input for translation to both ListView and Report filter formats.

### SavedList (existing — to be deprecated)

From `src/finance_agent/sandbox/models.py`. The local JSON-based SavedList will no longer be used for persistence. The model may be retained temporarily for backward compatibility during migration but the local JSON file (`saved_lists.json`) will no longer be written to or read from.

## Relationships

```text
CompoundFilter ──translate──> ListView filters (Metadata API format)
CompoundFilter ──translate──> Report filters (Analytics REST API format)
Report ──belongs_to──> ReportFolder ("Client Lists")
ListView ──filters──> Contact (sObject)
Report ──filters──> Contact (sObject)
```

## Filter Translation Rules

### CompoundFilter → ListView Filters

| CompoundFilter Field | ListView Filter | Notes |
|---------------------|----------------|-------|
| min_age | `{"field": "Age__c", "operation": "greaterOrEqual", "value": str(min_age)}` | |
| max_age | `{"field": "Age__c", "operation": "lessOrEqual", "value": str(max_age)}` | |
| min_value | `{"field": "Account_Value__c", "operation": "greaterOrEqual", "value": str(min_value)}` | |
| max_value | `{"field": "Account_Value__c", "operation": "lessOrEqual", "value": str(max_value)}` | |
| risk_tolerances | `{"field": "Risk_Tolerance__c", "operation": "equals", "value": ",".join(risk_tolerances)}` | CSV for multi-value |
| life_stages | `{"field": "Life_Stage__c", "operation": "equals", "value": ",".join(life_stages)}` | CSV for multi-value |
| contacted_after | `{"field": "ACTIVITY_DATE", "operation": "greaterOrEqual", "value": contacted_after}` | Absolute date only |
| contacted_before | `{"field": "ACTIVITY_DATE", "operation": "lessOrEqual", "value": contacted_before}` | Absolute date only |
| not_contacted_days | **OMITTED** — warn user | No relative date support |
| search | **OMITTED** — warn user | No multi-field text search |
| sort_by / sort_dir | **OMITTED** — warn user | No sort in ListView metadata |
| limit | **OMITTED** — warn user | No limit in ListView metadata |

### CompoundFilter → Report Filters

| CompoundFilter Field | Report Filter | Notes |
|---------------------|--------------|-------|
| min_age | `{"column": "Contact.Age__c", "operator": "greaterOrEqual", "value": str(min_age)}` | |
| max_age | `{"column": "Contact.Age__c", "operator": "lessOrEqual", "value": str(max_age)}` | |
| min_value | `{"column": "Contact.Account_Value__c", "operator": "greaterOrEqual", "value": str(min_value)}` | |
| max_value | `{"column": "Contact.Account_Value__c", "operator": "lessOrEqual", "value": str(max_value)}` | |
| risk_tolerances | `{"column": "Contact.Risk_Tolerance__c", "operator": "equals", "value": ",".join(risk_tolerances)}` | |
| life_stages | `{"column": "Contact.Life_Stage__c", "operator": "equals", "value": ",".join(life_stages)}` | |
| not_contacted_days | `{"column": "LAST_ACTIVITY", "operator": "equals", "value": f"LAST_N_DAYS:{not_contacted_days}"}` with NOT logic | Relative date supported |
| contacted_after | `{"column": "LAST_ACTIVITY", "operator": "greaterOrEqual", "value": contacted_after}` | |
| contacted_before | `{"column": "LAST_ACTIVITY", "operator": "lessOrEqual", "value": contacted_before}` | |
| search | Per-column `contains` filters | Partial support |
| sort_by / sort_dir | N/A — report default sort | Not controllable |
| limit | N/A — reports show all matches | Not controllable |
