"""Pydantic models for research data ingestion and analysis."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SignalType(StrEnum):
    """Types of research signals produced by analysis."""

    SENTIMENT = "sentiment"
    GUIDANCE_CHANGE = "guidance_change"
    LEADERSHIP_CHANGE = "leadership_change"
    COMPETITIVE_INSIGHT = "competitive_insight"
    RISK_FACTOR = "risk_factor"
    FINANCIAL_METRIC = "financial_metric"
    INVESTOR_ACTIVITY = "investor_activity"


class EvidenceType(StrEnum):
    """Whether a signal is a direct fact or an AI inference."""

    FACT = "fact"
    INFERENCE = "inference"


class Confidence(StrEnum):
    """Confidence level for a research signal."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ContentClassification(StrEnum):
    """Classification of source document content type."""

    FILING_10K = "10-K"
    FILING_10Q = "10-Q"
    FILING_8K = "8-K"
    EARNINGS_CALL = "earnings_call"
    PODCAST_DEEP_DIVE = "podcast_deep_dive"
    PODCAST_INTERVIEW = "podcast_interview"
    ANALYSIS_ARTICLE = "analysis_article"
    DAILY_UPDATE = "daily_update"
    HOLDINGS_13F = "13F-HR"


class FinancialMetric(BaseModel):
    """A structured financial metric extracted from a document."""

    name: str = Field(description="Metric name (e.g., 'Revenue', 'EPS')")
    value: str = Field(description="Current value as string")
    prior_value: str | None = Field(default=None, description="Prior period value")
    change_pct: float | None = Field(default=None, description="Percentage change")
    period: str | None = Field(default=None, description="Reporting period (e.g., 'Q3 2025')")


class ResearchSignalOutput(BaseModel):
    """A single research signal produced by LLM analysis."""

    signal_type: SignalType
    evidence_type: EvidenceType
    confidence: Confidence
    summary: str = Field(description="Human-readable finding (1-3 sentences)")
    details: str | None = Field(default=None, description="Extended explanation")
    source_section: str | None = Field(
        default=None, description="Section of source document (e.g., 'Item 1A: Risk Factors')"
    )
    metrics: list[FinancialMetric] = Field(
        default_factory=list, description="Structured financial metrics if applicable"
    )


class DocumentAnalysis(BaseModel):
    """Complete analysis output for a single source document."""

    company_ticker: str = Field(description="Primary company ticker this analysis is about")
    overall_sentiment: str = Field(
        description="Overall sentiment: bullish, bearish, neutral, or mixed"
    )
    signals: list[ResearchSignalOutput] = Field(
        description="List of research signals extracted from the document"
    )
    key_takeaways: list[str] = Field(
        description="Top 3-5 key takeaways from the document"
    )
    companies_mentioned: list[str] = Field(
        default_factory=list,
        description="Other company tickers mentioned in the document",
    )


class SourceDocumentMeta(BaseModel):
    """Metadata about an ingested source document."""

    source_type: str = Field(description="Source category: sec_filing, earnings_transcript, etc.")
    content_type: str = Field(description="Specific type: 10-K, 10-Q, 8-K, earnings_call, etc.")
    source_id: str = Field(description="External identifier (accession number, URL, etc.)")
    title: str
    published_at: str = Field(description="ISO 8601 UTC publication date")
    content: str = Field(description="Raw document content")
    company_ticker: str | None = Field(
        default=None, description="Ticker if known at ingestion time"
    )
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
