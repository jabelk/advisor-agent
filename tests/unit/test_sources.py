"""Unit tests for data source modules."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from finance_agent.data.storage import StorageManager


class TestStorageManager:
    def test_ensure_directory_structure(self, tmp_path: Path) -> None:
        storage = StorageManager(str(tmp_path / "research_data"))
        storage.ensure_directory_structure()
        assert (tmp_path / "research_data" / "filings").is_dir()
        assert (tmp_path / "research_data" / "transcripts").is_dir()
        assert (tmp_path / "research_data" / "podcasts").is_dir()
        assert (tmp_path / "research_data" / "articles").is_dir()

    def test_persist_document(self, tmp_path: Path) -> None:
        storage = StorageManager(str(tmp_path / "research_data"))
        storage.ensure_directory_structure()
        path = storage.persist_document(
            source_type="sec_filing",
            content="Filing content here",
            filename="test_filing.md",
            ticker="NVDA",
            content_type="10-K",
        )
        assert Path(path).exists()
        assert Path(path).read_text() == "Filing content here"

    def test_retrieve_document(self, tmp_path: Path) -> None:
        storage = StorageManager(str(tmp_path / "research_data"))
        storage.ensure_directory_structure()
        path = storage.persist_document(
            source_type="sec_filing",
            content="Test content",
            filename="test.md",
            ticker="NVDA",
            content_type="10-K",
        )
        content = storage.retrieve_document(path)
        assert content == "Test content"

    def test_retrieve_nonexistent_raises(self, tmp_path: Path) -> None:
        storage = StorageManager(str(tmp_path / "research_data"))
        with pytest.raises(FileNotFoundError):
            storage.retrieve_document("/nonexistent/path.md")

    def test_compute_hash(self) -> None:
        hash1 = StorageManager.compute_hash("test content")
        hash2 = StorageManager.compute_hash("test content")
        hash3 = StorageManager.compute_hash("different content")
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_persist_bytes(self, tmp_path: Path) -> None:
        storage = StorageManager(str(tmp_path / "research_data"))
        storage.ensure_directory_structure()
        path = storage.persist_document(
            source_type="sec_filing",
            content=b"Binary content",
            filename="test.bin",
            ticker="NVDA",
            content_type="10-K",
        )
        assert Path(path).exists()

    def test_subdir_resolution(self, tmp_path: Path) -> None:
        storage = StorageManager(str(tmp_path / "rd"))
        # SEC filing
        subdir = storage._resolve_subdir("sec_filing", "NVDA", "10-K")
        assert "filings" in str(subdir)
        assert "NVDA" in str(subdir)

        # Earnings transcript
        subdir = storage._resolve_subdir("earnings_transcript", "NVDA")
        assert "transcripts" in str(subdir)

        # Finnhub data
        subdir = storage._resolve_subdir("finnhub_data", "NVDA")
        assert "market_data" in str(subdir)
        assert "finnhub" in str(subdir)

        # Podcast
        subdir = storage._resolve_subdir("podcast_episode")
        assert "podcasts" in str(subdir)

        # Article
        subdir = storage._resolve_subdir("article")
        assert "articles" in str(subdir)


class TestSECEdgarSource:
    def test_source_name(self) -> None:
        from finance_agent.data.sources.sec_edgar import SECEdgarSource

        storage = MagicMock()
        source = SECEdgarSource(storage, "Test test@test.com")
        assert source.name == "sec"

    @patch("edgar.Company")
    def test_ingest_skips_existing(
        self, mock_company_cls: MagicMock, tmp_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        from finance_agent.data.sources.sec_edgar import SECEdgarSource

        storage = StorageManager(str(tmp_path / "rd"))
        storage.ensure_directory_structure()
        source = SECEdgarSource(storage, "Test test@test.com")

        # Insert a document to simulate already-ingested
        tmp_db.execute(
            "INSERT INTO source_document (source_type, content_type, source_id, title, "
            "published_at, content_hash, local_path, file_size_bytes) "
            "VALUES ('sec_filing', '10-K', 'sec:existing-accession', 'test', "
            "'2025-01-01T00:00:00Z', 'abc123', '/tmp/test', 100)"
        )
        tmp_db.commit()

        # Mock Company
        mock_filing = MagicMock()
        mock_filing.accession_no = "existing-accession"
        mock_filing.filing_date = "2025-01-01"

        mock_filings = MagicMock()
        mock_filings.filter.return_value.latest.return_value = [mock_filing]

        mock_ec = MagicMock()
        mock_ec.get_filings.return_value = mock_filings
        mock_company_cls.return_value = mock_ec

        watchlist = [{"ticker": "NVDA", "name": "NVIDIA", "cik": "0001045810"}]
        docs = source.ingest(tmp_db, watchlist)

        # Should skip the existing document
        assert len(docs) == 0


class TestFinnhubMarketSource:
    def test_source_name(self) -> None:
        from finance_agent.data.sources.finnhub import FinnhubMarketSource

        storage = MagicMock()
        source = FinnhubMarketSource(storage, "test_key")
        assert source.name == "finnhub"

    def test_format_analyst_ratings(self) -> None:
        from finance_agent.data.sources.finnhub import _format_analyst_ratings

        data = [
            {
                "period": "2025-02-01", "strongBuy": 10, "buy": 15,
                "hold": 5, "sell": 1, "strongSell": 0,
            },
            {
                "period": "2025-01-01", "strongBuy": 9, "buy": 14,
                "hold": 6, "sell": 2, "strongSell": 0,
            },
        ]
        result = _format_analyst_ratings(data, "NVDA", "2025-02-15")
        assert "# NVDA Analyst Ratings" in result
        assert "Strong Buy" in result
        assert "25 bullish" in result  # 10 + 15

    def test_format_earnings_history(self) -> None:
        from finance_agent.data.sources.finnhub import _format_earnings_history

        data = [
            {
                "period": "2025-01-31", "actual": 0.85, "estimate": 0.80,
                "surprise": 0.05, "surprisePercent": 6.25,
            },
            {
                "period": "2024-10-31", "actual": 0.72, "estimate": 0.75,
                "surprise": -0.03, "surprisePercent": -4.0,
            },
        ]
        result = _format_earnings_history(data, "NVDA")
        assert "# NVDA Earnings History" in result
        assert "1 beats" in result
        assert "1 misses" in result

    def test_format_insider_activity(self) -> None:
        from finance_agent.data.sources.finnhub import _format_insider_activity

        data = [
            {
                "transactionDate": "2025-02-01", "name": "CEO",
                "change": -1000, "transactionPrice": 100,
            },
            {
                "transactionDate": "2025-01-15", "name": "CFO",
                "change": 500, "transactionPrice": 95,
            },
        ]
        result = _format_insider_activity(data, "NVDA")
        assert "# NVDA Insider Transactions" in result
        assert "BUY" in result
        assert "SELL" in result
        assert "1 buys" in result
        assert "1 sells" in result

    def test_format_insider_sentiment(self) -> None:
        from finance_agent.data.sources.finnhub import _format_insider_sentiment

        data = [
            {"month": 1, "year": 2025, "mspr": 42.07, "change": 3934},
            {"month": 2, "year": 2025, "mspr": -15.5, "change": -500},
        ]
        result = _format_insider_sentiment(data, "NVDA")
        assert "# NVDA Insider Sentiment" in result
        assert "MSPR" in result
        assert "1 positive months" in result
        assert "1 negative months" in result

    def test_format_company_news(self) -> None:
        from finance_agent.data.sources.finnhub import _format_company_news

        data = [
            {
                "headline": "NVDA beats earnings",
                "source": "MarketWatch",
                "summary": "Strong quarter results.",
                "datetime": 1739750400,
                "category": "company news",
            },
        ]
        result = _format_company_news(data, "NVDA", "2025-02-17")
        assert "# NVDA Recent News" in result
        assert "NVDA beats earnings" in result
        assert "MarketWatch" in result

    def test_format_empty_data(self) -> None:
        from finance_agent.data.sources.finnhub import (
            _format_analyst_ratings,
            _format_company_news,
            _format_earnings_history,
            _format_insider_activity,
            _format_insider_sentiment,
        )

        assert "No analyst ratings" in _format_analyst_ratings([], "X", "2025-01-01")
        assert "No earnings data" in _format_earnings_history([], "X")
        assert "No insider transactions" in _format_insider_activity([], "X")
        assert "No insider sentiment" in _format_insider_sentiment([], "X")
        assert "No recent news" in _format_company_news([], "X", "2025-01-01")

    @patch("finance_agent.data.sources.finnhub.FinnhubMarketSource._get_client")
    def test_ingest_continues_on_endpoint_error(
        self, mock_get_client: MagicMock, tmp_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        from finance_agent.data.sources.finnhub import FinnhubMarketSource

        storage = StorageManager(str(tmp_path / "rd"))
        storage.ensure_directory_structure()
        source = FinnhubMarketSource(storage, "test_key")

        mock_client = MagicMock()
        # First endpoint fails
        mock_client.recommendation_trends.side_effect = Exception("Rate limit")
        # Second endpoint succeeds with data
        mock_client.company_earnings.return_value = [
            {"period": "2025-01-31", "actual": 0.85, "estimate": 0.80,
             "surprise": 0.05, "surprisePercent": 6.25},
        ]
        # Rest return empty
        mock_client.stock_insider_transactions.return_value = {"data": []}
        mock_client.stock_insider_sentiment.return_value = {"data": []}
        mock_client.company_news.return_value = []
        mock_get_client.return_value = mock_client

        watchlist = [{"ticker": "NVDA", "name": "NVIDIA", "cik": "0001045810"}]
        docs = source.ingest(tmp_db, watchlist)
        # Should get 1 doc from company_earnings despite recommendation_trends failing
        assert len(docs) == 1
        assert docs[0].content_type == "earnings_history"

    @patch("finance_agent.data.sources.finnhub.FinnhubMarketSource._get_client")
    def test_ingest_skips_existing(
        self, mock_get_client: MagicMock, tmp_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        from finance_agent.data.sources.finnhub import FinnhubMarketSource

        storage = StorageManager(str(tmp_path / "rd"))
        storage.ensure_directory_structure()
        source = FinnhubMarketSource(storage, "test_key")

        # Insert existing document for today's date
        from datetime import UTC, datetime

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        tmp_db.execute(
            "INSERT INTO source_document (source_type, content_type, source_id, title, "
            "published_at, content_hash, local_path, file_size_bytes) "
            "VALUES ('finnhub_data', 'analyst_ratings', ?, 'test', "
            "'2025-01-01T00:00:00Z', 'abc', '/tmp/test', 100)",
            (f"finnhub:NVDA:recommendation_trends:{today}",),
        )
        tmp_db.commit()

        mock_client = MagicMock()
        mock_client.recommendation_trends.return_value = [{
            "period": "2025-02-01", "strongBuy": 10, "buy": 15,
            "hold": 5, "sell": 1, "strongSell": 0,
        }]
        # Return empty for all other endpoints
        mock_client.company_earnings.return_value = []
        mock_client.stock_insider_transactions.return_value = {"data": []}
        mock_client.stock_insider_sentiment.return_value = {"data": []}
        mock_client.company_news.return_value = []
        mock_get_client.return_value = mock_client

        watchlist = [{"ticker": "NVDA", "name": "NVIDIA", "cik": "0001045810"}]
        docs = source.ingest(tmp_db, watchlist)
        # recommendation_trends should be skipped (already exists), others have no data
        assert len(docs) == 0


class TestEarningsCallSource:
    def test_source_name(self) -> None:
        from finance_agent.data.sources.earningscall_source import EarningsCallSource

        storage = MagicMock()
        source = EarningsCallSource(storage, "test_key")
        assert source.name == "transcripts"

    def test_format_transcript_with_speakers(self) -> None:
        from finance_agent.data.sources.earningscall_source import EarningsCallSource

        # Mock a transcript with speakers
        transcript = MagicMock()
        speaker1 = MagicMock()
        speaker1.name = "Tim Cook"
        speaker1.title = "CEO"
        speaker1.speeches = ["We had a great quarter with record revenue."]
        speaker2 = MagicMock()
        speaker2.name = "Analyst"
        speaker2.title = "Research Analyst"
        speaker2.speeches = ["What about margins?"]
        transcript.speakers = [speaker1, speaker2]
        transcript.text = None

        result = EarningsCallSource._format_transcript(transcript, "AAPL", 1, 2025)
        assert "# AAPL Q1 2025" in result
        assert "Tim Cook" in result
        assert "great quarter" in result

    def test_format_transcript_text_fallback(self) -> None:
        from finance_agent.data.sources.earningscall_source import EarningsCallSource

        # Mock a transcript with only .text
        transcript = MagicMock()
        transcript.speakers = None
        transcript.text = "Full transcript text here."

        result = EarningsCallSource._format_transcript(transcript, "AAPL", 1, 2025)
        assert "# AAPL Q1 2025" in result
        assert "Full transcript text here." in result

    def test_format_transcript_incomplete_speakers(self) -> None:
        from finance_agent.data.sources.earningscall_source import EarningsCallSource

        # Mock a transcript with speakers missing name/title
        transcript = MagicMock()
        speaker1 = MagicMock()
        speaker1.name = "Unknown"
        speaker1.title = ""
        speaker1.speeches = ["Opening remarks."]
        speaker2 = MagicMock()
        speaker2.name = "Jane Doe"
        speaker2.title = "CFO"
        speaker2.speeches = ["Revenue was strong."]
        transcript.speakers = [speaker1, speaker2]
        transcript.text = None

        result = EarningsCallSource._format_transcript(transcript, "AAPL", 2, 2025)
        assert "# AAPL Q2 2025" in result
        assert "Unknown" in result
        assert "Jane Doe" in result
        assert "Revenue was strong." in result

    def test_format_transcript_empty_speakers_falls_back_to_text(self) -> None:
        from finance_agent.data.sources.earningscall_source import EarningsCallSource

        # Bug case: speakers exist but have empty speeches, .text has real content
        transcript = MagicMock()
        speaker1 = MagicMock()
        speaker1.name = "Unknown"
        speaker1.title = ""
        speaker1.speeches = []
        speaker2 = MagicMock()
        speaker2.name = "Unknown"
        speaker2.title = ""
        speaker2.speeches = []
        transcript.speakers = [speaker1, speaker2]
        transcript.text = "Full earnings call transcript with real content here."

        result = EarningsCallSource._format_transcript(transcript, "CSCO", 3, 2025)
        assert "# CSCO Q3 2025" in result
        assert "Full earnings call transcript" in result
        # Should NOT contain "Unknown" headers with no content
        assert "**Unknown**" not in result

    def test_recent_quarters(self) -> None:
        from datetime import datetime

        from finance_agent.data.sources.earningscall_source import EarningsCallSource

        # Feb 2025 = Q1 2025
        now = datetime(2025, 2, 15)
        quarters = EarningsCallSource._recent_quarters(now, 4)
        assert quarters == [(2025, 1), (2024, 4), (2024, 3), (2024, 2)]

    @patch("earningscall.get_company")
    def test_ingest_skips_existing(
        self, mock_get_company: MagicMock, tmp_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        from finance_agent.data.sources.earningscall_source import EarningsCallSource

        storage = StorageManager(str(tmp_path / "rd"))
        storage.ensure_directory_structure()
        source = EarningsCallSource(storage, "test_key")

        # Insert existing documents for all recent quarters
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        quarters = EarningsCallSource._recent_quarters(now, 8)
        for year, quarter in quarters:
            tmp_db.execute(
                "INSERT INTO source_document (source_type, content_type, source_id, title, "
                "published_at, content_hash, local_path, file_size_bytes) "
                "VALUES ('earnings_transcript', 'earnings_call', ?, 'test', "
                "'2025-01-01T00:00:00Z', 'abc', '/tmp/test', 100)",
                (f"earningscall:AAPL:{year}:Q{quarter}",),
            )
        tmp_db.commit()

        watchlist = [{"ticker": "AAPL", "name": "Apple", "cik": "0000320193"}]
        docs = source.ingest(tmp_db, watchlist)
        # All should be skipped — get_company should never be called
        assert len(docs) == 0
        mock_get_company.assert_not_called()

    @patch("earningscall.get_company")
    def test_ingest_fetches_transcript(
        self, mock_get_company: MagicMock, tmp_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        from finance_agent.data.sources.earningscall_source import EarningsCallSource

        storage = StorageManager(str(tmp_path / "rd"))
        storage.ensure_directory_structure()
        source = EarningsCallSource(storage, "test_key")

        # Mock the earningscall company
        mock_company = MagicMock()
        mock_transcript = MagicMock()
        mock_transcript.speakers = None
        mock_transcript.text = "This is a test transcript."
        mock_company.get_transcript.return_value = mock_transcript
        mock_get_company.return_value = mock_company

        watchlist = [{"ticker": "AAPL", "name": "Apple", "cik": "0000320193"}]
        docs = source.ingest(tmp_db, watchlist)
        # Should get at least one document (the first non-existing quarter)
        assert len(docs) > 0
        assert docs[0].content_type == "earnings_call"
        assert docs[0].source_type == "earnings_transcript"
        assert "earningscall:AAPL:" in docs[0].source_id

    @patch("earningscall.get_company")
    def test_level_fallback(self, mock_get_company: MagicMock) -> None:
        """Test that level=2 failure falls back to level=1."""
        from finance_agent.data.sources.earningscall_source import EarningsCallSource

        mock_company = MagicMock()
        # level=2 raises, level=1 works
        call_count = 0

        def mock_get_transcript(year: int, quarter: int, level: int = 1) -> MagicMock | None:
            nonlocal call_count
            call_count += 1
            if level == 2:
                raise Exception("InsufficientApiAccessError")
            result = MagicMock()
            result.speakers = None
            result.text = "Fallback transcript"
            return result

        mock_company.get_transcript.side_effect = mock_get_transcript

        transcript = EarningsCallSource._fetch_transcript(mock_company, 2025, 1)
        assert transcript is not None
        assert call_count == 2  # Called with level=2, then level=1


class TestAcquiredSource:
    def test_source_name(self) -> None:
        from finance_agent.data.sources.acquired import AcquiredPodcastSource

        storage = MagicMock()
        source = AcquiredPodcastSource(storage)
        assert source.name == "acquired"

    def test_classify_deep_dive(self) -> None:
        from finance_agent.data.sources.acquired import AcquiredPodcastSource

        assert AcquiredPodcastSource._classify_episode("NVIDIA") == "deep_dive"
        assert AcquiredPodcastSource._classify_episode("Season 14 Episode 1: Costco") == "deep_dive"

    def test_classify_interview(self) -> None:
        from finance_agent.data.sources.acquired import AcquiredPodcastSource

        assert AcquiredPodcastSource._classify_episode("Interview with Jensen Huang") == "interview"
        assert AcquiredPodcastSource._classify_episode("Fireside Chat") == "interview"

    def test_classify_acq2(self) -> None:
        from finance_agent.data.sources.acquired import AcquiredPodcastSource

        assert AcquiredPodcastSource._classify_episode("ACQ2: Special Episode") == "acq2"

    @patch("finance_agent.data.sources.acquired.feedparser.parse")
    def test_ingest_with_mock_feed(
        self, mock_parse: MagicMock, tmp_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        from finance_agent.data.sources.acquired import AcquiredPodcastSource

        storage = StorageManager(str(tmp_path / "rd"))
        storage.ensure_directory_structure()
        source = AcquiredPodcastSource(storage)

        mock_parse.return_value = MagicMock(
            entries=[
                {
                    "title": "NVIDIA",
                    "link": "https://example.com/nvidia",
                    "published": "Mon, 01 Jan 2025 00:00:00 GMT",
                    "summary": "Deep dive into NVIDIA",
                    "links": [],
                }
            ]
        )
        watchlist = [{"ticker": "NVDA", "name": "NVIDIA", "cik": ""}]
        docs = source.ingest(tmp_db, watchlist)
        assert len(docs) == 1
        assert docs[0].content_type == "podcast_deep_dive"

    @patch("finance_agent.data.sources.acquired.feedparser.parse")
    def test_ingest_skips_existing(
        self, mock_parse: MagicMock, tmp_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        from finance_agent.data.sources.acquired import AcquiredPodcastSource

        storage = StorageManager(str(tmp_path / "rd"))
        storage.ensure_directory_structure()
        source = AcquiredPodcastSource(storage)

        # Insert existing
        tmp_db.execute(
            "INSERT INTO source_document (source_type, content_type, source_id, title, "
            "published_at, content_hash, local_path, file_size_bytes) "
            "VALUES ('podcast_episode', 'podcast_deep_dive', 'acquired:https://example.com/ep1', "
            "'test', '2025-01-01T00:00:00Z', 'abc', '/tmp/test', 100)"
        )
        tmp_db.commit()

        mock_parse.return_value = MagicMock(
            entries=[
                {
                    "title": "Test Episode",
                    "link": "https://example.com/ep1",
                    "published": "Mon, 01 Jan 2025 00:00:00 GMT",
                    "summary": "Test",
                    "links": [],
                }
            ]
        )
        docs = source.ingest(tmp_db, [])
        assert len(docs) == 0


class TestStratecherySource:
    def test_source_name(self) -> None:
        from finance_agent.data.sources.stratechery import StratecherySource

        storage = MagicMock()
        source = StratecherySource(storage, "https://example.com/feed")
        assert source.name == "stratechery"

    def test_html_to_text(self) -> None:
        from finance_agent.data.sources.stratechery import StratecherySource

        html = "<p>Hello <strong>world</strong></p><p>Second paragraph</p>"
        text = StratecherySource._html_to_text(html)
        assert "Hello" in text
        assert "world" in text
        assert "Second paragraph" in text
        assert "<p>" not in text

    def test_classify_article(self) -> None:
        from finance_agent.data.sources.stratechery import StratecherySource

        assert StratecherySource._classify_content("The AI Revolution", "") == "analysis_article"

    def test_classify_interview(self) -> None:
        from finance_agent.data.sources.stratechery import StratecherySource

        result = StratecherySource._classify_content("Interview with Tim Cook", "")
        assert result == "podcast_interview"

    def test_classify_daily_update(self) -> None:
        from finance_agent.data.sources.stratechery import StratecherySource

        assert StratecherySource._classify_content("Daily Update: Apple News", "") == "daily_update"

    @patch("finance_agent.data.sources.stratechery.feedparser.parse")
    def test_ingest_with_mock_feed(
        self, mock_parse: MagicMock, tmp_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        from finance_agent.data.sources.stratechery import StratecherySource

        storage = StorageManager(str(tmp_path / "rd"))
        storage.ensure_directory_structure()
        source = StratecherySource(storage, "https://example.com/feed")

        entry = MagicMock()
        entry.get.side_effect = lambda k, d="": {
            "link": "https://stratechery.com/article-1",
            "id": "https://stratechery.com/article-1",
            "published": "Mon, 01 Jan 2025 00:00:00 GMT",
            "title": "The AI Revolution",
        }.get(k, d)
        entry.content = [{"value": "<p>Article content here</p>"}]
        entry.__getitem__ = lambda self, k: getattr(self, k)

        mock_parse.return_value = MagicMock(
            entries=[entry],
            bozo=False,
        )
        docs = source.ingest(tmp_db, [])
        assert len(docs) == 1
        assert docs[0].content_type == "analysis_article"

    @patch("finance_agent.data.sources.stratechery.feedparser.parse")
    def test_auth_failure_returns_empty(
        self, mock_parse: MagicMock, tmp_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        from finance_agent.data.sources.stratechery import StratecherySource

        storage = StorageManager(str(tmp_path / "rd"))
        source = StratecherySource(storage, "https://example.com/bad-feed")

        mock_parse.return_value = MagicMock(
            entries=[],
            bozo=True,
            bozo_exception=Exception("401 Unauthorized"),
        )
        docs = source.ingest(tmp_db, [])
        assert len(docs) == 0


class TestInvestor13FSource:
    def test_source_name(self) -> None:
        from finance_agent.data.sources.investor_13f import Investor13FSource

        storage = MagicMock()
        source = Investor13FSource(storage, "Test test@test.com")
        assert source.name == "investors"

    def test_ingest_no_investors_configured(
        self, tmp_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        from finance_agent.data.sources.investor_13f import Investor13FSource

        storage = StorageManager(str(tmp_path / "rd"))
        source = Investor13FSource(storage, "Test test@test.com")
        docs = source.ingest(tmp_db, [])
        assert len(docs) == 0


class TestInvestorCRUD:
    def test_add_investor(self, tmp_db: sqlite3.Connection) -> None:
        from finance_agent.data.investors import add_investor

        inv_id = add_investor(tmp_db, "Berkshire Hathaway", "0001067983")
        assert inv_id > 0
        row = tmp_db.execute(
            "SELECT * FROM notable_investor WHERE id = ?", (inv_id,)
        ).fetchone()
        assert row["name"] == "Berkshire Hathaway"
        assert row["cik"] == "0001067983"
        assert row["active"] == 1

    def test_add_duplicate_raises(self, tmp_db: sqlite3.Connection) -> None:
        from finance_agent.data.investors import add_investor

        add_investor(tmp_db, "Berkshire Hathaway", "0001067983")
        with pytest.raises(ValueError, match="already being tracked"):
            add_investor(tmp_db, "Berkshire Hathaway", "0001067983")

    def test_remove_investor(self, tmp_db: sqlite3.Connection) -> None:
        from finance_agent.data.investors import add_investor, remove_investor

        add_investor(tmp_db, "Berkshire Hathaway", "0001067983")
        result = remove_investor(tmp_db, "Berkshire Hathaway")
        assert result is True
        row = tmp_db.execute(
            "SELECT active FROM notable_investor WHERE name = 'Berkshire Hathaway'"
        ).fetchone()
        assert row["active"] == 0

    def test_list_investors(self, tmp_db: sqlite3.Connection) -> None:
        from finance_agent.data.investors import add_investor, list_investors

        add_investor(tmp_db, "Berkshire Hathaway", "0001067983")
        add_investor(tmp_db, "ARK Invest", "0001803994")
        investors = list_investors(tmp_db)
        assert len(investors) == 2
