"""Scan schedule management via launchd (macOS) or cron (Linux).

Provides install/list/pause/resume/remove for a recurring pattern scanner
that runs during US market hours.
"""

from __future__ import annotations

import os
import platform
import plistlib
import shutil
import subprocess
import sys
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# US market holidays for 2026 (NYSE/NASDAQ closed)
US_MARKET_HOLIDAYS_2026 = {
    "2026-01-01",  # New Year's Day
    "2026-01-19",  # MLK Day
    "2026-02-16",  # Presidents' Day
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-07-03",  # Independence Day (observed)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving
    "2026-12-25",  # Christmas
}

MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / "com.advisor-agent.scanner.plist"
PLIST_LABEL = "com.advisor-agent.scanner"


def is_market_open(now: datetime | None = None) -> bool:
    """Check if US stock market is currently open.

    Args:
        now: Optional datetime to check. Defaults to current time.

    Returns:
        True if within market hours (9:30-16:00 ET, weekday, not a holiday).
    """
    if now is None:
        now = datetime.now(ET)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=ET)
    else:
        now = now.astimezone(ET)

    # Weekend check (Monday=0, Sunday=6)
    if now.weekday() >= 5:
        return False

    # Holiday check
    date_str = now.strftime("%Y-%m-%d")
    if date_str in US_MARKET_HOLIDAYS_2026:
        return False

    # Market hours check
    current_time = now.time()
    return MARKET_OPEN <= current_time < MARKET_CLOSE


def install_scan_schedule(
    interval_minutes: int,
    cooldown_hours: int = 24,
) -> dict:
    """Install a launchd plist (macOS) or crontab entry (Linux) for recurring scans.

    Args:
        interval_minutes: How often to scan (in minutes).
        cooldown_hours: Alert deduplication window in hours.

    Returns:
        Dict with plist_path and status.
    """
    if platform.system() == "Darwin":
        return _install_launchd(interval_minutes, cooldown_hours)
    elif platform.system() == "Linux":
        return _install_cron(interval_minutes, cooldown_hours)
    else:
        return {"error": f"Unsupported platform: {platform.system()}"}


