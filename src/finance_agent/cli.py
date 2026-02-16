"""CLI entry point for finance-agent: health check and version commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from finance_agent import __version__
from finance_agent.config import ConfigError, load_settings, validate_settings


def main(argv: list[str] | None = None) -> None:
    """Main CLI entry point, registered as console_script 'finance-agent'."""
    parser = argparse.ArgumentParser(
        prog="finance-agent",
        description="AI-powered day trading agent using Alpaca Markets",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("version", help="Print version and exit")
    subparsers.add_parser("health", help="Run health checks")

    args = parser.parse_args(argv)

    if args.command == "version":
        cmd_version()
    elif args.command == "health":
        cmd_health()
    else:
        parser.print_help()
        sys.exit(1)


def cmd_version() -> None:
    """Print version and exit."""
    print(f"finance-agent {__version__}")
    sys.exit(0)


def cmd_health() -> None:
    """Validate configuration, database, and broker connectivity."""
    from finance_agent.audit.logger import AuditLogger
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

    # Live mode prominent warning (Constitution Principle I: Safety First)
    if settings.is_live:
        print("  *** WARNING: LIVE TRADING MODE — real money at risk ***")

    # Print any config warnings
    for warning in settings.warnings:
        print(f"  WARNING: {warning}")

    # --- Validate config ---
    errors = validate_settings(settings)
    if errors:
        print("Configuration: FAIL")
        for error in errors:
            print(f"  - {error}")
        print("Database: SKIP (configuration incomplete)")
        print("Broker API: SKIP (configuration incomplete)")
        sys.exit(1)

    print("Configuration: OK (all required settings present)")

    # --- Database ---
    migrations_dir = str(Path(__file__).resolve().parent.parent.parent / "migrations")
    db_ok = False
    conn = None
    try:
        conn = get_connection(settings.db_path)
        # Audit: startup + config_validated (before migrations, so we can't log yet)
        applied = run_migrations(conn, migrations_dir)
        version = get_schema_version(conn)
        db_name = Path(settings.db_path).name
        print(f"Database: OK ({db_name}, schema version {version})")
        db_ok = True

        # Now that DB is ready, create audit logger and log startup events
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

    # --- Broker API ---
    if not db_ok:
        print("Broker API: SKIP (database unavailable)")
        if conn:
            conn.close()
        sys.exit(1)

    broker_ok = False
    try:
        from alpaca.trading.client import TradingClient

        client = TradingClient(
            api_key=settings.active_api_key,
            secret_key=settings.active_secret_key,
            paper=not settings.is_live,
        )
        account = client.get_account()
        bp = str(account.buying_power) if hasattr(account, "buying_power") else "0"
        buying_power = f"${float(bp):,.2f}"
        status = getattr(account, "status", "UNKNOWN")
        print(f"Broker API: OK (account {status}, buying power: {buying_power})")
        broker_ok = True
    except Exception as e:
        error_msg = str(e)
        lower_msg = error_msg.lower()
        is_auth_error = (
            "forbidden" in lower_msg or "unauthorized" in lower_msg
            or "403" in error_msg or "401" in error_msg
        )
        if is_auth_error:
            print(f"Broker API: FAIL (authentication error: {error_msg})")
        else:
            print(f"Broker API: FAIL ({error_msg})")

    # Audit: health_check result
    if audit:
        audit.log("health_check", "cli", {
            "config_ok": True,
            "db_ok": db_ok,
            "broker_ok": broker_ok,
        })

    if conn:
        close_connection(conn)

    sys.exit(0 if broker_ok else 1)
