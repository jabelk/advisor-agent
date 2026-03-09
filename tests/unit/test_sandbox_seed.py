"""Unit tests for sandbox seed data generator (Salesforce-backed, mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from finance_agent.sandbox.seed import (
    LIFE_STAGE_AGE_RANGES,
    RISK_WEIGHTS,
    _generate_client,
    _generate_interactions,
    reset_sandbox,
    seed_clients,
)

import random


@pytest.fixture
def mock_sf():
    """Create a mock Salesforce client."""
    sf = MagicMock()
    sf.Contact.create.return_value = {"id": "003xxTEST", "success": True}
    sf.Task.create.return_value = {"id": "00TxxTEST", "success": True}
    return sf


class TestGenerateClient:
    def test_returns_required_fields(self):
        rng = random.Random(42)
        client = _generate_client(rng)
        required = [
            "first_name", "last_name", "age", "occupation", "email", "phone",
            "account_value", "risk_tolerance", "life_stage",
        ]
        for field in required:
            assert field in client, f"Missing field: {field}"

    def test_account_value_in_range(self):
        rng = random.Random(42)
        for _ in range(100):
            client = _generate_client(rng)
            assert 50_000 <= client["account_value"] <= 5_000_000

    def test_age_matches_life_stage(self):
        rng = random.Random(42)
        for _ in range(100):
            client = _generate_client(rng)
            stage = client["life_stage"]
            age_min, age_max = LIFE_STAGE_AGE_RANGES[stage]
            assert age_min <= client["age"] <= age_max

    def test_email_format(self):
        rng = random.Random(42)
        client = _generate_client(rng)
        assert "@example.com" in client["email"]
        assert client["email"] == f"{client['first_name'].lower()}.{client['last_name'].lower()}@example.com"

    def test_phone_format(self):
        rng = random.Random(42)
        client = _generate_client(rng)
        assert client["phone"].startswith("555-")

    def test_deterministic_with_seed(self):
        c1 = _generate_client(random.Random(42))
        c2 = _generate_client(random.Random(42))
        assert c1 == c2


class TestGenerateInteractions:
    def test_returns_correct_count(self):
        rng = random.Random(42)
        interactions = _generate_interactions(rng, 3)
        assert len(interactions) == 3

    def test_sorted_by_date(self):
        rng = random.Random(42)
        interactions = _generate_interactions(rng, 5)
        dates = [i["interaction_date"] for i in interactions]
        assert dates == sorted(dates)

    def test_has_required_fields(self):
        rng = random.Random(42)
        interactions = _generate_interactions(rng, 1)
        ix = interactions[0]
        assert "interaction_date" in ix
        assert "interaction_type" in ix
        assert "summary" in ix


class TestSeedClients:
    def test_creates_correct_count(self, mock_sf):
        created = seed_clients(mock_sf, count=5, seed=42)
        assert created == 5
        assert mock_sf.Contact.create.call_count == 5

    def test_default_count_is_50(self, mock_sf):
        created = seed_clients(mock_sf, seed=42)
        assert created == 50
        assert mock_sf.Contact.create.call_count == 50

    def test_creates_interactions_for_each_client(self, mock_sf):
        seed_clients(mock_sf, count=3, seed=42)
        # Each client gets 1-5 interactions as Task records
        assert mock_sf.Task.create.call_count >= 3  # at least 1 per client

    def test_deterministic_output(self, mock_sf):
        seed_clients(mock_sf, count=3, seed=42)
        calls1 = [c[0][0] for c in mock_sf.Contact.create.call_args_list]

        mock_sf.reset_mock()
        seed_clients(mock_sf, count=3, seed=42)
        calls2 = [c[0][0] for c in mock_sf.Contact.create.call_args_list]

        assert calls1 == calls2

    def test_risk_distribution(self):
        """Risk tolerance should roughly match weighted distribution."""
        rng = random.Random(42)
        counts = {"conservative": 0, "moderate": 0, "growth": 0, "aggressive": 0}
        for _ in range(200):
            client = _generate_client(rng)
            counts[client["risk_tolerance"]] += 1
        # Moderate and growth should be most common (35% each)
        assert counts["moderate"] > counts["conservative"]
        assert counts["growth"] > counts["aggressive"]


class TestResetSandbox:
    def test_deletes_contacts_and_tasks(self, mock_sf):
        mock_sf.query.side_effect = [
            {"records": [{"Id": "003xx1"}, {"Id": "003xx2"}]},  # contacts query
            {"records": [{"Id": "00Txx1"}, {"Id": "00Txx2"}, {"Id": "00Txx3"}]},  # tasks query
        ]
        reset_sandbox(mock_sf)

        # Should delete tasks first, then contacts
        assert mock_sf.Task.delete.call_count == 3
        assert mock_sf.Contact.delete.call_count == 2

    def test_no_contacts_does_nothing(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        reset_sandbox(mock_sf)
        mock_sf.Task.delete.assert_not_called()
        mock_sf.Contact.delete.assert_not_called()

    def test_filters_by_example_email(self, mock_sf):
        mock_sf.query.return_value = {"records": []}
        reset_sandbox(mock_sf)
        soql = mock_sf.query.call_args[0][0]
        assert "@example.com" in soql
