# Research: Salesforce Sandbox Learning Playground

**Feature**: 019-sfdc-sandbox | **Date**: 2026-03-08

## R1: Seed Data Generation Strategy

**Decision**: Algorithmic generation using Python `random` module with weighted distributions — no external libraries, no API calls.

**Rationale**: The seed generator must produce 50+ realistic client profiles in under 30 seconds. Algorithmic generation with curated name/occupation/goal lists achieves this without network dependencies. The `random` module with seed support ensures reproducibility for testing. Account values follow a log-normal distribution (most clients $50K–$500K, few $1M+), matching a typical advisor's book of business.

**Alternatives considered**:
- **Faker library**: Heavyweight dependency for what amounts to name/address/phone generation. Our curated lists are more domain-appropriate (financial advisor context).
- **Claude API generation**: Too slow (~30s+ for 50 profiles), costs money per run, and introduces API dependency for a setup operation. Reserved for brief/commentary where NLG quality matters.

**Implementation details**:
- First/last name pools (~100 each) for ~10K unique combinations
- Occupation pool (~30) weighted toward professional/executive roles
- Account value: `random.lognormvariate(mu=12.2, sigma=1.0)` clipped to $50K–$5M
- Risk tolerance: weighted random — 15% conservative, 35% moderate, 35% growth, 15% aggressive
- Life stage: age-correlated — accumulation (25–45), pre-retirement (46–60), retirement (61–75), legacy (76+)
- Interaction history: 1–5 past interactions per client, generated with realistic date spacing

## R2: Meeting Brief Architecture

**Decision**: Single Claude API call per brief, with client profile + research signals injected as structured context in the user message.

**Rationale**: Following the existing `analyzer.py` pattern — construct a system prompt defining the advisor assistant role, inject client data + market signals into the user message, parse the structured response. A single API call keeps latency under 15 seconds. Research signals are fetched via the existing `query_signals()` function, filtered by relevance to the client's investment goals.

**Alternatives considered**:
- **Multi-turn conversation**: Unnecessary complexity for a single-shot generation task.
- **Template-based (no LLM)**: Produces generic output without the contextual reasoning that makes briefs useful for practice.
- **Pre-generated briefs stored in DB**: Stale immediately; on-the-fly generation ensures current market context.

**Implementation details**:
- System prompt: "You are a meeting preparation assistant for a financial advisor..."
- User message: JSON-formatted client profile + last 10 research signals matching client's investment focus
- Response format: Markdown with sections (Client Summary, Portfolio Context, Market Conditions, Talking Points)
- Graceful degradation: If no research signals available, brief still generates with client-only context + "market data unavailable" note

## R3: Market Commentary Architecture

**Decision**: Single Claude API call per commentary, with segment definition + research signals as context. Segment derived from client filter criteria (risk tolerance, life stage).

**Rationale**: Same pattern as meeting briefs. The segment definition provides targeting context, research signals provide data points. Commentary is 2–3 paragraphs, suitable for a client newsletter or email update.

**Alternatives considered**:
- **Pre-built templates with fill-in-the-blank**: Too rigid, doesn't capture nuanced market narratives.
- **Multiple API calls (outline → draft → polish)**: Over-engineered for 2–3 paragraph output.

**Implementation details**:
- Segment definition: risk_tolerance and/or life_stage filter → query matching clients → extract common traits
- Research signals: Last 20 signals across all sources, sorted by recency
- System prompt: "You are a market commentary writer for a financial advisor practice..."
- Response: 2–3 paragraphs with specific data point citations

## R4: Data Model & Storage Approach

**Decision**: Client data stored in a **real Salesforce Developer Edition org** (Contact + Task objects) via REST API + SOQL. Six custom fields deployed via Metadata Deploy REST API. Research signals remain in local SQLite (unchanged). No new SQLite migrations.

**Rationale**: The whole point of Track 2 is for Jordan to learn real Salesforce skills — SOQL queries, object relationships, Connected Apps, OAuth flows, custom fields, PermissionSets. A local SQLite database doesn't teach any of that. The Salesforce sandbox provides a real CRM environment with synthetic data, building transferable skills applicable to any CRM integration work.

**Implementation details**:
- **Authentication**: OAuth2 Client Credentials flow (only method that works for Agentforce-provisioned orgs)
- **Custom fields**: 6 fields on Contact (Age__c, Account_Value__c, Risk_Tolerance__c, Life_Stage__c, Investment_Goals__c, Household_Members__c) deployed via Metadata Deploy REST API (Tooling API doesn't work for Agentforce orgs)
- **Field-Level Security**: PermissionSet `Advisor_Agent_Fields` grants Read/Edit on custom fields, auto-assigned to Run As user
- **Interaction history**: Stored as Salesforce Task records (Description=type, Subject=summary — Task.Type field doesn't exist in Agentforce orgs)
- **Duplicate handling**: `Sforce-Duplicate-Rule-Header: allowSave=true` bypasses Standard Contact Duplicate Rule for seed data
- **Hybrid architecture**: Client data → Salesforce, research signals → SQLite, meeting briefs → both, commentary → SQLite only

**Alternatives considered (and rejected)**:
- **Local SQLite for client data**: Original implementation — rejected because it doesn't teach Salesforce skills, which is the core learning objective.
- **Salesforce SOAP API**: Disabled by default in Agentforce orgs.
- **Salesforce Tooling API for field creation**: Creates metadata but fields aren't accessible via REST API in Agentforce orgs.
- **Username-password OAuth flow**: Fails on Agentforce orgs (authentication error).

**Operational documentation**: See `specs/019-sfdc-sandbox/sfdc-setup-guide.md` for complete setup instructions.

## R5: MCP Tool Design

**Decision**: 7 new MCP tools added to `research_server.py`, following the existing `@mcp.tool()` pattern with `_get_readonly_conn()` for read operations.

**Rationale**: Consistent with existing MCP tools. Read-only connection for list/search/view operations. Separate writable connection only for seed/add/edit operations (matching existing pattern where MCP tools that modify data use a standard connection).

**Tools planned**:
1. `sandbox_seed_clients` — Generate synthetic clients (write)
2. `sandbox_list_clients` — List/filter clients (read)
3. `sandbox_search_clients` — Search by name/notes (read)
4. `sandbox_get_client` — View single client profile (read)
5. `sandbox_add_client` — Add new client manually (write)
6. `sandbox_edit_client` — Update client fields (write)
7. `sandbox_meeting_brief` — Generate meeting prep brief (read + Claude API)
8. `sandbox_market_commentary` — Generate market commentary (read + Claude API)
