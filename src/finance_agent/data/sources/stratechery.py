"""Stratechery content ingestion via authenticated RSS feed."""

from __future__ import annotations

import logging
import re
import sqlite3

import feedparser
from bs4 import BeautifulSoup

from finance_agent.data.models import SourceDocumentMeta
from finance_agent.data.sources import BaseSource
from finance_agent.data.storage import StorageManager
from finance_agent.research.signals import check_document_exists

logger = logging.getLogger(__name__)

# Max articles to process per run
MAX_ARTICLES = 30

# Content classification patterns
_INTERVIEW_PATTERN = re.compile(r"interview|conversation|podcast|episode", re.IGNORECASE)
_DAILY_UPDATE_PATTERN = re.compile(r"daily update|update:", re.IGNORECASE)


class StratecherySource(BaseSource):
    """Ingest Stratechery articles via authenticated RSS feed."""

    @property
    def name(self) -> str:
        return "stratechery"

    def __init__(self, storage: StorageManager, feed_url: str) -> None:
        self.storage = storage
        self.feed_url = feed_url

    def ingest(
        self,
        conn: sqlite3.Connection,
        watchlist: list[dict[str, str | int]],
        since_date: str | None = None,
    ) -> list[SourceDocumentMeta]:
        documents: list[SourceDocumentMeta] = []

        try:
            feed = feedparser.parse(
                self.feed_url,
                request_headers={"User-Agent": "finance-agent/0.2.0"},
            )
        except Exception as e:
            logger.warning("Failed to parse Stratechery RSS feed: %s", e)
            return documents

        # Check for auth failure
        if feed.bozo and not feed.entries:
            logger.warning(
                "Stratechery feed returned error (check credentials): %s",
                getattr(feed, "bozo_exception", "unknown error"),
            )
            return documents

        if not feed.entries:
            logger.warning("No entries found in Stratechery feed")
            return documents

        for entry in feed.entries[:MAX_ARTICLES]:
            article_url = entry.get("link", entry.get("id", ""))
            source_id = f"stratechery:{article_url}"

            if check_document_exists(conn, "article", source_id):
                continue

            # Date filter
            published = entry.get("published", "")
            published_at = self._parse_date(published)
            if since_date and published_at < since_date:
                continue

            title = entry.get("title", "Unknown Article")

            # Get full HTML content
            content_html = ""
            if entry.get("content"):
                content_html = entry.content[0].get("value", "")
            elif entry.get("summary"):
                content_html = entry.summary

            # Convert HTML to plain text
            content_text = self._html_to_text(content_html)

            # Classify content type
            content_type = self._classify_content(title, content_text)

            # Build analysis-ready content
            content = f"# {title}\n\n"
            content += f"Published: {published_at}\n"
            content += f"Content Type: {content_type}\n\n"
            content += content_text

            # Persist HTML version
            safe_title = re.sub(r"[^\w\s-]", "", title)[:80].strip().replace(" ", "_")
            filename = f"{safe_title}.html"
            self.storage.persist_document(
                source_type="article",
                content=content_html,
                filename=filename,
            )

            doc = SourceDocumentMeta(
                source_type="article",
                content_type=content_type,
                source_id=source_id,
                title=title,
                published_at=published_at,
                content=content,
                metadata={
                    "url": article_url,
                    "content_type": content_type,
                },
            )
            documents.append(doc)
            logger.info("Ingested Stratechery: %s (%s)", title, content_type)

        return documents

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Convert HTML content to plain text preserving structure."""
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n", strip=True)

    @staticmethod
    def _classify_content(title: str, content: str) -> str:
        """Classify as analysis_article, daily_update, or podcast_interview."""
        if _INTERVIEW_PATTERN.search(title):
            return "podcast_interview"
        if _DAILY_UPDATE_PATTERN.search(title):
            return "daily_update"
        return "analysis_article"

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Parse RSS date into ISO 8601 format."""
        from email.utils import parsedate_to_datetime

        try:
            dt = parsedate_to_datetime(date_str)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return "1970-01-01T00:00:00Z"
