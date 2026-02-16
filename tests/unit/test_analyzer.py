"""Unit tests for LLM analyzer (mocked Anthropic client)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from finance_agent.data.models import (
    Confidence,
    DocumentAnalysis,
    EvidenceType,
    ResearchSignalOutput,
    SignalType,
)
from finance_agent.research.analyzer import Analyzer


def _make_mock_response(analysis: DocumentAnalysis) -> MagicMock:
    """Create a mock Anthropic message response with JSON content."""
    json_str = analysis.model_dump_json()
    text_block = MagicMock()
    text_block.text = f"```json\n{json_str}\n```"
    response = MagicMock()
    response.content = [text_block]
    return response


class TestAnalyzer:
    @patch("finance_agent.research.analyzer.Anthropic")
    def test_analyze_document_single_pass(self, mock_anthropic_cls: MagicMock) -> None:
        expected = DocumentAnalysis(
            company_ticker="NVDA",
            overall_sentiment="bullish",
            signals=[
                ResearchSignalOutput(
                    signal_type=SignalType.SENTIMENT,
                    evidence_type=EvidenceType.FACT,
                    confidence=Confidence.HIGH,
                    summary="Revenue grew 94% YoY to $22.1B",
                )
            ],
            key_takeaways=["Record revenue quarter"],
        )

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(expected)
        mock_anthropic_cls.return_value = mock_client

        analyzer = Analyzer("test-key")
        result = analyzer.analyze_document(
            content="Short document content under 80K chars",
            content_type="10-K",
            company_ticker="NVDA",
        )

        assert result.company_ticker == "NVDA"
        assert result.overall_sentiment == "bullish"
        assert len(result.signals) == 1
        assert result.signals[0].signal_type == SignalType.SENTIMENT

        # Verify API was called with correct parameters
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-sonnet-4-5-20250929"
        assert call_kwargs.kwargs["max_tokens"] == 4096

    @patch("finance_agent.research.analyzer.Anthropic")
    def test_analyze_document_uses_prompt_caching(self, mock_anthropic_cls: MagicMock) -> None:
        expected = DocumentAnalysis(
            company_ticker="NVDA",
            overall_sentiment="neutral",
            signals=[],
            key_takeaways=["No key findings"],
        )

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(expected)
        mock_anthropic_cls.return_value = mock_client

        analyzer = Analyzer("test-key")
        analyzer.analyze_document("content", "10-K", "NVDA")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        system = call_kwargs["system"]
        assert system[0]["cache_control"] == {"type": "ephemeral"}

    @patch("finance_agent.research.analyzer.Anthropic")
    def test_fallback_on_non_json_response(self, mock_anthropic_cls: MagicMock) -> None:
        text_block = MagicMock()
        text_block.text = "This is a plain text analysis without JSON structure."
        response = MagicMock()
        response.content = [text_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = response
        mock_anthropic_cls.return_value = mock_client

        analyzer = Analyzer("test-key")
        result = analyzer.analyze_document("content", "10-K", "NVDA")

        # Should fallback to basic analysis
        assert result.company_ticker == "NVDA"
        assert len(result.signals) == 1
        assert result.signals[0].evidence_type == EvidenceType.INFERENCE

    @patch("finance_agent.research.analyzer.Anthropic")
    def test_large_document_splits_into_sections(self, mock_anthropic_cls: MagicMock) -> None:
        expected = DocumentAnalysis(
            company_ticker="NVDA",
            overall_sentiment="bullish",
            signals=[
                ResearchSignalOutput(
                    signal_type=SignalType.SENTIMENT,
                    evidence_type=EvidenceType.FACT,
                    confidence=Confidence.HIGH,
                    summary="Strong quarter",
                )
            ],
            key_takeaways=["Good results"],
        )

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(expected)
        mock_anthropic_cls.return_value = mock_client

        analyzer = Analyzer("test-key")
        # Create a large document with sections
        large_content = "\n".join([
            f"# Section {i}\n\n{'x' * 20000}" for i in range(6)
        ])
        result = analyzer.analyze_document(large_content, "10-K", "NVDA")

        # Should have called the API multiple times (once per section)
        assert mock_client.messages.create.call_count > 1
        assert result.company_ticker == "NVDA"


class TestSplitIntoSections:
    def test_splits_on_headers(self) -> None:
        section1 = "# Section 1\n" + ("Content 1 is here with enough text. " * 10) + "\n"
        section2 = "## Section 2\n" + ("Content 2 is here with enough text. " * 10) + "\n"
        content = section1 + section2
        sections = Analyzer._split_into_sections(content)
        assert len(sections) == 2

    def test_splits_by_length_when_no_headers(self) -> None:
        content = "x" * 200_000  # No headers, just raw text
        sections = Analyzer._split_into_sections(content)
        assert len(sections) > 1

    def test_skips_tiny_sections(self) -> None:
        content = "# Header\nshort\n# Real Section\n" + "x" * 200
        sections = Analyzer._split_into_sections(content)
        # Only the section with enough content should be included
        assert all(len(s.strip()) > 100 for s in sections)
