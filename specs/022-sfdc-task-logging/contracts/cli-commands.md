# CLI Contracts: Tasks & Activity Logging

## sandbox tasks create

Create a follow-up task for a client.

```text
finance-agent sandbox tasks create --client <name> --subject <text> [--due YYYY-MM-DD] [--priority High|Normal|Low]
```

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| --client | Yes | — | Contact name (fuzzy matched) |
| --subject | Yes | — | Task subject line |
| --due | No | Today + 7 days | Due date (YYYY-MM-DD) |
| --priority | No | Normal | High, Normal, or Low |

**Success output**:
```text
Task created: "Review portfolio allocation"
  Client:   Jane Doe (003xx000001ABC)
  Due:      2026-03-15
  Priority: Normal
  Status:   Not Started
```

**Ambiguous client**:
```text
Multiple contacts match "Jane":
  1. Jane Doe (003xx000001ABC)
  2. Jane Smith (003xx000001DEF)
Please specify the full name.
```

**Client not found**:
```text
No contacts found matching "Xyzzy".
```

---

## sandbox tasks show

List open tasks with optional filters.

```text
finance-agent sandbox tasks show [--overdue] [--client <name>] [--summary]
```

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| --overdue | No | false | Show only overdue tasks |
| --client | No | — | Filter by contact name (fuzzy) |
| --summary | No | false | Show count summary instead of table |

**Table output** (default):
```text
Subject                       Client      Due         Priority  Status
─────────────────────────────────────────────────────────────────────────
Review portfolio allocation   Jane Doe    2026-03-15  Normal    Not Started
Quick check-in                Bob Smith   2026-03-10  High      Not Started
Annual review follow-up       Jane Doe    2026-03-08  Normal    Not Started  ← OVERDUE

3 open tasks (1 overdue)
```

**Summary output** (--summary):
```text
Task Summary:
  Total open:    3
  Overdue:       1
  Due today:     0
  Due this week: 2
```

---

## sandbox tasks complete

Mark a task as completed by subject match.

```text
finance-agent sandbox tasks complete <subject>
```

| Arg | Required | Description |
|-----|----------|-------------|
| subject | Yes | Subject text (fuzzy matched against open tasks) |

**Success output**:
```text
Completed: "Review portfolio allocation" (Jane Doe, was due 2026-03-15)
```

**Multiple matches**:
```text
Multiple tasks match "review":
  1. "Review portfolio allocation" — Jane Doe (due 2026-03-15)
  2. "Review insurance options" — Bob Smith (due 2026-03-20)
Please provide a more specific subject.
```

**Not found**:
```text
No open tasks found matching "xyzzy".
```

**Already completed**:
```text
Task "Review portfolio allocation" is already completed.
```

---

## sandbox log

Log a completed activity.

```text
finance-agent sandbox log --client <name> --subject <text> --type <call|meeting|email|other> [--date YYYY-MM-DD]
```

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| --client | Yes | — | Contact name (fuzzy matched) |
| --subject | Yes | — | Activity description |
| --type | Yes | — | call, meeting, email, or other |
| --date | No | Today | Activity date (YYYY-MM-DD, cannot be future) |

**Success output**:
```text
Activity logged: "Discussed retirement timeline" (call)
  Client: Jane Doe (003xx000001ABC)
  Date:   2026-03-09
```

**Future date rejected**:
```text
Error: Activity date cannot be in the future (got 2026-04-01).
```

---

## sandbox outreach

Generate a prioritized outreach queue.

```text
finance-agent sandbox outreach --days <N> [--min-value <amount>] [--create-tasks]
```

| Arg | Required | Default | Description |
|-----|----------|---------|-------------|
| --days | Yes | — | Minimum days since last contact (0 = all) |
| --min-value | No | 0 | Minimum account value filter |
| --create-tasks | No | false | Auto-create follow-up tasks |

**List output** (default):
```text
Outreach Queue: Clients not contacted in 90+ days
  Min account value: $250,000

Name              Account Value    Last Contact    Days Ago
──────────────────────────────────────────────────────────────
Jane Doe          $500,000         2025-12-01      99
Bob Smith         $350,000         2025-11-15      115
Alice Johnson     $275,000         2025-10-20      141

3 clients need outreach
```

**With --create-tasks**:
```text
Outreach Queue: 3 clients not contacted in 90+ days

Created tasks:
  ✓ Jane Doe — "Follow-up: No contact in 99 days"
  ✓ Bob Smith — "Follow-up: No contact in 115 days"
  ⊘ Alice Johnson — skipped (existing open task: "Review insurance options")

2 tasks created, 1 skipped
```
