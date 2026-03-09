"""Pattern Lab storage: CRUD operations for patterns, backtests, and paper trades."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from finance_agent.patterns.models import (
    BacktestReport,
    BacktestTrade,
    CoveredCallCycle,
    RegimePeriod,
)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Pattern CRUD
# ---------------------------------------------------------------------------


def create_pattern(
    conn: sqlite3.Connection,
    name: str,
    description: str,
    rule_set_json: str,
) -> int:
    """Create a new pattern in draft status. Returns the pattern ID."""
    now = _now()
    cursor = conn.execute(
        "INSERT INTO trading_pattern (name, description, rule_set_json, status, created_at, updated_at) "
        "VALUES (?, ?, ?, 'draft', ?, ?)",
        (name, description, rule_set_json, now, now),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def get_pattern(conn: sqlite3.Connection, pattern_id: int) -> dict | None:
    """Get a pattern by ID. Returns None if not found."""
    row = conn.execute("SELECT * FROM trading_pattern WHERE id = ?", (pattern_id,)).fetchone()
    if not row:
        return None
    return dict(row)


def list_patterns(
    conn: sqlite3.Connection,
    status: str | None = None,
) -> list[dict]:
    """List patterns, optionally filtered by status."""
    if status:
        rows = conn.execute(
            "SELECT * FROM trading_pattern WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM trading_pattern ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def update_pattern_status(
    conn: sqlite3.Connection,
    pattern_id: int,
    new_status: str,
) -> bool:
    """Update a pattern's status. Returns True if updated."""
    now = _now()
    retired_at = now if new_status == "retired" else None
    cursor = conn.execute(
        "UPDATE trading_pattern SET status = ?, updated_at = ?, retired_at = COALESCE(?, retired_at) "
        "WHERE id = ?",
        (new_status, now, retired_at, pattern_id),
    )
    conn.commit()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Backtest results
# ---------------------------------------------------------------------------


def save_backtest_result(
    conn: sqlite3.Connection,
    report: BacktestReport,
) -> int:
    """Save a backtest result and its trades. Returns the backtest_result ID."""
    regime_json = json.dumps([r.model_dump() for r in report.regimes]) if report.regimes else None

    cursor = conn.execute(
        "INSERT INTO backtest_result "
        "(pattern_id, date_range_start, date_range_end, trigger_count, trade_count, "
        "win_count, total_return_pct, avg_return_pct, max_drawdown_pct, sharpe_ratio, "
        "regime_analysis_json, sample_size_warning) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            report.pattern_id,
            report.date_range_start,
            report.date_range_end,
            report.trigger_count,
            report.trade_count,
            report.win_count,
            report.total_return_pct,
            report.avg_return_pct,
            report.max_drawdown_pct,
            report.sharpe_ratio,
            regime_json,
            1 if report.sample_size_warning else 0,
        ),
    )
    backtest_id = cursor.lastrowid

    # Save individual trades
    for trade in report.trades:
        option_json = json.dumps(trade.option_details) if trade.option_details else None
        conn.execute(
            "INSERT INTO backtest_trade "
            "(backtest_id, ticker, trigger_date, entry_date, entry_price, "
            "exit_date, exit_price, return_pct, action_type, option_details_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                backtest_id,
                trade.ticker,
                trade.trigger_date,
                trade.entry_date,
                trade.entry_price,
                trade.exit_date,
                trade.exit_price,
                trade.return_pct,
                trade.action_type,
                option_json,
            ),
        )

    # Update pattern status to backtested (if currently draft)
    conn.execute(
        "UPDATE trading_pattern SET status = 'backtested', updated_at = ? "
        "WHERE id = ? AND status = 'draft'",
        (_now(), report.pattern_id),
    )
    conn.commit()
    return backtest_id  # type: ignore[return-value]


def get_backtest_results(
    conn: sqlite3.Connection,
    pattern_id: int,
) -> list[dict]:
    """Get all backtest results for a pattern."""
    rows = conn.execute(
        "SELECT * FROM backtest_result WHERE pattern_id = ? ORDER BY created_at DESC",
        (pattern_id,),
    ).fetchall()
    results = []
    for row in rows:
        result = dict(row)
        if result.get("regime_analysis_json"):
            result["regimes"] = json.loads(result["regime_analysis_json"])
        else:
            result["regimes"] = []
        results.append(result)
    return results


