"""Proposal generation, lifecycle management, and queries."""

from __future__ import annotations

import logging
import math
import sqlite3
from datetime import UTC, datetime, timedelta

from finance_agent.audit.logger import AuditLogger
from finance_agent.engine.scoring import (
    compute_atr,
    compute_base_score,
    compute_final_score,
    compute_indicator_score,
    compute_limit_price,
    compute_momentum_score,
    compute_signal_score,
    get_llm_adjustment,
    should_generate_proposal,
)
from finance_agent.engine.state import get_risk_settings

logger = logging.getLogger(__name__)


# --- Position sizing (T013) ---


def compute_position_size(
    final_score: float,
    limit_price: float,
    equity: float,
    max_position_pct: float = 0.10,
) -> int:
    """Compute position size as whole shares.

    Formula: floor(abs(score) * max_position_pct * equity / limit_price)
    Minimum 1 share if above threshold.
    """
    if limit_price <= 0 or equity <= 0:
        return 0

    target_dollars = abs(final_score) * max_position_pct * equity
    quantity = math.floor(target_dollars / limit_price)
    return max(1, quantity)


# --- Proposal persistence (T015) ---


def save_proposal(conn: sqlite3.Connection, proposal: dict) -> int:
    """Insert a trade proposal into the database. Returns the proposal ID."""
    cursor = conn.execute(
        "INSERT INTO trade_proposal "
        "(company_id, ticker, direction, quantity, limit_price, estimated_cost, "
        "confidence_score, base_score, llm_adjustment, llm_rationale, "
        "signal_score, indicator_score, momentum_score, "
        "status, risk_passed, staleness_warning, decision_reason, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            proposal["company_id"],
            proposal["ticker"],
            proposal["direction"],
            proposal["quantity"],
            proposal["limit_price"],
            proposal["estimated_cost"],
            proposal["confidence_score"],
            proposal["base_score"],
            proposal["llm_adjustment"],
            proposal.get("llm_rationale"),
            proposal["signal_score"],
            proposal["indicator_score"],
            proposal["momentum_score"],
            proposal.get("status", "pending"),
            proposal.get("risk_passed", 1),
            proposal.get("staleness_warning", 0),
            proposal.get("decision_reason"),
            proposal["expires_at"],
        ),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def save_proposal_sources(
    conn: sqlite3.Connection,
    proposal_id: int,
    cited_signals: list[dict],
    cited_indicators: list[dict],
    cited_bars: list[dict],
) -> int:
    """Save source citations for a proposal. Returns count saved."""
    count = 0
    for sig in cited_signals:
        conn.execute(
            "INSERT OR IGNORE INTO proposal_source "
            "(proposal_id, source_type, source_id, contribution) "
            "VALUES (?, 'research_signal', ?, ?)",
            (proposal_id, sig["id"], sig.get("contribution", "")),
        )
        count += 1

    for ind in cited_indicators:
        conn.execute(
            "INSERT OR IGNORE INTO proposal_source "
            "(proposal_id, source_type, source_id, contribution) "
            "VALUES (?, 'technical_indicator', ?, ?)",
            (proposal_id, ind["id"], ind.get("contribution", "")),
        )
        count += 1

    for bar in cited_bars:
        conn.execute(
            "INSERT OR IGNORE INTO proposal_source "
            "(proposal_id, source_type, source_id, contribution) "
            "VALUES (?, 'price_bar', ?, ?)",
            (proposal_id, bar["id"], bar.get("contribution", "")),
        )
        count += 1

    conn.commit()
    return count


