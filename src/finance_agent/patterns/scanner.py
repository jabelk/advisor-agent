"""Pattern scanner: evaluate paper_trading patterns against live market data."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import UTC, date, datetime, timedelta

from finance_agent.audit.logger import AuditLogger
from finance_agent.patterns.alert_storage import (
    create_alert,
    update_alert_auto_execute,
)
from finance_agent.patterns.models import RuleSet

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def evaluate_triggers(
    rule_set: RuleSet,
    bars: list[dict],
) -> dict:
    """Evaluate a pattern's trigger conditions against recent bars.

    Requires at least 2 bars. Evaluates the latest bar against the previous bar.

    Returns dict with 'triggered' bool plus details if triggered.
    """
    if len(bars) < 2:
        return {"triggered": False}

    latest = bars[-1]
    previous = bars[-2]

    conditions_met: list[str] = []
    price_change_pct = 0.0
    volume_multiple = 0.0

    for condition in rule_set.trigger_conditions:
        if condition.field == "price_change_pct":
            if previous["close"] == 0:
                return {"triggered": False}
            price_change_pct = ((latest["close"] - previous["close"]) / previous["close"]) * 100
            threshold = float(condition.value)

            if condition.operator == "gte" and price_change_pct < threshold:
                return {"triggered": False}
            elif condition.operator == "lte" and price_change_pct > threshold:
                return {"triggered": False}
            conditions_met.append(f"price_change_pct {condition.operator} {threshold}")

        elif condition.field == "volume_spike":
            # Compare to average volume over prior bars (up to 20)
            lookback_bars = bars[:-1]  # all bars except latest
            if len(lookback_bars) > 20:
                lookback_bars = lookback_bars[-20:]
            avg_vol = sum(b["volume"] for b in lookback_bars) / max(1, len(lookback_bars))
            if avg_vol == 0:
                return {"triggered": False}
            volume_multiple = latest["volume"] / avg_vol
            threshold = float(condition.value)

            if condition.operator == "gte" and volume_multiple < threshold:
                return {"triggered": False}
            conditions_met.append(f"volume_spike {condition.operator} {threshold}")

        elif condition.field in ("sector", "news_sentiment"):
            # Skip non-quantitative conditions in scanner
            pass

    if not conditions_met:
        return {"triggered": False}

    return {
        "triggered": True,
        "price_change_pct": round(price_change_pct, 2),
        "volume_multiple": round(volume_multiple, 2),
        "conditions_met": conditions_met,
        "latest_price": latest["close"],
        "previous_close": previous["close"],
    }


def _get_pattern_tickers(conn: sqlite3.Connection, pattern: dict) -> list[str]:
    """Determine tickers to scan for a pattern.

    Uses the watchlist if no tickers are explicitly associated with the pattern.
    """
    # Check if pattern has associated paper trades with specific tickers
    rows = conn.execute(
        "SELECT DISTINCT ticker FROM paper_trade WHERE pattern_id = ?",
        (pattern["id"],),
    ).fetchall()
    if rows:
        return [row["ticker"] for row in rows]

    # Fall back to watchlist
    try:
        rows = conn.execute(
            "SELECT ticker FROM company WHERE active = 1 ORDER BY ticker"
        ).fetchall()
        return [row["ticker"] for row in rows]
    except sqlite3.OperationalError:
        return []


def _get_latest_win_rate(conn: sqlite3.Connection, pattern_id: int) -> float | None:
    """Get win rate from the most recent backtest for this pattern."""
    row = conn.execute(
        "SELECT win_count, trade_count FROM backtest_result "
        "WHERE pattern_id = ? ORDER BY created_at DESC LIMIT 1",
        (pattern_id,),
    ).fetchone()
    if row and row["trade_count"] > 0:
        return round(row["win_count"] / row["trade_count"], 4)
    return None


def run_scan(
    conn: sqlite3.Connection,
    api_key: str,
    secret_key: str,
    cooldown_hours: int = 24,
    audit: AuditLogger | None = None,
) -> dict:
    """Run the pattern scanner: evaluate all paper_trading patterns against recent market data.

    Returns ScanResult dict with scan details, alerts generated, and auto-execution info.
    """
    from finance_agent.patterns.market_data import fetch_and_cache_bars
    from finance_agent.patterns.storage import list_patterns

    scan_timestamp = _now()
    patterns = list_patterns(conn, status="paper_trading")

    alerts: list[dict] = []
    tickers_scanned: set[str] = set()
    auto_executions = 0
    auto_executions_blocked = 0

    for pattern in patterns:
        rule_set = RuleSet.model_validate_json(pattern["rule_set_json"])
        tickers = _get_pattern_tickers(conn, pattern)
        win_rate = _get_latest_win_rate(conn, pattern["id"])

        for ticker in tickers:
            tickers_scanned.add(ticker)

            # Fetch last 10 trading days of bars
            end_date = date.today().isoformat()
            start_date = (date.today() - timedelta(days=15)).isoformat()
            try:
                bars = fetch_and_cache_bars(
                    conn, ticker, start_date, end_date, "day", api_key, secret_key,
                )
            except Exception as e:
                logger.warning("Failed to fetch bars for %s: %s", ticker, e)
                continue

            if not bars or len(bars) < 2:
                continue

            # Evaluate triggers
            result = evaluate_triggers(rule_set, bars)
            if not result["triggered"]:
                continue

            # Determine trigger date from latest bar
            trigger_date = bars[-1]["bar_timestamp"][:10]

            # Create alert (dedup handled by UNIQUE index)
            alert_id = create_alert(
                conn=conn,
                pattern_id=pattern["id"],
                pattern_name=pattern["name"],
                ticker=ticker,
                trigger_date=trigger_date,
                trigger_details=result,
                recommended_action=rule_set.action.action_type,
                pattern_win_rate=win_rate,
            )

            if alert_id == 0:
                # Duplicate within cooldown — skip
                continue

            alert_record = {
                "id": alert_id,
                "pattern_id": pattern["id"],
                "pattern_name": pattern["name"],
                "ticker": ticker,
                "trigger_date": trigger_date,
                "trigger_details": result,
                "recommended_action": rule_set.action.action_type,
                "pattern_win_rate": win_rate,
                "status": "new",
                "auto_executed": False,
                "auto_execute_result": None,
            }

            # Auto-execution check
            if pattern.get("auto_execute"):
                exec_result = _try_auto_execute(
                    conn, audit, pattern, ticker, rule_set, alert_id,
                )
                if exec_result.get("executed"):
                    auto_executions += 1
                    alert_record["auto_executed"] = True
                    alert_record["auto_execute_result"] = exec_result
                elif exec_result.get("blocked_reason"):
                    auto_executions_blocked += 1
                    alert_record["auto_execute_result"] = exec_result

            alerts.append(alert_record)

    scan_result = {
        "scan_timestamp": scan_timestamp,
        "patterns_evaluated": len(patterns),
        "tickers_scanned": len(tickers_scanned),
        "alerts_generated": len(alerts),
        "alerts": alerts,
        "auto_executions": auto_executions,
        "auto_executions_blocked": auto_executions_blocked,
    }

    # Audit log the scan
    if audit:
        audit.log("scanner_run", "pattern_scanner", {
            "patterns_evaluated": len(patterns),
            "tickers_scanned": len(tickers_scanned),
            "alerts_generated": len(alerts),
            "auto_executions": auto_executions,
            "auto_executions_blocked": auto_executions_blocked,
        })

    return scan_result


def _try_auto_execute(
    conn: sqlite3.Connection,
    audit: AuditLogger | None,
    pattern: dict,
    ticker: str,
    rule_set: RuleSet,
    alert_id: int,
) -> dict:
    """Attempt auto-execution of a paper trade. Returns result dict."""
    from finance_agent.safety.guards import get_kill_switch, get_risk_settings
    from finance_agent.patterns.storage import create_paper_trade

    # Safety check 1: kill switch
    if get_kill_switch(conn):
        reason = "kill_switch_active"
        result = {"blocked_reason": reason}
        update_alert_auto_execute(conn, alert_id, result)
        if audit:
            audit.log("auto_execute_blocked", "pattern_scanner", {
                "pattern_id": pattern["id"],
                "ticker": ticker,
                "alert_id": alert_id,
                "reason": reason,
            })
        return result

    # Safety check 2: daily trade limit
    risk_settings = get_risk_settings(conn)
    max_trades = int(risk_settings.get("max_trades_per_day", 20))
    today = date.today().isoformat()
    today_count_row = conn.execute(
        "SELECT COUNT(*) as cnt FROM paper_trade WHERE proposed_at >= ? AND proposed_at < date(?, '+1 day')",
        (today, today),
    ).fetchone()
    today_count = today_count_row["cnt"] if today_count_row else 0

    if today_count >= max_trades:
        reason = "daily_trade_limit_reached"
        result = {"blocked_reason": reason, "daily_count": today_count, "limit": max_trades}
        update_alert_auto_execute(conn, alert_id, result)
        if audit:
            audit.log("auto_execute_blocked", "pattern_scanner", {
                "pattern_id": pattern["id"],
                "ticker": ticker,
                "alert_id": alert_id,
                "reason": reason,
            })
        return result

    # Execute: create paper trade
    action_type = rule_set.action.action_type
    direction = "buy" if action_type.startswith("buy") else "sell"

    try:
        trade_id = create_paper_trade(
            conn=conn,
            pattern_id=pattern["id"],
            ticker=ticker,
            direction=direction,
            action_type=action_type,
            quantity=1,
        )
        result = {"executed": True, "trade_id": trade_id}
        update_alert_auto_execute(conn, alert_id, result)
        if audit:
            audit.log("auto_execute_success", "pattern_scanner", {
                "pattern_id": pattern["id"],
                "ticker": ticker,
                "alert_id": alert_id,
                "trade_id": trade_id,
            })
        return result
    except Exception as e:
        result = {"error": str(e)}
        update_alert_auto_execute(conn, alert_id, result)
        if audit:
            audit.log("auto_execute_error", "pattern_scanner", {
                "pattern_id": pattern["id"],
                "ticker": ticker,
                "alert_id": alert_id,
                "error": str(e),
            })
        return result
