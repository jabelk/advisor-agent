# Research: Pharma News Dip Pattern

**Feature**: 013-pharma-news-dip
**Date**: 2026-03-08

## 1. Event Detection via Price-Action Proxy

**Decision**: Detect news events as single-day price spikes ≥ configurable threshold (default 5%) with volume ≥ 1.5x the trailing 20-day average. Apply per-ticker cooldown to prevent double-counting consecutive spike days.

**Rationale**: Historical price data doesn't contain news event metadata. Price-action proxy is the standard approach in quantitative finance for identifying "event days" when actual news timestamps aren't available. The 5% threshold + 1.5x volume filter produces a reasonable precision/recall tradeoff for pharma catalysts (FDA approvals, trial results) which typically cause 5-30% single-day moves on unusually high volume.

**Alternatives considered**:
- **Finnhub news API backfill**: Would provide actual news timestamps but Finnhub free tier has limited historical news depth and rate limits. Would add external API dependency to backtesting. Rejected — adds complexity without proportional accuracy gain for backtesting.
- **SEC EDGAR filing dates**: Only covers formal filings, misses most pharma catalysts (FDA decisions, trial data, conference presentations). Rejected — too narrow.
- **Price-only (no volume filter)**: Simpler but produces many false positives from earnings moves, index rebalancing, and general volatility. Rejected — volume filter is cheap and dramatically improves signal quality.

## 2. Cooldown Between Events

**Decision**: After a trigger fires on a ticker, suppress new triggers on that same ticker until (a) the current trade closes, or (b) the entry window expires without entry. This is a per-ticker cooldown — triggers on other tickers are unaffected.

**Rationale**: Multi-day pharma events (e.g., FDA advisory committee day 1 + approval day 2) are almost always the same catalyst. Double-triggering would create overlapping positions on the same thesis, inflating trade count and distorting win rate.

**Alternatives considered**:
- **Fixed N-day cooldown**: Simpler but inflexible — a 5-day cooldown might miss a genuinely new catalyst. Rejected — trade-lifecycle-based cooldown adapts naturally.
- **No cooldown (treat each spike independently)**: Simplest but produces meaningless overlapping trades. Rejected.

## 3. Regime Detection Algorithm

**Decision**: Use a rolling window approach with configurable window size (default 63 trading days / ~3 months). For each window, calculate win rate and label as: strong (≥ 60%), weak (40–59%), breakdown (< 40%). Merge adjacent windows with the same label into contiguous regime periods.

**Rationale**: The existing `detect_regimes()` in backtest.py uses a 10-trade rolling window. For event-driven patterns with fewer trades, a time-based window is more appropriate. The 3-month default matches Jordan's observation ("worked for ~3 months, then stopped"). The 60/40 thresholds were confirmed during spec clarification.

**Alternatives considered**:
- **Change-point detection (CUSUM, Bayesian)**: More statistically rigorous but adds significant complexity and requires tuning parameters. Overkill for a CLI tool with 10-50 trades. Rejected — keep it simple, iterate if needed.
- **Existing 10-trade rolling window**: Already implemented but doesn't work well when trades are sparse (event-driven patterns may have long gaps between trades). Rejected for this pattern type — keep existing for standard patterns.

## 4. Manual Event Dates Input

**Decision**: Support two input modes: (1) CLI flag `--events "2024-08-15,2024-11-02"` for quick ad-hoc use, and (2) `--events-file path/to/events.csv` for larger sets. File format: one date per line, optional comma-separated label (e.g., `2024-08-15,FDA approval`). When manual events are provided, they completely replace the price-action proxy — no automatic detection runs.

**Rationale**: Jordan will often know the specific dates of pharma events he observed. CLI flag is fastest for 2-5 dates. File is better for backtesting across many historical FDA decisions.

**Alternatives considered**:
- **Hybrid mode (manual + automatic)**: Use manual dates AND run automatic detection, then deduplicate. Adds complexity with minimal benefit — if Jordan provides dates, he wants exactly those tested. Rejected.
- **JSON format**: More structured but overkill for a list of dates with optional labels. Rejected.

## 5. Qualitative Trigger Handling in Backtest vs. Paper Trading

**Decision**: In backtesting, treat qualitative triggers identically to quantitative — the price-action proxy serves as the automated stand-in for news. In paper trading, qualitative triggers always require human confirmation before proceeding to entry signal monitoring.

**Rationale**: Backtesting can't ask for human confirmation retroactively. The price-action proxy is our best approximation of "news happened." In paper trading, the human-in-the-loop is available and critical for pattern quality — Jordan should verify that the spike was actually pharma news, not an index rebalance.

**Alternatives considered**:
- **Skip qualitative triggers entirely in backtesting**: Would make the pattern untestable. Rejected.
- **Auto-approve in paper trading with post-trade review**: Defeats the purpose of qualitative classification. Rejected — safety first per constitution.

## 6. New Module vs. Inline Extension

**Decision**: Create two new modules: `event_detection.py` (spike detection, cooldown, manual event parsing) and `regime.py` (regime analysis with time-based windows). The main `backtest.py` gets a new `run_news_dip_backtest()` function that calls these modules.

**Rationale**: The existing `backtest.py` is already 250+ lines with covered call logic. Event detection and regime analysis are self-contained responsibilities that benefit from dedicated testing. Separate modules keep each file focused and under 200 lines.

**Alternatives considered**:
- **Add everything to backtest.py**: Fewer files but backtest.py would exceed 500 lines and mix three different pattern types. Rejected — violates single responsibility.
- **Create a generic EventDrivenBacktest base class**: Over-engineering for one pattern type. Rejected — YAGNI.

## 7. Parser Post-Processing for News Dip Patterns

**Decision**: Add `_apply_news_dip_defaults()` in parser.py, similar to `_apply_covered_call_defaults()`. Detects pharma dip patterns by: trigger_type == qualitative AND sector_filter contains "healthcare"/"pharma" AND action_type is buy_call. Applies sensible defaults: 5% spike threshold, 1.5x volume, 2% pullback entry, 2-day window.

**Rationale**: Claude's parser may not set the exact threshold values we need. Post-processing ensures consistency, just like covered call defaults ensure proper OTM/premium values.

**Alternatives considered**:
- **Rely entirely on Claude's parsing**: Claude might use different defaults each time. Rejected — consistency matters for backtesting reproducibility.
- **Hardcode defaults in CLI**: Would bypass the parser entirely. Rejected — the parser should produce a valid RuleSet that the CLI just executes.
