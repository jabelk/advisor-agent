"""Hybrid confidence scoring: signal + indicator + momentum + LLM adjustment."""

from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

# --- Weight constants ---

# Component weights (must sum to 1.0)
SIGNAL_WEIGHT = 0.50
INDICATOR_WEIGHT = 0.30
MOMENTUM_WEIGHT = 0.20

# Signal type weights (must sum to 1.0)
SIGNAL_TYPE_WEIGHTS: dict[str, float] = {
    "sentiment": 0.20,
    "guidance_change": 0.25,
    "financial_metric": 0.20,
    "risk_factor": 0.15,
    "competitive_insight": 0.10,
    "leadership_change": 0.05,
    "investor_activity": 0.05,
}

# Confidence multipliers
CONFIDENCE_MULTIPLIERS: dict[str, float] = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.3,
}

# Evidence multipliers
EVIDENCE_MULTIPLIERS: dict[str, float] = {
    "fact": 1.0,
    "inference": 0.7,
}

# Indicator sub-weights
SMA_WEIGHT = 0.30
RSI_WEIGHT = 0.35
VWAP_WEIGHT = 0.35

# Momentum sub-weights
MOMENTUM_5D_WEIGHT = 0.50
MOMENTUM_20D_WEIGHT = 0.30
VOLUME_CONFIRM_WEIGHT = 0.20

# Recency half-life in days
RECENCY_HALF_LIFE = 7.0

# LLM adjustment bounds
LLM_MAX_ADJUSTMENT = 0.15

# Minimum thresholds for proposal generation
DEFAULT_MIN_CONFIDENCE = 0.45
DEFAULT_MIN_SIGNALS = 3
DEFAULT_MIN_FACTS = 1
DEFAULT_MIN_SIGNAL_TYPES = 2
DEFAULT_MAX_SIGNAL_AGE_DAYS = 14

# ATR limit price parameters
ATR_MIN_MULTIPLIER = 0.3  # at score 1.0 (high confidence → tighter limit)
ATR_MAX_MULTIPLIER = 0.7  # at score 0.45 (low confidence → wider limit)
LIMIT_OFFSET_FLOOR = 0.001  # 0.1% minimum
LIMIT_OFFSET_CAP = 0.02  # 2.0% maximum

# --- LLM prompt templates ---

LLM_SYSTEM_PROMPT = (
    "You are a quantitative finance analyst. Given a stock's research signals "
    "and technical indicators, provide a small confidence adjustment to the "
    "base score. You must respond with ONLY a JSON object."
)

LLM_USER_TEMPLATE = """Stock: {ticker}
Base Score: {base_score:+.3f} \
(signal: {signal_score:+.3f}, indicator: {indicator_score:+.3f}, \
momentum: {momentum_score:+.3f})

Research Signals ({signal_count} total):
{signal_summary}

Technical Indicators:
{indicator_summary}

Provide a confidence adjustment between -0.15 and +0.15. Consider:
1. Do signals and technicals agree or conflict?
2. Are there any red flags the base score might miss?
3. Is there narrative context that strengthens or weakens the case?

Respond with ONLY this JSON:
{{"adjustment": <float between -0.15 and 0.15>, "rationale": "<1-2 sentence explanation>"}}"""


# --- Signal scoring (T008) ---


def classify_signal_direction(signal: dict) -> int:
    """Classify a signal as bullish (+1), bearish (-1), or neutral (0).

    Uses signal_type and summary keywords to determine direction.
    """
    signal_type = str(signal.get("signal_type", ""))
    summary = str(signal.get("summary", "")).lower()

    # Risk factors are inherently bearish
    if signal_type == "risk_factor":
        return -1

    # Guidance changes: check keywords
    if signal_type == "guidance_change":
        if any(w in summary for w in ["raised", "increased", "upgraded", "above"]):
            return 1
        if any(w in summary for w in ["lowered", "decreased", "downgraded", "below", "cut"]):
            return -1
        return 0

    # General keyword check
    bullish_words = [
        "bullish", "positive", "strong", "grew", "beat", "exceeded",
        "raised", "upgrade", "growth", "outperform", "buying", "increased",
    ]
    bearish_words = [
        "bearish", "negative", "weak", "decline", "miss", "missed",
        "lowered", "downgrade", "slowdown", "underperform", "selling", "decreased",
    ]

    bull_count = sum(1 for w in bullish_words if w in summary)
    bear_count = sum(1 for w in bearish_words if w in summary)

    if bull_count > bear_count:
        return 1
    if bear_count > bull_count:
        return -1
    return 0


