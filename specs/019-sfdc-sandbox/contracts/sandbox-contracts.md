# Contracts: Salesforce Sandbox Learning Playground

**Feature**: 019-sfdc-sandbox | **Date**: 2026-03-08

## Internal Functions (sandbox/ module)

### storage.py — Client CRUD

```python
def add_client(conn: sqlite3.Connection, client: dict) -> int:
    """Insert a new client profile. Returns client ID."""
    # Required fields: first_name, last_name, age, occupation, email, phone,
    #                  account_value, risk_tolerance, life_stage
    # Optional fields: investment_goals, household_members, notes
    # Returns: int (new client ID)

def get_client(conn: sqlite3.Connection, client_id: int) -> dict | None:
    """Fetch a single client by ID, including interaction history."""
    # Returns: dict with all client fields + "interactions" list, or None

def list_clients(
    conn: sqlite3.Connection,
    risk_tolerance: str | None = None,
    life_stage: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List clients with optional filters. Returns summary dicts."""
    # Returns: list of dicts with id, first_name, last_name, account_value,
    #          risk_tolerance, life_stage, last_interaction_date

def update_client(conn: sqlite3.Connection, client_id: int, updates: dict) -> bool:
    """Update client fields. Returns True if client existed."""
    # Allowed update fields: any column except id, created_at
    # Sets updated_at to current timestamp

def add_interaction(conn: sqlite3.Connection, client_id: int, interaction: dict) -> int:
    """Add an interaction record to a client. Returns interaction ID."""
    # Required: interaction_date, interaction_type, summary

def client_count(conn: sqlite3.Connection) -> int:
    """Return total number of sandbox clients."""
```

### seed.py — Synthetic Data Generator

```python
def seed_clients(
    conn: sqlite3.Connection,
    count: int = 50,
    seed: int | None = None,
) -> int:
    """Generate and insert synthetic client profiles with interactions.
    Returns number of clients created."""
    # Each client gets 1-5 randomly generated interactions
    # Account values follow log-normal distribution ($50K-$5M)
    # Risk tolerance weighted: 15% conservative, 35% moderate, 35% growth, 15% aggressive
    # Life stage correlated with age

def reset_sandbox(conn: sqlite3.Connection) -> None:
    """Delete all sandbox_client and sandbox_interaction records."""
```

### meeting_prep.py — Meeting Brief Generation

```python
async def generate_meeting_brief(
    conn: sqlite3.Connection,
    client_id: int,
    anthropic_client: anthropic.Anthropic | None = None,
) -> dict:
    """Generate a meeting preparation brief for a client.
    Returns MeetingBrief dict (see data-model.md).
    Raises ValueError if client_id not found."""
    # 1. Fetch client profile via get_client()
    # 2. Query research signals relevant to client's investment_goals
    # 3. Call Claude API with client context + signals
    # 4. Parse response into structured brief dict
```

### commentary.py — Market Commentary Generation

```python
async def generate_commentary(
    conn: sqlite3.Connection,
    risk_tolerance: str | None = None,
    life_stage: str | None = None,
    anthropic_client: anthropic.Anthropic | None = None,
) -> dict:
    """Generate market commentary targeted at a client segment.
    Returns MarketCommentary dict (see data-model.md).
    If no segment specified, generates general market overview."""
    # 1. Define segment from filters
    # 2. Query recent research signals (last 20)
    # 3. Call Claude API with segment context + signals
    # 4. Parse response into structured commentary dict
```

## CLI Contracts

### Subcommand Group: `sandbox`

```
advisor-agent sandbox seed [--count N] [--reset]
    # Populate sandbox with synthetic clients
    # --count: Number of clients (default: 50)
    # --reset: Drop existing data first (skips prompt)
    # Output: "Created N synthetic client profiles with interactions."

advisor-agent sandbox list [--risk TOLERANCE] [--stage STAGE] [--min-value N] [--max-value N] [--search TEXT]
    # List clients with optional filters
    # Output: Formatted table (Name | Account Value | Risk | Life Stage | Last Contact)

advisor-agent sandbox view CLIENT_ID
    # View full client profile + interaction history
    # Output: Formatted profile with all fields

advisor-agent sandbox add --first NAME --last NAME --age N --occupation TEXT --account-value N --risk TOLERANCE --life-stage STAGE [--goals TEXT] [--notes TEXT]
    # Add a new client manually
    # Output: "Client #ID created: First Last"

advisor-agent sandbox edit CLIENT_ID [--account-value N] [--risk TOLERANCE] [--life-stage STAGE] [--goals TEXT] [--notes TEXT]
    # Edit client fields
    # Output: "Client #ID updated."

advisor-agent sandbox brief CLIENT_ID
    # Generate meeting prep brief
    # Output: Formatted meeting brief (markdown)

advisor-agent sandbox commentary [--risk TOLERANCE] [--stage STAGE]
    # Generate market commentary for segment
    # Output: Formatted commentary (markdown)
```

## MCP Tool Contracts

All tools added to `research_server.py` following existing `@mcp.tool()` pattern.

### Read-Only Tools (use `_get_readonly_conn()`)

```python
@mcp.tool()
def sandbox_list_clients(
    risk_tolerance: str = "",
    life_stage: str = "",
    min_value: float = 0,
    max_value: float = 0,
    search: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    """List sandbox clients with optional filters."""
    # Returns: {"clients": [...], "total": N, "filters_applied": {...}}

@mcp.tool()
def sandbox_get_client(client_id: int) -> dict[str, Any]:
    """View a single sandbox client profile with interaction history."""
    # Returns: full client dict or {"error": "Client not found"}

@mcp.tool()
def sandbox_search_clients(query: str, limit: int = 20) -> dict[str, Any]:
    """Search sandbox clients by name or notes."""
    # Returns: {"clients": [...], "total": N, "query": query}
```

### Write Tools (use standard connection)

```python
@mcp.tool()
def sandbox_seed_clients(count: int = 50, reset: bool = False) -> dict[str, Any]:
    """Generate synthetic client profiles for the CRM sandbox."""
    # Returns: {"created": N, "total": M, "reset": bool}

@mcp.tool()
def sandbox_add_client(
    first_name: str, last_name: str, age: int, occupation: str,
    account_value: float, risk_tolerance: str, life_stage: str,
    investment_goals: str = "", notes: str = "",
) -> dict[str, Any]:
    """Add a new client to the sandbox."""
    # Returns: {"client_id": N, "name": "First Last"}

@mcp.tool()
def sandbox_edit_client(client_id: int, **kwargs) -> dict[str, Any]:
    """Update fields on an existing sandbox client."""
    # Returns: {"client_id": N, "updated_fields": [...]}
```

### Generation Tools (read + Claude API)

```python
@mcp.tool()
def sandbox_meeting_brief(client_id: int) -> dict[str, Any]:
    """Generate a meeting preparation brief for a sandbox client."""
    # Returns: MeetingBrief dict (see data-model.md)

@mcp.tool()
def sandbox_market_commentary(
    risk_tolerance: str = "", life_stage: str = "",
) -> dict[str, Any]:
    """Generate market commentary for a client segment."""
    # Returns: MarketCommentary dict (see data-model.md)
```
