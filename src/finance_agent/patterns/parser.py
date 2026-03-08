"""Pattern parser: converts plain-text descriptions into structured RuleSets via Claude."""

from __future__ import annotations

import logging

from finance_agent.patterns.models import (
    ClarifyingQuestion,
    PatternParseResult,
    RuleSet,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a trading pattern analyst. Your job is to parse plain-text descriptions of trading patterns into structured rule sets.

Given a user's description of a market pattern they've observed, extract:

1. **Trigger conditions**: What market events or data points start the pattern. Classify as:
   - "quantitative": Based on measurable data (price change %, volume spike, etc.) — can be fully automated
   - "qualitative": Based on news, events, or sentiment — requires human confirmation or external data

2. **Entry signal**: The specific condition that tells you when to enter a position after the trigger fires. Include:
   - What to watch for (pullback %, price level, time delay)
   - How long to wait (window in trading days)

3. **Trade action**: What to do — buy/sell shares or options. For options, include:
   - Option type (call or put)
   - Strike strategy (ATM, OTM 5%, OTM 10%, ITM 5%, or custom)
   - Expiration preference (days)

4. **Exit criteria**: When to close the position:
   - Profit target (% gain)
   - Stop loss (% loss)
   - Maximum hold period (days)

5. **Filters**: Any constraints on which stocks the pattern applies to (sector, market cap, volume).

IMPORTANT RULES:
- If a field is not specified, apply sensible defaults and note them.
- Defaults: profit target 20%, stop loss 10%, ATM strike, 30-day expiration, no max hold.
- If the description is too vague to determine trigger conditions OR entry signal OR action, set is_complete=false and provide clarifying questions (max 3).
- Suggest a short, descriptive name for the pattern (2-5 words).
- Be precise about what's quantitative vs qualitative.
"""

PARSE_PROMPT = """Parse this trading pattern description into a structured rule set:

"{description}"

Return a PatternParseResult with:
- is_complete: true if you have enough info, false if you need clarification
- rule_set: the parsed rules (if complete)
- suggested_name: a short name for the pattern
- clarifying_questions: questions if incomplete (max 3)
- defaults_applied: list of defaults you applied (e.g., "Profit target: 20% (not specified)")
"""


def parse_pattern_description(
    description: str,
    api_key: str,
) -> PatternParseResult:
    """Parse a plain-text pattern description into a structured PatternParseResult.

    Uses Claude's structured output to extract trigger conditions, entry signals,
    trade actions, and exit criteria from conversational language.
    """
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package required. Install with: pip install anthropic")
        return PatternParseResult(
            is_complete=False,
            suggested_name="unknown",
            clarifying_questions=[
                ClarifyingQuestion(
                    question="anthropic package is not installed",
                    field="system",
                    suggestions=["pip install anthropic"],
                )
            ],
        )

    client = anthropic.Anthropic(api_key=api_key)

    prompt = PARSE_PROMPT.format(description=description)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "name": "output_pattern",
                    "description": "Output the parsed pattern result",
                    "input_schema": PatternParseResult.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "output_pattern"},
        )
    except Exception as e:
        logger.error("Claude API call failed: %s", e)
        return PatternParseResult(
            is_complete=False,
            suggested_name="error",
            clarifying_questions=[
                ClarifyingQuestion(
                    question=f"API error: {e}",
                    field="system",
                    suggestions=["Check your ANTHROPIC_API_KEY"],
                )
            ],
        )

    # Extract the tool use result
    for block in response.content:
        if block.type == "tool_use" and block.name == "output_pattern":
            try:
                return PatternParseResult.model_validate(block.input)
            except Exception as e:
                logger.error("Failed to parse Claude response: %s", e)
                return PatternParseResult(
                    is_complete=False,
                    suggested_name="parse_error",
                    clarifying_questions=[
                        ClarifyingQuestion(
                            question=f"Failed to parse response: {e}",
                            field="system",
                            suggestions=["Try rephrasing your pattern description"],
                        )
                    ],
                )

    # No tool use in response
    return PatternParseResult(
        is_complete=False,
        suggested_name="no_response",
        clarifying_questions=[
            ClarifyingQuestion(
                question="No structured output received from AI",
                field="system",
                suggestions=["Try again or rephrase your description"],
            )
        ],
    )
