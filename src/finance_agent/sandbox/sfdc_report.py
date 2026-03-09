"""Report translation + Analytics REST API operations for Salesforce Reports.

Translates CompoundFilter instances into Salesforce Report filter format
for the Contact object, handling field mapping, unsupported filter warnings,
and report folder management via the Analytics REST API.
"""

from __future__ import annotations

from simple_salesforce import Salesforce

from finance_agent.sandbox.models import CompoundFilter

DEFAULT_REPORT_COLUMNS = [
    "FIRST_NAME",
    "LAST_NAME",
    "Contact.Age__c",
    "Contact.Account_Value__c",
    "Contact.Risk_Tolerance__c",
    "Contact.Life_Stage__c",
    "LAST_ACTIVITY",
]

REPORT_FOLDER_NAME = "Client Lists"
ADVISOR_AGENT_TAG = "[advisor-agent]"

# Module-level cache for the report folder ID
_folder_id_cache: str | None = None


def translate_filters_to_report(
    filters: CompoundFilter,
) -> tuple[list[dict], list[str]]:
    """Translate a CompoundFilter into Salesforce Report filter format.

    Returns a tuple of (filters_list, warnings_list) where filters_list contains
    Salesforce Report filter dicts and warnings_list contains messages about
    unsupported or partially supported filters.
    """
    rpt_filters: list[dict] = []
    warnings: list[str] = []

    # --- Supported filter mappings ---

    if filters.min_age is not None:
        rpt_filters.append({
            "column": "Contact.Age__c",
            "operator": "greaterOrEqual",
            "value": str(filters.min_age),
        })

    if filters.max_age is not None:
        rpt_filters.append({
            "column": "Contact.Age__c",
            "operator": "lessOrEqual",
            "value": str(filters.max_age),
        })

    if filters.min_value is not None:
        rpt_filters.append({
            "column": "Contact.Account_Value__c",
            "operator": "greaterOrEqual",
            "value": str(filters.min_value),
        })

    if filters.max_value is not None:
        rpt_filters.append({
            "column": "Contact.Account_Value__c",
            "operator": "lessOrEqual",
            "value": str(filters.max_value),
        })

    if filters.risk_tolerances:
        rpt_filters.append({
            "column": "Contact.Risk_Tolerance__c",
            "operator": "equals",
            "value": ",".join(filters.risk_tolerances),
        })

    if filters.life_stages:
        rpt_filters.append({
            "column": "Contact.Life_Stage__c",
            "operator": "equals",
            "value": ",".join(filters.life_stages),
        })

    if filters.not_contacted_days is not None:
        rpt_filters.append({
            "column": "LAST_ACTIVITY",
            "operator": "equals",
            "value": f"LAST_N_DAYS:{filters.not_contacted_days}",
        })

    if filters.contacted_after is not None:
        rpt_filters.append({
            "column": "LAST_ACTIVITY",
            "operator": "greaterOrEqual",
            "value": filters.contacted_after,
        })

    if filters.contacted_before is not None:
        rpt_filters.append({
            "column": "LAST_ACTIVITY",
            "operator": "lessOrEqual",
            "value": filters.contacted_before,
        })

    if filters.search is not None:
        rpt_filters.append({
            "column": "FIRST_NAME",
            "operator": "contains",
            "value": filters.search,
        })
        rpt_filters.append({
            "column": "LAST_NAME",
            "operator": "contains",
            "value": filters.search,
        })
        warnings.append(
            "search filter partially supported in Reports "
            "(per-column contains on name fields)"
        )

    # --- Unsupported filters — generate warnings ---

    # Sort warning (only warn once for sort_by and sort_dir together)
    sort_non_default = (filters.sort_by != "account_value") or (filters.sort_dir != "desc")
    if sort_non_default:
        warnings.append(
            "sort_by/sort_dir not supported in Reports "
            "(Salesforce applies default sort)"
        )

    if filters.limit != 50:
        warnings.append(
            "limit not supported in Reports (all matching contacts shown)"
        )

    return rpt_filters, warnings


