"""Unit tests for sfdc_report.py (021-sfdc-native-lists)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from finance_agent.sandbox.models import CompoundFilter
import finance_agent.sandbox.sfdc_report as sfdc_report_module
from finance_agent.sandbox.sfdc_report import (
    translate_filters_to_report,
    ensure_report_folder,
    create_report,
    list_reports,
    delete_report,
    ADVISOR_AGENT_TAG,
)


@pytest.fixture
def mock_sf():
    """Create a mock Salesforce client."""
    sf = MagicMock()
    sf.sf_instance = "test.salesforce.com"
    return sf


@pytest.fixture(autouse=True)
def reset_folder_cache():
    """Reset the module-level folder ID cache before each test."""
    sfdc_report_module._folder_id_cache = None
    yield
    sfdc_report_module._folder_id_cache = None


# ---------------------------------------------------------------------------
# TestTranslateFiltersToReport
# ---------------------------------------------------------------------------


class TestTranslateFiltersToReport:
    def test_all_supported_fields(self):
        filters = CompoundFilter(
            min_age=30,
            max_age=65,
            min_value=100000,
            max_value=500000,
            risk_tolerances=["growth"],
            life_stages=["accumulation"],
            contacted_after="2025-01-01",
            contacted_before="2025-06-30",
        )
        rpt_filters, warnings = translate_filters_to_report(filters)

        assert len(rpt_filters) == 8

        columns = [f["column"] for f in rpt_filters]
        assert columns.count("Contact.Age__c") == 2
        assert columns.count("Contact.Account_Value__c") == 2
        assert "Contact.Risk_Tolerance__c" in columns
        assert "Contact.Life_Stage__c" in columns
        assert columns.count("LAST_ACTIVITY") == 2

        # Default sort and limit -- no warnings expected
        assert len(warnings) == 0

    def test_not_contacted_days_uses_last_n_days(self):
        filters = CompoundFilter(not_contacted_days=90)
        rpt_filters, warnings = translate_filters_to_report(filters)

        activity_filter = [f for f in rpt_filters if f["column"] == "LAST_ACTIVITY"]
        assert len(activity_filter) == 1
        assert activity_filter[0]["operator"] == "equals"
        assert activity_filter[0]["value"] == "LAST_N_DAYS:90"

    def test_search_creates_two_filters_with_warning(self):
        filters = CompoundFilter(search="Smith")
        rpt_filters, warnings = translate_filters_to_report(filters)

        search_filters = [
            f for f in rpt_filters if f["operator"] == "contains"
        ]
        assert len(search_filters) == 2
        assert search_filters[0]["column"] == "FIRST_NAME"
        assert search_filters[0]["value"] == "Smith"
        assert search_filters[1]["column"] == "LAST_NAME"
        assert search_filters[1]["value"] == "Smith"

        assert len(warnings) == 1
        assert "search filter partially supported" in warnings[0]

    def test_non_default_sort_warning(self):
        filters = CompoundFilter(sort_by="age")
        rpt_filters, warnings = translate_filters_to_report(filters)

        sort_warnings = [w for w in warnings if "sort_by" in w]
        assert len(sort_warnings) == 1
        assert "not supported" in sort_warnings[0]

    def test_non_default_limit_warning(self):
        filters = CompoundFilter(limit=25)
        rpt_filters, warnings = translate_filters_to_report(filters)

        limit_warnings = [w for w in warnings if "limit" in w]
        assert len(limit_warnings) == 1
        assert "not supported" in limit_warnings[0]

    def test_default_filters_no_warnings(self):
        filters = CompoundFilter()
        rpt_filters, warnings = translate_filters_to_report(filters)

        assert len(rpt_filters) == 0
        assert len(warnings) == 0

    def test_risk_tolerances_comma_joined(self):
        filters = CompoundFilter(risk_tolerances=["growth", "aggressive"])
        rpt_filters, warnings = translate_filters_to_report(filters)

        risk_filter = [
            f for f in rpt_filters if f["column"] == "Contact.Risk_Tolerance__c"
        ]
        assert len(risk_filter) == 1
        assert risk_filter[0]["value"] == "growth,aggressive"
        assert risk_filter[0]["operator"] == "equals"


# ---------------------------------------------------------------------------
# TestEnsureReportFolder
# ---------------------------------------------------------------------------


class TestEnsureReportFolder:
    def test_returns_existing_folder(self, mock_sf):
        mock_sf.query.return_value = {
            "records": [{"Id": "00lxx000001AAAA", "Name": "Client Lists"}],
        }

        folder_id = ensure_report_folder(mock_sf)

        assert folder_id == "00lxx000001AAAA"
        mock_sf.restful.assert_not_called()

    def test_creates_new_folder(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        mock_sf.restful.return_value = {"id": "00lxx000001BBBB"}

        folder_id = ensure_report_folder(mock_sf)

        assert folder_id == "00lxx000001BBBB"
        mock_sf.restful.assert_called_once_with(
            "analytics/report-folders",
            method="POST",
            json={
                "name": "Client Lists",
                "description": "[advisor-agent] Auto-created folder",
            },
        )

    def test_caches_folder_id(self, mock_sf):
        mock_sf.query.return_value = {
            "records": [{"Id": "00lxx000001CCCC", "Name": "Client Lists"}],
        }

        first = ensure_report_folder(mock_sf)
        second = ensure_report_folder(mock_sf)

        assert first == second == "00lxx000001CCCC"
        assert mock_sf.query.call_count == 1


# ---------------------------------------------------------------------------
# TestCreateReport
# ---------------------------------------------------------------------------


class TestCreateReport:
    @patch(
        "finance_agent.sandbox.sfdc_report.ensure_report_folder",
        return_value="folder123",
    )
    def test_creates_new_report(self, mock_ensure, mock_sf):
        mock_sf.query.return_value = {"records": []}
        mock_sf.restful.return_value = {
            "reportMetadata": {"id": "00Oxx000001NEW1"}
        }

        result = create_report(
            mock_sf, "High Value Clients", CompoundFilter(min_value=500000)
        )

        assert result["id"] == "00Oxx000001NEW1"
        assert result["name"] == "AA: High Value Clients"
        assert "test.salesforce.com" in result["url"]
        assert "00Oxx000001NEW1" in result["url"]
        assert isinstance(result["warnings"], list)
        assert isinstance(result["filters_applied"], str)
        assert result["folder"] == "Client Lists"

        # Verify POST was used (not PATCH)
        mock_sf.restful.assert_called_once()
        call_kwargs = mock_sf.restful.call_args
        assert call_kwargs[1]["method"] == "POST" or call_kwargs[0][0] == "analytics/reports"

    @patch(
        "finance_agent.sandbox.sfdc_report.ensure_report_folder",
        return_value="folder123",
    )
    def test_updates_existing_report(self, mock_ensure, mock_sf):
        mock_sf.query.return_value = {
            "records": [{"Id": "00Oxx000001OLD1", "Name": "AA: Existing List"}],
        }

        result = create_report(
            mock_sf, "Existing List", CompoundFilter(min_age=50)
        )

        assert result["id"] == "00Oxx000001OLD1"

        # Verify PATCH was used
        mock_sf.restful.assert_called_once()
        call_args = mock_sf.restful.call_args
        assert call_args[1]["method"] == "PATCH"
        assert "00Oxx000001OLD1" in call_args[0][0]

    @patch(
        "finance_agent.sandbox.sfdc_report.ensure_report_folder",
        return_value="folder123",
    )
    def test_url_construction(self, mock_ensure, mock_sf):
        mock_sf.query.return_value = {"records": []}
        mock_sf.restful.return_value = {
            "reportMetadata": {"id": "00Oxx000001URL1"}
        }

        result = create_report(mock_sf, "Test", CompoundFilter())

        assert (
            result["url"]
            == "https://test.salesforce.com/lightning/r/Report/00Oxx000001URL1/view"
        )

    @patch(
        "finance_agent.sandbox.sfdc_report.ensure_report_folder",
        return_value="folder123",
    )
    def test_description_contains_tag(self, mock_ensure, mock_sf):
        mock_sf.query.return_value = {"records": []}
        mock_sf.restful.return_value = {
            "reportMetadata": {"id": "00Oxx000001TAG1"}
        }

        create_report(mock_sf, "Tagged Report", CompoundFilter(min_age=30))

        call_kwargs = mock_sf.restful.call_args
        metadata = call_kwargs[1]["json"]["reportMetadata"]
        assert ADVISOR_AGENT_TAG in metadata["description"]


# ---------------------------------------------------------------------------
# TestListReports
# ---------------------------------------------------------------------------


class TestListReports:
    def test_returns_sorted_stripped_names(self, mock_sf):
        mock_sf.query.return_value = {
            "records": [
                {
                    "Id": "00Oxx1",
                    "Name": "AA: Zebra Report",
                    "Description": "[advisor-agent] filters",
                    "LastRunDate": "2025-12-01",
                },
                {
                    "Id": "00Oxx2",
                    "Name": "AA: Alpha Report",
                    "Description": "[advisor-agent] filters",
                    "LastRunDate": "2025-11-15",
                },
            ]
        }

        results = list_reports(mock_sf)

        assert len(results) == 2
        # Sorted alphabetically by stripped name
        assert results[0]["name"] == "Alpha Report"
        assert results[1]["name"] == "Zebra Report"
        # AA: prefix is stripped
        assert not results[0]["name"].startswith("AA:")

    def test_empty_results(self, mock_sf):
        mock_sf.query.return_value = {"records": []}

        results = list_reports(mock_sf)

        assert results == []


# ---------------------------------------------------------------------------
# TestDeleteReport
# ---------------------------------------------------------------------------


class TestDeleteReport:
    def test_deletes_found(self, mock_sf):
        mock_sf.query.return_value = {
            "records": [
                {"Id": "00Oxx000001DEL1", "Name": "AA: To Delete"},
            ]
        }

        result = delete_report(mock_sf, "To Delete")

        assert result is True
        mock_sf.restful.assert_called_once_with(
            "analytics/reports/00Oxx000001DEL1", method="DELETE"
        )

    def test_not_found(self, mock_sf):
        mock_sf.query.return_value = {"records": []}

        result = delete_report(mock_sf, "Nonexistent")

        assert result is False
        mock_sf.restful.assert_not_called()

    def test_case_insensitive_match(self, mock_sf):
        mock_sf.query.return_value = {
            "records": [
                {"Id": "00Oxx000001CASE", "Name": "AA: Test Report"},
            ]
        }

        result = delete_report(mock_sf, "test report")

        assert result is True
        mock_sf.restful.assert_called_once_with(
            "analytics/reports/00Oxx000001CASE", method="DELETE"
        )
