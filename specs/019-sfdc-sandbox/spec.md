# Feature Specification: Salesforce Sandbox Learning Playground

**Feature Branch**: `019-sfdc-sandbox`
**Created**: 2026-03-08
**Status**: Draft
**Input**: User description: "Start Track 2 (Advisor Productivity) — Salesforce sandbox learning playground with seed data, client lists, and CRM practice environment to help Jordan learn SFDC better."

## User Scenarios & Testing

### User Story 1 - Seed Data & Client List Management (Priority: P1)

Jordan wants a local CRM practice environment pre-loaded with realistic but entirely synthetic client data so he can learn CRM workflows without needing access to a live Salesforce org. He needs to create, browse, search, and manage a list of fictional client profiles — each with a name, contact info, account value, risk tolerance, life stage, and notes. This gives him a sandbox to practice the kind of client segmentation, list-building, and data lookup skills that are fundamental to any CRM platform (Salesforce, Schwab Advisor Center, or otherwise).

**Why this priority**: Without seed data, there's nothing to practice on. A populated client list is the foundation for every other advisor productivity feature (meeting prep, market commentary targeting, portfolio review prep). This is the essential first building block of Track 2.

**Independent Test**: Run the seed command to populate 50 synthetic clients, then list, search, filter, and view individual client profiles to confirm the data is realistic and browseable.

**Acceptance Scenarios**:

1. **Given** the sandbox is empty, **When** Jordan runs the seed command, **Then** 50 synthetic client profiles are generated with realistic names, ages, occupations, account values ($50K-$5M range), risk tolerances, investment goals, and contact information.
2. **Given** seed data exists, **When** Jordan lists clients, **Then** he sees a summary table showing name, account value, risk tolerance, and last interaction date, sorted by account value descending.
3. **Given** seed data exists, **When** Jordan searches for clients by name, account value range, risk tolerance, or life stage, **Then** matching clients are returned with relevant details.
4. **Given** seed data exists, **When** Jordan views a single client profile, **Then** he sees all fields: name, age, occupation, email, phone, account value, risk tolerance, investment goals, life stage, household members, notes, and interaction history.
5. **Given** seed data exists, **When** Jordan adds a new client manually, **Then** the client appears in the list with all required fields populated.
6. **Given** a client exists, **When** Jordan edits client fields (e.g., updates account value or risk tolerance), **Then** the changes persist and appear on the next view.

---

### User Story 2 - Meeting Prep Briefs (Priority: P2)

Jordan wants to generate a meeting preparation brief for a specific client by combining their profile data with relevant public market information. Before a client meeting, he asks the system to prepare a brief that includes the client's profile summary, their investment goals and risk tolerance, relevant market conditions for their portfolio focus areas, and suggested talking points. This helps Jordan practice the meeting prep workflow that financial advisors do daily — pulling client context together with market data into a coherent narrative.

**Why this priority**: Meeting prep is the single highest-frequency task advisors perform and the most time-consuming. Practicing this workflow with synthetic data builds the muscle memory and templates Jordan needs for real client work. It depends on US1 (client data) being in place.

**Independent Test**: With seed data loaded, generate a meeting prep brief for a client and verify it includes client profile, market context for their investment focus areas, and actionable talking points.

**Acceptance Scenarios**:

