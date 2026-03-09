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

    # Pattern Lab commands
    pattern_parser = subparsers.add_parser(
        "pattern", help="Pattern Lab: describe, backtest, and paper trade patterns",
    )
    pattern_sub = pattern_parser.add_subparsers(dest="pattern_command")

    pat_describe = pattern_sub.add_parser(
        "describe", help="Describe a trading pattern in plain text",
    )
    pat_describe.add_argument("description", help="Plain-text pattern description")

    pat_backtest = pattern_sub.add_parser(
        "backtest", help="Backtest a pattern against historical data",
    )
    pat_backtest.add_argument("pattern_id", type=int, help="Pattern ID to backtest")
    pat_backtest.add_argument("--start", help="Start date (YYYY-MM-DD, default: 1 year ago)")
    pat_backtest.add_argument("--end", help="End date (YYYY-MM-DD, default: today)")
    pat_backtest.add_argument("--tickers", help="Comma-separated tickers to test against")
    pat_backtest.add_argument(
        "--shares", type=int, default=100,
        help="Number of shares owned (for covered calls, default: 100)",
    )
    pat_backtest.add_argument("--events", help="Manual event dates (comma-separated YYYY-MM-DD)")
    pat_backtest.add_argument("--events-file", help="File with event dates (one per line)")
    pat_backtest.add_argument("--spike-threshold", type=float, help="Override spike threshold %% (default: from pattern)")
    pat_backtest.add_argument("--volume-multiple", type=float, help="Override volume multiplier (default: from pattern)")

    pat_paper = pattern_sub.add_parser("paper-trade", help="Activate pattern for paper trading")
    pat_paper.add_argument("pattern_id", type=int, help="Pattern ID to paper trade")
    pat_paper.add_argument("--auto-approve", action="store_true", help="Skip manual approval for trades")
    pat_paper.add_argument("--tickers", help="Limit monitoring to specific tickers")
    pat_paper.add_argument("--shares", type=int, default=100, help="Number of shares owned (for covered calls, default: 100)")

    pat_list = pattern_sub.add_parser("list", help="List all patterns")
    pat_list.add_argument("--status", help="Filter by status (draft, backtested, paper_trading, retired)")

    pat_show = pattern_sub.add_parser("show", help="Show pattern details")
    pat_show.add_argument("pattern_id", type=int, help="Pattern ID")

    pat_compare = pattern_sub.add_parser("compare", help="Compare pattern performance")
    pat_compare.add_argument("pattern_ids", type=int, nargs="+", help="Pattern IDs to compare")

    pat_retire = pattern_sub.add_parser("retire", help="Retire a pattern")
    pat_retire.add_argument("pattern_id", type=int, help="Pattern ID to retire")

    pat_ab_test = pattern_sub.add_parser("ab-test", help="A/B test pattern variants with statistical significance")
    pat_ab_test.add_argument("pattern_ids", type=int, nargs="+", help="Two or more pattern IDs to compare")
    pat_ab_test.add_argument("--tickers", required=True, help="Comma-separated tickers (required)")
    pat_ab_test.add_argument("--start", help="Start date (YYYY-MM-DD, default: 1 year ago)")
    pat_ab_test.add_argument("--end", help="End date (YYYY-MM-DD, default: today)")

    pat_export = pattern_sub.add_parser("export", help="Export backtest results to markdown")
    pat_export.add_argument("pattern_id", type=int, help="Pattern ID to export results for")
    pat_export.add_argument("--format", default="markdown", dest="export_format", help="Output format (default: markdown)")
    pat_export.add_argument("--output", help="Output file path (default: auto-generated)")
    pat_export.add_argument("--backtest-id", type=int, help="Specific backtest result ID to export")

    pat_scan = pattern_sub.add_parser("scan", help="Scan all active patterns against live market data")
    pat_scan.add_argument("--watch", type=int, metavar="N", help="Repeat scan every N minutes")
    pat_scan.add_argument("--cooldown", type=int, default=24, help="Deduplication cooldown in hours (default: 24)")

    pat_alerts = pattern_sub.add_parser("alerts", help="List and manage pattern alerts")
    pat_alerts.add_argument("action", nargs="?", help="Action: ack, dismiss, acted (requires alert ID)")
    pat_alerts.add_argument("alert_id", nargs="?", type=int, help="Alert ID for ack/dismiss/acted actions")
    pat_alerts.add_argument("--status", help="Filter by status (new, acknowledged, acted_on, dismissed)")
    pat_alerts.add_argument("--pattern-id", type=int, help="Filter by pattern ID")
    pat_alerts.add_argument("--ticker", help="Filter by ticker")
    pat_alerts.add_argument("--days", type=int, default=7, help="Show last N days (default: 7)")

    pat_auto_exec = pattern_sub.add_parser("auto-execute", help="Enable/disable auto-execution for a pattern")
    pat_auto_exec.add_argument("pattern_id", type=int, help="Pattern ID")
    pat_auto_exec_group = pat_auto_exec.add_mutually_exclusive_group(required=True)
    pat_auto_exec_group.add_argument("--enable", action="store_true", help="Enable auto-execution")
    pat_auto_exec_group.add_argument("--disable", action="store_true", help="Disable auto-execution")

    pattern_sub.add_parser("dashboard", help="Show portfolio dashboard across all patterns")

    pat_perf = pattern_sub.add_parser("perf", help="Compare backtest predictions vs paper trade actuals")
    pat_perf.add_argument("pattern_id", nargs="?", type=int, help="Pattern ID (default: all patterns)")

    pat_schedule = pattern_sub.add_parser("schedule", help="Manage automated scan schedule")
    schedule_sub = pat_schedule.add_subparsers(dest="schedule_command")
    sched_install = schedule_sub.add_parser("install", help="Install recurring scan schedule")
    sched_install.add_argument("--interval", type=int, required=True, help="Scan interval in minutes")
    sched_install.add_argument("--cooldown", type=int, default=24, help="Deduplication cooldown hours (default: 24)")
    schedule_sub.add_parser("list", help="Show current schedule status")
    schedule_sub.add_parser("pause", help="Pause the scan schedule")
    schedule_sub.add_parser("resume", help="Resume a paused scan schedule")
    schedule_sub.add_parser("remove", help="Remove the scan schedule entirely")

    # Sandbox CRM commands
    sandbox_parser = subparsers.add_parser("sandbox", help="Salesforce CRM sandbox for advisor workflow training")
    sandbox_sub = sandbox_parser.add_subparsers(dest="sandbox_command")

    sandbox_sub.add_parser("setup", help="Create custom fields on Salesforce Contact object")

    sb_seed = sandbox_sub.add_parser("seed", help="Push synthetic client data to Salesforce")
    sb_seed.add_argument("--count", type=int, default=50, help="Number of clients to generate (default: 50)")
    sb_seed.add_argument("--reset", action="store_true", help="Delete existing sandbox data before seeding")

    sb_list = sandbox_sub.add_parser("list", help="List clients from Salesforce")
    sb_list.add_argument("--risk", nargs="+", help="Filter by risk tolerance(s): conservative moderate growth aggressive")
    sb_list.add_argument("--stage", nargs="+", help="Filter by life stage(s): accumulation pre-retirement retirement legacy")
    sb_list.add_argument("--min-value", type=float, help="Minimum account value")
    sb_list.add_argument("--max-value", type=float, help="Maximum account value")
    sb_list.add_argument("--search", help="Search by name or notes")
    sb_list.add_argument("--min-age", type=int, help="Minimum client age")
    sb_list.add_argument("--max-age", type=int, help="Maximum client age")
    sb_list.add_argument("--not-contacted-days", type=int, help="Clients not contacted in N days")
    sb_list.add_argument("--contacted-after", help="Last contact on or after date (YYYY-MM-DD)")
    sb_list.add_argument("--contacted-before", help="Last contact on or before date (YYYY-MM-DD)")
    sb_list.add_argument("--sort-by", choices=["account_value", "age", "last_name", "last_interaction_date"], default="account_value", help="Sort field")
    sb_list.add_argument("--sort-dir", choices=["asc", "desc"], default="desc", help="Sort direction")
    sb_list.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")

    sb_view = sandbox_sub.add_parser("view", help="View a client profile")
    sb_view.add_argument("client_id", type=str, help="Salesforce Contact ID")

    sb_add = sandbox_sub.add_parser("add", help="Add a new client to Salesforce")
    sb_add.add_argument("--first", required=True, help="First name")
    sb_add.add_argument("--last", required=True, help="Last name")
    sb_add.add_argument("--age", type=int, required=True, help="Age")
    sb_add.add_argument("--occupation", required=True, help="Occupation")
    sb_add.add_argument("--account-value", type=float, required=True, help="Account value in USD")
    sb_add.add_argument("--risk", required=True, help="Risk tolerance")
    sb_add.add_argument("--life-stage", required=True, help="Life stage")
    sb_add.add_argument("--goals", help="Investment goals")
    sb_add.add_argument("--notes", help="Notes")

    sb_edit = sandbox_sub.add_parser("edit", help="Edit a client in Salesforce")
    sb_edit.add_argument("client_id", type=str, help="Salesforce Contact ID")
    sb_edit.add_argument("--account-value", type=float, help="Account value")
    sb_edit.add_argument("--risk", help="Risk tolerance")
    sb_edit.add_argument("--life-stage", help="Life stage")
    sb_edit.add_argument("--goals", help="Investment goals")
    sb_edit.add_argument("--notes", help="Notes")

    sb_brief = sandbox_sub.add_parser("brief", help="Generate meeting prep brief")
    sb_brief.add_argument("client_id", type=str, help="Salesforce Contact ID")

    sb_commentary = sandbox_sub.add_parser("commentary", help="Generate market commentary")
    sb_commentary.add_argument("--risk", help="Target risk tolerance")
    sb_commentary.add_argument("--stage", help="Target life stage")

    # Saved lists subcommand group
    sb_lists = sandbox_sub.add_parser("lists", help="Manage Salesforce List Views")
    lists_sub = sb_lists.add_subparsers(dest="lists_command")

    sb_lists_save = lists_sub.add_parser("save", help="Save compound filters as a Salesforce List View")
    sb_lists_save.add_argument("--name", required=True, help="List View name")
    sb_lists_save.add_argument("--risk", nargs="+", help="Risk tolerance(s)")
    sb_lists_save.add_argument("--stage", nargs="+", help="Life stage(s)")
    sb_lists_save.add_argument("--min-value", type=float, help="Minimum account value")
    sb_lists_save.add_argument("--max-value", type=float, help="Maximum account value")
    sb_lists_save.add_argument("--min-age", type=int, help="Minimum client age")
    sb_lists_save.add_argument("--max-age", type=int, help="Maximum client age")
    sb_lists_save.add_argument("--not-contacted-days", type=int, help="Not contacted in N days")
    sb_lists_save.add_argument("--contacted-after", help="Contacted after date (YYYY-MM-DD)")
    sb_lists_save.add_argument("--contacted-before", help="Contacted before date (YYYY-MM-DD)")
    sb_lists_save.add_argument("--search", help="Search text")
    sb_lists_save.add_argument("--sort-by", choices=["account_value", "age", "last_name", "last_interaction_date"], default="account_value")
    sb_lists_save.add_argument("--sort-dir", choices=["asc", "desc"], default="desc")
    sb_lists_save.add_argument("--limit", type=int, default=50, help="Max results")

    lists_sub.add_parser("show", help="Show all tool-created List Views")

    sb_lists_delete = lists_sub.add_parser("delete", help="Delete a List View")
    sb_lists_delete.add_argument("name", help="List View name to delete")

    # Reports subcommand group (021-sfdc-native-lists)
    sb_reports = sandbox_sub.add_parser("reports", help="Manage Salesforce Reports")
    reports_sub = sb_reports.add_subparsers(dest="reports_command")

    sb_reports_save = reports_sub.add_parser("save", help="Save compound filters as a Salesforce Report")
    sb_reports_save.add_argument("--name", required=True, help="Report name")
    sb_reports_save.add_argument("--risk", nargs="+", help="Risk tolerance(s)")
    sb_reports_save.add_argument("--stage", nargs="+", help="Life stage(s)")
    sb_reports_save.add_argument("--min-value", type=float, help="Minimum account value")
    sb_reports_save.add_argument("--max-value", type=float, help="Maximum account value")
    sb_reports_save.add_argument("--min-age", type=int, help="Minimum client age")
    sb_reports_save.add_argument("--max-age", type=int, help="Maximum client age")
    sb_reports_save.add_argument("--not-contacted-days", type=int, help="Not contacted in N days")
    sb_reports_save.add_argument("--contacted-after", help="Contacted after date (YYYY-MM-DD)")
    sb_reports_save.add_argument("--contacted-before", help="Contacted before date (YYYY-MM-DD)")
    sb_reports_save.add_argument("--search", help="Search text")
    sb_reports_save.add_argument("--sort-by", choices=["account_value", "age", "last_name", "last_interaction_date"], default="account_value")
    sb_reports_save.add_argument("--sort-dir", choices=["asc", "desc"], default="desc")
    sb_reports_save.add_argument("--limit", type=int, default=50, help="Max results")

    reports_sub.add_parser("show", help="Show all tool-created Reports")

    sb_reports_delete = reports_sub.add_parser("delete", help="Delete a Report")
    sb_reports_delete.add_argument("name", help="Report name to delete")

    # Tasks subcommand group (022-sfdc-task-logging)
    sb_tasks = sandbox_sub.add_parser("tasks", help="Manage follow-up tasks")
    tasks_sub = sb_tasks.add_subparsers(dest="tasks_command")

    sb_tasks_create = tasks_sub.add_parser("create", help="Create a follow-up task")
    sb_tasks_create.add_argument("--client", required=True, help="Client name (fuzzy matched)")
    sb_tasks_create.add_argument("--subject", required=True, help="Task subject")
    sb_tasks_create.add_argument("--due", help="Due date (YYYY-MM-DD, default: 7 days from today)")
    sb_tasks_create.add_argument("--priority", choices=["High", "Normal", "Low"], default="Normal", help="Task priority")

    sb_tasks_show = tasks_sub.add_parser("show", help="Show open tasks")
    sb_tasks_show.add_argument("--overdue", action="store_true", help="Show only overdue tasks")
    sb_tasks_show.add_argument("--client", help="Filter by client name")
    sb_tasks_show.add_argument("--summary", action="store_true", help="Show summary counts only")

    sb_tasks_complete = tasks_sub.add_parser("complete", help="Mark a task as completed")
    sb_tasks_complete.add_argument("subject", help="Task subject (fuzzy matched)")

    # Activity logging (022-sfdc-task-logging)
    sb_log = sandbox_sub.add_parser("log", help="Log a completed activity")
    sb_log.add_argument("--client", required=True, help="Client name (fuzzy matched)")
    sb_log.add_argument("--subject", required=True, help="Activity description")
    sb_log.add_argument("--type", required=True, choices=["call", "meeting", "email", "other"], dest="activity_type", help="Activity type")
    sb_log.add_argument("--date", dest="activity_date", help="Activity date (YYYY-MM-DD, default: today)")

    # Outreach queue (022-sfdc-task-logging)
    sb_outreach = sandbox_sub.add_parser("outreach", help="Generate outreach queue")
    sb_outreach.add_argument("--days", type=int, required=True, help="Min days since last contact (0 = all)")
    sb_outreach.add_argument("--min-value", type=float, default=0, help="Min account value")
    sb_outreach.add_argument("--create-tasks", action="store_true", help="Auto-create follow-up tasks")

    # Natural language query
    sb_ask = sandbox_sub.add_parser("ask", help="Query clients in plain English")
    sb_ask.add_argument("query", help="Natural language query (e.g., 'top 50 clients under 50')")
    sb_ask.add_argument("--yes", action="store_true", help="Skip confirmation for low-confidence interpretations")
    sb_ask.add_argument("--save-as", dest="save_as", help="Save NL-interpreted filters as a Salesforce List View")

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
    elif args.command == "pattern":
        cmd_pattern(args)
    elif args.command == "sandbox":
        cmd_sandbox(args)
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


