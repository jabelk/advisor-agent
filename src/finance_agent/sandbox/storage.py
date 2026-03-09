"""Client CRUD operations against Salesforce (Contact + Task objects)."""

from __future__ import annotations

from datetime import date, timedelta

from simple_salesforce import Salesforce

from finance_agent.sandbox.models import CompoundFilter

# ---------------------------------------------------------------------------
# Field mapping: local name -> Salesforce Contact API name
# ---------------------------------------------------------------------------

_CONTACT_FIELDS = {
    "first_name": "FirstName",
    "last_name": "LastName",
    "email": "Email",
    "phone": "Phone",
    "occupation": "Title",
    "notes": "Description",
    "age": "Age__c",
    "account_value": "Account_Value__c",
    "risk_tolerance": "Risk_Tolerance__c",
    "life_stage": "Life_Stage__c",
    "investment_goals": "Investment_Goals__c",
    "household_members": "Household_Members__c",
}

_SFDC_TO_LOCAL = {v: k for k, v in _CONTACT_FIELDS.items()}

_ALL_FIELDS = (
    "Id, FirstName, LastName, Email, Phone, Title, Description, "
    "Age__c, Account_Value__c, Risk_Tolerance__c, Life_Stage__c, "
    "Investment_Goals__c, Household_Members__c, CreatedDate, LastModifiedDate"
)

_SUMMARY_FIELDS = (
    "Id, FirstName, LastName, Age__c, Account_Value__c, Risk_Tolerance__c, Life_Stage__c"
)

# Map sort_by names to SOQL field names
_SORT_FIELD_MAP = {
    "account_value": "Account_Value__c",
    "age": "Age__c",
    "last_name": "LastName",
    "last_interaction_date": "LastActivityDate",
}


