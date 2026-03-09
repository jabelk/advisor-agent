"""Task management and activity logging via Salesforce Task objects.

Provides CLI and MCP-facing functions for creating follow-up tasks,
viewing/completing tasks, logging activities, and generating outreach
queues — all backed by the Salesforce standard Task object.
"""

from __future__ import annotations

from datetime import date, timedelta

from simple_salesforce import Salesforce

from finance_agent.sandbox.models import ADVISOR_AGENT_TAG
from finance_agent.sandbox.storage import _soql_escape


# Map CLI activity types to Salesforce TaskSubtype values
_ACTIVITY_TYPE_MAP: dict[str, str | None] = {
    "call": "Call",
    "email": "Email",
    "meeting": None,
    "other": None,
}


def resolve_contact(sf: Salesforce, name: str) -> list[dict]:
    """Resolve a client name to Contact records via fuzzy SOQL match.

    Returns a list of dicts with 'id' and 'name' keys. Empty list if
    no matches. Callers should handle disambiguation when len() > 1.
    """
    safe = _soql_escape(name)
    soql = (
        "SELECT Id, FirstName, LastName FROM Contact "
        f"WHERE FirstName LIKE '%{safe}%' OR LastName LIKE '%{safe}%' "
        "ORDER BY LastName, FirstName"
    )
    result = sf.query(soql)
    return [
        {
            "id": rec["Id"],
            "name": f"{rec.get('FirstName') or ''} {rec.get('LastName') or ''}".strip(),
        }
        for rec in result.get("records", [])
    ]


def create_task(
    sf: Salesforce,
    client_id: str,
    subject: str,
    due_date: str | None = None,
    priority: str = "Normal",
) -> dict:
    """Create a follow-up Task in Salesforce linked to a Contact.

    Args:
        sf: Salesforce connection.
        client_id: 18-char Contact ID (WhoId).
        subject: Task subject line.
        due_date: YYYY-MM-DD string, defaults to today + 7 days.
        priority: 'High', 'Normal', or 'Low'.

    Returns:
        Dict with task_id, subject, client_id, due_date, priority, status.
    """
    if due_date is None:
        due_date = (date.today() + timedelta(days=7)).isoformat()

    task_data = {
        "WhoId": client_id,
        "Subject": subject,
        "ActivityDate": due_date,
        "Status": "Not Started",
        "Priority": priority,
        "Description": f"{ADVISOR_AGENT_TAG} Created by advisor-agent CLI",
    }
    result = sf.Task.create(task_data)
    return {
        "task_id": result["id"],
        "subject": subject,
        "client_id": client_id,
        "due_date": due_date,
        "priority": priority,
        "status": "Not Started",
    }


def _resolve_contact_name(sf: Salesforce, who_id: str) -> str:
    """Look up a Contact name by ID. Returns 'Unknown Contact' on failure."""
    if not who_id:
        return "Unknown Contact"
    try:
        safe = _soql_escape(who_id)
        result = sf.query(
            f"SELECT FirstName, LastName FROM Contact WHERE Id = '{safe}'"
        )
        if result.get("records"):
            rec = result["records"][0]
            return f"{rec.get('FirstName') or ''} {rec.get('LastName') or ''}".strip()
    except Exception:
        pass
    return "Unknown Contact"


def list_tasks(
    sf: Salesforce,
    client_name: str | None = None,
    overdue_only: bool = False,
) -> list[dict]:
    """List open [advisor-agent]-tagged Tasks.

    Args:
        sf: Salesforce connection.
        client_name: Optional — filter by contact name (fuzzy match).
        overdue_only: If True, only return tasks with due date before today.

    Returns:
        List of task dicts sorted by due date, each with task_id, subject,
        client_name, client_id, due_date, priority, status, overdue flag.
    """
    conditions = [
        "Status != 'Completed'",
    ]

    if client_name:
        contacts = resolve_contact(sf, client_name)
        if not contacts:
            return []
        contact_ids = "', '".join(c["id"] for c in contacts)
        conditions.append(f"WhoId IN ('{contact_ids}')")

    if overdue_only:
        conditions.append(f"ActivityDate < {date.today().isoformat()}")

    where = " AND ".join(conditions)
    soql = (
        "SELECT Id, Subject, WhoId, ActivityDate, Priority, Status, Description "
        f"FROM Task WHERE {where} "
        "ORDER BY ActivityDate ASC NULLS LAST"
    )
    result = sf.query(soql)

    # Filter for [advisor-agent]-tagged tasks in Python
    # (Description is a long text area — cannot use LIKE in SOQL)
    records = [
        r for r in result.get("records", [])
        if ADVISOR_AGENT_TAG in (r.get("Description") or "")
    ]
    who_ids = {r["WhoId"] for r in records if r.get("WhoId")}
    name_cache: dict[str, str] = {}
    if who_ids:
        ids_str = "', '".join(who_ids)
        contacts_result = sf.query(
            f"SELECT Id, FirstName, LastName FROM Contact WHERE Id IN ('{ids_str}')"
        )
        for c in contacts_result.get("records", []):
            name_cache[c["Id"]] = (
                f"{c.get('FirstName') or ''} {c.get('LastName') or ''}".strip()
            )

    today = date.today().isoformat()
    tasks = []
    for rec in records:
        due = rec.get("ActivityDate") or ""
        tasks.append({
            "task_id": rec["Id"],
            "subject": rec.get("Subject") or "",
            "client_name": name_cache.get(rec.get("WhoId", ""), "Unknown Contact"),
            "client_id": rec.get("WhoId") or "",
            "due_date": due,
            "priority": rec.get("Priority") or "Normal",
            "status": rec.get("Status") or "",
            "overdue": bool(due and due < today),
        })
    return tasks


