"""Unit tests for Pydantic research data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from finance_agent.data.models import (
    Confidence,
    ContentClassification,
    DocumentAnalysis,
    EvidenceType,
    FinancialMetric,
    ResearchSignalOutput,
    SignalType,
    SourceDocumentMeta,
)


class TestSignalType:
    def test_all_values(self) -> None:
        expected = {
            "sentiment", "guidance_change", "leadership_change",
            "competitive_insight", "risk_factor", "financial_metric",
            "investor_activity",
        }
        assert {st.value for st in SignalType} == expected

    def test_string_comparison(self) -> None:
        assert SignalType.SENTIMENT == "sentiment"
        assert SignalType.GUIDANCE_CHANGE == "guidance_change"


class TestEvidenceType:
    def test_fact_and_inference(self) -> None:
        assert EvidenceType.FACT == "fact"
        assert EvidenceType.INFERENCE == "inference"

    def test_only_two_values(self) -> None:
        assert len(EvidenceType) == 2


class TestConfidence:
    def test_levels(self) -> None:
        assert {c.value for c in Confidence} == {"high", "medium", "low"}


class TestContentClassification:
    def test_all_content_types(self) -> None:
        expected = {
            "10-K", "10-Q", "8-K", "earnings_call",
            "podcast_deep_dive", "podcast_interview",
            "analysis_article", "daily_update", "13F-HR",
        }
        assert {c.value for c in ContentClassification} == expected


class TestFinancialMetric:
    def test_required_fields(self) -> None:
        metric = FinancialMetric(name="Revenue", value="$22.1B")
        assert metric.name == "Revenue"
        assert metric.value == "$22.1B"

    def test_optional_fields(self) -> None:
        metric = FinancialMetric(
            name="EPS", value="$5.16",
            prior_value="$4.02", change_pct=28.4, period="Q4 2025",
        )
        assert metric.prior_value == "$4.02"
        assert metric.change_pct == 28.4
        assert metric.period == "Q4 2025"

    def test_defaults_none(self) -> None:
        metric = FinancialMetric(name="Rev", value="100")
        assert metric.prior_value is None
        assert metric.change_pct is None
        assert metric.period is None


class TestResearchSignalOutput:
    def test_required_fields(self) -> None:
        signal = ResearchSignalOutput(
            signal_type=SignalType.SENTIMENT,
            evidence_type=EvidenceType.FACT,
            confidence=Confidence.HIGH,
            summary="Revenue grew 94% YoY",
        )
        assert signal.signal_type == SignalType.SENTIMENT
        assert signal.evidence_type == EvidenceType.FACT
        assert signal.summary == "Revenue grew 94% YoY"

    def test_optional_fields(self) -> None:
        signal = ResearchSignalOutput(
            signal_type=SignalType.FINANCIAL_METRIC,
            evidence_type=EvidenceType.FACT,
            confidence=Confidence.HIGH,
            summary="Revenue: $22.1B",
            details="Up from $11.4B in prior year",
            source_section="Item 7: MD&A",
            metrics=[FinancialMetric(name="Revenue", value="$22.1B")],
        )
        assert signal.details is not None
        assert signal.source_section == "Item 7: MD&A"
        assert len(signal.metrics) == 1

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            ResearchSignalOutput(
                signal_type=SignalType.SENTIMENT,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.HIGH,
                # missing summary
            )


class TestDocumentAnalysis:
    def test_full_analysis(self) -> None:
        analysis = DocumentAnalysis(
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
            key_takeaways=["Record revenue", "AI demand strong"],
            companies_mentioned=["AMD", "INTC"],
        )
        assert analysis.company_ticker == "NVDA"
        assert len(analysis.signals) == 1
        assert len(analysis.key_takeaways) == 2
        assert "AMD" in analysis.companies_mentioned

    def test_empty_optional_lists(self) -> None:
        analysis = DocumentAnalysis(
            company_ticker="AAPL",
            overall_sentiment="neutral",
            signals=[],
            key_takeaways=[],
        )
        assert analysis.companies_mentioned == []


class TestSourceDocumentMeta:
    def test_required_fields(self) -> None:
        meta = SourceDocumentMeta(
            source_type="sec_filing",
            content_type="10-K",
            source_id="sec:0001045810-24-000123",
            title="NVDA 10-K (2025-01-15)",
            published_at="2025-01-15T00:00:00Z",
            content="Full filing content...",
        )
        assert meta.source_type == "sec_filing"
        assert meta.company_ticker is None

    def test_with_ticker(self) -> None:
        meta = SourceDocumentMeta(
            source_type="sec_filing",
            content_type="10-K",
            source_id="test:123",
            title="Test",
            published_at="2025-01-15T00:00:00Z",
            content="content",
            company_ticker="NVDA",
        )
        assert meta.company_ticker == "NVDA"
