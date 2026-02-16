"""Unit tests for signal storage and query."""

from __future__ import annotations

import sqlite3

import pytest

from finance_agent.data.models import (
    Confidence,
    EvidenceType,
    FinancialMetric,
    ResearchSignalOutput,
    SignalType,
)
from finance_agent.data.watchlist import add_company
from finance_agent.research.pipeline import save_document_record
from finance_agent.research.signals import (
    aggregate_by_source,
    check_document_exists,
    compare_periods,
    compute_overall_sentiment,
    get_signal_counts,
    query_signals,
    save_signals,
)


@pytest.fixture
def company_and_doc(tmp_db: sqlite3.Connection) -> tuple[int, int]:
    """Create a test company and document, return (company_id, doc_id)."""
    company_id = add_company(tmp_db, "NVDA", "NVIDIA Corporation", "0001045810")
    doc_id = save_document_record(
        tmp_db,
        company_id=company_id,
        source_type="sec_filing",
        content_type="10-K",
        source_id="sec:test-accession-001",
        title="NVDA 10-K (2025-01-15)",
        published_at="2025-01-15T00:00:00Z",
        content_hash="abc123",
        local_path="/tmp/test.md",
        file_size_bytes=1000,
    )
    return company_id, doc_id


class TestSaveSignals:
    def test_save_signals(
        self, tmp_db: sqlite3.Connection, company_and_doc: tuple[int, int]
    ) -> None:
        company_id, doc_id = company_and_doc
        signals = [
            ResearchSignalOutput(
                signal_type=SignalType.SENTIMENT,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.HIGH,
                summary="Revenue grew 94% YoY",
            ),
            ResearchSignalOutput(
                signal_type=SignalType.GUIDANCE_CHANGE,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.HIGH,
                summary="Guidance raised to $24B",
                source_section="Item 7: MD&A",
            ),
        ]
        count = save_signals(tmp_db, doc_id, company_id, signals)
        assert count == 2

        rows = tmp_db.execute(
            "SELECT * FROM research_signal WHERE company_id = ?", (company_id,)
        ).fetchall()
        assert len(rows) == 2

    def test_save_signals_with_metrics(
        self, tmp_db: sqlite3.Connection, company_and_doc: tuple[int, int]
    ) -> None:
        company_id, doc_id = company_and_doc
        signals = [
            ResearchSignalOutput(
                signal_type=SignalType.FINANCIAL_METRIC,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.HIGH,
                summary="Revenue $22.1B",
                metrics=[FinancialMetric(name="Revenue", value="$22.1B", prior_value="$11.4B")],
            ),
        ]
        save_signals(tmp_db, doc_id, company_id, signals)

        row = tmp_db.execute(
            "SELECT metrics_json FROM research_signal WHERE company_id = ?", (company_id,)
        ).fetchone()
        assert row["metrics_json"] is not None
        assert "Revenue" in row["metrics_json"]

    def test_save_empty_list(
        self, tmp_db: sqlite3.Connection, company_and_doc: tuple[int, int]
    ) -> None:
        company_id, doc_id = company_and_doc
        count = save_signals(tmp_db, doc_id, company_id, [])
        assert count == 0


class TestQuerySignals:
    def test_query_by_company(
        self, tmp_db: sqlite3.Connection, company_and_doc: tuple[int, int]
    ) -> None:
        company_id, doc_id = company_and_doc
        signals = [
            ResearchSignalOutput(
                signal_type=SignalType.SENTIMENT,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.HIGH,
                summary="Strong quarter",
            ),
        ]
        save_signals(tmp_db, doc_id, company_id, signals)
        result = query_signals(tmp_db, company_id=company_id)
        assert len(result) == 1
        assert result[0]["ticker"] == "NVDA"

    def test_query_by_signal_type(
        self, tmp_db: sqlite3.Connection, company_and_doc: tuple[int, int]
    ) -> None:
        company_id, doc_id = company_and_doc
        signals = [
            ResearchSignalOutput(
                signal_type=SignalType.SENTIMENT,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.HIGH,
                summary="Strong",
            ),
            ResearchSignalOutput(
                signal_type=SignalType.RISK_FACTOR,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.MEDIUM,
                summary="China risk",
            ),
        ]
        save_signals(tmp_db, doc_id, company_id, signals)

        sentiment = query_signals(tmp_db, company_id=company_id, signal_type="sentiment")
        assert len(sentiment) == 1
        assert sentiment[0]["signal_type"] == "sentiment"

    def test_query_by_source_type(
        self, tmp_db: sqlite3.Connection, company_and_doc: tuple[int, int]
    ) -> None:
        company_id, doc_id = company_and_doc
        signals = [
            ResearchSignalOutput(
                signal_type=SignalType.SENTIMENT,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.HIGH,
                summary="Test",
            ),
        ]
        save_signals(tmp_db, doc_id, company_id, signals)
        result = query_signals(tmp_db, source_type="sec_filing")
        assert len(result) == 1

        result2 = query_signals(tmp_db, source_type="podcast_episode")
        assert len(result2) == 0

    def test_query_empty_results(self, tmp_db: sqlite3.Connection) -> None:
        result = query_signals(tmp_db, company_id=9999)
        assert result == []


