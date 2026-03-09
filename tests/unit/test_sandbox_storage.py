"""Unit tests for sandbox storage CRUD against Salesforce (mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from finance_agent.sandbox.storage import (
    add_client,
    add_interaction,
    client_count,
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
