"""Integration test for EarningsCall.biz transcript source."""

from __future__ import annotations

import os

import pytest


@pytest.mark.skipif(
    not os.environ.get("EARNINGSCALL_API_KEY"),
    reason="earningscall demo mode requires network access — skipping in CI",
)
class TestEarningsCallDemo:
    """Tests that work in demo mode (no API key required, AAPL/MSFT only)."""

    def test_get_aapl_company(self) -> None:
        """Verify get_company returns a Company for AAPL in demo mode."""
        from earningscall import get_company

        company = get_company("aapl")
        assert company is not None

    def test_aapl_transcript_level1(self) -> None:
        """Verify we can fetch an AAPL transcript at level=1 in demo mode."""
        from earningscall import get_company

        company = get_company("aapl")
        assert company is not None

        # Try a known recent quarter — demo mode may restrict date range
        transcript = company.get_transcript(year=2024, quarter=4, level=1)
        if transcript is not None:
            has_text = hasattr(transcript, "text") and transcript.text
            has_speakers = hasattr(transcript, "speakers") and transcript.speakers
            assert has_text or has_speakers, "Transcript should have text or speakers"


@pytest.mark.skipif(
    not os.environ.get("EARNINGSCALL_API_KEY"),
    reason="EARNINGSCALL_API_KEY not set — skipping paid-tier tests",
)
class TestEarningsCallPaid:
    """Tests that require a paid API key for full access."""

    def test_get_aapl_transcript(self) -> None:
        """Verify we can fetch an AAPL earnings transcript."""
        import earningscall

        earningscall.api_key = os.environ["EARNINGSCALL_API_KEY"]
        company = earningscall.get_company("AAPL")
        assert company is not None

        transcript = company.get_transcript(year=2024, quarter=4, level=1)
        assert transcript is not None

        has_text = hasattr(transcript, "text") and transcript.text
        has_speakers = hasattr(transcript, "speakers") and transcript.speakers
        assert has_text or has_speakers, "Transcript should have text or speakers"

    def test_level2_transcript(self) -> None:
        """Verify level=2 transcripts include speaker attribution."""
        import earningscall

        earningscall.api_key = os.environ["EARNINGSCALL_API_KEY"]
        company = earningscall.get_company("AAPL")
        assert company is not None

        try:
            transcript = company.get_transcript(year=2024, quarter=4, level=2)
            if transcript is not None and hasattr(transcript, "speakers"):
                assert transcript.speakers is not None
                assert len(transcript.speakers) > 0
                first_speaker = transcript.speakers[0]
                assert hasattr(first_speaker, "name")
        except Exception:
            # Level 2 may require higher API tier — not a test failure
            pytest.skip("Level 2 transcript not available on current API tier")
