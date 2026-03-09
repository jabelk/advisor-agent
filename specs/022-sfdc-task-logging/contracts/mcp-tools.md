# MCP Tool Contracts: Tasks & Activity Logging

All tools registered on the existing `research_server.py` FastMCP instance. Follow existing `sandbox_*` naming convention.

---

## sandbox_create_task

Create a follow-up task for a client.

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| client_name | str | Yes | — | Contact name (fuzzy matched) |
| subject | str | Yes | — | Task subject line |
| due_date | str | No | Today + 7 days | Due date (YYYY-MM-DD) |
| priority | str | No | "Normal" | "High", "Normal", or "Low" |

**Returns**: `dict`
```json
{
  "task_id": "00Txx000003abcDEF",
  "subject": "Review portfolio allocation",
  "client_name": "Jane Doe",
  "client_id": "003xx000001ABC",
  "due_date": "2026-03-15",
  "priority": "Normal",
  "status": "Not Started"
}
```

**Error**: `{"error": "No contacts found matching 'Xyzzy'"}`
**Ambiguous**: `{"error": "Multiple contacts match 'Jane'", "matches": [{"id": "...", "name": "Jane Doe"}, ...]}`

---

## sandbox_show_tasks

List open tasks with optional filters.

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| client_name | str | No | None | Filter by contact name |
| overdue_only | bool | No | false | Show only overdue tasks |
| include_summary | bool | No | false | Include count summary |

**Returns**: `dict`
```json
{
  "tasks": [
    {
      "task_id": "00Txx000003abcDEF",
      "subject": "Review portfolio allocation",
      "client_name": "Jane Doe",
      "due_date": "2026-03-15",
      "priority": "Normal",
      "status": "Not Started",
      "overdue": false
    }
  ],
  "total": 1,
  "summary": {
    "total_open": 3,
    "overdue": 1,
    "due_today": 0,
    "due_this_week": 2
  }
}
```

---

## sandbox_complete_task

Mark a task as completed by subject match.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| subject | str | Yes | Subject text (fuzzy matched) |

**Returns**: `dict`
```json
{
  "task_id": "00Txx000003abcDEF",
  "subject": "Review portfolio allocation",
  "client_name": "Jane Doe",
  "status": "Completed",
  "completed_date": "2026-03-09"
}
```

**Error**: `{"error": "No open tasks found matching 'xyzzy'"}`
**Ambiguous**: `{"error": "Multiple tasks match 'review'", "matches": [...]}`

---

## sandbox_log_activity

Log a completed activity for a client.

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| client_name | str | Yes | — | Contact name (fuzzy matched) |
| subject | str | Yes | — | Activity description |
| activity_type | str | Yes | — | "call", "meeting", "email", or "other" |
| activity_date | str | No | Today | Date (YYYY-MM-DD, cannot be future) |

**Returns**: `dict`
```json
{
  "task_id": "00Txx000003xyzDEF",
  "subject": "Discussed retirement timeline",
  "client_name": "Jane Doe",
  "client_id": "003xx000001ABC",
  "activity_type": "call",
  "activity_date": "2026-03-09",
  "status": "Completed"
}
```

**Error**: `{"error": "Activity date cannot be in the future"}`

---

## sandbox_outreach_queue

Generate a prioritized outreach list of clients not contacted recently.

**Parameters**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| days | int | Yes | — | Minimum days since last contact (0 = all) |
| min_value | float | No | 0 | Minimum account value |
| create_tasks | bool | No | false | Auto-create follow-up tasks |

**Returns**: `dict`
```json
{
  "clients": [
    {
      "client_id": "003xx000001ABC",
      "name": "Jane Doe",
      "account_value": 500000,
      "last_activity_date": "2025-12-01",
      "days_since_contact": 99
    }
  ],
  "total": 3,
  "tasks_created": 2,
  "tasks_skipped": 1,
  "skipped_reasons": [
    {"name": "Alice Johnson", "reason": "existing open task: Review insurance options"}
  ]
}
```
