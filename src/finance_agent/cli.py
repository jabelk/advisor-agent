"""CLI entry point for finance-agent: health check, research, and management commands."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from finance_agent import __version__
from finance_agent.audit.logger import AuditLogger
from finance_agent.config import ConfigError, Settings, load_settings, validate_settings


def _get_db_and_audit() -> tuple[sqlite3.Connection, AuditLogger, Settings]:
    """Shared helper to get DB connection and audit logger."""
    from finance_agent.db import get_connection, run_migrations

    settings = load_settings()
    migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
    conn = get_connection(settings.db_path)
    run_migrations(conn, migrations_dir)
    audit = AuditLogger(conn)
    return conn, audit, settings


def main(argv: list[str] | None = None) -> None:
    """Main CLI entry point, registered as console_script 'finance-agent'."""
    parser = argparse.ArgumentParser(
        prog="finance-agent",
        description="Research-powered investment system using Alpaca Markets",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("version", help="Print version and exit")
    subparsers.add_parser("health", help="Run health checks")

    # Watchlist commands
    watchlist_parser = subparsers.add_parser("watchlist", help="Manage research watchlist")
    watchlist_sub = watchlist_parser.add_subparsers(dest="watchlist_command")
    wl_add = watchlist_sub.add_parser("add", help="Add a company to the watchlist")
    wl_add.add_argument("ticker", help="Stock ticker symbol (e.g., NVDA)")
    wl_remove = watchlist_sub.add_parser("remove", help="Remove a company from the watchlist")
    wl_remove.add_argument("ticker", help="Stock ticker symbol")
    watchlist_sub.add_parser("list", help="List watchlist companies")

    # Investors commands
    investors_parser = subparsers.add_parser("investors", help="Manage notable investor tracking")
    investors_sub = investors_parser.add_subparsers(dest="investors_command")
    inv_add = investors_sub.add_parser("add", help="Add a notable investor")
    inv_add.add_argument("name", help="Investor/fund name")
    inv_add.add_argument("cik", help="SEC CIK number")
    inv_remove = investors_sub.add_parser("remove", help="Stop tracking an investor")
    inv_remove.add_argument("name", help="Investor/fund name")
    investors_sub.add_parser("list", help="List tracked investors")

    # Research commands
    research_parser = subparsers.add_parser("research", help="Run research ingestion")
    research_sub = research_parser.add_subparsers(dest="research_command")
    run_parser = research_sub.add_parser("run", help="Run research pipeline")
    run_parser.add_argument(
        "--source", action="append", dest="sources",
        help="Limit to specific source "
        "(sec, transcripts, finnhub, acquired, stratechery, investors)",
    )
    run_parser.add_argument("--ticker", help="Limit to specific ticker")
    run_parser.add_argument("--full", action="store_true", help="Force re-analysis of all docs")
    research_sub.add_parser("status", help="Show research pipeline status")

    # Signals command
    signals_parser = subparsers.add_parser("signals", help="Query research signals")
    signals_parser.add_argument("ticker", help="Stock ticker symbol")
    signals_parser.add_argument("--type", dest="signal_type", help="Filter by signal type")
    signals_parser.add_argument("--since", help="Start date (ISO 8601)")
    signals_parser.add_argument("--until", help="End date (ISO 8601)")
    signals_parser.add_argument("--source", help="Filter by source type")

    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Show company research profile")
    profile_parser.add_argument("ticker", help="Stock ticker symbol")

    # MCP server command
    mcp_parser = subparsers.add_parser("mcp", help="Start the MCP research server")
    mcp_parser.add_argument(
        "--http", action="store_true",
        help="Run in HTTP mode (0.0.0.0:8000) instead of stdio",
    )

    args = parser.parse_args(argv)

    if args.command == "version":
        cmd_version()
    elif args.command == "health":
        cmd_health()
    elif args.command == "watchlist":
        cmd_watchlist(args)
    elif args.command == "investors":
        cmd_investors(args)
    elif args.command == "research":
        cmd_research(args)
    elif args.command == "signals":
        cmd_signals(args)
    elif args.command == "profile":
        cmd_profile(args)
    elif args.command == "mcp":
        cmd_mcp(args)
    else:
        parser.print_help()
        sys.exit(1)


def cmd_version() -> None:
    """Print version and exit."""
    print(f"finance-agent {__version__}")
    sys.exit(0)


def cmd_health() -> None:
    """Validate configuration, database, and broker connectivity."""
    from finance_agent.db import (
        DatabaseError,
        close_connection,
        get_connection,
        get_schema_version,
        run_migrations,
    )

    audit: AuditLogger | None = None

    # --- Load config ---
    try:
        settings = load_settings()
    except ConfigError as e:
        print(f"[PAPER MODE] Finance Agent v{__version__}")
        print("Configuration: FAIL")
        print(f"  - {e}")
        sys.exit(1)

    print(f"[{settings.mode_label}] Finance Agent v{__version__}")

    if settings.is_live:
        print("  *** WARNING: LIVE TRADING MODE — real money at risk ***")

    for warning in settings.warnings:
        print(f"  WARNING: {warning}")

    # --- Validate config ---
    errors = validate_settings(settings)
    if errors:
        print("Configuration: FAIL")
        for error in errors:
            print(f"  - {error}")
        print("Database: SKIP (configuration incomplete)")
        sys.exit(1)

    print("Configuration: OK (all required settings present)")

    # --- Database ---
    migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
    db_ok = False
    conn = None
    try:
        conn = get_connection(settings.db_path)
        applied = run_migrations(conn, migrations_dir)
        version = get_schema_version(conn)
        db_name = Path(settings.db_path).name
        print(f"Database: OK ({db_name}, schema version {version})")
        db_ok = True

        audit = AuditLogger(conn)
        audit.log("startup", "cli", {"version": __version__})
        audit.log("config_validated", "config", {
            "mode": settings.trading_mode,
            "is_live": settings.is_live,
        })
        audit.log("db_initialized", "db", {"path": settings.db_path})
        audit.log("migrations_applied", "db", {
            "applied": applied,
            "schema_version": version,
        })
    except DatabaseError as e:
        print(f"Database: FAIL ({e})")
    except Exception as e:
        print(f"Database: FAIL (unexpected: {e})")

    # --- Research Pipeline ---
    research_ok = False
    if db_ok and conn:
        try:
            from finance_agent.research.pipeline import get_last_run

            last_run = get_last_run(conn)
            if last_run:
                started = str(last_run['started_at'])[:16]
                print(f"Research Pipeline: OK (last run: {started})")
            else:
                print("Research Pipeline: OK (no runs yet)")
            research_ok = True
        except Exception as e:
            print(f"Research Pipeline: FAIL ({e})")

    if audit:
        audit.log("health_check", "cli", {
            "config_ok": True,
            "db_ok": db_ok,
            "research_ok": research_ok,
        })

    if conn:
        close_connection(conn)

    sys.exit(0 if db_ok else 1)


def cmd_watchlist(args: argparse.Namespace) -> None:
    """Handle watchlist subcommands."""
    from finance_agent.data.watchlist import (
        add_company,
        get_company_by_ticker,
        list_companies,
        remove_company,
    )
    from finance_agent.db import close_connection
    from finance_agent.research.signals import get_signal_counts

    conn, audit, _settings = _get_db_and_audit()

    try:
        if args.watchlist_command == "add":
            ticker = args.ticker.upper()
            # Check if already on watchlist
            existing = get_company_by_ticker(conn, ticker)
            if existing:
                print(f"{ticker} is already on the watchlist")
                sys.exit(0)

            # Resolve company info via edgartools
            try:
                from edgar import Company as EdgarCompany

                ec = EdgarCompany(ticker)
                name = ec.name
                cik = str(ec.cik).zfill(10)
            except Exception:
                name = ticker
                cik = None

            company_id = add_company(conn, ticker, name, cik)
            cik_str = f", CIK: {cik}" if cik else ""
            print(f"Added {ticker} ({name}{cik_str}) to watchlist")
            audit.log("watchlist_add", "cli", {"ticker": ticker, "company_id": company_id})

        elif args.watchlist_command == "remove":
            ticker = args.ticker.upper()
            removed = remove_company(conn, ticker)
            if removed:
                print(f"Removed {ticker} from watchlist (existing research data preserved)")
                audit.log("watchlist_remove", "cli", {"ticker": ticker})
            else:
                print(f"Error: {ticker} is not on the watchlist")
                sys.exit(1)

        elif args.watchlist_command == "list":
            companies = list_companies(conn)
            print(f"Research Watchlist ({len(companies)} companies):")
            print()
            if not companies:
                print(
                    "  No companies on watchlist. "
                    "Add one with: finance-agent watchlist add <TICKER>"
                )
            else:
                for c in companies:
                    c_id = c["id"]
                    assert c_id is not None
                    counts = get_signal_counts(conn, int(c_id))
                    total_signals = sum(counts.values())
                    # Get last signal date
                    last_row = conn.execute(
                        "SELECT MAX(created_at) as last_date FROM research_signal "
                        "WHERE company_id = ?", (c["id"],)
                    ).fetchone()
                    has_date = last_row and last_row["last_date"]
                    last_date = last_row["last_date"][:10] if has_date else "never"
                    print(
                        f"  {c['ticker']:<6}{c['name']:<30}"
                        f"{total_signals:>3} signals  (last: {last_date})"
                    )
        else:
            print("Usage: finance-agent watchlist {add|remove|list}")
            sys.exit(1)
    finally:
        close_connection(conn)


def cmd_investors(args: argparse.Namespace) -> None:
    """Handle investors subcommands."""
    from finance_agent.data.investors import add_investor, list_investors, remove_investor
    from finance_agent.db import close_connection

    conn, audit, _settings = _get_db_and_audit()

    try:
        if args.investors_command == "add":
            try:
                investor_id = add_investor(conn, args.name, args.cik)
                print(f'Added "{args.name}" (CIK: {args.cik}) to investor tracking')
                audit.log("investor_add", "cli", {
                    "name": args.name, "cik": args.cik, "investor_id": investor_id,
                })
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)

        elif args.investors_command == "remove":
            removed = remove_investor(conn, args.name)
            if removed:
                print(f'Removed "{args.name}" from investor tracking')
                audit.log("investor_remove", "cli", {"name": args.name})
            else:
                print(f'Error: "{args.name}" is not being tracked')
                sys.exit(1)

        elif args.investors_command == "list":
            investors = list_investors(conn)
            print(f"Tracked Investors ({len(investors)}):")
            print()
            if not investors:
                print(
                    "  No investors tracked. "
                    'Add one with: finance-agent investors add "Name" CIK'
                )
            else:
                for inv in investors:
                    # Get last 13F date
                    last_row = conn.execute(
                        "SELECT MAX(published_at) as last_date FROM source_document "
                        "WHERE source_type = 'holdings_13f' AND metadata_json LIKE ?",
                        (f'%{inv["cik"]}%',),
                    ).fetchone()
                    has_date = last_row and last_row["last_date"]
                    last_date = last_row["last_date"][:10] if has_date else "never"
                    print(f'  {inv["name"]:<25}CIK: {inv["cik"]}    last 13F: {last_date}')
        else:
            print("Usage: finance-agent investors {add|remove|list}")
            sys.exit(1)
    finally:
        close_connection(conn)


def cmd_research(args: argparse.Namespace) -> None:
    """Handle research subcommands."""
    from finance_agent.db import close_connection
    from finance_agent.research.orchestrator import run_research_pipeline

    conn, audit, settings = _get_db_and_audit()

    try:
        if args.research_command == "run" or args.research_command is None:
            sources = getattr(args, "sources", None)
            ticker = getattr(args, "ticker", None)
            full = getattr(args, "full", False)
            run_research_pipeline(conn, audit, settings, sources=sources, ticker=ticker, full=full)

        elif args.research_command == "status":
            _show_research_status(conn, settings)

        else:
            print("Usage: finance-agent research {run|status}")
            sys.exit(1)
    finally:
        close_connection(conn)


def _show_research_status(conn: sqlite3.Connection, settings: Settings) -> None:
    """Display research pipeline status."""
    from finance_agent.research.pipeline import get_last_run

    last_run = get_last_run(conn)
    print("Research Status:")
    print()

    if last_run:
        duration = ""
        if last_run.get("completed_at") and last_run.get("started_at"):
            duration = f" ({last_run['status']})"
        print(f"Last run: {last_run['started_at']}{duration}")
    else:
        print("Last run: never")

    # Document counts
    doc_stats = conn.execute(
        "SELECT analysis_status, COUNT(*) as cnt FROM source_document GROUP BY analysis_status"
    ).fetchall()
    doc_counts = {row["analysis_status"]: row["cnt"] for row in doc_stats}
    total_docs = sum(doc_counts.values())
    analyzed = doc_counts.get("complete", 0)
    pending = doc_counts.get("pending", 0)
    failed = doc_counts.get("failed", 0)

    # Signal count
    signal_count = conn.execute("SELECT COUNT(*) as cnt FROM research_signal").fetchone()["cnt"]
    company_count = conn.execute(
        "SELECT COUNT(DISTINCT company_id) as cnt FROM research_signal"
    ).fetchone()["cnt"]

    print(
        f"Documents: {total_docs} total "
        f"({analyzed} analyzed, {pending} pending, {failed} failed)"
    )
    print(f"Signals: {signal_count} total across {company_count} companies")
    print()

    # Source status
    print("Sources:")
    source_configs = [
        ("SEC EDGAR", "sec_filing", settings.sec_edgar_available),
        ("Transcripts", "earnings_transcript", True),
        ("Finnhub Mkt", "finnhub_data", settings.finnhub_available),
        ("Acquired", "podcast_episode", True),
        ("Stratechery", "article", settings.stratechery_available),
        ("13F Holdings", "holdings_13f", True),
    ]
    for label, source_type, enabled in source_configs:
        if not enabled:
            print(f"  {label:<16}DISABLED")
            continue
        last = conn.execute(
            "SELECT MAX(ingested_at) as last_date, COUNT(*) as cnt "
            "FROM source_document WHERE source_type = ?",
            (source_type,),
        ).fetchone()
        count = last["cnt"]
        last_date = last["last_date"][:10] if last and last["last_date"] else "never"
        print(f"  {label:<16}OK (last: {last_date}, {count} documents)")

    # Failed documents
    if failed > 0:
        print()
        print(f"Failed documents ({failed}):")
        failed_docs = conn.execute(
            "SELECT sd.title, sd.analysis_error, c.ticker FROM source_document sd "
            "LEFT JOIN company c ON sd.company_id = c.id "
            "WHERE sd.analysis_status = 'failed' LIMIT 10"
        ).fetchall()
        for doc in failed_docs:
            ticker = doc["ticker"] or "?"
            print(f"  {ticker} {doc['title']}: {doc['analysis_error']}")


def cmd_signals(args: argparse.Namespace) -> None:
    """Query and display research signals for a company."""
    from finance_agent.data.watchlist import get_company_by_ticker
    from finance_agent.db import close_connection
    from finance_agent.research.signals import query_signals

    conn, _audit, _settings = _get_db_and_audit()

    try:
        company = get_company_by_ticker(conn, args.ticker.upper())
        if not company:
            print(f"Error: {args.ticker.upper()} is not on the watchlist")
            sys.exit(1)

        assert company["id"] is not None
        cid = int(company["id"])
        signals = query_signals(
            conn,
            company_id=cid,
            signal_type=args.signal_type,
            since=args.since,
            until=args.until,
            source_type=args.source,
        )

        print(f"Research Signals for {company['ticker']} ({len(signals)} total):")
        print()

        if not signals:
            print("  No signals found. Run: finance-agent research run")
            return

        for s in signals:
            date = str(s["created_at"])[:10]
            ev = "FACT" if s["evidence_type"] == "fact" else "INFERENCE"
            conf = str(s["confidence"]).upper()[:3]
            print(f"{date}  {s['signal_type']:<22}[{ev}]   {conf}   {s['summary']}")
            print(f"            Source: {s['content_type']} {s['document_title']}")
            print()
    finally:
        close_connection(conn)


def cmd_profile(args: argparse.Namespace) -> None:
    """Display unified company research profile."""
    from finance_agent.data.watchlist import get_company_by_ticker
    from finance_agent.db import close_connection
    from finance_agent.research.signals import get_signal_counts, query_signals

    conn, _audit, _settings = _get_db_and_audit()

    try:
        company = get_company_by_ticker(conn, args.ticker.upper())
        if not company:
            print(f"Error: {args.ticker.upper()} is not on the watchlist")
            sys.exit(1)

        assert company["id"] is not None
        cid = int(company["id"])
        signals = query_signals(conn, company_id=cid)
        counts = get_signal_counts(conn, cid)
        total = sum(counts.values())

        # Compute overall sentiment from sentiment signals
        sentiment_signals = [s for s in signals if s["signal_type"] == "sentiment"]
        bullish = sum(
            1 for s in sentiment_signals
            if any(w in str(s.get("summary") or "").lower() for w in ["bullish", "grew", "beat"])
        )
        bearish = sum(
            1 for s in sentiment_signals
            if any(w in str(s.get("summary") or "").lower() for w in ["bearish", "decline", "miss"])
        )
        if bullish > bearish:
            overall = "Bullish"
        elif bearish > bullish:
            overall = "Bearish"
        else:
            overall = "Neutral"

        # Source counts
        source_breakdown: dict[str, int] = {}
        for s in signals:
            st = str(s.get("source_type") or "unknown")
            source_breakdown[st] = source_breakdown.get(st, 0) + 1

        sector = company.get("sector") or "N/A"
        cik = company.get("cik") or "N/A"
        added = str(company.get("added_at") or "")[:10]

        print(f"Research Profile: {company['ticker']} ({company['name']})")
        print(f"Sector: {sector} | CIK: {cik} | On watchlist since: {added}")
        print()
        print(f"Overall Sentiment: {overall} (based on {total} signals)")
        print()

        # Latest signals (top 5)
        print("Latest Signals:")
        for s in signals[:5]:
            date = str(s["created_at"])[:10]
            print(f"  [{date}] {s['summary']} ({s['content_type']})")
        print()

        # Signal summary by type
        print("Signal Summary:")
        for stype, count in sorted(counts.items()):
            print(f"  {stype:<24}{count}")
        print()

        # Source breakdown
        print("Sources Contributing:")
        source_labels = {
            "sec_filing": "SEC Filings",
            "earnings_transcript": "Earnings Calls",
            "finnhub_data": "Finnhub Market Data",
            "podcast_episode": "Acquired Podcast",
            "article": "Stratechery",
            "holdings_13f": "13F Holdings",
        }
        for st, label in source_labels.items():
            count = source_breakdown.get(st, 0)
            print(f"  {label:<24}{count} signals")
    finally:
        close_connection(conn)


def cmd_mcp(args: argparse.Namespace) -> None:
    """Start the MCP research server."""
    from finance_agent.mcp.research_server import mcp

    if args.http:
        print("Starting MCP server in HTTP mode on 0.0.0.0:8000...")
        mcp.run(transport="http", host="0.0.0.0", port=8000)
    else:
        mcp.run()


