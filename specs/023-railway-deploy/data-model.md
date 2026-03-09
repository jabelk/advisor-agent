# Data Model: Railway Deployment (023)

This is an infrastructure feature — no new database entities. The data model covers configuration and runtime state only.

## Configuration Entities

### Railway Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCP_API_TOKEN` | Yes | — | Bearer token for MCP endpoint auth |
| `ANTHROPIC_API_KEY` | Yes | — | Claude API access |
| `SFDC_CONSUMER_KEY` | Yes | — | Salesforce Connected App key |
| `SFDC_CONSUMER_SECRET` | Yes | — | Salesforce Connected App secret |
| `SFDC_INSTANCE_URL` | Yes | — | Salesforce sandbox instance URL |
| `SFDC_USERNAME` | Yes | — | Salesforce sandbox username |
| `SFDC_PASSWORD` | Yes | — | Salesforce sandbox password |
| `SFDC_SECURITY_TOKEN` | Yes | — | Salesforce sandbox security token |
| `SFDC_LOGIN_URL` | Yes | `https://test.salesforce.com` | Salesforce login endpoint |
| `ALPACA_PAPER_API_KEY` | Yes | — | Alpaca paper trading API key |
| `ALPACA_PAPER_SECRET_KEY` | Yes | — | Alpaca paper trading secret |
| `EDGAR_IDENTITY` | Yes | — | SEC EDGAR user agent string |
| `DB_PATH` | No | `/app/data/finance_agent.db` | SQLite database file path |
| `RESEARCH_DATA_DIR` | No | `/app/research_data` | Research artifacts directory |
| `PORT` | No | `8000` | Server listen port |
| `FINNHUB_API_KEY` | No | — | Finnhub market signals |
| `EARNINGSCALL_API_KEY` | No | — | Earnings call transcripts |
| `TRADING_MODE` | No | `paper` | Trading mode (paper/live) |

### Health Check Response

```json
{
  "status": "healthy | degraded | unhealthy",
  "uptime_seconds": 3600,
  "integrations": {
    "salesforce": {
      "required": true,
      "configured": true,
      "connected": true,
      "error": null
    },
    "anthropic": {
      "required": true,
      "configured": true,
      "connected": true,
      "error": null
    },
    "alpaca": {
      "required": true,
      "configured": true,
      "connected": true,
      "error": null
    },
    "finnhub": {
      "required": false,
      "configured": true,
      "connected": true,
      "error": null
    }
  },
  "storage": {
    "db_exists": true,
    "db_size_mb": 12.5,
    "research_dir_exists": true
  }
}
```

### Status Rules

- **healthy**: All required integrations configured and connected
- **degraded**: All required integrations OK, but one or more optional integrations down
- **unhealthy**: One or more required integrations missing or failing → HTTP 503

## Persistent Storage

| Mount Path | Contents | Persistence |
|------------|----------|-------------|
| `/app/data` | SQLite database (finance_agent.db) | Railway volume — survives deploys |
| `/app/research_data` | Cached SEC filings, research artifacts | Railway volume — survives deploys |
