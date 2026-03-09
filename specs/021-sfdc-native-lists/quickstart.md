# Quickstart: Salesforce-Native List Views & Reports

**Feature**: 021-sfdc-native-lists | **Date**: 2026-03-09

## Prerequisites

- Salesforce developer sandbox with synthetic Contact data (from 019-sfdc-sandbox)
- Environment variables: `SF_USERNAME`, `SF_PASSWORD`, `SF_SECURITY_TOKEN`, `SF_DOMAIN`
- `uv` installed, project dependencies installed (`uv sync`)

## Scenario 1: Create a List View from compound filters (US1)

```bash
# Create a List View for "Top 50 Under 50" clients
uv run finance-agent sandbox lists save --name "Top 50 Under 50" --max-age 50 --sort-by account_value --limit 50

# Expected output:
# List View created: AA: Top 50 Under 50
# Filters: age <= 50 | sorted by account_value (desc) | limit 50
# ⚠ Warnings:
#   - sort_by/sort_dir not supported in List Views (Salesforce applies default sort)
#   - limit not supported in List Views (all matching contacts shown)
# URL: https://orgfarm-XXX.develop.my.salesforce.com/lightning/o/Contact/list?filterName=00BXX0000XXXXX
```

Open the URL in browser — verify the List View appears in the Contacts tab with the `AA:` prefix.

## Scenario 2: List and delete List Views (US2)

```bash
# Show all tool-created List Views
uv run finance-agent sandbox lists show

# Expected output:
# Name                  Type        Filters                           URL
# Top 50 Under 50       List View   age <= 50                        https://...
# Growth Under 40       List View   age <= 40 | risk: growth         https://...

# Delete a List View
uv run finance-agent sandbox lists delete "Top 50 Under 50"

# Expected output:
# Deleted List View: Top 50 Under 50
```

## Scenario 3: Create a Report (US3)

```bash
# Create a Report for growth clients under 40
uv run finance-agent sandbox reports save --name "Growth Clients Under 40" --risk growth --max-age 40

# Expected output:
# Report created: AA: Growth Clients Under 40
# Folder: Client Lists
# Filters: age <= 40 | risk: growth
# URL: https://orgfarm-XXX.develop.my.salesforce.com/lightning/r/Report/00OXX0000XXXXX/view

# Show all tool-created Reports
uv run finance-agent sandbox reports show

# Delete a Report
uv run finance-agent sandbox reports delete "Growth Clients Under 40"
```

## Scenario 4: NL query with --save-as (US4)

```bash
# Natural language query → save as List View
uv run finance-agent sandbox ask "top 50 clients under 50" --save-as "Top 50 Under 50"

# Expected output:
# Query: "top 50 clients under 50"
# Confidence: high
# Interpreted filters: age <= 50 | sorted by account_value (desc) | limit 50
#
# List View created: AA: Top 50 Under 50
# URL: https://...
```

## Scenario 5: Partial List View with warnings

```bash
# Filter with unsupported dimensions for ListView
uv run finance-agent sandbox lists save --name "Inactive Growth" --risk growth --not-contacted-days 90

# Expected output:
# List View created: AA: Inactive Growth
# Filters: risk: growth
# ⚠ Warnings:
#   - not_contacted_days (90 days) cannot be represented in List View filters — omitted
#   - The Salesforce List View may show more results than the CLI query
# URL: https://...
```

## Validation Checklist

- [ ] List View appears in Salesforce Contacts tab with `AA:` prefix
- [ ] List View filters match CLI output (for supported dimensions)
- [ ] Report appears in Reports tab under "Client Lists" folder
- [ ] Report data matches CLI query results
- [ ] `sandbox lists show` lists only tool-created List Views
- [ ] `sandbox reports show` lists only tool-created Reports
- [ ] Delete removes the object from Salesforce
- [ ] Warnings clearly indicate omitted filter dimensions
- [ ] URLs are clickable and open the correct Salesforce page
