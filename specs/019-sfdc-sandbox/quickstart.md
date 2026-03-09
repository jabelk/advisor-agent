# Quickstart: Salesforce Sandbox Learning Playground

**Feature**: 019-sfdc-sandbox | **Date**: 2026-03-08

## Prerequisites

- Python 3.12+
- `ANTHROPIC_API_KEY` environment variable set (for meeting briefs and commentary)
- Existing advisor-agent installation with migrations applied

## Scenario 1: Seed Data & Browse Clients (US1)

```bash
# 1. Populate sandbox with 50 synthetic clients
advisor-agent sandbox seed
# Expected: "Created 50 synthetic client profiles with interactions."

# 2. List all clients (sorted by account value descending)
advisor-agent sandbox list
# Expected: Table with 50 rows showing Name, Account Value, Risk, Life Stage, Last Contact

# 3. Filter by risk tolerance
advisor-agent sandbox list --risk growth
# Expected: ~17-18 clients (35% of 50)

# 4. Filter by account value range
advisor-agent sandbox list --min-value 500000 --max-value 2000000
# Expected: Subset of clients with $500K-$2M accounts

# 5. Search by name
advisor-agent sandbox list --search "Johnson"
# Expected: Any clients with "Johnson" in name or notes

# 6. View a single client profile
advisor-agent sandbox view 1
# Expected: Full profile with all fields + interaction history

# 7. Add a new client manually
advisor-agent sandbox add --first "Test" --last "Client" --age 45 --occupation "Engineer" \
    --account-value 250000 --risk moderate --life-stage accumulation --goals "College fund"
# Expected: "Client #51 created: Test Client"

# 8. Edit a client
advisor-agent sandbox edit 1 --account-value 750000 --notes "Updated after annual review"
# Expected: "Client #1 updated."

# 9. Verify edit persisted
advisor-agent sandbox view 1
# Expected: Account value shows $750,000, notes show "Updated after annual review"
```

## Scenario 2: Meeting Prep Brief (US2)

```bash
# Prerequisites: Seed data exists, research pipeline has been run at least once

# 1. Generate meeting brief for a growth-oriented client
advisor-agent sandbox view 1  # Note: check client's risk tolerance first
advisor-agent sandbox brief 1
# Expected: Structured brief with:
#   - Client Summary (name, age, occupation, account value)
#   - Portfolio Context (investment goals, risk tolerance)
#   - Market Conditions (data from research signals)
#   - 3-5 Talking Points tailored to client's profile

# 2. Generate brief for a conservative client
advisor-agent sandbox brief 10  # Pick a conservative client
# Expected: Talking points emphasize capital preservation, fixed income, downside protection

# 3. Generate brief with no market data available (fresh install, no research run)
# Expected: Brief generates with client profile only + "Market data unavailable" note

# 4. Request brief for nonexistent client
advisor-agent sandbox brief 999
# Expected: Error "Client 999 not found. Run 'sandbox list' to see available clients."
```

## Scenario 3: Market Commentary (US3)

```bash
# Prerequisites: Seed data exists, research pipeline has been run

# 1. Generate commentary for growth-oriented clients
advisor-agent sandbox commentary --risk growth
# Expected: 2-3 paragraphs focusing on equity markets, sector performance, growth opportunities
#           References specific data points from research signals

# 2. Generate commentary for income-focused/conservative clients
advisor-agent sandbox commentary --risk conservative
# Expected: Commentary focuses on bonds, dividends, interest rates, capital preservation

# 3. Generate commentary for pre-retirees
advisor-agent sandbox commentary --stage pre-retirement
# Expected: Commentary focuses on transition planning, income strategies, risk reduction

# 4. Generate general market overview (no segment filter)
advisor-agent sandbox commentary
# Expected: Broad market overview suitable for all client types

# 5. Combine filters
advisor-agent sandbox commentary --risk growth --stage accumulation
# Expected: Commentary for young growth investors — tech/innovation focus, long time horizon
```

## Scenario 4: Seed Reset & Re-seed (Edge Cases)

```bash
# 1. Seed when data already exists (interactive prompt)
advisor-agent sandbox seed
# Expected: "Sandbox already has 51 clients. Options: add more (--count N), reset (--reset), or cancel."

# 2. Reset and re-seed
advisor-agent sandbox seed --reset
# Expected: "Reset sandbox data. Created 50 synthetic client profiles with interactions."

# 3. Add more clients without reset
advisor-agent sandbox seed --count 10
# Expected: "Created 10 synthetic client profiles with interactions. Total: 60 clients."
```

## MCP Tool Verification

In Claude Desktop, verify these tools are available:

1. `sandbox_seed_clients` — "Seed 50 clients into the sandbox"
2. `sandbox_list_clients` — "List all sandbox clients"
3. `sandbox_search_clients` — "Search for clients named Johnson"
4. `sandbox_get_client` — "Show me client #1"
5. `sandbox_add_client` — "Add a new client: Jane Doe, age 55, retired, $2M account, conservative"
6. `sandbox_edit_client` — "Update client #1's risk tolerance to moderate"
7. `sandbox_meeting_brief` — "Prepare a meeting brief for client #1"
8. `sandbox_market_commentary` — "Write market commentary for growth-oriented clients"
