# 006 Architecture Research — Findings

## Area 1: MCP Server Ecosystem

### 1.1 Alpaca MCP Server (Our Broker)

**Repo**: [alpacahq/alpaca-mcp-server](https://github.com/alpacahq/alpaca-mcp-server) | 509 stars | Python | Official

**43 tools** covering: account/positions (3), assets (2), corporate actions (1), portfolio history (1), watchlists (7), market calendar/clock (2), stock data (7), crypto data (8), options data (3), trading/orders (4), position management (5).

**Setup**: `uvx alpaca-mcp-server init` + configure in Claude Desktop/Code config. Paper trading default. Works with Claude Code via `claude mcp add`.

**Key Concerns**:
- **13K+ token context footprint** (Issue #45) — tool definitions alone consume ~16% of context window. Combined with system overhead, sessions can start at 51% usage.
- **Live trading auth broken for some users** (Issue #16) — `"request is not authorized"` even with valid live keys. Unresolved for months.
- **LLM hallucination** (Issue #14) — Claude hallucinates successful orders, uses wrong dates, claims it can't access real data. Tool descriptions don't guard against this well.
- **Docker build flaky** (Issue #43) — yanked PyPI packages break builds.
- **No streaming** — request/response only, no WebSocket subscriptions.
- **No news API** — despite Alpaca having news endpoints.
- **No bracket/conditional orders** through MCP.
- **No built-in audit/logging** of LLM decisions.

**Verdict**: Best for **interactive human-in-the-loop** use (chatting with Claude Desktop: "buy 5 shares of AAPL"). For **programmatic agent execution**, `alpaca-py` SDK is more reliable. We should support both paths.

---

### 1.2 Finance MCP Servers — Top Picks

#### Tier 1: High Value

| Server | Stars | Tools | Cost | Why It Matters |
|--------|-------|-------|------|----------------|
| [Polygon.io MCP](https://github.com/polygon-io/mcp_polygon) | 252 | 35+ | $29/mo starter | Best real-time market data MCP. Official. Last commit Feb 2026. |
| [Alpha Vantage MCP](https://mcp.alphavantage.co/) | — | 100+ | Free tier (25 req/day) | Earnings transcripts, news sentiment, 50+ technical indicators, 20yr history |
| [MaverickMCP](https://github.com/wshobson/maverick-mcp) | 353 | 15+ | Free (Tiingo) | Professional backtesting (VectorBT), 520 pre-seeded stocks, 20+ indicators |
| [sec-edgar-mcp](https://github.com/stefanoamorelli/sec-edgar-mcp) | 203 | ~10 | Free | Built on **same edgartools library** we use. Could replace our custom SEC code. |
| [Financial Datasets MCP](https://github.com/financial-datasets/mcp-server) | 756 | ~10 | API key needed | Income statements, balance sheets, cash flow, stock prices |
| [Financial Modeling Prep MCP](https://github.com/imbenrabi/Financial-Modeling-Prep-MCP-Server) | 113 | 253 | API key needed | Unique: **congressional trading disclosures**, ESG, insider data |

#### Tier 2: Useful

| Server | Stars | What It Does |
|--------|-------|-------------|
| [Composer Trade MCP](https://github.com/invest-composer/composer-trade-mcp) | 219 | 33 tools, 1000+ pre-built strategies, backtesting. Paid subscription. |
| [Yahoo Finance MCP](https://github.com/Alex2Yang97/yahoo-finance-mcp) | 212 | Free (yfinance), but reliability issues. Good as fallback. |
| [OctagonAI MCP](https://github.com/OctagonAI/octagon-mcp-server) | 97 | 8K+ public companies, 3M+ private. Paid API. |
| [Finnhub MCP](https://github.com/cfdude/mcp-finnhub) | 2 | Wraps Finnhub. We already use Finnhub directly. |
| [Finance News RSS MCP](https://lobehub.com/mcp/jvenkatasandeep-finance-news-mcp) | — | Bloomberg, WSJ, CNBC, Seeking Alpha, MarketWatch, FT feeds |

---

### 1.3 Web Research / Scraping MCP Servers

| Server | Stars | What It Does |
|--------|-------|-------------|
| [Firecrawl MCP](https://github.com/firecrawl/firecrawl-mcp-server) | 5,500+ | Best-in-class. 7 tools: scrape, batch, map, crawl, search, **Agent** (autonomous multi-source), browser. Self-hostable. |
| [Tavily MCP](https://github.com/tavily-ai/tavily-mcp) | — | Production-ready search optimized for LLMs. Remote endpoint available. |
| [Deep Research MCP](https://github.com/pinkpixel-dev/deep-research-mcp) | — | Uses Tavily for comprehensive topic research, structures output for LLMs. |
| [Playwright MCP](https://github.com/microsoft/playwright-mcp) (Microsoft) | — | Browser automation for JS-rendered sites. |

---

### 1.4 Database MCP Servers (SQLite)

| Server | What It Does | Relevance |
|--------|-------------|-----------|
| [mcp-sqlite](https://github.com/jparkerweb/mcp-sqlite) (86 stars) | Full CRUD + arbitrary SQL on SQLite | HIGH — let Claude directly query research DB |
| [sqlite-explorer-fastmcp](https://github.com/hannesrudolph/sqlite-explorer-fastmcp-mcp-server) | Read-only + query validation | Safer for analysis sessions |
| Official Anthropic SQLite (archived) | Reference implementation via npx | Good to study, but community versions are better |

---

### 1.5 Building Custom MCP Servers (Python)

**SDK**: `mcp` package on PyPI (v1.26.0 stable, v2.0 pre-alpha). Install: `uv add "mcp[cli]"`.

**FastMCP** is the high-level decorator API — type hints + docstrings auto-generate tool schemas. ~60 lines for a complete research DB server:

```python
from mcp.server.fastmcp import FastMCP, Context
mcp = FastMCP("finance-research", lifespan=db_lifespan)

@mcp.tool()
def query_signals(ticker: str, limit: int = 10, ctx: Context = None) -> str:
    """Query research signals for a specific ticker."""
    db = ctx.request_context.lifespan_context["db"]
    rows = db.execute("SELECT * FROM research_signals WHERE ticker = ? LIMIT ?", (ticker, limit)).fetchall()
    return json.dumps([dict(r) for r in rows])
```

**Claude Code integration**:
```bash
claude mcp add --transport stdio research-db -- uv run src/mcp/research_server.py
```

**Multi-server config** via `.mcp.json` (committed to repo) with `${VAR}` env expansion. Tool Search auto-activates when combined tool defs exceed 10% of context.

**Key gotchas**: Never `print()` in stdio servers (corrupts JSON-RPC). 60-second request timeout (send progress updates). Output limit 25K tokens (paginate large queries). Startup timeout configurable via `MCP_TIMEOUT`.

---

### 1.6 MCP Registries

- **Official**: [registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io/) (canonical, launched Sep 2025)
- **Curated lists**: [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers), [wong2/awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers)
- **Directories**: [mcp.so](https://mcp.so) (3K+ servers), [Smithery](https://smithery.ai) (2.2K+), [mcpservers.org](https://mcpservers.org)

---

### 1.7 Area 1 Key Takeaways

1. **Don't build what exists**: sec-edgar-mcp uses the same library (edgartools) we do. Polygon.io and Alpha Vantage cover market data comprehensively. We should use these instead of custom wrappers.

2. **Custom MCP for our research DB is trivial** (~60 lines) and unlocks conversational analysis — Claude can directly query signals, filings, watchlists.

3. **Context budget is real**: Alpaca MCP alone = 13K tokens. Each additional MCP server adds more. Need to be selective, or rely on Tool Search auto-filtering.

4. **Two-path execution**: MCP for interactive use (human-in-the-loop), alpaca-py for programmatic agent execution. Both should be supported.

5. **Firecrawl + Tavily** are the best options for autonomous web research — directly applicable to our "always watching" agent goal.

6. **Congressional trading data** (via Financial Modeling Prep MCP) is a unique alpha source worth exploring.

---

## Area 2: Workflow Automation

### 2.1 n8n (Recommended)

**Repo**: [n8n-io/n8n](https://github.com/n8n-io/n8n) | 157K+ stars | Fair-code (Sustainable Use License)

**What**: Visual workflow automation platform with inline code execution, 400+ integrations, and native AI agent support via LangChain nodes.

**Intel NUC deployment**: ~500 MB RAM total (n8n + PostgreSQL). Minimum 2 GB RAM / 2 cores; recommended 4 GB / 2-4 cores. Docker Compose deployment. Runs comfortably alongside NATS and GitHub Actions runner.

**Claude/AI integration**:
- Native [Anthropic Chat Model node](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.lmchatanthropic/) — first-class Claude support
- AI Agent node (LangChain-based) — Claude can autonomously select and chain tool calls
- [MCP Client Tool](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp/) — connects AI agents directly to MCP servers (e.g., Alpaca MCP)
- MCP Server Trigger — exposes n8n workflows as MCP tools for Claude Desktop

**Trigger types**:
| Type | Node | Use Case |
|------|------|----------|
| RSS Feed | RSS Feed Trigger | SEC EDGAR filings (10-min updates), CNBC, Bloomberg, Fed |
| Schedule | Schedule Trigger | Full cron flexibility, market-hours-only jobs |
| Webhook | Webhook node | Alpaca order fills, custom Python script notifications |

**Financial templates available**:
- [Automated Stock Trading with AI + Alpaca](https://n8n.io/workflows/5711-automated-stock-trading-with-ai-integrating-alpaca-and-google-sheets/)
- [AI Stock Trades with Technical Analysis + Alpaca](https://n8n.io/workflows/7240-automate-stock-trades-with-ai-driven-technical-analysis-and-alpaca-trading/)
- [Stock Analysis with Claude + GPT + Gemini via Telegram](https://n8n.io/workflows/10460-stock-market-analysis-and-prediction-with-gpt-claude-and-gemini-via-telegram/)

**Calling Python code**: Execute Command node runs `python your_script.py`, or HTTP Request node calls a FastAPI sidecar. Our existing research pipeline modules can be invoked directly.

**Recommended NUC architecture**:
```
Intel NUC (Docker Compose)
├── n8n (orchestration, triggers, AI agents, notifications)
├── PostgreSQL (n8n backend)
├── Python app (FastAPI sidecar for research pipeline)
│   ├── src/finance_agent/research/pipeline.py
│   ├── src/finance_agent/data/sources/
│   └── SQLite DB (research_data/)
└── NATS (existing)
```

---

### 2.2 Alternatives Evaluated

| Platform | Stars | Verdict |
|----------|-------|---------|
| **Windmill** ([windmill-labs/windmill](https://github.com/windmill-labs/windmill)) | 15K | Python-native, lower RAM (~287 MB), but weaker AI agent ecosystem and much smaller community. Consider if Python-first matters more than AI integration. |
| **Activepieces** ([activepieces/activepieces](https://github.com/activepieces/activepieces)) | 20K | MIT license, ~400 MCP servers support. Less mature AI agent architecture, fewer financial templates. |
| **Temporal** ([temporalio/temporal](https://github.com/temporalio/temporal)) | 13K | Enterprise-grade overkill. Heavy resource footprint (Cassandra/MySQL + Elasticsearch). Not for solo developers. |
| **Prefect / Dagster** | 20K / 13K | Data engineering orchestrators, not workflow automation. Would need a separate scheduler/notifier. |
| **LangGraph / CrewAI** | 15K / 33K | AI agent frameworks, not workflow platforms. No built-in triggers, scheduling, or notifications. Better used as libraries inside your Python app that n8n calls. |

---

### 2.3 Event-Driven Patterns

**SEC EDGAR RSS**: `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={CIK}&type=&dateb=&owner=include&count=40&output=atom` — updates every 10 minutes (M-F, 6am-10pm EST).

**Example schedule**:
- Every 15 min (market hours): Check SEC EDGAR RSS, Finnhub news
- Daily 7am EST: Run full research synthesis for watchlist
- Weekly Sunday: Generate weekly summary report

n8n handles this naturally — each workflow has its own trigger, all run simultaneously. Workflows can trigger other workflows via the "Execute Workflow" node.

---

### 2.4 Area 2 Key Takeaways

1. **n8n is the clear winner** for our use case: native Claude integration, MCP support, financial trading templates, and comfortable NUC resource footprint.
2. **n8n + FastAPI sidecar** is the recommended pattern: n8n handles scheduling/triggers/notifications, Python app handles heavy data processing and SQLite.
3. **Don't use LangGraph/CrewAI as replacements for n8n** — they lack scheduling, triggers, and notification infrastructure. Use them as libraries inside your Python app if needed.
4. **SEC EDGAR RSS feeds** provide near-real-time filing alerts for free.

---

## Area 3: Autonomous Research Agents

### 3.1 Web Crawling Agents

| Tool | Stars | What It Does | NUC Feasibility | Rating |
|------|-------|-------------|-----------------|--------|
| [Crawl4AI](https://github.com/unclecode/crawl4ai) | 51K | Python-native LLM web crawler. "Scrapy for LLMs." Self-hosted, JS rendering, LLM-ready markdown output. | Excellent | **Recommended** |
| [browser-use](https://github.com/browser-use/browser-use) | 60K | AI-controlled Chrome via Playwright + LLM. Multi-tab workflows. | Good (memory-intensive) | Complex |
| [Playwright MCP](https://github.com/microsoft/playwright-mcp) | — | Microsoft MCP server, accessibility-tree-based browser control. 10x more stable than selector-based approaches. | Excellent | Easy-Moderate |
| [ScrapeGraphAI](https://github.com/ScrapeGraphAI/Scrapegraph-ai) | 21K | Natural language scraping pipelines. Describe what you want, it extracts. | Good | Easy |
| Claude Computer Use | — | Anthropic beta. Screenshot + mouse/keyboard. 61.4% on OSWorld benchmark. | Works but slow | Too expensive for monitoring |

**Recommendation**: **Crawl4AI** for batch document ingestion, **Playwright MCP** for interactive browsing, reserve browser-use/Computer Use for edge cases.

---

### 3.2 Financial News Monitoring

**RSS Feeds (Free, Primary)**:
| Source | Feed | Update Frequency |
|--------|------|-----------------|
| SEC EDGAR | Per-company Atom feed | Every 10 min |
| CNBC | [cnbc.com/rss-feeds](https://www.cnbc.com/rss-feeds/) | Minutes |
| Federal Reserve | [federalreserve.gov/feeds](https://www.federalreserve.gov/feeds/feeds.htm) | On publication |
| Substack (any) | `https://<name>.substack.com/feed` | On publication |
| Seeking Alpha | `seekingalpha.com/feed.xml` | Minutes |

**News APIs**:
| API | Free Tier | Quality | Best For |
|-----|-----------|---------|----------|
| Finnhub (already integrated) | 60 req/min | Good breadth | Company + market news |
| [GDELT](https://www.gdeltproject.org/) | 100% free, unlimited | Massive global coverage | Macro/geopolitical monitoring |
| [OpenBB](https://github.com/OpenBB-finance/OpenBB) | Free (50K+ stars) | 350+ datasets | Closest thing to a free Bloomberg |

**Breaking news detection**: Track article velocity per ticker (3x baseline in 30 min = breaking), weight by source authority, classify urgency with Claude Haiku (~$0.001/headline).

---

### 3.3 Social Media Monitoring

| Platform | Tool | Cost | Quality | Priority |
|----------|------|------|---------|----------|
| **Reddit** | [PRAW](https://praw.readthedocs.io/) + [ApeWisdom API](https://apewisdom.io/api/) | Free | Good (r/wallstreetbets, r/stocks) | HIGH |
| **StockTwits** | [StockTwits API](https://api-docs.stocktwits.com/) | Free | Pre-labeled bull/bear sentiment, [Alpaca integration](https://alpaca.markets/blog/provide-real-time-social-sentiment-to-customers-with-alpacas-stocktwits-integration/) | HIGH |
| **Twitter/X** | Official API: $200/mo minimum for reads. Use [TwitterAPI.io](https://twitterapi.io/) ($0.15/1K tweets) instead | ~$15/mo | Fragmented ecosystem | LOW |
| **Discord/Telegram** | discord.py / python-telegram-bot | Free | Poor signal-to-noise for equities | SKIP |

**Aggregators**: Finnhub social sentiment endpoint (already in stack), [LunarCrush](https://lunarcrush.com/) (crypto-focused), [Prospero.ai](https://www.prospero.ai/) (paid).

---

### 3.4 Agent Frameworks

| Framework | Stars | What It Does | Recommendation |
|-----------|-------|-------------|----------------|
| **[Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)** | — | Anthropic's official SDK. Terminal, filesystem, web access. Same agent loop as Claude Code. Python v0.1.34. | **PRIMARY — use this** |
| [GPT Researcher](https://github.com/assafelovic/gpt-researcher) | 18K | Autonomous research agent. Planner/executor pattern. 5-6 page reports with citations. Claude-compatible. | Good for deep research briefs |
| [CrewAI](https://github.com/crewAIInc/crewAI) | 44K | Role-based multi-agent framework. Used by PwC, IBM, NVIDIA. | Overkill for solo developer |
| [LangGraph](https://github.com/langchain-ai/langgraph) | 15K | Stateful multi-agent graphs. LangChain ecosystem. | Use only if Claude Agent SDK isn't enough |
| AutoGPT | 170K | Pioneered autonomous agents. **Superseded** by the above. | SKIP |

---

### 3.5 Academic / Research Monitoring

All free, all RSS-based:
- **arXiv q-fin**: [arxiv.org/list/q-fin/new](https://arxiv.org/list/q-fin/new) — daily new submissions
- **NBER**: [nber.org/papers](https://www.nber.org/papers) — weekly working papers
- **Federal Reserve**: All regional Feds have RSS (speeches, FOMC, research)
- **Semantic Scholar API**: [api.semanticscholar.org](https://api.semanticscholar.org/) — 225M+ papers, free

---

### 3.6 Area 3 Key Takeaways

1. **Claude Agent SDK is the primary agent framework** — native Claude integration, lightweight, same patterns as Claude Code.
2. **Crawl4AI for web crawling** — self-hosted, free, designed for LLM pipelines.
3. **RSS + feedparser is the backbone** — free, reliable, covers SEC/news/academia. Already a project dependency.
4. **Reddit (PRAW) + StockTwits** are the highest-value social sources at zero cost.
5. **Skip Twitter/X official API** ($200/mo minimum) — use TwitterAPI.io if needed later.
6. **Estimated monthly cost**: $10-75/mo across tiers, mostly Claude API tokens.

---

## Area 4: Existing AI Trading/Research Frameworks

### 4.1 Multi-Agent Trading Frameworks

#### TradingAgents (Tauric Research)
- **Repo**: [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | 30.1K stars | Apache-2.0
- **Latest**: v0.2.0 (Feb 2026) with multi-provider LLM support including Claude
- **Architecture**: 7 specialized agents mirroring a real trading firm:
  1. Fundamentals Analyst → 2. Sentiment Analyst → 3. News Analyst → 4. Technical Analyst → 5. Bull/Bear Researchers (debate mechanism) → 6. Trader → 7. Risk Manager + Portfolio Manager
- **Key innovation**: Adversarial bull/bear debate with configurable rounds
- **Status**: Explicitly **research-only**. Built on LangGraph. Python 3.13.
- **Verdict**: **Borrow the debate pattern; do not adopt the framework.** The multi-perspective analysis forcing both bull and bear cases is the most valuable idea here.

#### FinRobot (AI4Finance Foundation)
- **Repo**: [AI4Finance-Foundation/FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | 6.2K stars | Apache-2.0
- Built on Microsoft AutoGen. Financial Chain-of-Thought prompting.
- **Verdict**: Useful for studying structured financial analysis prompts. AutoGen dependency is a negative.

#### Dexter (virattt)
- **Repo**: [virattt/dexter](https://github.com/virattt/dexter) | 15.5K stars | Active (last commit Feb 16, 2026)
- Autonomous deep financial research agent with self-reflection, validation loops, loop detection.
- Claude-compatible. **Written in TypeScript** (99.1% of codebase).
- **Verdict**: Closest to what we're building. **Study the research decomposition and self-validation patterns**, but don't adopt (TypeScript).

#### Others Evaluated
| Framework | Stars | Verdict |
|-----------|-------|---------|
| FinGPT | 18.6K | Sentiment models (F1 87.62%) are good. Stock prediction (~50%) is coin-flip. **Not needed now.** |
| AgenticTrading (Open-Finance-Lab) | 70 | Academic (NeurIPS 2025). Neo4j dependency. **Skip.** |
| BloombergGPT | — | Proprietary, not available. Frontier models have largely caught up. |

---

### 4.2 Quantitative Backtesting

| Framework | Stars | Cost | Claude Integration | Verdict |
|-----------|-------|------|-------------------|---------|
| **[QuantConnect](https://www.quantconnect.com/)** (LEAN) | — | Free tier (unlimited backtests, 200 projects) | **Official MCP server** | **Best option** — free, institutional data, Claude integration |
| **[VectorBT](https://github.com/polakowo/vectorbt)** | 6.2K | Free (Pro: $25/mo) | Via [MaverickMCP](https://github.com/wshobson/maverick-mcp) (353 stars) | Excellent for rapid strategy evaluation. MaverickMCP uses same stack (Python 3.12+, SQLite). |
| Zipline-Reloaded | 3K | Free | None | Solid but no LLM integration. Skip. |
| Backtrader | 16.5K | Free | Community wrappers | **Abandonware.** No new releases in 12+ months. Skip. |
| NautilusTrader | 15K | Free | None | Institutional-grade. Overkill for weekly trading. |
| [StrateQueue](https://github.com/StrateQueue/StrateQueue) | 166 | Free | None | Deploys strategies from backtesting frameworks to live brokers (including Alpaca). **Bookmark for later.** |

---

### 4.3 What Retail AI Traders Actually Use

**Community consensus** (r/algotrading, HN):
- Claude/GPT as **research assistants** (not execution) — most successful approach
- TradingView for charting (dominant platform)
- QuantConnect free tier for backtesting
- Python + Alpaca API for execution
- Human makes the final call
- 2025 Stanford study: 58% of retail algo-trading models collapse within 3 months (curve-fitting)
- Hybrid human+AI generates 3-5% higher ROI than either alone

**Commercial tools assessment** (at $500-1000 account size):
| Service | Cost | Worth It? |
|---------|------|-----------|
| Trade Ideas | $89-254/mo | **No** — costs more than your monthly capital |
| Tickeron | $60-250/mo | **No** — terrible cost-to-capital ratio |
| Composer | $5-40/mo | Maybe at $5/mo promo |
| Kavout | $20+/mo | Replicable with Claude |
| QuantConnect | Free | **Yes** |
| VectorBT (open-source) | Free | **Yes** |

**Bottom line**: No commercial tool is worth it at this account size. Spend on Claude API credits instead.

---

### 4.4 Patterns to Borrow

| Pattern | Source | How to Apply |
|---------|--------|-------------|
| **Bull/Bear debate** | TradingAgents | Have Claude analyze from both perspectives before producing signals |
| **Research decomposition** | Dexter | Break complex financial questions into structured steps with self-validation |
| **Token optimization** | LangChain Stock Research Agent V3 | 73% cost reduction via caching and specialized sub-agents |
| **MCP bridge to backtesting** | QuantConnect MCP | Research → backtest validation through MCP |
| **Walk-forward optimization** | MaverickMCP | Strategy validation before live deployment |

---

### 4.5 Area 4 Key Takeaways

1. **Don't adopt any framework wholesale.** Our lightweight Python + Claude + Alpaca + SQLite stack is the right architecture for a solo developer.
2. **Borrow the TradingAgents debate pattern** — force bull/bear perspectives in research analysis.
3. **QuantConnect free tier + MCP server** is the most practical backtesting option.
4. **MaverickMCP** is worth installing as a complementary tool (same Python 3.12+ / SQLite stack).
5. **No commercial tool is worth it** at $500-1000 account size.

---

## Area 5: Data Sources Beyond Current

### 5.1 Earnings Call Transcripts

| Source | Cost | Quality | Verdict |
|--------|------|---------|---------|
| **Finnhub** (current) | Free (60 req/min) | Good for most companies. Transcripts available 2-4 hours post-call. Speaker attribution inconsistent. | **Keep as starting point** |
| [EarningsCall.biz](https://earningscall.biz/) | Pricing gated (contact sales) | 5,000+ companies. Free tier: Apple/Microsoft only. Python library [`earningscall`](https://pypi.org/project/earningscall/). | Try once pricing is known |
| Financial Modeling Prep | $149/mo (Ultimate plan) | 8,000+ companies, 10+ years. Bundled with 13F, social sentiment, fundamentals. | Only if consolidating data sources |
| Quartr | Enterprise pricing (contact sales) | 14,000+ companies. **Best speaker attribution** (typeId=22). Also provides slide decks. | Likely too expensive |
| Alpha Vantage | 25 req/day free | 15+ years, pre-computed LLM sentiment. Community reports quality issues. | Free tier too limited |

**Recommendation**: Stick with Finnhub free tier. Upgrade to FMP Ultimate ($149/mo) only if also using its other bundled data.

---

### 5.2 Real-Time News

| Source | Cost | Best For | Verdict |
|--------|------|----------|---------|
| **Finnhub** (current) | Free | Company + market news | Keep |
| **[Tiingo](https://www.tiingo.com/)** | Free (1K calls/day) | Ticker-tagged news from top sources | **Add — best bang-for-buck second source** |
| [GDELT](https://www.gdeltproject.org/) | Free (unlimited) | Macro/geopolitical sentiment | Add for macro context |
| [Polygon.io/Massive](https://massive.com/) | $29/mo | Market data + news bundle | Only if Alpaca data insufficient |
| Benzinga | Contact sales | Sub-minute breaking news | Too expensive for weekly trading |
| NewsAPI.ai | $90+/mo | 150K+ sources | Too broad, not finance-specific |

**Recommendation**: **Finnhub + Tiingo free tiers** = two complementary news sources at zero cost.

---

### 5.3 Insider Trading Data

| Source | Cost | Verdict |
|--------|------|---------|
| **SEC Form 4 via edgartools** (already installed) | Free | **Best option.** `company.get_filings(form="4")[0].obj()` returns structured `Form4` object with transactions. |
| Finnhub insider transactions | Free | Good for quick lookups. Already in stack. |
| [Quiver Quantitative](https://www.quiverquant.com/) | $25/mo | **Congressional trading data** — genuinely differentiated. Also covers government contracts, lobbying. Python API: `quiver-python`. |
| OpenInsider | Free website, no API | Use for manual research only. |

**Recommendation**: Use edgartools (free, already installed) for Form 4 parsing. Add Quiver Quantitative ($25/mo) when ready for congressional trading signals.

---

### 5.4 Macro / Economic Data

**FRED (Federal Reserve Economic Data)** — **Must-add. Free.**

Install `fredapi`, get a free API key. Key series for stock traders:
- `UNRATE` (unemployment), `DGS10` / `DGS2` (yield curve), `T10Y2Y` (10Y-2Y spread)
- `CPIAUCSL` (CPI/inflation), `FEDFUNDS` (Fed funds rate), `VIXCLS` (VIX)
- `ICSA` (initial jobless claims — weekly leading indicator), `M2SL` (money supply)

BLS, Treasury.gov, and ISM data are all available through FRED — use FRED as the single interface.

---

### 5.5 13F / Institutional Holdings

**Use edgartools (already installed)**:
1. Look up CIK for each investor's fund
2. Pull 13F-HR filings quarterly
3. Diff holdings quarter-over-quarter
4. Store in SQLite for LLM research context

Free alternatives for manual spot-checks: [WhaleWisdom](https://whalewisdom.com/) (free tier: 2 years of data), [Dataroma](https://dataroma.com/) (82 "superinvestors").

---

### 5.6 Options Flow

**Skip for now.** Options flow signals decay too rapidly for weekly trading. If added later, [Unusual Whales](https://unusualwhales.com/) ($50/mo) is the clear retail choice — includes congressional trading data.

---

### 5.7 Alternative Data

| Category | Affordable? | Verdict |
|----------|------------|---------|
| Social sentiment | Yes ($25/mo via Quiver) | **Worth it** for congressional trading + Reddit sentiment |
| Satellite imagery | No ($25K-100K+/yr) | Institutional only. **Skip.** |
| App usage (SimilarWeb) | No ($199/mo) | Use free web checker manually. **Skip API.** |
| Credit card spending | No ($50K+/yr) | Completely inaccessible to retail. **Skip.** |
| Web traffic data | No ($130+/mo) | Use free tools manually. **Skip API.** |

---

### 5.8 Podcast / Video Content

- Free transcripts available for All-In, Acquired via [podscripts.co](https://podscripts.co/), HappyScribe, Substack
- YouTube transcripts via [`youtube-transcript-api`](https://pypi.org/project/youtube-transcript-api/) (free, no API key)
- Local transcription via [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) on NUC (4x faster than stock Whisper)
- **Recommendation**: Use free transcript sites manually for now. Build ingestion pipeline only if repeatedly needed.

---

### 5.9 Prioritized Data Source Roadmap

**Phase 1 — Immediate (Free)**:
- FRED API (`fredapi`) — macro economic context
- Tiingo News (free tier) — second news source
- 13F tracking via edgartools — quarterly notable investor scraper
- Form 4 parsing via edgartools — insider trading data

**Phase 2 — When Budget Allows ($25/mo)**:
- Quiver Quantitative — congressional trading + social sentiment

**Phase 3 — If Consolidating ($149/mo)**:
- FMP Ultimate — transcripts + 13F + social + fundamentals in one API

---

## Area 6: Architecture Patterns

### 6.1 AI Trading System Architectures

**Common patterns observed**:

1. **Pipeline Architecture** (what we have): Data flows linearly through ingestion → analysis → decision → execution. Simple, debuggable, appropriate for single-user systems.

2. **Multi-Agent Debate**: Multiple LLM agents with different perspectives argue about trades. Token-expensive but reduces bias. (TradingAgents pattern.)

3. **Event-Driven / Pub-Sub**: Market events trigger analysis pipelines. Good for real-time systems. Our NATS server could enable this later.

4. **Ensemble Scoring**: Multiple analysis methods each produce a score; a decision engine combines them. This is what quant firms do. Our `research/signals.py` aligns with this.

**Our existing layered architecture (from constitution) is solid** and maps well to industry patterns. The key insight to borrow from TradingAgents is the **adversarial perspective** — explicitly considering bull and bear cases before any trade proposal.

---

### 6.2 Storage: Keep SQLite

**SQLite (WAL mode)** is the right choice for our scale (~50 stocks, single user, daily ingestion). Its limits are theoretical at our usage level.

**DuckDB** — add later as an **analytical layer only**. DuckDB can query SQLite files directly with zero ETL:
```python
import duckdb
duckdb.sql("SELECT * FROM sqlite_scan('finance.db', 'trades') WHERE date > '2026-01-01'")
```

**PostgreSQL** — skip. Operational burden not justified for single-user home server.

**Vector search**: Start with **[sqlite-vec](https://github.com/asg017/sqlite-vec)** — a vector search extension for SQLite. Zero operational overhead, stays in one database:
```sql
CREATE VIRTUAL TABLE vec_filings USING vec0(embedding float[768]);
SELECT rowid, distance FROM vec_filings WHERE embedding MATCH ? ORDER BY distance LIMIT 10;
```

Graduate to [LanceDB](https://lancedb.com/) only if sqlite-vec proves insufficient. Skip server-based vector databases (ChromaDB, Pinecone, Qdrant) entirely.

---

### 6.3 Feeding Research Context into Claude Efficiently

**Layer 1: Pre-Summarization (Most Token-Efficient)**
```
Raw 10-K (80,000 tokens)
  → Section summaries (2,000 tokens each for MD&A, Risk Factors, etc.)
  → Company brief (500 tokens)
  → Key metrics JSON (200 tokens)
```
Store at multiple granularities. Match summary level to question complexity.

**Layer 2: RAG for Specific Questions**
- Chunk by section headers, then paragraphs (~1,500 chars each), 100-300 token overlap
- Hybrid retrieval: vector similarity (semantic) + BM25/FTS5 (keyword) at 0.6 weight
- Cross-encoder reranking using Claude itself
- Finance-tuned embeddings deliver ~18% better recall than generic

**Layer 3: [Anthropic Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)**
- Cached tokens cost **0.1x** normal price (90% savings)
- 5-minute TTL, refreshed on each use
- Structure prompts: static research context first (cached) + user question last (varies)
```python
messages = [{
    "role": "user",
    "content": [
        {"type": "text", "text": research_context,  # 10K tokens, cached
         "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": user_question}  # changes each turn
    ]
}]
```

**Layer 4: MCP Resources for Static Reference Data**
- Watchlist, portfolio positions, recent signals → MCP resources (not tools)
- Loaded by client, injected into context without tool-call overhead

**What NOT to do**: Don't fit entire 10-K filings into context (80K tokens each). Don't skip pre-summarization and go straight to RAG.

---

### 6.4 Custom MCP Server as Persistence Layer

**Use domain-specific tools, not raw SQL**:
```python
# Good: constrained, tested, token-efficient
@server.tool()
async def get_research_summary(symbol: str, days: int = 7) -> ResearchSummary:
    """Get research summary for a symbol over the last N days."""

# Bad: security risk, forces Claude to write SQL
@server.tool()
async def query_db(sql: str) -> list[dict]:
    """Run arbitrary SQL against the database."""
```

**Advantages**: Security (no accidental DELETE), token efficiency (no schema knowledge needed), reliability (pre-written queries are tested).

**Handle large results**: Pagination with `limit`/`offset`, pre-summarization in MCP server, tiered detail levels (`summary` / `standard` / `full`).

**MCP Resources vs Tools**:
| Use Case | Primitive | Reason |
|----------|----------|--------|
| Watchlist | Resource | Static reference data |
| Portfolio positions | Resource | Updated infrequently |
| Research query | Tool | Dynamic, parameterized |
| Place trade | Tool | Action with side effects |

---

### 6.5 The "Daily Briefing" Pattern

**Architecture**:
```
[Scheduled Crawlers] → [Raw Data Store] → [Prioritization] → [Summarization] → [Delivery]
   (cron/systemd)       (SQLite + files)    (scoring engine)     (Claude API)      (ntfy/Telegram)
```

**Prioritization scoring** (deterministic, not LLM):
- Filing type: 8-K > 10-Q/10-K > other
- Price movement: > 3% intraday for watchlist stock = high priority
- Earnings surprise: actual vs. estimate deviation
- News sentiment: significant negative on held position

**Notification**: [ntfy.sh](https://ntfy.sh/) — self-hostable on NUC, native mobile apps, single-curl API:
```bash
curl -d "AAPL 8-K filed: CEO transition" ntfy.sh/finance-agent-alerts
```

**Alert fatigue prevention**:
- Priority tiers: Critical (immediate push) → High (push within 15 min) → Normal (batched in evening) → Low (logged only)
- Cooldown: max 1 notification per symbol per hour (unless critical)
- Compound triggers: don't alert on 3% drop alone, alert when 3% drop AND negative news AND held position
- Daily cap: 5-10 push notifications max
- Weekend suppression except critical alerts

---

### 6.6 Evolution Path: Decision Support → Autonomous

**Stage 1: Decision Support (Months 1-6)** — Human decides everything
- Paper trading then real money ($500-1000)
- System provides research and analysis
- Human reviews, asks follow-ups, decides, executes via MCP

**Stage 2: Semi-Autonomous (Months 6-12)** — Agents suggest, human approves
- Trade proposals via notification with confidence, rationale, citations
- Human approval required (e.g., reply YES to Telegram bot)
- Time-limited approvals (expire after 30 min)
- Paper trading validation: run Stage 2 in paper for 30+ days before live

**Stage 3: Autonomous within Guardrails (Month 12+)** — Only after proven track record
- Hard limits: max 10% per position, 5% daily loss, 20 trades/day, limit orders only
- Strategy allowlist (validated 60+ days in paper)
- Symbol allowlist (large-cap, liquid only)
- Guardian agent monitors for anomalies
- Drawdown circuit breaker

**Key design principle**: Build Stage 1 so adding Stage 2 requires only new code, not rewriting existing code.

**Safety testing**: [Inspect AI](https://inspect.aisi.org.uk/) (UK AISI) — evaluation framework for AI agents including insider trading tests and adversarial scenarios.

---

### 6.7 Code Organization for AI-Assisted Development

**Smaller files are better** for Claude Code context:
- Target: 200-400 lines per file (~5-10KB)
- One concern per file
- Self-documenting names (`research/analyzer.py` not `research/utils.py`)

**What works for LLM developers**:
- Type hints everywhere (documentation Claude reads and respects)
- Pydantic models for data structures (validation + documentation)
- Subdirectory-level CLAUDE.md files for module-specific instructions
- Avoid deep inheritance — prefer composition
- Explicit over implicit (named constants, explicit imports)
- Linters as architecture guards — ruff catches violations, Claude self-corrects

---

### 6.8 Area 6 Key Takeaways

1. **Keep SQLite** — add sqlite-vec for vector search, DuckDB later for analytics only.
2. **Pre-summarization + prompt caching** is the most token-efficient strategy for research context.
3. **Custom MCP with domain-specific tools** (not raw SQL) for the research DB.
4. **ntfy.sh** for notifications — self-hosted on NUC, simplest path to push alerts.
5. **Stage-gated evolution** — decision support for months before semi-autonomous.
6. **Small files, explicit code, linters** — optimize for Claude Code's context window.

---

## Cross-Cutting Summary

### Recommended Architecture Stack

| Concern | Recommendation | Cost |
|---------|---------------|------|
| Primary DB | SQLite (WAL mode) | Free |
| Vector search | sqlite-vec extension | Free |
| Analytics (later) | DuckDB analytical layer | Free |
| Workflow orchestration | n8n (Docker on NUC) | Free |
| Agent framework | Claude Agent SDK (Python) | API tokens |
| Web crawling | Crawl4AI | Free |
| News monitoring | Finnhub + Tiingo + RSS/feedparser | Free |
| Social monitoring | Reddit (PRAW) + StockTwits | Free |
| Macro data | FRED API (fredapi) | Free |
| Insider data | edgartools Form 4 | Free |
| Backtesting | QuantConnect free tier (MCP server) | Free |
| Notifications | ntfy.sh (self-hosted on NUC) | Free |
| Broker execution | Alpaca MCP (interactive) + alpaca-py (programmatic) | Free |
| Context management | Pre-summarization + prompt caching + RAG | API tokens |

### Monthly Cost Estimate

- **Phase 1** (immediate): **$10-20/mo** — Claude API tokens only
- **Phase 2** (add social signals): **$35-45/mo** — add Quiver Quantitative ($25/mo)
- **Phase 3** (consolidate data): **$149+/mo** — add FMP Ultimate if needed

### Top 5 Patterns to Implement

1. **Bull/Bear debate** in research analysis (from TradingAgents)
2. **Pre-summarization → prompt caching → RAG** context pipeline
3. **n8n + FastAPI sidecar** for scheduled research and notifications
4. **Domain-specific MCP tools** for research DB (not raw SQL)
5. **Stage-gated autonomy** with paper trading validation at each stage
