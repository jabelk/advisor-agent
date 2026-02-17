# 006 Architecture Research Sprint

## Context & Motivation

Features 001-005 built a working end-to-end pipeline: SEC/Finnhub data ingestion → LLM analysis → deterministic scoring → proposal lifecycle → order execution via alpaca-py → CLI interface. End-to-end test on 2026-02-17 confirmed it all works against Alpaca paper trading.

**Problem**: We over-engineered the execution, scoring, and CLI layers. ~3,000 lines of custom plumbing code doing what existing tools handle. This eats context budget (the user codes primarily via Claude Code) and pulls focus from the real differentiator: research and analysis.

**Pivot**: The system should be a **research analyst + decision support tool**, not an automated trading bot. User trades a couple times per week based on synthesized research, not 20 automated trades per day.

## New Vision

- **Autonomous agents** crawl and discover information throughout the day (news, filings, social, blogs)
- **Claude synthesizes** the research into actionable analysis
- **User makes the decisions** — reviews analysis, asks follow-up questions, decides to act
- **MCP server executes** — conversational: "Buy 10 shares of AAPL" and it's done
- **Maybe someday**: agents trade autonomously once research quality is proven

## What to Keep from 001-005

- Research data sources (SEC EDGAR, Finnhub, EarningsCall, 13F, Acquired, Stratechery)
- SQLite persistence + audit trail
- Safety rails (risk limits, kill switch) — can't be LLM-only
- The `filter_10k_markdown()` fix for SEC boilerplate

## What to Replace

- Custom execution layer (orders.py, reconcile.py, status.py) → Alpaca MCP server
- Deterministic scoring formula (scoring.py) → conversational Claude analysis
- Proposal lifecycle (proposals.py) → human decision in conversation
- CLI interface (1,600 lines) → Claude Desktop / conversational interface
- Market data client (bars.py, indicators.py) → Alpaca MCP or lightweight wrapper

---

## Research Areas

### 1. MCP Server Ecosystem
- **Alpaca MCP server**: Setup, capabilities, limitations, Claude Desktop integration
- **Other finance MCP servers**: Are there MCP servers for SEC data, news, market data?
- **MCP server authoring**: How hard to build custom MCP servers for our research sources?
- **Claude Desktop configuration**: How to wire up multiple MCP servers

### 2. Workflow Automation (n8n, etc.)
- **n8n**: Self-hosted workflow automation — can it run on the Intel NUC?
- **n8n + AI**: Does n8n have LLM/Claude integrations? Can it trigger analysis?
- **Alternatives**: Temporal, Windmill, Activepieces — what do people prefer for AI workflows?
- **Event-driven**: RSS monitoring, webhook triggers, scheduled crawls
- **Key question**: Can n8n orchestrate the research pipeline (crawl → ingest → analyze → notify)?

### 3. Autonomous Research Agents
- **Web crawling agents**: What tools let AI agents browse the web, find news, follow leads?
- **Browser-use / computer-use**: Claude computer use, Playwright, browser agents
- **News aggregation**: How do people build real-time financial news monitors?
- **Social media monitoring**: Reddit (r/wallstreetbets, r/stocks), Twitter/X fintwit, StockTwits
- **Academic research**: arXiv, SSRN finance papers — any tools to monitor and summarize?

### 4. Existing AI Trading/Research Frameworks
- **TradingAgents** (Tauric Research): Multi-agent debate system — any useful patterns to borrow?
- **FinRobot, FinGPT, BloombergGPT**: What's the state of open-source financial AI?
- **LangChain/LangGraph finance agents**: Community templates or examples?
- **Quantitative frameworks**: QuantConnect, Zipline, Backtrader — any with LLM integration?
- **Commercial tools**: What do retail AI traders actually use? (Reddit/HN survey)

### 5. Data Sources Beyond What We Have
- **Alternative data**: Satellite imagery, shipping data, app usage (too expensive?)
- **Earnings call services**: Beyond EarningsCall.biz — are there better/cheaper options?
- **Real-time news**: Benzinga, NewsAPI, GDELT — what's best for financial news?
- **Options flow / unusual activity**: Any free or cheap sources?
- **Insider trading data**: Beyond Finnhub — OpenInsider, SEC Form 4 direct?
- **Macro data**: FRED, BLS, Treasury — important for context?

### 6. Architecture Patterns
- **How do others structure AI trading research systems?**
- **Storage**: Keep SQLite or move to something else?
- **How to feed research context into Claude conversations efficiently?**
- **MCP server as the persistence layer?** (Custom MCP server wrapping our SQLite DB)
- **How to handle the "daily briefing" pattern**: Agent crawls all day → evening summary for user

---

## Deliverables

1. **`findings.md`** — Research findings organized by area, with links and evaluations
2. **Updated constitution** — New principles reflecting research-first, human-decides architecture
3. **Updated `CLAUDE.md`** — New tech stack, architecture description
4. **`architecture-proposal.md`** — New system design with component diagram
5. **Migration notes** — What to keep, what to rewrite, what to delete from 001-005

## Research Method

- Web searches (Reddit, HN, blogs, GitHub, academic papers)
- Evaluate GitHub repos (stars, activity, documentation quality)
- Try tools hands-on where possible (Alpaca MCP server, n8n on NUC)
- Read through community discussions for real-world experience reports
- Prioritize tools that are actively maintained and have good docs
