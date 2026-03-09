# Quickstart: MCP Pattern Lab Tools

**Feature**: 015-mcp-pattern-tools

## What It Does

Adds 3 MCP tools to the existing research server so Jordan can run backtests, compare pattern variants, and export reports directly from Claude Desktop without switching to the terminal.

## Prerequisites

- Pattern Lab (011) is set up with confirmed patterns
- Pattern Lab Extensions (014) are installed (multi-ticker, A/B testing, export)
- MCP server configured in Claude Desktop settings
- Alpaca API keys configured in environment

## Scenario 1: Multi-Ticker Backtest from Claude Desktop

In Claude Desktop, ask:

> "Backtest pattern 1 across ABBV, MRNA, and PFE from January 2024 to December 2025"

**Expected**: Claude calls `run_backtest` with `pattern_id=1, tickers="ABBV,MRNA,PFE", start_date="2024-01-01", end_date="2025-12-31"`. The tool returns structured data with per-ticker breakdown and combined aggregate. Claude presents the results conversationally, highlighting key metrics like win rate and average return per ticker.

## Scenario 2: A/B Test from Claude Desktop

In Claude Desktop, ask:

> "Compare patterns 1 and 2 on ABBV and MRNA — which one works better?"

**Expected**: Claude calls `run_ab_test` with `pattern_ids="1,2", tickers="ABBV,MRNA"`. The tool returns variant metrics, pairwise p-values, and the best variant. Claude explains whether the difference is statistically significant in plain language, e.g., "Pattern #2 had a higher win rate (22% vs 11%), but this difference is not statistically significant (p=1.00). With only 9 trades per variant, you'd need more data to draw reliable conclusions."

## Scenario 3: Export from Claude Desktop

In Claude Desktop, ask:

> "Export the latest backtest results for pattern 1 as a markdown report"

**Expected**: Claude calls `export_backtest` with `pattern_id=1`. The tool generates a markdown file and returns the file path. Claude confirms: "I've exported the backtest results for Pattern #1 to pattern-1-backtest-2026-03-08.md."

## Key Files

| File | Purpose |
|------|---------|
| `src/finance_agent/mcp/research_server.py` | 3 new MCP tool functions added to existing server |
| `tests/unit/test_mcp_pattern_tools.py` | Unit tests for new MCP tools |

## Safety

- No trading operations — all tools are analysis and reporting only.
- Backtest and A/B test tools write to market data cache only (performance optimization).
- Export writes markdown files to the local filesystem. No client data is ever included.
- Alpaca API keys are read from environment variables, never exposed through MCP tool parameters.
- Kill switch from the safety module continues to function normally for any active paper trades.