1. **Given** a client profile exists with investment goals, **When** Jordan requests a meeting prep brief for that client, **Then** the system produces a structured brief with: client summary, portfolio context, relevant market conditions, and 3-5 suggested talking points.
2. **Given** a client has a "growth" investment goal, **When** a meeting brief is generated, **Then** the talking points reference current growth sector performance and relevant market signals from the research pipeline.
3. **Given** a client has "conservative" risk tolerance, **When** a meeting brief is generated, **Then** the talking points emphasize capital preservation, fixed income conditions, and downside protection strategies.
4. **Given** no market data is available (research pipeline hasn't run), **When** Jordan requests a meeting brief, **Then** the system still produces the client profile portion with a note that market data is unavailable.

---

### User Story 3 - Market Commentary Generator (Priority: P3)

Jordan wants to generate short market commentary paragraphs tailored to different client segments — for example, a commentary for "high-net-worth growth-oriented clients" vs. "pre-retirees focused on income." This helps him practice writing the kind of personalized market updates that advisors send to client groups. The commentary draws on public market data from the existing research pipeline and is customized based on the audience segment's typical concerns and interests.

**Why this priority**: Market commentary is a weekly/monthly advisor task that demonstrates thought leadership and keeps clients engaged. It builds on both the client data (for segmentation) and the meeting prep (for market context), making it a natural extension. It's lower priority because it's less frequent than meeting prep.

**Independent Test**: Generate market commentary for a specific client segment and verify it references current market conditions and is tailored to that segment's investment profile.

**Acceptance Scenarios**:

1. **Given** clients exist across multiple risk tolerances, **When** Jordan requests commentary for "growth-oriented" clients, **Then** the system produces a 2-3 paragraph market update focusing on equity markets, sector performance, and growth opportunities.
2. **Given** clients exist across multiple risk tolerances, **When** Jordan requests commentary for "income-focused" clients, **Then** the commentary focuses on bond markets, dividend stocks, interest rate environment, and income strategies.
3. **Given** the research pipeline has recent signals, **When** commentary is generated, **Then** it incorporates specific data points (e.g., "The S&P 500 is up 12% YTD" or "Fed held rates steady this week").
4. **Given** no specific segment is requested, **When** Jordan generates commentary, **Then** a general market overview is produced suitable for all client types.

---

### Edge Cases

- What happens when Jordan runs seed again after data already exists? The system asks whether to add more clients, reset all data, or cancel — it does not silently overwrite existing data.
- What happens when Jordan requests a meeting brief for a client that doesn't exist? The system returns an error with the client ID and suggests listing available clients.
- What happens when a client has no investment goals specified? The meeting brief omits the tailored talking points section and suggests completing the client profile first.
- What happens when the research pipeline has no recent data? Meeting briefs and commentary include a "Market data unavailable — run research pipeline first" notice rather than failing silently.
- What happens when Jordan searches for clients with no matching results? The system shows "No clients match your criteria" with the search filters applied, and suggests broadening the search.
- What happens when the seed data generator produces duplicate names? Names are generated with sufficient variety (first + last name combinations) to avoid duplicates in a 50-client set, but the system does not enforce name uniqueness — clients are identified by ID.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a command to generate and populate synthetic client profiles with realistic financial advisor data fields.
- **FR-002**: System MUST store client profiles in a Salesforce Developer Edition org (Contact + Task objects) with fields including: name, age, occupation, email, phone, account value, risk tolerance (conservative/moderate/growth/aggressive), investment goals, life stage (accumulation/pre-retirement/retirement/legacy), household members, notes, and interaction history.
- **FR-003**: System MUST provide commands to list, search, filter, view, add, and edit client profiles.
- **FR-004**: System MUST support filtering clients by risk tolerance, life stage, account value range, and free-text search across name and notes.
- **FR-005**: System MUST provide a command to generate a meeting preparation brief for a specific client, combining client profile data with available public market information.
- **FR-006**: Meeting briefs MUST include: client summary, investment context, relevant market conditions, and suggested talking points appropriate to the client's risk tolerance and goals.
- **FR-007**: System MUST provide a command to generate market commentary tailored to a specified client segment (by risk tolerance or life stage).
- **FR-008**: Market commentary MUST incorporate data from the existing research pipeline when available.
- **FR-009**: All client data MUST be clearly marked as synthetic/practice data (e.g., @example.com emails) and MUST NEVER connect to or import from any production CRM system. The Salesforce org is a dedicated developer sandbox for learning only.
- **FR-010**: System MUST provide these capabilities via both CLI and as tools in Claude Desktop (MCP).
- **FR-011**: The seed data generator MUST produce a configurable number of clients (default: 50) with realistic distributions of account values, risk tolerances, and life stages.

### Key Entities

- **Client Profile**: A synthetic client record representing a fictional advisory client, with demographics, financial situation, investment preferences, and interaction history. Identified by a unique ID.
- **Meeting Brief**: A generated document combining a specific client's profile with market context and talking points, designed for pre-meeting review.
- **Market Commentary**: A generated text piece tailored to a client segment, incorporating public market data and framed for the segment's typical concerns.
- **Client Segment**: A grouping of clients based on shared attributes (risk tolerance, life stage, account value tier) used for targeting commentary and analysis.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Jordan can populate a practice CRM with 50 realistic synthetic clients in under 30 seconds via a single command.
- **SC-002**: Jordan can find any client by name, risk tolerance, or account value range in under 5 seconds.
- **SC-003**: A meeting preparation brief for any client is generated in under 15 seconds and includes at least 3 relevant talking points.
- **SC-004**: Market commentary for a client segment is generated in under 15 seconds and references at least 2 specific market data points when research data is available.
- **SC-005**: All synthetic data is clearly distinguishable from real data — no real client names, account numbers, or PII are used anywhere in the system.

## Assumptions

- Client data is synthetic, generated locally, and **pushed to a real Salesforce Developer Edition org** via the Salesforce REST API. This is a learning sandbox — Jordan practices real CRM workflows (SOQL queries, object relationships, Connected Apps, OAuth flows) against a live Salesforce instance with synthetic data only.
- **No connection to Schwab systems or any production CRM.** The Salesforce org is a dedicated developer sandbox provisioned for experimentation.
- The Salesforce org uses the **Client Credentials OAuth2 flow** for authentication (the only working method for Agentforce-provisioned orgs). See `specs/019-sfdc-sandbox/sfdc-setup-guide.md` for full setup details.
- **Hybrid architecture**: Client profiles and interactions → Salesforce (Contact + Task objects); research signals → local SQLite (unchanged); meeting briefs → Salesforce client data + SQLite signals; commentary → SQLite signals only.
- The synthetic data generator uses randomized but realistic-looking names, occupations, and financial figures. No real person's identity is replicated intentionally. Data is pushed to Salesforce as Contact records.
- Meeting briefs and market commentary use Claude (via Anthropic API) for natural language generation, drawing on client profile data (from Salesforce) and public market signals (from local SQLite research pipeline).
- The "learning playground" concept means this is a safe environment for Jordan to practice CRM workflows. There is no expectation of data accuracy or compliance — it's explicitly a training tool.
- Risk tolerance categories follow a standard advisor framework: conservative, moderate, growth, aggressive.
- Life stage categories follow standard financial planning stages: accumulation (early career), pre-retirement (10-15 years from retirement), retirement, legacy (estate planning focus).
- The seed data distribution roughly mirrors a typical financial advisor's book of business: skewed toward moderate/growth risk tolerance, with account values following a log-normal distribution.
- Six custom fields on the Contact object (Age__c, Account_Value__c, Risk_Tolerance__c, Life_Stage__c, Investment_Goals__c, Household_Members__c) are deployed via the Metadata Deploy REST API, with a PermissionSet granting field-level security access.