def cmd_pattern(args: argparse.Namespace) -> None:
    """Handle pattern subcommands."""
    from finance_agent.db import close_connection

    conn, audit, settings = _get_db_and_audit()

    try:
        if args.pattern_command == "describe":
            _pattern_describe(conn, audit, settings, args.description)
        elif args.pattern_command == "backtest":
            _pattern_backtest(conn, audit, settings, args)
        elif args.pattern_command == "paper-trade":
            _pattern_paper_trade(conn, audit, settings, args)
        elif args.pattern_command == "list":
            _pattern_list(conn, args)
        elif args.pattern_command == "show":
            _pattern_show(conn, args.pattern_id)
        elif args.pattern_command == "compare":
            _pattern_compare(conn, args.pattern_ids)
        elif args.pattern_command == "retire":
            _pattern_retire(conn, audit, args.pattern_id)
        elif args.pattern_command == "ab-test":
            _pattern_ab_test(conn, audit, settings, args)
        elif args.pattern_command == "export":
            _pattern_export(conn, args)
        elif args.pattern_command == "scan":
            _pattern_scan(conn, audit, settings, args)
        elif args.pattern_command == "alerts":
            _pattern_alerts(conn, args)
        elif args.pattern_command == "auto-execute":
            _pattern_auto_execute(conn, audit, args)
        elif args.pattern_command == "dashboard":
            _pattern_dashboard(conn)
        elif args.pattern_command == "perf":
            _pattern_perf(conn, args)
        elif args.pattern_command == "schedule":
            _pattern_schedule(args)
        else:
            print("Usage: finance-agent pattern {describe|backtest|paper-trade|list|show|compare|retire|ab-test|export|scan|alerts|auto-execute|dashboard|perf|schedule}")
            sys.exit(1)
    finally:
        close_connection(conn)


def _pattern_describe(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    settings: Settings,
    description: str,
) -> None:
    """Parse a plain-text pattern description and create a draft pattern."""
    from finance_agent.patterns.parser import parse_pattern_description
    from finance_agent.patterns.storage import create_pattern

    if not settings.anthropic_available:
        print("Error: ANTHROPIC_API_KEY is required for pattern description parsing")
        sys.exit(1)

    print(f"Parsing pattern description...")
    print()

    result = parse_pattern_description(description, settings.anthropic_api_key)

    if not result.is_complete:
        print("The description needs more detail. Please clarify:")
        print()
        for q in result.clarifying_questions:
            print(f"  - {q.question}")
            if q.suggestions:
                print(f"    Suggestions: {', '.join(q.suggestions)}")
            print()
        return

    rule_set = result.rule_set
    assert rule_set is not None

    is_covered_call = rule_set.action.action_type.value == "sell_call"

    print(f"Pattern: {result.suggested_name}")
    print(f"Status: draft")
    print()

    if is_covered_call:
        # Covered call display format
        print("Trigger:")
        print(f"  Type: {rule_set.trigger_type}")
        for tc in rule_set.trigger_conditions:
            print(f"  Condition: {tc.description}")
        print()
        print("Call Sale:")
        print(f"  {rule_set.action.description}")
        print(f"  Strike: {rule_set.action.strike_strategy.value}")
        print(f"  Expiration: {rule_set.action.expiration_days} days")
        print()
        print("Exit Criteria:")
        print(f"  {rule_set.exit_criteria.description}")
        print(f"  Close at {rule_set.exit_criteria.profit_target_pct}% premium profit")
        roll_dte = rule_set.action.expiration_days - (rule_set.exit_criteria.max_hold_days or rule_set.action.expiration_days)
        if roll_dte > 0:
            print(f"  Roll at {roll_dte} DTE")
        print(f"  Accept assignment if ITM at expiration")
        print()
        if rule_set.action.action_type.value == "sell_call":
            print("  Note: This is a COVERED CALL strategy (requires owning underlying shares)")
            print()
    else:
        # Standard pattern display
        print("Trigger:")
        print(f"  Type: {rule_set.trigger_type}")
        for tc in rule_set.trigger_conditions:
            print(f"  Condition: {tc.description}")
        if rule_set.sector_filter:
            print(f"  Sector: {rule_set.sector_filter}")
        print()
        print("Entry Signal:")
        print(f"  {rule_set.entry_signal.description}")
        print(f"  Window: {rule_set.entry_signal.window_days} trading days")
        print()
        print("Action:")
        print(f"  {rule_set.action.description}")
        if "call" in rule_set.action.action_type.value or "put" in rule_set.action.action_type.value:
            print(f"  Strike: {rule_set.action.strike_strategy.value}")
            print(f"  Expiration: {rule_set.action.expiration_days} days")
        print()
        print("Exit Criteria:")
        print(f"  {rule_set.exit_criteria.description}")
        print(f"  Profit target: {rule_set.exit_criteria.profit_target_pct}%")
        print(f"  Stop loss: {rule_set.exit_criteria.stop_loss_pct}%")
        if rule_set.exit_criteria.max_hold_days:
            print(f"  Max hold: {rule_set.exit_criteria.max_hold_days} days")
        print()

    if result.defaults_applied:
        print("Defaults applied:")
        for d in result.defaults_applied:
            print(f"  - {d}")
        print()

    # Ask for confirmation
    try:
        choice = input("Confirm this pattern? [Y/cancel]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    if choice not in ("y", "yes", ""):
        print("Cancelled.")
        return

    rule_set_json = rule_set.model_dump_json()
    pattern_id = create_pattern(conn, result.suggested_name, description, rule_set_json)
    print(f"\nPattern saved as #{pattern_id} (status: draft)")

    event_name = "covered_call_described" if is_covered_call else "pattern_created"
    audit.log(event_name, "pattern_lab", {
        "pattern_id": pattern_id,
        "name": result.suggested_name,
        "is_covered_call": is_covered_call,
    })


def _pattern_backtest(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    settings: Settings,
    args: argparse.Namespace,
) -> None:
    """Run a backtest for a pattern."""
    from datetime import date, timedelta

    from finance_agent.patterns.market_data import fetch_and_cache_bars
    from finance_agent.patterns.models import RuleSet
    from finance_agent.patterns.storage import get_pattern, save_backtest_result

    pattern = get_pattern(conn, args.pattern_id)
    if not pattern:
        print(f"Error: Pattern #{args.pattern_id} not found")
        sys.exit(1)

    # Parse dates
    end_date = args.end or date.today().isoformat()
    start_date = args.start or (date.today() - timedelta(days=365)).isoformat()

    # Parse tickers
    tickers = args.tickers.split(",") if args.tickers else None
    if not tickers:
        # Use watchlist tickers as default
        from finance_agent.data.watchlist import list_companies
        companies = list_companies(conn)
        tickers = [c["ticker"] for c in companies]
        if not tickers:
            print("Error: No tickers specified and watchlist is empty. Use --tickers or add to watchlist.")
            sys.exit(1)

    rule_set = RuleSet.model_validate_json(pattern["rule_set_json"])

    # Validate mutually exclusive event flags
    if getattr(args, 'events', None) and getattr(args, 'events_file', None):
        print("Error: --events and --events-file are mutually exclusive. Use one or the other.")
        sys.exit(1)

    # Detect covered call → use specialized backtest
    is_covered_call = rule_set.action.action_type.value == "sell_call"

    print(f"Backtesting pattern #{args.pattern_id}: {pattern['name']}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Tickers: {', '.join(tickers)}")
    if is_covered_call:
        print(f"Shares: {args.shares}")
    print()

    # Fetch price data for all tickers
    print("Fetching market data...")
    all_bars: dict[str, list[dict]] = {}
    for ticker in tickers:
        bars = fetch_and_cache_bars(
            conn, ticker, start_date, end_date, "day",
            settings.active_api_key, settings.active_secret_key,
        )
        if bars:
            all_bars[ticker] = bars
            print(f"  {ticker}: {len(bars)} bars")
        else:
            print(f"  {ticker}: no data available")

    if not all_bars:
        print("\nError: No price data available for any ticker")
        sys.exit(1)

    # Route to appropriate backtest engine
    is_qualitative = rule_set.trigger_type.value == "qualitative"

    if is_covered_call:
        _run_covered_call_backtest(conn, audit, args, rule_set, all_bars, start_date, end_date)
    elif is_qualitative:
        _run_news_dip_backtest(conn, audit, args, rule_set, all_bars, start_date, end_date)
    else:
        _run_standard_backtest(conn, audit, args, rule_set, all_bars, start_date, end_date)


def _run_standard_backtest(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    args: argparse.Namespace,
    rule_set: RuleSet,
    all_bars: dict[str, list[dict]],
    start_date: str,
    end_date: str,
) -> None:
    """Run standard pattern backtest (non-covered-call)."""
    from finance_agent.patterns.backtest import run_backtest
    from finance_agent.patterns.storage import save_backtest_result

    print("\nRunning backtest...")
    report = run_backtest(args.pattern_id, rule_set, all_bars, start_date, end_date, conn=conn)

    # Save results
    backtest_id = save_backtest_result(conn, report)

    # Display results
    print(f"\nBacktest Results (saved as #{backtest_id}):")
    print(f"  Triggers: {report.trigger_count}")
    print(f"  Trades: {report.trade_count}")
    if report.trade_count > 0:
        print(f"  Win rate: {report.win_count}/{report.trade_count} ({report.win_count/report.trade_count*100:.1f}%)")
        print(f"  Avg return: {report.avg_return_pct:.2f}%")
        print(f"  Total return: {report.total_return_pct:.2f}%")
        print(f"  Max drawdown: {report.max_drawdown_pct:.2f}%")
        if report.sharpe_ratio is not None:
            print(f"  Sharpe ratio: {report.sharpe_ratio:.2f}")
    else:
        print("  No trades triggered")

    if report.sample_size_warning:
        print(f"\n  WARNING: Only {report.trigger_count} triggers — sample too small for statistical significance (need 30+)")

    if report.regimes:
        print(f"\nRegime Analysis:")
        for regime in report.regimes:
            print(f"  {regime.start_date} to {regime.end_date}: {regime.label}")
            print(f"    Win rate: {regime.win_rate*100:.1f}%, Avg return: {regime.avg_return_pct:.2f}%")
            if regime.explanation:
                print(f"    Possible explanation: {regime.explanation}")

    audit.log("backtest_run", "pattern_lab", {
        "pattern_id": args.pattern_id,
        "backtest_id": backtest_id,
        "trade_count": report.trade_count,
        "win_rate": report.win_count / report.trade_count if report.trade_count > 0 else 0,
    })


def _build_event_config(
    args: argparse.Namespace,
    rule_set: RuleSet,
) -> tuple[EventDetectionConfig, str]:
    """Build EventDetectionConfig from CLI args with fallbacks to pattern defaults.

    Returns:
        Tuple of (EventDetectionConfig, events_source_description)
    """
    from finance_agent.patterns.event_detection import parse_events_file, parse_manual_events
    from finance_agent.patterns.models import EventDetectionConfig

    spike_threshold = getattr(args, "spike_threshold", None)
    volume_multiple = getattr(args, "volume_multiple", None)

    for tc in rule_set.trigger_conditions:
        if tc.field == "price_change_pct" and spike_threshold is None:
            spike_threshold = float(tc.value)
        if tc.field == "volume_spike" and volume_multiple is None:
            volume_multiple = float(tc.value)

    manual_events = None
    events_source = "price-action proxy"

    events_str = getattr(args, "events", None)
    events_file = getattr(args, "events_file", None)

    if events_str:
        try:
            manual_events = parse_manual_events(events_str)
            events_source = "manual (CLI)"
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif events_file:
        try:
            manual_events = parse_events_file(events_file)
            events_source = f"manual (file: {events_file})"
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}")
            sys.exit(1)

    event_config = EventDetectionConfig(
        spike_threshold_pct=spike_threshold or 5.0,
        volume_multiple_min=volume_multiple or 1.5,
        entry_window_days=rule_set.entry_signal.window_days,
        manual_events=manual_events,
    )
    return event_config, events_source


