"""Filesystem storage manager for raw research documents."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Directory hierarchy under research_data/
_DIRECTORY_STRUCTURE = {
    "filings": "{ticker}/{content_type}",
    "transcripts": "{ticker}",
    "market_data": "finnhub/{ticker}",
    "podcasts": "acquired",
    "articles": "stratechery",
}


class StorageManager:
    """Manages filesystem storage for raw research documents."""

    def __init__(self, base_dir: str = "research_data/") -> None:
        self.base_path = Path(base_dir)

    def ensure_directory_structure(self) -> None:
        """Create the research_data/ hierarchy."""
        for category, pattern in _DIRECTORY_STRUCTURE.items():
            # Create the base category directory
            (self.base_path / category).mkdir(parents=True, exist_ok=True)
        logger.info("Research data directory structure verified at %s", self.base_path)

    def persist_document(
        self,
        source_type: str,
        content: str | bytes,
        filename: str,
        ticker: str | None = None,
        content_type: str | None = None,
    ) -> str:
        """Persist a raw document to the filesystem.

        Returns the local path relative to the project root.
        """
        subdir = self._resolve_subdir(source_type, ticker, content_type)
        subdir.mkdir(parents=True, exist_ok=True)

        file_path = subdir / filename
        if isinstance(content, bytes):
            file_path.write_bytes(content)
        else:
            file_path.write_text(content, encoding="utf-8")

        local_path = str(file_path)
        logger.debug("Persisted document: %s (%d bytes)", local_path, file_path.stat().st_size)
        return local_path

    def retrieve_document(self, local_path: str) -> str:
        """Retrieve a document's content from the filesystem."""
        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {local_path}")
        return path.read_text(encoding="utf-8")

    def get_file_size(self, local_path: str) -> int:
        """Get file size in bytes."""
        return Path(local_path).stat().st_size

    @staticmethod
    def compute_hash(content: str | bytes) -> str:
        """Compute SHA-256 hash of content."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def _resolve_subdir(
        self,
        source_type: str,
        ticker: str | None = None,
        content_type: str | None = None,
    ) -> Path:
        """Resolve the subdirectory for a given source type."""
        if source_type == "sec_filing":
            if not ticker:
                raise ValueError("ticker required for sec_filing storage")
            return self.base_path / "filings" / ticker / (content_type or "other")
        elif source_type == "earnings_transcript":
            if not ticker:
                raise ValueError("ticker required for earnings_transcript storage")
            return self.base_path / "transcripts" / ticker
        elif source_type == "finnhub_data":
            return self.base_path / "market_data" / "finnhub" / (ticker or "unknown")
        elif source_type == "podcast_episode":
            return self.base_path / "podcasts" / "acquired"
        elif source_type == "article":
            return self.base_path / "articles" / "stratechery"
        elif source_type == "holdings_13f":
            return self.base_path / "filings" / (ticker or "investors") / "13F"
        else:
            return self.base_path / "other"
