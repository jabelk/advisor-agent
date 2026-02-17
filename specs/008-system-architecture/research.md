# Phase 0 Research: System Architecture Design

**Feature**: 008-system-architecture | **Date**: 2026-02-17

---

## Research Area 1: MCP Server Ecosystem

### Decision: Use Alpaca MCP + SEC EDGAR MCP + Custom FastMCP Research Server

**Rationale**: MCP servers let Claude Desktop directly query data and execute trades via natural language. Three servers cover the core needs without excessive token overhead (~56 tools total).

**Alternatives Considered**:
- Yahoo Finance MCP (experimental, scraping-based — skipped for reliability)
- MaverickMCP (39+ tools, impressive but overlaps with Alpaca + adds Tiingo dependency)
- Finnhub MCP (only 2 stars, too immature)
- FMP MCP (requires $149/mo subscription)

### Specific MCP Servers

| Server | Tools | Transport | Maturity | Cost |
|--------|-------|-----------|----------|------|
| **Alpaca MCP** (official) | 43 (trading, positions, market data) | stdio | Production | Free |
| **sec-edgar-mcp** (stefanoamorelli) | ~8 (filings, financials, insider) | stdio/Docker | Stable (v1.0.8) | Free (AGPL) |
| **Custom Research DB** (FastMCP) | ~5-8 (signals, watchlist, documents) | stdio or HTTP | We build it | Free |

### Claude Desktop Configuration

All three servers configured in `claude_desktop_config.json`. Multiple stdio servers supported natively. Remote access (NUC → Claude Desktop) via `mcp-remote` proxy or Claude.ai Connectors.

### Token Budget Warning

Each MCP server adds tool definitions to context. At ~56 tools, this is manageable but should be monitored. Do not exceed ~10 servers without pruning.

---

## Research Area 2: Orchestration & Scheduling

### Decision: Cron/systemd + Python (NOT n8n)

**Rationale**: n8n is not the right fit for this project:
1. **Language mismatch** — entire codebase is Python; n8n is Node.js. Running Python in n8n is second-class (import restrictions, CVE-2025-68668 sandbox bypass, performance overhead)
2. **Memory overhead** — n8n uses 500MB–1.1GB at idle with reported memory leaks (fresh install crashes after 7 days). Wastes NUC resources
3. **Architectural split** — would split logic between Python research code and n8n's JS/LangChain runtime
4. **Workflow mismatch** — development happens in Claude Code (code-first), not n8n's visual builder

**Alternatives Considered**:

| Option | RAM Overhead | Python Integration | Complexity | Verdict |
|--------|-------------|-------------------|------------|---------|
| **Cron/systemd + Python** | ~0 MB | Native | Minimal | **CHOSEN** |
| n8n | 500MB–1.1GB | Poor (Node.js) | Medium | Rejected |
| Prefect | 2–4 GB + PostgreSQL | Excellent (@flow/@task) | Medium | Future Tier 2 |
| Apache Airflow | 4–8 GB + PostgreSQL + Redis | Native (DAGs = Python) | High | Overkill |
| Temporal | Cluster + PostgreSQL | Good (Python SDK) | Very High | Wrong tool |

### n8n: Retained for Notifications Only (Optional Tier 3)

n8n's value is in connecting SaaS services (Slack, email, Telegram) visually. If needed later, it could run as a sidecar specifically for notifications and monitoring dashboards — not for core pipeline orchestration.

### Notification Strategy

Use **ntfy.sh** (self-hosted on NUC) for push notifications. A single `httpx.post("https://ntfy.sh/your-topic", ...)` call (3 lines of Python) replaces n8n's entire notification stack for the common case.

---

## Research Area 3: Agent Frameworks

### Decision: Claude Agent SDK (primary) + Pydantic AI (validation/structured output)

**Rationale**: The Claude Agent SDK is the most natural fit — it gives Claude Code's entire toolchain (file I/O, bash, web search, MCP integration) without boilerplate. Pydantic AI adds type-safe structured output validation. Together they cover the full spectrum: SDK for research orchestration, Pydantic for validated signal/analysis models.

**Alternatives Considered**:

| Framework | Claude Support | Boilerplate | Multi-Agent | Solo Dev Fit | Verdict |
|-----------|--------------|-------------|-------------|--------------|---------|
| **Claude Agent SDK** | Native | Low | Yes (subagents) | Best | **Primary** |
| **Pydantic AI** | First-class | Low | Partial | Good | **Complement** |
| LangGraph | Via ChatAnthropic | High | First-class | Overkill | Skip |
| CrewAI | Via LiteLLM | Low | Primary purpose | Decent | Skip |
| AutoGen | Via adapters | Medium | Primary purpose | Too complex | Skip |
| Smolagents | Via LiteLLM | Very low | Limited | Immature | Skip |

### Claude Agent SDK Details