def _install_launchd(interval_minutes: int, cooldown_hours: int) -> dict:
    """Generate and install a launchd plist on macOS."""
    # Find the finance-agent executable
    executable = shutil.which("finance-agent") or sys.executable

    program_args = [executable]
    if executable == sys.executable:
        program_args.extend(["-m", "finance_agent.cli"])
    program_args.extend(["pattern", "scan", "--cooldown", str(cooldown_hours)])

    # Build environment dict with Alpaca keys
    env_dict = {}
    for key in ["ALPACA_PAPER_API_KEY", "ALPACA_PAPER_SECRET_KEY", "ANTHROPIC_API_KEY"]:
        val = os.environ.get(key, "")
        if val:
            env_dict[key] = val

    # Also pass DB_PATH if set
    db_path = os.environ.get("DB_PATH", "")
    if db_path:
        env_dict["DB_PATH"] = db_path

    plist_data = {
        "Label": PLIST_LABEL,
        "ProgramArguments": program_args,
        "StartInterval": interval_minutes * 60,
        "StandardOutPath": str(Path.home() / ".advisor-agent-scanner.log"),
        "StandardErrorPath": str(Path.home() / ".advisor-agent-scanner.err"),
        "RunAtLoad": False,
    }
    if env_dict:
        plist_data["EnvironmentVariables"] = env_dict

    # Write plist
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Unload existing if present
    if PLIST_PATH.exists():
        subprocess.run(
            ["launchctl", "unload", str(PLIST_PATH)],
            capture_output=True,
        )

    with open(PLIST_PATH, "wb") as f:
        plistlib.dump(plist_data, f)

    # Load the plist
    result = subprocess.run(
        ["launchctl", "load", str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return {
            "error": f"launchctl load failed: {result.stderr.strip()}",
            "plist_path": str(PLIST_PATH),
            "status": "error",
        }

    return {
        "plist_path": str(PLIST_PATH),
        "status": "active",
    }


def _install_cron(interval_minutes: int, cooldown_hours: int) -> dict:
    """Add a crontab entry on Linux."""
    executable = shutil.which("finance-agent") or f"{sys.executable} -m finance_agent.cli"
    cron_line = (
        f"*/{interval_minutes} * * * 1-5 {executable} pattern scan --cooldown {cooldown_hours}"
    )

    # Get existing crontab
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""

    # Remove any existing advisor-agent scanner line
    lines = [
        l
        for l in existing.strip().split("\n")
        if l and "advisor-agent" not in l and "pattern scan" not in l
    ]
    lines.append(f"{cron_line}  # advisor-agent scanner")

    # Install updated crontab
    new_crontab = "\n".join(lines) + "\n"
    proc = subprocess.run(
        ["crontab", "-"],
        input=new_crontab,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return {"error": f"crontab install failed: {proc.stderr.strip()}", "status": "error"}

    return {"plist_path": "crontab", "status": "active"}


def get_scan_schedule() -> dict | None:
    """Get current schedule status.

    Returns:
        ScanScheduleConfig dict or None if no schedule installed.
    """
    if platform.system() == "Darwin":
        return _get_launchd_schedule()
    elif platform.system() == "Linux":
        return _get_cron_schedule()
    return None


def _get_launchd_schedule() -> dict | None:
    """Check launchd schedule status on macOS."""
    if not PLIST_PATH.exists():
        return None

    # Parse plist for interval
    with open(PLIST_PATH, "rb") as f:
        plist_data = plistlib.load(f)

    interval_seconds = plist_data.get("StartInterval", 0)
    interval_minutes = interval_seconds // 60 if interval_seconds else 0

    # Check if job is loaded
    result = subprocess.run(
        ["launchctl", "list", PLIST_LABEL],
        capture_output=True,
        text=True,
    )
    active = result.returncode == 0

    return {
        "interval_minutes": interval_minutes,
        "market_hours_only": True,
        "plist_path": str(PLIST_PATH),
        "active": active,
        "last_run": None,  # Would need audit_log query with db connection
    }


def _get_cron_schedule() -> dict | None:
    """Check cron schedule status on Linux."""
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0:
        return None

    for line in result.stdout.strip().split("\n"):
        if "advisor-agent" in line and "pattern scan" in line:
            # Parse interval from cron expression
            parts = line.split()
            if len(parts) >= 5 and parts[0].startswith("*/"):
                interval = int(parts[0].replace("*/", ""))
                return {
                    "interval_minutes": interval,
                    "market_hours_only": True,
                    "plist_path": "crontab",
                    "active": True,
                    "last_run": None,
                }
    return None


def pause_scan_schedule() -> bool:
    """Pause the schedule without deleting it.

    Returns:
        True if state changed (was active, now paused).
    """
    if platform.system() == "Darwin":
        if not PLIST_PATH.exists():
            return False
        result = subprocess.run(
            ["launchctl", "unload", str(PLIST_PATH)],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    return False


def resume_scan_schedule() -> bool:
    """Resume a paused schedule.

    Returns:
        True if state changed (was paused, now active).
    """
    if platform.system() == "Darwin":
        if not PLIST_PATH.exists():
            return False
        result = subprocess.run(
            ["launchctl", "load", str(PLIST_PATH)],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    return False


def remove_scan_schedule() -> bool:
    """Remove the scan schedule entirely.

    Returns:
        True if removed.
    """
    if platform.system() == "Darwin":
        if not PLIST_PATH.exists():
            return False
        subprocess.run(
            ["launchctl", "unload", str(PLIST_PATH)],
            capture_output=True,
        )
        PLIST_PATH.unlink(missing_ok=True)
        return True

    elif platform.system() == "Linux":
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode != 0:
            return False
        lines = [
            l
            for l in result.stdout.strip().split("\n")
            if l and "advisor-agent" not in l and "pattern scan" not in l
        ]
        new_crontab = "\n".join(lines) + "\n" if lines else ""
        subprocess.run(["crontab", "-"], input=new_crontab, capture_output=True, text=True)
        return True

    return False
