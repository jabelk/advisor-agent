# Contracts: Client List Builder

**Feature**: 020-client-list-builder | **Date**: 2026-03-09

## 1. Compound Filter Query

### `query_clients(sf, filters) -> dict`

**Module**: `src/finance_agent/sandbox/storage.py` (enhanced `list_clients()`)

**Input**: Salesforce client + CompoundFilter (or individual keyword args for backward compatibility)

**New parameters added to `list_clients()`**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| min_age | int or None | None | Minimum age (inclusive) |
| max_age | int or None | None | Maximum age (inclusive) |
| risk_tolerances | list[str] or None | None | Multiple risk values (OR). Overrides single `risk_tolerance` if both provided. |
| life_stages | list[str] or None | None | Multiple life stage values (OR). Overrides single `life_stage` if both provided. |
| not_contacted_days | int or None | None | Recency: last interaction > N days ago (or never) |
| contacted_after | str or None | None | Absolute: last interaction >= this date (YYYY-MM-DD) |
| contacted_before | str or None | None | Absolute: last interaction <= this date (YYYY-MM-DD) |
| sort_by | str | "account_value" | Sort field: account_value, age, last_name, last_interaction_date |
| sort_dir | str | "desc" | Sort direction: asc or desc |

**Existing parameters preserved** (backward compatible):
- `risk_tolerance: str | None` — single value, still works
- `life_stage: str | None` — single value, still works
- `min_value: float | None`, `max_value: float | None`, `search: str | None`
- `limit: int = 50`, `offset: int = 0`

**Output**: `list[dict]` — same format as current `list_clients()`, plus `age` field added to summary:

```python
{
    "id": "003xx...",
    "first_name": "John",
    "last_name": "Doe",
    "age": 42,
    "account_value": 350000.0,
    "risk_tolerance": "growth",
    "life_stage": "accumulation",
    "last_interaction_date": "2026-01-15" or None,
}
```

**Result metadata** (new helper function):

```python
def format_query_results(clients: list[dict], filters: CompoundFilter) -> dict:
    """Format query results with filter summary and count."""
    return {
        "clients": clients,
        "count": len(clients),
        "requested_limit": filters.limit,
        "filters_applied": filters.describe(),  # human-readable filter summary
    }
```

**Error handling**:
- Invalid filter values → ValidationError (Pydantic)
- Salesforce connection failure → RuntimeError (existing pattern)
- Contradictory filters (e.g., min_age > max_age) → ValidationError

---

## 2. Saved List CRUD

### `save_list(name, description, filters) -> SavedList`

**Module**: `src/finance_agent/sandbox/list_builder.py`

Creates a new saved list. Raises `ValueError` if name already exists (case-insensitive).

### `get_saved_lists() -> list[SavedList]`

Returns all saved lists, sorted by name.

### `get_saved_list(name) -> SavedList | None`

Returns a single saved list by name (case-insensitive), or None if not found.

### `run_saved_list(sf, name) -> dict`

Executes a saved list's filters against Salesforce. Returns result dict from `format_query_results()`. Updates `last_run_at` timestamp.

Raises `ValueError` if list not found.

### `update_saved_list(name, updates) -> SavedList`

Updates a saved list's name, description, or filters. Raises `ValueError` if not found. If renaming, validates new name doesn't conflict.

### `delete_saved_list(name) -> bool`

Deletes a saved list. Returns True if deleted, False if not found.

### Storage format

File: `~/.advisor-agent/saved_lists.json` (configurable via `ADVISOR_AGENT_DATA_DIR` env var)

---

## 3. Natural Language Query Translation

### `translate_nl_query(query, anthropic_client=None) -> QueryInterpretation`

**Module**: `src/finance_agent/sandbox/list_builder.py`

**Input**: Natural language string (e.g., "top 50 clients under 50")

**Output**: `QueryInterpretation` with parsed filters, confidence, and filter mapping.

**Claude API call**:
- Model: claude-sonnet-4-5-20250929
- System prompt: defines CompoundFilter schema, valid values, 5-10 example translations
- User message: raw NL query
- Response format: JSON matching QueryInterpretation schema
- max_tokens: 1024

**Confidence levels**:
- `high`: All parts of the query mapped to filters
- `medium`: Some parts unmapped but core intent is clear
- `low`: Significant ambiguity — system should ask for confirmation (FR-012)

### `execute_nl_query(sf, query, anthropic_client=None, confirmed=False) -> dict`

**Module**: `src/finance_agent/sandbox/list_builder.py`

Translates NL query, checks confidence, executes if confident (or confirmed), returns results + filter mapping.

**Flow**:
1. Call `translate_nl_query(query)`
2. If confidence is "low" and not `confirmed`, return interpretation for user review (don't execute)
3. Execute `list_clients(sf, **filters)` with parsed filters
4. Return `format_query_results()` + `filter_mapping` + `original_query`

---

## 4. CLI Subcommands

**Module**: `src/finance_agent/cli.py`

### Enhanced `sandbox list`

Add new flags to existing `sandbox list` command:

```
sandbox list [--risk RISK...] [--stage STAGE...] [--min-value N] [--max-value N]
             [--min-age N] [--max-age N] [--not-contacted-days N]
             [--contacted-after DATE] [--contacted-before DATE]
             [--search TEXT] [--sort-by FIELD] [--sort-dir asc|desc] [--limit N]
```

`--risk` and `--stage` accept multiple values (e.g., `--risk growth aggressive`).

### New `sandbox lists` subcommand group

```
sandbox lists save --name NAME [--desc TEXT] [FILTER_FLAGS...]
sandbox lists show
sandbox lists run NAME
sandbox lists update NAME [--name NEW_NAME] [--desc TEXT] [FILTER_FLAGS...]
sandbox lists delete NAME
```

### New `sandbox ask` subcommand

```
sandbox ask "top 50 clients under 50"
sandbox ask "clients I haven't talked to in 3 months" [--yes]
```

`--yes` skips confirmation for low-confidence interpretations.

---

## 5. MCP Tools

**Module**: `src/finance_agent/mcp/research_server.py`

### New tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `sandbox_query_clients` | Run compound filter query | All CompoundFilter fields as params |
| `sandbox_save_list` | Save a named list | name, description, filter params |
| `sandbox_show_lists` | List all saved lists | (none) |
| `sandbox_run_list` | Run a saved list by name | name |
| `sandbox_delete_list` | Delete a saved list | name |
| `sandbox_ask_clients` | Natural language client query | query (string) |

### Modified tools

| Tool | Change |
|------|--------|
| `sandbox_list_clients` | Add compound filter params (backward compatible) |
| `sandbox_search_clients` | Unchanged (convenience wrapper) |
