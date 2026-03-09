# Quickstart: Client List Builder

**Feature**: 020-client-list-builder | **Date**: 2026-03-09

## Prerequisites

- Salesforce sandbox set up and seeded (019-sfdc-sandbox)
- `.env` configured with SFDC credentials + ANTHROPIC_API_KEY
- `uv run advisor-agent sandbox list` works (verifies Salesforce connection)

## Scenario 1: Compound Filter — "Top 50 Under 50"

```bash
# Age under 50, sorted by account value descending, limit 50
uv run advisor-agent sandbox list --max-age 50 --sort-by account_value --sort-dir desc --limit 50

# Expected: Table of up to 50 clients, all age <= 50, sorted by highest account value
# Output includes: "Filters applied: age <= 50 | sorted by account value (desc) | limit 50"
```

## Scenario 2: Multi-Dimension Compound Filter

```bash
# Growth or aggressive risk, under 50, over $200K
uv run advisor-agent sandbox list --risk growth aggressive --max-age 50 --min-value 200000

# Expected: Only clients matching ALL criteria:
#   - Risk tolerance is growth OR aggressive
#   - Age <= 50
#   - Account value >= $200,000
```

## Scenario 3: Recency-Based Filter

```bash
# Clients not contacted in 90 days
uv run advisor-agent sandbox list --not-contacted-days 90

# Expected: Clients whose last interaction was > 90 days ago, OR who have no interactions
# Output includes: "Filters applied: not contacted in 90 days"
```

## Scenario 4: Absolute Date Range Filter

```bash
# Clients last contacted in Q1 2026
uv run advisor-agent sandbox list --contacted-after 2026-01-01 --contacted-before 2026-03-31

# Expected: Only clients whose most recent interaction falls within Jan 1 - Mar 31, 2026
```

## Scenario 5: Save a Named List

```bash
# Save the "Top 50 Under 50" as a reusable list
uv run advisor-agent sandbox lists save --name "Top 50 Under 50" --desc "High-value clients under age 50" --max-age 50 --sort-by account_value --sort-dir desc --limit 50

# Expected: "Saved list 'Top 50 Under 50' with filters: age <= 50 | sorted by account value (desc) | limit 50"
```

## Scenario 6: List and Run Saved Lists

```bash
# Show all saved lists
uv run advisor-agent sandbox lists show

# Expected: Table showing name, description, filter summary, last run date

# Run a saved list
uv run advisor-agent sandbox lists run "Top 50 Under 50"

# Expected: Fresh results from Salesforce matching the saved filters
# Output includes the list name, filter summary, and result count
```

## Scenario 7: Natural Language Query

```bash
# Ask in plain English
uv run advisor-agent sandbox ask "show me my biggest clients under 50"

# Expected:
# Filters applied:
#   "biggest clients" → sorted by account value (desc)
#   "under 50" → age < 50
#
# [Results table]
# Showing 23 clients matching filters
```

## Scenario 8: Natural Language with Recency

```bash
# Recency-based natural language query
uv run advisor-agent sandbox ask "clients I haven't talked to in 3 months with over 500K"

# Expected:
# Filters applied:
#   "haven't talked to in 3 months" → not contacted in 90 days
#   "over 500K" → account value >= $500,000
#
# [Results table]
```

## Scenario 9: Ambiguous Natural Language Query

```bash
# Ambiguous query
uv run advisor-agent sandbox ask "show me the good clients"

# Expected (low confidence):
# I interpreted "good clients" as: sorted by account value (desc), limit 50
# Some parts of your query were unclear: "good" — did you mean high-value? growth-oriented?
# Run with these filters? Use --yes to skip confirmation, or rephrase your query.
```

## Scenario 10: MCP Tool via Claude Desktop

```
User: "Show me my top 20 growth clients under 40"

Claude Desktop calls sandbox_ask_clients(query="top 20 growth clients under 40")

Response:
  Filters applied: risk_tolerance = growth, age < 40, sorted by account_value desc, limit 20
  [20 client results]
```

## Validation Checklist

- [ ] Compound filters combine correctly (AND across dimensions, OR within)
- [ ] Multi-value risk/stage filters work (e.g., `--risk growth aggressive`)
- [ ] Age filters work (min/max)
- [ ] Recency filter works (--not-contacted-days)
- [ ] Absolute date range filter works (--contacted-after, --contacted-before)
- [ ] Custom sort order works (all 4 sort fields, both directions)
- [ ] Result limit works
- [ ] Saved list save/show/run/update/delete cycle works
- [ ] Saved lists persist across application restarts
- [ ] Natural language query translates correctly for common patterns
- [ ] Filter mapping display shows NL → filter translation
- [ ] Low-confidence NL queries ask for confirmation
- [ ] All features work via MCP tools
- [ ] Existing `sandbox list` command continues to work unchanged
