# Data Model: Salesforce Sandbox Learning Playground

**Feature**: 019-sfdc-sandbox | **Date**: 2026-03-08

## Entities

### SandboxClient (persisted — `sandbox_client` table)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | INTEGER | PK, AUTOINCREMENT | Unique client identifier |
| first_name | TEXT | NOT NULL | Generated or manual |
| last_name | TEXT | NOT NULL | Generated or manual |
| age | INTEGER | NOT NULL, CHECK(age >= 18 AND age <= 100) | |
| occupation | TEXT | NOT NULL | |
| email | TEXT | NOT NULL | Synthetic — `first.last@example.com` |
| phone | TEXT | NOT NULL | Synthetic — `555-XXX-XXXX` |
| account_value | REAL | NOT NULL, CHECK(account_value >= 0) | USD, range $50K–$5M for seed data |
| risk_tolerance | TEXT | NOT NULL, CHECK(IN conservative,moderate,growth,aggressive) | |
| investment_goals | TEXT | | Comma-separated or free text |
| life_stage | TEXT | NOT NULL, CHECK(IN accumulation,pre-retirement,retirement,legacy) | Age-correlated |
| household_members | TEXT | | JSON array of names/relationships |
| notes | TEXT | | Free-text advisor notes |
| created_at | TEXT | NOT NULL, DEFAULT CURRENT_TIMESTAMP | ISO 8601 |
| updated_at | TEXT | NOT NULL, DEFAULT CURRENT_TIMESTAMP | ISO 8601 |

### SandboxInteraction (persisted — `sandbox_interaction` table)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | INTEGER | PK, AUTOINCREMENT | |
| client_id | INTEGER | NOT NULL, FK → sandbox_client(id) ON DELETE CASCADE | |
| interaction_date | TEXT | NOT NULL | ISO 8601 date |
| interaction_type | TEXT | NOT NULL, CHECK(IN call,meeting,email,review) | |
| summary | TEXT | NOT NULL | Brief description of interaction |
| created_at | TEXT | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |

### MeetingBrief (in-memory only — not persisted)

Generated on-the-fly by Claude API. Returned as a dict:

| Field | Type | Notes |
|-------|------|-------|
| client_id | int | Reference to sandbox_client |
| client_name | str | Full name for display |
| generated_at | str | ISO 8601 timestamp |
| client_summary | str | Profile overview paragraph |
| portfolio_context | str | Investment goals, risk tolerance, life stage context |
| market_conditions | str | Relevant market data from research signals |
| talking_points | list[str] | 3–5 suggested talking points |
| market_data_available | bool | Whether research signals were found |

### MarketCommentary (in-memory only — not persisted)

Generated on-the-fly by Claude API. Returned as a dict:

| Field | Type | Notes |
|-------|------|-------|
| segment | str | Description of target segment |
| segment_criteria | dict | Filters used (risk_tolerance, life_stage) |
| generated_at | str | ISO 8601 timestamp |
| commentary | str | 2–3 paragraph market update |
| data_points_cited | int | Number of research signals referenced |
| market_data_available | bool | Whether research signals were found |

## Relationships

```
sandbox_client (1) ──── (N) sandbox_interaction
    │
    │  (queried at brief generation time)
    ▼
MeetingBrief (in-memory, references client + research_signal)

sandbox_client (filtered by segment criteria)
    │
    │  (queried at commentary generation time)
    ▼
MarketCommentary (in-memory, references segment + research_signal)
```

## State Transitions

**SandboxClient**: No formal state machine. Clients are created (via seed or manual add), updated (edit fields), and can be implicitly "active" (have recent interactions) or "dormant" (no recent interactions). No delete operation in v1 — seed reset drops and recreates all data.

**Seed Operation States**:
- Empty DB → `seed` → 50 clients + interactions created
- Populated DB → `seed` → Prompt: add more / reset / cancel
  - "add" → Append N new clients
  - "reset" → DROP + recreate all sandbox data
  - "cancel" → No change

## Migration: 011_sandbox_crm.sql

```sql
CREATE TABLE IF NOT EXISTS sandbox_client (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK(age >= 18 AND age <= 100),
    occupation TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    account_value REAL NOT NULL CHECK(account_value >= 0),
    risk_tolerance TEXT NOT NULL CHECK(risk_tolerance IN ('conservative', 'moderate', 'growth', 'aggressive')),
    investment_goals TEXT,
    life_stage TEXT NOT NULL CHECK(life_stage IN ('accumulation', 'pre-retirement', 'retirement', 'legacy')),
    household_members TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS sandbox_interaction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES sandbox_client(id) ON DELETE CASCADE,
    interaction_date TEXT NOT NULL,
    interaction_type TEXT NOT NULL CHECK(interaction_type IN ('call', 'meeting', 'email', 'review')),
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_sandbox_client_risk ON sandbox_client(risk_tolerance);
CREATE INDEX IF NOT EXISTS idx_sandbox_client_life_stage ON sandbox_client(life_stage);
CREATE INDEX IF NOT EXISTS idx_sandbox_client_account_value ON sandbox_client(account_value);
CREATE INDEX IF NOT EXISTS idx_sandbox_interaction_client ON sandbox_interaction(client_id);
```