def recency_weight(created_at: str, half_life_days: float = RECENCY_HALF_LIFE) -> float:
    """Compute exponential decay weight based on signal age.

    Returns 1.0 for brand new signals, 0.5 at half_life_days, approaching 0 for old signals.
    """
    try:
        if "T" in created_at:
            signal_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            signal_time = datetime.strptime(created_at[:10], "%Y-%m-%d").replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return 0.5  # fallback for unparseable dates

    now = datetime.now(UTC)
    age_days = max((now - signal_time).total_seconds() / 86400, 0)
    return math.pow(0.5, age_days / half_life_days)


def compute_signal_score(signals: list[dict]) -> float:
    """Aggregate research signals into a score from -1.0 to +1.0.

    Uses type weights, confidence multipliers, evidence multipliers,
    and recency weighting per research.md Decision 1.
    """
    if not signals:
        return 0.0

    weighted_sum = 0.0
    total_weight = 0.0

    for signal in signals:
        signal_type = str(signal.get("signal_type", "sentiment"))
        confidence = str(signal.get("confidence", "medium"))
        evidence = str(signal.get("evidence_type", "inference"))
        created_at = str(signal.get("created_at", ""))

        direction = classify_signal_direction(signal)
        type_weight = SIGNAL_TYPE_WEIGHTS.get(signal_type, 0.05)
        conf_mult = CONFIDENCE_MULTIPLIERS.get(confidence, 0.6)
        ev_mult = EVIDENCE_MULTIPLIERS.get(evidence, 0.7)
        recency = recency_weight(created_at)

        weight = type_weight * conf_mult * ev_mult * recency
        weighted_sum += direction * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    score = weighted_sum / total_weight
    return max(-1.0, min(1.0, score))


# --- Indicator scoring (T009) ---


def compute_indicator_score(
    last_close: float,
    sma_20: float | None,
    sma_50: float | None,
    rsi_14: float | None,
    vwap: float | None,
) -> float:
    """Score technical indicators from -1.0 to +1.0.

    Components (weighted):
    - SMA alignment (0.30): golden cross / death cross, price vs SMAs
    - RSI momentum (0.35): overbought/oversold and neutral zone
    - VWAP positioning (0.35): price above/below VWAP
    """
    components = []
    weights = []

    # SMA alignment
    if sma_20 is not None and sma_50 is not None:
        sma_score = 0.0
        # Golden cross / death cross
        if sma_20 > sma_50:
            sma_score += 0.5
        elif sma_20 < sma_50:
            sma_score -= 0.5
        # Price vs SMA-20
        if last_close > sma_20:
            sma_score += 0.3
        elif last_close < sma_20:
            sma_score -= 0.3
        # Price vs SMA-50
        if last_close > sma_50:
            sma_score += 0.2
        elif last_close < sma_50:
            sma_score -= 0.2
        sma_score = max(-1.0, min(1.0, sma_score))
        components.append(sma_score)
        weights.append(SMA_WEIGHT)

    # RSI momentum
    if rsi_14 is not None:
        if rsi_14 >= 70:
            rsi_score = -0.5 - (rsi_14 - 70) / 60  # Overbought
        elif rsi_14 <= 30:
            rsi_score = 0.5 + (30 - rsi_14) / 60  # Oversold (bullish)
        elif rsi_14 >= 50:
            rsi_score = (rsi_14 - 50) / 40  # Mild bullish momentum
        else:
            rsi_score = (rsi_14 - 50) / 40  # Mild bearish momentum
        rsi_score = max(-1.0, min(1.0, rsi_score))
        components.append(rsi_score)
        weights.append(RSI_WEIGHT)

    # VWAP positioning
    if vwap is not None and vwap > 0:
        vwap_pct = (last_close - vwap) / vwap
        # Scale: +/-5% from VWAP maps to +/-1.0
        vwap_score = max(-1.0, min(1.0, vwap_pct / 0.05))
        components.append(vwap_score)
        weights.append(VWAP_WEIGHT)

    if not components:
        return 0.0

    total_weight = sum(weights)
    return sum(c * w for c, w in zip(components, weights)) / total_weight


