# Implementation Plan: System Architecture Design

**Branch**: `008-system-architecture` | **Date**: 2026-02-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-system-architecture/spec.md`

## Summary

Design the complete system architecture for a research-powered investment system. The system runs on an Intel NUC (always-on processes), connects to Claude Desktop via MCP servers for human interaction, and uses Claude API for LLM-powered analysis. Key decisions: cron/systemd + Python for orchestration (not n8n), Claude Agent SDK + Pydantic AI for agent framework, phased data source expansion starting at $0/mo.

## Technical Context

**Language/Version**: Python 3.12+ (existing codebase)
**Primary Dependencies**: claude-agent-sdk, pydantic-ai, fastmcp, fredapi, httpx, edgartools, feedparser
**Storage**: SQLite (WAL mode) + filesystem for research artifacts
**Testing**: pytest
**Target Platform**: Intel NUC (Linux/Docker), Claude Desktop (macOS)
**Project Type**: Single project (Python package)
**Performance Goals**: Research pipeline completes within 5 minutes per company; monitoring checks complete within 30 seconds
**Constraints**: Solo developer; NUC has limited RAM (shared with NATS, GitHub Actions runner); context window is a real constraint
**Scale/Scope**: ~10-20 watchlist companies, ~$50-100/mo API costs

## Constitution Check

*GATE: All gates pass.*

| Gate | Status | Notes |
|------|--------|-------|
| Safety First | PASS | Safety guardrails in `safety_state` table; kill switch enforced at human review point |
| Research-Driven | PASS | All analysis cites data sources; distinguishes facts from inferences |
| Modular Architecture | PASS | 4 independent layers; MCP servers for external tools; minimal custom code |
| Audit Everything | PASS | Append-only logging of all signals, decisions, safety state changes |
| Security by Design | PASS | Secrets in env vars; paper/live key separation; Docker isolation |
| Less Code More Context | PASS | Off-the-shelf MCP servers, systemd timers, ntfy.sh over custom implementations |

## Project Structure

### Documentation (this feature)

```text
specs/008-system-architecture/
├── plan.md              # This file (architecture blueprint)
├── research.md          # Phase 0 research findings
├── data-model.md        # Component catalog and data flows
├── quickstart.md        # Setup guide for the architecture
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (no changes — this is a docs-only feature)

The architecture describes the target state. No source code modifications in this feature.

```text
# Target architecture (implemented in future features)
src/finance_agent/
├── data/                # Layer 1: Data Ingestion (existing)
│   ├── sources/         # SEC EDGAR, Finnhub, Tiingo, FRED, RSS
│   ├── storage.py       # Filesystem storage
│   └── models.py        # Data models
├── research/            # Layer 2: Research/Analysis (existing)
│   ├── analyzer.py      # LLM-powered analysis
│   ├── orchestrator.py  # Pipeline orchestration
│   └── signals.py       # Structured signal models
├── safety/              # Layer 3: Safety (existing)
│   └── guards.py        # Kill switch + risk limits
├── mcp/                 # NEW: Custom MCP server
│   └── research_server.py  # FastMCP server for research DB
├── agents/              # NEW: Agent definitions
│   ├── monitor.py       # SEC RSS + data source monitor
│   ├── scanner.py       # News scanner with Haiku triage
│   ├── researcher.py    # Deep company research
│   └── briefing.py      # Daily briefing generator
└── cli.py               # CLI entry point (existing)
```

**Structure Decision**: Single Python package, extended with `mcp/` and `agents/` directories for new capabilities. Agents are standalone Python scripts triggered by systemd timers on the NUC.

---

## Architecture Blueprint (US1: FR-001, FR-006)

### Component Catalog

Every component in the system with its runtime location, responsibility, and status:

