"""Dashboard aggregation and performance comparison queries.

Provides cross-pattern aggregation for the portfolio dashboard and
side-by-side backtest vs. paper trade performance comparisons.
All functions are read-only — no writes to any table.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta


def get_dashboard_data(conn: sqlite3.Connection) -> dict:
    """Aggregate all dashboard data in a single call.

    Returns a DashboardSummary dict with:
    - patterns: total count and breakdown by status
    - paper_trades: aggregate P&L across all patterns
    - alerts: last 7 days count by status
    - active_patterns: per-pattern summaries for paper_trading patterns
    """
    conn.row_factory = sqlite3.Row

    # --- Pattern counts by status ---
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM trading_pattern GROUP BY status"
    ).fetchall()
    by_status = {row["status"]: row["cnt"] for row in rows}
    total_patterns = sum(by_status.values())

    # --- Aggregate paper trade P&L (closed trades) ---
    closed_row = conn.execute(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
            COALESCE(SUM(pnl), 0.0) as total_pnl,
            COALESCE(AVG(pnl), 0.0) as avg_pnl
        FROM paper_trade
        WHERE status = 'closed'
        """
    ).fetchone()

    closed_trades = closed_row["total"] if closed_row["total"] else 0
    wins = closed_row["wins"] if closed_row["wins"] else 0
    losses = closed_row["losses"] if closed_row["losses"] else 0
    total_pnl = closed_row["total_pnl"] if closed_row["total_pnl"] else 0.0
    avg_pnl = closed_row["avg_pnl"] if closed_row["avg_pnl"] else 0.0
    win_rate = (wins / closed_trades) if closed_trades > 0 else 0.0

    # --- Open trades count ---
    open_row = conn.execute(
        "SELECT COUNT(*) as cnt FROM paper_trade WHERE status = 'executed'"
    ).fetchone()
    open_trades = open_row["cnt"] if open_row["cnt"] else 0

    # --- Alert counts (last 7 days) ---
    seven_days_ago = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    alert_rows = conn.execute(
        """
        SELECT status, COUNT(*) as cnt
        FROM pattern_alert
        WHERE created_at >= ?
        GROUP BY status
        """,
        (seven_days_ago,),
    ).fetchall()
    alert_by_status = {row["status"]: row["cnt"] for row in alert_rows}
    alert_total_7d = sum(alert_by_status.values())

    # --- Per-pattern summaries for paper_trading patterns ---
    active_patterns = []
    pt_patterns = conn.execute(
        "SELECT id, name, auto_execute FROM trading_pattern WHERE status = 'paper_trading'"
    ).fetchall()

    for pat in pt_patterns:
        pid = pat["id"]
        pname = pat["name"]

        # Most recent backtest
        bt_row = conn.execute(
            """
            SELECT win_count, trade_count, avg_return_pct
            FROM backtest_result
            WHERE pattern_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (pid,),
        ).fetchone()

        bt_win_rate = None
        bt_avg_return = None
        if bt_row and bt_row["trade_count"] > 0:
            bt_win_rate = bt_row["win_count"] / bt_row["trade_count"]
            bt_avg_return = bt_row["avg_return_pct"]

        # Paper trade stats (closed)
        pt_closed = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                COALESCE(SUM(pnl), 0.0) as total_pnl
            FROM paper_trade
            WHERE pattern_id = ? AND status = 'closed'
            """,
            (pid,),
        ).fetchone()

        pt_count = pt_closed["total"] if pt_closed["total"] else 0
        pt_wins = pt_closed["wins"] if pt_closed["wins"] else 0
        pt_pnl = pt_closed["total_pnl"] if pt_closed["total_pnl"] else 0.0
        pt_win_rate = (pt_wins / pt_count) if pt_count > 0 else None

        # Open trades for this pattern
        pt_open = conn.execute(
            "SELECT COUNT(*) as cnt FROM paper_trade WHERE pattern_id = ? AND status = 'executed'",
            (pid,),
        ).fetchone()
        pt_open_count = pt_open["cnt"] if pt_open["cnt"] else 0

        # Alerts in last 7 days for this pattern
        pat_alert_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM pattern_alert WHERE pattern_id = ? AND created_at >= ?",
            (pid, seven_days_ago),
        ).fetchone()
        pat_alert_count = pat_alert_row["cnt"] if pat_alert_row["cnt"] else 0

        # Divergence warning
        divergence_warning = False
        if bt_win_rate is not None and pt_win_rate is not None:
            divergence_warning = abs(bt_win_rate - pt_win_rate) > 0.10

        active_patterns.append({
            "pattern_id": pid,
            "pattern_name": pname,
            "backtest_win_rate": bt_win_rate,
            "backtest_avg_return": bt_avg_return,
            "paper_trade_win_rate": pt_win_rate,
            "paper_trade_count": pt_count,
            "paper_trade_pnl": pt_pnl,
            "open_trades": pt_open_count,
            "alert_count_7d": pat_alert_count,
            "auto_execute": bool(pat["auto_execute"]),
            "divergence_warning": divergence_warning,
        })

    return {
        "patterns": {
            "total": total_patterns,
            "by_status": by_status,
        },
        "paper_trades": {
            "total_trades": closed_trades + open_trades,
            "closed_trades": closed_trades,
            "open_trades": open_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
        },
        "alerts": {
            "last_7_days": alert_total_7d,
            "by_status": alert_by_status,
        },
        "active_patterns": active_patterns,
    }


