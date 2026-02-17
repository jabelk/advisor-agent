# Quickstart: MCP Integration Testing & Verification

**Feature**: 010-mcp-integration | **Date**: 2026-02-17

## Prerequisites

- Python 3.12+ with uv
- Finance agent project cloned and dependencies installed (`uv sync`)
- SQLite database with at least one pipeline run (or use test fixtures)
- Claude Desktop installed (for end-to-end testing)

## 1. Run Unit Tests

```bash
# Run all MCP server unit tests
uv run pytest tests/unit/test_mcp_server.py -v

# Expected: 7 tool tests + edge case tests pass
```

## 2. Run Integration Tests

```bash
# Run MCP integration test (starts real server, sends MCP protocol messages)
uv run pytest tests/integration/test_mcp_integration.py -v

# Expected: Server starts, tools respond, read-only enforced
```

## 3. Manual Server Testing (stdio mode)

```bash
# Start the MCP server in stdio mode (default)
uv run python -m finance_agent.mcp.research_server

# The server reads JSON-RPC from stdin and writes to stdout.
# Send a tools/list request to verify tools are registered:
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | uv run python -m finance_agent.mcp.research_server
```

Expected output: JSON response listing all 7 tools with their descriptions and parameter schemas.

## 4. Manual Server Testing (HTTP mode)

```bash
# Start the MCP server in HTTP mode
DB_PATH=data/finance_agent.db uv run python -m finance_agent.mcp.research_server --http

# Server listens on http://0.0.0.0:8000
# Test with curl:
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## 5. Claude Desktop Configuration (Local/stdio)

1. Copy the example config:
   ```bash
   cp docs/claude-desktop-config.json.example ~/tmp/claude-desktop-config.json
   ```

2. Edit paths in the config to match your local setup:
   - Replace `/path/to/finance-agent` with your actual project path
   - Replace `/path/to/data/finance_agent.db` with your actual DB path

3. Copy to Claude Desktop config location:
   ```bash
   cp ~/tmp/claude-desktop-config.json "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
   ```

4. Restart Claude Desktop.

5. Verify tools appear in the Claude Desktop tool list (hammer icon).

## 6. Verification Checklist

### Tool Verification (per FR)

| Tool | FR | Test Query (in Claude Desktop) | Expected Result |
|------|----|-------------------------------|-----------------|
| `get_signals` | FR-001 | "What are the latest signals for AAPL?" | List of signals with ticker, type, confidence, summary |
| `list_documents` | FR-002 | "Show me all ingested documents this month" | Document list with titles, types, dates |
| `read_document` | FR-003 | "Show me document #1 in full" | Full document content (or truncation note if >50K) |
| `get_watchlist` | FR-004 | "What companies am I tracking?" | Active companies with tickers, names, sectors |
| `get_safety_state` | FR-005 | "Can I trade right now?" | Kill switch status + risk limits |
| `get_audit_log` | FR-006 | "Show me recent system events" | Timestamped audit entries |
| `get_pipeline_status` | FR-007 | "When did the pipeline last run?" | Latest run timing, status, counts |

### Non-Functional Verification

| Requirement | Test | Expected |
|-------------|------|----------|
| FR-008 (read-only) | Try to modify DB via tool | Connection opened with `?mode=ro`, writes fail |
| FR-010 (truncation) | Read a document >50K chars | Content truncated with message |
| SC-001 (performance) | Time a `get_signals` call | Response within 2 seconds |
| SC-004 (concurrent) | Run pipeline while querying MCP | Both succeed without lock errors |

### External MCP Server Verification

| Server | Test | Expected |
|--------|------|----------|
| Alpaca | "What are my positions?" | Account/position info from Alpaca paper account |
| SEC EDGAR | "Look up Apple's latest 10-K filing" | Filing info from SEC EDGAR |
| Research DB unavailable | Stop research server, query Alpaca | Alpaca still works, research tools show error |

## 7. Troubleshooting

**Server won't start**: Check `DB_PATH` env var points to an existing SQLite file.

**Empty results**: Run the research pipeline first (`uv run finance-agent research run`) to populate the database.

**Claude Desktop doesn't show tools**: Restart Claude Desktop after config changes. Check `~/Library/Logs/Claude/` for MCP connection errors.

**HTTP mode connection refused**: Ensure port 8000 is not in use. Check firewall rules if connecting from another machine.

**mcp-remote errors**: Known issue with FastMCP streamable-http sessions. Use `stateless_http=True` flag or fall back to SSE transport.