def _soql_escape(value: str) -> str:
    """Escape a string for use in SOQL single-quoted literals."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _to_local(record: dict) -> dict:
    """Convert a Salesforce Contact record to local field names."""
    result = {"id": record.get("Id", "")}
    for sfdc_name, local_name in _SFDC_TO_LOCAL.items():
        if sfdc_name in record:
            result[local_name] = record[sfdc_name]
    if "CreatedDate" in record:
        result["created_at"] = record["CreatedDate"]
    if "LastModifiedDate" in record:
        result["updated_at"] = record["LastModifiedDate"]
    return result


def _to_sfdc(client: dict) -> dict:
    """Convert local field names to Salesforce Contact API names."""
    result = {}
    for local_name, sfdc_name in _CONTACT_FIELDS.items():
        if local_name in client:
            result[sfdc_name] = client[local_name]
    return result


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


def add_client(sf: Salesforce, client: dict) -> str:
    """Insert a new Contact in Salesforce. Returns the Contact ID (18-char string)."""
    sfdc_data = _to_sfdc(client)
    # Allow duplicates — sandbox seed data may have similar names
    result = sf.Contact.create(sfdc_data, headers={"Sforce-Duplicate-Rule-Header": "allowSave=true"})
    return result["id"]


def get_client(sf: Salesforce, client_id: str) -> dict | None:
    """Fetch a single Contact by Salesforce ID, including Task history."""
    try:
        record = sf.Contact.get(client_id)
    except Exception:
        return None

    result = _to_local(record)

    # Query related Tasks as interaction history
    safe_id = _soql_escape(client_id)
    soql = (
        f"SELECT Id, ActivityDate, Description, Subject, CreatedDate "
        f"FROM Task WHERE WhoId = '{safe_id}' "
        f"ORDER BY ActivityDate DESC"
    )
    task_result = sf.query(soql)
    result["interactions"] = [
        {
            "id": t["Id"],
            "interaction_date": t.get("ActivityDate") or "",
            "interaction_type": t.get("Description") or "",
            "summary": t.get("Subject") or "",
            "created_at": t.get("CreatedDate") or "",
        }
        for t in task_result.get("records", [])
    ]
    return result


def list_clients(
    sf: Salesforce,
    risk_tolerance: str | None = None,
    life_stage: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    # --- Compound filter parameters (020-client-list-builder) ---
    min_age: int | None = None,
    max_age: int | None = None,
    risk_tolerances: list[str] | None = None,
    life_stages: list[str] | None = None,
    not_contacted_days: int | None = None,
    contacted_after: str | None = None,
    contacted_before: str | None = None,
    sort_by: str = "account_value",
    sort_dir: str = "desc",
) -> list[dict]:
    """List Contacts with optional filters. Returns summary dicts."""
    conditions: list[str] = []

    # Multi-value risk_tolerances overrides single risk_tolerance
    if risk_tolerances:
        escaped = ", ".join(f"'{_soql_escape(v)}'" for v in risk_tolerances)
        conditions.append(f"Risk_Tolerance__c IN ({escaped})")
    elif risk_tolerance:
        conditions.append(f"Risk_Tolerance__c = '{_soql_escape(risk_tolerance)}'")

    # Multi-value life_stages overrides single life_stage
    if life_stages:
        escaped = ", ".join(f"'{_soql_escape(v)}'" for v in life_stages)
        conditions.append(f"Life_Stage__c IN ({escaped})")
    elif life_stage:
        conditions.append(f"Life_Stage__c = '{_soql_escape(life_stage)}'")

    if min_value is not None:
        conditions.append(f"Account_Value__c >= {min_value}")
    if max_value is not None:
        conditions.append(f"Account_Value__c <= {max_value}")

    # Age range filters
    if min_age is not None:
        conditions.append(f"Age__c >= {min_age}")
    if max_age is not None:
        conditions.append(f"Age__c <= {max_age}")

    # Recency filter: not contacted in N days (or never contacted)
    if not_contacted_days is not None:
        cutoff = (date.today() - timedelta(days=not_contacted_days)).isoformat()
        conditions.append(
            f"(LastActivityDate < {cutoff} OR LastActivityDate = null)"
        )

    # Absolute date range filters on LastActivityDate
    if contacted_after is not None:
        conditions.append(f"LastActivityDate >= {contacted_after}")
    if contacted_before is not None:
        conditions.append(f"LastActivityDate <= {contacted_before}")

    if search:
        safe = _soql_escape(search)
        conditions.append(
            f"(FirstName LIKE '%{safe}%' OR LastName LIKE '%{safe}%')"
        )

    where = f"WHERE {' AND '.join(conditions)} " if conditions else ""

    # Resolve sort field
    sort_field = _SORT_FIELD_MAP.get(sort_by, "Account_Value__c")
    direction = "ASC" if sort_dir == "asc" else "DESC"

    # Use relationship subquery to get most recent Task date for display
    soql = (
        f"SELECT {_SUMMARY_FIELDS}, "
        f"(SELECT ActivityDate FROM Tasks ORDER BY ActivityDate DESC LIMIT 1) "
        f"FROM Contact {where}"
        f"ORDER BY {sort_field} {direction} NULLS LAST "
        f"LIMIT {limit} OFFSET {offset}"
    )

    result = sf.query(soql)
    clients = []
    for rec in result.get("records", []):
        # Extract last interaction date from subquery
        tasks_data = rec.get("Tasks")
        last_date = None
        if tasks_data and tasks_data.get("records"):
            last_date = tasks_data["records"][0].get("ActivityDate")

        clients.append({
            "id": rec["Id"],
            "first_name": rec.get("FirstName") or "",
            "last_name": rec.get("LastName") or "",
            "age": rec.get("Age__c"),
            "account_value": rec.get("Account_Value__c") or 0,
            "risk_tolerance": rec.get("Risk_Tolerance__c") or "",
            "life_stage": rec.get("Life_Stage__c") or "",
            "last_interaction_date": last_date,
        })
    return clients


def format_query_results(clients: list[dict], filters: CompoundFilter) -> dict:
    """Format query results with filter summary and count."""
    return {
        "clients": clients,
        "count": len(clients),
        "requested_limit": filters.limit,
        "filters_applied": filters.describe(),
    }


def update_client(sf: Salesforce, client_id: str, updates: dict) -> bool:
    """Update Contact fields. Returns True if successful, False if not found."""
    allowed = {
        "first_name", "last_name", "age", "occupation", "email", "phone",
        "account_value", "risk_tolerance", "investment_goals", "life_stage",
        "household_members", "notes",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return True

    sfdc_data = _to_sfdc(filtered)
    try:
        sf.Contact.update(client_id, sfdc_data)
        return True
    except Exception:
        return False


def add_interaction(sf: Salesforce, client_id: str, interaction: dict) -> str:
    """Create a Task record linked to a Contact. Returns Task ID."""
    # Map interaction_type to Subject prefix; use Description for the type
    itype = interaction.get("interaction_type", "Other")
    task_data = {
        "WhoId": client_id,
        "ActivityDate": interaction["interaction_date"],
        "Subject": interaction["summary"],
        "Description": itype,
        "Status": "Completed",
    }
    result = sf.Task.create(task_data)
    return result["id"]


def client_count(sf: Salesforce) -> int:
    """Return total number of Contacts in the org."""
    result = sf.query("SELECT COUNT() FROM Contact")
    return result["totalSize"]