def format_dashboard(data: dict) -> str:
    """Format DashboardSummary dict into CLI display output.

    Returns a formatted string matching the quickstart.md Scenario 1 output.
    """
    lines: list[str] = []

    # Handle empty state
    if data["patterns"]["total"] == 0:
        lines.append("Portfolio Dashboard")
        lines.append("\u2550" * 19)
        lines.append("")
        lines.append("  No patterns found. Get started with:")
        lines.append("    finance-agent pattern describe \"<your pattern description>\"")
        return "\n".join(lines)

    lines.append("Portfolio Dashboard")
    lines.append("\u2550" * 19)
    lines.append("")

    # Pattern counts
    status_parts = []
    for status in ["draft", "backtested", "paper_trading", "retired"]:
        count = data["patterns"]["by_status"].get(status, 0)
        if count > 0:
            status_parts.append(f"{count} {status}")
    lines.append(f"  Patterns:  {data['patterns']['total']} total ({', '.join(status_parts)})")
    lines.append("")

    # Paper trade summary
    pt = data["paper_trades"]
    if pt["closed_trades"] > 0:
        pnl_str = f"+${pt['total_pnl']:.2f}" if pt["total_pnl"] >= 0 else f"-${abs(pt['total_pnl']):.2f}"
        lines.append("  Paper Trades (all patterns):")
        lines.append(
            f"    Closed: {pt['closed_trades']} trades  |  "
            f"Win rate: {pt['win_rate'] * 100:.1f}%  |  "
            f"P&L: {pnl_str}"
        )
        if pt["open_trades"] > 0:
            lines.append(f"    Open: {pt['open_trades']} trades")
    else:
        lines.append("  Paper Trades: No closed trades yet")
        if pt["open_trades"] > 0:
            lines.append(f"    Open: {pt['open_trades']} trades")
    lines.append("")

    # Alert summary
    alerts = data["alerts"]
    if alerts["last_7_days"] > 0:
        alert_parts = []
        for status in ["new", "acknowledged", "acted_on", "dismissed"]:
            count = alerts["by_status"].get(status, 0)
            if count > 0:
                alert_parts.append(f"{count} {status}")
        lines.append(f"  Alerts (last 7 days):  {alerts['last_7_days']} total ({', '.join(alert_parts)})")
    else:
        lines.append("  Alerts (last 7 days):  0")
    lines.append("")

    # Active patterns table
    active = data["active_patterns"]
    if active:
        lines.append("  Active Patterns:")
        lines.append(f"  {'ID':<5}{'Name':<24}{'BT Win%':<10}{'PT Win%':<10}{'Trades':<9}{'P&L':<11}{'Alerts'}")
        lines.append("  " + "\u2500" * 73)
        for p in active:
            bt_str = f"{p['backtest_win_rate'] * 100:.1f}%" if p["backtest_win_rate"] is not None else "\u2014"
            pt_str = f"{p['paper_trade_win_rate'] * 100:.1f}%" if p["paper_trade_win_rate"] is not None else "\u2014"
            pnl = p["paper_trade_pnl"]
            pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
            alert_str = str(p["alert_count_7d"])
            if p["divergence_warning"]:
                alert_str += " \u26a0\ufe0f"
            lines.append(
                f"  {p['pattern_id']:<5}{p['pattern_name']:<24}{bt_str:<10}{pt_str:<10}"
                f"{p['paper_trade_count']:<9}{pnl_str:<11}{alert_str}"
            )

    return "\n".join(lines)


