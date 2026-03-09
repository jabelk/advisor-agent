# Quickstart: Salesforce Learning Guide Validation

## Prerequisites

- Salesforce developer sandbox accessible at `orgfarm-561a3648a3-dev-ed.develop.my.salesforce.com`
- Claude Desktop connected to advisor-agent MCP server (Railway)
- Sandbox seeded with 50 synthetic clients (run `sandbox_seed_clients` if needed)

## Validation Scenarios

### Scenario 1: Getting Started Guide Works

1. Open `guide/00-getting-started.md`
2. Follow the sandbox login instructions
3. Verify the Salesforce sandbox loads and shows contacts
4. In Claude Desktop, ask: "How many clients are in the sandbox?"
5. **Expected**: Claude uses `sandbox_list_clients` and reports ~50 clients

### Scenario 2: Lesson 1 Core Exercise

1. Open `guide/01-contacts.md`
2. Follow exercise steps to find a specific client in Salesforce
3. In Claude Desktop, ask: "Show me details for Janet Morales"
4. **Expected**: Claude uses `sandbox_get_client` and returns matching data
5. Compare Claude's output to what Salesforce shows — fields should match

### Scenario 3: Lesson 2 MCP Verification

1. Open `guide/02-tasks.md`
2. Create a task for a client manually in Salesforce
3. In Claude Desktop, ask: "Show me open tasks"
4. **Expected**: Claude uses `sandbox_show_tasks` and the manually created task appears

### Scenario 4: Claude Tutor Prompt

1. Open `guide/` as a Claude Desktop Project
2. Ask Claude: "What lessons are available?"
3. **Expected**: Claude lists all 6 lessons (00-05) with descriptions
4. Ask Claude: "Help me get started with Lesson 1"
5. **Expected**: Claude gives guidance referencing the lesson content and seed data

### Scenario 5: Challenge Exercise Verification

1. Complete Lesson 3's challenge exercise (search/filter)
2. Ask Claude to verify using the suggested verification prompt
3. **Expected**: Claude uses `sandbox_query_clients` or `sandbox_search_clients` and confirms results
