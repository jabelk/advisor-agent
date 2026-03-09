# Implementation Plan: MCP Pattern Lab Tools

**Branch**: `015-mcp-pattern-tools` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/015-mcp-pattern-tools/spec.md`

## Summary

Add 3 MCP tools to the existing research server: `run_backtest` (multi-ticker backtest), `run_ab_test` (statistical variant comparison), and `export_backtest` (markdown report generation). These reuse the backtest, stats, and export modules from feature 014 and expose them through Claude Desktop.

## Technical Context

**Language/Version**: Python 3.12+ with type hints
**Primary Dependencies**: fastmcp (MCP tool exposure), alpaca-py (market data), scipy (stats), pydantic (models)
**Storage**: SQLite (WAL mode) — read-only for pattern queries, read-write for market data cache
**Testing**: pytest
**Target Platform**: macOS/Linux, Claude Desktop via MCP stdio transport
**Project Type**: Single project (existing MCP server extension)
**Performance Goals**: Tool response within 2x CLI equivalent
**Constraints**: Alpaca API keys required for backtest/A/B tools; export writes to filesystem
**Scale/Scope**: 3 new MCP tools added to existing server with 11 tools

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| I. Client Data Isolation | PASS | Tools use only public market data (price bars). No client PII involved. |
| II. Research-Driven | PASS | Tools expose backtesting and statistical comparison — directly support data-driven decisions. |
| III. Advisor Productivity | PASS | Running backtests and comparisons from Claude Desktop eliminates terminal context switching. |
| IV. Safety First | PASS | No trading operations — backtest, analysis, and reporting only. |
| V. Security by Design | PASS | Alpaca keys read from environment, not exposed through MCP. Export writes only backtest data. |

All 5 gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/015-mcp-pattern-tools/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── mcp-tools.md     # MCP tool contracts
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/finance_agent/
├── mcp/
│   └── research_server.py          # MODIFY: add 3 new MCP tool functions

tests/
├── unit/
│   └── test_mcp_pattern_tools.py   # NEW: unit tests for new MCP tools
```

**Structure Decision**: Follows existing single-project pattern. All 3 new tools are added to the existing `research_server.py` file, consistent with how the 11 existing tools are organized. No new modules needed — the tools call into the existing backtest, stats, and export modules.
