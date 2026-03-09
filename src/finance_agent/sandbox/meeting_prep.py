"""Meeting preparation brief generation using Claude API + research signals.

Client data comes from Salesforce. Research signals come from local SQLite.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

import anthropic
from simple_salesforce import Salesforce

from finance_agent.sandbox.storage import get_client

SYSTEM_PROMPT = """You are a meeting preparation assistant for a financial advisor. \
Your job is to create a structured meeting brief that helps the advisor prepare for \
a client meeting. The brief should be professional, actionable, and tailored to the \
client's specific situation.

Return your response as a JSON object with these exact keys:
- "client_summary": A 2-3 sentence overview of the client
- "portfolio_context": A paragraph about their investment situation and goals
- "market_conditions": A paragraph about relevant market conditions (use provided signals if available, otherwise note that market data is unavailable)
- "talking_points": A list of 3-5 specific, actionable talking points appropriate for this client

Respond ONLY with the JSON object, no markdown fences or other text."""


def generate_meeting_brief(
    sf: Salesforce,
    client_id: str,
    anthropic_client: anthropic.Anthropic | None = None,
    db_conn: sqlite3.Connection | None = None,
) -> dict:
    """Generate a meeting preparation brief for a client.

    Args:
        sf: Authenticated Salesforce client (for client data).
        client_id: Salesforce Contact ID.
        anthropic_client: Optional pre-configured Anthropic client.
        db_conn: Optional SQLite connection for research signals.

    Returns MeetingBrief dict. Raises ValueError if client_id not found.
    """
    client = get_client(sf, client_id)
    if not client:
        raise ValueError(
            f"Client {client_id} not found. Run 'sandbox list' to see available clients."
        )

    # Query research signals from local SQLite (if available)
    signals = _get_relevant_signals(db_conn) if db_conn else []
    market_data_available = len(signals) > 0

    # Build user message
    client_context = {
        "name": f"{client['first_name']} {client['last_name']}",
        "age": client.get("age"),
        "occupation": client.get("occupation"),
        "account_value": client.get("account_value"),
        "risk_tolerance": client.get("risk_tolerance"),
        "investment_goals": client.get("investment_goals") or "Not specified",
        "life_stage": client.get("life_stage"),
        "household": client.get("household_members") or "Not specified",
        "notes": client.get("notes") or "None",
        "recent_interactions": [
            {"date": ix["interaction_date"], "type": ix["interaction_type"], "summary": ix["summary"]}
            for ix in (client.get("interactions") or [])[:5]
        ],
    }

    user_message = f"Client profile:\n{json.dumps(client_context, indent=2)}\n\n"

    if signals:
        signal_data = [
            {"type": s.get("signal_type"), "summary": s.get("summary"), "confidence": s.get("confidence")}
            for s in signals[:10]
        ]
        user_message += f"Recent market signals:\n{json.dumps(signal_data, indent=2)}\n\n"
    else:
        user_message += "Market data: No recent research signals available. Note this in the market conditions section.\n\n"

    user_message += "Generate a meeting preparation brief for this client."

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
        # Try extracting JSON from markdown fences
        if "```" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(response_text[start:end])
            else:
                parsed = _fallback_brief(client, market_data_available)
        else:
            parsed = _fallback_brief(client, market_data_available)

    talking_points = parsed.get("talking_points", [])
    if isinstance(talking_points, str):
        talking_points = [talking_points]

    return {
        "client_id": client_id,
        "client_name": f"{client['first_name']} {client['last_name']}",
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "client_summary": parsed.get("client_summary", ""),
        "portfolio_context": parsed.get("portfolio_context", ""),
        "market_conditions": parsed.get("market_conditions", ""),
        "talking_points": talking_points,
        "market_data_available": market_data_available,
    }


def _get_relevant_signals(conn: sqlite3.Connection | None) -> list[dict]:
    """Query recent research signals from local SQLite."""
    if conn is None:
        return []
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT rs.signal_type, rs.confidence, rs.summary, rs.details,
                      sd.source_type, c.ticker
               FROM research_signal rs
               JOIN source_document sd ON rs.document_id = sd.id
               JOIN company c ON rs.company_id = c.id
               ORDER BY rs.created_at DESC
               LIMIT 10""",
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []


def _fallback_brief(client: dict, market_data_available: bool) -> dict:
    """Generate a minimal brief when API parsing fails."""
    return {
        "client_summary": (
            f"{client['first_name']} {client['last_name']}, age {client.get('age', '?')}, "
            f"{client.get('occupation', 'N/A')}. Account value: ${client.get('account_value', 0):,.0f}."
        ),
        "portfolio_context": (
            f"Risk tolerance: {client.get('risk_tolerance', 'N/A')}. "
            f"Life stage: {client.get('life_stage', 'N/A')}. "
            f"Goals: {client.get('investment_goals') or 'Not specified'}."
        ),
        "market_conditions": (
            "Market data available — review recent signals before meeting."
            if market_data_available
            else "Market data unavailable — run research pipeline first."
        ),
        "talking_points": [
            "Review current portfolio allocation",
            "Discuss investment goals and timeline",
            "Address any recent market concerns",
        ],
    }
