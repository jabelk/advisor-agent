# Architecture Proposal — Research-Powered Investment System

## Executive Summary

Pivot from an automated trading bot (features 001-005) to a **research-powered investment system** where autonomous agents discover and analyze information, Claude synthesizes research into actionable analysis, and the human makes the final trading decisions through conversation.

**Core insight**: The differentiator isn't execution (Alpaca MCP handles that in one tool call) — it's the quality, breadth, and timeliness of research.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Intel NUC (Home Server)                   │
│                                                                  │
│  ┌─────────────┐    ┌──────────────────────────────────────┐    │
│  │   n8n        │    │  Python Application                  │    │
│  │ (orchestrator)│   │                                      │    │
│  │             │    │  ┌────────────┐  ┌────────────────┐  │    │
│  │ - Schedules │───▶│  │ Data       │  │ Research        │  │    │
│  │ - RSS feeds │    │  │ Ingestion  │  │ Pipeline        │  │    │
│  │ - Webhooks  │    │  │            │  │                 │  │    │
│  │ - AI Agents │    │  │ SEC EDGAR  │  │ Claude Agent SDK│  │    │
│  │ - Alerts    │    │  │ Finnhub    │  │ Summarization   │  │    │
│  │             │    │  │ Tiingo     │  │ Signal Gen      │  │    │
│  └──────┬──────┘    │  │ FRED       │  │ Bull/Bear       │  │    │
│         │           │  │ RSS/News   │  │ Analysis        │  │    │
│         │           │  │ Reddit     │  │                 │  │    │
│         │           │  │ StockTwits │  │                 │  │    │
│         │           │  └─────┬──────┘  └───────┬─────────┘  │    │
│         │           │        │                  │            │    │
│         │           │        ▼                  ▼            │    │
│         │           │  ┌─────────────────────────────────┐  │    │
│         │           │  │         SQLite + Files           │  │    │
│         │           │  │  - Research signals              │  │    │
│         │           │  │  - Filing summaries              │  │    │
│         │           │  │  - Audit trail                   │  │    │
│         │           │  │  - sqlite-vec (embeddings)       │  │    │
│         │           │  └──────────────┬──────────────────┘  │    │
│         │           │                 │                      │    │
│         │           │                 ▼                      │    │
│         │           │  ┌─────────────────────────────────┐  │    │
│         │           │  │    Custom MCP Server             │  │    │
│         │           │  │  (domain-specific tools)         │  │    │
│         │           │  │  - get_research_summary()        │  │    │
│         │           │  │  - get_signals()                 │  │    │
│         │           │  │  - get_watchlist()               │  │    │
│         │           │  └─────────────────────────────────┘  │    │
│         │           └──────────────────────────────────────┘    │
│         │                                                        │
│  ┌──────▼──────┐                                                │
│  │  ntfy.sh    │◀── Push notifications to phone                 │
│  └─────────────┘                                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

                              │
                              │ MCP Protocol
                              ▼

┌──────────────────────────────────────────────────────────────┐
│                    Claude Desktop / Claude Code                │
│                                                                │
│  Connected MCP Servers:                                        │
│  ├── Alpaca MCP (43 tools — trading + market data)            │
│  ├── Custom Research MCP (our SQLite research DB)             │
│  ├── QuantConnect MCP (backtesting)                           │
│  └── sec-edgar-mcp (filing lookup)                            │
│                                                                │
│  User Interaction:                                             │
│  "Show me the research summary for AAPL this week"            │
│  "What are the bull and bear cases for MSFT?"                 │
│  "Buy 10 shares of AAPL at $185 limit"                       │
│  "Backtest this strategy on NVDA over the last year"          │
└──────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. n8n (Workflow Orchestrator)

**Role**: Schedule data ingestion, trigger research pipelines, send notifications. Runs on NUC via Docker Compose alongside PostgreSQL.

**Workflows**:
| Workflow | Trigger | Action |
|----------|---------|--------|
| SEC Filing Monitor | RSS (every 15 min, market hours) | Detect new filings → call Python ingestion → alert if 8-K |
| News Aggregator | RSS + Schedule (every 30 min) | Collect Finnhub + Tiingo news → deduplicate → store |
| Daily Research Run | Schedule (7 AM EST) | Run full research pipeline for watchlist → generate briefing |
| Evening Briefing | Schedule (6 PM EST) | Summarize day's findings via Claude → push to ntfy.sh |
| Price Alert | Webhook (from Alpaca) | Check for > 3% moves on watchlist → alert if held position |

