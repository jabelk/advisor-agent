"""Integration test for SEC EDGAR source — requires EDGAR_IDENTITY env var."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("EDGAR_IDENTITY"),
    reason="EDGAR_IDENTITY not set — skipping SEC EDGAR integration test",
)


class TestSECEdgarIntegration:
    def test_fetch_aapl_filings(self) -> None:
        """Verify we can fetch AAPL filing metadata from SEC EDGAR."""
        from edgar import Company

        ec = Company("AAPL")
        assert ec.name is not None
        assert "apple" in ec.name.lower() or "AAPL" in str(ec.cik)

        filings = ec.get_filings()
        ten_ks = filings.filter(form="10-K").latest(2)
        assert len(ten_ks) >= 1

    def test_filing_has_content(self) -> None:
        """Verify we can get content from a filing."""
        from edgar import Company

        ec = Company("AAPL")
        filings = ec.get_filings()
        ten_ks = filings.filter(form="10-K").latest(2)
        filing = ten_ks[0]

        assert filing.accession_no is not None
        assert filing.filing_date is not None
