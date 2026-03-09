# Contract: ListView Service

**Module**: `src/finance_agent/sandbox/sfdc_listview.py`

## Functions

### `translate_filters_to_listview(filters: CompoundFilter) -> tuple[list[dict], list[str]]`

Translate a CompoundFilter into Salesforce ListView filter format.

**Parameters**:
- `filters` — CompoundFilter instance

**Returns**: Tuple of:
- `list[dict]` — ListView filter dicts (`{"field": ..., "operation": ..., "value": ...}`)
- `list[str]` — Warning messages for omitted/unsupported dimensions

**Behavior**:
- Maps supported fields (age, value, risk, life_stage, contacted_after/before) to ListView filter format
- Skips unsupported fields (not_contacted_days, search, sort_by, sort_dir, limit)
- Returns a warning string for each skipped field
- Enforces max 10 filters — if exceeded, truncates and warns

---

### `create_listview(sf, name: str, filters: CompoundFilter) -> dict`

Create a Salesforce ListView from a CompoundFilter.

**Parameters**:
- `sf` — Salesforce connection instance
- `name` — Display name (without AA: prefix — function adds it)
- `filters` — CompoundFilter instance

**Returns**: Dict with:
- `id` — 18-char Salesforce ListView ID
- `name` — Display name (with AA: prefix)
- `developer_name` — DeveloperName (with AA_ prefix)
- `url` — Salesforce Lightning URL
- `warnings` — List of omitted filter warnings
- `filters_applied` — Human-readable filter summary

**Behavior**:
- Prefixes label with `AA: `
- Generates DeveloperName as `AA_` + sanitized name (alphanumeric + underscores)
- Checks for existing ListView with same DeveloperName (upsert)
- If exists: updates filters via `sf.mdapi.ListView.update()`
- If new: creates via `sf.mdapi.ListView.create()`
- Returns clickable Salesforce URL

**Errors**:
- `SalesforceError` if API call fails (e.g., limit reached)

---

### `list_listviews(sf) -> list[dict]`

List all tool-created ListViews on the Contact object.

**Parameters**:
- `sf` — Salesforce connection instance

**Returns**: List of dicts, each with:
- `id` — Salesforce ListView ID
- `name` — Display name (AA: prefix stripped for display)
- `developer_name` — Full DeveloperName
- `url` — Salesforce Lightning URL

**Behavior**:
- Queries `SELECT Id, DeveloperName, Name FROM ListView WHERE SobjectType = 'Contact' AND DeveloperName LIKE 'AA_%'`
- Strips `AA: ` prefix from name for display
- Sorts by name

---

### `delete_listview(sf, name: str) -> bool`

Delete a tool-created ListView by display name.

**Parameters**:
- `sf` — Salesforce connection instance
- `name` — Display name (without AA: prefix — function matches with prefix)

**Returns**: `True` if deleted, `False` if not found

**Behavior**:
- Finds ListView by matching `AA_` + sanitized name in DeveloperName
- Deletes via `sf.mdapi.ListView.delete("Contact.{developer_name}")`
- Case-insensitive name matching

---

### `_sanitize_developer_name(name: str) -> str`

Convert a display name to a valid Salesforce DeveloperName.

**Parameters**:
- `name` — Human-readable name

**Returns**: Sanitized string (alphanumeric + underscores, max 40 chars)

**Behavior**:
- Replaces spaces and special characters with underscores
- Removes consecutive underscores
- Strips leading/trailing underscores
- Truncates to 40 characters