| Component | Runtime | Responsibility | Build/Buy | Status |
|-----------|---------|---------------|-----------|--------|
| **Research Pipeline** | NUC (Python) | Ingest data, run LLM analysis, produce signals | Build (existing) | ~3,600 LOC |
| **Safety Module** | NUC (SQLite) | Kill switch + risk limits storage | Build (existing) | ~200 LOC |
| **Audit Log** | NUC (SQLite) | Append-only logging of all activity | Build (existing) | ~150 LOC |
| **Custom Research MCP** | NUC (FastMCP) | Expose research DB to Claude Desktop | Build (new) | ~100 LOC |
| **Monitor Agent** | NUC (systemd timer) | Poll SEC RSS + data sources for new data | Build (new) | ~200 LOC |
| **Scanner Agent** | NUC (systemd timer) | Fetch news, triage with Haiku | Build (new) | ~150 LOC |
| **Deep Research Agent** | NUC (on-demand) | Full company analysis using Sonnet | Build (new) | ~300 LOC |
| **Briefing Agent** | NUC (systemd timer) | Synthesize daily research summary | Build (new) | ~150 LOC |
| **Alpaca MCP Server** | Claude Desktop (stdio) | Trading, positions, market data (43 tools) | Buy (official) | Production |
| **SEC EDGAR MCP** | Claude Desktop (stdio) | SEC filings, financials, insider data | Buy (community) | Stable v1.0.8 |
| **ntfy.sh** | NUC (Docker) | Mobile push notifications | Buy (self-hosted) | Production |
| **Claude Desktop** | Workstation (macOS) | Human interface for research review + trading | Buy | Production |
| **Claude API** | Cloud (Anthropic) | LLM inference (Haiku, Sonnet, Opus) | Buy | Production |
| **SQLite** | NUC | Structured data storage (research, audit, safety) | Buy | Production |
| **NATS** | NUC (Docker) | Event messaging between agents | Buy (existing) | Production |

**Custom code total**: ~4,850 LOC (existing ~3,950 + new ~900). Increase of ~23% over current codebase — within the "less code, more context" constraint (FR-010).

**NUC Resource Estimates** (always-on services):

| Service | Estimated RAM | Notes |
|---------|--------------|-------|
| NATS | ~30 MB | Already running |
| ntfy.sh (Docker) | ~20 MB | Lightweight Go binary |
| FastMCP server | ~50 MB | Python process, idle most of the time |
| GitHub Actions runner | ~100 MB | Already running |
| Python agents (transient) | ~100-200 MB | Short-lived, triggered by systemd timers |
| SQLite | ~10 MB | File-based, minimal memory |
| **Total always-on** | **~210 MB** | Well within NUC capacity |

### Runtime Locations (FR-006)

```
┌────────────────────────────────────────────────────────────────┐
│  INTEL NUC (always-on)                                         │
│                                                                │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ systemd timers    │  │ NATS         │  │ ntfy.sh          │ │
│  │                   │  │ (msg bus)    │  │ (notifications)  │ │
│  │ • monitor (15min) │  │              │  │                  │ │
│  │ • scanner (1-4hr) │  │              │  │                  │ │
│  │ • briefing (6am)  │  │              │  │                  │ │
│  └───────┬───────────┘  └──────┬───────┘  └──────────────────┘ │
│          │                     │                                │
│  ┌───────▼─────────────────────▼───────────────────────────┐   │
│  │ Python Processes                                         │   │
│  │  monitor.py → ingest.py → research.py → briefing.py    │   │
│  └──────────────────────┬──────────────────────────────────┘   │
│                         │                                      │
│  ┌──────────────────────▼──────────────────────────────────┐   │
│  │ Data Layer                                               │   │
│  │  SQLite (research, audit, safety) + research_data/       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Custom MCP Server (FastMCP, HTTP transport, port 8000)  │   │
│  │  → Exposes research DB for remote Claude Desktop access  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  CLAUDE DESKTOP (workstation, on-demand)                       │
│                                                                │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ MCP Servers (stdio, configured in claude_desktop_config)  │ │
│  │  • Alpaca MCP        — 43 tools (trading, data)          │ │
│  │  • SEC EDGAR MCP     — ~8 tools (filings, financials)    │ │
│  │  • Research DB MCP   — ~6 tools (via mcp-remote to NUC)  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                │
│  Human → Claude conversation → MCP tool calls → results       │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  EXTERNAL APIs (cloud)                                         │
│                                                                │
│  Anthropic API ←── Claude inference (Haiku, Sonnet)            │
│  SEC EDGAR     ←── Filings, RSS feeds (free)                   │
│  Finnhub       ←── Market signals, news (free tier)            │
│  Tiingo        ←── Ticker-tagged news (free tier)              │
│  FRED          ←── Macro indicators (free)                     │
│  Alpaca        ←── Market data, trading (paper/live)           │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Component Interaction Map (US2: FR-002, FR-005, FR-007)

### Scenario 1: New SEC Filing Drops for Watchlist Company

```
SEC EDGAR RSS Feed (updates every 10 min, M-F 6am-10pm ET)
    │
    ▼
