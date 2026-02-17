# Research: MCP Integration

**Feature**: 010-mcp-integration | **Date**: 2026-02-17

## Decision 1: FastMCP Version

**Decision**: Use `fastmcp>=2.14,<3` (pin to v2.x stable)

**Rationale**: FastMCP 2.14.5 is the current production-stable release. v3.0 is in RC (3.0.0rc2, Feb 14 2026) and may introduce breaking changes. The v2 API covers all our needs (tool decorators, stdio/HTTP transport, error handling).

**Alternatives considered**:
- FastMCP 3.0 RC: Has useful features (versioned tools, OpenTelemetry) but not stable yet. Can upgrade later.
- Raw `mcp` SDK: Lower level, more boilerplate. FastMCP wraps it with a cleaner decorator API.

## Decision 2: Transport Strategy

**Decision**: Build server with dual transport support — stdio (default for development/local) and HTTP (for NUC deployment). Use `mcp-remote` for Claude Desktop to connect to HTTP server on NUC.

**Rationale**:
- **stdio**: Default for Claude Desktop. Zero network config. Best for development and local testing.
- **HTTP (streamable-http)**: Required for the NUC deployment scenario where Claude Desktop on macOS connects to the research DB on the NUC. FastMCP supports `mcp.run(transport="http", host="0.0.0.0", port=8000)`.
- **mcp-remote**: Acts as stdio-to-HTTP bridge for Claude Desktop. Config: `npx mcp-remote http://nuc-ip:8000/mcp --allow-http`.

**Known issue**: There's a [GitHub issue](https://github.com/geelen/mcp-remote/issues/113) about mcp-remote incompatibility with FastMCP streamable-http session management. Mitigation: use `stateless_http=True` on the FastMCP server, or fall back to SSE transport if needed.

**Alternatives considered**:
- SSE transport: Legacy, being deprecated. Not recommended for new projects.
- SSH tunnel + stdio: Works but more complex setup. Unnecessary when HTTP + mcp-remote works.
- FastMCP `create_proxy()`: Another approach for bridging remote servers. Requires a proxy Python script on the client side.

## Decision 3: Database Access Pattern

**Decision**: Read-only SQLite access via context manager. Open a fresh connection per tool call with `uri=True` and `mode=ro` for SQLite read-only mode. Use WAL mode for concurrent access.

**Rationale**: The MCP server should never modify the research database. Read-only mode prevents accidental writes from conversational queries. WAL mode (already configured on the DB) allows the research pipeline to write while the MCP server reads.

**Pattern** (from FastMCP SQLite Explorer reference):
```python
@mcp.tool()
def query_signals(ticker: str) -> list[dict]:
    """Get research signals for a company."""
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT ... WHERE ticker = ?", (ticker,)).fetchall()
        return [dict(row) for row in rows]
```

**Alternatives considered**:
- Reuse `get_connection()` from `db.py`: Sets `foreign_keys=ON` and WAL mode, but also allows writes. We specifically want read-only for MCP.
- Generic SQL query tool: Too permissive. Better to have purpose-built tools with parameterized queries.

## Decision 4: MCP Server Architecture

**Decision**: Single Python module `src/finance_agent/mcp/research_server.py` with 7 tools. Server reads DB path from `DB_PATH` env var (or config default). Research data directory path from `RESEARCH_DATA_DIR` env var.

**Tools** (mapped to spec FR-001 through FR-007):
1. `get_signals` — Query research signals by ticker, filterable by date/type/confidence (FR-001)
2. `list_documents` — List ingested source documents, filterable by company/type/date (FR-002)
3. `read_document` — Retrieve full text content of a specific document (FR-003)
4. `get_watchlist` — List active watchlist companies (FR-004)
5. `get_safety_state` — Read kill switch status and risk limits (FR-005)
6. `get_audit_log` — Recent audit log entries, filterable by event type/date (FR-006)
7. `get_pipeline_status` — Most recent research pipeline run status (FR-007)

**Rationale**: Purpose-built tools give Claude better tool descriptions and parameter types than a generic SQL interface. Each tool returns structured, well-formatted data that Claude can present conversationally.

## Decision 5: Claude Desktop Configuration

**Decision**: Provide three configurations in a single `claude_desktop_config.json`:

1. **Research DB MCP** (custom, stdio for local / mcp-remote for NUC):
   ```json
   {
     "command": "uv",
     "args": ["run", "--project", "/path/to/finance-agent", "python", "-m", "finance_agent.mcp.research_server"],
     "env": {"DB_PATH": "/path/to/finance_agent.db", "RESEARCH_DATA_DIR": "/path/to/research_data"}
   }
   ```

2. **Alpaca MCP** (official, stdio):
   ```json
   {
     "command": "uvx",
     "args": ["alpaca-mcp-server", "serve"],
     "env": {"ALPACA_API_KEY": "...", "ALPACA_SECRET_KEY": "...", "ALPACA_PAPER_TRADE": "True"}
   }
   ```

3. **SEC EDGAR MCP** (community, Docker stdio):
   ```json
   {
     "command": "docker",
     "args": ["run", "-i", "--rm", "-e", "SEC_EDGAR_USER_AGENT=Jason Belk (email@example.com)", "stefanoamorelli/sec-edgar-mcp:latest"]
   }
   ```

**Rationale**: All three use stdio transport for Claude Desktop, which is the simplest and most reliable. The research DB server can also run in HTTP mode for NUC deployment.

## Decision 6: Alpaca MCP Server

**Decision**: Use the official `alpacahq/alpaca-mcp-server` via `uvx`.

**Details**:
- Install: `uvx alpaca-mcp-server serve` (no git clone needed)
- Env vars: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_PAPER_TRADE` (default True)
- 43 tools: account, positions, assets, watchlists, calendar, stock data, crypto data, options, orders
- Paper trading by default — aligns with Safety First principle

## Decision 7: SEC EDGAR MCP Server

**Decision**: Use `stefanoamorelli/sec-edgar-mcp` via Docker.

**Details**:
- Package: `sec-edgar-mcp` (PyPI) or Docker image `stefanoamorelli/sec-edgar-mcp:latest`
- Env: `SEC_EDGAR_USER_AGENT` (required, SEC fair access policy)
- 10 tools: company_lookup, company_info, company_facts, filings_recent, filing_content, eight_k_analysis, section_extraction, financial_statements, xbrl_parse, insider_transactions
- AGPL-3.0 license (fine for personal use)

**Alternatives considered**:
- `leopoldodonnell/edgar-mcp`: Another community option but less maintained
- Direct edgartools usage: Already in our pipeline — SEC EDGAR MCP adds Claude Desktop interactive access
