# Research: Decision Engine

**Feature**: 004-decision-engine
**Date**: 2026-02-16

## Decision 1: Hybrid Confidence Scoring Formula

**Decision**: Use a 3-component weighted formula (signal 50%, indicators 30%, momentum 20%) as the base score, with LLM adjustment bounded to +/-0.15.

**Rationale**: Research signals get the highest weight because the constitution requires research-driven decisions. Technical indicators are well-established non-hallucinated inputs. Momentum provides a market-reality check. The LLM adjustment range of +/-0.15 allows qualitative corrections without overriding the deterministic model.

**Alternatives considered**:
- Pure rule-based (no LLM): Cheaper and fully reproducible, but misses narrative coherence and qualitative context that LLMs excel at evaluating.
- Pure LLM: Anthropic API call per company per run. Non-reproducible, expensive, and prone to hallucination in the scoring step.
- Wider LLM range (+/-0.3): Too much power for the LLM to override strong signals. Safety-first principle dictates constraining the adjustment.

**Key parameters**:
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Signal score weight | 0.50 | Constitution: research-driven |
| Indicator score weight | 0.30 | Non-hallucinated, established |
| Momentum score weight | 0.20 | Price action reality check |
| Recency half-life | 7 days | Day trading relevance |
| LLM adjustment range | +/-0.15 | Qualitative nudge, not override |
| High confidence multiplier | 1.0 | Full weight |
| Medium confidence multiplier | 0.6 | Moderate discount |
| Low confidence multiplier | 0.3 | Significant discount |
| Fact evidence multiplier | 1.0 | Constitution: fact vs inference |
| Inference evidence multiplier | 0.7 | Moderate discount |

## Decision 2: Minimum Confidence Threshold

**Decision**: Minimum absolute score of 0.45 on the -1.0 to +1.0 scale, plus additional safety gates.

**Rationale**: 0.45 requires either multiple medium-to-high confidence signals in agreement plus supportive technicals, or fewer signals with strong confidence and fact-based evidence. This filters noise while not being so restrictive that the system never trades.

**Safety gates** (all must pass in addition to threshold):
- Minimum 3 research signals
- At least 1 fact-based signal (not all inferences)
- At least 2 distinct signal types (multi-factor confirmation)
- Most recent signal must be within 14 days

**Alternatives considered**:
- 0.30 threshold: Too permissive for a $500-1000 account, triggers on weak/ambiguous signals.
- 0.70 threshold: Too restrictive, requires near-unanimous strong signals. Would miss reasonable opportunities.

## Decision 3: Limit Price Derivation (ATR-Based)

**Decision**: Use ATR-14 (Average True Range, 14-period) as a volatility-adaptive offset. Offset scales inversely with confidence (high confidence = tighter limit, more aggressive fill).

**Formula**: `limit_price = last_close -/+ (ATR% * confidence_multiplier * last_close)`
- BUY: subtract offset (buy on dip)
- SELL: add offset (sell on bounce)
- Confidence multiplier: 0.3x ATR at score 1.0, up to 0.7x ATR at score 0.45
- Floor: minimum 0.1% offset (avoid market-like fills)
- Cap: maximum 2.0% offset (avoid unrealistic limits)

**Rationale**: ATR adapts to each stock's volatility. High-confidence trades use tighter limits to increase fill probability. Low-confidence trades demand a better entry price as additional margin of safety.

**Alternatives considered**:
- Fixed percentage (0.5%): Does not account for stock-specific volatility. A 0.5% offset on a volatile stock is meaningless; on a stable stock it may be too large.
- Bid-ask spread based: Requires real-time level 2 data not available in free tier.

## Decision 4: Alpaca Trading Client for Account Data

**Decision**: Use `alpaca-py` `TradingClient` for account info, positions, order history, and portfolio P&L. The project already creates a TradingClient in `cli.py` health check.

**Key API calls**:
- `client.get_account()` → `TradeAccount` (equity, buying_power, last_equity)
- `client.get_all_positions()` → `List[Position]` (symbol, qty, unrealized_pl, market_value)
- `client.get_orders(filter)` → `List[Order]` (today's filled order count)
- `client.get_portfolio_history(filter)` → `PortfolioHistory` (daily P&L)

**Daily P&L computation**: `equity - last_equity` gives total daily change. `sum(unrealized_intraday_pl)` from positions gives unrealized portion. Realized = total - unrealized.

**Important notes**:
- All numeric fields on TradeAccount/Position are `Optional[str]`, must cast to `float()` and guard for `None`
- `paper=True` is the default (auto-routes to paper API)
- `portfolio_value` is deprecated, use `equity` instead
- Max 500 orders per request

## Decision 5: Sell Proposals Scope

**Decision**: Sell-to-close only. No short selling.

**Rationale**: Short selling requires margin, carries unlimited loss risk, and is inappropriate for a $500-1000 experimental account. Aligns with Safety First principle.

## Decision 6: Position Sizing Formula

**Decision**: Use a confidence-scaled percentage of portfolio with the constitution's 10% maximum.

**Formula**:
```
max_dollars = portfolio_equity * max_position_pct  # default 10%
confidence_scale = abs(final_score)  # 0.45 to 1.0
target_dollars = max_dollars * confidence_scale
quantity = floor(target_dollars / limit_price)
```

**Rationale**: Higher confidence = larger position (up to the cap). A score of 0.45 (minimum threshold) results in 4.5% of portfolio. A score of 1.0 results in 10% (the constitutional maximum). This naturally sizes positions proportional to conviction.

**Alternatives considered**:
- Fixed sizing (always max): Wastes the confidence score signal and over-commits on marginal proposals.
- Kelly criterion: Requires win rate estimation that does not exist yet (no trade history).

## Decision 7: Kill Switch Persistence

**Decision**: Store kill switch state in SQLite (engine_state table) rather than a file flag or environment variable.

**Rationale**: Consistent with the project's SQLite-for-everything pattern. Survives restarts, is queryable, and allows audit logging of toggle events in the same transaction.

## Decision 8: Proposal Expiration

**Decision**: Proposals expire at 16:00 ET (market close) on the day they were generated.

**Rationale**: Day trading context — stale proposals from a previous trading session are based on outdated market conditions. A background check is not needed; expiration is checked at query time (when reviewing or listing proposals).
