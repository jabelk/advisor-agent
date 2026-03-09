# Contract: Report Service

**Module**: `src/finance_agent/sandbox/sfdc_report.py`

## Functions

### `translate_filters_to_report(filters: CompoundFilter) -> tuple[list[dict], list[str]]`

Translate a CompoundFilter into Salesforce Report filter format.

**Parameters**:
- `filters` — CompoundFilter instance

**Returns**: Tuple of:
- `list[dict]` — Report filter dicts (`{"column": ..., "operator": ..., "value": ...}`)
- `list[str]` — Warning messages for partially supported dimensions

**Behavior**:
- Maps all supported fields to Analytics API report filter format
- Translates `not_contacted_days` to `LAST_N_DAYS` relative date
- `search` translates to per-column `contains` on name fields (partial support)
- `sort_by`, `sort_dir`, `limit` have no report equivalent — warns if set to non-defaults

---

### `ensure_report_folder(sf) -> str`

Get or create the "Client Lists" report folder.

**Parameters**:
- `sf` — Salesforce connection instance

**Returns**: Folder ID (18-char string)

**Behavior**:
- Queries for existing folder named "Client Lists" with `[advisor-agent]` in description
- If found: returns its ID
- If not found: creates via `POST /analytics/report-folders` and returns new ID
- Caches folder ID for the session (avoids repeated lookups)

---

### `create_report(sf, name: str, filters: CompoundFilter) -> dict`

Create a Salesforce Report from a CompoundFilter.

**Parameters**:
- `sf` — Salesforce connection instance
- `name` — Display name (without AA: prefix — function adds it)
- `filters` — CompoundFilter instance

**Returns**: Dict with:
- `id` — 18-char Salesforce Report ID
- `name` — Display name (with AA: prefix)
- `url` — Salesforce Lightning URL
- `warnings` — List of filter translation warnings
- `filters_applied` — Human-readable filter summary
- `folder` — Folder name ("Client Lists")

**Behavior**:
- Prefixes name with `AA: `
- Sets description to `[advisor-agent] {filters.describe()}`
- Uses `TABULAR` report format with `ContactList` report type
- Ensures "Client Lists" folder exists (calls `ensure_report_folder`)
- Checks for existing report with same name (upsert via name match in description-tagged reports)
- If exists: updates via `PATCH /analytics/reports/{id}`
- If new: creates via `POST /analytics/reports`
- Returns clickable Salesforce URL

**Errors**:
- `SalesforceError` if API call fails

---

### `list_reports(sf) -> list[dict]`

List all tool-created Reports.

**Parameters**:
- `sf` — Salesforce connection instance

**Returns**: List of dicts, each with:
- `id` — Salesforce Report ID
- `name` — Display name (AA: prefix stripped for display)
- `url` — Salesforce Lightning URL
- `description` — Full description (includes filter summary)

**Behavior**:
- Queries `SELECT Id, Name, Description, LastRunDate FROM Report WHERE Description LIKE '%[advisor-agent]%'`
- Strips `AA: ` prefix from name for display
- Sorts by name

---

### `delete_report(sf, name: str) -> bool`

Delete a tool-created Report by display name.

**Parameters**:
- `sf` — Salesforce connection instance
- `name` — Display name (without AA: prefix — function matches with prefix)

**Returns**: `True` if deleted, `False` if not found

**Behavior**:
- Finds report by matching `AA: {name}` in Name among `[advisor-agent]` tagged reports
- Deletes via `DELETE /analytics/reports/{id}`
- Case-insensitive name matching