class TestGetSignalCounts:
    def test_counts_by_type(
        self, tmp_db: sqlite3.Connection, company_and_doc: tuple[int, int]
    ) -> None:
        company_id, doc_id = company_and_doc
        signals = [
            ResearchSignalOutput(
                signal_type=SignalType.SENTIMENT,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.HIGH,
                summary="A",
            ),
            ResearchSignalOutput(
                signal_type=SignalType.SENTIMENT,
                evidence_type=EvidenceType.INFERENCE,
                confidence=Confidence.MEDIUM,
                summary="B",
            ),
            ResearchSignalOutput(
                signal_type=SignalType.RISK_FACTOR,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.HIGH,
                summary="C",
            ),
        ]
        save_signals(tmp_db, doc_id, company_id, signals)
        counts = get_signal_counts(tmp_db, company_id)
        assert counts["sentiment"] == 2
        assert counts["risk_factor"] == 1

    def test_counts_empty(self, tmp_db: sqlite3.Connection) -> None:
        company_id = add_company(tmp_db, "AAPL", "Apple Inc")
        counts = get_signal_counts(tmp_db, company_id)
        assert counts == {}


class TestAggregateBySource:
    def test_aggregate(
        self, tmp_db: sqlite3.Connection, company_and_doc: tuple[int, int]
    ) -> None:
        company_id, doc_id = company_and_doc
        signals = [
            ResearchSignalOutput(
                signal_type=SignalType.SENTIMENT,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.HIGH,
                summary="Test",
            ),
        ]
        save_signals(tmp_db, doc_id, company_id, signals)
        result = aggregate_by_source(tmp_db, company_id)
        assert result.get("sec_filing") == 1


class TestComparePeriods:
    def test_compare(
        self, tmp_db: sqlite3.Connection, company_and_doc: tuple[int, int]
    ) -> None:
        company_id, doc_id = company_and_doc
        signals = [
            ResearchSignalOutput(
                signal_type=SignalType.SENTIMENT,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.HIGH,
                summary="Bullish outlook",
            ),
        ]
        save_signals(tmp_db, doc_id, company_id, signals)
        result = compare_periods(
            tmp_db, company_id,
            "2020-01-01", "2030-12-31",
            "2040-01-01", "2040-12-31",
        )
        assert result["period1"].get("sentiment", 0) >= 1
        assert result["period2"].get("sentiment", 0) == 0


class TestComputeOverallSentiment:
    def test_bullish(
        self, tmp_db: sqlite3.Connection, company_and_doc: tuple[int, int]
    ) -> None:
        company_id, doc_id = company_and_doc
        signals = [
            ResearchSignalOutput(
                signal_type=SignalType.SENTIMENT,
                evidence_type=EvidenceType.FACT,
                confidence=Confidence.HIGH,
                summary="Revenue grew strongly, beating estimates",
            ),
        ]
        save_signals(tmp_db, doc_id, company_id, signals)
        result = compute_overall_sentiment(tmp_db, company_id)
        assert result == "bullish"

    def test_neutral_when_no_signals(self, tmp_db: sqlite3.Connection) -> None:
        company_id = add_company(tmp_db, "AAPL", "Apple Inc")
        result = compute_overall_sentiment(tmp_db, company_id)
        assert result == "neutral"


class TestCheckDocumentExists:
    def test_exists(self, tmp_db: sqlite3.Connection, company_and_doc: tuple[int, int]) -> None:
        assert check_document_exists(tmp_db, "sec_filing", "sec:test-accession-001") is True

    def test_not_exists(self, tmp_db: sqlite3.Connection) -> None:
        assert check_document_exists(tmp_db, "sec_filing", "sec:nonexistent") is False