def complete_task(sf: Salesforce, subject: str) -> dict:
    """Mark an open [advisor-agent]-tagged Task as completed by subject match.

    Args:
        sf: Salesforce connection.
        subject: Subject text to fuzzy-match (SOQL LIKE).

    Returns:
        Dict with status='completed' and task details, or
        status='ambiguous' with list of matches, or
        status='not_found', or status='already_completed'.
    """
    safe = _soql_escape(subject)

    # First check for already-completed matches
    # (Description is a long text area — cannot use LIKE in SOQL, filter in Python)
    completed_soql = (
        "SELECT Id, Subject, WhoId, Status, Description FROM Task "
        f"WHERE Subject LIKE '%{safe}%' "
        "AND Status = 'Completed'"
    )
    completed_result = sf.query(completed_soql)
    completed_matches = [
        r for r in completed_result.get("records", [])
        if ADVISOR_AGENT_TAG in (r.get("Description") or "")
    ]

    # Then check open tasks
    open_soql = (
        "SELECT Id, Subject, WhoId, ActivityDate, Priority, Description FROM Task "
        f"WHERE Subject LIKE '%{safe}%' "
        "AND Status != 'Completed'"
    )
    open_result = sf.query(open_soql)
    open_matches = [
        r for r in open_result.get("records", [])
        if ADVISOR_AGENT_TAG in (r.get("Description") or "")
    ]

    if not open_matches:
        if completed_matches:
            rec = completed_matches[0]
            return {
                "status": "already_completed",
                "task_id": rec["Id"],
                "subject": rec.get("Subject") or "",
            }
        return {"status": "not_found"}

    if len(open_matches) > 1:
        matches = []
        for rec in open_matches:
            matches.append({
                "task_id": rec["Id"],
                "subject": rec.get("Subject") or "",
                "client_name": _resolve_contact_name(sf, rec.get("WhoId", "")),
                "due_date": rec.get("ActivityDate") or "",
            })
        return {"status": "ambiguous", "matches": matches}

    # Single match — complete it
    rec = open_matches[0]
    sf.Task.update(rec["Id"], {"Status": "Completed"})
    return {
        "status": "completed",
        "task_id": rec["Id"],
        "subject": rec.get("Subject") or "",
        "client_name": _resolve_contact_name(sf, rec.get("WhoId", "")),
        "due_date": rec.get("ActivityDate") or "",
        "completed_date": date.today().isoformat(),
    }


def get_task_summary(sf: Salesforce) -> dict:
    """Get summary counts of open [advisor-agent]-tagged Tasks.

    Returns dict with total_open, overdue, due_today, due_this_week.
    """
    today = date.today()
    # Calculate end of week (Sunday)
    days_until_sunday = 6 - today.weekday()  # Monday=0, Sunday=6
    if days_until_sunday < 0:
        days_until_sunday = 0
    end_of_week = (today + timedelta(days=days_until_sunday)).isoformat()
    today_str = today.isoformat()

    # Description is a long text area — cannot use LIKE in SOQL, filter in Python
    soql = (
        "SELECT Id, ActivityDate, Description FROM Task "
        "WHERE Status != 'Completed'"
    )
    result = sf.query(soql)
    records = [
        r for r in result.get("records", [])
        if ADVISOR_AGENT_TAG in (r.get("Description") or "")
    ]

    total_open = len(records)
    overdue = 0
    due_today = 0
    due_this_week = 0

    for rec in records:
        due = rec.get("ActivityDate") or ""
        if due:
            if due < today_str:
                overdue += 1
            elif due == today_str:
                due_today += 1
            if due <= end_of_week and due >= today_str:
                due_this_week += 1

    return {
        "total_open": total_open,
        "overdue": overdue,
        "due_today": due_today,
        "due_this_week": due_this_week,
    }


