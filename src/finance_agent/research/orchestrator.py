"""Research pipeline orchestrator: coordinates ingestion, analysis, and signal storage."""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import UTC, datetime

from finance_agent.audit.logger import AuditLogger
from finance_agent.config import Settings
from finance_agent.data.sources import BaseSource, SourceResult
from finance_agent.data.storage import StorageManager
from finance_agent.data.watchlist import get_company_by_ticker, list_companies
from finance_agent.research.analyzer import Analyzer
from finance_agent.research.pipeline import (
    complete_run,
    fail_run,
    save_document_record,
    set_document_status,
    start_run,
)
from finance_agent.research.signals import save_signals

logger = logging.getLogger(__name__)

# Source name → module mapping
SOURCE_MODULES = {
    "sec": "finance_agent.data.sources.sec_edgar",
    "transcripts": "finance_agent.data.sources.earningscall_source",
    "finnhub": "finance_agent.data.sources.finnhub",
    "acquired": "finance_agent.data.sources.acquired",
    "stratechery": "finance_agent.data.sources.stratechery",
    "investors": "finance_agent.data.sources.investor_13f",
}


def _build_sources(settings: Settings, storage: StorageManager) -> dict[str, BaseSource]:
    """Build available source instances based on configuration."""
    sources: dict[str, BaseSource] = {}

    if settings.sec_edgar_available:
        from finance_agent.data.sources.sec_edgar import SECEdgarSource

        sources["sec"] = SECEdgarSource(storage, settings.edgar_identity)

    # Earnings call transcripts via EarningsCall.biz
    try:
        from finance_agent.data.sources.earningscall_source import EarningsCallSource

        sources["transcripts"] = EarningsCallSource(
            storage, settings.earningscall_api_key
        )
    except ImportError:
        logger.debug("EarningsCall source not available")

    # Finnhub market signals (free-tier endpoints)
    if settings.finnhub_available:
        from finance_agent.data.sources.finnhub import FinnhubMarketSource

        sources["finnhub"] = FinnhubMarketSource(storage, settings.finnhub_api_key)

    # Acquired podcast is always available (RSS is free)
    try:
        from finance_agent.data.sources.acquired import AcquiredPodcastSource

        sources["acquired"] = AcquiredPodcastSource(
            storage, assemblyai_api_key=settings.assemblyai_api_key
        )
    except ImportError:
        logger.debug("Acquired podcast source not yet implemented")

    if settings.stratechery_available:
        try:
            from finance_agent.data.sources.stratechery import StratecherySource

            sources["stratechery"] = StratecherySource(storage, settings.stratechery_feed_url)
        except ImportError:
            logger.debug("Stratechery source not yet implemented")

    # 13F investor source (always available, uses edgartools)
    try:
        from finance_agent.data.sources.investor_13f import Investor13FSource

        if settings.sec_edgar_available:
            sources["investors"] = Investor13FSource(storage, settings.edgar_identity)
    except ImportError:
        logger.debug("13F investor source not yet implemented")

    return sources


