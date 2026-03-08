# Research: Pattern Lab

**Feature**: 011-pattern-lab
**Date**: 2026-03-08

## R1: Pattern Rule Representation

**Decision**: Structured Pydantic models serialized to JSON for storage.

**Rationale**: The codebase already uses Pydantic extensively (data/models.py) for structured LLM output. Representing rules as Pydantic models gives us validation, serialization, and direct compatibility with Claude's structured output feature. JSON serialization to SQLite's `rule_set_json` column is consistent with how `safety_state` stores risk settings.

**Alternatives considered**:
- YAML schema: More human-readable but adds a dependency and doesn't integrate with existing Pydantic patterns.
- DSL (domain-specific language): Powerful but over-engineered for the current scope. Jordan describes patterns in English, not code.

## R2: Backtest Engine Approach

**Decision**: Pure Python simulation engine using historical price data from Alpaca market data API.

**Rationale**: Alpaca provides free historical bar data (daily/hourly) through alpaca-py SDK which is already a dependency. A custom simulation engine gives full control over regime detection logic and options estimation — features not available in off-the-shelf backtesting libraries. The existing `price_bar` table was dropped in migration 006 but the schema pattern exists and can be restored.

**Alternatives considered**:
- Backtrader/Zipline: Mature backtesting frameworks but add heavy dependencies and impose their own data model. Overkill for the initial pattern testing use case.
- Alpaca backtesting API: Alpaca doesn't offer a dedicated backtesting API; it provides historical data which we simulate against.

## R3: Historical Options Data

**Decision**: Estimate options returns from underlying price movement + implied volatility approximation. No dedicated options data source initially.

**Rationale**: Granular historical options chain data (strikes, expirations, Greeks) is expensive (CBOE, OptionMetrics). For Pattern Lab's purpose — testing whether a pattern *concept* works — estimating call/put returns from the underlying stock's price movement and a simplified IV model is sufficient. Jordan is testing whether "buy calls on the dip" works directionally, not optimizing Greeks.

**Alternatives considered**:
- Polygon.io options data: Good quality but paid ($199/mo for options). Can be added later if Jordan needs precise options pricing.
- Alpaca options data: Alpaca supports options trading but historical options chain data availability is limited on free tier.

## R4: Real-Time Trigger Detection

**Decision**: Polling loop with configurable interval (default 5 minutes during market hours).

**Rationale**: The system is a personal tool for one user, not a high-frequency trading platform. A simple polling loop checking Alpaca market data at intervals is easy to implement, debug, and understand. It can run as a long-lived CLI process or be triggered via cron. This matches the existing architecture — no async event infrastructure exists.

**Alternatives considered**:
- WebSocket streaming (Alpaca real-time): Lower latency but adds async complexity. The patterns Jordan describes (news → spike → dip over 1-2 days) don't need sub-second detection.
- Event-driven with message queue: Over-engineered for single-user personal tool.

## R5: News/Qualitative Trigger Handling

**Decision**: Two-tier trigger system — quantitative triggers are fully automated, qualitative triggers (news/events) notify the user and require confirmation.

**Rationale**: Jordan's pharma example has a qualitative component ("major positive news") that can't be reliably automated from headlines alone. The system will use existing Finnhub news API and RSS feeds to detect potential news events, but will present them to the user for confirmation rather than auto-triggering. This is consistent with Constitution Principle II (research-driven, human decides) and Principle IV (safety first).

**Alternatives considered**:
- Full NLP sentiment analysis: Could auto-detect "major positive news" but adds complexity and false positive risk. Not appropriate for a learning/safety-first platform.
- Manual-only qualitative triggers: Too restrictive — the system should at least surface relevant news for the user to evaluate.

## R6: Price Data Restoration

**Decision**: Create new migration (007) that re-adds price data tables plus new Pattern Lab tables. Fetch historical data from Alpaca on demand for backtests.

**Rationale**: Migration 006 dropped the `price_bar` table during architecture cleanup. Pattern Lab needs historical price data for backtesting. Rather than caching all price data upfront, fetch from Alpaca's historical bars API when a backtest is requested and cache locally for future runs. This is storage-efficient and avoids stale data.

**Alternatives considered**:
- Pre-fetch all price data nightly: Wastes storage for tickers Jordan never backtests.
- No local cache (always fetch from API): Slow for repeated backtests on the same data range.