### 2. Data Ingestion Layer (Python)

**Role**: Fetch, parse, and store raw data from all sources.

**Sources** (Phase 1 — all free):
| Source | Library | Data |
|--------|---------|------|
| SEC EDGAR | edgartools | 10-K, 10-Q, 8-K filings + Form 4 (insider) + 13F (institutional) |
| Finnhub | finnhub-python | Market signals (analyst ratings, earnings history, insider activity, news) |
| Tiingo | tiingo (Python) | Ticker-tagged news articles |
| FRED | fredapi | Macro indicators (yields, CPI, VIX, unemployment, etc.) |
| RSS Feeds | feedparser | SEC EDGAR, CNBC, Fed, arXiv q-fin, Substack |
| Reddit | PRAW | r/wallstreetbets, r/stocks sentiment |
| StockTwits | REST API (httpx) | Pre-labeled bull/bear sentiment |

**What to keep from 001-005**: SEC EDGAR source (edgartools), storage manager, `filter_10k_markdown()`, SQLite schema + migrations.

**What to remove**: Custom execution layer (641 lines), deterministic scoring engine, 1,600-line CLI.

### 3. Research Pipeline (Python + Claude)

**Role**: Analyze ingested data, produce structured signals with citations.

**Key patterns**:

1. **Pre-summarization**: Raw filing (80K tokens) → section summaries (2K each) → company brief (500 tokens) → metrics JSON (200 tokens). Store at all levels.

2. **Bull/Bear debate** (borrowed from TradingAgents): For each watchlist company, Claude analyzes from both bullish and bearish perspectives before producing a final signal. Reduces confirmation bias.

3. **Prompt caching**: Static research context goes first in prompts (cached at 0.1x cost), user question goes last.

4. **RAG for specifics**: sqlite-vec for vector search over filing chunks. Hybrid retrieval (semantic + FTS5 keyword). Cross-encoder reranking.

### 4. Custom MCP Server

**Role**: Expose research DB to Claude Desktop/Code via domain-specific tools.

**Tools** (~10-15, built with FastMCP):
- `get_watchlist()` — current watchlist with latest signals
- `get_research_summary(symbol, days)` — research summary for a ticker
- `get_signals(symbol, signal_type)` — recent signals, filterable
- `get_filing_summary(symbol, filing_type)` — summarized SEC filings
- `get_macro_context()` — current macro indicators from FRED
- `get_insider_activity(symbol, days)` — recent Form 4 transactions
- `search_research(query)` — semantic search over research artifacts

**Resources** (loaded into context automatically):
- Watchlist with basic stats
- Portfolio positions
- Risk limit status

### 5. Notification System (ntfy.sh)

**Role**: Push alerts to mobile. Self-hosted on NUC.

**Priority tiers**:
| Priority | Delivery | Examples |
|----------|----------|---------|
| Critical | Immediate push | Kill switch trigger, daily loss limit approaching, 8-K from held position |
| High | Push within 15 min | > 5% price move on held position, earnings surprise |
| Normal | Batched in evening briefing | New filings processed, routine analysis complete |
| Low | Logged only | Data ingestion success, scheduled jobs completing |

### 6. Safety Layer (Python — kept from 001-005)

**Role**: Hard programmatic limits that can't be LLM-only.

**Kept**:
- Kill switch (single flag halts all orders)
- Position size limits (% of portfolio per symbol)
- Daily loss limits (% of portfolio)
- Trade count limits
- Limit-orders-only default

**Enforcement**: These checks run at the execution boundary, whether the trade originates from MCP conversation or programmatic agent. They are NOT delegated to the LLM.

---

## What Changes from 001-005

### Keep (Refactor)
| Component | Lines | Action |
|-----------|-------|--------|
| `data/sources/sec_edgar.py` | 115 | Keep, enhance with Form 4 + 13F |
| `data/storage.py` | ~200 | Keep, add new source types |
| `data/models.py` | ~100 | Keep, extend for new data types |
| `data/watchlist.py` | ~80 | Keep as-is |
| `research/signals.py` | ~150 | Keep, add new signal types |
| `research/prompts.py` | ~200 | Keep, add bull/bear debate prompts |
| `config.py` | ~100 | Keep, add new API keys (FRED, Tiingo) |
| `db.py` | ~100 | Keep, add new migrations |
| Safety checks (from engine/) | ~100 | Extract and keep risk limit checks |

