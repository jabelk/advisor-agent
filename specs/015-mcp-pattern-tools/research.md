# Research: MCP Pattern Lab Tools

**Feature**: 015-mcp-pattern-tools
**Date**: 2026-03-08

## R1: Database Access Pattern for Backtest/A/B Tools

**Decision**: Use a read-write database connection for backtest and A/B test tools, separate from the read-only connection used by existing query tools. The existing `_get_readonly_conn()` pattern cannot be used because `fetch_and_cache_bars()` writes to the market data cache.

**Rationale**: The existing 11 MCP tools use `_get_readonly_conn()` which opens the database with `?mode=ro`. The backtest and A/B test tools need to call `fetch_and_cache_bars()` from `market_data.py`, which caches Alpaca price bars in the database to avoid redundant API calls. This cache write is essential for performance — without it, every backtest request would re-fetch all price data from Alpaca.

The tools themselves are "read-only in intent" — they do not create trades, modify patterns, or change any user-facing state. The only write is to the market data cache, which is an implementation optimization. This distinction is documented in the tool docstrings.

A helper `_get_readwrite_conn()` function will be added alongside the existing `_get_readonly_conn()`, using the same busy timeout and row factory but without the `?mode=ro` flag. This follows the existing pattern while making the access mode explicit.

**Alternatives considered**:
- **Use read-only connection and pre-populate cache via CLI**: Require the user to run the CLI backtest first to populate the cache, then the MCP tool only reads cached data. This defeats the purpose — Jordan wants to stay in Claude Desktop without switching to the terminal. Rejected.
- **Separate cache database**: Store market data cache in a different SQLite file so the main DB can remain read-only. Adds complexity (two DB files, cross-DB queries) for no user benefit. Rejected.
- **In-memory cache only**: Cache price data in memory during the MCP server session. Lost on restart, wastes Alpaca API calls across sessions. Rejected.

## R2: MCP Tool Return Format

**Decision**: Return Pydantic model `.model_dump()` dicts from all tools. Let FastMCP handle serialization. Do not return pre-formatted text.

**Rationale**: Claude Desktop works best when tools return structured data it can interpret and present conversationally. Returning a dict with fields like `win_rate`, `avg_return_pct`, `p_value` lets Claude say "Pattern #2 had a 63% win rate, which was not significantly different from Pattern #1 (p=0.42)" rather than regurgitating a pre-formatted table.

The existing MCP tools follow this pattern — `get_backtest_results` returns dicts, not formatted strings. The new tools should be consistent.

For the `AggregatedBacktestReport` and `ABTestResult` models, `.model_dump()` produces nested dicts that are JSON-serializable. FastMCP handles the serialization automatically.

**Alternatives considered**:
- **Return formatted text**: Match the CLI output format. Claude would then need to parse the formatted text to answer follow-up questions. Defeats the purpose of structured tool results. Rejected.
- **Return simplified summary**: Strip out trade-level detail and return only aggregate metrics. Loses information Claude could use (e.g., "show me the worst trade"). Rejected — return full data, let Claude decide what to present.

## R3: Alpaca API Key Handling in MCP Context

**Decision**: Read Alpaca API keys from environment variables at tool call time, matching how the existing MCP server reads `DB_PATH`. If keys are missing, return a structured error message rather than crashing.

**Rationale**: The MCP server runs as a subprocess launched by Claude Desktop. Environment variables are the standard way to pass configuration to MCP servers (documented in the Claude Desktop MCP config). The existing server already uses `os.environ.get("DB_PATH", ...)`.

For the backtest and A/B test tools, the Alpaca paper trading keys (`ALPACA_PAPER_API_KEY`, `ALPACA_PAPER_SECRET_KEY`) must be available. If missing, the tool should return `{"error": "Alpaca API keys not configured. Set ALPACA_PAPER_API_KEY and ALPACA_PAPER_SECRET_KEY."}` rather than raising an exception.

The export tool does not need Alpaca keys (it reads from the database).

**Alternatives considered**:
- **Pass keys as tool parameters**: Would expose secrets in the MCP tool call payload, visible in logs. Security violation per constitution V. Rejected.
- **Config file**: Read from `.env` file at a known path. Adds a dependency on `python-dotenv` in the MCP server context and assumes a specific file location. Environment variables are simpler and more portable. Rejected.
