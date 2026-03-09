"""Unit tests for NL query translation (020-client-list-builder / 021-sfdc-native-lists)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from finance_agent.sandbox.models import CompoundFilter, QueryInterpretation
from finance_agent.sandbox.list_builder import (
    translate_nl_query,
    execute_nl_query,
)


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
        assert "filters_raw" in result
        assert result["executed"] is True

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