monitor.py (systemd timer, every 15 min)
    │ Polls RSS feed via feedparser
    │ Checks: is this ticker on our watchlist?
    │ Checks: have we already ingested this filing?
    │
    ├─── If new filing found ───▶ NATS message: {"event": "new_filing", "ticker": "AAPL", "form": "10-K", "url": "..."}
    │                                │
    │                                ▼
    │                           ingest.py (triggered by NATS)
    │                                │ Downloads filing via edgartools
    │                                │ Stores raw document in research_data/
    │                                │ Records metadata in SQLite documents table
    │                                │
    │                                ▼
    │                           research.py (triggered by NATS: "new_document")
    │                                │ Reads document from filesystem
    │                                │ Sends to Claude Sonnet for analysis
    │                                │ Receives structured signal (Pydantic model)
    │                                │ Stores signal in SQLite signals table
    │                                │ Logs analysis in audit_log table
    │                                │
    │                                ▼
    │                           ntfy.sh push notification
    │                                "New 10-K analysis for AAPL: bullish signal (0.72)"
    │
    └─── If no new filings ───▶ (silent, no action)
```

**Trigger**: Schedule (systemd timer, every 15 min during market hours)
**Data format**: JSON messages via NATS between Python processes
**Safety check**: N/A for research ingestion (no trading)

### Scenario 2: Evening Research Session via Claude Desktop

```
Human opens Claude Desktop
    │
    ▼
"What's the latest research on AAPL?"
    │
    ▼
Claude uses Research DB MCP tool: get_signals(ticker="AAPL", limit=5)
    │ → Calls FastMCP server on NUC (via mcp-remote)
    │ → Returns latest 5 signals with timestamps, sources, scores
    │
    ▼
Claude uses Research DB MCP tool: search_documents(query="AAPL", doc_type="10-K")
    │ → Returns list of ingested filings
    │
    ▼
Claude synthesizes: "AAPL has 3 recent signals..."
    │
    ▼
Human: "Compare that with their latest earnings call"
    │
    ▼
Claude uses SEC EDGAR MCP tool: get_company_filings(ticker="AAPL", form_type="10-Q")
    │ → Returns latest quarterly filing sections
    │
    ▼
Claude provides comparative analysis with citations
```

**Trigger**: Human request (on-demand)
**Data format**: MCP/JSON-RPC between Claude Desktop and MCP servers
**Safety check**: N/A (research only, no trading)

### Scenario 3: Human Decides to Place a Trade

```
Human in Claude Desktop: "I want to buy 10 shares of AAPL"
    │
    ▼
Claude uses Research DB MCP: get_safety_state()
    │ → Checks kill switch (must be inactive)
    │ → Checks current position count vs max_positions_per_symbol
    │ → Checks daily trade count vs max_trades_per_day
    │
    ├─── If safety check fails ───▶ Claude: "Cannot trade: [kill switch active / daily limit reached / ...]"
    │
    └─── If safety checks pass ───▶ Claude: "Safety checks pass. Confirming: buy 10 shares AAPL at market?"
                                         │
                                         ▼
                                    Human: "Yes, confirm"
                                         │
                                         ▼
                                    Claude uses Alpaca MCP: place_stock_order(
                                         symbol="AAPL", qty=10, side="buy", type="market"
                                    )
                                         │
                                         ▼
                                    Claude: "Order placed. Order ID: xyz, Status: accepted"
                                         │
                                         ▼
                                    (Audit: order logged in audit_log via MCP or separate call)
