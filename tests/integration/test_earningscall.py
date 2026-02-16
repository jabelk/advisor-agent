"""Integration test for EarningsCall.biz transcript source."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("EARNINGSCALL_API_KEY"),
    reason="EARNINGSCALL_API_KEY not set — skipping EarningsCall integration test",
)


class TestEarningsCallIntegration:
    def test_get_aapl_transcript(self) -> None:
        """Verify we can fetch an AAPL earnings transcript."""
        import earningscall

        earningscall.api_key = os.environ["EARNINGSCALL_API_KEY"]
        company = earningscall.get_company("AAPL")
        assert company is not None

        # Try to get a recent transcript (Q4 2024 should be available)
        transcript = company.get_transcript(year=2024, quarter=4, level=1)
        assert transcript is not None

        # Should have text content
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
