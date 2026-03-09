"""Acquired podcast RSS feed ingestion and transcript retrieval."""

from __future__ import annotations

import json
import logging
import re
import sqlite3

import feedparser

from finance_agent.data.models import SourceDocumentMeta
from finance_agent.data.sources import BaseSource
from finance_agent.data.storage import StorageManager
from finance_agent.research.signals import check_document_exists

logger = logging.getLogger(__name__)

ACQUIRED_RSS_URL = "https://feeds.transistor.fm/acquired"

# Episode classification patterns
_COMPANY_KEYWORDS = re.compile(
    r"^(?:Season \d+ Episode \d+[:\s]+)?(.+?)(?:\s+(?:Part|Pt\.?)\s+\d+)?$",
    re.IGNORECASE,
)
_INTERVIEW_PATTERN = re.compile(r"interview|conversation with|fireside|AMA|Q&A", re.IGNORECASE)
_ACQ2_PATTERN = re.compile(r"ACQ2|acquired2|Season 2", re.IGNORECASE)

# Max episodes to process per run
MAX_EPISODES = 20


class AcquiredPodcastSource(BaseSource):
    """Ingest Acquired podcast episodes via RSS feed."""

    @property
    def name(self) -> str:
        return "acquired"

    def __init__(
        self,
        storage: StorageManager,
        assemblyai_api_key: str = "",
    ) -> None:
        self.storage = storage
        self.assemblyai_api_key = assemblyai_api_key

    def ingest(
        self,
        conn: sqlite3.Connection,
        watchlist: list[dict[str, str | int]],
        since_date: str | None = None,
    ) -> list[SourceDocumentMeta]:
        documents: list[SourceDocumentMeta] = []

        try:
            feed = feedparser.parse(ACQUIRED_RSS_URL)
        except Exception as e:
            logger.warning("Failed to parse Acquired RSS feed: %s", e)
            return documents

        if not feed.entries:
            logger.warning("No entries found in Acquired RSS feed")
            return documents

        for entry in feed.entries[:MAX_EPISODES]:
            # Build source ID from episode URL or GUID
            episode_url = entry.get("link", entry.get("id", ""))
            source_id = f"acquired:{episode_url}"

            if check_document_exists(conn, "podcast_episode", source_id):
                continue

            # Date filter
            published = entry.get("published", "")
            published_at = self._parse_date(published)
            if since_date and published_at < since_date:
                continue

            title = entry.get("title", "Unknown Episode")
            description = entry.get("summary", entry.get("description", ""))

            # Classify episode type
            episode_type = self._classify_episode(title)
            content_type = (
                "podcast_deep_dive" if episode_type == "deep_dive" else "podcast_interview"
            )

            # Build content from available data
            # For now, use description + title as content
            # AssemblyAI transcription would be added here for full transcripts
            content = f"# {title}\n\n"
            content += f"Episode Type: {episode_type}\n"
            content += f"Published: {published_at}\n\n"
            content += f"## Description\n\n{description}\n"

            # Check if there's an audio URL for potential transcription
            audio_url = ""
            for link in entry.get("links", []):
                if link.get("type", "").startswith("audio/"):
                    audio_url = link.get("href", "")
                    break

            # Persist
            safe_title = re.sub(r"[^\w\s-]", "", title)[:80].strip().replace(" ", "_")
            filename = f"{safe_title}.json"
            episode_data = {
                "title": title,
                "url": episode_url,
                "published": published_at,
                "description": description,
                "type": episode_type,
                "audio_url": audio_url,
            }
            self.storage.persist_document(
                source_type="podcast_episode",
                content=json.dumps(episode_data, indent=2),
                filename=filename,
            )

            doc = SourceDocumentMeta(
                source_type="podcast_episode",
                content_type=content_type,
                source_id=source_id,
                title=title,
                published_at=published_at,
                content=content,
                metadata={
                    "episode_type": episode_type,
                    "audio_url": audio_url,
                    "url": episode_url,
                },
            )
            documents.append(doc)
            logger.info("Ingested Acquired episode: %s (%s)", title, episode_type)

        return documents

    @staticmethod
    def _classify_episode(title: str) -> str:
        """Classify episode as deep_dive, interview, or acq2."""
        if _ACQ2_PATTERN.search(title):
            return "acq2"
        if _INTERVIEW_PATTERN.search(title):
            return "interview"
        # Default: company deep-dive (most episodes are this type)
        return "deep_dive"

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Parse RSS date into ISO 8601 format."""
        from email.utils import parsedate_to_datetime

        try:
            dt = parsedate_to_datetime(date_str)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return "1970-01-01T00:00:00Z"
