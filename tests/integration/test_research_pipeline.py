"""Integration test for end-to-end research pipeline.

Requires EDGAR_IDENTITY and ANTHROPIC_API_KEY environment variables.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not (os.environ.get("EDGAR_IDENTITY") and os.environ.get("ANTHROPIC_API_KEY")),
    reason="EDGAR_IDENTITY and ANTHROPIC_API_KEY required for pipeline integration test",
)


class TestResearchPipelineIntegration:
    def test_watchlist_add_and_signals_query(self, tmp_db) -> None:
        """Verify watchlist add works and signals can be queried."""
        from finance_agent.data.watchlist import add_company, get_company_by_ticker
        from finance_agent.research.signals import get_signal_counts

        company_id = add_company(tmp_db, "AAPL", "Apple Inc", "0000320193", "Technology")
        company = get_company_by_ticker(tmp_db, "AAPL")
        assert company is not None
        assert company["ticker"] == "AAPL"

        counts = get_signal_counts(tmp_db, company_id)
        assert isinstance(counts, dict)