def compute_momentum_score(daily_bars: list[dict]) -> float:
    """Score price momentum from -1.0 to +1.0.

    Components (weighted):
    - 5-day return (0.50): short-term momentum
    - 20-day return (0.30): medium-term trend
    - Volume confirmation (0.20): above/below average volume
    """
    if len(daily_bars) < 5:
        return 0.0

    closes = [float(b.get("close", 0)) for b in daily_bars]
    volumes = [float(b.get("volume", 0)) for b in daily_bars]

    components = []
    weights = []

    # 5-day return
    if len(closes) >= 6 and closes[-6] > 0:
        ret_5d = (closes[-1] - closes[-6]) / closes[-6]
        # Scale: +/-10% maps to +/-1.0
        score_5d = max(-1.0, min(1.0, ret_5d / 0.10))
        components.append(score_5d)
        weights.append(MOMENTUM_5D_WEIGHT)

    # 20-day return
    if len(closes) >= 21 and closes[-21] > 0:
        ret_20d = (closes[-1] - closes[-21]) / closes[-21]
        # Scale: +/-20% maps to +/-1.0
        score_20d = max(-1.0, min(1.0, ret_20d / 0.20))
        components.append(score_20d)
        weights.append(MOMENTUM_20D_WEIGHT)

    # Volume confirmation
    if len(volumes) >= 20:
        avg_vol = sum(volumes[-20:]) / 20
        if avg_vol > 0:
            recent_vol = sum(volumes[-5:]) / 5
            vol_ratio = recent_vol / avg_vol
            # Above-average volume confirms direction of last 5d return
            if components:  # Only if we have a price direction
                direction = 1.0 if components[0] > 0 else -1.0
                if vol_ratio > 1.0:
                    vol_score = direction * min(1.0, (vol_ratio - 1.0) / 0.5)
                else:
                    # Below-average volume weakens conviction
                    vol_score = -direction * min(1.0, (1.0 - vol_ratio) / 0.5)
                components.append(max(-1.0, min(1.0, vol_score)))
                weights.append(VOLUME_CONFIRM_WEIGHT)

    if not components:
        return 0.0

    total_weight = sum(weights)
    return max(-1.0, min(1.0, sum(c * w for c, w in zip(components, weights)) / total_weight))


# --- ATR and limit price (T010) ---


def compute_atr(daily_bars: list[dict], period: int = 14) -> float | None:
    """Compute Average True Range over the given period.

    Returns None if insufficient data.
    """
    if len(daily_bars) < period + 1:
        return None

    true_ranges = []
    for i in range(1, len(daily_bars)):
        high = float(daily_bars[i].get("high", 0))
        low = float(daily_bars[i].get("low", 0))
        prev_close = float(daily_bars[i - 1].get("close", 0))

        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)

    # Use the last `period` true ranges
    recent_trs = true_ranges[-period:]
    return sum(recent_trs) / len(recent_trs)


def compute_limit_price(
    side: str,
    last_close: float,
    atr_14: float | None,
    final_score: float,
) -> float:
    """Derive limit price using ATR-based offset scaled by confidence.

    For BUY: limit = last_close - offset (buy on dip)
    For SELL: limit = last_close + offset (sell on bounce)

    Offset scales inversely with confidence: 0.3x ATR at score 1.0, 0.7x ATR at score 0.45.
    Floor: 0.1% of last_close. Cap: 2.0% of last_close.
    """
    if atr_14 is None or atr_14 <= 0 or last_close <= 0:
        # Fallback: use 0.5% offset
        offset = last_close * 0.005
    else:
        # Interpolate multiplier: score 0.45→0.7x, score 1.0→0.3x
        abs_score = abs(final_score)
        t = max(0, min(1, (abs_score - 0.45) / (1.0 - 0.45)))
        multiplier = ATR_MAX_MULTIPLIER - t * (ATR_MAX_MULTIPLIER - ATR_MIN_MULTIPLIER)

        offset = atr_14 * multiplier

    # Apply floor and cap as percentage of last_close
    min_offset = last_close * LIMIT_OFFSET_FLOOR
    max_offset = last_close * LIMIT_OFFSET_CAP
    offset = max(min_offset, min(max_offset, offset))

    if side == "buy":
        price = last_close - offset
    else:
        price = last_close + offset

    return round(max(0.01, price), 2)


# --- Base score + LLM adjustment (T011) ---


def compute_base_score(
    signal_score: float, indicator_score: float, momentum_score: float
) -> float:
    """Combine sub-scores using configured weights. Returns -1.0 to +1.0."""
    raw = (
        signal_score * SIGNAL_WEIGHT
        + indicator_score * INDICATOR_WEIGHT
        + momentum_score * MOMENTUM_WEIGHT
    )
    return max(-1.0, min(1.0, raw))


