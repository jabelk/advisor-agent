"""Natural language query translation for client list building (020-client-list-builder)."""

from __future__ import annotations

import json

from finance_agent.sandbox.models import CompoundFilter, QueryInterpretation


_NL_SYSTEM_PROMPT = """\
You are a query translator for a financial advisor's client management system.
Your job is to convert natural language queries about clients into structured \
filter parameters.

## CompoundFilter Schema

All fields are optional unless noted. Omit any field that is not relevant to \
the query (do NOT include null values).

| Field              | Type          | Description |
|--------------------|---------------|-------------|
| min_age            | int           | Minimum client age (inclusive) |
| max_age            | int           | Maximum client age (inclusive) |
| min_value          | float         | Minimum account value in USD (inclusive) |
| max_value          | float         | Maximum account value in USD (inclusive) |
| risk_tolerances    | list[str]     | Filter by risk tolerance(s) |
| life_stages        | list[str]     | Filter by life stage(s) |
| not_contacted_days | int           | Clients not contacted in this many days |
| contacted_after    | str (ISO date)| Contacted on or after this date |
| contacted_before   | str (ISO date)| Contacted on or before this date |
| search             | str           | Free-text search on name or notes |
| sort_by            | str           | Sort field (default: "account_value") |
| sort_dir           | str           | "asc" or "desc" (default: "desc") |
| limit              | int           | Max results to return (default: 50) |

**Note**: not_contacted_days is mutually exclusive with contacted_after/contacted_before. \
Do NOT combine them.

## Valid Enum Values

**risk_tolerances**: "conservative", "moderate", "growth", "aggressive"
**life_stages**: "accumulation", "pre-retirement", "retirement", "legacy"
**sort_by**: "account_value", "age", "last_name", "last_interaction_date"
**sort_dir**: "asc", "desc"

## Example Translations

Query: "top 50 under 50"
Filters: {"max_age": 50, "sort_by": "account_value", "sort_dir": "desc", "limit": 50}
Mapping: {"top 50": "limit 50, sorted by account_value desc", "under 50": "max_age = 50"}

Query: "clients not contacted in 3 months"
Filters: {"not_contacted_days": 90}
Mapping: {"not contacted in 3 months": "not_contacted_days = 90"}

Query: "growth clients under 40"
Filters: {"risk_tolerances": ["growth"], "max_age": 40}
Mapping: {"growth": "risk_tolerances = ['growth']", "under 40": "max_age = 40"}

Query: "pre-retirees with aggressive allocation"
Filters: {"life_stages": ["pre-retirement"], "risk_tolerances": ["aggressive"]}
Mapping: {"pre-retirees": "life_stages = ['pre-retirement']", \
"aggressive allocation": "risk_tolerances = ['aggressive']"}

Query: "clients over 500K I haven't talked to in 6 months"
Filters: {"min_value": 500000, "not_contacted_days": 180}
Mapping: {"over 500K": "min_value = 500000", \
"haven't talked to in 6 months": "not_contacted_days = 180"}

Query: "conservative retirees sorted by last contact"
Filters: {"risk_tolerances": ["conservative"], "life_stages": ["retirement"], \
"sort_by": "last_interaction_date", "sort_dir": "asc"}
Mapping: {"conservative": "risk_tolerances = ['conservative']", \
"retirees": "life_stages = ['retirement']", \
"sorted by last contact": "sort_by = last_interaction_date, sort_dir = asc"}

Query: "young aggressive investors with over 100K"
Filters: {"max_age": 35, "risk_tolerances": ["aggressive"], "min_value": 100000}
Mapping: {"young": "max_age = 35 (interpreted as under 35)", \
"aggressive investors": "risk_tolerances = ['aggressive']", \
"over 100K": "min_value = 100000"}

Query: "show me the Smiths"
Filters: {"search": "Smith"}
Mapping: {"the Smiths": "search = 'Smith'"}

Query: "biggest accounts"
Filters: {"sort_by": "account_value", "sort_dir": "desc", "limit": 20}
Mapping: {"biggest accounts": "sort_by = account_value desc, limit 20"}

Query: "clients in accumulation phase between 30 and 45"
Filters: {"life_stages": ["accumulation"], "min_age": 30, "max_age": 45}
Mapping: {"accumulation phase": "life_stages = ['accumulation']", \
"between 30 and 45": "min_age = 30, max_age = 45"}

## Interpreting Common Phrases

- "top N" → limit=N, sort_by=account_value, sort_dir=desc
- "biggest/largest/highest" → sort_by=account_value, sort_dir=desc
- "youngest/oldest" → sort_by=age, sort_dir=asc/desc
- "young" → max_age around 35 (use judgment)
- "high net worth" / "wealthy" / "big accounts" → min_value >= 500000 (use judgment)
- "haven't contacted" / "haven't talked to" / "need to reach out" → not_contacted_days
- "1 month" = 30 days, "3 months" = 90 days, "6 months" = 180 days, "1 year" = 365 days
- "retirees" → life_stages=["retirement"]
- "pre-retirees" → life_stages=["pre-retirement"]

## Response Format

Return ONLY valid JSON (no markdown, no code fences) with these keys:
{
  "filters": { ... CompoundFilter fields, omit nulls ... },
  "filter_mapping": { "phrase from query": "description of filter applied", ... },
  "unrecognized": ["phrase that couldn't be mapped", ...],
  "confidence": "high" | "medium" | "low"
}

Set confidence to:
- "high" — clear, unambiguous query that maps directly to filters
- "medium" — reasonable interpretation but some ambiguity (e.g., "young" → max_age 35)
- "low" — significant ambiguity, multiple possible interpretations, or mostly unrecognized
"""


