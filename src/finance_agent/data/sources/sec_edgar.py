"""SEC EDGAR filing ingestion via edgartools."""

from __future__ import annotations

import logging
import os
import sqlite3

from finance_agent.data.models import SourceDocumentMeta
from finance_agent.data.sources import BaseSource
from finance_agent.data.storage import StorageManager
from finance_agent.research.signals import check_document_exists

logger = logging.getLogger(__name__)

# Filing types we ingest
FILING_TYPES = ["10-K", "10-Q", "8-K"]

# How many recent filings per type to check
MAX_FILINGS_PER_TYPE = 5


class SECEdgarSource(BaseSource):
    """Ingest SEC filings (10-K, 10-Q, 8-K) via edgartools."""

    @property
    def name(self) -> str:
        return "sec"

    def __init__(self, storage: StorageManager, edgar_identity: str) -> None:
        self.storage = storage
        # Set EDGAR identity for SEC rate limiting compliance
        os.environ.setdefault("EDGAR_IDENTITY", edgar_identity)

    def ingest(
        self,
        conn: sqlite3.Connection,
        watchlist: list[dict[str, str | int]],
        since_date: str | None = None,
    ) -> list[SourceDocumentMeta]:
        from edgar import Company

        documents: list[SourceDocumentMeta] = []

        for company in watchlist:
            ticker = str(company["ticker"])
            try:
                ec = Company(ticker)
                filings = ec.get_filings()
            except Exception as e:
                logger.warning("Failed to fetch filings for %s: %s", ticker, e)
                continue

            for form_type in FILING_TYPES:
                try:
                    typed_filings = filings.filter(form=form_type).latest(MAX_FILINGS_PER_TYPE)
                except Exception:
                    typed_filings = []

                for filing in typed_filings:
                    accession = filing.accession_no
                    source_id = f"sec:{accession}"

                    if check_document_exists(conn, "sec_filing", source_id):
                        logger.debug("Skipping already ingested: %s", source_id)
                        continue

                    # Check date filter
                    filed_date = str(filing.filing_date)
                    if since_date and filed_date < since_date:
                        continue

                    try:
                        # Get markdown representation for LLM analysis
                        content = filing.markdown()
                        if not content:
                            content = str(filing.text())
                    except Exception as e:
                        logger.warning("Failed to get content for %s %s: %s", ticker, accession, e)
                        continue

                    # Persist to filesystem
                    filename = f"{accession.replace('/', '_')}.md"
                    self.storage.persist_document(
                        source_type="sec_filing",
                        content=content,
                        filename=filename,
                        ticker=ticker,
                        content_type=form_type,
                    )

                    title = f"{ticker} {form_type} ({filed_date})"
                    metadata = {
                        "accession_no": accession,
                        "form_type": form_type,
                        "cik": str(company.get("cik", "")),
                    }

                    doc = SourceDocumentMeta(
                        source_type="sec_filing",
                        content_type=form_type,
                        source_id=source_id,
                        title=title,
                        published_at=f"{filed_date}T00:00:00Z",
                        content=content,
                        company_ticker=ticker,
                        metadata=metadata,
                    )
                    documents.append(doc)
                    logger.info("Ingested %s %s for %s", form_type, accession, ticker)

        return documents
