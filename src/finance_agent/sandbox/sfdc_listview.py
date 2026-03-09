"""ListView translation and Metadata API operations for Salesforce List Views.

Translates CompoundFilter instances into Salesforce ListView filter format
for the Contact object, handling field mapping, unsupported filter warnings,
and DeveloperName sanitization.
"""

from __future__ import annotations

import re

from simple_salesforce import Salesforce

from finance_agent.sandbox.models import CompoundFilter

DEFAULT_LISTVIEW_COLUMNS = [
    "FULL_NAME",
    "CONTACT_EMAIL",
    "CONTACT_PHONE",
    "Contact.Age__c",
    "Contact.Account_Value__c",
    "Contact.Risk_Tolerance__c",
    "Contact.Life_Stage__c",
]


def _sanitize_developer_name(name: str) -> str:
    """Convert a display name to a valid Salesforce DeveloperName.

    Replaces spaces and special characters with underscores, removes consecutive
    underscores, strips leading/trailing underscores, and truncates to 40 characters.
    """
    # Replace any non-alphanumeric/underscore character with underscore
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # Remove consecutive underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    # Strip leading/trailing underscores
    sanitized = sanitized.strip("_")
    # Truncate to 40 characters
    sanitized = sanitized[:40]
    return sanitized


def translate_filters_to_listview(
    filters: CompoundFilter,
) -> tuple[list[dict], list[str]]:
    """Translate a CompoundFilter into Salesforce ListView filter format.

    Returns a tuple of (filters_list, warnings_list) where filters_list contains
    Salesforce ListView filter dicts and warnings_list contains messages about
    unsupported filters that were omitted.

    A maximum of 10 filters are supported; excess filters are truncated with a warning.
    """
    lv_filters: list[dict] = []
    warnings: list[str] = []

    # --- Supported filter mappings ---

    if filters.min_age is not None:
        lv_filters.append({
            "field": "Age__c",
            "operation": "greaterOrEqual",
            "value": str(filters.min_age),
        })

    if filters.max_age is not None:
        lv_filters.append({
            "field": "Age__c",
            "operation": "lessOrEqual",
            "value": str(filters.max_age),
        })

    if filters.min_value is not None:
        lv_filters.append({
            "field": "Account_Value__c",
            "operation": "greaterOrEqual",
            "value": str(filters.min_value),
        })

    if filters.max_value is not None:
        lv_filters.append({
            "field": "Account_Value__c",
            "operation": "lessOrEqual",
            "value": str(filters.max_value),
        })

    if filters.risk_tolerances:
        lv_filters.append({
            "field": "Risk_Tolerance__c",
            "operation": "equals",
            "value": ",".join(filters.risk_tolerances),
        })

    if filters.life_stages:
        lv_filters.append({
            "field": "Life_Stage__c",
            "operation": "equals",
            "value": ",".join(filters.life_stages),
        })

    if filters.contacted_after is not None:
        lv_filters.append({
            "field": "ACTIVITY_DATE",
            "operation": "greaterOrEqual",
            "value": filters.contacted_after,
        })

    if filters.contacted_before is not None:
        lv_filters.append({
            "field": "ACTIVITY_DATE",
            "operation": "lessOrEqual",
            "value": filters.contacted_before,
        })

    # --- Unsupported filters — generate warnings ---

    if filters.not_contacted_days is not None:
        warnings.append(
            f"not_contacted_days ({filters.not_contacted_days} days) "
            "cannot be represented in List View filters — omitted"
        )

    if filters.search is not None:
        warnings.append(
            "search filter cannot be represented in List View filters — omitted"
        )

    # Sort warning (only warn once for sort_by and sort_dir together)
    sort_non_default = (filters.sort_by != "account_value") or (filters.sort_dir != "desc")
    if sort_non_default:
        warnings.append(
            "sort_by/sort_dir not supported in List Views "
            "(Salesforce applies default sort)"
        )

    if filters.limit != 50:
        warnings.append(
            "limit not supported in List Views (all matching contacts shown)"
        )

    # --- Enforce max 10 filter limit ---

    if len(lv_filters) > 10:
        lv_filters = lv_filters[:10]
        warnings.append(
            "List View filter limit (10) exceeded — some filters truncated"
        )

    return lv_filters, warnings


