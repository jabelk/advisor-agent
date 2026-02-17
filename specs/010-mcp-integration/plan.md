# Implementation Plan: MCP Integration

**Branch**: `010-mcp-integration` | **Date**: 2026-02-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-mcp-integration/spec.md`

## Summary

Build a custom FastMCP server exposing the research database (signals, documents, watchlist, safety state, audit log, pipeline status) as 7 read-only tools for Claude Desktop. Configure Claude Desktop with three MCP servers: custom research DB, Alpaca trading (official), and SEC EDGAR filings (community). Server supports stdio (local dev) and HTTP (NUC deployment) transport.

## Technical Context

**Language/Version**: Python 3.12+ (existing codebase)
**Primary Dependencies**: `fastmcp>=2.14,<3` (new); sqlite3, pathlib (stdlib); existing `finance_agent` package
**Storage**: SQLite read-only access (`file:{path}?mode=ro` URI), filesystem for document content
**Testing**: pytest with mocked SQLite databases
**Target Platform**: Intel NUC (Linux, HTTP mode) + macOS (stdio mode for dev)
**Project Type**: Single Python package (extends existing `finance_agent`)
**Performance Goals**: <2 seconds per tool call (SC-001); concurrent reads while pipeline writes
**Constraints**: Read-only DB access (FR-008); document content truncated at 50K chars (FR-010)
**Scale/Scope**: ~10-20 watchlist companies, single user, 7 tools

## Constitution Check

*GATE: All gates pass.*

| Gate | Status | Notes |
|------|--------|-------|
| Safety First | PASS | Safety state exposed read-only (FR-005, FR-008). Kill switch status visible to Claude for pre-trade checks. No write operations. |
| Research-Driven | PASS | All research data accessible via MCP tools — signals cite source documents, documents cite data sources |
| Modular Architecture | PASS | MCP server is a new independent module (`mcp/`). Uses FastMCP (off-the-shelf). ~150 LOC custom code. |
| Audit Everything | PASS | Audit log exposed via `get_audit_log` tool (FR-006). MCP server itself is read-only so no new audit events needed. |
| Security by Design | PASS | DB path via env var, not hardcoded. API keys for Alpaca/EDGAR in Claude Desktop config env, not in source. Read-only DB prevents data modification. |

## Project Structure

### Documentation (this feature)

```text
specs/010-mcp-integration/
├── plan.md              # This file
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: tool parameter/response schemas
├── quickstart.md        # Phase 1: testing and verification guide
├── contracts/
│   └── mcp-tools.md     # Phase 1: MCP tool contracts
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```text
src/finance_agent/
├── mcp/                        # NEW: Custom MCP server module
│   ├── __init__.py             # Package init
│   └── research_server.py      # FastMCP server with 7 tools
├── data/                       # Existing: data ingestion
├── research/                   # Existing: analysis pipeline
├── safety/                     # Existing: kill switch + risk limits
├── cli.py                      # Existing: extend with MCP commands
├── config.py                   # Existing: add MCP config fields
└── db.py                       # Existing: reference for schema

tests/
├── unit/
│   └── test_mcp_server.py      # NEW: unit tests for all 7 tools
├── integration/
│   └── test_mcp_integration.py # NEW: end-to-end MCP server test
└── conftest.py                 # Existing: extend with MCP fixtures

docs/
└── claude-desktop-config.json.example  # NEW: example Claude Desktop config
```

**Structure Decision**: Single Python package. New `mcp/` directory under existing `src/finance_agent/`. The MCP server is a standalone module that can be run as `python -m finance_agent.mcp.research_server` or via `fastmcp run`.

---

## MCP Server Design

### Tool Definitions (mapped to spec requirements)

| Tool | FR | Parameters | Returns |
|------|-----|-----------|---------|
| `get_signals` | FR-001 | `ticker: str`, `limit: int = 20`, `signal_type: str = ""`, `days: int = 30` | List of signals with company, document, type, confidence, summary, timestamp |
| `list_documents` | FR-002 | `ticker: str = ""`, `content_type: str = ""`, `limit: int = 20`, `days: int = 90` | List of document metadata (title, type, date, company, analysis status) |
| `read_document` | FR-003 | `document_id: int` | Document metadata + full text content (truncated at 50K chars per FR-010) |
| `get_watchlist` | FR-004 | *(none)* | List of active companies with ticker, name, CIK, sector |
| `get_safety_state` | FR-005 | *(none)* | Kill switch status + all risk limit values |
| `get_audit_log` | FR-006 | `event_type: str = ""`, `limit: int = 50`, `days: int = 7` | Recent audit log entries with timestamp, event type, source, payload |
| `get_pipeline_status` | FR-007 | *(none)* | Most recent ingestion run: timing, status, doc count, signal count, errors |

### Transport Configuration

```python
# Server supports both transports via __main__ entry point
# Default: stdio (for Claude Desktop local)
# Flag: --http (for NUC deployment)

from fastmcp import FastMCP

mcp = FastMCP("Finance Agent Research DB")

if __name__ == "__main__":
    import sys
    if "--http" in sys.argv:
        mcp.run(transport="http", host="0.0.0.0", port=8000)
    else:
        mcp.run()  # stdio default
```

### Database Access Pattern

All tools use read-only SQLite connections:

```python
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH", "data/finance_agent.db")

def _get_readonly_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn
```

### Claude Desktop Configuration (FR-009)

Three MCP servers in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "finance-research": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/finance-agent", "python", "-m", "finance_agent.mcp.research_server"],
      "env": {
        "DB_PATH": "/path/to/data/finance_agent.db",
        "RESEARCH_DATA_DIR": "/path/to/research_data"
      }
    },
    "alpaca": {
      "command": "uvx",
      "args": ["alpaca-mcp-server", "serve"],
      "env": {
        "ALPACA_API_KEY": "your-paper-api-key",
        "ALPACA_SECRET_KEY": "your-paper-secret-key",
        "ALPACA_PAPER_TRADE": "True"
      }
    },
    "sec-edgar": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "SEC_EDGAR_USER_AGENT=Your Name (your@email.com)", "stefanoamorelli/sec-edgar-mcp:latest"]
    }
  }
}
```

**For NUC deployment** (remote HTTP), replace `finance-research` entry with:

```json
{
  "finance-research": {
    "command": "npx",
    "args": ["mcp-remote", "http://nuc-ip:8000/mcp", "--allow-http"]
  }
}
```

---

## Complexity Tracking

No constitution violations to justify. All decisions align with principles. The MCP server adds ~150 LOC of custom code, well within the "less code, more context" constraint.
