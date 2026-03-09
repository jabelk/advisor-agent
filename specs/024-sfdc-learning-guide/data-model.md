# Data Model: Salesforce Learning Guide

This is a content feature. No new database tables, API endpoints, or application entities are created. The "data model" describes the content artifacts and their relationships.

## Content Entities

### Lesson

A structured markdown file teaching one Salesforce CRM concept.

| Field | Type | Description |
|-------|------|-------------|
| number | int | Sequential lesson number (00-05) |
| title | string | Lesson title (e.g., "Navigating Contacts") |
| objective | string | What the learner will accomplish |
| crm_concept | text | Transferable CRM concept explanation |
| prerequisites | list[int] | Lesson numbers that must be completed first |
| manual_exercises | list[Exercise] | Steps to perform in Salesforce sandbox |
| verification_steps | list[Verification] | MCP tool calls to verify manual work |
| key_takeaways | list[string] | Transferable concepts learned |
| challenge | Exercise | Unguided independent exercise |

### Exercise

A step-by-step task for Jordan to perform manually in Salesforce.

| Field | Type | Description |
|-------|------|-------------|
| description | string | What to do in plain language |
| expected_result | string | What Jordan should see after completing the step |
| seed_data_reference | string | Specific client name or data point from seed data |

### Verification

An MCP tool call that confirms the manual exercise succeeded.

| Field | Type | Description |
|-------|------|-------------|
| prompt | string | What Jordan types in Claude Desktop |
| mcp_tool | string | Which MCP tool Claude will use |
| expected_match | string | What the MCP output should show |

### Tutor Project

The Claude Desktop Project configuration (CLAUDE.md).

| Field | Type | Description |
|-------|------|-------------|
| role | string | "Salesforce tutor for a financial advisor" |
| curriculum | list[Lesson] | Awareness of all lessons and their order |
| mcp_tools | list[string] | Which MCP tools to use for verification |
| teaching_style | string | Guide without giving away answers, verify work on request |

## Relationships

```text
Tutor Project (CLAUDE.md)
  └── references → Lesson[0..5]
                      ├── contains → Exercise[1..n]
                      ├── contains → Verification[1..n]
                      └── references → Sandbox Data (seed clients)
```

## Existing Data Dependencies

No new data is created. The guide depends on:

- **Salesforce sandbox seed data**: 50 synthetic clients created by `sandbox_seed_clients` MCP tool
- **Advisor-agent MCP tools**: 21 sandbox tools already deployed on Railway
- **Claude Desktop**: Connected to advisor-agent MCP server via mcp-remote
