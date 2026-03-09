# Quickstart: Railway Deployment (023)

## Prerequisites

- Railway account (https://railway.com)
- Railway CLI installed (`npm i -g @railway/cli`)
- GitHub repo with Actions enabled
- Node.js/npm installed locally (for `mcp-remote`)

## Deployment Walkthrough

### Step 1: Create Railway Project

```bash
railway login
railway init   # Create new project "advisor-agent"
```

### Step 2: Configure Environment Variables

In Railway dashboard (Settings > Variables), set all required env vars:

```
MCP_API_TOKEN=<generate-strong-random-token>
ANTHROPIC_API_KEY=sk-ant-...
SFDC_CONSUMER_KEY=...
SFDC_CONSUMER_SECRET=...
SFDC_INSTANCE_URL=https://...-dev-ed.my.salesforce.com
SFDC_USERNAME=...
SFDC_PASSWORD=...
SFDC_SECURITY_TOKEN=...
SFDC_LOGIN_URL=https://test.salesforce.com
ALPACA_PAPER_API_KEY=...
ALPACA_PAPER_SECRET_KEY=...
EDGAR_IDENTITY=Name email@example.com
DB_PATH=/app/data/finance_agent.db
RESEARCH_DATA_DIR=/app/research_data
PORT=8000
TRADING_MODE=paper
```

### Step 3: Attach Persistent Volumes

In Railway dashboard (Service > Settings > Volumes):
1. Add volume: mount path `/app/data`, size 1 GB
2. Add volume: mount path `/app/research_data`, size 1 GB

### Step 4: Deploy

```bash
railway up --detach
```

Wait for deployment to complete. Check health:

```bash
curl https://<app-name>.railway.app/health
```

Expected: `{"status": "healthy", ...}`

### Step 5: Configure Claude Desktop

Update `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "advisor-agent": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://<app-name>.railway.app/mcp",
        "--header",
        "Authorization: Bearer <MCP_API_TOKEN>"
      ]
    }
  }
}
```

Restart Claude Desktop.

### Step 6: Verify

In Claude Desktop, invoke any MCP tool:
- "Show my Salesforce tasks" → should trigger `sandbox_show_tasks`
- "Get signals for AAPL" → should trigger `get_signals`

## Validation Scenarios

### Scenario 1: Basic MCP Tool Invocation
1. Open Claude Desktop
2. Ask: "What are my open Salesforce tasks?"
3. Verify `sandbox_show_tasks` tool is called and returns results

### Scenario 2: Health Check
```bash
curl https://<app-name>.railway.app/health | python3 -m json.tool
```
Verify all required integrations show `"configured": true`.

### Scenario 3: Data Persistence
1. Create a task via Claude Desktop: "Create a Salesforce task for Grey: Test persistence"
2. Redeploy: `railway up --detach`
3. Query tasks: "Show my Salesforce tasks"
4. Verify the "Test persistence" task still appears

### Scenario 4: Auth Rejection
```bash
curl -X POST https://<app-name>.railway.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```
Verify: Request rejected (401/403) without valid Bearer token.

### Scenario 5: CI/CD Pipeline
1. Push a minor change to main branch
2. Verify GitHub Actions runs: lint → test → deploy
3. After deploy completes, verify health check passes

## Troubleshooting

### MCP tools not appearing in Claude Desktop
- Ensure `npx mcp-remote` is working: `npx mcp-remote --help`
- Check the Railway URL is correct and accessible
- Verify the Bearer token matches `MCP_API_TOKEN` on Railway

### Health check returns unhealthy
- Check Railway dashboard > Deployments > Logs for startup errors
- Verify all required env vars are set in Railway dashboard
- Ensure volumes are mounted correctly

### Database empty after deploy
- Verify Railway volumes are attached at `/app/data` and `/app/research_data`
- Check that `DB_PATH` env var points to the volume mount path
