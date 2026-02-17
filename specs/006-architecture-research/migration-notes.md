# Migration Notes — 001-005 to New Architecture

## Overview

Features 001-005 built a working end-to-end pipeline (~5,000 lines). The architecture pivot retains the research core (~1,500 lines) and replaces the execution/scoring/CLI plumbing (~3,500 lines) with MCP servers and conversational Claude.

---

## What to Keep

### Core Research Infrastructure (Keep As-Is or Enhance)

| File | Lines | Action | Rationale |
|------|-------|--------|-----------|
| `data/sources/sec_edgar.py` | 115 | **Enhance** — add Form 4 + 13F parsing | edgartools is the right tool, just needs more filing types |
| `data/sources/finnhub.py` | ~200 | **Keep** — already refactored for free-tier signals | Analyst ratings, earnings history, insider activity, news |
| `data/sources/earningscall_source.py` | ~150 | **Keep** — transcript ingestion | Works well for earnings call transcripts |
| `data/sources/__init__.py` (BaseSource) | ~50 | **Keep** — clean interface for sources | Good abstraction for adding new sources |
| `data/models.py` | ~100 | **Enhance** — add models for new data types | SourceDocumentMeta is a good base |
| `data/storage.py` | ~200 | **Enhance** — add new source type subdirs | Filesystem persistence works well |
| `data/watchlist.py` | ~80 | **Keep** | Watchlist management works |
| `data/investors.py` | ~50 | **Enhance** — expand investor tracking | Add 13F quarterly diff logic |
| `research/signals.py` | ~150 | **Enhance** — add new signal types | Signal storage + dedup works well |
| `research/prompts.py` | ~200 | **Enhance** — add bull/bear debate prompts | Prompt templates are the right pattern |
| `research/analyzer.py` | ~200 | **Keep** — Claude-powered analysis | Core analysis logic is sound |
| `research/pipeline.py` | ~150 | **Refactor** — simplify, remove tight coupling | Pipeline pattern is good, execution is too rigid |
| `research/orchestrator.py` | ~200 | **Refactor** — update source registration | Add new sources, remove old coupling |
| `config.py` | ~100 | **Enhance** — add FRED, Tiingo, ntfy keys | Settings pattern works well |
| `db.py` | ~100 | **Keep** — add new migrations | SQLite migration system works |

**Subtotal kept/enhanced**: ~1,500 lines

### Key Algorithms to Preserve

1. **`filter_10k_markdown()`** — Saves significant tokens on every SEC filing. Location: should stay in sec_edgar.py or move to a shared utility.

2. **Document dedup** (`check_document_exists()`) — Prevents re-processing already-ingested documents. Keep in signals.py.

3. **SQLite WAL mode + PRAGMA user_version migrations** — Working migration system. Keep in db.py.

4. **StorageManager filesystem layout** — `research_data/{source_type}/{ticker}/` convention. Keep in storage.py.

---

## What to Remove

### Execution Layer (~1,000 lines)

| File | Lines | Replaced By |
|------|-------|-------------|
| `execution/orders.py` | 641 | Alpaca MCP: `place_order` tool |
| `execution/reconcile.py` | ~200 | Alpaca MCP: `get_positions`, `get_orders` tools |
| `execution/status.py` | ~150 | Alpaca MCP: order status queries |
| `execution/__init__.py` | ~10 | N/A |

**Why remove**: The Alpaca MCP server provides all 43 trading tools. Custom order management code adds maintenance burden and context cost without adding value. One MCP tool call replaces 641 lines.

### Decision Engine (~700 lines)

| File | Lines | Replaced By |
|------|-------|-------------|
| `engine/scoring.py` | ~300 | Conversational Claude analysis (bull/bear debate) |
| `engine/proposals.py` | ~400 | Human decision in conversation |
| `engine/__init__.py` | ~10 | N/A |

**Why remove**: Deterministic scoring formulas can't capture "this CEO's tone shifted in the earnings call" or "this 8-K filing implies a strategic pivot." Conversational Claude analysis with the bull/bear debate pattern is more nuanced and flexible.

**Exception**: Extract the **risk limit checks** from the engine layer and keep them as a standalone safety module. Kill switch, position limits, daily loss limits, and trade count limits must remain as hard programmatic guardrails.

### CLI (~1,600 lines)

| File | Lines | Replaced By |
|------|-------|-------------|
| `cli.py` | 1,600 | Claude Desktop as the interface |