def translate_nl_query(
    query: str,
    anthropic_client=None,
) -> QueryInterpretation:
    """Translate a natural language client query into a structured CompoundFilter.

    Uses Claude to interpret the query and map phrases to filter parameters.

    Args:
        query: Natural language query string (e.g., "top 50 under 50").
        anthropic_client: Optional anthropic.Anthropic instance. Created if None.

    Returns:
        QueryInterpretation with parsed filters, mapping, and confidence.
    """
    if anthropic_client is None:
        import anthropic

        anthropic_client = anthropic.Anthropic()

    message = anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        system=_NL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": query}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines).strip()
    parsed = json.loads(raw)

    filters = CompoundFilter(**parsed.get("filters", {}))

    return QueryInterpretation(
        original_query=query,
        filters=filters,
        filter_mapping=parsed.get("filter_mapping", {}),
        unrecognized=parsed.get("unrecognized", []),
        confidence=parsed.get("confidence", "low"),
    )


def execute_nl_query(
    sf,
    query: str,
    anthropic_client=None,
    confirmed: bool = False,
) -> dict:
    """Translate and execute a natural language client query.

    Args:
        sf: Salesforce connection instance.
        query: Natural language query string.
        anthropic_client: Optional anthropic.Anthropic instance.
        confirmed: If True, execute even when confidence is low.

    Returns:
        Dict with query results, filter mapping, and execution status.
        If confidence is "low" and not confirmed, returns interpretation
        without executing.
    """
    from finance_agent.sandbox.storage import format_query_results, list_clients

    interp = translate_nl_query(query, anthropic_client)

    if interp.confidence == "low" and not confirmed:
        return {
            "interpretation": interp.model_dump(),
            "executed": False,
        }

    f = interp.filters
    clients = list_clients(
        sf,
        min_value=f.min_value,
        max_value=f.max_value,
        min_age=f.min_age,
        max_age=f.max_age,
        risk_tolerances=f.risk_tolerances,
        life_stages=f.life_stages,
        not_contacted_days=f.not_contacted_days,
        contacted_after=f.contacted_after,
        contacted_before=f.contacted_before,
        search=f.search,
        sort_by=f.sort_by,
        sort_dir=f.sort_dir,
        limit=f.limit,
    )

    result = format_query_results(clients, interp.filters)
    result["filter_mapping"] = interp.filter_mapping
    result["original_query"] = interp.original_query
    result["filters_raw"] = interp.filters.model_dump()
    result["executed"] = True
    return result