def get_llm_adjustment(
    anthropic_client: object | None,
    ticker: str,
    base_score: float,
    signal_score: float,
    indicator_score: float,
    momentum_score: float,
    signals: list[dict],
    indicators: dict[str, float | None],
) -> tuple[float, str]:
    """Get LLM confidence adjustment. Returns (adjustment, rationale).

    If anthropic_client is None, returns (0.0, "No API key").
    Clamps result to +/-0.15.
    """
    if anthropic_client is None:
        return (0.0, "No API key — using base score only")

    # Build signal summary
    signal_lines = []
    for s in signals[:10]:  # Limit to 10 most recent
        sig_type = s.get("signal_type", "?")
        evidence = s.get("evidence_type", "?")
        confidence = s.get("confidence", "?")
        summary = s.get("summary", "")[:100]
        signal_lines.append(f"  - [{sig_type}/{evidence}/{confidence}] {summary}")
    signal_summary = "\n".join(signal_lines) if signal_lines else "  (none)"

    # Build indicator summary
    ind_parts = []
    for key, val in indicators.items():
        if val is not None:
            ind_parts.append(f"  - {key}: {val:.2f}")
    indicator_summary = "\n".join(ind_parts) if ind_parts else "  (none)"

    prompt = LLM_USER_TEMPLATE.format(
        ticker=ticker,
        base_score=base_score,
        signal_score=signal_score,
        indicator_score=indicator_score,
        momentum_score=momentum_score,
        signal_count=len(signals),
        signal_summary=signal_summary,
        indicator_summary=indicator_summary,
    )

    try:
        response = anthropic_client.messages.create(  # type: ignore[union-attr]
            model="claude-sonnet-4-5-20250929",
            max_tokens=200,
            system=LLM_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        data = json.loads(text)
        adjustment = float(data.get("adjustment", 0))
        rationale = str(data.get("rationale", ""))

        # Clamp to bounds
        adjustment = max(-LLM_MAX_ADJUSTMENT, min(LLM_MAX_ADJUSTMENT, adjustment))
        return (adjustment, rationale)

    except Exception as e:
        logger.warning("LLM adjustment failed for %s: %s", ticker, e)
        return (0.0, f"LLM call failed: {e}")


def compute_final_score(base_score: float, llm_adjustment: float) -> float:
    """Combine base score and LLM adjustment, clamping to -1.0/+1.0."""
    return max(-1.0, min(1.0, base_score + llm_adjustment))


# --- Safety gates (T012) ---


def should_generate_proposal(
    final_score: float,
    signals: list[dict],
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    min_signals: int = DEFAULT_MIN_SIGNALS,
    min_facts: int = DEFAULT_MIN_FACTS,
    min_signal_types: int = DEFAULT_MIN_SIGNAL_TYPES,
    max_signal_age_days: int = DEFAULT_MAX_SIGNAL_AGE_DAYS,
) -> tuple[bool, str]:
    """Check if a proposal should be generated based on safety gates.

    Returns (should_generate, reason).
    """
    # Check absolute confidence threshold
    if abs(final_score) < min_confidence:
        return (
            False,
            f"Confidence insufficient ({abs(final_score):.2f} < {min_confidence})",
        )

    # Check minimum signal count
    if len(signals) < min_signals:
        return (
            False,
            f"Insufficient signals ({len(signals)} < {min_signals})",
        )

    # Check minimum fact-based signals
    fact_count = sum(
        1 for s in signals if str(s.get("evidence_type", "")) == "fact"
    )
    if fact_count < min_facts:
        return (
            False,
            f"Insufficient fact signals ({fact_count} < {min_facts})",
        )

    # Check minimum distinct signal types
    signal_types = set(str(s.get("signal_type", "")) for s in signals)
    if len(signal_types) < min_signal_types:
        return (
            False,
            f"Insufficient signal types ({len(signal_types)} < {min_signal_types})",
        )

    # Check signal freshness
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=max_signal_age_days)
    most_recent = None
    for s in signals:
        created = str(s.get("created_at", ""))
        try:
            if "T" in created:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(created[:10], "%Y-%m-%d").replace(tzinfo=UTC)
            if most_recent is None or dt > most_recent:
                most_recent = dt
        except (ValueError, TypeError):
            pass

    if most_recent is None or most_recent < cutoff:
        return (
            False,
            f"Signals too old (most recent > {max_signal_age_days} days)",
        )

    return (True, "OK")