- **Version**: 0.1.36 (alpha) — API evolving but underlying agent loop is battle-tested (powers Claude Code)
- **Key capabilities**: Built-in tools (Read, Write, Bash, Grep, WebSearch), custom tools via `@tool` decorator, MCP server integration, subagent support, automatic context compaction
- **Limitation**: No built-in daemon mode — wrap in Python loop/scheduler. State between sessions must be persisted manually (files, DB)

### Anthropic's Recommended Patterns (from official engineering blog)

Five composable patterns in order of complexity:
1. **Prompt Chaining** — sequential LLM steps (e.g., extract metrics → generate thesis)
2. **Routing** — classify input → specialized handler (e.g., route filings by type)
3. **Parallelization** — multiple analysis perspectives simultaneously
4. **Orchestrator-Workers** — dynamic task breakdown and delegation
5. **Evaluator-Optimizer** — generate + critique loop

**Mapping to our system**:
- Monitoring agent = Workflow (routing pattern)
- Deep research agent = Agent (orchestrator-workers)
- Daily briefing = Workflow (prompt chaining)

### Cost Estimates (Claude API)

| Component | Model | Frequency | Monthly Cost |
|-----------|-------|-----------|-------------|
| Monitoring (triage) | Haiku 4.5 | Hourly (market hours) | ~$0.50 |
| Daily briefings | Sonnet 4.5 | Once daily | ~$1.60 |
| Deep research | Sonnet 4.5 | 10 companies/month | ~$35–75 |
| Ad-hoc analysis | Sonnet 4.5 | As needed | ~$10–20 |
| **Total** | | | **~$50–100/month** |

Cost reduction: Prompt caching (90% savings on cached input), batch processing (50% off), model routing (Haiku for triage, Sonnet for analysis).

---

## Research Area 4: Data Source Expansion

### Decision: Phased expansion from $0/mo to $25/mo to $149/mo

### Phase 1: Free Sources (Add Immediately)

| Source | Data Type | Library | Integration |
|--------|-----------|---------|-------------|
| **FRED** | Macro indicators (10+ series) | `fredapi` | New — high value, trivial |
| **Tiingo** (free tier) | Ticker-tagged news | `tiingo` or HTTP | New — complements Finnhub |
| **13F tracking** | Institutional holdings | `edgartools` (existing) | Extend existing code |
| **Form 4 parsing** | Insider trades | `edgartools` (existing) | Extend existing code |
| **SEC RSS feeds** | Filing notifications | `feedparser` (existing) | New — 10-min update cycle |

### Phase 2: Paid Sources ($25/mo)

| Source | Data Type | Cost | Value |
|--------|-----------|------|-------|
| **Quiver Quantitative** | Congressional trading + social sentiment | $25/mo | Genuinely differentiated signal |

### Phase 3: Consolidation ($149/mo, if needed)

| Source | Data Type | Cost | Value |
|--------|-----------|------|-------|
| **FMP Ultimate** | Transcripts + 13F + social + fundamentals | $149/mo | All-in-one, replaces multiple |

### Sources Evaluated and Skipped

- **Options flow** (Unusual Whales $50/mo) — not aligned with weekly research cadence
- **Satellite/app/credit card data** — institutional pricing ($25K+/yr)
- **SimilarWeb API** ($199/mo) — use free web checker manually
- **Benzinga** (enterprise pricing) — too expensive for research pace
- **Automated podcast ingestion** — manual for now; `youtube-transcript-api` later if needed
- **Seeking Alpha** — no real programmatic API access

### Key FRED Series for Research Context

`UNRATE`, `DGS10`, `DGS2`, `T10Y2Y`, `CPIAUCSL`, `M2SL`, `FEDFUNDS`, `DTWEXBGS`, `VIXCLS`, `ICSA`

---

## Research Area 5: Architecture Patterns

### Decision: Event-driven Python processes on NUC + MCP for human interaction

### Architecture Overview

The system is organized around **four runtime contexts**:

1. **Intel NUC (always-on)** — Python scripts triggered by systemd timers, NATS for event passing, SQLite + filesystem for storage
2. **Claude Desktop (human sessions)** — MCP servers expose research DB, SEC EDGAR, and Alpaca trading to the human via conversation
3. **Anthropic API (cloud)** — Claude inference for all LLM-powered analysis
4. **External APIs** — SEC EDGAR, Finnhub, Tiingo, FRED, Alpaca, etc.

### NUC Process Model

| Process | Trigger | Function | LLM Usage |
|---------|---------|----------|-----------|
| `monitor.py` | systemd timer, every 15 min | Poll SEC RSS + Finnhub for new data | None (pure HTTP) |
| `scanner.py` | systemd timer, every 1–4 hrs | Fetch news, triage with Haiku | Haiku (cheap triage) |
| `research.py` | On-demand (CLI, NATS msg) | Deep company analysis | Sonnet (analysis) |
| `briefing.py` | systemd timer, daily 6am ET | Synthesize overnight signals | Sonnet (synthesis) |
| `ingest.py` | Triggered by monitor | Download + store filings/transcripts | None (I/O only) |

### Communication Paths

