"""Unit tests for sandbox storage CRUD against Salesforce (mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datetime import date, timedelta

from finance_agent.sandbox.models import CompoundFilter
from finance_agent.sandbox.storage import (
    add_client,
    add_interaction,
    client_count,
    format_query_results,
    get_client,
    list_clients,
    update_client,
)


@pytest.fixture
def mock_sf():
    """Create a mock Salesforce client."""
    return MagicMock()


class TestAddClient:
    def test_returns_salesforce_id(self, mock_sf):
        mock_sf.Contact.create.return_value = {"id": "003xx000004TmiUAAS", "success": True}
        cid = add_client(mock_sf, {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "555-123-4567",
            "occupation": "Engineer",
            "age": 35,
            "account_value": 100000,
            "risk_tolerance": "moderate",
            "life_stage": "accumulation",
        })
        assert cid == "003xx000004TmiUAAS"
        mock_sf.Contact.create.assert_called_once()

    def test_maps_fields_to_sfdc(self, mock_sf):
        mock_sf.Contact.create.return_value = {"id": "003xx", "success": True}
        add_client(mock_sf, {
            "first_name": "Jane",
            "last_name": "Smith",
            "occupation": "Attorney",
            "notes": "VIP client",
            "age": 45,
            "account_value": 500000,
            "risk_tolerance": "growth",
            "life_stage": "pre-retirement",
        })
        call_data = mock_sf.Contact.create.call_args[0][0]
        assert call_data["FirstName"] == "Jane"
        assert call_data["LastName"] == "Smith"
        assert call_data["Title"] == "Attorney"
        assert call_data["Description"] == "VIP client"
        assert call_data["Age__c"] == 45
        assert call_data["Account_Value__c"] == 500000
        assert call_data["Risk_Tolerance__c"] == "growth"
        assert call_data["Life_Stage__c"] == "pre-retirement"


class TestGetClient:
    def test_returns_client_with_interactions(self, mock_sf):
        mock_sf.Contact.get.return_value = {
            "Id": "003xx000004TmiUAAS",
            "FirstName": "John",
            "LastName": "Doe",
            "Email": "john.doe@example.com",
            "Phone": "555-123-4567",
            "Title": "Engineer",
            "Description": "Notes here",
            "Age__c": 35,
            "Account_Value__c": 100000.0,
            "Risk_Tolerance__c": "moderate",
            "Life_Stage__c": "accumulation",
            "Investment_Goals__c": "Retirement planning",
            "Household_Members__c": '["Spouse"]',
            "CreatedDate": "2025-01-01T00:00:00.000+0000",
            "LastModifiedDate": "2025-06-01T00:00:00.000+0000",
        }
        mock_sf.query.return_value = {
            "records": [
                {"Id": "00Txx1", "ActivityDate": "2025-05-01", "Description": "Call",
                 "Subject": "Quarterly review", "CreatedDate": "2025-05-01T10:00:00.000+0000"},
                {"Id": "00Txx2", "ActivityDate": "2025-03-15", "Description": "Email",
                 "Subject": "Follow up", "CreatedDate": "2025-03-15T09:00:00.000+0000"},
            ]
        }

        result = get_client(mock_sf, "003xx000004TmiUAAS")
        assert result is not None
        assert result["id"] == "003xx000004TmiUAAS"
        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        assert result["occupation"] == "Engineer"
        assert result["account_value"] == 100000.0
        assert result["risk_tolerance"] == "moderate"
        assert len(result["interactions"]) == 2
        assert result["interactions"][0]["interaction_type"] == "Call"

    def test_not_found_returns_none(self, mock_sf):
        mock_sf.Contact.get.side_effect = Exception("NOT_FOUND")
        result = get_client(mock_sf, "003xxNONEXISTENT")
        assert result is None


class TestListClients:
    def test_default_query(self, mock_sf):
        mock_sf.query.return_value = {
            "records": [
                {"Id": "003xx1", "FirstName": "John", "LastName": "Doe",
                 "Account_Value__c": 200000, "Risk_Tolerance__c": "growth",
                 "Life_Stage__c": "accumulation", "Tasks": None},
            ]
        }
        clients = list_clients(mock_sf)
        assert len(clients) == 1
        assert clients[0]["first_name"] == "John"
        assert clients[0]["account_value"] == 200000
        soql = mock_sf.query.call_args[0][0]
        assert "FROM Contact" in soql
        assert "ORDER BY Account_Value__c DESC" in soql

    def test_filter_by_risk(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf, risk_tolerance="growth")
        soql = mock_sf.query.call_args[0][0]
        assert "Risk_Tolerance__c = 'growth'" in soql

    def test_filter_by_life_stage(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf, life_stage="retirement")
        soql = mock_sf.query.call_args[0][0]
        assert "Life_Stage__c = 'retirement'" in soql

    def test_filter_by_min_value(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf, min_value=100000)
        soql = mock_sf.query.call_args[0][0]
        assert "Account_Value__c >= 100000" in soql

    def test_filter_by_max_value(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf, max_value=500000)
        soql = mock_sf.query.call_args[0][0]
        assert "Account_Value__c <= 500000" in soql

    def test_search_by_name(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf, search="Smith")
        soql = mock_sf.query.call_args[0][0]
        assert "FirstName LIKE '%Smith%'" in soql
        assert "LastName LIKE '%Smith%'" in soql

    def test_last_interaction_from_subquery(self, mock_sf):
        mock_sf.query.return_value = {
            "records": [
                {"Id": "003xx1", "FirstName": "John", "LastName": "Doe",
                 "Account_Value__c": 200000, "Risk_Tolerance__c": "growth",
                 "Life_Stage__c": "accumulation",
                 "Tasks": {"records": [{"ActivityDate": "2025-05-01"}]}},
            ]
        }
        clients = list_clients(mock_sf)
        assert clients[0]["last_interaction_date"] == "2025-05-01"

    def test_no_tasks_returns_none_date(self, mock_sf):
        mock_sf.query.return_value = {
            "records": [
                {"Id": "003xx1", "FirstName": "John", "LastName": "Doe",
                 "Account_Value__c": 200000, "Risk_Tolerance__c": "growth",
                 "Life_Stage__c": "accumulation", "Tasks": None},
            ]
        }
        clients = list_clients(mock_sf)
        assert clients[0]["last_interaction_date"] is None

    def test_sort_by_account_value_desc(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf)
        soql = mock_sf.query.call_args[0][0]
        assert "ORDER BY Account_Value__c DESC" in soql


class TestUpdateClient:
    def test_updates_fields(self, mock_sf):
        result = update_client(mock_sf, "003xx1", {"account_value": 250000, "risk_tolerance": "aggressive"})
        assert result is True
        call_data = mock_sf.Contact.update.call_args[0][1]
        assert call_data["Account_Value__c"] == 250000
        assert call_data["Risk_Tolerance__c"] == "aggressive"

    def test_nonexistent_returns_false(self, mock_sf):
        mock_sf.Contact.update.side_effect = Exception("NOT_FOUND")
        result = update_client(mock_sf, "003xxBAD", {"account_value": 100})
        assert result is False

    def test_empty_updates_returns_true(self, mock_sf):
        result = update_client(mock_sf, "003xx1", {})
        assert result is True
        mock_sf.Contact.update.assert_not_called()

    def test_filters_disallowed_fields(self, mock_sf):
        update_client(mock_sf, "003xx1", {"account_value": 100, "hacker_field": "bad"})
        call_data = mock_sf.Contact.update.call_args[0][1]
        assert "Account_Value__c" in call_data
        assert "hacker_field" not in call_data


class TestAddInteraction:
    def test_creates_task(self, mock_sf):
        mock_sf.Task.create.return_value = {"id": "00Txx001", "success": True}
        tid = add_interaction(mock_sf, "003xx1", {
            "interaction_date": "2025-06-01",
            "interaction_type": "Call",
            "summary": "Quarterly review",
        })
        assert tid == "00Txx001"
        call_data = mock_sf.Task.create.call_args[0][0]
        assert call_data["WhoId"] == "003xx1"
        assert call_data["ActivityDate"] == "2025-06-01"
        assert call_data["Description"] == "Call"
        assert call_data["Subject"] == "Quarterly review"
        assert call_data["Status"] == "Completed"


class TestClientCount:
    def test_returns_count(self, mock_sf):
        mock_sf.query.return_value = {"totalSize": 42, "records": []}
        count = client_count(mock_sf)
        assert count == 42
        soql = mock_sf.query.call_args[0][0]
        assert "COUNT()" in soql


# Helper: a minimal Contact record for list_clients, including Age__c
def _make_record(
    id_="003xx1",
    first="John",
    last="Doe",
    age=35,
    value=200000,
    risk="growth",
    stage="accumulation",
    tasks=None,
):
    return {
        "Id": id_,
        "FirstName": first,
        "LastName": last,
        "Age__c": age,
        "Account_Value__c": value,
        "Risk_Tolerance__c": risk,
        "Life_Stage__c": stage,
        "Tasks": tasks,
    }


class TestCompoundFilters:
    """Tests for compound filter parameters added in 020-client-list-builder."""

    def test_age_range_filter(self, mock_sf):
        mock_sf.query.return_value = {"records": [_make_record(age=40)]}
        clients = list_clients(mock_sf, min_age=30, max_age=50)
        soql = mock_sf.query.call_args[0][0]
        assert "Age__c >= 30" in soql
        assert "Age__c <= 50" in soql
        assert len(clients) == 1

    def test_multi_risk_tolerances(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf, risk_tolerances=["growth", "aggressive"])
        soql = mock_sf.query.call_args[0][0]
        assert "Risk_Tolerance__c IN ('growth', 'aggressive')" in soql

    def test_multi_life_stages(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf, life_stages=["accumulation", "pre-retirement"])
        soql = mock_sf.query.call_args[0][0]
        assert "Life_Stage__c IN ('accumulation', 'pre-retirement')" in soql

    def test_risk_tolerances_overrides_single(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(
            mock_sf,
            risk_tolerance="moderate",
            risk_tolerances=["growth"],
        )
        soql = mock_sf.query.call_args[0][0]
        assert "Risk_Tolerance__c IN ('growth')" in soql
        assert "Risk_Tolerance__c = 'moderate'" not in soql

    def test_not_contacted_days(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf, not_contacted_days=90)
        soql = mock_sf.query.call_args[0][0]
        cutoff = (date.today() - timedelta(days=90)).isoformat()
        assert f"(LastActivityDate < {cutoff} OR LastActivityDate = null)" in soql

    def test_contacted_after_before(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(
            mock_sf,
            contacted_after="2026-01-01",
            contacted_before="2026-03-31",
        )
        soql = mock_sf.query.call_args[0][0]
        assert "LastActivityDate >= 2026-01-01" in soql
        assert "LastActivityDate <= 2026-03-31" in soql

    def test_combined_compound_filter(self, mock_sf):
        mock_sf.query.return_value = {
            "records": [_make_record(age=35, value=300000, risk="growth")]
        }
        clients = list_clients(
            mock_sf,
            min_age=25,
            max_age=50,
            risk_tolerances=["growth"],
            min_value=200000,
        )
        soql = mock_sf.query.call_args[0][0]
        assert "Age__c >= 25" in soql
        assert "Age__c <= 50" in soql
        assert "Risk_Tolerance__c IN ('growth')" in soql
        assert "Account_Value__c >= 200000" in soql
        assert len(clients) == 1

    def test_sort_by_age_asc(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf, sort_by="age", sort_dir="asc")
        soql = mock_sf.query.call_args[0][0]
        assert "ORDER BY Age__c ASC" in soql

    def test_sort_by_last_name(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf, sort_by="last_name")
        soql = mock_sf.query.call_args[0][0]
        assert "ORDER BY LastName DESC" in soql

    def test_sort_by_last_interaction_date(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf, sort_by="last_interaction_date")
        soql = mock_sf.query.call_args[0][0]
        assert "ORDER BY LastActivityDate DESC" in soql

    def test_backward_compat_single_risk(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        list_clients(mock_sf, risk_tolerance="growth")
        soql = mock_sf.query.call_args[0][0]
        assert "Risk_Tolerance__c = 'growth'" in soql

    def test_age_in_results(self, mock_sf):
        mock_sf.query.return_value = {
            "records": [_make_record(age=42)]
        }
        clients = list_clients(mock_sf)
        assert clients[0]["age"] == 42

    def test_format_query_results(self, mock_sf):
        clients = [
            {"id": "003xx1", "first_name": "John", "last_name": "Doe",
             "age": 35, "account_value": 200000, "risk_tolerance": "growth",
             "life_stage": "accumulation", "last_interaction_date": None},
            {"id": "003xx2", "first_name": "Jane", "last_name": "Smith",
             "age": 45, "account_value": 500000, "risk_tolerance": "moderate",
             "life_stage": "pre-retirement", "last_interaction_date": "2026-02-01"},
        ]
        filters = CompoundFilter(
            min_age=30,
            max_age=50,
            risk_tolerances=["growth", "moderate"],
            limit=25,
        )
        result = format_query_results(clients, filters)
        assert result["clients"] is clients
        assert result["count"] == 2
        assert result["requested_limit"] == 25
        assert "age 30" in result["filters_applied"]
        assert "risk: growth, moderate" in result["filters_applied"]
