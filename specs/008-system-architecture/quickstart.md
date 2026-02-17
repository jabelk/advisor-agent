# Quickstart: System Architecture Setup

**Feature**: 008-system-architecture | **Date**: 2026-02-17

This guide describes how to set up the target architecture. Each section maps to an implementation phase from the plan.

---

## Phase 1: MCP Integration

### Prerequisites
- Claude Desktop installed on workstation
- Intel NUC running with existing finance-agent codebase
- Alpaca paper trading API keys
- Node.js 18+ (for mcp-remote proxy)

### Step 1: Install MCP Servers

```bash
# Alpaca MCP Server (official)
uvx alpaca-mcp-server init

# SEC EDGAR MCP Server
pip install sec-edgar-mcp
# or via Docker: docker pull mcp/sec-edgar

# FastMCP for custom research server
pip install fastmcp
```

### Step 2: Create Custom Research MCP Server

Create `src/finance_agent/mcp/research_server.py`:
- Expose ~6 tools: `list_companies`, `get_signals`, `search_documents`, `get_watchlist`, `run_query`, `get_safety_state`
- Use FastMCP framework with `@mcp.tool` decorators
- Connect to existing SQLite database

### Step 3: Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "alpaca": {
      "type": "stdio",
      "command": "uvx",
      "args": ["alpaca-mcp-server", "serve"],
      "env": {
        "ALPACA_API_KEY": "<paper-key>",
        "ALPACA_SECRET_KEY": "<paper-secret>"
      }
    },
    "sec-edgar": {
      "command": "uvx",
      "args": ["sec-edgar-mcp"],
      "env": {
        "SEC_EDGAR_USER_AGENT": "Your Name your@email.com"
      }
    },
    "finance-research": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://<nuc-ip>:8000/mcp"
      ]
    }
  }
}
```

### Step 4: Start Research MCP Server on NUC

```bash
# On the Intel NUC
cd /path/to/finance-agent
fastmcp run src/finance_agent/mcp/research_server.py --transport http --host 0.0.0.0 --port 8000
```

### Step 5: Verify

1. Restart Claude Desktop
2. Check MCP server icons appear in the chat interface
3. Ask Claude: "What companies are on my watchlist?"
4. Ask Claude: "Show me the latest signals for AAPL"
5. Ask Claude: "What is the current safety state?"

---

## Phase 2: Data Source Expansion

### FRED Macro Data

```bash
pip install fredapi
```

Get a free API key at https://fredaccount.stlouisfed.org/apikeys

Add to `.env`:
```
FRED_API_KEY=your_key_here
```

### Tiingo News

Get a free API key at https://api.tiingo.com/

Add to `.env`:
```
TIINGO_API_KEY=your_key_here
```

### SEC RSS Monitoring

No additional setup — uses existing `feedparser` dependency. SEC EDGAR RSS feeds are publicly accessible at https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<ticker>&type=&dateb=&owner=include&count=40&search_text=&action=getcompany&output=atom

### Verify Data Sources

```bash
# Run research pipeline with all sources
uv run finance-agent research run --ticker AAPL

# Check that new data types appear
uv run finance-agent research status
```

---

## Phase 3: Agent Framework

### Install Agent Dependencies

```bash
pip install claude-agent-sdk nats-py
```

### systemd Timer Setup (on NUC)

Create timer files in `/etc/systemd/system/`:

```ini
# finance-monitor.timer
[Unit]
Description=Finance Agent Monitor (every 15 min)

[Timer]
OnCalendar=*:0/15
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# finance-monitor.service
[Unit]
Description=Finance Agent Monitor

[Service]
Type=oneshot
ExecStart=/path/to/uv run finance-agent monitor run
WorkingDirectory=/path/to/finance-agent
EnvironmentFile=/path/to/finance-agent/.env
```

Enable timers:
```bash
sudo systemctl enable --now finance-monitor.timer
sudo systemctl enable --now finance-scanner.timer
sudo systemctl enable --now finance-briefing.timer
```

### ntfy.sh Setup

```bash
# Self-hosted ntfy on NUC (Docker)
docker run -d \
  --name ntfy \
  --restart unless-stopped \
  -p 8080:80 \
  -v /var/cache/ntfy:/var/cache/ntfy \
  binwiederhier/ntfy serve

# Install ntfy app on phone, subscribe to your topic
# Test notification
curl -d "Test from finance agent" http://localhost:8080/finance-alerts
```

### Verify Agents

```bash
# Check timer status
systemctl list-timers --all | grep finance

# Run monitor manually
uv run finance-agent monitor run --verbose

# Check audit log for agent activity
uv run finance-agent audit show --last 10
```

---

## Phase 4: Paid Sources & Optimization

### Quiver Quantitative ($25/mo)

```bash
pip install quiver-python
```

Sign up at https://www.quiverquant.com/ and add to `.env`:
```
QUIVER_API_KEY=your_key_here
```

### Prompt Caching

Enable in anthropic SDK calls:
```python
# System prompt and filing text cached across analysis passes
# 90% savings on cached input tokens
# Break-even after 2 cache hits
```

### Cost Monitoring

```bash
# Check API usage
uv run finance-agent costs show --period month

# Expected: ~$50-100/month total
```
