"""Data source modules for research ingestion."""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from finance_agent.data.models import SourceDocumentMeta


@dataclass
class SourceResult:
    """Tracks per-source ingestion statistics."""

    source_name: str
    documents_ingested: int = 0
    signals_generated: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class BaseSource(ABC):
    """Abstract base class for data ingestion sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Source name for registry and CLI (e.g., 'sec', 'transcripts')."""
        ...

    @abstractmethod
    def ingest(
        self,
        conn: sqlite3.Connection,
        watchlist: list[dict[str, str | int]],
        since_date: str | None = None,
    ) -> list[SourceDocumentMeta]:
        """Ingest new documents from this source.

        Args:
            conn: Database connection for dedup checks.
            watchlist: List of company dicts with 'ticker', 'name', 'cik' keys.
            since_date: Optional ISO 8601 date to limit ingestion window.

        Returns:
            List of newly ingested document metadata.
        """
        ...