def get_performance_comparison(
    conn: sqlite3.Connection, pattern_id: int | None = None,
) -> list[dict]:
    """Compare backtest predictions vs paper trade actuals.

    Args:
        conn: Database connection.
        pattern_id: Specific pattern ID. None = all patterns with backtest data.

    Returns:
        List of PerformanceComparison dicts per data-model.md.
    """
    conn.row_factory = sqlite3.Row

    # Get patterns with backtest data
    if pattern_id:
        patterns = conn.execute(
            "SELECT id, name, status, created_at FROM trading_pattern WHERE id = ?",
            (pattern_id,),
        ).fetchall()
    else:
        # All patterns that have at least one backtest result
        patterns = conn.execute(
            """
            SELECT DISTINCT tp.id, tp.name, tp.status, tp.created_at
            FROM trading_pattern tp
            JOIN backtest_result br ON br.pattern_id = tp.id
            ORDER BY tp.id
            """
        ).fetchall()

    comparisons = []
    for pat in patterns:
        pid = pat["id"]

        # Most recent backtest
        bt = conn.execute(
            """
            SELECT win_count, trade_count, avg_return_pct, total_return_pct,
                   max_drawdown_pct, sharpe_ratio, created_at
            FROM backtest_result
            WHERE pattern_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (pid,),
        ).fetchone()

        if not bt:
            continue

        bt_trade_count = bt["trade_count"] or 0
        bt_win_rate = (bt["win_count"] / bt_trade_count) if bt_trade_count > 0 else 0.0

        # Paper trade stats (closed only)
        pt_row = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                COALESCE(SUM(pnl), 0.0) as total_pnl,
                COALESCE(AVG(pnl), 0.0) as avg_pnl
            FROM paper_trade
            WHERE pattern_id = ? AND status = 'closed'
            """,
            (pid,),
        ).fetchone()

        pt_total = pt_row["total"] if pt_row["total"] else 0
        pt_wins = pt_row["wins"] if pt_row["wins"] else 0
        pt_pnl = pt_row["total_pnl"] if pt_row["total_pnl"] else 0.0
        pt_win_rate = (pt_wins / pt_total) if pt_total > 0 else None
        pt_avg_return = pt_row["avg_pnl"] if pt_total > 0 else None

        # Open trades
        open_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM paper_trade WHERE pattern_id = ? AND status = 'executed'",
            (pid,),
        ).fetchone()
        open_count = open_row["cnt"] if open_row["cnt"] else 0

        # Days in paper trading
        days_in_pt = None
        if pat["status"] == "paper_trading":
            first_pt = conn.execute(
                "SELECT MIN(proposed_at) as first FROM paper_trade WHERE pattern_id = ?",
                (pid,),
            ).fetchone()
            if first_pt and first_pt["first"]:
                first_date = datetime.fromisoformat(first_pt["first"].replace("Z", "+00:00"))
                days_in_pt = (datetime.now(UTC) - first_date).days
            else:
                days_in_pt = 0

        # Divergence
        win_rate_diff = None
        avg_return_diff = None
        warning = False
        note = None

        if pt_total > 0 and pt_win_rate is not None:
            win_rate_diff = round((pt_win_rate - bt_win_rate) * 100, 1)
            if pt_avg_return is not None and bt["avg_return_pct"]:
                avg_return_diff = round(pt_avg_return - bt["avg_return_pct"], 1)
            warning = abs(win_rate_diff) > 10
        elif pt_total == 0:
            note = "No closed trades yet"

        # Check for 30+ days with 0 alerts
        if pat["status"] == "paper_trading" and days_in_pt is not None and days_in_pt >= 30:
            alert_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM pattern_alert WHERE pattern_id = ?",
                (pid,),
            ).fetchone()
            if alert_count["cnt"] == 0:
                note = f"No triggers in {days_in_pt}+ days \u2014 consider adjusting thresholds"

        comparisons.append({
            "pattern_id": pid,
            "pattern_name": pat["name"],
            "pattern_status": pat["status"],
            "days_in_paper_trading": days_in_pt,
            "backtest": {
                "win_rate": bt_win_rate,
                "avg_return_pct": bt["avg_return_pct"],
                "trade_count": bt_trade_count,
                "total_return_pct": bt["total_return_pct"],
                "max_drawdown_pct": bt["max_drawdown_pct"],
                "sharpe_ratio": bt["sharpe_ratio"],
                "backtest_date": bt["created_at"],
            },
            "paper_trading": {
                "win_rate": pt_win_rate,
                "avg_return_pct": pt_avg_return,
                "trade_count": pt_total,
                "total_pnl": pt_pnl,
                "open_trades": open_count,
            },
            "divergence": {
                "win_rate_diff_pp": win_rate_diff,
                "avg_return_diff_pp": avg_return_diff,
                "warning": warning,
                "note": note,
            },
        })

    return comparisons