def _run_news_dip_backtest(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    args: argparse.Namespace,
    rule_set: RuleSet,
    all_bars: dict[str, list[dict]],
    start_date: str,
    end_date: str,
) -> None:
    """Run news dip backtest with event detection and formatted report."""
    from finance_agent.patterns.storage import save_backtest_result

    event_config, events_source = _build_event_config(args, rule_set)

    tickers = list(all_bars.keys())
    is_multi_ticker = len(tickers) > 1

    if is_multi_ticker:
        _run_multi_ticker_news_dip(
            conn, audit, args, rule_set, all_bars, tickers,
            start_date, end_date, event_config, events_source,
        )
    else:
        _run_single_ticker_news_dip(
            conn, audit, args, rule_set, all_bars, tickers,
            start_date, end_date, event_config, events_source,
        )


def _run_single_ticker_news_dip(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    args: argparse.Namespace,
    rule_set: RuleSet,
    all_bars: dict[str, list[dict]],
    tickers: list[str],
    start_date: str,
    end_date: str,
    event_config,
    events_source: str,
) -> None:
    """Run single-ticker news dip backtest (original format)."""
    from finance_agent.patterns.backtest import run_news_dip_backtest
    from finance_agent.patterns.storage import save_backtest_result

    for ticker, bars in all_bars.items():
        print(f"\nRunning news dip backtest for {ticker}...")
        report, no_entry_events = run_news_dip_backtest(
            pattern_id=args.pattern_id,
            rule_set=rule_set,
            bars=bars,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            event_config=event_config,
            conn=conn,
        )

        backtest_id = save_backtest_result(conn, report)

        no_entry_count = len(no_entry_events)
        print()
        print("═" * 51)
        print(f"  NEWS DIP BACKTEST: {args.pattern_id} – {ticker}")
        print(f"  {start_date} → {end_date}")
        print("═" * 51)
        print()
        print(f"  Events Detected:  {report.trigger_count}  (source: {events_source})")
        print(f"  Spike Threshold:  {event_config.spike_threshold_pct}%  |  Volume Filter: {event_config.volume_multiple_min}x avg")
        if no_entry_count > 0:
            print(f"  Trades Entered:   {report.trade_count}  ({no_entry_count} events had no qualifying dip)")
        else:
            print(f"  Trades Entered:   {report.trade_count}")

        if report.trade_count > 0:
            win_rate = report.win_count / report.trade_count * 100
            loss_count = report.trade_count - report.win_count
            sign = "+" if report.avg_return_pct >= 0 else ""
            total_sign = "+" if report.total_return_pct >= 0 else ""
            print()
            print("  ─── AGGREGATE ──────────────────────────────────")
            print(f"  Win Rate:     {win_rate:.1f}%  ({report.win_count}W / {loss_count}L)")
            print(f"  Avg Return:   {sign}{report.avg_return_pct:.1f}%")
            print(f"  Total Return: {total_sign}{report.total_return_pct:.1f}%")
            print(f"  Max Drawdown: -{report.max_drawdown_pct:.1f}%")
            if report.sharpe_ratio is not None:
                print(f"  Sharpe Ratio: {report.sharpe_ratio:.2f}")

            if report.regimes:
                print()
                print("  ─── REGIME ANALYSIS ───────────────────────────")
                if report.trade_count < 10:
                    print("  ⚠ Regime detection requires 10+ trades")
                print(f"  {'Period':<22}{'Label':<12}{'Trades':<9}{'Win Rate':<11}Avg Return")
                for regime in report.regimes:
                    period = f"{regime.start_date[:7]} – {regime.end_date[:7]}"
                    sign = "+" if regime.avg_return_pct >= 0 else ""
                    print(f"  {period:<22}{regime.label:<12}{regime.trade_count:<9}{regime.win_rate*100:.1f}%{'':>5}{sign}{regime.avg_return_pct:.1f}%")
            elif report.trade_count >= 10:
                print()
                print("  ─── REGIME ANALYSIS ───────────────────────────")
                print("  No regime shifts detected.")

            print()
            print("  ─── TRADE LOG ──────────────────────────────────")
            print(f"  {'#':<4}{'Trigger':<13}{'Entry':<13}{'Exit':<13}{'Return':<9}Action")
            for i, trade in enumerate(report.trades, 1):
                ret_sign = "+" if trade.return_pct >= 0 else ""
                action_str = trade.action_type
                if trade.option_details:
                    strike = trade.option_details.get("strike_strategy", "")
                    exp = trade.option_details.get("expiration_days", "")
                    pricing = trade.option_details.get("pricing", "")
                    symbol = trade.option_details.get("option_symbol", "")
                    if symbol and pricing == "real":
                        action_str = f"{symbol} (real)"
                    elif pricing == "estimated":
                        action_str = f"{trade.action_type} ({strike}, {exp}d) [est]"
                    else:
                        action_str = f"{trade.action_type} ({strike}, {exp}d)"
                print(f"  {i:<4}{trade.trigger_date:<13}{trade.entry_date:<13}{trade.exit_date:<13}{ret_sign}{trade.return_pct:.1f}%{'':>3}{action_str}")
        else:
            if report.trigger_count == 0:
                print()
                print("  No qualifying events detected. Try: lower --spike-threshold,")
                print("  wider date range, or provide --events manually.")
            else:
                print()
                print("  Events detected but no trades entered (no qualifying dips).")

        if no_entry_events:
            print()
            print("  ─── NO-ENTRY EVENTS ────────────────────────────")
            print(f"  {'Date':<13}{'Spike':<9}{'Volume':<9}Reason")
            for ne in no_entry_events:
                print(f"  {ne['date']:<13}+{ne['spike_pct']:.1f}%{'':>3}{ne['volume_multiple']:.1f}x{'':>4}{ne['reason']}")

        if report.sample_size_warning and report.trade_count > 0:
            print()
            print(f"  Warning: Only {report.trade_count} trades — results may not be statistically meaningful.")

        if report.trade_count > 0 and report.trade_count < 10 and report.regimes:
            print(f"  Warning: Fewer than 10 trades — regime analysis may be unreliable.")

        print("═" * 51)

        audit.log("news_dip_backtested", "pattern_lab", {
            "pattern_id": args.pattern_id,
            "backtest_id": backtest_id,
            "ticker": ticker,
            "events_detected": report.trigger_count,
            "trades_entered": report.trade_count,
            "events_source": events_source,
        })


def _run_multi_ticker_news_dip(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    args: argparse.Namespace,
    rule_set: RuleSet,
    all_bars: dict[str, list[dict]],
    tickers: list[str],
    start_date: str,
    end_date: str,
    event_config,
    events_source: str,
) -> None:
    """Run multi-ticker news dip backtest with aggregated report."""
    from finance_agent.patterns.backtest import run_multi_ticker_news_dip_backtest
    from finance_agent.patterns.storage import save_backtest_result

    print("\nRunning multi-ticker news dip backtest...")
    agg_report = run_multi_ticker_news_dip_backtest(
        pattern_id=args.pattern_id,
        rule_set=rule_set,
        all_bars=all_bars,
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        event_config=event_config,
        conn=conn,
    )

    report = agg_report.combined_report
    backtest_id = save_backtest_result(conn, report)

    tickers_str = ",".join(agg_report.tickers)
    print()
    print("═" * 51)
    print(f"  NEWS DIP BACKTEST: Pattern #{args.pattern_id} -- {tickers_str}")
    print(f"  {start_date} -> {end_date}")
    print("═" * 51)

    # Per-ticker breakdown
    print()
    print("  --- PER-TICKER BREAKDOWN ----------------------")
    print(f"  {'Ticker':<8}{'Events':<8}{'Trades':<8}{'Win Rate':<10}Avg Return")
    for tb in agg_report.ticker_breakdowns:
        wr_str = f"{tb.win_rate * 100:.1f}%" if tb.trades_entered > 0 else "—"
        ar_sign = "+" if tb.avg_return_pct >= 0 else ""
        ar_str = f"{ar_sign}{tb.avg_return_pct:.1f}%" if tb.trades_entered > 0 else "—"
        print(f"  {tb.ticker:<8}{tb.events_detected:<8}{tb.trades_entered:<8}{wr_str:<10}{ar_str}")

    # Combined aggregate
    print()
    print("  --- COMBINED AGGREGATE ------------------------")
    print(f"  Total Events:     {report.trigger_count}")
    print(f"  Total Trades:     {report.trade_count}")
    if report.trade_count > 0:
        win_rate = report.win_count / report.trade_count * 100
        sign = "+" if report.avg_return_pct >= 0 else ""
        total_sign = "+" if report.total_return_pct >= 0 else ""
        print(f"  Win Rate:         {win_rate:.1f}% ({report.win_count}/{report.trade_count})")
        print(f"  Avg Return:       {sign}{report.avg_return_pct:.1f}%")
        print(f"  Total Return:     {total_sign}{report.total_return_pct:.1f}%")
        print(f"  Max Drawdown:     -{report.max_drawdown_pct:.1f}%")
        if report.sharpe_ratio is not None:
            print(f"  Sharpe Ratio:     {report.sharpe_ratio:.2f}")

        # Regime analysis
        if report.regimes:
            print()
            print("  --- REGIME ANALYSIS ---------------------------")
            for regime in report.regimes:
                period = f"{regime.start_date[:7]} to {regime.end_date[:7]}"
                sign = "+" if regime.avg_return_pct >= 0 else ""
                strength = regime.label.capitalize()
                print(f"  {period}: {strength} (win rate {regime.win_rate*100:.1f}%, avg {sign}{regime.avg_return_pct:.1f}%, {regime.trade_count} trades)")
    else:
        print()
        print("  No qualifying events detected across any ticker.")
        print("  Consider lowering thresholds or widening the date range.")

    # No-entry events with ticker column
    if agg_report.no_entry_events:
        print()
        print("  --- NO-ENTRY EVENTS ---------------------------")
        for ne in agg_report.no_entry_events:
            ticker_name = ne.get("ticker", "")
            print(f"  {ticker_name:<6}{ne['date']}  {ne['reason']}")

    # Sample size warning
    if report.trade_count > 0 and report.sample_size_warning:
        print()
        print(f"  ! Sample size warning: {report.trade_count} trades may be insufficient")
        print("    for reliable statistical conclusions.")

    print("═" * 51)

    audit.log("multi_ticker_backtested", "pattern_lab", {
        "pattern_id": args.pattern_id,
        "backtest_id": backtest_id,
        "tickers": tickers,
        "events_detected": report.trigger_count,
        "trades_entered": report.trade_count,
        "events_source": events_source,
    })


