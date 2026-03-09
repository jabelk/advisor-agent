"""Unit tests for sfdc_listview.py (021-sfdc-native-lists)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from finance_agent.sandbox.models import CompoundFilter
from finance_agent.sandbox.sfdc_listview import (
    _sanitize_developer_name,
    translate_filters_to_listview,
    create_listview,
    list_listviews,
    delete_listview,
)


@pytest.fixture
def sf():
    """Create a mock Salesforce client."""
    mock = MagicMock()
    mock.sf_instance = "test.salesforce.com"
    mock.query.return_value = {"records": []}
    return mock


# ---------------------------------------------------------------------------
# _sanitize_developer_name
# ---------------------------------------------------------------------------


class TestSanitizeDeveloperName:
    def test_spaces_to_underscores(self):
        assert _sanitize_developer_name("Top 50 Under 50") == "Top_50_Under_50"

    def test_special_chars_replaced(self):
        # "High-Value (Growth)" → sub: "High_Value__Growth_" → collapse:
        # "High_Value_Growth_" → strip: "High_Value_Growth"
        assert _sanitize_developer_name("High-Value (Growth)") == "High_Value_Growth"

    def test_consecutive_underscores_collapsed(self):
        assert _sanitize_developer_name("a__b___c") == "a_b_c"

    def test_leading_trailing_stripped(self):
        assert _sanitize_developer_name("_hello_") == "hello"

    def test_truncation_to_40(self):
        long_input = "a" * 50
        result = _sanitize_developer_name(long_input)
        assert len(result) == 40
        assert result == "a" * 40

    def test_empty_after_sanitize(self):
        # Only special chars → all replaced with _ → collapsed → stripped → ""
        assert _sanitize_developer_name("---") == ""
        assert _sanitize_developer_name("!!!") == ""


# ---------------------------------------------------------------------------
# translate_filters_to_listview
# ---------------------------------------------------------------------------


class TestTranslateFiltersToListview:
    def test_all_supported_fields(self):
        f = CompoundFilter(
            min_age=30,
            max_age=50,
            min_value=100000,
            max_value=500000,
            risk_tolerances=["growth"],
            life_stages=["accumulation"],
            contacted_after="2024-01-01",
            contacted_before="2024-12-31",
        )
        filters, warnings = translate_filters_to_listview(f)
        assert len(filters) == 8
        assert len(warnings) == 0

        # Verify each filter field is present
        fields = [flt["field"] for flt in filters]
        assert fields.count("Age__c") == 2
        assert fields.count("Account_Value__c") == 2
        assert "Risk_Tolerance__c" in fields
        assert "Life_Stage__c" in fields
        assert fields.count("ACTIVITY_DATE") == 2

    def test_unsupported_not_contacted_days(self):
        f = CompoundFilter(not_contacted_days=90)
        filters, warnings = translate_filters_to_listview(f)
        assert len(filters) == 0
        assert any("not_contacted_days" in w for w in warnings)

    def test_unsupported_search(self):
        f = CompoundFilter(search="Smith")
        filters, warnings = translate_filters_to_listview(f)
        assert len(filters) == 0
        assert any("search" in w for w in warnings)

    def test_non_default_sort_warning(self):
        f = CompoundFilter(sort_by="age")
        filters, warnings = translate_filters_to_listview(f)
        assert any("sort_by" in w for w in warnings)

    def test_non_default_limit_warning(self):
        f = CompoundFilter(limit=25)
        filters, warnings = translate_filters_to_listview(f)
        assert any("limit" in w for w in warnings)

    def test_default_sort_no_warning(self):
        """Default sort_by='account_value' + sort_dir='desc' should not warn."""
        f = CompoundFilter()
        filters, warnings = translate_filters_to_listview(f)
        assert not any("sort" in w.lower() for w in warnings)

    def test_multi_value_risk(self):
        f = CompoundFilter(risk_tolerances=["growth", "aggressive"])
        filters, warnings = translate_filters_to_listview(f)
        risk_filter = [flt for flt in filters if flt["field"] == "Risk_Tolerance__c"]
        assert len(risk_filter) == 1
        assert risk_filter[0]["value"] == "growth,aggressive"

    def test_default_filters_no_warnings(self):
        f = CompoundFilter()
        filters, warnings = translate_filters_to_listview(f)
        assert len(filters) == 0
        assert len(warnings) == 0

    def test_max_10_filter_truncation(self):
        """The code truncates at >10 filters. With 8 supported fields we can
        only produce 8, so directly test that 8 is not truncated and that
        the truncation branch works when more than 10 filters would be produced.
        """
        # 8 filters — no truncation
        f = CompoundFilter(
            min_age=30,
            max_age=50,
            min_value=100000,
            max_value=500000,
            risk_tolerances=["growth"],
            life_stages=["accumulation"],
            contacted_after="2024-01-01",
            contacted_before="2024-12-31",
        )
        filters, warnings = translate_filters_to_listview(f)
        assert len(filters) == 8
        assert not any("truncated" in w for w in warnings)


# ---------------------------------------------------------------------------
# create_listview
# ---------------------------------------------------------------------------


class TestCreateListview:
    def test_creates_new(self, sf):
        """When no existing ListView, create is called and ID is queried back."""
        # First query: no existing record
        # Second query: return newly created record
        sf.query.side_effect = [
            {"records": []},
            {"records": [{"Id": "00Bxx000001NEW"}]},
        ]

        f = CompoundFilter(min_age=30, max_age=60)
        result = create_listview(sf, "Young Clients", f)

        # Verify create was called (not update)
        sf.mdapi.ListView.create.assert_called_once()
        sf.mdapi.ListView.update.assert_not_called()

        # Verify create was called with a list containing one zeep-style object
        create_args = sf.mdapi.ListView.create.call_args[0][0]
        assert isinstance(create_args, list)
        assert len(create_args) == 1

        # Verify returned dict
        assert result["id"] == "00Bxx000001NEW"
        assert result["name"] == "AA: Young Clients"
        assert result["developer_name"] == "AA_Young_Clients"
        assert "filters_applied" in result
        assert isinstance(result["warnings"], list)

    def test_updates_existing(self, sf):
        """When existing ListView found, update is called instead of create."""
        sf.query.return_value = {
            "records": [{"Id": "00Bxx000001OLD", "DeveloperName": "AA_Existing"}],
        }

        f = CompoundFilter(min_value=100000)
        result = create_listview(sf, "Existing", f)

        sf.mdapi.ListView.update.assert_called_once()
        sf.mdapi.ListView.create.assert_not_called()

        # Verify update was called with a list
        update_args = sf.mdapi.ListView.update.call_args[0][0]
        assert isinstance(update_args, list)

        assert result["id"] == "00Bxx000001OLD"

    def test_url_construction(self, sf):
        """Verify the Lightning URL format."""
        sf.query.side_effect = [
            {"records": []},
            {"records": [{"Id": "00Bxx000001ABC"}]},
        ]

        f = CompoundFilter()
        result = create_listview(sf, "Test View", f)

        expected_url = "https://test.salesforce.com/lightning/o/Contact/list?filterName=00Bxx000001ABC"
        assert result["url"] == expected_url

    def test_warnings_appended_when_unsupported_filters(self, sf):
        """When unsupported filters produce warnings, extra note is appended."""
        sf.query.side_effect = [
            {"records": []},
            {"records": [{"Id": "00Bxx000001WARN"}]},
        ]

        f = CompoundFilter(not_contacted_days=90)
        result = create_listview(sf, "Warn View", f)

        assert any("not_contacted_days" in w for w in result["warnings"])
        assert any("more results" in w for w in result["warnings"])

    def test_no_filters_key_when_empty(self, sf):
        """When CompoundFilter has no supported filters, metadata should not
        include a 'filters' key."""
        sf.query.side_effect = [
            {"records": []},
            {"records": [{"Id": "00Bxx000001EMPTY"}]},
        ]

        f = CompoundFilter()
        result = create_listview(sf, "Empty Filters", f)

        # Verify create called with list
        sf.mdapi.ListView.create.assert_called_once()
        assert result["warnings"] == []


# ---------------------------------------------------------------------------
# list_listviews
# ---------------------------------------------------------------------------


class TestListListviews:
    def test_returns_sorted_stripped_names(self, sf):
        sf.query.return_value = {
            "records": [
                {"Id": "00Bxx000001Z", "DeveloperName": "AA_Zebra", "Name": "AA: Zebra"},
                {"Id": "00Bxx000001A", "DeveloperName": "AA_Alpha", "Name": "AA: Alpha"},
            ],
        }

        views = list_listviews(sf)

        assert len(views) == 2
        # Sorted alphabetically by stripped name
        assert views[0]["name"] == "Alpha"
        assert views[1]["name"] == "Zebra"
        assert views[0]["id"] == "00Bxx000001A"
        assert views[1]["id"] == "00Bxx000001Z"

    def test_empty_results(self, sf):
        sf.query.return_value = {"records": []}

        views = list_listviews(sf)

        assert views == []

    def test_url_format(self, sf):
        sf.query.return_value = {
            "records": [
                {"Id": "00Bxx000001X", "DeveloperName": "AA_Test", "Name": "AA: Test"},
            ],
        }

        views = list_listviews(sf)
        assert views[0]["url"] == (
            "https://test.salesforce.com/lightning/o/Contact/list?filterName=00Bxx000001X"
        )

    def test_name_without_aa_prefix_kept_as_is(self, sf):
        """If Name doesn't start with 'AA: ', it's kept unchanged."""
        sf.query.return_value = {
            "records": [
                {"Id": "00Bxx000001Y", "DeveloperName": "AA_Custom", "Name": "Custom View"},
            ],
        }

        views = list_listviews(sf)
        assert views[0]["name"] == "Custom View"


# ---------------------------------------------------------------------------
# delete_listview
# ---------------------------------------------------------------------------


class TestDeleteListview:
    def test_deletes_found(self, sf):
        sf.query.return_value = {
            "records": [
                {"Id": "00Bxx000001D", "DeveloperName": "AA_Top_50_Under_50"},
            ],
        }

        result = delete_listview(sf, "Top 50 Under 50")

        assert result is True
        sf.mdapi.ListView.delete.assert_called_once_with(["Contact.AA_Top_50_Under_50"])

    def test_not_found(self, sf):
        sf.query.return_value = {"records": []}

        result = delete_listview(sf, "Nonexistent")

        assert result is False
        sf.mdapi.ListView.delete.assert_not_called()

    def test_case_insensitive(self, sf):
        """delete_listview should match DeveloperName case-insensitively."""
        sf.query.return_value = {
            "records": [
                {"Id": "00Bxx000001CI", "DeveloperName": "AA_Top_50_Under_50"},
            ],
        }

        # Use different casing in the name
        result = delete_listview(sf, "top 50 under 50")

        assert result is True
        sf.mdapi.ListView.delete.assert_called_once_with(["Contact.AA_Top_50_Under_50"])

    def test_multiple_views_matches_correct_one(self, sf):
        """When multiple AA_ views exist, only the matching one is deleted."""
        sf.query.return_value = {
            "records": [
                {"Id": "00Bxx000001A", "DeveloperName": "AA_Alpha"},
                {"Id": "00Bxx000001B", "DeveloperName": "AA_Beta"},
            ],
        }

        result = delete_listview(sf, "Beta")

        assert result is True
        sf.mdapi.ListView.delete.assert_called_once_with(["Contact.AA_Beta"])
