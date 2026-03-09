"""Salesforce connection helper using OAuth2.

Tries Client Credentials flow first (preferred for service-to-service),
then falls back to username-password flow.

Requires environment variables:
  SFDC_INSTANCE_URL, SFDC_CONSUMER_KEY, SFDC_CONSUMER_SECRET
  (optional) SFDC_USERNAME, SFDC_PASSWORD, SFDC_SECURITY_TOKEN, SFDC_LOGIN_URL
"""

from __future__ import annotations

import io
import json
import os
import time
import zipfile

import requests
from simple_salesforce import Salesforce

# Fields we need on the Contact object for advisor workflow data
REQUIRED_CUSTOM_FIELDS = [
    "Age__c", "Account_Value__c", "Risk_Tolerance__c",
    "Life_Stage__c", "Investment_Goals__c", "Household_Members__c",
]


def get_sf_client() -> Salesforce:
    """Create an authenticated Salesforce client.

    Returns a simple_salesforce.Salesforce instance.
    Raises RuntimeError if authentication fails.
    """
    instance_url = os.environ.get("SFDC_INSTANCE_URL", "")
    consumer_key = os.environ.get("SFDC_CONSUMER_KEY", "")
    consumer_secret = os.environ.get("SFDC_CONSUMER_SECRET", "")

    if not all([instance_url, consumer_key, consumer_secret]):
        raise RuntimeError(
            "Missing Salesforce credentials. Set SFDC_INSTANCE_URL, "
            "SFDC_CONSUMER_KEY, SFDC_CONSUMER_SECRET in .env"
        )

    # --- Try Client Credentials flow ---
    token_url = f"{instance_url}/services/oauth2/token"
    resp = requests.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": consumer_key,
            "client_secret": consumer_secret,
        },
        timeout=30,
    )

    if resp.status_code == 200:
        token_data = resp.json()
        return Salesforce(
            instance_url=token_data.get("instance_url", instance_url),
            session_id=token_data["access_token"],
        )

    # --- Fallback: username-password flow ---
    username = os.environ.get("SFDC_USERNAME", "")
    password = os.environ.get("SFDC_PASSWORD", "")
    security_token = os.environ.get("SFDC_SECURITY_TOKEN", "")

    if username and password:
        login_url = os.environ.get("SFDC_LOGIN_URL", "https://login.salesforce.com")
        resp2 = requests.post(
            f"{login_url}/services/oauth2/token",
            data={
                "grant_type": "password",
                "client_id": consumer_key,
                "client_secret": consumer_secret,
                "username": username,
                "password": password + security_token,
            },
            timeout=30,
        )

        if resp2.status_code == 200:
            token_data = resp2.json()
            return Salesforce(
                instance_url=token_data.get("instance_url", instance_url),
                session_id=token_data["access_token"],
            )

    # Both flows failed
    error_detail = resp.json() if resp.content else {"error": "no response"}
    raise RuntimeError(
        f"Salesforce authentication failed: {error_detail}\n"
        "Ensure your Connected App has:\n"
        "  1. 'Enable Client Credentials Flow' checked with Run As user set\n"
        "  2. 'Manage user data via APIs (api)' in Selected OAuth Scopes\n"
        "  3. Wait ~2 minutes after changes for Salesforce to propagate"
    )


# --- Custom field setup via Metadata Deploy REST API ---

_FIELDS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <fields>
        <fullName>Age__c</fullName>
        <label>Age</label>
        <type>Number</type>
        <precision>3</precision>
        <scale>0</scale>
        <required>false</required>
    </fields>
    <fields>
        <fullName>Account_Value__c</fullName>
        <label>Account Value</label>
        <type>Currency</type>
        <precision>18</precision>
        <scale>2</scale>
        <required>false</required>
    </fields>
    <fields>
        <fullName>Risk_Tolerance__c</fullName>
        <label>Risk Tolerance</label>
        <type>Text</type>
        <length>20</length>
        <required>false</required>
    </fields>
    <fields>
        <fullName>Life_Stage__c</fullName>
        <label>Life Stage</label>
        <type>Text</type>
        <length>20</length>
        <required>false</required>
    </fields>
    <fields>
        <fullName>Investment_Goals__c</fullName>
        <label>Investment Goals</label>
        <type>LongTextArea</type>
        <length>5000</length>
        <visibleLines>3</visibleLines>
        <required>false</required>
    </fields>
    <fields>
        <fullName>Household_Members__c</fullName>
        <label>Household Members</label>
        <type>LongTextArea</type>
        <length>2000</length>
        <visibleLines>3</visibleLines>
        <required>false</required>
    </fields>
