# Architecture Decision Log

**Feature**: 008-system-architecture | **Created**: 2026-02-17

Captures the "why" behind key architecture decisions, including alternatives considered, operator input, and conditions under which decisions should be revisited. Referenced from plan.md.

---

## ADR-001: systemd Timers Over n8n for Orchestration

**Date**: 2026-02-17 | **Status**: Accepted

**Decision**: Use systemd timers + Python scripts for scheduling and orchestration. Do not use n8n for core pipeline orchestration.

**Context**: n8n was originally listed in the constitution as the orchestration layer. Evaluated during Phase 0 research.

**Arguments that DON'T apply to our setup**:
- RAM overhead (~500MB-1GB): NUC has 32GB — irrelevant (~3%)
- Security (CVE-2025-68668 sandbox bypass): NUC runs locally on home WiFi, not internet-exposed. Claude maintains all workflows, so the attack surface is minimal.

**Arguments that DO drive this decision**:
1. **Claude Code can't maintain n8n workflows** — Workflows are JSON blobs edited in a browser UI. Claude Code (our primary development tool) cannot create, modify, or debug them. Every workflow change requires leaving Claude Code and using the n8n visual editor manually.
2. **Language split** — Core logic is Python. n8n would either call Python scripts via Execute Command (making it a fancy cron) or run Python in its Code node (second-class, import restrictions). Logic stays in Python regardless.
3. **Version control** — Python scripts are git-native `.py` files. n8n workflows are opaque JSON exports that are hard to diff or review.

**Where n8n remains viable** (future Tier 3):
- Multi-channel notification routing (Slack + email + Telegram + Google Sheets) — trivial in n8n, ~50 LOC per channel in Python
- Visual execution monitoring dashboard
- If notification needs grow beyond ntfy.sh, n8n as a notification sidecar is reasonable

**Revisit when**: Multi-channel notifications become a priority, or a visual workflow monitoring UI is needed.

---

## ADR-002: Reddit/StockTwits Deferred (Not Rejected)

**Date**: 2026-02-17 | **Status**: Deferred

**Decision**: Remove Reddit (PRAW) and StockTwits (REST API) from the constitution's Technology Stack. Not rejected — deferred to a future feature.

**Rationale**: Higher-value free sources (FRED, Tiingo, SEC RSS, 13F, Form 4) were prioritized first. Reddit and StockTwits provide social sentiment, which is valuable but lower priority than macro indicators, insider trading data, and real-time filing notifications.

**Revisit when**: Social sentiment analysis becomes a research priority, or a "sentiment-driven" trading strategy is explored.

---

## ADR-003: QuantConnect Backtesting Removed from Scope

**Date**: 2026-02-17 | **Status**: Deferred

**Decision**: Remove QuantConnect MCP server from the constitution. Backtesting is out of scope for the current architecture.

**Rationale**: The system is research-first, human-decides. Backtesting requires a different architecture (historical data replay, strategy codification, performance metrics). This is a separate feature that should be specified independently.

**Revisit when**: A backtesting or strategy validation feature is specified.

---

## ADR-004: sqlite-vec Removed from Storage Stack

**Date**: 2026-02-17 | **Status**: Deferred

**Decision**: Remove sqlite-vec (vector search) from the constitution's Storage section. The current architecture doesn't require embedding-based search.

**Rationale**: Current research queries are structured (by ticker, date, content type). Semantic search of research artifacts (e.g., "find all filings discussing supply chain risk") is a future enhancement, not a current need.

**Revisit when**: The research database grows large enough that structured queries aren't sufficient, or semantic search of documents becomes a research workflow need.

---

## ADR-005: EarningsCall.biz Replaces Finnhub Transcripts

**Date**: 2026-02-17 | **Status**: Accepted

**Decision**: Use EarningsCall.biz (`earningscall` library) for earnings call transcripts instead of Finnhub.

**Rationale**: Finnhub's transcript endpoint requires a $3,000/mo premium plan (returns 403 on free tier). EarningsCall.biz provides dedicated transcript access with speaker attribution via a clean Python library. Finnhub's free tier remains valuable for market signals (analyst ratings, earnings history, insider activity, news).

**Revisit when**: Finnhub changes pricing, or a better all-in-one data provider (e.g., FMP Ultimate at $149/mo) makes individual source management unnecessary.
