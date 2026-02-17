# Feature Specification: MCP Integration

**Feature Branch**: `010-mcp-integration`
**Created**: 2026-02-17
**Status**: Draft
**Input**: User description: "MCP integration feature"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Query Research Signals from Claude Desktop (Priority: P1)

As a trader using Claude Desktop, I want to ask conversational questions about my research data (signals, documents, watchlist) and get answers grounded in my local database, so I can make informed decisions without leaving the chat interface.

**Why this priority**: This is the core value proposition — making the existing research database *accessible* through natural conversation. Without this, all the data ingested in features 002-009 requires running CLI commands and reading terminal output.

**Independent Test**: Open Claude Desktop, ask "What are the latest signals for AAPL?", and receive a response citing actual data from the local research database.

**Acceptance Scenarios**:

1. **Given** the research database contains signals for AAPL, **When** the user asks Claude Desktop "What are the latest research signals for AAPL?", **Then** Claude returns a summary of recent signals with timestamps, signal types, confidence levels, and source document references.
2. **Given** the research database contains ingested documents, **When** the user asks "Show me all 10-K filings ingested this month", **Then** Claude returns a list of matching documents with titles, dates, and companies.
3. **Given** the watchlist has 5 active companies, **When** the user asks "What companies am I tracking?", **Then** Claude returns the full watchlist with tickers, names, and sectors.
4. **Given** no signals exist for a ticker, **When** the user asks about that ticker, **Then** Claude reports that no research data is available and suggests running the research pipeline.

---

### User Story 2 - Check Safety State Before Trading (Priority: P1)

As a trader, I want Claude Desktop to check my safety guardrails (kill switch status, risk limits, daily trade count) before I place any trade, so I am protected from exceeding my risk parameters even when trading conversationally.

**Why this priority**: Safety First is a non-negotiable constitutional principle. The MCP server must expose safety state so Claude can enforce guardrails during conversational trading sessions.

**Independent Test**: Ask Claude Desktop to check safety status and receive kill switch state, current risk limits, and any active warnings.

**Acceptance Scenarios**:

1. **Given** the kill switch is inactive and risk limits are within bounds, **When** the user asks "Can I trade right now?", **Then** Claude reports all safety checks pass with current limit values.
2. **Given** the kill switch is active, **When** the user asks to place a trade, **Then** Claude refuses and reports the kill switch is active with the timestamp and reason it was toggled.
3. **Given** the risk settings include a daily trade limit, **When** the user asks to place a trade, **Then** Claude checks the configured limit (from the research MCP server) and the current trade count (from the Alpaca MCP server) to warn if the limit would be exceeded.

---

### User Story 3 - Configure Claude Desktop with All MCP Servers (Priority: P2)

As a trader setting up my workstation, I want a documented configuration that connects Claude Desktop to three MCP servers (research database, Alpaca trading, SEC EDGAR filings), so I can access all my tools from a single conversation.

**Why this priority**: Configuration is a one-time setup step that enables all other user stories. It's P2 because the custom research server (US1) must exist first.

**Independent Test**: Follow the setup documentation to configure Claude Desktop with all three MCP servers, then verify each server's tools are available in a new conversation.

**Acceptance Scenarios**:

1. **Given** a fresh Claude Desktop installation, **When** the user follows the setup guide and configures the research database MCP server, **Then** research query tools appear in the Claude Desktop tool list.
2. **Given** the configuration includes the Alpaca MCP server, **When** the user starts a conversation, **Then** trading tools (place order, get positions, get account info) are available.
3. **Given** the configuration includes the SEC EDGAR MCP server, **When** the user asks about a company's filings, **Then** Claude can fetch filing data directly from SEC EDGAR.
4. **Given** the research MCP server is unreachable (NUC offline), **When** the user starts Claude Desktop, **Then** the other two MCP servers still function normally and an appropriate error is shown for the unavailable server.

---

### User Story 4 - Read Research Documents (Priority: P2)

As a trader, I want to ask Claude to read the full content of any ingested research document (filing summary, earnings transcript, analyst report), so I can deep-dive into specific sources during my analysis session.

**Why this priority**: Querying signals gives a high-level view; reading full documents provides the depth needed for trade decisions. Depends on US1's infrastructure.

