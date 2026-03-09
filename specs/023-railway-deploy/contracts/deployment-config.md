# Contract: Deployment Configuration

## railway.toml

```toml
[build]
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 60
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

## Dockerfile CMD

```dockerfile
CMD ["python", "-m", "finance_agent.mcp.research_server", "--http"]
```

## Claude Desktop Configuration

### Option 1: mcp-remote bridge (works on all plans)

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

### Option 2: Custom Connectors UI (Pro/Max/Team/Enterprise)

1. Claude Desktop > Settings > Connectors > Add custom connector
2. Enter URL: `https://<app-name>.railway.app/mcp`
3. Configure OAuth/Bearer token authentication

## GitHub Actions Secrets

| Secret | Description |
|--------|-------------|
| `RAILWAY_TOKEN` | Railway API token for CLI deployment |

## Railway Dashboard Configuration (Manual)

### Volumes

| Mount Path | Size | Purpose |
|------------|------|---------|
| `/app/data` | 1 GB | SQLite database |
| `/app/research_data` | 1 GB | Research artifacts |

### Environment Variables

Set via Railway dashboard (see data-model.md for full list).
