# Quickstart: Tasks & Activity Logging

**Branch**: `022-sfdc-task-logging` | **Date**: 2026-03-09

## Prerequisites

- Salesforce developer sandbox connected (`finance-agent sandbox setup` from 019)
- Sandbox seeded with contacts (`finance-agent sandbox seed` from 019)
- Environment variables set: `SFDC_CLIENT_ID`, `SFDC_CLIENT_SECRET`, `SFDC_USERNAME`, `SFDC_INSTANCE_URL`

## Quick Test Scenarios

### 1. Create a Task (US1)

```bash
# Create a task with default due date (today + 7 days)
finance-agent sandbox tasks create --client "Jane Doe" --subject "Review portfolio allocation"

# Create with explicit due date and priority
finance-agent sandbox tasks create --client "Jane Doe" --subject "Discuss retirement plan" --due 2026-03-20 --priority High

# Test fuzzy matching — partial name
finance-agent sandbox tasks create --client "Jane" --subject "Quick check-in"
# → Should show disambiguation if multiple Janes exist
```

### 2. View Tasks (US2)

```bash
# Show all open tasks
finance-agent sandbox tasks show

# Show only overdue
finance-agent sandbox tasks show --overdue

# Filter by client
finance-agent sandbox tasks show --client "Jane Doe"

# Summary view
finance-agent sandbox tasks show --summary
```

### 3. Complete a Task (US2)

```bash
# Complete by subject match
finance-agent sandbox tasks complete "Review portfolio"

# Test ambiguous match
finance-agent sandbox tasks complete "check"
# → Should show multiple matches if they exist
```

### 4. Log an Activity (US3)

```bash
# Log a phone call
finance-agent sandbox log --client "Jane Doe" --subject "Discussed retirement timeline" --type call

# Log a past meeting
finance-agent sandbox log --client "Bob Smith" --subject "Annual review" --type meeting --date 2026-03-07

# Test future date rejection
finance-agent sandbox log --client "Jane Doe" --subject "Test" --type call --date 2027-01-01
# → Should reject with error
```

### 5. Outreach Queue (US4)

```bash
# Find clients not contacted in 90+ days
finance-agent sandbox outreach --days 90

# With minimum value filter
finance-agent sandbox outreach --days 90 --min-value 250000

# Auto-create tasks
finance-agent sandbox outreach --days 90 --create-tasks

# All contacts regardless of activity
finance-agent sandbox outreach --days 0
```

### 6. MCP Tools (via Claude Desktop)

After starting the MCP server, test in Claude Desktop:

- "Create a follow-up task for Jane Doe to review her portfolio by next Friday"
- "Show me all my overdue tasks"
- "Mark the portfolio review task as complete"
- "Log that I had a phone call with Bob Smith about his retirement plan"
- "Which clients haven't I contacted in 90 days? Create tasks for anyone with over $250k"

## Verification Checklist

- [ ] Task appears in Salesforce UI under Contact's activity timeline
- [ ] Task has [advisor-agent] tag in Description field
- [ ] Completed tasks show CompletedDateTime in Salesforce
- [ ] Activity logs appear as completed tasks with correct TaskSubtype
- [ ] Outreach queue correctly identifies stale contacts
- [ ] Outreach --create-tasks skips contacts with existing open tasks
- [ ] MCP tools return proper JSON responses