def _run_covered_call_backtest(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    args: argparse.Namespace,
    rule_set: RuleSet,
    all_bars: dict[str, list[dict]],
    start_date: str,
    end_date: str,
) -> None:
    """Run covered call backtest with monthly income report."""
    from finance_agent.patterns.backtest import run_covered_call_backtest
    from finance_agent.patterns.storage import save_backtest_result, save_covered_call_cycles

    from finance_agent.patterns.models import BacktestReport

    # Covered call backtests run per-ticker
    for ticker, bars in all_bars.items():
        print(f"\nRunning covered call backtest for {ticker}...")
        report = run_covered_call_backtest(
            pattern_id=args.pattern_id,
            rule_set=rule_set,
            bars=bars,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            shares=args.shares,
            conn=conn,
        )

        # Save as standard backtest result for pattern status tracking
        bt_report = BacktestReport(
            pattern_id=args.pattern_id,
            date_range_start=start_date,
            date_range_end=end_date,
            trigger_count=report.cycle_count,
            trade_count=report.cycle_count,
            win_count=report.cycle_count - report.assignment_count,
            total_return_pct=report.covered_call_return_pct,
            avg_return_pct=report.covered_call_return_pct / report.cycle_count if report.cycle_count > 0 else 0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=None,
            sample_size_warning=report.sample_size_warning,
        )
        backtest_id = save_backtest_result(conn, bt_report)

        # Save covered call cycles
        if report.cycles:
            save_covered_call_cycles(conn, report.cycles, args.pattern_id, backtest_id)

        # Display covered call report
        print(f"\nBacktest Results (saved as #{backtest_id}):")
        print(f"  Period: {start_date} to {end_date}")
        print(f"  Ticker: {ticker}")
        print(f"  Shares: {args.shares}")
        print()
        print(f"  Monthly Cycles: {report.cycle_count}")
        if report.cycle_count > 0:
            avg_per_share = report.avg_premium_per_cycle / args.shares if args.shares > 0 else 0
            print(f"  Avg Premium/Month: ${report.avg_premium_per_cycle:,.2f} (${avg_per_share:.2f}/share)")
        print(f"  Total Premium Collected: ${report.total_premium_collected:,.2f}")
        print(f"  Annualized Income Yield: {report.annualized_income_yield_pct:.1f}%")
        print()
        print(f"  Assignment Events: {report.assignment_count} of {report.cycle_count} cycles ({report.assignment_frequency_pct:.1f}%)")
        print(f"  Cycles Closed Early (profit target): {report.closed_early_count}")
        print(f"  Cycles Rolled: {report.rolled_count}")
        print(f"  Cycles Expired Worthless: {report.expired_worthless_count}")
        print()
        print(f"  Buy-and-Hold Return: {'+' if report.buy_and_hold_return_pct >= 0 else ''}{report.buy_and_hold_return_pct:.1f}%")
        print(f"  Covered Call Return: {'+' if report.covered_call_return_pct >= 0 else ''}{report.covered_call_return_pct:.1f}% (stock gain + premium - capped upside)")
        print(f"  Capped Upside Cost: -${report.capped_upside_cost:,.2f} (forfeited gains from assignment)")

        # Month-by-month breakdown
        if report.cycles:
            print()
            print("  Month-by-Month:")
            for cycle in report.cycles:
                stock_chg = ""
                if cycle.stock_price_at_exit and cycle.stock_entry_price:
                    chg = ((cycle.stock_price_at_exit - cycle.stock_entry_price) / cycle.stock_entry_price) * 100
                    stock_chg = f"Stock: {'+' if chg >= 0 else ''}{chg:.1f}%"
                outcome = cycle.outcome or "open"
                pricing_tag = ""
                if getattr(cycle, "pricing", None) == "real":
                    symbol = getattr(cycle, "option_symbol", "") or ""
                    pricing_tag = f" | {symbol} (real)"
                elif getattr(cycle, "pricing", None) == "estimated":
                    pricing_tag = " | [est]"
                print(f"    {cycle.cycle_start_date}  | Premium: ${cycle.call_premium:,.2f} | {stock_chg} | Outcome: {outcome}{pricing_tag}")

        if report.sample_size_warning:
            print(f"\n  WARNING: Only {report.cycle_count} cycles — fewer than {6} needed for meaningful income estimation")

        print()
        print("  WARNING: Premium estimates use historical volatility approximation (not actual option prices)")

        audit.log("covered_call_backtested", "pattern_lab", {
            "pattern_id": args.pattern_id,
            "backtest_id": backtest_id,
            "ticker": ticker,
            "cycle_count": report.cycle_count,
            "total_premium": report.total_premium_collected,
            "annualized_yield": report.annualized_income_yield_pct,
        })


def _pattern_paper_trade(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    settings: Settings,
    args: argparse.Namespace,
) -> None:
    """Activate a pattern for paper trading."""
    from finance_agent.patterns.executor import CoveredCallMonitor, NewsPatternMonitor, PatternMonitor
    from finance_agent.patterns.models import RuleSet
    from finance_agent.patterns.storage import get_pattern, update_pattern_status

    pattern = get_pattern(conn, args.pattern_id)
    if not pattern:
        print(f"Error: Pattern #{args.pattern_id} not found")
        sys.exit(1)

    if pattern["status"] not in ("backtested", "paper_trading"):
        print(f"Error: Pattern must be backtested before paper trading (current status: {pattern['status']})")
        sys.exit(1)

    tickers = args.tickers.split(",") if args.tickers else None
    rule_set = RuleSet.model_validate_json(pattern["rule_set_json"])
    is_covered_call = rule_set.action.action_type.value == "sell_call"

    # Block --auto-approve for qualitative patterns (safety requirement)
    is_qualitative = rule_set.trigger_type.value == "qualitative"
    if is_qualitative and args.auto_approve:
        print("Error: --auto-approve is not allowed for qualitative patterns (safety requirement).")
        print("Qualitative triggers require human confirmation.")
        return

    update_pattern_status(conn, args.pattern_id, "paper_trading")

    print(f"Activating paper trading for pattern #{args.pattern_id}: {pattern['name']}")
    if is_covered_call:
        print(f"Type: Covered Call (shares: {args.shares})")
    if args.auto_approve:
        print("Auto-approve: ON (trades will execute without confirmation)")
    else:
        print("Auto-approve: OFF (you'll be asked to approve each trade)")
    if tickers:
        print(f"Monitoring tickers: {', '.join(tickers)}")
    print()
    print("Monitoring for triggers... (Ctrl+C to stop)")

    audit.log("paper_trade_started", "pattern_lab", {
        "pattern_id": args.pattern_id,
        "auto_approve": args.auto_approve,
        "is_covered_call": is_covered_call,
    })

    if is_covered_call:
        shares = getattr(args, "shares", 100)
        monitor = CoveredCallMonitor(
            conn, audit, settings, args.pattern_id, tickers, args.auto_approve, shares=shares,
        )
    elif is_qualitative:
        monitor = NewsPatternMonitor(conn, audit, settings, args.pattern_id, tickers, auto_approve=False)
    else:
        monitor = PatternMonitor(conn, audit, settings, args.pattern_id, tickers, args.auto_approve)

    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\nStopped monitoring.")


