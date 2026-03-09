"""Unit tests for saved list CRUD (020-client-list-builder, US2)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from finance_agent.sandbox.models import CompoundFilter, QueryInterpretation, SavedList
from finance_agent.sandbox.list_builder import (
    save_list,
    get_saved_lists,
    get_saved_list,
    run_saved_list,
    update_saved_list,
    delete_saved_list,
    translate_nl_query,
    execute_nl_query,
)


@pytest.fixture
def sample_filters():
    return CompoundFilter(max_age=50, sort_by="account_value", sort_dir="desc", limit=50)


class TestSaveList:
    def test_save_creates_list(self, tmp_path, sample_filters):
        result = save_list("Top 50 Under 50", "High-value young clients", sample_filters, data_dir=tmp_path)
        assert isinstance(result, SavedList)
        assert result.name == "Top 50 Under 50"
        assert result.description == "High-value young clients"
        assert result.filters.max_age == 50
        assert result.created_at  # non-empty
        assert result.last_run_at is None

    def test_save_rejects_duplicate_name_case_insensitive(self, tmp_path, sample_filters):
        save_list("My List", "", sample_filters, data_dir=tmp_path)
        with pytest.raises(ValueError, match="already exists"):
            save_list("my list", "", sample_filters, data_dir=tmp_path)


class TestGetSavedLists:
    def test_returns_all_sorted(self, tmp_path, sample_filters):
        save_list("Zebra List", "", sample_filters, data_dir=tmp_path)
        save_list("Alpha List", "", sample_filters, data_dir=tmp_path)
        lists = get_saved_lists(data_dir=tmp_path)
        assert len(lists) == 2
        assert lists[0].name == "Alpha List"
        assert lists[1].name == "Zebra List"

    def test_empty_returns_empty(self, tmp_path):
        assert get_saved_lists(data_dir=tmp_path) == []


class TestGetSavedList:
    def test_finds_by_name_case_insensitive(self, tmp_path, sample_filters):
        save_list("My List", "", sample_filters, data_dir=tmp_path)
        result = get_saved_list("my list", data_dir=tmp_path)
        assert result is not None
        assert result.name == "My List"

    def test_returns_none_for_missing(self, tmp_path):
        assert get_saved_list("Nonexistent", data_dir=tmp_path) is None


class TestRunSavedList:
    def test_executes_filters(self, tmp_path, sample_filters):
        save_list("Test List", "", sample_filters, data_dir=tmp_path)
        mock_sf = MagicMock()
        mock_sf.query.return_value = {"records": [
            {"Id": "003xx1", "FirstName": "John", "LastName": "Doe", "Age__c": 40,
             "Account_Value__c": 300000, "Risk_Tolerance__c": "growth",
             "Life_Stage__c": "accumulation", "Tasks": None},
        ]}
        result = run_saved_list(mock_sf, "Test List", data_dir=tmp_path)
        assert "clients" in result
        assert result["count"] == 1
        # Verify last_run_at was updated
        updated = get_saved_list("Test List", data_dir=tmp_path)
        assert updated.last_run_at is not None

    def test_raises_for_missing_list(self, tmp_path):
        mock_sf = MagicMock()
        with pytest.raises(ValueError, match="not found"):
            run_saved_list(mock_sf, "Nonexistent", data_dir=tmp_path)


class TestUpdateSavedList:
    def test_updates_description(self, tmp_path, sample_filters):
        save_list("My List", "old desc", sample_filters, data_dir=tmp_path)
        result = update_saved_list("My List", {"description": "new desc"}, data_dir=tmp_path)
        assert result.description == "new desc"

    def test_updates_filters(self, tmp_path, sample_filters):
        save_list("My List", "", sample_filters, data_dir=tmp_path)
        new_filters = CompoundFilter(max_age=60, min_value=100000)
        result = update_saved_list("My List", {"filters": new_filters}, data_dir=tmp_path)
        assert result.filters.max_age == 60
        assert result.filters.min_value == 100000

    def test_renames_list(self, tmp_path, sample_filters):
        save_list("Old Name", "", sample_filters, data_dir=tmp_path)
        result = update_saved_list("Old Name", {"name": "New Name"}, data_dir=tmp_path)
        assert result.name == "New Name"
        assert get_saved_list("Old Name", data_dir=tmp_path) is None
        assert get_saved_list("New Name", data_dir=tmp_path) is not None

    def test_rejects_rename_to_existing(self, tmp_path, sample_filters):
        save_list("List A", "", sample_filters, data_dir=tmp_path)
        save_list("List B", "", sample_filters, data_dir=tmp_path)
        with pytest.raises(ValueError, match="already exists"):
            update_saved_list("List A", {"name": "List B"}, data_dir=tmp_path)

    def test_raises_for_missing(self, tmp_path, sample_filters):
        with pytest.raises(ValueError, match="not found"):
            update_saved_list("Nope", {"description": "x"}, data_dir=tmp_path)


class TestDeleteSavedList:
    def test_deletes_existing(self, tmp_path, sample_filters):
        save_list("My List", "", sample_filters, data_dir=tmp_path)
        assert delete_saved_list("My List", data_dir=tmp_path) is True
        assert get_saved_list("My List", data_dir=tmp_path) is None

    def test_returns_false_for_missing(self, tmp_path):
        assert delete_saved_list("Nope", data_dir=tmp_path) is False


class TestPersistence:
    def test_persists_across_calls(self, tmp_path, sample_filters):
        save_list("Persistent List", "desc", sample_filters, data_dir=tmp_path)
        # Read back in a separate call
        lists = get_saved_lists(data_dir=tmp_path)
        assert len(lists) == 1
        assert lists[0].name == "Persistent List"
        assert lists[0].description == "desc"


class TestTranslateNlQuery:
    def test_top_50_under_50(self):
        """'top 50 under 50' → max_age=50, sort_by=account_value, limit=50"""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                "filters": {"max_age": 50, "sort_by": "account_value", "sort_dir": "desc", "limit": 50},
                "filter_mapping": {"under 50": "max_age: 50", "top 50": "sort by account value, limit 50"},
                "unrecognized": [],
                "confidence": "high"
            }))]
        )
        result = translate_nl_query("top 50 under 50", anthropic_client=mock_client)
        assert isinstance(result, QueryInterpretation)
        assert result.filters.max_age == 50
        assert result.filters.limit == 50
        assert result.confidence == "high"
        assert result.original_query == "top 50 under 50"

    def test_not_contacted_3_months(self):
        """'clients not contacted in 3 months' → not_contacted_days=90"""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                "filters": {"not_contacted_days": 90},
                "filter_mapping": {"not contacted in 3 months": "not_contacted_days: 90"},
                "unrecognized": [],
                "confidence": "high"
            }))]
        )
        result = translate_nl_query("clients not contacted in 3 months", anthropic_client=mock_client)
        assert result.filters.not_contacted_days == 90
        assert "not contacted in 3 months" in result.filter_mapping

    def test_low_confidence_ambiguous(self):
        """Ambiguous query returns low confidence with unrecognized items"""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                "filters": {"sort_by": "account_value", "sort_dir": "desc", "limit": 50},
                "filter_mapping": {},
                "unrecognized": ["good"],
                "confidence": "low"
            }))]
        )
        result = translate_nl_query("show me the good clients", anthropic_client=mock_client)
        assert result.confidence == "low"
        assert "good" in result.unrecognized

    def test_filter_mapping_present(self):
        """Result includes filter_mapping dict"""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                "filters": {"max_age": 50},
                "filter_mapping": {"under 50": "max_age: 50"},
                "unrecognized": [],
                "confidence": "high"
            }))]
        )
        result = translate_nl_query("clients under 50", anthropic_client=mock_client)
        assert isinstance(result.filter_mapping, dict)
        assert len(result.filter_mapping) > 0


class TestExecuteNlQuery:
    def test_high_confidence_executes(self):
        """High confidence query executes and returns results"""
        mock_sf = MagicMock()
        mock_sf.query.return_value = {"records": [
            {"Id": "003xx1", "FirstName": "John", "LastName": "Doe", "Age__c": 40,
             "Account_Value__c": 300000, "Risk_Tolerance__c": "growth",
             "Life_Stage__c": "accumulation", "Tasks": None}
        ]}
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                "filters": {"max_age": 50},
                "filter_mapping": {"under 50": "max_age: 50"},
                "unrecognized": [],
                "confidence": "high"
            }))]
        )
        result = execute_nl_query(mock_sf, "clients under 50", anthropic_client=mock_anthropic)
        assert "clients" in result
        assert "filter_mapping" in result
        assert "original_query" in result

    def test_low_confidence_not_confirmed_skips(self):
        """Low confidence without confirmed=True returns interpretation only"""
        mock_sf = MagicMock()
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                "filters": {},
                "filter_mapping": {},
                "unrecognized": ["good"],
                "confidence": "low"
            }))]
        )
        result = execute_nl_query(mock_sf, "show me good clients", anthropic_client=mock_anthropic, confirmed=False)
        # Should NOT have executed (no "clients" key with actual results)
        assert "interpretation" in result
        assert result.get("executed") is False
        mock_sf.query.assert_not_called()

    def test_low_confidence_confirmed_executes(self):
        """Low confidence with confirmed=True executes query"""
        mock_sf = MagicMock()
        mock_sf.query.return_value = {"records": []}
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.return_value = MagicMock(
            content=[MagicMock(text=json.dumps({
                "filters": {"sort_by": "account_value"},
                "filter_mapping": {},
                "unrecognized": ["good"],
                "confidence": "low"
            }))]
        )
        result = execute_nl_query(mock_sf, "good clients", anthropic_client=mock_anthropic, confirmed=True)
        assert "clients" in result
        mock_sf.query.assert_called_once()