**Independent Test**: Ask Claude to show the full content of a specific ingested document and receive the formatted text.

**Acceptance Scenarios**:

1. **Given** an AAPL 10-K filing has been ingested, **When** the user asks "Show me the full AAPL 10-K analysis", **Then** Claude returns the formatted document content from the local filesystem.
2. **Given** a document ID is referenced in a signal, **When** the user asks to see the source document for that signal, **Then** Claude retrieves and displays the document that produced the signal.
3. **Given** a document file has been deleted from disk but metadata remains in the database, **When** the user requests that document, **Then** Claude reports the document metadata but notes the content is no longer available locally.

---

### Edge Cases

- What happens when the research database is empty (no companies, no signals)? The server should return empty results with a helpful message, not an error.
- What happens when the database file is locked by another process (e.g., the research pipeline is running)? The server should use WAL mode (already configured) to allow concurrent reads, or report a clear error if the lock cannot be acquired within 5 seconds.
- What happens when the user queries a ticker not in the watchlist? The server should return an empty result and note the ticker is not being tracked.
- What happens when the MCP server process crashes? Claude Desktop should show the tool as unavailable; restarting the server should restore functionality without data loss.
- What happens when research documents are very large (e.g., a full 10-K filing)? The server should return a truncated summary with a note about the full size, to avoid exceeding context limits.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose a server that allows conversational AI assistants to query research signals by ticker, date range, or signal type (confidence is included in each signal's response data)
- **FR-002**: The system MUST expose a tool to list all ingested source documents, filterable by company, content type, and date range
- **FR-003**: The system MUST expose a tool to retrieve the full text content of a specific ingested document by its identifier
- **FR-004**: The system MUST expose a tool to list all companies on the active watchlist with their metadata (ticker, name, sector, CIK)
- **FR-005**: The system MUST expose a tool to read the current safety state: kill switch status (active/inactive, last toggled timestamp, toggled by), and all risk limit values
- **FR-006**: The system MUST expose a tool to retrieve recent audit log entries, filterable by event type and date range
- **FR-007**: The system MUST expose a tool to get the status of the most recent research pipeline run (start time, completion status, documents ingested, signals generated, errors)
- **FR-008**: All server tools MUST open the database in read-only mode to prevent accidental data modification from conversational queries
- **FR-009**: The system MUST provide a documented configuration for connecting Claude Desktop to the research database server, the Alpaca trading server, and the SEC EDGAR filings server
- **FR-010**: The system MUST truncate document content that exceeds 50,000 characters, returning the first portion with a note about truncation
- **FR-011**: The system MUST return structured, well-formatted responses that Claude can easily interpret and present to the user

### Key Entities

- **Research Signal**: A structured analysis output tied to a company and source document, with signal type, confidence, evidence classification, and summary
- **Source Document**: Metadata and local file path for an ingested research artifact (filing, transcript, news, market signal)
- **Company (Watchlist)**: A tracked company with ticker, name, CIK, and sector
- **Safety State**: Kill switch status and risk limit settings stored as key-value pairs
- **Audit Log Entry**: An append-only record of system events with timestamp, event type, source, and payload
- **Ingestion Run**: A record of a research pipeline execution with timing, counts, and error details

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can retrieve research signals for any watchlist company within 2 seconds of asking
- **SC-002**: Users can access all 7 server tools (signals, documents, document content, watchlist, safety state, audit log, pipeline status) from a single Claude Desktop conversation
- **SC-003**: Setup from documentation to working configuration takes less than 15 minutes for a user familiar with Claude Desktop
- **SC-004**: The server handles concurrent read requests without errors (research pipeline can run simultaneously)
- **SC-005**: All server responses include enough context (timestamps, source references, counts) for the user to make informed follow-up questions

## Assumptions

- The user has Claude Desktop installed on their macOS workstation
- The Intel NUC is on the same local network as the workstation (for research DB access)
- The research database has been populated by at least one pipeline run (features 002/009)
- The Alpaca MCP server and SEC EDGAR MCP server are publicly available and maintained by their respective communities
- The user has Alpaca API keys (paper mode) and understands basic trading concepts