| From | To | Protocol | Data Format |
|------|------|----------|-------------|
| systemd | Python scripts | Process exec | CLI args / env |
| monitor.py | ingest.py | NATS message | JSON (ticker, filing type, URL) |
| scanner.py | SQLite | Direct access | SQL |
| research.py | Anthropic API | HTTPS | JSON (Messages API) |
| Claude Desktop | Research DB MCP | stdio | MCP/JSON-RPC |
| Claude Desktop | Alpaca MCP | stdio | MCP/JSON-RPC |
| Claude Desktop | SEC EDGAR MCP | stdio | MCP/JSON-RPC |
| briefing.py | ntfy.sh | HTTP POST | Text/markdown |

### TradingAgents Pattern (Inspiration, Not Adoption)

The TradingAgents framework (UCLA/MIT, LangGraph-based) uses specialized analyst agents running in parallel with a synthesis/debate step. The **pattern** is valuable (parallel analysis → synthesis) but the **framework** is too heavy. We implement the pattern using Claude Agent SDK subagents.

---

## Research Area 6: Custom FastMCP Server Design

### Decision: Build a ~50–100 line MCP server exposing the SQLite research DB

**Effort**: 1–2 hours. FastMCP handles all protocol mechanics.

### Proposed Tools

| Tool | Description | SQL |
|------|-------------|-----|
| `list_companies` | All tracked companies | `SELECT * FROM companies` |
| `get_signals` | Latest signals for a ticker | `SELECT * FROM signals WHERE ticker = ? ORDER BY created_at DESC` |
| `search_documents` | Search ingested documents | `SELECT ... FROM documents WHERE title LIKE ?` |
| `get_watchlist` | Active watchlist with priorities | `SELECT ... FROM watchlist JOIN companies` |
| `run_query` | Read-only SQL (SELECT only) | User-provided SQL |
| `get_safety_state` | Current safety settings | `SELECT * FROM safety_state` |

### Transport

- **stdio** for Claude Desktop on same machine
- **HTTP** (Streamable HTTP) for remote access from Claude Desktop to NUC via `mcp-remote`

---

## Summary of Decisions

| Area | Decision | Key Rationale |
|------|----------|---------------|
| MCP Servers | Alpaca + SEC EDGAR + Custom Research DB | Covers trading, filings, and research data |
| Orchestration | systemd/cron + Python (not n8n) | Language alignment, zero overhead, simplicity |
| Agent Framework | Claude Agent SDK + Pydantic AI | Native Claude support, type-safe outputs |
| Data Sources (Phase 1) | FRED, Tiingo, 13F, Form 4, SEC RSS | All free, high value |
| Data Sources (Phase 2) | Quiver Quantitative ($25/mo) | Congressional trading is unique alpha |
| Notifications | ntfy.sh (self-hosted) | 3 lines of Python, mobile push |
| Human Interface | Claude Desktop via MCP | Conversational research + trading |
| Deployment | Python processes + SQLite on NUC | Already have the infrastructure |
| n8n | Optional Tier 3 (notifications sidecar) | Not for core pipeline |

---

## Sources

### MCP Ecosystem
- [Alpaca MCP Server](https://github.com/alpacahq/alpaca-mcp-server) | [Docs](https://docs.alpaca.markets/docs/alpaca-mcp-server)
- [SEC EDGAR MCP (stefanoamorelli)](https://github.com/stefanoamorelli/sec-edgar-mcp)
- [FastMCP](https://github.com/jlowin/fastmcp) | [Docs](https://gofastmcp.com/deployment/running-server)
- [mcp-remote (npm)](https://www.npmjs.com/package/mcp-remote)
- [Claude Remote MCP Connectors](https://support.claude.com/en/articles/11503834)

### Agent Frameworks
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) | [PyPI](https://pypi.org/project/claude-agent-sdk/)
- [Building Effective Agents (Anthropic)](https://www.anthropic.com/research/building-effective-agents)
- [Effective Context Engineering (Anthropic)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Effective Harnesses for Long-Running Agents (Anthropic)](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Pydantic AI](https://ai.pydantic.dev/) | [v1 Announcement](https://pydantic.dev/articles/pydantic-ai-v1)
- [TradingAgents](https://github.com/TauricResearch/TradingAgents)

### Orchestration
- [n8n GitHub](https://github.com/n8n-io/n8n) | [Memory Issues](https://github.com/n8n-io/n8n/issues/7939)
- [n8n Python Code Node CVE](https://thehackernews.com/2026/01/new-n8n-vulnerability-99-cvss-lets.html)
- [Prefect Open Source](https://www.prefect.io/prefect/open-source)

### Data Sources
- [FRED API / fredapi](https://github.com/mortada/fredapi)
- [Tiingo](https://www.tiingo.com/about/pricing)
- [Quiver Quantitative](https://www.quiverquant.com/)
- [EdgarTools](https://edgartools.readthedocs.io/) (13F, Form 4)
- [SEC EDGAR RSS Feeds](https://www.sec.gov/about/rss-feeds)
- [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
