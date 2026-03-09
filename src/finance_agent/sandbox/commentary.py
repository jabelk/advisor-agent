"""Market commentary generation using Claude API + research signals.

Uses local SQLite for research signals only — no Salesforce dependency.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

import anthropic

SYSTEM_PROMPT = """You are a market commentary writer for a financial advisor practice. \
Your job is to write a 2-3 paragraph market update tailored to a specific client segment. \
The commentary should be professional, informative, and reference specific data points \
when available.

Return your response as a JSON object with these exact keys:
- "commentary": The full 2-3 paragraph market commentary text
- "data_points_cited": An integer count of specific market data points referenced

Respond ONLY with the JSON object, no markdown fences or other text."""


def generate_commentary(
    conn: sqlite3.Connection | None = None,
    risk_tolerance: str | None = None,
    life_stage: str | None = None,
    anthropic_client: anthropic.Anthropic | None = None,
) -> dict:
    """Generate market commentary targeted at a client segment.

    Returns MarketCommentary dict. If no segment specified, generates general overview.
    """
    # Define segment
    segment_parts = []
    segment_criteria = {}
    if risk_tolerance:
        segment_parts.append(f"{risk_tolerance} risk tolerance")
        segment_criteria["risk_tolerance"] = risk_tolerance
    if life_stage:
        segment_parts.append(f"{life_stage} life stage")
        segment_criteria["life_stage"] = life_stage

    segment = ", ".join(segment_parts) if segment_parts else "All clients (general overview)"

    # Query recent research signals
    signals = _get_recent_signals(conn)
    market_data_available = len(signals) > 0

    # Build user message
    user_message = f"Target client segment: {segment}\n\n"

    if risk_tolerance:
        user_message += _get_segment_guidance(risk_tolerance, life_stage)

    if signals:
        signal_data = [
            {
                "type": s.get("signal_type"),
                "ticker": s.get("ticker"),
                "summary": s.get("summary"),
                "confidence": s.get("confidence"),
                "source": s.get("source_type"),
            }
            for s in signals[:20]
        ]
        user_message += f"\nRecent market signals:\n{json.dumps(signal_data, indent=2)}\n\n"
    else:
        user_message += "\nNo recent market data available. Write a general commentary noting that specific data points are not available.\n\n"

    user_message += "Write a 2-3 paragraph market commentary for this segment."

    # Call Claude API
    if anthropic_client is None:
        anthropic_client = anthropic.Anthropic()

    message = anthropic_client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    # Parse response
    response_text = message.content[0].text
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        if "{" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(response_text[start:end])
            else:
                parsed = {"commentary": response_text, "data_points_cited": 0}
        else:
            parsed = {"commentary": response_text, "data_points_cited": 0}

    return {
        "segment": segment,
        "segment_criteria": segment_criteria,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commentary": parsed.get("commentary", ""),
        "data_points_cited": parsed.get("data_points_cited", 0),
        "market_data_available": market_data_available,
    }


def _get_recent_signals(conn: sqlite3.Connection) -> list[dict]:
    """Query the 20 most recent research signals."""
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT rs.signal_type, rs.confidence, rs.summary, rs.details,
                      sd.source_type, c.ticker
               FROM research_signal rs
               JOIN source_document sd ON rs.document_id = sd.id
               JOIN company c ON rs.company_id = c.id
               ORDER BY rs.created_at DESC
               LIMIT 20""",
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []


def _get_segment_guidance(risk_tolerance: str, life_stage: str | None = None) -> str:
    """Return writing guidance based on segment characteristics."""
    guidance = {
        "conservative": (
            "Focus on: bond markets, dividend stocks, interest rate environment, "
            "capital preservation strategies, fixed income conditions. "
            "Tone: reassuring, stability-focused."
        ),
        "moderate": (
            "Focus on: balanced market outlook, diversification benefits, "
            "mix of growth and income opportunities. "
            "Tone: balanced, measured optimism."
        ),
        "growth": (
            "Focus on: equity markets, sector performance, growth opportunities, "
            "technology and innovation trends. "
            "Tone: forward-looking, opportunity-focused."
        ),
        "aggressive": (
            "Focus on: high-growth sectors, momentum plays, options strategies, "
            "emerging markets, concentrated positions. "
            "Tone: dynamic, conviction-driven."
        ),
    }

    text = f"Segment writing guidance: {guidance.get(risk_tolerance, '')}\n"

    if life_stage:
        stage_notes = {
            "accumulation": "Long time horizon. Emphasize compound growth.",
            "pre-retirement": "Transitioning to preservation. Discuss de-risking.",
            "retirement": "Income-focused. Emphasize stability and distributions.",
            "legacy": "Estate planning focus. Emphasize wealth transfer strategies.",
        }
        text += f"Life stage note: {stage_notes.get(life_stage, '')}\n"

    return text
