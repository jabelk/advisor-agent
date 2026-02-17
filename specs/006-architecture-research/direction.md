# Project Direction & Key Decisions

Captured from architecture pivot discussion on 2026-02-17.

## Who Is Building This

Jason Belk — Cisco engineer in Reno NV. Codes primarily through Claude Code (AI agent), not manually. This means **context window is a real constraint** — every line of custom code we maintain is context that can't be spent on innovation. Willing to pay for tools and data services.

## What We Learned from 001-005

- Built a full end-to-end pipeline in 5 features: scaffolding → research ingestion → market data → decision engine → order execution
- End-to-end test against Alpaca paper account worked (2026-02-17)
- The engine correctly refused to trade AAPL (bearish signals, score -0.39 < 0.45 threshold) — safety-first works
- **But**: ~3,000 lines of execution/scoring/CLI code doing what Alpaca MCP server + conversational Claude can handle natively
- We were debugging JSON parsing and SEC boilerplate filtering — plumbing, not intelligence
- The spec-kit workflow drove 40+ task specs per feature — great for teams, overkill for a solo AI-assisted experiment

## The Real Goal

**Not** an automated day trading bot making 20 trades/day.

**Actually**: A research-powered investment system where:
- Trade a couple times per week based on deep analysis
- The computer's job is to **find, read, and distill massive amounts of information**
- The human's job is to **make the big decisions** based on synthesized research
- The interaction is **conversational** — back-and-forth with Claude to explore nuance, not deterministic scoring formulas
- Financial data isn't just numbers — it requires context, narrative analysis, follow-up questions

## Core Philosophy

1. **Don't reinvent wheels** — use MCP servers, n8n, existing frameworks. Only build what's truly custom.
2. **Less code = more context** — every line of plumbing we maintain is context Claude Code can't use for research innovation
3. **Conversational > formulaic** — a weighted scoring formula can't capture the nuance of "this CEO's tone shifted in the earnings call". Claude in conversation can.
4. **Research is the differentiator** — anyone can place an order via MCP. The unique value is in what data we find, how we analyze it, and how we synthesize it.
5. **Autonomous discovery** — agents should crawl and find things throughout the day, not just pull from 3 known APIs on a schedule. News breaks, social media reacts, filings drop. The system should be always watching.
6. **Human-in-the-loop for now** — maybe agents trade on their own someday, but only after the research and analysis quality is proven. Start with decision support, earn trust, then automate.

## What to Keep

- **Research data sources** (SEC EDGAR, Finnhub, EarningsCall, 13F, Acquired, Stratechery) — these are a starting point, not the finish line
- **SQLite + filesystem persistence** — research artifacts need to be stored and searchable
- **Audit trail** — append-only logging of decisions and reasoning
- **Safety rails** — risk limits and kill switch can't be LLM-only, need hard programmatic limits
- **10-K boilerplate filter** — `filter_10k_markdown()` saves tokens on every filing

## What to Replace

| Current (001-005) | Replace With |
|---|---|
| `execution/` layer (641 lines orders.py) | Alpaca MCP server — one tool call |
| `engine/scoring.py` (deterministic formula) | Conversational Claude analysis |
| `engine/proposals.py` (lifecycle state machine) | Human decides in conversation |
| `cli.py` (1,600 lines, 20+ commands) | Claude Desktop as the interface |
| Scheduled data pulls from 3 sources | n8n workflows + autonomous crawling agents |

## What to Explore

- **n8n on the Intel NUC** — can it orchestrate crawlers, trigger analysis, send notifications?
- **MCP servers** — Alpaca for trading, custom MCP for our research DB, others?
- **Web crawling agents** — autonomous discovery of news, social signals, blog posts
- **Social media monitoring** — Reddit, Twitter/X fintwit, StockTwits
- **Better data sources** — what are retail AI traders actually paying for?
- **Claude Desktop workflow** — daily briefing pattern: agents research all day → Claude presents evening summary → user decides

## Evolution Path

1. **Now**: Research sprint — figure out what tools exist, don't write code yet
2. **Next**: Set up MCP servers + n8n on NUC, minimal custom code
3. **Then**: Build research agents that crawl and discover autonomously
4. **Eventually**: Agents suggest trades with full reasoning, user approves via conversation
5. **Maybe someday**: Agents trade within tight guardrails (small position sizes, proven strategies only)