def run_research_pipeline(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    settings: Settings,
    sources: list[str] | None = None,
    ticker: str | None = None,
    full: bool = False,
) -> None:
    """Run the research ingestion and analysis pipeline."""
    start_time = time.time()
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Get watchlist
    if ticker:
        company = get_company_by_ticker(conn, ticker.upper())
        if not company:
            print(f"Error: {ticker.upper()} is not on the watchlist")
            return
        watchlist = [company]
    else:
        watchlist = list_companies(conn)

    if not watchlist:
        print(
            "Warning: No companies on watchlist. "
            "Add one with: finance-agent watchlist add <TICKER>"
        )
        return

    # Setup storage
    storage = StorageManager(settings.research_data_dir)
    storage.ensure_directory_structure()

    # Build sources
    available_sources = _build_sources(settings, storage)
    if sources:
        # Filter to requested sources
        available_sources = {k: v for k, v in available_sources.items() if k in sources}

    if not available_sources:
        print("Warning: No research sources configured. Set API keys in .env")
        return

    # Start ingestion run
    run_id = start_run(conn)
    audit.log("research_start", "pipeline", {
        "run_id": run_id,
        "companies": len(watchlist),
        "sources": list(available_sources.keys()),
    })

    tickers_str = ", ".join(str(c["ticker"]) for c in watchlist)
    sources_str = ", ".join(available_sources.keys())
    print(f"Research Ingestion — {now}")
    print(f"Watchlist: {len(watchlist)} companies ({tickers_str}) | Sources: {sources_str}")
    print()

    # Initialize analyzer if API key available
    analyzer: Analyzer | None = None
    if settings.anthropic_available:
        analyzer = Analyzer(settings.anthropic_api_key)
    else:
        print("Warning: ANTHROPIC_API_KEY not set — documents will be ingested but not analyzed")

    total_docs = 0
    total_signals = 0
    source_stats: dict[str, dict[str, int]] = {}
    errors: list[str] = []

    # Process each source
    for source_name, source in available_sources.items():
        result = SourceResult(source_name=source_name)
        print(f"{source_name.upper()}:")

        try:
            # Ingest new documents
            watchlist_for_source: list[dict[str, str | int]] = [
                {k: v for k, v in c.items() if v is not None}
                for c in watchlist
            ]
            documents = source.ingest(conn, watchlist_for_source)

            for doc in documents:
                try:
                    # Save document record
                    if doc.company_ticker:
                        company = get_company_by_ticker(conn, doc.company_ticker)
                    else:
                        company = None
                    company_id = (
                        int(company["id"])
                        if company and company["id"] is not None
                        else None
                    )

                    content_hash = StorageManager.compute_hash(doc.content)
                    local_path = storage.persist_document(
                        source_type=doc.source_type,
                        content=doc.content,
                        filename=f"{doc.source_id.replace(':', '_').replace('/', '_')}.txt",
                        ticker=doc.company_ticker,
                        content_type=doc.content_type,
                    )
                    file_size = storage.get_file_size(local_path)

                    doc_id = save_document_record(
                        conn,
                        company_id=company_id,
                        source_type=doc.source_type,
                        content_type=doc.content_type,
                        source_id=doc.source_id,
                        title=doc.title,
                        published_at=doc.published_at,
                        content_hash=content_hash,
                        local_path=local_path,
                        file_size_bytes=file_size,
                    )

                    result.documents_ingested += 1
                    total_docs += 1

                    # Analyze with LLM
                    if analyzer and company_id is not None:
                        try:
                            set_document_status(conn, doc_id, "analyzing")
                            analysis = analyzer.analyze_document(
                                doc.content, doc.content_type, doc.company_ticker or ""
                            )
                            signal_count = save_signals(
                                conn, doc_id, company_id, analysis.signals
                            )
                            set_document_status(conn, doc_id, "complete")
                            result.signals_generated += signal_count
                            total_signals += signal_count

                            ticker_label = doc.company_ticker or "?"
                            print(
                                f"  {ticker_label}: {doc.title} — "
                                f"{signal_count} signals generated"
                            )
                        except Exception as e:
                            set_document_status(conn, doc_id, "failed", str(e))
                            result.errors.append(f"{doc.title}: {e}")
                            logger.warning("Analysis failed for %s: %s", doc.title, e)
                    else:
                        ticker_label = doc.company_ticker or "?"
                        print(f"  {ticker_label}: {doc.title} — ingested (pending analysis)")

                except Exception as e:
                    result.errors.append(f"{doc.source_id}: {e}")
                    logger.warning("Failed to process document %s: %s", doc.source_id, e)

            if result.documents_ingested == 0:
                print("  No new documents")

        except Exception as e:
            error_msg = f"{source_name}: {e}"
            result.errors.append(error_msg)
            errors.append(error_msg)
            logger.error("Source %s failed: %s", source_name, e)
            print(f"  Error: {e}")

        print()
        source_stats[source_name] = {
            "docs": result.documents_ingested,
            "signals": result.signals_generated,
            "errors": len(result.errors),
        }

    # Complete run
    duration = time.time() - start_time
    minutes = int(duration // 60)
    seconds = int(duration % 60)

    if errors:
        fail_run(conn, run_id, errors)
    else:
        complete_run(conn, run_id, total_docs, total_signals, source_stats)

    audit.log("research_complete", "pipeline", {
        "run_id": run_id,
        "documents": total_docs,
        "signals": total_signals,
        "errors": len(errors),
        "duration_seconds": round(duration, 1),
    })

    print("Summary:")
    print(f"  Documents: {total_docs} new")
    print(f"  Signals: {total_signals} new")
    print(f"  Errors: {len(errors)}")
    print(f"  Duration: {minutes}m {seconds}s")
