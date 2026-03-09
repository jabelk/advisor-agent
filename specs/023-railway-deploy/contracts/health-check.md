# Contract: Health Check Endpoint

## `GET /health`

Health check endpoint for Railway's restart policy and monitoring.

### Request

No parameters. No authentication required (health checks come from Railway infrastructure).

### Response

**200 OK** — Server is healthy or degraded (optional integrations down)

```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "integrations": {
    "salesforce": {"required": true, "configured": true, "connected": true, "error": null},
    "anthropic": {"required": true, "configured": true, "connected": true, "error": null},
    "alpaca": {"required": true, "configured": true, "connected": true, "error": null},
    "finnhub": {"required": false, "configured": false, "connected": false, "error": null}
  },
  "storage": {
    "db_exists": true,
    "db_size_mb": 12.5,
    "research_dir_exists": true
  }
}
```

**503 Service Unavailable** — Required integration missing or failing

```json
{
  "status": "unhealthy",
  "uptime_seconds": 5,
  "integrations": {
    "salesforce": {"required": true, "configured": false, "connected": false, "error": "SFDC_CONSUMER_KEY not set"},
    "anthropic": {"required": true, "configured": true, "connected": true, "error": null},
    "alpaca": {"required": true, "configured": true, "connected": true, "error": null}
  },
  "storage": {
    "db_exists": true,
    "db_size_mb": 0.0,
    "research_dir_exists": true
  }
}
```

### Status Rules

| Status | Condition | HTTP Code |
|--------|-----------|-----------|
| healthy | All required integrations configured + connected | 200 |
| degraded | Required OK, optional integration(s) down | 200 |
| unhealthy | Any required integration missing or failing | 503 |

### Required Integrations

- **salesforce**: Check `SFDC_CONSUMER_KEY` env var is set
- **anthropic**: Check `ANTHROPIC_API_KEY` env var is set
- **alpaca**: Check `ALPACA_PAPER_API_KEY` env var is set

### Optional Integrations

- **finnhub**: Check `FINNHUB_API_KEY` env var is set
- **earningscall**: Check `EARNINGSCALL_API_KEY` env var is set

### Notes

- Health check does NOT live-test Salesforce/Alpaca connections (too slow for Railway's 60s timeout on cold start). It checks env var presence only.
- Storage checks verify file/directory existence, not write capability.
- The `/health` endpoint is separate from the MCP `/mcp` endpoint and does NOT require Bearer token auth.