def format_performance(comparisons: list[dict], single: bool = False) -> str:
    """Format PerformanceComparison list into CLI display output.

    Args:
        comparisons: List of PerformanceComparison dicts.
        single: True for detailed single-pattern view, False for ranking table.
    """
    lines: list[str] = []

    if single and len(comparisons) == 1:
        c = comparisons[0]
        bt = c["backtest"]
        pt = c["paper_trading"]
        div = c["divergence"]

        lines.append(f"Performance: {c['pattern_name']} (#{c['pattern_id']})")
        lines.append("\u2550" * (len(lines[0])))
        lines.append("")

        # Header
        lines.append(f"  {'':20}{'Backtest':<16}{'Paper Trading':<18}{'Divergence'}")

        # Win rate
        bt_wr = f"{bt['win_rate'] * 100:.1f}%"
        pt_wr = f"{pt['win_rate'] * 100:.1f}%" if pt["win_rate"] is not None else "\u2014"
        div_wr = ""
        if div["win_rate_diff_pp"] is not None:
            sign = "+" if div["win_rate_diff_pp"] >= 0 else ""
            div_wr = f"{sign}{div['win_rate_diff_pp']:.1f}pp"
            if div["warning"]:
                div_wr += " \u26a0\ufe0f"
        lines.append(f"  {'Win rate:':<20}{bt_wr:<16}{pt_wr:<18}{div_wr}")

        # Avg return
        bt_ar = f"+{bt['avg_return_pct']:.1f}%" if bt["avg_return_pct"] >= 0 else f"{bt['avg_return_pct']:.1f}%"
        if pt["avg_return_pct"] is not None:
            pt_ar = f"+{pt['avg_return_pct']:.1f}%" if pt["avg_return_pct"] >= 0 else f"{pt['avg_return_pct']:.1f}%"
        else:
            pt_ar = "\u2014"
        div_ar = ""
        if div["avg_return_diff_pp"] is not None:
            sign = "+" if div["avg_return_diff_pp"] >= 0 else ""
            div_ar = f"{sign}{div['avg_return_diff_pp']:.1f}pp"
        lines.append(f"  {'Avg return:':<20}{bt_ar:<16}{pt_ar:<18}{div_ar}")

        # Trade count
        lines.append(f"  {'Trade count:':<20}{bt['trade_count']:<16}{pt['trade_count']:<18}")

        # Total return
        bt_tr = f"+{bt['total_return_pct']:.1f}%" if bt["total_return_pct"] >= 0 else f"{bt['total_return_pct']:.1f}%"
        pt_pnl = f"+${pt['total_pnl']:.2f}" if pt["total_pnl"] >= 0 else f"-${abs(pt['total_pnl']):.2f}"
        lines.append(f"  {'Total return:':<20}{bt_tr:<16}{pt_pnl:<18}")

        # Max drawdown
        bt_dd = f"-{abs(bt['max_drawdown_pct']):.1f}%"
        lines.append(f"  {'Max drawdown:':<20}{bt_dd:<16}{'\u2014':<18}")

        # Warning message
        if div["warning"] and div["win_rate_diff_pp"] is not None:
            lines.append("")
            diff = abs(div["win_rate_diff_pp"])
            direction = "exceeds" if div["win_rate_diff_pp"] > 0 else "trails"
            lines.append(f"  \u26a0\ufe0f Paper trade win rate {direction} backtest by {diff:.0f}pp \u2014 monitor for reversion.")

        if div["note"]:
            lines.append("")
            lines.append(f"  Note: {div['note']}")

    else:
        # All-patterns ranking table
        lines.append("Performance Ranking")
        lines.append("\u2550" * 19)
        lines.append("")

        lines.append(f"  {'#':<4}{'Pattern':<30}{'BT Win%':<10}{'PT Win%':<10}{'Divergence':<13}{'PT P&L'}")
        lines.append("  " + "\u2500" * 73)

        for c in comparisons:
            bt = c["backtest"]
            pt = c["paper_trading"]
            div = c["divergence"]

            bt_wr = f"{bt['win_rate'] * 100:.1f}%"
            pt_wr = f"{pt['win_rate'] * 100:.1f}%" if pt["win_rate"] is not None else "\u2014"

            if div["win_rate_diff_pp"] is not None:
                sign = "+" if div["win_rate_diff_pp"] >= 0 else ""
                div_str = f"{sign}{div['win_rate_diff_pp']:.1f}pp"
                if div["warning"]:
                    div_str += " \u26a0\ufe0f"
            elif pt["trade_count"] == 0:
                div_str = "No trades"
            else:
                div_str = "\u2014"

            pnl = pt["total_pnl"]
            pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"

            name = c["pattern_name"][:28]
            lines.append(
                f"  {c['pattern_id']:<4}{name:<30}{bt_wr:<10}{pt_wr:<10}{div_str:<13}{pnl_str}"
            )

            if div["note"]:
                lines.append(f"      \u2514\u2500 Note: {div['note']}")

    return "\n".join(lines)
