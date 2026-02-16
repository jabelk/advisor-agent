"""13F institutional holdings ingestion for notable investors via edgartools."""

from __future__ import annotations

import json
import logging
import os
import sqlite3

from finance_agent.data.investors import list_investors
from finance_agent.data.models import SourceDocumentMeta
from finance_agent.data.sources import BaseSource
from finance_agent.data.storage import StorageManager
from finance_agent.research.signals import check_document_exists

logger = logging.getLogger(__name__)

# How many recent 13F filings to check per investor
MAX_13F_PER_INVESTOR = 2


class Investor13FSource(BaseSource):
    """Ingest 13F-HR institutional holdings filings for notable investors."""

    @property
    def name(self) -> str:
        return "investors"

    def __init__(self, storage: StorageManager, edgar_identity: str) -> None:
        self.storage = storage
        os.environ.setdefault("EDGAR_IDENTITY", edgar_identity)

    def ingest(
        self,
        conn: sqlite3.Connection,
        watchlist: list[dict[str, str | int]],
        since_date: str | None = None,
    ) -> list[SourceDocumentMeta]:
        from edgar import Company

        documents: list[SourceDocumentMeta] = []
        investors = list_investors(conn)

        if not investors:
            logger.debug("No notable investors configured for tracking")
            return documents

        # Build ticker set from watchlist for filtering
        watchlist_tickers = {str(c["ticker"]).upper() for c in watchlist}

        for investor in investors:
            investor_name = str(investor["name"])
            investor_cik = str(investor["cik"])

            try:
                ec = Company(investor_cik)
                filings = ec.get_filings()
                thirteenfs = filings.filter(form="13F-HR").latest(MAX_13F_PER_INVESTOR)
            except Exception as e:
                logger.warning("Failed to fetch 13F filings for %s: %s", investor_name, e)
                continue

            for filing in thirteenfs:
                accession = filing.accession_no
                source_id = f"13f:{investor_cik}:{accession}"

                if check_document_exists(conn, "holdings_13f", source_id):
                    continue

                filed_date = str(filing.filing_date)
                if since_date and filed_date < since_date:
                    continue

                try:
                    # Get holdings data
                    filing_obj = filing.obj()
                    if hasattr(filing_obj, "holdings"):
                        holdings_df = filing_obj.holdings
                        # Convert to list of dicts for JSON storage
                        if hasattr(holdings_df, "to_dict"):
                            holdings_data = holdings_df.to_dict("records")
                        else:
                            holdings_data = []
                    else:
                        holdings_data = []

                    content = json.dumps({
                        "investor": investor_name,
                        "cik": investor_cik,
                        "filing_date": filed_date,
                        "accession_no": accession,
                        "holdings_count": len(holdings_data),
                        "watchlist_holdings": [
                            h for h in holdings_data
                            if any(t in str(h) for t in watchlist_tickers)
                        ],
                    }, indent=2, default=str)

                except Exception as e:
                    logger.warning(
                        "Failed to parse 13F for %s (%s): %s",
                        investor_name, accession, e,
                    )
                    # Still create document record with basic info
                    content = json.dumps({
                        "investor": investor_name,
                        "cik": investor_cik,
                        "filing_date": filed_date,
                        "accession_no": accession,
                        "parse_error": str(e),
                    }, indent=2)

                # Persist
                filename = f"{investor_cik}_{accession.replace('/', '_')}.json"
                self.storage.persist_document(
                    source_type="holdings_13f",
                    content=content,
                    filename=filename,
                    ticker=investor_cik,
                    content_type="13F",
                )

                title = f"{investor_name} 13F-HR ({filed_date})"
                doc = SourceDocumentMeta(
                    source_type="holdings_13f",
                    content_type="13F-HR",
                    source_id=source_id,
                    title=title,
                    published_at=f"{filed_date}T00:00:00Z",
                    content=content,
                    metadata={
                        "investor_name": investor_name,
                        "investor_cik": investor_cik,
                        "accession_no": accession,
                    },
                )
                documents.append(doc)
                logger.info("Ingested 13F for %s (%s)", investor_name, filed_date)

        return documents
