# Research: Railway Deployment (023)

## Decision 1: Authentication Mechanism

**Decision**: Use FastMCP's built-in `StaticTokenVerifier` with a Bearer token stored as a Railway environment variable.

**Rationale**: Railway has no built-in OAuth2 proxy or auth layer. Their oauth2-proxy template is browser-based (Google login + cookies) — incompatible with programmatic MCP clients. FastMCP 2.x provides `StaticTokenVerifier` out of the box, requiring zero additional infrastructure. Claude Desktop supports Bearer token headers natively in MCP config.

**Alternatives considered**:
- Railway oauth2-proxy template — browser-based redirect flow, doesn't work for programmatic clients
- nginx-password-auth Railway template — HTTP Basic Auth, extra service to manage
- Self-managed JWT validation — overengineered for single-user deployment
- No auth (URL obscurity) — unacceptable for Salesforce-connected service

## Decision 2: Claude Desktop Connection Method

**Decision**: Use `mcp-remote` npm bridge in `claude_desktop_config.json` for initial deployment. Document Custom Connectors UI as alternative for Pro/Max plans.

**Rationale**: Claude Desktop's `claude_desktop_config.json` only supports the `command`/`args` pattern for spawning local processes — it cannot connect to remote HTTP URLs directly. The `mcp-remote` package bridges this by spawning a local process that proxies HTTP-to-stdio. Custom Connectors (Settings > Connectors > Add custom connector) is available on paid plans and connects to HTTPS URLs directly, but `mcp-remote` works universally.

**Alternatives considered**:
- Custom Connectors UI only — requires Pro/Max/Team plan, not universally available
- Keep SSH-over-stdio — defeats the purpose of cloud deployment
- Direct URL in config — not supported by Claude Desktop

## Decision 3: MCP Transport Protocol

**Decision**: Keep existing `mcp.run(transport="http", host="0.0.0.0", port=8000)` — this is Streamable HTTP in FastMCP 2.14.5.

**Rationale**: FastMCP 2.x's `transport="http"` implements the MCP Streamable HTTP spec (2025-03-26). The server exposes a single `/mcp` endpoint. SSE is deprecated. No code changes needed — the existing entry point is cloud-ready.

**Alternatives considered**:
- SSE transport — deprecated in MCP spec
- Custom HTTP wrapper — unnecessary, FastMCP handles it
- WebSocket — not part of MCP spec

## Decision 4: Railway Deployment Method

**Decision**: Deploy via Railway CLI (`railway up --detach --service <name>`) from GitHub Actions, following the family-meeting pattern.

**Rationale**: The family-meeting project uses this exact pattern successfully. Railway CLI deploys are triggered from CI after tests pass, providing a gated deployment pipeline. Railway's native GitHub auto-deploy skips the test gate.

**Alternatives considered**:
- Railway native GitHub auto-deploy — no test gate, less control
- Manual Railway CLI deploys — error-prone, no CI gate

## Decision 5: Health Check Implementation

**Decision**: Add a `/health` endpoint to the FastMCP server that reports server status, credential connectivity (Salesforce, Alpaca, Anthropic), and storage availability.

**Rationale**: Railway requires a health check endpoint for restart policy. The family-meeting project has an excellent pattern: categorize integrations as required vs optional, live-test each with timeouts, return "healthy"/"degraded"/"unhealthy" status.

**Alternatives considered**:
- Simple 200 OK — doesn't report integration status
- CLI `health` command only — not accessible via HTTP for Railway

## Decision 6: HTTPS/TLS

**Decision**: Use Railway's automatic TLS termination via the `*.railway.app` domain.

**Rationale**: Railway provides free `*.railway.app` domains with automatic TLS certificates. No need for Caddy, Cloudflare Tunnel, or manual certificate management.

**Alternatives considered**:
- Caddy reverse proxy — extra service, unnecessary with Railway's built-in TLS
- Cloudflare Tunnel — added complexity for no benefit
- Custom domain with Let's Encrypt — premature, can add later if needed

## Environment Variables Required

### Required for MCP Server
- `MCP_API_TOKEN` — Bearer token for FastMCP auth (new)
- `ANTHROPIC_API_KEY` — Claude API access
- `SFDC_CONSUMER_KEY`, `SFDC_CONSUMER_SECRET`, `SFDC_INSTANCE_URL`, `SFDC_USERNAME`, `SFDC_PASSWORD`, `SFDC_SECURITY_TOKEN`, `SFDC_LOGIN_URL` — Salesforce sandbox
- `ALPACA_PAPER_API_KEY`, `ALPACA_PAPER_SECRET_KEY` — Paper trading
- `EDGAR_IDENTITY` — SEC EDGAR user agent
- `DB_PATH` — SQLite database path (default: `/app/data/finance_agent.db`)
- `RESEARCH_DATA_DIR` — Research artifacts path (default: `/app/research_data`)

### Optional
- `FINNHUB_API_KEY` — Market signals
- `EARNINGSCALL_API_KEY` — Earnings transcripts
- `TRADING_MODE` — `paper` (default) or `live`
- `PORT` — Server port (default: 8000)
