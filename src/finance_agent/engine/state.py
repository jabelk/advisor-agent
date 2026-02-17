"""Engine state persistence: kill switch and risk settings in SQLite."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime

from finance_agent.audit.logger import AuditLogger

logger = logging.getLogger(__name__)

# Default risk settings (must match migration 004)
DEFAULT_RISK_SETTINGS = {
    "max_position_pct": 0.10,
    "max_daily_loss_pct": 0.05,
    "max_trades_per_day": 20,
    "max_positions_per_symbol": 2,
    "min_confidence_threshold": 0.45,
    "max_signal_age_days": 14,
    "min_signal_count": 3,
    "data_staleness_hours": 24,
}

# Validation ranges for risk settings
RISK_SETTING_RANGES: dict[str, tuple[float, float]] = {
    "max_position_pct": (0.01, 0.50),
    "max_daily_loss_pct": (0.01, 0.20),
    "max_trades_per_day": (1, 100),
    "max_positions_per_symbol": (1, 10),
    "min_confidence_threshold": (0.1, 0.9),
    "max_signal_age_days": (1, 90),
    "min_signal_count": (1, 20),
    "data_staleness_hours": (1, 168),
}


def get_kill_switch(conn: sqlite3.Connection) -> bool:
    """Return True if kill switch is active."""
    row = conn.execute(
        "SELECT value FROM engine_state WHERE key = 'kill_switch'"
    ).fetchone()
    if not row:
        return False
    state = json.loads(row["value"])
    return bool(state.get("active", False))


def set_kill_switch(
    conn: sqlite3.Connection,
    active: bool,
    toggled_by: str = "operator",
    audit: AuditLogger | None = None,
) -> bool:
    """Toggle kill switch state. Returns True if state changed."""
    current = get_kill_switch(conn)
    if current == active:
        return False

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = json.dumps({
        "active": active,
        "toggled_at": now,
        "toggled_by": toggled_by,
    })
    conn.execute(
        "UPDATE engine_state SET value = ?, updated_at = ?, updated_by = ? "
        "WHERE key = 'kill_switch'",
        (state, now, toggled_by),
    )
    conn.commit()

    action = "activated" if active else "deactivated"
    logger.info("Kill switch %s by %s", action, toggled_by)

    if audit:
        audit.log("kill_switch_toggle", "engine", {
            "active": active,
            "toggled_by": toggled_by,
        })

    return True


def get_risk_settings(conn: sqlite3.Connection) -> dict[str, float | int]:
    """Return current risk settings from engine_state table."""
    row = conn.execute(
        "SELECT value FROM engine_state WHERE key = 'risk_settings'"
    ).fetchone()
    if not row:
        return dict(DEFAULT_RISK_SETTINGS)
    return json.loads(row["value"])


def update_risk_setting(
    conn: sqlite3.Connection,
    key: str,
    value: float | int,
    updated_by: str = "operator",
    audit: AuditLogger | None = None,
) -> tuple[float | int, float | int]:
    """Update a single risk setting. Returns (old_value, new_value).

    Raises ValueError if key is unknown or value is out of valid range.
    """
    if key not in RISK_SETTING_RANGES:
        valid_keys = ", ".join(sorted(RISK_SETTING_RANGES.keys()))
        raise ValueError(f"Unknown risk setting: '{key}'. Valid keys: {valid_keys}")

    min_val, max_val = RISK_SETTING_RANGES[key]
    if value < min_val or value > max_val:
        raise ValueError(
            f"Value {value} for '{key}' is out of range [{min_val}, {max_val}]"
        )

    settings = get_risk_settings(conn)
    old_value = settings.get(key, DEFAULT_RISK_SETTINGS.get(key, 0))

    # Use int for integer-type settings
    if key in ("max_trades_per_day", "max_positions_per_symbol",
               "max_signal_age_days", "data_staleness_hours", "min_signal_count"):
        value = int(value)

    settings[key] = value
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "UPDATE engine_state SET value = ?, updated_at = ?, updated_by = ? "
        "WHERE key = 'risk_settings'",
        (json.dumps(settings), now, updated_by),
    )
    conn.commit()

    logger.info("Risk setting %s: %s → %s (by %s)", key, old_value, value, updated_by)

    if audit:
        audit.log("risk_setting_update", "engine", {
            "key": key,
            "old_value": old_value,
            "new_value": value,
            "updated_by": updated_by,
        })

    return (old_value, value)
