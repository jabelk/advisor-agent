"""Earnings call transcript ingestion via EarningsCall.biz API."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime
from typing import Any

from finance_agent.data.models import SourceDocumentMeta
from finance_agent.data.sources import BaseSource
from finance_agent.data.storage import StorageManager
from finance_agent.research.signals import check_document_exists

logger = logging.getLogger(__name__)

# How many recent quarters to check per company
MAX_QUARTERS = 8


class EarningsCallSource(BaseSource):
    """Ingest earnings call transcripts via EarningsCall.biz API."""

    @property
    def name(self) -> str:
        return "transcripts"

    def __init__(self, storage: StorageManager, api_key: str = "") -> None:
        self.storage = storage
        self.api_key = api_key

    def _configure_api_key(self) -> None:
        """Set the earningscall API key if provided."""
        if self.api_key:
            import earningscall

            earningscall.api_key = self.api_key

    def ingest(
        self,
        conn: sqlite3.Connection,
        watchlist: list[dict[str, str | int]],
        since_date: str | None = None,
    ) -> list[SourceDocumentMeta]:
        self._configure_api_key()
        from earningscall import get_company

        documents: list[SourceDocumentMeta] = []
        now = datetime.now(UTC)

        for company in watchlist:
            ticker = str(company["ticker"])

            # Build list of (year, quarter) to check
            quarters = self._recent_quarters(now, MAX_QUARTERS)

            for year, quarter in quarters:
                source_id = f"earningscall:{ticker}:{year}:Q{quarter}"

                if check_document_exists(conn, "earnings_transcript", source_id):
                    logger.debug("Skipping already ingested: %s", source_id)
                    continue

                try:
                    ec_company = get_company(ticker)
                    if ec_company is None:
                        logger.warning("Company not found on EarningsCall: %s", ticker)
                        break  # No point trying more quarters

                    transcript = self._fetch_transcript(ec_company, year, quarter)
                    if transcript is None:
                        logger.debug("No transcript for %s Q%d %d", ticker, quarter, year)
                        continue

                    content = self._format_transcript(transcript, ticker, quarter, year)

                    # Persist raw JSON
                    raw_data = {
                        "ticker": ticker, "year": year,
                        "quarter": quarter, "text": str(transcript),
                    }
                    raw_json = json.dumps(raw_data, indent=2)
                    filename = f"{ticker}_Q{quarter}_{year}.json"
                    self.storage.persist_document(
                        source_type="earnings_transcript",
                        content=raw_json,
                        filename=filename,
                        ticker=ticker,
                    )

                    title = f"{ticker} Q{quarter} {year} Earnings Call"
                    published_at = f"{year}-{quarter * 3:02d}-28T00:00:00Z"

                    doc = SourceDocumentMeta(
                        source_type="earnings_transcript",
                        content_type="earnings_call",
                        source_id=source_id,
                        title=title,
                        published_at=published_at,
                        content=content,
                        company_ticker=ticker,
                        metadata={
                            "quarter": quarter,
                            "year": year,
                            "source": "earningscall.biz",
                        },
                    )
                    documents.append(doc)
                    logger.info("Ingested transcript Q%d %d for %s", quarter, year, ticker)

                except Exception as e:
                    logger.warning(
                        "Failed to fetch transcript Q%d %d for %s: %s",
                        quarter, year, ticker, e,
                    )
                    continue

        return documents

    @staticmethod
    def _fetch_transcript(ec_company: Any, year: int, quarter: int) -> Any:
        """Fetch transcript, trying level=2 first then falling back to level=1."""
        try:
            transcript = ec_company.get_transcript(year=year, quarter=quarter, level=2)
            if transcript is not None:
                return transcript
        except Exception:
            # InsufficientApiAccessError or similar — fall back to level=1
            pass

        try:
            return ec_company.get_transcript(year=year, quarter=quarter, level=1)
        except Exception:
            return None

    @staticmethod
    def _format_transcript(transcript: Any, ticker: str, quarter: int, year: int) -> str:
        """Format transcript into readable markdown with speaker attribution."""
        lines: list[str] = []
        lines.append(f"# {ticker} Q{quarter} {year} Earnings Call Transcript")
        lines.append("")

        # The earningscall library returns a Transcript object with .text or speaker entries
        if hasattr(transcript, "speakers") and transcript.speakers:
            current_section: str | None = None
            for speaker in transcript.speakers:
                speaker_name = getattr(speaker, "name", "Unknown")
                speaker_title = getattr(speaker, "title", "")
                speeches = getattr(speaker, "speeches", [])

                # Try to detect section from speaker title
                section = _detect_section(speaker_title)
                if section != current_section:
                    current_section = section
                    lines.append(f"\n## {section}\n")

                header = f"**{speaker_name}**"
                if speaker_title:
                    header += f" ({speaker_title})"
                header += ":"
                lines.append(header)

                for speech in speeches:
                    text = str(speech) if not hasattr(speech, "text") else speech.text
                    lines.append(text)
                lines.append("")
        elif hasattr(transcript, "text") and transcript.text:
            lines.append(str(transcript.text))
        else:
            lines.append(str(transcript))

        return "\n".join(lines)

    @staticmethod
    def _recent_quarters(now: datetime, count: int) -> list[tuple[int, int]]:
        """Generate (year, quarter) tuples for the most recent N quarters."""
        current_quarter = (now.month - 1) // 3 + 1
        year = now.year
        quarter = current_quarter

        quarters: list[tuple[int, int]] = []
        for _ in range(count):
            quarters.append((year, quarter))
            quarter -= 1
            if quarter == 0:
                quarter = 4
                year -= 1
        return quarters


def _detect_section(title: str) -> str:
    """Detect the transcript section from speaker title."""
    if not title:
        return "Discussion"
    lower = title.lower()
    if "operator" in lower or "moderator" in lower:
        return "Q&A Session"
    if "analyst" in lower or "research" in lower:
        return "Q&A Session"
    return "Management Discussion"