def ensure_report_folder(sf: Salesforce) -> str:
    """Get or create the 'Client Lists' report folder.

    Uses a module-level cache to avoid redundant queries. Returns the
    Salesforce ID of the folder.
    """
    global _folder_id_cache

    if _folder_id_cache is not None:
        return _folder_id_cache

    # Check if the folder already exists
    result = sf.query(
        "SELECT Id, Name FROM Folder "
        "WHERE Name = 'Client Lists' AND Type = 'Report'"
    )

    if result.get("records"):
        _folder_id_cache = result["records"][0]["Id"]
        return _folder_id_cache

    # Create the folder via Analytics REST API
    resp = sf.restful(
        "analytics/report-folders",
        method="POST",
        json={
            "name": "Client Lists",
            "description": "[advisor-agent] Auto-created folder",
        },
    )
    _folder_id_cache = resp["id"]
    return _folder_id_cache


def create_report(sf: Salesforce, name: str, filters: CompoundFilter) -> dict:
    """Create or update a Salesforce Report from a CompoundFilter.

    Implements upsert behavior: if a report with the same AA: name exists among
    [advisor-agent]-tagged reports, it is updated; otherwise a new one is created.

    Args:
        sf: Salesforce connection instance.
        name: Display name (without AA: prefix — this function adds it).
        filters: CompoundFilter instance with the filter criteria.

    Returns:
        Dict with id, name, url, warnings, filters_applied, folder.
    """
    display_name = f"AA: {name}"
    description = f"{ADVISOR_AGENT_TAG} {filters.describe()}"
    rpt_filters, warnings = translate_filters_to_report(filters)
    folder_id = ensure_report_folder(sf)

    report_metadata = {
        "reportMetadata": {
            "name": display_name,
            "description": description,
            "reportFormat": "TABULAR",
            "reportType": {"type": "ContactList"},
            "detailColumns": DEFAULT_REPORT_COLUMNS,
            "reportFilters": rpt_filters,
            "folderId": folder_id,
        }
    }

    # Check for existing report with same name (upsert)
    existing = sf.query(
        "SELECT Id, Name FROM Report "
        f"WHERE Description LIKE '%{ADVISOR_AGENT_TAG}%' "
        f"AND Name = '{display_name}'"
    )

    if existing.get("records"):
        report_id = existing["records"][0]["Id"]
        sf.restful(
            f"analytics/reports/{report_id}",
            method="PATCH",
            json=report_metadata,
        )
    else:
        resp = sf.restful(
            "analytics/reports",
            method="POST",
            json=report_metadata,
        )
        report_id = resp["reportMetadata"]["id"]

    url = f"https://{sf.sf_instance}/lightning/r/Report/{report_id}/view"

    return {
        "id": report_id,
        "name": display_name,
        "url": url,
        "warnings": warnings,
        "filters_applied": filters.describe(),
        "folder": REPORT_FOLDER_NAME,
    }


def list_reports(sf: Salesforce) -> list[dict]:
    """List all tool-created Reports.

    Returns a sorted list of dicts with id, name, url, description.
    Only reports with the [advisor-agent] description tag are returned.
    """
    result = sf.query(
        "SELECT Id, Name, Description, LastRunDate FROM Report "
        f"WHERE Description LIKE '%{ADVISOR_AGENT_TAG}%'"
    )

    reports = []
    for rec in result.get("records", []):
        display_name = rec["Name"]
        if display_name.startswith("AA: "):
            display_name = display_name[4:]
        reports.append({
            "id": rec["Id"],
            "name": display_name,
            "url": f"https://{sf.sf_instance}/lightning/r/Report/{rec['Id']}/view",
            "description": rec.get("Description") or "",
            "last_run_date": rec.get("LastRunDate"),
        })

    return sorted(reports, key=lambda r: r["name"].lower())


def delete_report(sf: Salesforce, name: str) -> bool:
    """Delete a tool-created Report by display name.

    Args:
        sf: Salesforce connection instance.
        name: Display name (without AA: prefix — function matches with prefix).

    Returns:
        True if deleted, False if not found.
    """
    target_name = f"AA: {name}"

    result = sf.query(
        "SELECT Id, Name FROM Report "
        f"WHERE Description LIKE '%{ADVISOR_AGENT_TAG}%'"
    )

    for rec in result.get("records", []):
        if rec["Name"].lower() == target_name.lower():
            sf.restful(f"analytics/reports/{rec['Id']}", method="DELETE")
            return True

    return False
