"""Pattern parser: converts plain-text descriptions into structured RuleSets via Claude."""

from __future__ import annotations

import logging

from finance_agent.patterns.models import (
    ActionType,
    ClarifyingQuestion,
    PatternParseResult,
    RuleSet,
    StrikeStrategy,
    TriggerCondition,
    TriggerType,
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

COVERED CALL RECOGNITION:
- If the description mentions "covered call", "sell calls", "write calls", "sell call against shares", or "monthly income from options", this is a COVERED CALL strategy.
- For covered calls, set action_type to "sell_call".
- Trigger type should be "quantitative" with a calendar/time-based trigger (e.g., "monthly cycle").
- Entry signal: immediate entry (condition="time_delay", value="0", window_days=1).
- Exit criteria for covered calls: profit_target_pct is the % of premium to close early (e.g., 50% means buy back when premium drops 50%), stop_loss_pct=0 (no stop loss on covered calls — max loss is the stock dropping), max_hold_days is calculated as expiration_days minus roll_threshold (e.g., 30 - 21 = 9).
- If strike distance is specified as "X% out of the money" or "X% OTM", use the appropriate StrikeStrategy (otm_5 for ~5%, otm_10 for ~10%, custom for other values).
- CRITICAL: If someone says "sell call" or "sell calls" WITHOUT mentioning owning shares, treat it as a covered call anyway but add a default noting "Treated as covered call — naked calls not supported".
- Covered call defaults: 5% OTM strike, 30-day expiration, 50% premium profit target, 21 DTE roll threshold.

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


def _apply_covered_call_defaults(result: PatternParseResult) -> PatternParseResult:
    """Post-process parsed result: ensure covered call defaults are applied and logged.

    When action_type is sell_call, applies any missing defaults:
    - 5% OTM strike (otm_5)
    - 30-day expiration
    - 50% premium profit target
    - 21-day roll threshold (max_hold_days = expiration - 21)
    - No stop loss (0%)
    """
    if not result.is_complete or not result.rule_set:
        return result

    action = result.rule_set.action
    if action.action_type != ActionType.SELL_CALL:
        return result

    defaults_applied = list(result.defaults_applied)

    # Strike strategy: default to 5% OTM
    if action.strike_strategy == StrikeStrategy.ATM:
        action.strike_strategy = StrikeStrategy.OTM_5
        defaults_applied.append("Strike: 5% OTM (covered call default)")
        logger.info("Applied covered call default: 5%% OTM strike")

    # Expiration: default to 30 days
    if action.expiration_days != 30:
        # Only override if it looks like a generic default (e.g., 0 or unset)
        pass  # Keep user-specified expiration
    elif "expiration" not in " ".join(defaults_applied).lower():
        defaults_applied.append("Expiration: 30 days (covered call default)")
        logger.info("Applied covered call default: 30-day expiration")

    # Exit criteria defaults for covered calls
    exit_criteria = result.rule_set.exit_criteria

    # Premium profit target: 50% (means buy back when premium drops to 50% of initial)
    if exit_criteria.profit_target_pct == 20.0:  # Still at generic default
        exit_criteria.profit_target_pct = 50.0
        defaults_applied.append("Premium profit target: 50% (covered call default — buy back at 50% premium decay)")
        logger.info("Applied covered call default: 50%% premium profit target")

    # Stop loss: 0% for covered calls (max loss is stock dropping)
    if exit_criteria.stop_loss_pct == 10.0:  # Still at generic default
        exit_criteria.stop_loss_pct = 0.0
        defaults_applied.append("Stop loss: 0% (covered call — no stop loss on short call)")
        logger.info("Applied covered call default: 0%% stop loss")

    # Max hold: expiration_days - 21 (roll threshold)
    roll_threshold = 21
    expected_max_hold = action.expiration_days - roll_threshold
    if exit_criteria.max_hold_days is None or exit_criteria.max_hold_days == expected_max_hold:
        exit_criteria.max_hold_days = expected_max_hold
        if "roll" not in " ".join(defaults_applied).lower():
            defaults_applied.append(
                f"Roll threshold: {roll_threshold} DTE (max hold = {expected_max_hold} days)"
            )
            logger.info("Applied covered call default: %d DTE roll threshold", roll_threshold)

    result.defaults_applied = defaults_applied
    return result


def _apply_news_dip_defaults(result: PatternParseResult) -> PatternParseResult:
    """Post-process parsed result: ensure pharma news dip defaults are applied.

    Detects pharma dip patterns by: trigger_type == qualitative AND
    sector_filter contains healthcare/pharma AND action_type == buy_call.

    Applies defaults:
    - price_change_pct >= 5.0 trigger condition (if missing)
    - volume_spike >= 1.5 trigger condition (if missing)
    - pullback_pct entry with 2-day window (if entry looks generic)
    """
    if not result.is_complete or not result.rule_set:
        return result

    rs = result.rule_set
    # Check if this is a pharma news dip pattern
    is_qualitative = rs.trigger_type.value == "qualitative" if hasattr(rs.trigger_type, 'value') else rs.trigger_type == "qualitative"
    has_pharma_sector = rs.sector_filter and any(
        kw in rs.sector_filter.lower() for kw in ("healthcare", "pharma", "biotech")
    )
    is_buy_call = rs.action.action_type.value == "buy_call" if hasattr(rs.action.action_type, 'value') else rs.action.action_type == "buy_call"

    if not (is_qualitative and has_pharma_sector and is_buy_call):
        return result

    defaults_applied = list(result.defaults_applied)

    # Ensure price_change_pct trigger condition exists
    has_price_change = any(c.field == "price_change_pct" for c in rs.trigger_conditions)
    if not has_price_change:
        rs.trigger_conditions.append(TriggerCondition(
            field="price_change_pct",
            operator="gte",
            value="5.0",
            description="Single-day price spike >= 5%",
        ))
        defaults_applied.append("Trigger: price_change_pct >= 5.0% (pharma dip default)")
        logger.info("Applied pharma dip default: 5%% spike threshold")

    # Ensure volume_spike trigger condition exists
    has_volume = any(c.field == "volume_spike" for c in rs.trigger_conditions)
    if not has_volume:
        rs.trigger_conditions.append(TriggerCondition(
            field="volume_spike",
            operator="gte",
            value="1.5",
            description="Volume >= 1.5x 20-day average",
        ))
        defaults_applied.append("Trigger: volume_spike >= 1.5x (pharma dip default)")
        logger.info("Applied pharma dip default: 1.5x volume threshold")

    # Ensure entry signal is pullback_pct with 2-day window
    entry = rs.entry_signal
    if entry.condition == "time_delay" and entry.value == "0":
        entry.condition = "pullback_pct"
        entry.value = "2.0"
        entry.window_days = 2
        entry.description = "Buy on 2% pullback within 2 trading days"
        defaults_applied.append("Entry: 2% pullback within 2-day window (pharma dip default)")
        logger.info("Applied pharma dip default: 2%% pullback entry")

    result.defaults_applied = defaults_applied
    return result


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
                result = PatternParseResult.model_validate(block.input)
                result = _apply_covered_call_defaults(result)
                return _apply_news_dip_defaults(result)
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