def _pattern_list(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """List all patterns."""
    from finance_agent.patterns.storage import get_backtest_results, get_paper_trade_summary, list_patterns

    patterns = list_patterns(conn, status=args.status)

    if not patterns:
        print("No patterns found. Create one with: finance-agent pattern describe \"<description>\"")
        return

    print(f"Patterns ({len(patterns)}):")
    print()
    print(f"  {'ID':<5}{'Name':<30}{'Status':<15}{'Win Rate':<12}{'P&L':<10}")
    print(f"  {'─'*5}{'─'*30}{'─'*15}{'─'*12}{'─'*10}")

    for p in patterns:
        win_rate = ""
        pnl = ""

        # Get latest backtest win rate
        backtests = get_backtest_results(conn, p["id"])
        if backtests:
            latest = backtests[0]
            if latest["trade_count"] > 0:
                wr = latest["win_count"] / latest["trade_count"] * 100
                win_rate = f"{wr:.0f}%"

        # Get paper trade P&L
        if p["status"] == "paper_trading":
            summary = get_paper_trade_summary(conn, p["id"])
            if summary["total_trades"] > 0:
                pnl = f"${summary['total_pnl']:.2f}"

        print(f"  {p['id']:<5}{p['name']:<30}{p['status']:<15}{win_rate:<12}{pnl:<10}")


def _pattern_show(conn: sqlite3.Connection, pattern_id: int) -> None:
    """Show detailed pattern information."""
    import json

    from finance_agent.patterns.storage import get_backtest_results, get_paper_trades, get_pattern

    pattern = get_pattern(conn, pattern_id)
    if not pattern:
        print(f"Error: Pattern #{pattern_id} not found")
        sys.exit(1)

    rules = json.loads(pattern["rule_set_json"])

    print(f"Pattern #{pattern['id']}: {pattern['name']}")
    print(f"Status: {pattern['status']}")
    print(f"Created: {pattern['created_at'][:10]}")
    print()
    print(f"Description: {pattern['description']}")
    print()
    print("Rules:")
    print(f"  Trigger type: {rules.get('trigger_type', 'N/A')}")
    for tc in rules.get("trigger_conditions", []):
        print(f"  Trigger: {tc.get('description', tc)}")
    entry = rules.get("entry_signal", {})
    print(f"  Entry: {entry.get('description', 'N/A')}")
    action = rules.get("action", {})
    print(f"  Action: {action.get('description', 'N/A')}")
    exit_c = rules.get("exit_criteria", {})
    print(f"  Exit: {exit_c.get('description', 'N/A')}")

    # Backtest results
    backtests = get_backtest_results(conn, pattern_id)
    if backtests:
        print(f"\nBacktest Results ({len(backtests)}):")
        for bt in backtests:
            wr = bt["win_count"] / bt["trade_count"] * 100 if bt["trade_count"] > 0 else 0
            print(f"  [{bt['created_at'][:10]}] {bt['date_range_start']} to {bt['date_range_end']}: "
                  f"{bt['trade_count']} trades, {wr:.0f}% win rate, {bt['avg_return_pct']:.2f}% avg return")

    # Paper trades
    trades = get_paper_trades(conn, pattern_id)
    if trades:
        print(f"\nPaper Trades ({len(trades)}):")
        for t in trades:
            pnl_str = f"${t['pnl']:.2f}" if t["pnl"] is not None else "open"
            print(f"  [{t['proposed_at'][:10]}] {t['ticker']} {t['direction']} {t['quantity']}x "
                  f"({t['status']}) P&L: {pnl_str}")


def _pattern_compare(conn: sqlite3.Connection, pattern_ids: list[int]) -> None:
    """Compare performance across patterns."""
    import json

    from finance_agent.patterns.storage import (
        get_backtest_results,
        get_covered_call_summary,
        get_pattern,
    )

    patterns = []
    for pid in pattern_ids:
        p = get_pattern(conn, pid)
        if not p:
            print(f"Warning: Pattern #{pid} not found, skipping")
            continue
        backtests = get_backtest_results(conn, pid)
        patterns.append((p, backtests[0] if backtests else None))

    if len(patterns) < 2:
        print("Need at least 2 valid patterns to compare")
        sys.exit(1)

    # Detect if all patterns are covered calls
    all_covered_calls = all(
        json.loads(p["rule_set_json"]).get("action", {}).get("action_type") == "sell_call"
        for p, _ in patterns
    )

    # Detect if all patterns are news dip (qualitative + buy_call)
    all_news_dip = all(
        json.loads(p["rule_set_json"]).get("trigger_type") == "qualitative"
        and json.loads(p["rule_set_json"]).get("action", {}).get("action_type") == "buy_call"
        for p, _ in patterns
    )

    print("Pattern Comparison:")
    print()
    print(f"  {'Metric':<22}", end="")
    for p, _ in patterns:
        print(f"  {p['name'][:18]:<20}", end="")
    print()
    print(f"  {'─'*22}", end="")
    for _ in patterns:
        print(f"  {'─'*20}", end="")
    print()

    if all_covered_calls:
        # Covered call-specific comparison
        summaries = []
        for p, bt in patterns:
            summary = get_covered_call_summary(conn, p["id"])
            summaries.append(summary)

        # Annualized Yield
        print(f"  {'Annualized Yield':<22}", end="")
        for summary in summaries:
            if summary["cycle_count"] > 0:
                print(f"  {summary['avg_premium_return_pct']:.1f}%{'':<16}", end="")
            else:
                print(f"  {'N/A':<20}", end="")
        print()

        # Assignment Frequency
        print(f"  {'Assignment Freq':<22}", end="")
        for summary in summaries:
            if summary["cycle_count"] > 0:
                print(f"  {summary['assignment_frequency_pct']:.1f}%{'':<16}", end="")
            else:
                print(f"  {'N/A':<20}", end="")
        print()

        # Avg Premium/Month
        print(f"  {'Avg Premium/Cycle':<22}", end="")
        for summary in summaries:
            if summary["cycle_count"] > 0:
                print(f"  ${summary['avg_premium']:,.2f}{'':<12}", end="")
            else:
                print(f"  {'N/A':<20}", end="")
        print()

        # Capped Upside Cost
        print(f"  {'Capped Upside Cost':<22}", end="")
        for summary in summaries:
            if summary["total_capped_upside_pct"] > 0:
                print(f"  -{summary['total_capped_upside_pct']:.1f}%{'':<15}", end="")
            else:
                print(f"  {'0.0%':<20}", end="")
        print()

        # Total Return (from backtest)
        print(f"  {'Total Return':<22}", end="")
        for _, bt in patterns:
            if bt:
                print(f"  {bt['total_return_pct']:.1f}%{'':<16}", end="")
            else:
                print(f"  {'N/A':<20}", end="")
        print()

        # Cycles
        print(f"  {'Cycles':<22}", end="")
        for summary in summaries:
            print(f"  {summary['cycle_count']:<20}", end="")
        print()

        # Outcome breakdown
        print(f"  {'Expired Worthless':<22}", end="")
        for summary in summaries:
            print(f"  {summary['expired_count']:<20}", end="")
        print()

        print(f"  {'Closed Early':<22}", end="")
        for summary in summaries:
            print(f"  {summary['closed_early_count']:<20}", end="")
        print()

        print(f"  {'Rolled':<22}", end="")
        for summary in summaries:
            print(f"  {summary['rolled_count']:<20}", end="")
        print()

    elif all_news_dip:
        # News dip pattern comparison — show events, trades, regimes
        print()
        print("═" * 51)
        print("  PATTERN COMPARISON")
        print("═" * 51)
        print()
        print(f"  {'ID':<5}{'Name':<20}{'Events':<9}{'Trades':<9}{'Win%':<9}{'Avg Ret':<10}Regimes")

        for p, bt in patterns:
            pid = p["id"]
            name = p["name"][:18]
            events = bt["trigger_count"] if bt else 0
            trades = bt["trade_count"] if bt else 0
            if bt and bt["trade_count"] > 0:
                wr = f"{bt['win_count'] / bt['trade_count'] * 100:.1f}%"
                sign = "+" if bt["avg_return_pct"] >= 0 else ""
                avg_ret = f"{sign}{bt['avg_return_pct']:.1f}%"
            else:
                wr = "N/A"
                avg_ret = "N/A"

            # Summarize regimes from backtest regimes_json
            regime_str = "—"
            if bt and bt.get("regimes_json"):
                try:
                    regimes = json.loads(bt["regimes_json"])
                    if regimes:
                        counts = {}
                        for r in regimes:
                            label = r.get("label", "unknown")
                            counts[label] = counts.get(label, 0) + 1
                        parts = [f"{c} {l}" for l, c in counts.items()]
                        regime_str = ", ".join(parts)
                except (json.JSONDecodeError, TypeError):
                    pass

            print(f"  {pid:<5}{name:<20}{events:<9}{trades:<9}{wr:<9}{avg_ret:<10}{regime_str}")

        # Regime overlay table
        # Collect all regimes across patterns
        all_regimes = {}  # pid -> list of regime dicts
        for p, bt in patterns:
            if bt and bt.get("regimes_json"):
                try:
                    all_regimes[p["id"]] = json.loads(bt["regimes_json"])
                except (json.JSONDecodeError, TypeError):
                    all_regimes[p["id"]] = []
            else:
                all_regimes[p["id"]] = []

        has_any_regimes = any(r for r in all_regimes.values())
        if has_any_regimes:
            # Collect all unique periods
            all_periods = set()
            for regimes in all_regimes.values():
                for r in regimes:
                    period = f"{r.get('start_date', '')[:7]} – {r.get('end_date', '')[:7]}"
                    all_periods.add(period)

            if all_periods:
                print()
                print("  ─── REGIME OVERLAY ─────────────────────────────")
                header = f"  {'Period':<22}"
                for p, _ in patterns:
                    header += f"{'ID ' + str(p['id']):<12}"
                print(header)

                for period in sorted(all_periods):
                    row = f"  {period:<22}"
                    for p, _ in patterns:
                        label = "—"
                        for r in all_regimes.get(p["id"], []):
                            rp = f"{r.get('start_date', '')[:7]} – {r.get('end_date', '')[:7]}"
                            if rp == period:
                                label = r.get("label", "—")
                                break
                        row += f"{label:<12}"
                    print(row)

        print("═" * 51)

    else:
        # Standard pattern comparison
        # Win rate
        print(f"  {'Win Rate':<22}", end="")
        for _, bt in patterns:
            if bt and bt["trade_count"] > 0:
                wr = bt["win_count"] / bt["trade_count"] * 100
                print(f"  {wr:.1f}%{'':<16}", end="")
            else:
                print(f"  {'N/A':<20}", end="")
        print()

        # Avg return
        print(f"  {'Avg Return':<22}", end="")
        for _, bt in patterns:
            if bt:
                print(f"  {bt['avg_return_pct']:.2f}%{'':<15}", end="")
            else:
                print(f"  {'N/A':<20}", end="")
        print()

        # Max drawdown
        print(f"  {'Max Drawdown':<22}", end="")
        for _, bt in patterns:
            if bt:
                print(f"  {bt['max_drawdown_pct']:.2f}%{'':<15}", end="")
            else:
                print(f"  {'N/A':<20}", end="")
        print()

        # Trade count
        print(f"  {'Trades':<22}", end="")
        for _, bt in patterns:
            if bt:
                print(f"  {bt['trade_count']:<20}", end="")
            else:
                print(f"  {'N/A':<20}", end="")
        print()


def _pattern_retire(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    pattern_id: int,
) -> None:
    """Retire a pattern."""
    from finance_agent.patterns.storage import get_pattern, update_pattern_status

    pattern = get_pattern(conn, pattern_id)
    if not pattern:
        print(f"Error: Pattern #{pattern_id} not found")
        sys.exit(1)

    if pattern["status"] == "retired":
        print(f"Pattern #{pattern_id} is already retired")
        return

    update_pattern_status(conn, pattern_id, "retired")
    print(f"Pattern #{pattern_id} ({pattern['name']}) has been retired")

    audit.log("pattern_retired", "pattern_lab", {"pattern_id": pattern_id})


def _pattern_ab_test(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    settings: Settings,
    args: argparse.Namespace,
) -> None:
    """Run an A/B test comparing pattern variants with statistical significance."""
    from datetime import date, timedelta

    from finance_agent.patterns.market_data import fetch_and_cache_bars
    from finance_agent.patterns.models import EventDetectionConfig, RuleSet
    from finance_agent.patterns.stats import format_significance, run_ab_test
    from finance_agent.patterns.storage import get_pattern

    # Validate: need at least 2 pattern IDs
    if len(args.pattern_ids) < 2:
        print("Error: A/B test requires at least 2 pattern IDs.")
        sys.exit(1)

    # Validate: tickers required
    tickers = args.tickers.split(",") if args.tickers else []
    if not tickers:
        print("Error: --tickers is required for A/B testing.")
        sys.exit(1)

    # Validate patterns exist and are confirmed
    event_configs: dict[int, tuple[RuleSet, EventDetectionConfig]] = {}
    pattern_names: dict[int, str] = {}
    for pid in args.pattern_ids:
        pattern = get_pattern(conn, pid)
        if not pattern:
            print(f"Error: Pattern #{pid} not found.")
            sys.exit(1)
        if pattern["status"] == "draft":
            print(f"Error: Pattern #{pid} is in draft status. Confirm the pattern first.")
            sys.exit(1)

        rule_set = RuleSet.model_validate_json(pattern["rule_set_json"])
        pattern_names[pid] = pattern["name"]

        # Build event config per pattern
        spike_threshold = None
        volume_multiple = None
        for tc in rule_set.trigger_conditions:
            if tc.field == "price_change_pct" and spike_threshold is None:
                spike_threshold = float(tc.value)
            if tc.field == "volume_spike" and volume_multiple is None:
                volume_multiple = float(tc.value)

        event_config = EventDetectionConfig(
            spike_threshold_pct=spike_threshold or 5.0,
            volume_multiple_min=volume_multiple or 1.5,
            entry_window_days=rule_set.entry_signal.window_days,
        )
        event_configs[pid] = (rule_set, event_config)

    # Parse dates
    end_date = args.end or date.today().isoformat()
    start_date = args.start or (date.today() - timedelta(days=365)).isoformat()

    # Fetch price data
    print(f"A/B Testing patterns: {', '.join(f'#{p}' for p in args.pattern_ids)}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Tickers: {', '.join(tickers)}")
    print()
    print("Fetching market data...")
    all_bars: dict[str, list[dict]] = {}
    for ticker in tickers:
        bars = fetch_and_cache_bars(
            conn, ticker, start_date, end_date, "day",
            settings.active_api_key, settings.active_secret_key,
        )
        if bars:
            all_bars[ticker] = bars
            print(f"  {ticker}: {len(bars)} bars")
        else:
            print(f"  {ticker}: no data available")

    if not all_bars:
        print("\nError: No price data available for any ticker")
        sys.exit(1)

    print("\nRunning A/B test...")
    result = run_ab_test(
        conn=conn,
        pattern_ids=args.pattern_ids,
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        all_bars=all_bars,
        event_configs=event_configs,
    )

    # Display A/B test results
    tickers_str = ",".join(tickers)
    print()
    print("═" * 51)
    print("  A/B TEST COMPARISON")
    print(f"  {start_date} -> {end_date} | Tickers: {tickers_str}")
    print("═" * 51)

    # Variant metrics table
    print()
    print("  --- VARIANT METRICS ---------------------------")
    print(f"  {'ID':<5}{'Name':<20}{'Events':<8}{'Trades':<8}{'Win%':<7}Avg Ret")
    for vr in result.variant_reports:
        cr = vr.combined_report
        name = pattern_names.get(vr.pattern_id, "")[:18]
        wr = f"{cr.win_count / cr.trade_count * 100:.1f}%" if cr.trade_count > 0 else "—"
        sign = "+" if cr.avg_return_pct >= 0 else ""
        ar = f"{sign}{cr.avg_return_pct:.1f}%" if cr.trade_count > 0 else "—"
        print(f"  {vr.pattern_id:<5}{name:<20}{cr.trigger_count:<8}{cr.trade_count:<8}{wr:<7}{ar}")

    # Statistical significance table
    print()
    print("  --- STATISTICAL SIGNIFICANCE ------------------")
    print(f"  {'Comparison':<19}{'Win Rate':<17}Avg Return")
    for comp in result.comparisons:
        label = f"#{comp.variant_a_id} vs #{comp.variant_b_id}"
        wr_str = f"p={comp.win_rate_p_value:.2f} {format_significance(comp.win_rate_p_value)}"
        ar_str = f"p={comp.avg_return_p_value:.2f} {format_significance(comp.avg_return_p_value)}"
        print(f"  {label:<19}{wr_str:<17}{ar_str}")

    # Multiple comparisons warning for 3+ variants
    n_comparisons = len(result.comparisons)
    if n_comparisons > 1:
        false_positive_rate = 1 - (0.95 ** n_comparisons)
        print()
        print(f"  Note: With {n_comparisons} comparisons, ~{false_positive_rate*100:.0f}% chance")
        print("  of at least one false positive at p < 0.05.")

    # Result section
    print()
    print("  --- RESULT ------------------------------------")
    best_name = pattern_names.get(result.best_variant_id, "")
    print(f"  Best variant: #{result.best_variant_id} ({best_name})")
    if result.best_is_significant:
        print("  Advantage: Statistically significant (p < 0.05)")
    else:
        print("  Advantage: Not statistically significant (p > 0.05)")
        print("  ! Consider collecting more data before choosing.")

    # Sample size warnings
    for warning in result.sample_size_warnings:
        print(f"  {warning}")

    print("═" * 51)

    audit.log("ab_test_run", "pattern_lab", {
        "pattern_ids": args.pattern_ids,
        "tickers": tickers,
        "best_variant_id": result.best_variant_id,
        "best_is_significant": result.best_is_significant,
    })


def _pattern_export(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> None:
    """Export backtest results to a markdown file."""
    from finance_agent.patterns.export import (
        export_backtest_markdown,
        generate_export_path,
    )
    from finance_agent.patterns.storage import get_pattern

    # Validate format
    if args.export_format != "markdown":
        print(f"Error: Unsupported format '{args.export_format}'. Supported formats: markdown")
        sys.exit(1)

    # Validate pattern exists
    pattern = get_pattern(conn, args.pattern_id)
    if not pattern:
        print(f"Error: Pattern #{args.pattern_id} not found.")
        sys.exit(1)

    # Get backtest results
    backtest_id = getattr(args, "backtest_id", None)
    if backtest_id:
        row = conn.execute(
            "SELECT * FROM backtest_result WHERE id = ? AND pattern_id = ?",
            (backtest_id, args.pattern_id),
        ).fetchone()
        if not row:
            print(f"Error: Backtest result #{backtest_id} not found for pattern #{args.pattern_id}.")
            sys.exit(1)
        backtest_row = dict(row)
    else:
        # Get most recent backtest
        row = conn.execute(
            "SELECT * FROM backtest_result WHERE pattern_id = ? ORDER BY id DESC LIMIT 1",
            (args.pattern_id,),
        ).fetchone()
        if not row:
            print(f"Error: No backtest results found for pattern #{args.pattern_id}. Run a backtest first.")
            sys.exit(1)
        backtest_row = dict(row)
        backtest_id = backtest_row["id"]

    # Get trades for this backtest
    trade_rows = conn.execute(
        "SELECT * FROM backtest_trade WHERE backtest_id = ? ORDER BY trigger_date",
        (backtest_id,),
    ).fetchall()
    trades = [dict(r) for r in trade_rows]

    # Generate markdown content
    markdown = export_backtest_markdown(pattern, backtest_row, trades)

    # Determine output path
    output_path = args.output or generate_export_path(args.pattern_id, "backtest")

    # Write file
    from pathlib import Path
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")

    print(f"Exported backtest results for pattern #{args.pattern_id} to {output_path}")


def _pattern_scan(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    settings: Settings,
    args: argparse.Namespace,
) -> None:
    """Run the pattern scanner against live market data."""
    import os
    import time

    from finance_agent.patterns.scanner import run_scan

    api_key = os.environ.get("ALPACA_PAPER_API_KEY", "")
    secret_key = os.environ.get("ALPACA_PAPER_SECRET_KEY", "")
    if not api_key or not secret_key:
        print("Error: ALPACA_PAPER_API_KEY and ALPACA_PAPER_SECRET_KEY must be set")
        sys.exit(1)

    def _do_scan() -> None:
        result = run_scan(
            conn=conn,
            api_key=api_key,
            secret_key=secret_key,
            cooldown_hours=args.cooldown,
            audit=audit,
        )
        print("Pattern Scanner")
        print(f"  Patterns evaluated: {result['patterns_evaluated']}")
        print(f"  Tickers scanned: {result['tickers_scanned']}")
        print(f"  Alerts generated: {result['alerts_generated']}")

        if result["auto_executions"] > 0:
            print(f"  Auto-executions: {result['auto_executions']}")
        if result["auto_executions_blocked"] > 0:
            print(f"  Auto-executions blocked: {result['auto_executions_blocked']}")

        if result["alerts"]:
            print()
            print("  NEW ALERTS:")
            for alert in result["alerts"]:
                details = alert["trigger_details"]
                prev = details.get("previous_close", 0)
                latest = details.get("latest_price", 0)
                pct = details.get("price_change_pct", 0)
                vol = details.get("volume_multiple", 0)
                wr = alert.get("pattern_win_rate")
                wr_str = f"{wr * 100:.1f}%" if wr is not None else "N/A"

                print(f"  #{alert['id']}  {alert['pattern_name']}  |  {alert['ticker']}  |  {alert['trigger_date']}")
                print(f"      Price: {pct:+.1f}% (${prev:.2f} → ${latest:.2f})  |  Volume: {vol:.1f}x avg")
                print(f"      Action: {alert['recommended_action']}  |  Win rate: {wr_str}")

                status_line = f"      Status: {alert['status']}"
                if alert.get("auto_executed"):
                    exec_result = alert.get("auto_execute_result", {})
                    trade_id = exec_result.get("trade_id", "?")
                    status_line += f"  |  AUTO-EXECUTED: paper trade #{trade_id} submitted"
                elif (alert.get("auto_execute_result") or {}).get("blocked_reason"):
                    reason = alert["auto_execute_result"]["blocked_reason"]
                    status_line += f"  |  AUTO-BLOCKED: {reason}"
                print(status_line)
        elif result["patterns_evaluated"] == 0:
            print("\n  No patterns in paper_trading status. Run 'finance-agent pattern paper-trade <id>' first.")

    if args.watch:
        print(f"Watching for triggers every {args.watch} minutes. Press Ctrl+C to stop.\n")
        try:
            while True:
                _do_scan()
                print(f"\n  Next scan in {args.watch} minutes...\n")
                time.sleep(args.watch * 60)
        except KeyboardInterrupt:
            print("\nScanner stopped.")
    else:
        _do_scan()


def _pattern_alerts(
    conn: sqlite3.Connection,
    args: argparse.Namespace,
) -> None:
    """List and manage pattern alerts."""
    from finance_agent.patterns.alert_storage import list_alerts, update_alert_status

    # Handle status update actions: ack, dismiss, acted
    if args.action in ("ack", "dismiss", "acted"):
        if not args.alert_id:
            print(f"Error: alert ID required for '{args.action}' action")
            sys.exit(1)

        status_map = {"ack": "acknowledged", "dismiss": "dismissed", "acted": "acted_on"}
        new_status = status_map[args.action]

        if update_alert_status(conn, args.alert_id, new_status):
            print(f"Alert #{args.alert_id} → {new_status}")
        else:
            print(f"Alert #{args.alert_id} not found")
            sys.exit(1)
        return

    # List alerts
    alerts = list_alerts(
        conn,
        status=args.status,
        pattern_id=getattr(args, "pattern_id", None),
        ticker=args.ticker,
        days=args.days,
    )

    if not alerts:
        print("No alerts found.")
        return

    print(f"Pattern Alerts (last {args.days} days):\n")
    for a in alerts:
        details = a.get("trigger_details", {})
        pct = details.get("price_change_pct", 0)
        vol = details.get("volume_multiple", 0)
        wr = a.get("pattern_win_rate")
        wr_str = f"{wr * 100:.1f}%" if wr is not None else "N/A"

        status_tag = a["status"].upper()
        auto_tag = ""
        if a.get("auto_executed"):
            auto_tag = " [AUTO-EXECUTED]"

        print(f"  #{a['id']}  [{status_tag}]{auto_tag}  {a['pattern_name']}  |  {a['ticker']}  |  {a['trigger_date']}")
        print(f"       Price: {pct:+.1f}%  |  Volume: {vol:.1f}x  |  Action: {a['recommended_action']}  |  Win rate: {wr_str}")


def _pattern_auto_execute(
    conn: sqlite3.Connection,
    audit: AuditLogger,
    args: argparse.Namespace,
) -> None:
    """Enable or disable auto-execution for a pattern."""
    from finance_agent.patterns.storage import get_pattern

    pattern = get_pattern(conn, args.pattern_id)
    if not pattern:
        print(f"Error: pattern #{args.pattern_id} not found")
        sys.exit(1)

    new_value = 1 if args.enable else 0
    conn.execute(
        "UPDATE trading_pattern SET auto_execute = ? WHERE id = ?",
        (new_value, args.pattern_id),
    )
    conn.commit()

    action = "enabled" if args.enable else "disabled"
    print(f"Auto-execution {action} for pattern #{args.pattern_id} ({pattern['name']})")

    audit.log("auto_execute_toggle", "pattern_lab", {
        "pattern_id": args.pattern_id,
        "enabled": args.enable,
    })


def _pattern_dashboard(conn: sqlite3.Connection) -> None:
    """Display the portfolio dashboard."""
    from finance_agent.patterns.dashboard import format_dashboard, get_dashboard_data

    data = get_dashboard_data(conn)
    print(format_dashboard(data))


def _pattern_perf(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    """Show performance comparison: backtest vs paper trade."""
    from finance_agent.patterns.dashboard import (
        format_performance,
        get_performance_comparison,
    )

    pattern_id = getattr(args, "pattern_id", None)
    comparisons = get_performance_comparison(conn, pattern_id=pattern_id)

    if not comparisons:
        if pattern_id:
            print(f"No backtest data found for pattern #{pattern_id}")
        else:
            print("No patterns with backtest data found")
        sys.exit(1)

    single = pattern_id is not None
    print(format_performance(comparisons, single=single))


def _pattern_schedule(args: argparse.Namespace) -> None:
    """Manage the automated scan schedule."""
    from finance_agent.scheduling.scan_schedule import (
        get_scan_schedule,
        install_scan_schedule,
        pause_scan_schedule,
        remove_scan_schedule,
        resume_scan_schedule,
    )

    cmd = getattr(args, "schedule_command", None)

    if cmd == "install":
        result = install_scan_schedule(args.interval, cooldown_hours=args.cooldown)
        if "error" in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        print("Scan schedule installed:")
        print(f"  Interval: every {args.interval} minutes")
        print(f"  Market hours: 9:30 AM \u2013 4:00 PM ET (weekdays only)")
        print(f"  Plist: {result['plist_path']}")
        print(f"  Status: {result['status']}")

    elif cmd == "list":
        schedule = get_scan_schedule()
        if not schedule:
            print("No scan schedule installed.")
            print("Install one with: finance-agent pattern schedule install --interval 15")
            return
        print("Scan Schedule:")
        print(f"  Interval: every {schedule['interval_minutes']} minutes")
        print(f"  Market hours: 9:30 AM \u2013 4:00 PM ET")
        status_str = "active" if schedule["active"] else "paused"
        print(f"  Status: {status_str}")
        if schedule.get("last_run"):
            print(f"  Last run: {schedule['last_run']}")

    elif cmd == "pause":
        if pause_scan_schedule():
            print("Scan schedule paused.")
        else:
            print("No active schedule to pause.")

    elif cmd == "resume":
        if resume_scan_schedule():
            print("Scan schedule resumed.")
        else:
            print("No paused schedule to resume.")

    elif cmd == "remove":
        if remove_scan_schedule():
            print("Scan schedule removed.")
        else:
            print("No schedule to remove.")

    else:
        print("Usage: finance-agent pattern schedule {install|list|pause|resume|remove}")
        sys.exit(1)


def cmd_sandbox(args: argparse.Namespace) -> None:
    """Dispatch sandbox subcommands."""
    sub = getattr(args, "sandbox_command", None)
    if sub == "setup":
        _sandbox_setup()
    elif sub == "seed":
        _sandbox_seed(args)
    elif sub == "list":
        _sandbox_list(args)
    elif sub == "view":
        _sandbox_view(args)
    elif sub == "add":
        _sandbox_add(args)
    elif sub == "edit":
        _sandbox_edit(args)
    elif sub == "brief":
        _sandbox_brief(args)
    elif sub == "commentary":
        _sandbox_commentary(args)
    elif sub == "lists":
        _sandbox_lists(args)
    elif sub == "reports":
        _sandbox_reports(args)
    elif sub == "tasks":
        _sandbox_tasks(args)
    elif sub == "log":
        _sandbox_log(args)
    elif sub == "outreach":
        _sandbox_outreach(args)
    elif sub == "ask":
        _sandbox_ask(args)
    else:
        print("Usage: finance-agent sandbox {setup|seed|list|view|add|edit|brief|commentary|lists|reports|tasks|log|outreach|ask}")
        sys.exit(1)


def _get_sf() -> "Salesforce":  # noqa: F821
    """Get authenticated Salesforce client, loading .env if needed."""
    from dotenv import load_dotenv

    from finance_agent.sandbox.sfdc import get_sf_client

    load_dotenv()
    return get_sf_client()


def _sandbox_setup() -> None:
    from finance_agent.sandbox.sfdc import ensure_custom_fields

    sf = _get_sf()
    print("Checking Salesforce custom fields on Contact...")
    created = ensure_custom_fields(sf)
    if created:
        print(f"Created {len(created)} custom fields: {', '.join(created)}")
    else:
        print("All custom fields already exist.")
    print("Salesforce sandbox is ready.")


def _sandbox_seed(args: argparse.Namespace) -> None:
    from finance_agent.sandbox.seed import reset_sandbox, seed_clients
    from finance_agent.sandbox.storage import client_count

    sf = _get_sf()
    existing = client_count(sf)
    if existing > 0 and not args.reset:
        print(f"Salesforce already has {existing} contacts.")
        print(f"  Use --reset to delete sandbox data first, or --count N to add more.")
        print(f"  Adding {args.count} new clients...")

    if args.reset:
        reset_sandbox(sf)
        print("Reset sandbox data (deleted @example.com contacts and their tasks).")

    created = seed_clients(sf, count=args.count)
    total = client_count(sf)
    print(f"Pushed {created} synthetic clients to Salesforce. Total contacts: {total}.")


def _sandbox_list(args: argparse.Namespace) -> None:
    from finance_agent.sandbox.models import CompoundFilter
    from finance_agent.sandbox.storage import format_query_results, list_clients

    sf = _get_sf()

    # Build filter kwargs — risk/stage are now lists (nargs="+")
    risk_tolerances = args.risk  # list or None
    life_stages = args.stage  # list or None

    clients = list_clients(
        sf,
        risk_tolerances=risk_tolerances,
        life_stages=life_stages,
        min_value=getattr(args, "min_value", None),
        max_value=getattr(args, "max_value", None),
        min_age=getattr(args, "min_age", None),
        max_age=getattr(args, "max_age", None),
        not_contacted_days=getattr(args, "not_contacted_days", None),
        contacted_after=getattr(args, "contacted_after", None),
        contacted_before=getattr(args, "contacted_before", None),
        search=args.search,
        sort_by=args.sort_by,
        sort_dir=args.sort_dir,
        limit=args.limit,
    )

    # Build CompoundFilter for describe()
    filters = CompoundFilter(
        risk_tolerances=risk_tolerances,
        life_stages=life_stages,
        min_value=getattr(args, "min_value", None),
        max_value=getattr(args, "max_value", None),
        min_age=getattr(args, "min_age", None),
        max_age=getattr(args, "max_age", None),
        not_contacted_days=getattr(args, "not_contacted_days", None),
        contacted_after=getattr(args, "contacted_after", None),
        contacted_before=getattr(args, "contacted_before", None),
        search=args.search,
        sort_by=args.sort_by,
        sort_dir=args.sort_dir,
        limit=args.limit,
    )

    if not clients:
        print("No clients match your criteria.")
        if filters.describe() != "no filters":
            print(f"Filters applied: {filters.describe()}")
        return

    # Header with age column
    print(f"\n{'ID':<20} {'Name':<25} {'Age':>4} {'Account Value':>14} {'Risk':<14} {'Life Stage':<16} {'Last Contact':<12}")
    print("-" * 111)

    for c in clients:
        cid = c["id"][:15] + "..."
        name = f"{c['first_name']} {c['last_name']}"[:23]
        age_str = str(c.get("age") or "—")
        value = f"${c['account_value']:,.0f}"
        risk = c["risk_tolerance"]
        stage = c["life_stage"]
        last_contact = c.get("last_interaction_date") or "—"
        print(f"{cid:<20} {name:<25} {age_str:>4} {value:>14} {risk:<14} {stage:<16} {last_contact:<12}")

    print(f"\nFilters applied: {filters.describe()}")
    print(f"Showing {len(clients)} clients")


def _sandbox_view(args: argparse.Namespace) -> None:
    from finance_agent.sandbox.storage import get_client

    sf = _get_sf()
    client = get_client(sf, args.client_id)
    if not client:
        print(f"Client {args.client_id} not found. Run 'sandbox list' to see available clients.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Client: {client['first_name']} {client['last_name']}")
    print(f"  SFDC ID: {client['id']}")
    print(f"{'='*60}")
    print(f"  Age:              {client.get('age') or '—'}")
    print(f"  Occupation:       {client.get('occupation') or '—'}")
    print(f"  Email:            {client.get('email') or '—'}")
    print(f"  Phone:            {client.get('phone') or '—'}")
    acct_val = client.get('account_value')
    print(f"  Account Value:    ${acct_val:,.2f}" if acct_val else "  Account Value:    —")
    print(f"  Risk Tolerance:   {client.get('risk_tolerance') or '—'}")
    print(f"  Life Stage:       {client.get('life_stage') or '—'}")
    print(f"  Investment Goals: {client.get('investment_goals') or '—'}")
    print(f"  Household:        {client.get('household_members') or '—'}")
    print(f"  Notes:            {client.get('notes') or '—'}")
    print(f"  Created:          {client.get('created_at') or '—'}")
    print(f"  Updated:          {client.get('updated_at') or '—'}")

    interactions = client.get("interactions", [])
    if interactions:
        print(f"\n  Interaction History ({len(interactions)} records):")
        print(f"  {'-'*55}")
        for ix in interactions:
            itype = (ix.get("interaction_type") or "").upper()
            print(f"  [{ix['interaction_date']}] {itype}: {ix['summary']}")
    else:
        print("\n  No interaction history.")
    print()


def _sandbox_add(args: argparse.Namespace) -> None:
    from finance_agent.sandbox.models import ClientCreate
    from finance_agent.sandbox.storage import add_client

    try:
        client_data = ClientCreate(
            first_name=args.first,
            last_name=args.last,
            age=args.age,
            occupation=args.occupation,
            email=f"{args.first.lower()}.{args.last.lower()}@example.com",
            phone="555-000-0000",
            account_value=args.account_value,
            risk_tolerance=args.risk,
            life_stage=args.life_stage,
            investment_goals=args.goals,
            notes=args.notes,
        )
    except Exception as e:
        print(f"Validation error: {e}")
        sys.exit(1)

    sf = _get_sf()
    cid = add_client(sf, client_data.model_dump())
    print(f"Client created in Salesforce: {args.first} {args.last} (ID: {cid})")


def _sandbox_edit(args: argparse.Namespace) -> None:
    from finance_agent.sandbox.storage import update_client

    updates = {}
    if args.account_value is not None:
        updates["account_value"] = args.account_value
    if args.risk:
        updates["risk_tolerance"] = args.risk
    if args.life_stage:
        updates["life_stage"] = args.life_stage
    if args.goals is not None:
        updates["investment_goals"] = args.goals
    if args.notes is not None:
        updates["notes"] = args.notes

    if not updates:
        print("No fields to update. Use --account-value, --risk, --life-stage, --goals, or --notes.")
        sys.exit(1)

    sf = _get_sf()
    ok = update_client(sf, args.client_id, updates)
    if ok:
        print(f"Client {args.client_id} updated in Salesforce.")
    else:
        print(f"Client {args.client_id} not found.")
        sys.exit(1)


def _sandbox_brief(args: argparse.Namespace) -> None:
    from finance_agent.sandbox.meeting_prep import generate_meeting_brief

    sf = _get_sf()
    # Also get SQLite connection for research signals
    conn, _, _ = _get_db_and_audit()
    try:
        brief = generate_meeting_brief(sf, args.client_id, db_conn=conn)
        print(f"\n{'='*60}")
        print(f"  Meeting Brief: {brief['client_name']}")
        print(f"  Generated: {brief['generated_at']}")
        print(f"{'='*60}\n")
        print("## Client Summary\n")
        print(brief["client_summary"])
        print("\n## Portfolio Context\n")
        print(brief["portfolio_context"])
        print("\n## Market Conditions\n")
        print(brief["market_conditions"])
        print("\n## Talking Points\n")
        for i, tp in enumerate(brief["talking_points"], 1):
            print(f"{i}. {tp}")
        if not brief["market_data_available"]:
            print("\n⚠ Market data unavailable — run research pipeline first.")
        print()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        conn.close()


def _sandbox_commentary(args: argparse.Namespace) -> None:
    from finance_agent.sandbox.commentary import generate_commentary

    conn, _, _ = _get_db_and_audit()
    try:
        result = generate_commentary(
            conn,
            risk_tolerance=args.risk,
            life_stage=args.stage,
        )
        print(f"\n{'='*60}")
        print(f"  Market Commentary: {result['segment']}")
        print(f"  Generated: {result['generated_at']}")
        print(f"{'='*60}\n")
        print(result["commentary"])
        if not result["market_data_available"]:
            print("\n⚠ Market data unavailable — run research pipeline first.")
        print()
    finally:
        conn.close()


def _build_compound_filter(args: argparse.Namespace) -> "CompoundFilter":
    """Build a CompoundFilter from CLI args that have filter flags."""
    from finance_agent.sandbox.models import CompoundFilter

    return CompoundFilter(
        risk_tolerances=getattr(args, "risk", None),
        life_stages=getattr(args, "stage", None),
        min_value=getattr(args, "min_value", None),
        max_value=getattr(args, "max_value", None),
        min_age=getattr(args, "min_age", None),
        max_age=getattr(args, "max_age", None),
        not_contacted_days=getattr(args, "not_contacted_days", None),
        contacted_after=getattr(args, "contacted_after", None),
        contacted_before=getattr(args, "contacted_before", None),
        search=getattr(args, "search", None),
        sort_by=getattr(args, "sort_by", None) or "account_value",
        sort_dir=getattr(args, "sort_dir", None) or "desc",
        limit=getattr(args, "limit", None) or 50,
    )


def _sandbox_ask(args: argparse.Namespace) -> None:
    from finance_agent.sandbox.list_builder import execute_nl_query

    sf = _get_sf()
    try:
        result = execute_nl_query(sf, args.query, confirmed=args.yes)
    except Exception as e:
        print(f"Error: NL query service unavailable — {e}")
        sys.exit(1)

    if not result.get("executed"):
        interp = result["interpretation"]
        print(f"\nI interpreted your query as:")
        print(f"  Filters: {interp['filters'].get('sort_by', 'account_value')} sorted, limit {interp['filters'].get('limit', 50)}")
        if interp.get("filter_mapping"):
            print("\n  Filter mapping:")
            for phrase, filt in interp["filter_mapping"].items():
                print(f'    "{phrase}" → {filt}')
        if interp.get("unrecognized"):
            print(f"\n  Unclear parts: {', '.join(interp['unrecognized'])}")
        print("\nRun with --yes to skip confirmation, or rephrase your query.")
        return

    clients = result["clients"]
    if not clients:
        print("No clients match your query.")
        print(f"Filters applied: {result['filters_applied']}")
        return

    # Show filter mapping
    if result.get("filter_mapping"):
        print("\nFilters applied:")
        for phrase, filt in result["filter_mapping"].items():
            print(f'  "{phrase}" → {filt}')
        print()

    # Results table
    print(f"{'ID':<20} {'Name':<25} {'Age':>4} {'Account Value':>14} {'Risk':<14} {'Life Stage':<16} {'Last Contact':<12}")
    print("-" * 111)
    for c in clients:
        cid = c["id"][:15] + "..."
        name = f"{c['first_name']} {c['last_name']}"[:23]
        age_str = str(c.get("age") or "—")
        value = f"${c['account_value']:,.0f}"
        print(f"{cid:<20} {name:<25} {age_str:>4} {value:>14} {c['risk_tolerance']:<14} {c['life_stage']:<16} {c.get('last_interaction_date') or '—':<12}")

    print(f"\nShowing {result['count']} clients matching filters")

    # --save-as: create a Salesforce List View from the interpreted filters
    save_as = getattr(args, "save_as", None)
    if save_as and result.get("executed") and clients:
        from finance_agent.sandbox.models import CompoundFilter
        from finance_agent.sandbox.sfdc_listview import create_listview

        raw_filters = result.get("filters_raw") or result.get("interpretation", {}).get("filters", {})
        cf = CompoundFilter(**{k: v for k, v in raw_filters.items() if v is not None})
        try:
            lv = create_listview(sf, save_as, cf)
            print(f"\nList View created: {lv['name']}")
            print(f"Filters: {lv['filters_applied']}")
            if lv["warnings"]:
                print("Warnings:")
                for w in lv["warnings"]:
                    print(f"  - {w}")
            print(f"URL: {lv['url']}")
        except Exception as e:
            print(f"\nError creating List View: {e}")


def _sandbox_reports(args: argparse.Namespace) -> None:
    from finance_agent.sandbox.sfdc_report import (
        create_report,
        delete_report,
        list_reports,
    )

    sub = getattr(args, "reports_command", None)

    if sub == "save":
        sf = _get_sf()
        filters = _build_compound_filter(args)
        try:
            result = create_report(sf, args.name, filters)
            print(f"\nReport created: {result['name']}")
            print(f"Folder: {result['folder']}")
            print(f"Filters: {result['filters_applied']}")
            if result["warnings"]:
                print("Warnings:")
                for w in result["warnings"]:
                    print(f"  - {w}")
            print(f"URL: {result['url']}")
        except Exception as e:
            print(f"Error creating Report: {e}")
            sys.exit(1)

    elif sub == "show":
        sf = _get_sf()
        reports = list_reports(sf)
        if not reports:
            print("No tool-created Reports found.")
            return
        print(f"\n{'Name':<35} {'Folder':<15} {'URL'}")
        print("-" * 120)
        for r in reports:
            print(f"{r['name']:<35} {'Client Lists':<15} {r['url']}")
        print(f"\n{len(reports)} Report(s).")

    elif sub == "delete":
        sf = _get_sf()
        deleted = delete_report(sf, args.name)
        if deleted:
            print(f"Deleted Report '{args.name}'.")
        else:
            print(f"Report '{args.name}' not found.")

    else:
        print("Usage: finance-agent sandbox reports {save|show|delete}")
        sys.exit(1)


def _sandbox_lists(args: argparse.Namespace) -> None:
    from finance_agent.sandbox.sfdc_listview import (
        create_listview,
        delete_listview,
        list_listviews,
    )

    sub = getattr(args, "lists_command", None)

    if sub == "save":
        sf = _get_sf()
        filters = _build_compound_filter(args)
        try:
            result = create_listview(sf, args.name, filters)
            print(f"\nList View created: {result['name']}")
            print(f"Filters: {result['filters_applied']}")
            if result["warnings"]:
                print("Warnings:")
                for w in result["warnings"]:
                    print(f"  - {w}")
            print(f"URL: {result['url']}")
        except Exception as e:
            print(f"Error creating List View: {e}")
            sys.exit(1)

    elif sub == "show":
        sf = _get_sf()
        views = list_listviews(sf)
        if not views:
            print("No tool-created List Views found.")
            return
        print(f"\n{'Name':<35} {'URL'}")
        print("-" * 100)
        for v in views:
            print(f"{v['name']:<35} {v['url']}")
        print(f"\n{len(views)} List View(s).")

    elif sub == "delete":
        sf = _get_sf()
        deleted = delete_listview(sf, args.name)
        if deleted:
            print(f"Deleted List View '{args.name}'.")
        else:
            print(f"List View '{args.name}' not found.")

    else:
        print("Usage: finance-agent sandbox lists {save|show|delete}")
        sys.exit(1)


def _sandbox_tasks(args: argparse.Namespace) -> None:
    """Dispatch sandbox tasks sub-subcommands."""
    from finance_agent.sandbox.sfdc_tasks import (
        complete_task,
        create_task,
        get_task_summary,
        list_tasks,
        resolve_contact,
    )

    sub = getattr(args, "tasks_command", None)

    if sub == "create":
        sf = _get_sf()
        contacts = resolve_contact(sf, args.client)
        if not contacts:
            print(f"No contacts found matching '{args.client}'.")
            sys.exit(1)
        if len(contacts) > 1:
            print(f"Multiple contacts match '{args.client}':")
            for c in contacts:
                print(f"  {c['name']} ({c['id']})")
            print("Please specify the full name.")
            sys.exit(1)

        contact = contacts[0]
        try:
            result = create_task(
                sf,
                contact["id"],
                args.subject,
                due_date=args.due,
                priority=args.priority,
            )
        except Exception as e:
            print(f"Error creating task: {e}")
            sys.exit(1)

        print(f"Task created: \"{result['subject']}\"")
        print(f"  Client:   {contact['name']} ({contact['id']})")
        print(f"  Due:      {result['due_date']}")
        print(f"  Priority: {result['priority']}")
        print(f"  Status:   {result['status']}")

    elif sub == "show":
        sf = _get_sf()
        client_name = getattr(args, "client", None)
        overdue_only = getattr(args, "overdue", False)
        summary_only = getattr(args, "summary", False)

        if summary_only:
            summary = get_task_summary(sf)
            print("Task Summary:")
            print(f"  Total open:    {summary['total_open']}")
            print(f"  Overdue:       {summary['overdue']}")
            print(f"  Due today:     {summary['due_today']}")
            print(f"  Due this week: {summary['due_this_week']}")
            return

        tasks = list_tasks(sf, client_name=client_name, overdue_only=overdue_only)
        if not tasks:
            print("No open tasks found.")
            return

        # Print table
        header = f"{'Subject':<35} {'Client':<18} {'Due':<12} {'Priority':<10} {'Status'}"
        print(header)
        print("─" * len(header))
        overdue_count = 0
        for t in tasks:
            overdue_marker = " ← OVERDUE" if t["overdue"] else ""
            if t["overdue"]:
                overdue_count += 1
            print(
                f"{t['subject'][:35]:<35} "
                f"{t['client_name'][:18]:<18} "
                f"{t['due_date']:<12} "
                f"{t['priority']:<10} "
                f"{t['status']}{overdue_marker}"
            )
        print(f"\n{len(tasks)} open tasks ({overdue_count} overdue)")

    elif sub == "complete":
        sf = _get_sf()
        result = complete_task(sf, args.subject)

        if result["status"] == "completed":
            print(
                f"Completed: \"{result['subject']}\" "
                f"({result['client_name']}, was due {result['due_date']})"
            )
        elif result["status"] == "ambiguous":
            print(f"Multiple tasks match \"{args.subject}\":")
            for m in result["matches"]:
                print(f"  \"{m['subject']}\" — {m['client_name']} (due {m['due_date']})")
            print("Please provide a more specific subject.")
        elif result["status"] == "already_completed":
            print(f"Task \"{result['subject']}\" is already completed.")
        else:
            print(f"No open tasks found matching \"{args.subject}\".")

    else:
        print("Usage: finance-agent sandbox tasks {create|show|complete}")
        sys.exit(1)


def _sandbox_log(args: argparse.Namespace) -> None:
    """Handle sandbox log command."""
    from finance_agent.sandbox.sfdc_tasks import log_activity, resolve_contact

    sf = _get_sf()
    contacts = resolve_contact(sf, args.client)
    if not contacts:
        print(f"No contacts found matching '{args.client}'.")
        sys.exit(1)
    if len(contacts) > 1:
        print(f"Multiple contacts match '{args.client}':")
        for c in contacts:
            print(f"  {c['name']} ({c['id']})")
        print("Please specify the full name.")
        sys.exit(1)

    contact = contacts[0]
    try:
        result = log_activity(
            sf,
            contact["id"],
            args.subject,
            args.activity_type,
            activity_date=args.activity_date,
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Activity logged: \"{result['subject']}\" ({result['activity_type']})")
    print(f"  Client: {contact['name']} ({contact['id']})")
    print(f"  Date:   {result['activity_date']}")


def _sandbox_outreach(args: argparse.Namespace) -> None:
    """Handle sandbox outreach command."""
    from finance_agent.sandbox.sfdc_tasks import (
        create_outreach_tasks,
        get_outreach_queue,
    )

    sf = _get_sf()
    days = args.days
    min_value = getattr(args, "min_value", 0) or 0
    do_create = getattr(args, "create_tasks", False)

    queue = get_outreach_queue(sf, days, min_value=min_value)

    if not queue:
        label = f"not contacted in {days}+ days" if days > 0 else ""
        print(f"No clients found{' ' + label if label else ''}.")
        return

    # Print header
    label = f"Clients not contacted in {days}+ days" if days > 0 else "All clients"
    print(f"Outreach Queue: {label}")
    if min_value > 0:
        print(f"  Min account value: ${min_value:,.0f}")
    print()

    header = f"{'Name':<22} {'Account Value':>15}    {'Last Contact':<14} {'Days Ago':>8}"
    print(header)
    print("─" * len(header))
    for c in queue:
        last = c["last_activity_date"] or "Never"
        days_ago = str(c["days_since_contact"]) if c["days_since_contact"] < 9999 else "Never"
        print(
            f"{c['name'][:22]:<22} "
            f"${c['account_value']:>14,.0f}    "
            f"{last:<14} "
            f"{days_ago:>8}"
        )

    print(f"\n{len(queue)} clients need outreach")

    if do_create:
        print()
        result = create_outreach_tasks(sf, queue, days)
        if result["tasks_created"] > 0 or result["tasks_skipped"] > 0:
            print("Created tasks:")
            # Re-list to show what happened
            for c in queue:
                skip = next(
                    (s for s in result["skipped_reasons"] if s["name"] == c["name"]),
                    None,
                )
                if skip:
                    print(f"  ⊘ {c['name']} — skipped ({skip['reason']})")
                else:
                    print(f"  ✓ {c['name']} — \"Follow-up: No contact in {c['days_since_contact']} days\"")
            print(
                f"\n{result['tasks_created']} tasks created, "
                f"{result['tasks_skipped']} skipped"
            )


def cmd_mcp(args: argparse.Namespace) -> None:
    """Start the MCP research server."""
    from finance_agent.mcp.research_server import mcp

    if args.http:
        print("Starting MCP server in HTTP mode on 0.0.0.0:8000...")
        mcp.run(transport="http", host="0.0.0.0", port=8000)
    else:
        mcp.run()