def get_backtest_trades(
    conn: sqlite3.Connection,
    backtest_id: int,
) -> list[dict]:
    """Get individual trades for a backtest result."""
    rows = conn.execute(
        "SELECT * FROM backtest_trade WHERE backtest_id = ? ORDER BY trigger_date",
        (backtest_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Paper trades
# ---------------------------------------------------------------------------


def create_paper_trade(
    conn: sqlite3.Connection,
    pattern_id: int,
    ticker: str,
    direction: str,
    action_type: str,
    quantity: int,
    option_details: dict | None = None,
) -> int:
    """Create a proposed paper trade. Returns the trade ID."""
    option_json = json.dumps(option_details) if option_details else None
    cursor = conn.execute(
        "INSERT INTO paper_trade "
        "(pattern_id, ticker, direction, action_type, quantity, status, option_details_json) "
        "VALUES (?, ?, ?, ?, ?, 'proposed', ?)",
        (pattern_id, ticker, direction, action_type, quantity, option_json),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def update_paper_trade_executed(
    conn: sqlite3.Connection,
    trade_id: int,
    alpaca_order_id: str,
    entry_price: float,
) -> None:
    """Mark a paper trade as executed."""
    now = _now()
    conn.execute(
        "UPDATE paper_trade SET status = 'executed', alpaca_order_id = ?, "
        "entry_price = ?, executed_at = ? WHERE id = ?",
        (alpaca_order_id, entry_price, now, trade_id),
    )
    conn.commit()


def update_paper_trade_closed(
    conn: sqlite3.Connection,
    trade_id: int,
    exit_price: float,
    pnl: float,
) -> None:
    """Mark a paper trade as closed with final P&L."""
    now = _now()
    conn.execute(
        "UPDATE paper_trade SET status = 'closed', exit_price = ?, pnl = ?, closed_at = ? "
        "WHERE id = ?",
        (exit_price, pnl, now, trade_id),
    )
    conn.commit()


def get_paper_trades(
    conn: sqlite3.Connection,
    pattern_id: int,
    status: str | None = None,
) -> list[dict]:
    """Get paper trades for a pattern, optionally filtered by status."""
    if status:
        rows = conn.execute(
            "SELECT * FROM paper_trade WHERE pattern_id = ? AND status = ? ORDER BY proposed_at DESC",
            (pattern_id, status),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM paper_trade WHERE pattern_id = ? ORDER BY proposed_at DESC",
            (pattern_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_paper_trade_summary(
    conn: sqlite3.Connection,
    pattern_id: int,
) -> dict:
    """Get aggregate paper trade performance for a pattern."""
    row = conn.execute(
        "SELECT COUNT(*) as total, "
        "SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins, "
        "SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses, "
        "SUM(pnl) as total_pnl, "
        "AVG(pnl) as avg_pnl "
        "FROM paper_trade WHERE pattern_id = ? AND status = 'closed'",
        (pattern_id,),
    ).fetchone()

    total = row["total"] or 0
    return {
        "total_trades": total,
        "wins": row["wins"] or 0,
        "losses": row["losses"] or 0,
        "win_rate": (row["wins"] or 0) / total if total > 0 else 0.0,
        "total_pnl": row["total_pnl"] or 0.0,
        "avg_pnl": row["avg_pnl"] or 0.0,
        "open_trades": conn.execute(
            "SELECT COUNT(*) as cnt FROM paper_trade WHERE pattern_id = ? AND status = 'executed'",
            (pattern_id,),
        ).fetchone()["cnt"],
    }


# ---------------------------------------------------------------------------
# Covered call cycles
# ---------------------------------------------------------------------------


def save_covered_call_cycles(
    conn: sqlite3.Connection,
    cycles: list[CoveredCallCycle],
    pattern_id: int,
    backtest_result_id: int | None = None,
) -> None:
    """Save covered call cycles to the database."""
    for cycle in cycles:
        conn.execute(
            "INSERT INTO covered_call_cycle "
            "(pattern_id, backtest_result_id, ticker, cycle_number, stock_entry_price, "
            "call_strike, call_premium, call_expiration_date, cycle_start_date, cycle_end_date, "
            "stock_price_at_exit, outcome, premium_return_pct, total_return_pct, "
            "capped_upside_pct, historical_volatility) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                pattern_id,
                backtest_result_id,
                cycle.ticker,
                cycle.cycle_number,
                cycle.stock_entry_price,
                cycle.call_strike,
                cycle.call_premium,
                cycle.call_expiration_date,
                cycle.cycle_start_date,
                cycle.cycle_end_date,
                cycle.stock_price_at_exit,
                cycle.outcome,
                cycle.premium_return_pct,
                cycle.total_return_pct,
                cycle.capped_upside_pct,
                cycle.historical_volatility,
            ),
        )
    conn.commit()


def get_covered_call_cycles(
    conn: sqlite3.Connection,
    pattern_id: int,
    backtest_result_id: int | None = None,
) -> list[dict]:
    """Get covered call cycles for a pattern."""
    if backtest_result_id:
        rows = conn.execute(
            "SELECT * FROM covered_call_cycle WHERE pattern_id = ? AND backtest_result_id = ? "
            "ORDER BY cycle_number",
            (pattern_id, backtest_result_id),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM covered_call_cycle WHERE pattern_id = ? ORDER BY cycle_number",
            (pattern_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_covered_call_summary(
    conn: sqlite3.Connection,
    pattern_id: int,
) -> dict:
    """Get aggregate covered call performance for a pattern."""
    row = conn.execute(
        "SELECT "
        "COUNT(*) as cycle_count, "
        "SUM(call_premium) as total_premium, "
        "AVG(call_premium) as avg_premium, "
        "SUM(CASE WHEN outcome = 'assigned' THEN 1 ELSE 0 END) as assignment_count, "
        "SUM(CASE WHEN outcome = 'expired_worthless' THEN 1 ELSE 0 END) as expired_count, "
        "SUM(CASE WHEN outcome = 'rolled' THEN 1 ELSE 0 END) as rolled_count, "
        "SUM(CASE WHEN outcome = 'closed_early' THEN 1 ELSE 0 END) as closed_early_count, "
        "AVG(premium_return_pct) as avg_premium_return_pct, "
        "SUM(capped_upside_pct) as total_capped_upside_pct "
        "FROM covered_call_cycle WHERE pattern_id = ? AND outcome IS NOT NULL",
        (pattern_id,),
    ).fetchone()

    total = row["cycle_count"] or 0
    return {
        "cycle_count": total,
        "total_premium": row["total_premium"] or 0.0,
        "avg_premium": row["avg_premium"] or 0.0,
        "assignment_count": row["assignment_count"] or 0,
        "assignment_frequency_pct": (row["assignment_count"] or 0) / total * 100
        if total > 0
        else 0.0,
        "expired_count": row["expired_count"] or 0,
        "rolled_count": row["rolled_count"] or 0,
        "closed_early_count": row["closed_early_count"] or 0,
        "avg_premium_return_pct": row["avg_premium_return_pct"] or 0.0,
        "total_capped_upside_pct": row["total_capped_upside_pct"] or 0.0,
    }