def get_proposal(conn: sqlite3.Connection, proposal_id: int) -> dict | None:
    """Get a proposal with joined sources and risk checks."""
    row = conn.execute(
        "SELECT * FROM trade_proposal WHERE id = ?", (proposal_id,)
    ).fetchone()
    if not row:
        return None

    proposal = dict(row)

    # Get sources
    sources = conn.execute(
        "SELECT * FROM proposal_source WHERE proposal_id = ?", (proposal_id,)
    ).fetchall()
    proposal["sources"] = [dict(s) for s in sources]

    # Get risk checks
    checks = conn.execute(
        "SELECT * FROM risk_check_result WHERE proposal_id = ?", (proposal_id,)
    ).fetchall()
    proposal["risk_checks"] = [dict(c) for c in checks]

    return proposal


# --- Proposal generation orchestrator (T014) ---


def _get_market_close_today() -> str:
    """Return today's 16:00 ET (market close) as ISO 8601 UTC string."""
    now = datetime.now(UTC)
    # Market closes at 16:00 ET = 21:00 UTC (EST) or 20:00 UTC (EDT)
    # Use 21:00 UTC as conservative estimate (EST)
    close_utc = now.replace(hour=21, minute=0, second=0, microsecond=0)
    if close_utc < now:
        # If we're past close, use tomorrow
        close_utc += timedelta(days=1)
    return close_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _query_signals_for_company(conn: sqlite3.Connection, company_id: int) -> list[dict]:
    """Query recent research signals for a company."""
    rows = conn.execute(
        "SELECT rs.id, rs.signal_type, rs.evidence_type, rs.confidence, "
        "rs.summary, rs.details, rs.created_at, "
        "sd.source_type, sd.content_type, sd.title as document_title "
        "FROM research_signal rs "
        "JOIN source_document sd ON rs.document_id = sd.id "
        "WHERE rs.company_id = ? "
        "ORDER BY rs.created_at DESC",
        (company_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _query_indicators_for_company(
    conn: sqlite3.Connection, ticker: str
) -> dict[str, float | None]:
    """Query latest technical indicators for a ticker."""
    rows = conn.execute(
        "SELECT indicator_type, value FROM technical_indicator "
        "WHERE ticker = ? AND timeframe = 'day'",
        (ticker,),
    ).fetchall()
    indicators: dict[str, float | None] = {
        "sma_20": None, "sma_50": None, "rsi_14": None, "vwap": None,
    }
    for row in rows:
        key = str(row["indicator_type"])
        if key in indicators:
            indicators[key] = float(row["value"])
    return indicators


def _query_daily_bars(conn: sqlite3.Connection, ticker: str) -> list[dict]:
    """Query daily price bars for momentum scoring."""
    rows = conn.execute(
        "SELECT id, open, high, low, close, volume, bar_timestamp "
        "FROM price_bar WHERE ticker = ? AND timeframe = 'day' "
        "ORDER BY bar_timestamp ASC",
        (ticker,),
    ).fetchall()
    return [dict(r) for r in rows]


def _query_indicator_rows(conn: sqlite3.Connection, ticker: str) -> list[dict]:
    """Query indicator rows for citation purposes."""
    rows = conn.execute(
        "SELECT id, indicator_type, value FROM technical_indicator "
        "WHERE ticker = ? AND timeframe = 'day'",
        (ticker,),
    ).fetchall()
    return [dict(r) for r in rows]


def _check_data_staleness(
    daily_bars: list[dict], staleness_hours: int = 24,
) -> bool:
    """Return True if market data is stale (most recent bar older than threshold)."""
    if not daily_bars:
        return True
    last_bar_ts = str(daily_bars[-1].get("bar_timestamp", ""))
    try:
        if "T" in last_bar_ts:
            bar_time = datetime.fromisoformat(last_bar_ts.replace("Z", "+00:00"))
        else:
            bar_time = datetime.strptime(last_bar_ts[:10], "%Y-%m-%d").replace(tzinfo=UTC)
        age = datetime.now(UTC) - bar_time
        return age.total_seconds() > staleness_hours * 3600
    except (ValueError, TypeError):
        return True


def generate_proposals(
    conn: sqlite3.Connection,
    trading_client: object,
    anthropic_client: object | None,
    account_summary: dict,
    positions: list[dict],
    risk_settings: dict | None = None,
    ticker: str | None = None,
    dry_run: bool = False,
    audit: AuditLogger | None = None,
) -> list[dict]:
    """Generate trade proposals for watchlist companies.

    Returns a list of proposal dicts (saved to DB unless dry_run=True).
    """
    from finance_agent.data.watchlist import get_company_by_ticker, list_companies

    if risk_settings is None:
        risk_settings = get_risk_settings(conn)

    # Get companies
    if ticker:
        company = get_company_by_ticker(conn, ticker.upper())
        if not company:
            logger.warning("Ticker %s not on watchlist", ticker)
            return []
        companies = [company]
    else:
        companies = list_companies(conn)

    if not companies:
        logger.info("No companies on watchlist")
        return []

    equity = float(account_summary.get("equity", 0))
    max_position_pct = float(risk_settings.get("max_position_pct", 0.10))
    min_confidence = float(risk_settings.get("min_confidence_threshold", 0.45))
    min_signals = int(risk_settings.get("min_signal_count", 3))
    max_signal_age = int(risk_settings.get("max_signal_age_days", 14))
    staleness_hours = int(risk_settings.get("data_staleness_hours", 24))

    expires_at = _get_market_close_today()
    proposals: list[dict] = []

    for company in companies:
        company_id = int(company["id"])  # type: ignore[arg-type]
        tk = str(company["ticker"])

        # Query data
        signals = _query_signals_for_company(conn, company_id)
        indicators = _query_indicators_for_company(conn, tk)
        daily_bars = _query_daily_bars(conn, tk)

        # Check data availability
        if not signals:
            proposals.append({
                "ticker": tk,
                "status": "skipped",
                "reason": "No research signals",
            })
            continue

        if not daily_bars:
            proposals.append({
                "ticker": tk,
                "status": "skipped",
                "reason": "No market data (daily bars)",
            })
            continue

        # Compute scores
        signal_score = compute_signal_score(signals)
        last_close = float(daily_bars[-1].get("close", 0))

        indicator_score = compute_indicator_score(
            last_close,
            indicators.get("sma_20"),
            indicators.get("sma_50"),
            indicators.get("rsi_14"),
            indicators.get("vwap"),
        )
        momentum_score = compute_momentum_score(daily_bars)
        base_score = compute_base_score(signal_score, indicator_score, momentum_score)

        # LLM adjustment
        llm_adj, llm_rationale = get_llm_adjustment(
            anthropic_client, tk, base_score,
            signal_score, indicator_score, momentum_score,
            signals, indicators,
        )
        final_score = compute_final_score(base_score, llm_adj)

        # Safety gates
        should_gen, reason = should_generate_proposal(
            final_score, signals,
            min_confidence=min_confidence,
            min_signals=min_signals,
            max_signal_age_days=max_signal_age,
        )

        if not should_gen:
            proposals.append({
                "ticker": tk,
                "status": "skipped",
                "reason": reason,
                "confidence_score": final_score,
                "base_score": base_score,
                "llm_adjustment": llm_adj,
                "signal_score": signal_score,
                "indicator_score": indicator_score,
                "momentum_score": momentum_score,
            })
            continue

        # Determine direction
        if final_score > 0:
            direction = "buy"
        else:
            # Check if we hold a position to sell
            held = [p for p in positions if str(p.get("symbol", "")) == tk]
            if not held:
                proposals.append({
                    "ticker": tk,
                    "status": "skipped",
                    "reason": "Bearish but no position held to sell",
                    "confidence_score": final_score,
                })
                continue
            direction = "sell"

        # Compute limit price and position size
        atr_14 = compute_atr(daily_bars)
        limit_price = compute_limit_price(direction, last_close, atr_14, final_score)

        if direction == "sell":
            # Sell quantity = shares held
            held_qty = sum(
                int(p.get("qty", 0))
                for p in positions if str(p.get("symbol", "")) == tk
            )
            quantity = held_qty if held_qty > 0 else 1
        else:
            quantity = compute_position_size(
                final_score, limit_price, equity, max_position_pct,
            )

        # Check staleness
        staleness_warning = 1 if _check_data_staleness(daily_bars, staleness_hours) else 0

        proposal = {
            "company_id": company_id,
            "ticker": tk,
            "direction": direction,
            "quantity": quantity,
            "limit_price": limit_price,
            "estimated_cost": round(quantity * limit_price, 2),
            "confidence_score": round(final_score, 4),
            "base_score": round(base_score, 4),
            "llm_adjustment": round(llm_adj, 4),
            "llm_rationale": llm_rationale,
            "signal_score": round(signal_score, 4),
            "indicator_score": round(indicator_score, 4),
            "momentum_score": round(momentum_score, 4),
            "status": "pending",
            "risk_passed": 1,
            "staleness_warning": staleness_warning,
            "expires_at": expires_at,
            # Metadata for display (not stored in DB)
            "signals": signals,
            "indicators": indicators,
            "daily_bars": daily_bars,
            "last_close": last_close,
        }

        if dry_run:
            proposals.append(proposal)
            continue

        # Save proposal
        proposal_id = save_proposal(conn, proposal)
        proposal["id"] = proposal_id

        # Save source citations
        cited_signals = [
            {
                "id": s["id"],
                "contribution": (
                    f"{s['signal_type']}/{s['evidence_type']}/{s['confidence']}"
                ),
            }
            for s in signals[:10]
        ]
        indicator_rows = _query_indicator_rows(conn, tk)
        cited_indicators = [
            {"id": ind["id"], "contribution": f"{ind['indicator_type']}={ind['value']:.2f}"}
            for ind in indicator_rows
        ]
        # Cite the most recent bar for price reference
        cited_bars = [
            {"id": daily_bars[-1]["id"], "contribution": f"close={last_close:.2f}"}
        ] if daily_bars and "id" in daily_bars[-1] else []
        save_proposal_sources(conn, proposal_id, cited_signals, cited_indicators, cited_bars)

        if audit:
            audit.log("proposal_generated", "engine", {
                "proposal_id": proposal_id,
                "ticker": tk,
                "direction": direction,
                "quantity": quantity,
                "confidence_score": round(final_score, 4),
                "status": "pending",
            })

        proposals.append(proposal)

    return proposals


# --- Proposal lifecycle (T030 — stub for now, full implementation in Phase 6) ---


def get_pending_proposals(
    conn: sqlite3.Connection, ticker: str | None = None,
) -> list[dict]:
    """Query pending proposals with lazy expiration check."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Mark expired proposals
    conn.execute(
        "UPDATE trade_proposal SET status = 'expired' "
        "WHERE status = 'pending' AND expires_at < ?",
        (now,),
    )
    conn.commit()

    query = (
        "SELECT * FROM trade_proposal WHERE status = 'pending'"
    )
    params: list[str] = []
    if ticker:
        query += " AND ticker = ?"
        params.append(ticker.upper())
    query += " ORDER BY confidence_score DESC"

    rows = conn.execute(query, params).fetchall()
    proposals = []
    for row in rows:
        p = dict(row)
        # Attach sources
        sources = conn.execute(
            "SELECT * FROM proposal_source WHERE proposal_id = ?", (p["id"],)
        ).fetchall()
        p["sources"] = [dict(s) for s in sources]
        # Attach risk checks
        checks = conn.execute(
            "SELECT * FROM risk_check_result WHERE proposal_id = ?", (p["id"],)
        ).fetchall()
        p["risk_checks"] = [dict(c) for c in checks]
        proposals.append(p)
    return proposals


def approve_proposal(
    conn: sqlite3.Connection,
    proposal_id: int,
    reason: str | None = None,
    audit: AuditLogger | None = None,
) -> bool:
    """Approve a pending proposal. Returns True if successful."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = conn.execute(
        "UPDATE trade_proposal SET status = 'approved', decided_at = ?, "
        "decision_reason = ? WHERE id = ? AND status = 'pending'",
        (now, reason, proposal_id),
    )
    conn.commit()

    if cursor.rowcount == 0:
        return False

    if audit:
        audit.log("proposal_approved", "engine", {
            "proposal_id": proposal_id,
            "reason": reason,
        })
    return True


def reject_proposal(
    conn: sqlite3.Connection,
    proposal_id: int,
    reason: str | None = None,
    audit: AuditLogger | None = None,
) -> bool:
    """Reject a pending proposal. Returns True if successful."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = conn.execute(
        "UPDATE trade_proposal SET status = 'rejected', decided_at = ?, "
        "decision_reason = ? WHERE id = ? AND status = 'pending'",
        (now, reason, proposal_id),
    )
    conn.commit()

    if cursor.rowcount == 0:
        return False

    if audit:
        audit.log("proposal_rejected", "engine", {
            "proposal_id": proposal_id,
            "reason": reason,
        })
    return True


def query_proposal_history(
    conn: sqlite3.Connection,
    ticker: str | None = None,
    status: str | None = None,
    since: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Query proposal history with optional filters."""
    # First expire any stale pending proposals
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "UPDATE trade_proposal SET status = 'expired' "
        "WHERE status = 'pending' AND expires_at < ?",
        (now,),
    )
    conn.commit()

    query = "SELECT * FROM trade_proposal WHERE 1=1"
    params: list[str | int] = []

    if ticker:
        query += " AND ticker = ?"
        params.append(ticker.upper())
    if status:
        query += " AND status = ?"
        params.append(status)
    if since:
        query += " AND created_at >= ?"
        params.append(since)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_engine_status(
    conn: sqlite3.Connection,
    account_summary: dict,
    daily_order_count: int,
    daily_pnl: dict,
) -> dict:
    """Return engine status summary."""
    from finance_agent.engine.state import get_kill_switch, get_risk_settings

    risk_settings = get_risk_settings(conn)
    kill_switch = get_kill_switch(conn)

    # Count proposals
    now = datetime.now(UTC)
    today = now.strftime("%Y-%m-%d")
    pending = conn.execute(
        "SELECT COUNT(*) as cnt FROM trade_proposal WHERE status = 'pending'"
    ).fetchone()["cnt"]
    today_generated = conn.execute(
        "SELECT COUNT(*) as cnt FROM trade_proposal WHERE created_at >= ?",
        (today,),
    ).fetchone()["cnt"]
    today_approved = conn.execute(
        "SELECT COUNT(*) as cnt FROM trade_proposal "
        "WHERE status = 'approved' AND decided_at >= ?",
        (today,),
    ).fetchone()["cnt"]
    today_rejected = conn.execute(
        "SELECT COUNT(*) as cnt FROM trade_proposal "
        "WHERE status = 'rejected' AND decided_at >= ?",
        (today,),
    ).fetchone()["cnt"]

    equity = float(account_summary.get("equity", 0))
    max_trades = int(risk_settings.get("max_trades_per_day", 20))
    max_loss_pct = float(risk_settings.get("max_daily_loss_pct", 0.05))
    max_loss_dollars = equity * max_loss_pct

    return {
        "kill_switch": kill_switch,
        "equity": equity,
        "buying_power": float(account_summary.get("buying_power", 0)),
        "daily_order_count": daily_order_count,
        "max_trades_per_day": max_trades,
        "daily_pnl": daily_pnl,
        "max_daily_loss": max_loss_dollars,
        "pending_proposals": pending,
        "today_generated": today_generated,
        "today_approved": today_approved,
        "today_rejected": today_rejected,
        "risk_settings": risk_settings,
    }