**Why remove**: Claude Desktop + MCP servers provides a conversational interface that's more natural than a CLI with 20+ commands. The user says "show me research on AAPL" instead of `finance-agent research show --ticker AAPL --days 7 --format table`.

**Exception**: Keep a minimal CLI for:
- `finance-agent ingest` — trigger data ingestion (useful for cron/n8n)
- `finance-agent serve` — start the FastAPI sidecar for n8n
- `finance-agent migrate` — run database migrations
- `finance-agent status` — health check

### Market Data Layer (~500 lines)

| File | Lines | Replaced By |
|------|-------|-------------|
| `market/bars.py` | ~300 | Alpaca MCP stock data tools |
| `market/indicators.py` | ~200 | MaverickMCP or QuantConnect MCP |
| `market/__init__.py` | ~10 | N/A |

**Why remove**: Alpaca MCP provides 7 stock data tools and 8 crypto data tools. MaverickMCP wraps VectorBT with 20+ technical indicators. Custom indicator calculation code is redundant.

---

## What to Add

### New Data Sources

| File | Purpose | Library |
|------|---------|---------|
| `data/sources/tiingo.py` | Ticker-tagged news (free tier) | `tiingo` |
| `data/sources/fred.py` | Macro indicators | `fredapi` |
| `data/sources/reddit.py` | Reddit sentiment | `praw` |
| `data/sources/stocktwits.py` | StockTwits sentiment | `httpx` (REST API) |
| `data/sources/rss_monitor.py` | Generic RSS feed monitor | `feedparser` (already a dep) |

### New Research Components

| File | Purpose |
|------|---------|
| `research/debate.py` | Bull/bear adversarial analysis pattern |
| `research/summarizer.py` | Multi-level pre-summarization (filing → section → brief → metrics) |
| `research/rag.py` | sqlite-vec RAG pipeline for specific questions |

### MCP Server

| File | Purpose |
|------|---------|
| `mcp/research_server.py` | Custom MCP server exposing research DB via domain-specific tools |

### Infrastructure

| File | Purpose |
|------|---------|
| `api/main.py` | FastAPI sidecar for n8n → Python communication |
| `notify.py` | ntfy.sh notification client |
| `docker-compose.yml` | Updated for n8n + PostgreSQL + Python app |

---

## Database Migration

### Tables to Keep
- `research_signals` — core signal storage
- `research_documents` — document metadata
- `watchlist` — stock watchlist
- `company` — company metadata
- `audit_log` — append-only audit trail

### Tables to Remove
- `trade_proposals` — replaced by conversational decisions
- `orders` — replaced by Alpaca MCP
- `positions` — replaced by Alpaca MCP queries
- `price_bar` — replaced by Alpaca MCP market data
- `technical_indicator` — replaced by MaverickMCP/QuantConnect
- `market_data_fetch` — no longer needed

### Tables to Add
- `macro_indicators` — FRED data cache
- `social_sentiment` — Reddit + StockTwits signals
- `filing_summaries` — pre-computed multi-level summaries
- `vec_filings` — sqlite-vec virtual table for embeddings
- `rss_seen` — dedup for RSS feed items
- `notification_log` — track sent notifications (cooldown enforcement)

---

## Dependencies

### Add
| Package | Purpose |
|---------|---------|
| `fredapi` | FRED macro data |
| `tiingo` | Tiingo news API |
| `praw` | Reddit API |
| `mcp[cli]` | MCP server SDK (FastMCP) |
| `sqlite-vec` | Vector search extension |
| `fastapi` + `uvicorn` | API sidecar for n8n |

### Remove
None immediately — the removed code doesn't add unique dependencies beyond what the kept code already uses.

### Keep
All existing: `edgartools`, `finnhub-python`, `earningscall`, `anthropic`, `feedparser`, `beautifulsoup4`, `pydantic`, `alpaca-py`, `httpx`, `python-dotenv`.

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Removing execution layer loses order management | Alpaca MCP provides complete order management. Paper trade first. |
| Conversational analysis is inconsistent | Bull/bear debate forces structured analysis. Prompt caching ensures consistency. |
| n8n adds operational complexity | Docker Compose deployment. n8n has visual debugging. Start simple, add workflows incrementally. |
| Too many data sources = noise | Phase rollout. Start with SEC + Finnhub + FRED. Add social/news only after research pipeline is solid. |
| MCP context budget (13K tokens for Alpaca alone) | Use Tool Search auto-filtering. Be selective about which MCP servers are active. |
| Loss of CLI for scripting | Keep minimal CLI for ingest/serve/migrate/status. n8n handles scheduling. |
