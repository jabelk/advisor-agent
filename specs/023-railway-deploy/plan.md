# Implementation Plan: Railway Deployment

**Branch**: `023-railway-deploy` | **Date**: 2026-03-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/023-railway-deploy/spec.md`

## Summary

Deploy the advisor-agent MCP server to Railway as a containerized service with Streamable HTTP transport, Bearer token authentication via FastMCP's StaticTokenVerifier, persistent SQLite storage via Railway volumes, and automated CI/CD deployment from GitHub Actions.

## Technical Context

**Language/Version**: Python 3.12+ with type hints
**Primary Dependencies**: fastmcp 2.14.5 (Streamable HTTP + StaticTokenVerifier), simple_salesforce, alpaca-py, anthropic
**Storage**: SQLite (WAL mode) on Railway persistent volume at `/app/data`
**Testing**: pytest (existing suite, 576 tests)
**Target Platform**: Railway (Docker container, `*.railway.app` domain with auto TLS)
**Project Type**: Single project (existing codebase)
**Performance Goals**: MCP tool invocations < 10s for standard operations
**Constraints**: Railway free/starter tier, single container instance
**Scale/Scope**: Single user (Jordan), ~20+ MCP tools

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Client Data Isolation | PASS | Salesforce developer sandbox only, no production CRM data |
| II. Research-Driven | PASS | No change to research pipeline |
| III. Advisor Productivity | PASS | Cloud deployment makes tools available from any network |
| IV. Safety First | PASS | Paper trading by default, kill switch unchanged |
| V. Security by Design | PASS | Secrets as Railway env vars, Bearer token auth on endpoint, no secrets in code/logs/images |
| Salesforce-native first | PASS | No new local storage — existing SQLite for research DB only |

## Project Structure

### Documentation (this feature)

```text
specs/023-railway-deploy/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal — infra feature)
├── quickstart.md        # Phase 1 output (deployment guide)
├── contracts/           # Phase 1 output (health check contract)
└── tasks.md             # Phase 2 output
```

### Source Code (changes to existing files + new files)

```text
# New files
railway.toml                              # Railway build/deploy config
.github/workflows/ci.yml                  # CI/CD pipeline

# Modified files
Dockerfile                                # Change CMD to MCP server with --http
docker-entrypoint.sh                      # Add MCP_API_TOKEN handling
src/finance_agent/mcp/research_server.py  # Add health endpoint, auth, PORT env var
```

**Structure Decision**: This is an infrastructure feature — no new Python modules, just config files and minor modifications to existing entry points.

## Key Architecture Decisions

### 1. Authentication: FastMCP StaticTokenVerifier

The MCP server validates a Bearer token on every request using FastMCP's built-in auth. The token is stored as `MCP_API_TOKEN` Railway environment variable. No external auth service needed.

```
Claude Desktop → mcp-remote bridge → HTTPS (Railway TLS) → FastMCP StaticTokenVerifier → Tool execution
```

### 2. Claude Desktop Connection: mcp-remote bridge

Claude Desktop's config file only supports local process spawning. The `mcp-remote` npm package bridges HTTP-to-stdio:

```json
{
  "mcpServers": {
    "advisor-agent": {
      "command": "npx",
      "args": ["mcp-remote", "https://<app>.railway.app/mcp"]
    }
  }
}
```

### 3. Health Check: /health endpoint

A new HTTP endpoint at `/health` (separate from the MCP `/mcp` path) reports:
- Server status (healthy/degraded/unhealthy)
- Required integrations: Salesforce, Anthropic API key, Alpaca
- Optional integrations: Finnhub, EarningsCall
- Storage: DB file existence and size
- Uptime

### 4. CI/CD Pipeline

GitHub Actions workflow triggered on push/PR to main:
1. Change detection (skip if only docs/specs changed)
2. Lint (ruff) + Test (pytest) + Security scan (trivy) — parallel
3. Gate job (aggregates pass/fail)
4. Deploy to Railway via CLI (main branch only, after gate passes)
5. Post-deploy health check

### 5. Persistent Storage

Railway volume mounted at `/app/data` for SQLite database. Research data directory at `/app/research_data`. Both created in Dockerfile, volume attached via Railway dashboard.

## Complexity Tracking

No constitution violations. No complexity justification needed.
