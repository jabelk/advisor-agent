"""Integration test for Finnhub market signals source — requires FINNHUB_API_KEY env var."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("FINNHUB_API_KEY"),
    reason="FINNHUB_API_KEY not set — skipping Finnhub integration test",
)


class TestFinnhubIntegration:
    def test_recommendation_trends(self) -> None:
        """Verify we can fetch AAPL analyst recommendation trends (free tier)."""
        import finnhub

        client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])
        result = client.recommendation_trends("AAPL")

        assert isinstance(result, list)
        assert len(result) > 0

        first = result[0]
        assert "period" in first
        assert "strongBuy" in first
        assert "buy" in first
        assert "hold" in first
        assert "sell" in first

    def test_company_earnings(self) -> None:
        """Verify we can fetch AAPL earnings history (free tier)."""
        import finnhub

        client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])
        result = client.company_earnings("AAPL", limit=4)

        assert isinstance(result, list)
        assert len(result) > 0

        first = result[0]
        assert "actual" in first
        assert "estimate" in first
        assert "period" in first

    def test_company_news(self) -> None:
        """Verify we can fetch AAPL company news (free tier)."""
        import finnhub

        client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])
        result = client.company_news("AAPL", _from="2025-01-01", to="2025-02-01")

        assert isinstance(result, list)
        # News may be empty for some date ranges, just check it returns a list