```

**Trigger**: Human request (on-demand)
**Data format**: MCP/JSON-RPC
**Safety check**: Kill switch + risk limits checked BEFORE order placement (FR-007). Human must explicitly confirm. Safety state read from SQLite `safety_state` table via Research DB MCP.

---

## Build vs. Buy Decisions (US3: FR-003, FR-010)

| Capability | Decision | Rationale | Alternatives Rejected |
|-----------|----------|-----------|----------------------|
| **Trading execution** | Buy: Alpaca MCP Server (43 tools) | Official, production-ready, zero custom code | alpaca-py SDK direct calls (more code, less interactive) |
| **SEC filing access** | Buy: sec-edgar-mcp + edgartools | sec-edgar-mcp for Claude Desktop; edgartools for automated pipeline | Custom SEC API wrapper (reinventing wheel) |
| **Research DB access** | Build: Custom FastMCP server (~100 LOC) | No existing MCP server for our specific SQLite schema | Generic sqlite MCP (doesn't know our schema) |
| **LLM analysis** | Buy: Claude API via anthropic SDK | Already committed to Claude; SDK handles structured output | OpenAI, local models (not as capable for financial reasoning) |
| **Agent orchestration** | Build: Claude Agent SDK + custom scripts (~600 LOC) | SDK provides tool execution + context management; we add domain logic | LangGraph (overkill), CrewAI (less control), n8n (language mismatch) |
| **Scheduling** | Buy: systemd timers (built-in) | Zero overhead, native to Linux | n8n (500MB+ RAM, memory leaks), Airflow (4-8GB RAM), Prefect (needs PostgreSQL) |
| **Notifications** | Buy: ntfy.sh (self-hosted) | 3 lines of Python for mobile push | n8n notifications (500MB+ overhead for a POST request), Slack bot (more setup) |
| **Event messaging** | Buy: NATS (already running) | Already on NUC, lightweight, reliable | Redis (heavier), RabbitMQ (heavier), direct function calls (less decoupled) |
| **Macro data** | Buy: FRED API (free) | Gold standard for US economic data | BLS API (harder to use), Treasury.gov (subset of FRED) |
| **News data** | Buy: Finnhub + Tiingo (both free) | Two complementary sources, ticker-tagged | Benzinga (enterprise pricing), NewsAPI (too broad) |
| **Structured output** | Buy: Pydantic AI (v1, production) | Type-safe LLM outputs, already using Pydantic | Manual JSON parsing (error-prone), LangChain (heavy) |

**Score**: 9 of 11 capabilities use off-the-shelf tools (82%), exceeding the 60% target (SC-003). The 2 "Build" items (Research DB MCP, Agent orchestration) still leverage off-the-shelf frameworks (FastMCP, Claude Agent SDK) — the custom code is domain-specific glue.

### Existing Python Pipeline Verdict (FR-004)

| Module | LOC | Verdict | Rationale |
|--------|-----|---------|-----------|
| `data/sources/` | ~800 | **Keep + extend** | Add FRED, Tiingo, SEC RSS sources |
| `data/storage.py` | ~200 | **Keep as-is** | Working filesystem storage |
| `data/models.py` | ~300 | **Keep + extend** | Add models for new data types |
| `research/analyzer.py` | ~500 | **Keep as-is** | LLM analysis pipeline works |
| `research/orchestrator.py` | ~400 | **Keep + refactor** | Add agent framework integration |
| `research/signals.py` | ~200 | **Keep + extend** | Add signal types for new sources |
| `research/prompts.py` | ~300 | **Keep + extend** | Add prompts for new content types |
| `safety/guards.py` | ~200 | **Keep as-is** | Kill switch + risk limits working |
| `cli.py` | ~600 | **Keep + extend** | Add agent management commands |
| `config.py` | ~150 | **Keep + extend** | Add new API key configs |

**Total existing code preserved**: 100% (no regressions per FR-004).

---

## Phased Implementation Roadmap (US4: FR-008)

### Phase 1: MCP Integration (Small — ~1 week)

**Goal**: Connect Claude Desktop to the existing research database and Alpaca trading.

**Deliverables**:
- Custom FastMCP server exposing research DB (~100 LOC)
- Claude Desktop configuration with 3 MCP servers (Alpaca, SEC EDGAR, Research DB)
- Safety check tool in Research DB MCP (reads `safety_state` before trades)
- Documentation for MCP server setup

**Definition of Done**: Human can open Claude Desktop, query research signals by ticker, browse ingested documents, check safety state, and place a paper trade — all through conversation.

**Dependency**: None (works with existing data in SQLite).

### Phase 2: Data Source Expansion (Small — ~1 week)

**Goal**: Add free data sources that improve research quality.

**Deliverables**:
- FRED macro data source (`fredapi` integration)
- Tiingo news source (free tier)
- SEC RSS feed monitoring (via `feedparser`)
- 13F institutional holdings tracking (extend `edgartools` usage)
- Form 4 insider trade parsing (extend `edgartools` usage)

**Definition of Done**: `finance-agent research run` ingests data from all new sources. FRED macro indicators are available in research context. SEC RSS detects new filings within 15 minutes.

**Dependency**: None (extends existing pipeline).

### Phase 3: Agent Framework (Medium — ~2 weeks)

**Goal**: Autonomous monitoring and analysis agents running on the NUC.

**Deliverables**:
- Monitor agent (SEC RSS polling, new data detection)
- Scanner agent (news triage with Haiku)
- Deep research agent (on-demand company analysis with Sonnet)
- Briefing agent (daily summary generation)
- systemd timer configurations
- NATS message contracts for inter-agent communication
- ntfy.sh integration for push notifications

**Definition of Done**: Agents run autonomously on the NUC. Monitor detects new SEC filings within 15 minutes. Scanner triages news hourly. Daily briefing arrives via ntfy push at 6am ET. All activity logged in audit trail.

**Dependency**: Phase 2 (agents need the expanded data sources to be useful).

### Phase 4: Refinement & Paid Sources (Small — ~1 week)

**Goal**: Add paid data sources and optimize the pipeline.

**Deliverables**:
- Quiver Quantitative integration ($25/mo — congressional trading + social sentiment)
- Prompt caching optimization (reduce API costs)
- Model routing (Haiku for triage, Sonnet for analysis)
- Agent error handling and recovery
- Performance monitoring dashboard (CLI-based)

**Definition of Done**: Congressional trading signals available in research context. API costs reduced by 30%+ via caching. Agents recover gracefully from API failures.

**Dependency**: Phase 3 (agents must exist before optimizing them).

### Roadmap Summary

| Phase | Scope | Duration | Standalone Value | Dependencies |
|-------|-------|----------|-----------------|--------------|
| 1: MCP Integration | Small | ~1 week | Yes — conversational trading + research | None |
| 2: Data Sources | Small | ~1 week | Yes — richer research signals | None |
| 3: Agent Framework | Medium | ~2 weeks | Yes — autonomous monitoring + analysis | Phase 2 |
| 4: Refinement | Small | ~1 week | Yes — better data + lower costs | Phase 3 |

Each phase delivers a working increment (SC-004). No phase requires more than 2 weeks (accounting for AI-assisted development). Phase 1 builds on existing data (the existing research pipeline already has signals in SQLite).

---

## Data Source Expansion Plan (US5: FR-009)

### Current Sources (6 API-integrated)

| Source | Data Type | Library | Cost | Notes |
|--------|-----------|---------|------|-------|
| SEC EDGAR (filings) | 10-K, 10-Q, 8-K | edgartools | Free | Primary filing source |
| SEC EDGAR (XBRL) | Financial statements | edgartools | Free | Structured financial data |
| Finnhub (market signals) | Analyst ratings, earnings, insider, news | finnhub-python | Free tier | Transcript endpoint requires $3K/mo premium — use EarningsCall.biz instead |
| EarningsCall.biz | Earnings call transcripts | earningscall | Free (demo) / paid | Speaker-attributed transcripts; replaces Finnhub transcripts |
| Alpaca | Market data (bars, quotes, trades) | alpaca-py | Free | Paper + live trading |
| RSS feeds | Financial news | feedparser | Free | General news ingestion |

**Manually consumed** (not API-integrated): Acquired podcast, Stratechery newsletter — used for qualitative context during human research sessions.

### New Sources (7 additional — exceeds SC-005 target of 5)

| Priority | Source | Data Type | Library | Cost | Value |
|----------|--------|-----------|---------|------|-------|
| **P1** | FRED | Macro indicators (10+ series) | fredapi | Free | Economic context for all research |
| **P1** | Tiingo News | Ticker-tagged financial news | tiingo / httpx | Free | Complements Finnhub news |
| **P1** | SEC RSS | Real-time filing notifications | feedparser | Free | Filing detection within 10-15 min |
| **P2** | 13F Holdings | Institutional investor positions | edgartools | Free | Track Buffett, Burry, etc. |
| **P2** | Form 4 | Insider buy/sell transactions | edgartools | Free | Insider trading signals |
| **P3** | Quiver Quantitative | Congressional trading + social sentiment | quiver-python | $25/mo | Unique alpha signal |
| **P3** | YouTube transcripts | Financial channel analysis | youtube-transcript-api | Free | Qualitative research context |

### Autonomous Discovery (SC-005, scenario 2)

The **SEC RSS monitoring** constitutes proactive crawling — the system monitors SEC EDGAR's RSS feed every 15 minutes and automatically triggers ingestion + analysis when new filings appear for watchlist companies. This is not a scheduled API pull; it's event-driven discovery of new documents.

Future enhancement: monitor financial news RSS feeds (Bloomberg, Reuters, WSJ) for company mentions and automatically trigger research when a watchlist company appears in breaking news.

### Evaluation Criteria for New Sources

Each new source is evaluated against:
1. **Data uniqueness**: Does it provide information not available from existing sources?
2. **Integration effort**: How many lines of code to add? Does a library exist?
3. **Cost vs. value**: Is the data worth the subscription cost?
4. **Maintenance burden**: Will it break frequently? API stability?
5. **Research quality impact**: Does it meaningfully improve LLM analysis?

---

## Edge Cases (from spec)

| Edge Case | Mitigation |
|-----------|-----------|
| **NUC offline/rebooting** | systemd timers auto-resume on boot. SQLite WAL mode handles unclean shutdowns. NATS has durable subscriptions for message replay. No data loss — just delayed processing. |
| **MCP server unavailable during Claude Desktop session** | Claude Desktop shows tool as unavailable. User can still use other MCP servers. Graceful degradation — not a crash. |
| **Conflicting research signals** | Display all signals with source attribution. The human resolves conflicts. LLM can present both bullish and bearish perspectives but does not auto-resolve. |
| **Data source API changes** | Each source is an independent module. API changes affect only that module. edgartools library handles SEC format changes upstream. Version-pin dependencies. |
| **Disaster recovery for SQLite** | Daily automated backup (cp + journal flush) to a second location on NUC. Git-tracked schema migrations for rebuilding. Research artifacts in filesystem are independently recoverable. |

---

## Complexity Tracking

No constitution violations to justify. All decisions align with principles:
- Safety First: Safety checks via MCP before any trade
- Research-Driven: All data sources cited in analysis
- Modular Architecture: Independent layers, off-the-shelf tools, ~900 LOC new code
- Audit Everything: All activity logged
- Security by Design: Secrets in env vars, paper/live separation
- Less Code More Context: 82% buy rate, systemd over n8n, FastMCP over custom protocol

---

## Architecture Decision Notes

### n8n Orchestration — Evaluated and Rejected for Core Use (2026-02-17)

**Context**: n8n was originally listed in the constitution as the orchestration layer. After Phase 0 research and operator review, it was rejected for core orchestration but remains viable as a future notification sidecar.

**Weak arguments (not the real reasons)**:
- RAM overhead (~500MB-1GB) — NUC has 32GB, this is irrelevant (~3%)
- Security CVE (sandbox bypass) — NUC runs locally on home WiFi, not internet-exposed; Claude maintains workflows, so attack surface is minimal

**Strong arguments (the actual decision drivers)**:
1. **Claude Code can't maintain n8n workflows** — Workflows are JSON blobs edited in a browser UI. Claude Code (the primary development tool) cannot create, modify, or debug them. Every workflow change requires leaving the Claude Code loop and using the n8n visual editor manually.
2. **Language split** — Core logic is Python. n8n would either call Python scripts (making it a fancy cron) or try to run Python in its Code node (second-class support). The logic stays in Python regardless.
3. **Version control** — Python scripts are git-native `.py` files. n8n workflows are opaque JSON exports that are hard to diff/review meaningfully.

**Where n8n adds genuine value** (Tier 3, future consideration):
- Multi-channel notification routing (Slack + email + Telegram + Google Sheets) — trivial in n8n, ~50 LOC per channel in Python
- Visual execution monitoring dashboard
- If notification needs grow beyond ntfy.sh mobile push, n8n as a sidecar specifically for notifications is a reasonable addition

**Operator decision**: systemd timers + Python for core orchestration. ntfy.sh for notifications. Revisit n8n only if multi-channel notification routing becomes a priority.

### Data Sources — Reddit/StockTwits Deferred (2026-02-17)

**Context**: Reddit (PRAW) and StockTwits (REST API) were listed in the constitution's Technology Stack but removed during 008 architecture alignment because they aren't in the current architecture plan.

**Rationale**: Not rejected — deferred. Higher-value free sources (FRED, Tiingo, SEC RSS, 13F, Form 4) were prioritized first. Social sentiment analysis via Reddit/StockTwits can be added in a future data source expansion feature if it becomes a research priority.

### QuantConnect / sqlite-vec — Removed from Constitution (2026-02-17)

**QuantConnect**: Was listed as a planned MCP server for backtesting. Removed because backtesting is not in the current architecture scope. Can be re-added when a backtesting feature is specified.

**sqlite-vec**: Was listed for vector search. Removed because the current architecture doesn't require embedding-based search. If semantic search of research artifacts becomes valuable (e.g., "find all filings discussing supply chain risk"), sqlite-vec can be re-evaluated.