### Remove
| Component | Lines | Replaced By |
|-----------|-------|-------------|
| `execution/orders.py` | 641 | Alpaca MCP server (one tool call) |
| `execution/reconcile.py` | ~200 | Alpaca MCP position queries |
| `execution/status.py` | ~150 | Alpaca MCP order status |
| `engine/scoring.py` | ~300 | Conversational Claude analysis |
| `engine/proposals.py` | ~400 | Human decision in conversation |
| `cli.py` | 1,600 | Claude Desktop as interface |
| `market/bars.py` | ~300 | Alpaca MCP or lightweight wrapper |
| `market/indicators.py` | ~200 | MaverickMCP or QuantConnect |

### Add (New)
| Component | Purpose |
|-----------|---------|
| `mcp/research_server.py` | Custom MCP server for research DB |
| `data/sources/tiingo.py` | Tiingo news ingestion |
| `data/sources/fred.py` | FRED macro data ingestion |
| `data/sources/reddit.py` | Reddit sentiment via PRAW |
| `data/sources/stocktwits.py` | StockTwits sentiment |
| `data/sources/rss_monitor.py` | Generic RSS feed monitor |
| `research/debate.py` | Bull/bear analysis pattern |
| `research/summarizer.py` | Multi-level pre-summarization |
| `research/rag.py` | sqlite-vec RAG pipeline |
| FastAPI sidecar | Endpoint for n8n to call |

---

## Technology Stack Update

| Concern | 001-005 | Proposed |
|---------|---------|----------|
| Orchestration | CLI commands + cron | n8n (Docker on NUC) |
| User interface | Custom CLI (1,600 lines) | Claude Desktop + MCP servers |
| Execution | Custom orders.py (641 lines) | Alpaca MCP server |
| Decision making | Deterministic scoring formula | Conversational Claude analysis |
| Market data | Custom bars.py + indicators.py | Alpaca MCP + QuantConnect MCP |
| News | Finnhub only | Finnhub + Tiingo + RSS feeds |
| Social | None | Reddit (PRAW) + StockTwits |
| Macro | None | FRED API (fredapi) |
| Insider data | None | edgartools Form 4 parsing |
| Vector search | None | sqlite-vec extension |
| Notifications | None | ntfy.sh (self-hosted) |
| Backtesting | None | QuantConnect MCP (free tier) |
| Agent framework | None | Claude Agent SDK |

---

## Implementation Phases

### Phase 1: Foundation (Next Feature)
- Strip out execution/scoring/CLI layers
- Add new data sources (Tiingo, FRED, RSS monitor)
- Build custom MCP server for research DB
- Set up ntfy.sh on NUC

### Phase 2: Research Pipeline
- Implement pre-summarization pipeline
- Add bull/bear debate analysis
- Integrate sqlite-vec for RAG
- Add Reddit + StockTwits ingestion

### Phase 3: Orchestration
- Deploy n8n on NUC
- Build scheduled workflows (SEC monitor, daily briefing, evening summary)
- Set up FastAPI sidecar for n8n → Python communication

### Phase 4: Backtesting & Validation
- Connect QuantConnect MCP
- Install MaverickMCP as complementary tool
- Paper trading validation of research quality

### Phase 5: Semi-Autonomous (Later)
- Trade proposals via notification
- Human approval via Telegram/ntfy response
- Performance tracking (proposed vs. actual)

---

## Monthly Cost Estimate

| Phase | Components | Cost |
|-------|-----------|------|
| Phase 1-2 | Claude API tokens + free data sources | $10-20/mo |
| Phase 3 | + n8n (free, self-hosted) | $10-20/mo |
| Phase 4 | + QuantConnect (free tier) | $10-20/mo |
| Optional | + Quiver Quantitative (congressional trading) | +$25/mo |
| Optional | + FMP Ultimate (consolidated data) | +$149/mo |

All infrastructure runs on the existing Intel NUC. No cloud costs.