def log_activity(
    sf: Salesforce,
    client_id: str,
    subject: str,
    activity_type: str,
    activity_date: str | None = None,
) -> dict:
    """Log a completed activity as a Salesforce Task.

    Creates a Task with Status='Completed' and appropriate TaskSubtype.

    Args:
        sf: Salesforce connection.
        client_id: 18-char Contact ID.
        subject: Activity description.
        activity_type: One of 'call', 'meeting', 'email', 'other'.
        activity_date: YYYY-MM-DD string, defaults to today. Cannot be future.

    Returns:
        Dict with task_id, subject, client_id, activity_type, activity_date, status.

    Raises:
        ValueError: If activity_date is in the future or activity_type is invalid.
    """
    if activity_type not in _ACTIVITY_TYPE_MAP:
        raise ValueError(
            f"Invalid activity type '{activity_type}'. "
            f"Valid types: {', '.join(_ACTIVITY_TYPE_MAP.keys())}"
        )

    if activity_date is None:
        activity_date = date.today().isoformat()
    elif activity_date > date.today().isoformat():
        raise ValueError(
            f"Activity date cannot be in the future (got {activity_date})."
        )

    subtype = _ACTIVITY_TYPE_MAP[activity_type]
    task_data: dict = {
        "WhoId": client_id,
        "Subject": subject,
        "ActivityDate": activity_date,
        "Status": "Completed",
        "Priority": "Normal",
        "Description": f"{ADVISOR_AGENT_TAG} Logged via advisor-agent CLI",
    }
    if subtype is not None:
        task_data["TaskSubtype"] = subtype

    result = sf.Task.create(task_data)
    return {
        "task_id": result["id"],
        "subject": subject,
        "client_id": client_id,
        "activity_type": activity_type,
        "activity_date": activity_date,
        "status": "Completed",
    }


def get_outreach_queue(
    sf: Salesforce,
    days: int,
    min_value: float = 0,
) -> list[dict]:
    """Generate a prioritized outreach queue of clients not contacted recently.

    Queries all Contacts and their last Task activity date (from ALL tasks,
    not just [advisor-agent]-tagged) to find clients who need outreach.

    Args:
        sf: Salesforce connection.
        days: Minimum days since last contact. 0 means all contacts.
        min_value: Minimum Account_Value__c filter.

    Returns:
        List of dicts sorted by account value (desc), each with client_id,
        name, account_value, last_activity_date, days_since_contact.
    """
    conditions = []
    if min_value > 0:
        conditions.append(f"Account_Value__c >= {min_value}")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    soql = (
        "SELECT Id, FirstName, LastName, Account_Value__c, "
        "(SELECT ActivityDate FROM Tasks ORDER BY ActivityDate DESC LIMIT 1) "
        f"FROM Contact {where} "
        "ORDER BY Account_Value__c DESC NULLS LAST"
    )
    result = sf.query(soql)

    today = date.today()
    queue = []

    for rec in result.get("records", []):
        # Extract last activity date from subquery
        tasks = rec.get("Tasks")
        last_activity = None
        if tasks and tasks.get("records"):
            last_activity = tasks["records"][0].get("ActivityDate")

        if days > 0:
            if last_activity:
                activity_date = date.fromisoformat(last_activity)
                days_since = (today - activity_date).days
                if days_since < days:
                    continue  # Contacted recently — skip
            else:
                days_since = 9999  # Never contacted
        else:
            # days=0 means all contacts
            if last_activity:
                activity_date = date.fromisoformat(last_activity)
                days_since = (today - activity_date).days
            else:
                days_since = 9999

        name = f"{rec.get('FirstName') or ''} {rec.get('LastName') or ''}".strip()
        queue.append({
            "client_id": rec["Id"],
            "name": name,
            "account_value": rec.get("Account_Value__c") or 0,
            "last_activity_date": last_activity or "",
            "days_since_contact": days_since,
        })

    return queue


def create_outreach_tasks(
    sf: Salesforce,
    contacts: list[dict],
    days: int,
) -> dict:
    """Create follow-up tasks for outreach queue contacts.

    Checks for existing open [advisor-agent]-tagged tasks on each contact
    and skips those that already have one (dedup).

    Args:
        sf: Salesforce connection.
        contacts: List from get_outreach_queue().
        days: Used in the task subject.

    Returns:
        Dict with tasks_created, tasks_skipped, and skipped_reasons list.
    """
    created = 0
    skipped = 0
    skipped_reasons: list[dict] = []

    for contact in contacts:
        client_id = contact["client_id"]
        safe_id = _soql_escape(client_id)

        # Check for existing open [advisor-agent] task
        # (Description is a long text area — cannot use LIKE in SOQL, filter in Python)
        existing = sf.query(
            "SELECT Id, Subject, Description FROM Task "
            f"WHERE WhoId = '{safe_id}' "
            "AND Status != 'Completed'"
        )
        tagged_existing = [
            r for r in existing.get("records", [])
            if ADVISOR_AGENT_TAG in (r.get("Description") or "")
        ]

        if tagged_existing:
            skipped += 1
            skipped_reasons.append({
                "name": contact["name"],
                "reason": f"existing open task: {tagged_existing[0].get('Subject', '')}",
            })
            continue

        actual_days = contact["days_since_contact"]
        subject = f"Follow-up: No contact in {actual_days} days"
        create_task(sf, client_id, subject, due_date=date.today().isoformat())
        created += 1

    return {
        "tasks_created": created,
        "tasks_skipped": skipped,
        "skipped_reasons": skipped_reasons,
    }
