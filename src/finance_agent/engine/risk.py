"""Risk control checks and settings management."""

from __future__ import annotations

import logging
import sqlite3

from finance_agent.audit.logger import AuditLogger

logger = logging.getLogger(__name__)


def check_position_size(
    proposal: dict,
    account_summary: dict,
    risk_settings: dict,
) -> dict:
    """Check if proposal exceeds maximum position size."""
    equity = float(account_summary.get("equity", 0))
    max_pct = float(risk_settings.get("max_position_pct", 0.10))
    max_dollars = equity * max_pct

    estimated_cost = float(proposal.get("estimated_cost", 0))
    actual_pct = (estimated_cost / equity * 100) if equity > 0 else 100

    passed = estimated_cost <= max_dollars
    return {
        "rule_name": "position_size",
        "passed": passed,
        "limit_value": f"{max_pct:.0%} (${max_dollars:,.2f})",
        "actual_value": f"${estimated_cost:,.2f} ({actual_pct:.1f}%)",
        "details": (
            f"${estimated_cost:,.2f} = {actual_pct:.1f}% of portfolio"
            + ("" if passed else f" > {max_pct:.0%} cap")
        ),
    }


def check_daily_loss(
    daily_pnl: dict,
    account_summary: dict,
    risk_settings: dict,
) -> dict:
    """Check if daily loss limit has been reached."""
    equity = float(account_summary.get("equity", 0))
    max_pct = float(risk_settings.get("max_daily_loss_pct", 0.05))
    max_loss = equity * max_pct

    total_change = float(daily_pnl.get("total_change", 0))
    # Loss is negative, so check if loss exceeds limit
    actual_loss = abs(min(total_change, 0))
    actual_pct = (actual_loss / equity * 100) if equity > 0 else 0

    passed = actual_loss < max_loss
    return {
        "rule_name": "daily_loss",
        "passed": passed,
        "limit_value": f"{max_pct:.0%} (${max_loss:,.2f})",
        "actual_value": f"${actual_loss:,.2f} ({actual_pct:.1f}%)",
        "details": f"{actual_pct:.1f}% loss" + ("" if passed else f" >= {max_pct:.0%} limit"),
    }


def check_trade_count(
    daily_order_count: int,
    risk_settings: dict,
) -> dict:
    """Check if maximum daily trade count has been reached."""
    max_trades = int(risk_settings.get("max_trades_per_day", 20))
    passed = daily_order_count < max_trades
    return {
        "rule_name": "trade_count",
        "passed": passed,
        "limit_value": str(max_trades),
        "actual_value": str(daily_order_count),
        "details": f"{daily_order_count} today" + ("" if passed else f" >= {max_trades} limit"),
    }


def check_concentration(
    proposal: dict,
    positions: list[dict],
    risk_settings: dict,
) -> dict:
    """Check if adding this position exceeds concentration limits."""
    max_per_symbol = int(risk_settings.get("max_positions_per_symbol", 2))
    ticker = str(proposal.get("ticker", ""))

    # Count existing positions in the same symbol
    existing_count = sum(
        1 for p in positions if str(p.get("symbol", "")) == ticker
    )

    # For buy proposals, check if adding one more exceeds the limit
    direction = str(proposal.get("direction", "buy"))
    if direction == "buy":
        passed = existing_count < max_per_symbol
    else:
        # Selling reduces concentration, always passes
        passed = True

    return {
        "rule_name": "concentration",
        "passed": passed,
        "limit_value": str(max_per_symbol),
        "actual_value": f"{existing_count} existing {ticker}",
        "details": (
            f"{existing_count} existing {ticker} positions"
            + ("" if passed else f" >= {max_per_symbol} limit")
        ),
    }


def adjust_position_for_risk(
    proposal: dict,
    account_summary: dict,
    risk_settings: dict,
) -> dict:
    """Reduce quantity to fit within position size limit. Returns adjusted proposal."""
    equity = float(account_summary.get("equity", 0))
    max_pct = float(risk_settings.get("max_position_pct", 0.10))
    max_dollars = equity * max_pct
    limit_price = float(proposal.get("limit_price", 1))

    if limit_price <= 0:
        return proposal

    max_qty = int(max_dollars / limit_price)
    if max_qty < 1:
        max_qty = 1

    current_qty = int(proposal.get("quantity", 1))
    if current_qty > max_qty:
        proposal = dict(proposal)  # Don't mutate original
        proposal["quantity"] = max_qty
        proposal["estimated_cost"] = round(max_qty * limit_price, 2)

    return proposal


def run_all_risk_checks(
    conn: sqlite3.Connection,
    proposal: dict,
    account_summary: dict,
    positions: list[dict],
    daily_order_count: int,
    daily_pnl: dict,
    risk_settings: dict,
    audit: AuditLogger | None = None,
) -> list[dict]:
    """Run all 4 risk checks and save results. Returns list of check results.

    If position size fails, attempt to adjust quantity before marking as rejected.
    """
    results = []

    # Check position size
    pos_check = check_position_size(proposal, account_summary, risk_settings)
    if not pos_check["passed"]:
        # Try to adjust
        adjusted = adjust_position_for_risk(proposal, account_summary, risk_settings)
        if adjusted["quantity"] != proposal["quantity"]:
            # Re-check with adjusted quantity
            proposal_id = proposal.get("id")
            if proposal_id:
                conn.execute(
                    "UPDATE trade_proposal SET quantity = ?, estimated_cost = ? WHERE id = ?",
                    (adjusted["quantity"], adjusted["estimated_cost"], proposal_id),
                )
                conn.commit()
            proposal.update(adjusted)
            pos_check = check_position_size(proposal, account_summary, risk_settings)
            pos_check["details"] += f" → ADJUSTED qty to {adjusted['quantity']}"
    results.append(pos_check)

    # Check daily loss
    results.append(check_daily_loss(daily_pnl, account_summary, risk_settings))

    # Check trade count
    results.append(check_trade_count(daily_order_count, risk_settings))

    # Check concentration
    results.append(check_concentration(proposal, positions, risk_settings))

    # Save results to DB
    proposal_id = proposal.get("id")
    any_failed = any(not r["passed"] for r in results)

    if proposal_id:
        for r in results:
            conn.execute(
                "INSERT INTO risk_check_result "
                "(proposal_id, rule_name, passed, limit_value, actual_value, details) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    proposal_id,
                    r["rule_name"],
                    1 if r["passed"] else 0,
                    r["limit_value"],
                    r["actual_value"],
                    r.get("details", ""),
                ),
            )

        if any_failed:
            failed_rules = [r["rule_name"] for r in results if not r["passed"]]
            conn.execute(
                "UPDATE trade_proposal SET risk_passed = 0, status = 'rejected', "
                "decision_reason = ? WHERE id = ?",
                (", ".join(failed_rules), proposal_id),
            )

        conn.commit()

        if audit:
            audit.log("risk_checks_evaluated", "engine", {
                "proposal_id": proposal_id,
                "ticker": proposal.get("ticker"),
                "all_passed": not any_failed,
                "results": [
                    {"rule": r["rule_name"], "passed": r["passed"]}
                    for r in results
                ],
            })

    return results