def create_listview(sf: Salesforce, name: str, filters: CompoundFilter) -> dict:
    """Create or update a Salesforce ListView from a CompoundFilter.

    Implements upsert behavior: if a ListView with the same DeveloperName exists,
    it is updated; otherwise a new one is created.

    Args:
        sf: Salesforce connection instance.
        name: Display name (without AA: prefix — this function adds it).
        filters: CompoundFilter instance with the filter criteria.

    Returns:
        Dict with id, name, developer_name, url, warnings, filters_applied.
    """
    dev_name = "AA_" + _sanitize_developer_name(name)
    label = f"AA: {name}"
    lv_filters, warnings = translate_filters_to_listview(filters)

    full_name = f"Contact.{dev_name}"
    metadata = {
        "fullName": full_name,
        "label": label,
        "filterScope": "Everything",
        "columns": DEFAULT_LISTVIEW_COLUMNS,
    }
    if lv_filters:
        metadata["filters"] = lv_filters

    # Check if ListView already exists (upsert)
    existing = sf.query(
        f"SELECT Id, DeveloperName FROM ListView "
        f"WHERE SobjectType = 'Contact' AND DeveloperName = '{dev_name}'"
    )

    if existing.get("records"):
        # Update existing
        sf.mdapi.ListView.update(full_name, metadata)
        lv_id = existing["records"][0]["Id"]
    else:
        # Create new
        sf.mdapi.ListView.create(metadata)
        # Query back to get the ID
        created = sf.query(
            f"SELECT Id FROM ListView "
            f"WHERE SobjectType = 'Contact' AND DeveloperName = '{dev_name}'"
        )
        lv_id = created["records"][0]["Id"]

    # Build Salesforce Lightning URL
    url = f"https://{sf.sf_instance}/lightning/o/Contact/list?filterName={lv_id}"

    if warnings:
        warnings.append(
            "The Salesforce List View may show more results than the CLI query"
        )

    return {
        "id": lv_id,
        "name": label,
        "developer_name": dev_name,
        "url": url,
        "warnings": warnings,
        "filters_applied": filters.describe(),
    }


def list_listviews(sf: Salesforce) -> list[dict]:
    """List all tool-created ListViews on the Contact object.

    Returns a sorted list of dicts with id, name, developer_name, url.
    Only ListViews with the AA_ DeveloperName prefix are returned.
    """
    result = sf.query(
        "SELECT Id, DeveloperName, Name FROM ListView "
        "WHERE SobjectType = 'Contact' AND DeveloperName LIKE 'AA_%'"
    )

    views = []
    for rec in result.get("records", []):
        display_name = rec["Name"]
        if display_name.startswith("AA: "):
            display_name = display_name[4:]
        views.append({
            "id": rec["Id"],
            "name": display_name,
            "developer_name": rec["DeveloperName"],
            "url": f"https://{sf.sf_instance}/lightning/o/Contact/list?filterName={rec['Id']}",
        })

    return sorted(views, key=lambda v: v["name"].lower())


def delete_listview(sf: Salesforce, name: str) -> bool:
    """Delete a tool-created ListView by display name.

    Args:
        sf: Salesforce connection instance.
        name: Display name (without AA: prefix — function matches with prefix).

    Returns:
        True if deleted, False if not found.
    """
    dev_name = "AA_" + _sanitize_developer_name(name)
    full_name = f"Contact.{dev_name}"

    # Case-insensitive: query all AA_ views and match
    result = sf.query(
        "SELECT Id, DeveloperName FROM ListView "
        "WHERE SobjectType = 'Contact' AND DeveloperName LIKE 'AA_%'"
    )

    for rec in result.get("records", []):
        if rec["DeveloperName"].lower() == dev_name.lower():
            actual_full_name = f"Contact.{rec['DeveloperName']}"
            sf.mdapi.ListView.delete(actual_full_name)
            return True

    return False