</CustomObject>"""

_PERM_SET_XML = """<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Advisor Agent Fields</label>
    <description>Grants access to custom Contact fields used by Advisor Agent</description>
    <fieldPermissions>
        <field>Contact.Age__c</field>
        <editable>true</editable>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <field>Contact.Account_Value__c</field>
        <editable>true</editable>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <field>Contact.Risk_Tolerance__c</field>
        <editable>true</editable>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <field>Contact.Life_Stage__c</field>
        <editable>true</editable>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <field>Contact.Investment_Goals__c</field>
        <editable>true</editable>
        <readable>true</readable>
    </fieldPermissions>
    <fieldPermissions>
        <field>Contact.Household_Members__c</field>
        <editable>true</editable>
        <readable>true</readable>
    </fieldPermissions>
</PermissionSet>"""


def ensure_custom_fields(sf: Salesforce) -> list[str]:
    """Create custom fields on Contact and grant FLS via PermissionSet.

    Uses the Metadata Deploy REST API (no SOAP required).
    Returns list of fields that were created (empty if all exist).
    """
    # Check which custom fields already exist
    desc = sf.Contact.describe()
    existing = {f["name"] for f in desc["fields"]}
    missing = [f for f in REQUIRED_CUSTOM_FIELDS if f not in existing]

    if not missing:
        return []

    # Build deployment zip with fields + permission set
    members = "\n        ".join(
        f"<members>Contact.{f}</members>" for f in REQUIRED_CUSTOM_FIELDS
    )
    package_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        {members}
        <name>CustomField</name>
    </types>
    <types>
        <members>Advisor_Agent_Fields</members>
        <name>PermissionSet</name>
    </types>
    <version>66.0</version>
</Package>"""

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("package.xml", package_xml)
        zf.writestr("objects/Contact.object", _FIELDS_XML)
        zf.writestr("permissionsets/Advisor_Agent_Fields.permissionset", _PERM_SET_XML)
    zip_buffer.seek(0)

    # Deploy via REST Metadata API
    api_version = sf.sf_version or "66.0"
    deploy_url = f"https://{sf.sf_instance}/services/data/v{api_version}/metadata/deployRequest"
    headers = {"Authorization": f"Bearer {sf.session_id}"}
    deploy_options = json.dumps({
        "deployOptions": {
            "allowMissingFiles": False,
            "checkOnly": False,
            "singlePackage": True,
            "rollbackOnError": True,
        }
    })

    resp = requests.post(
        deploy_url,
        headers=headers,
        files={
            "json": (None, deploy_options, "application/json"),
            "file": ("deploy.zip", zip_buffer, "application/zip"),
        },
        timeout=60,
    )
    resp.raise_for_status()
    deploy_id = resp.json().get("id")

    # Poll for completion
    for _ in range(20):
        time.sleep(3)
        status_resp = requests.get(
            f"{deploy_url}/{deploy_id}", headers=headers, timeout=30
        )
        result = status_resp.json().get("deployResult", {})
        status = result.get("status")
        if status == "Succeeded":
            break
        if status in ("Failed", "Canceled"):
            raise RuntimeError(f"Metadata deploy failed: {json.dumps(result)[:500]}")
    else:
        raise RuntimeError("Metadata deploy timed out after 60 seconds")

    # Assign permission set to the current user
    _assign_permission_set(sf)

    return missing


def _assign_permission_set(sf: Salesforce) -> None:
    """Assign the Advisor_Agent_Fields permission set to the current user."""
    ps = sf.query("SELECT Id FROM PermissionSet WHERE Name = 'Advisor_Agent_Fields'")
    if not ps.get("records"):
        return
    ps_id = ps["records"][0]["Id"]

    # Find current user
    username = os.environ.get("SFDC_USERNAME", "")
    if username:
        user = sf.query(f"SELECT Id FROM User WHERE Username = '{username}'")
        if user.get("records"):
            user_id = user["records"][0]["Id"]
            # Check if already assigned
            existing = sf.query(
                f"SELECT Id FROM PermissionSetAssignment "
                f"WHERE PermissionSetId = '{ps_id}' AND AssigneeId = '{user_id}'"
            )
            if not existing.get("records"):
                sf.PermissionSetAssignment.create(
                    {"PermissionSetId": ps_id, "AssigneeId": user_id}
                )
