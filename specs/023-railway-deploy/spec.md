# Feature Specification: Railway Deployment

**Feature Branch**: `023-railway-deploy`
**Created**: 2026-03-09
**Status**: Draft
**Input**: User description: "Deploy advisor-agent MCP server to Railway so Claude Desktop connects over HTTPS instead of local process."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cloud-Hosted MCP Server (Priority: P1)

Jordan wants the advisor-agent MCP tools (research, sandbox CRM, task management) available in Claude Desktop without running a local process or SSH-tunneling to a home server. The MCP server should be deployed to a cloud platform and Claude Desktop should connect to it over HTTPS.

**Why this priority**: This is the core value — eliminates dependency on a local machine or SSH tunnel, making all 20+ MCP tools available from any network.

**Independent Test**: Deploy the server to the cloud platform, update Claude Desktop configuration to point at the cloud URL, and verify that an MCP tool call (e.g., `get_signals`) returns data successfully.

**Acceptance Scenarios**:

1. **Given** the MCP server is deployed, **When** Jordan opens Claude Desktop, **Then** all advisor-agent tools appear in the tool list and respond to invocations within 5 seconds.
2. **Given** the cloud service restarts, **When** Jordan invokes an MCP tool, **Then** the service recovers automatically and the tool call succeeds without manual intervention.
3. **Given** the server is running, **When** a health check endpoint is called, **Then** it returns a success response confirming the server is operational.

---

### User Story 2 - Persistent Data Across Deploys (Priority: P2)

Jordan's research database (market signals, SEC filings, pattern backtests) and Salesforce sandbox data must survive deployments and container restarts. Data stored in the database should not be lost when the server is updated or restarted.

**Why this priority**: Without persistent storage, every deploy wipes the research database and all cached data, making the tools unreliable.

**Independent Test**: Create a Salesforce task via MCP tool, redeploy the server, then query tasks and verify the previously created task still exists in the database.

**Acceptance Scenarios**:

1. **Given** data exists in the research database, **When** the server is redeployed, **Then** all previously stored data is intact and queryable.
2. **Given** the server writes new data (e.g., caching a research document), **When** the container restarts, **Then** the cached data persists.

---

### User Story 3 - Secure Credential Management (Priority: P3)

Jordan's Salesforce sandbox credentials, API keys (Finnhub, EarningsCall), and other secrets must be securely stored and injected into the running server without being committed to source code or visible in logs.

**Why this priority**: Security is non-negotiable — credentials must never appear in code, build logs, or container images.

**Independent Test**: Deploy the server with credentials configured as environment variables on the cloud platform, invoke `sandbox_show_tasks` MCP tool, and verify it successfully connects to the Salesforce sandbox.

**Acceptance Scenarios**:

1. **Given** Salesforce credentials are configured on the cloud platform, **When** the MCP server starts, **Then** it connects to the Salesforce sandbox successfully.
2. **Given** a secret is misconfigured or missing, **When** the server starts, **Then** the health check reports which credential is missing without exposing the secret value.
3. **Given** a request arrives without a valid Bearer token, **When** the server processes it, **Then** the request is rejected and no tool is invoked.

---

### User Story 4 - Automated Deployment Pipeline (Priority: P4)

When Jordan (or a collaborator) merges code to the main branch, the cloud server should automatically rebuild and redeploy with the latest changes, including running tests before deploying.

**Why this priority**: Manual deployment is error-prone and slow. Automated CI/CD ensures every deploy is tested and consistent.

**Independent Test**: Push a minor change to the main branch and verify the cloud service automatically rebuilds, passes tests, and serves the updated code.

**Acceptance Scenarios**:

1. **Given** a commit is merged to main, **When** the CI pipeline runs, **Then** tests execute and, if passing, the server is automatically deployed.
2. **Given** tests fail in the pipeline, **When** a deploy is attempted, **Then** the deployment is blocked and the current running version is unaffected.
3. **Given** a deployment completes, **When** the health check runs, **Then** it confirms the new version is live.

---

### Edge Cases

- What happens when the cloud platform is temporarily unavailable? Claude Desktop should show a clear connection error rather than hanging indefinitely.
- What happens when the database file grows beyond the persistent storage quota? The health check should report storage utilization.
- What happens when Salesforce sandbox credentials expire or are rotated? The health check should report the authentication failure without exposing credentials.
- What happens when multiple Claude Desktop sessions connect simultaneously? The server should handle concurrent requests without data corruption.
- What happens when an unauthenticated or invalid-token request reaches the MCP endpoint? It must be rejected before any tool logic executes.

## Clarifications

### Session 2026-03-09

- Q: How should the cloud-hosted MCP endpoint be protected from unauthorized access? → A: Bearer token authentication via FastMCP StaticTokenVerifier (research found Railway has no built-in OAuth2 proxy — see research.md Decision 1)
- Q: Which auth provider approach should be used? → A: FastMCP StaticTokenVerifier with MCP_API_TOKEN env var (originally chose Railway OAuth2 proxy, but research invalidated — Railway has no such feature)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The MCP server MUST be deployable as a containerized service on a cloud platform with a stable HTTPS URL.
- **FR-002**: The MCP server MUST expose all existing tools (research, sandbox CRM, task management, pattern lab, alerts) over an HTTP-based MCP transport protocol.
- **FR-003**: The deployment MUST include a health check endpoint that reports server status, credential connectivity, and storage availability.
- **FR-004**: Claude Desktop configuration MUST be updatable to connect to the cloud-hosted MCP server via its HTTPS URL, including authentication credentials.
- **FR-005**: All secrets (Salesforce credentials, API keys) MUST be configured as environment variables on the cloud platform, never stored in source code or container images.
- **FR-011**: The MCP endpoint MUST be protected by Bearer token authentication (FastMCP StaticTokenVerifier); unauthenticated requests MUST be rejected before any tool logic executes.
- **FR-006**: The database and research data MUST persist across container restarts and redeployments via mounted persistent storage.
- **FR-007**: The CI/CD pipeline MUST run the test suite before deploying, blocking deployment if tests fail.
- **FR-008**: The server MUST automatically restart on failure with a bounded retry policy.
- **FR-009**: The container build MUST use the existing multi-stage build pattern for minimal image size.
- **FR-010**: The deployment configuration MUST be defined in version-controlled configuration files in the repository.

### Key Entities

- **Deployment Configuration**: Cloud platform settings including build instructions, health check path, restart policy, and environment variable declarations.
- **Claude Desktop Configuration**: Local configuration file pointing Claude Desktop at the cloud-hosted MCP server URL instead of a local process or SSH tunnel.
- **CI/CD Pipeline**: Automated workflow triggered on main branch merges that runs tests, builds the container, and deploys to the cloud platform.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 20+ MCP tools respond successfully when invoked from Claude Desktop connected to the cloud-hosted server.
- **SC-002**: Tool invocations complete within 10 seconds for standard operations (list tasks, get signals, search clients).
- **SC-003**: Server recovers automatically from a crash within 60 seconds without manual intervention.
- **SC-004**: Data persists across at least 3 consecutive redeployments with zero data loss.
- **SC-005**: A code merge to main triggers a fully automated deploy pipeline that completes within 10 minutes.
- **SC-006**: Zero secrets are visible in build logs, container images, or source code.

## Assumptions

- The family-meeting project's deployment pattern (containerized service with health check, persistent volume, CI/CD pipeline) is the reference architecture.
- The existing Dockerfile and multi-stage build pattern will be adapted for the MCP server entrypoint rather than rewritten.
- The MCP server's existing HTTP transport mode is sufficient for cloud deployment — no custom transport implementation needed.
- Railway is the target cloud platform (based on user's existing infrastructure with family-meeting).
- The current `finance-research` MCP entry in Claude Desktop (SSH tunnel to home server) will be replaced by the cloud-hosted URL.
- Salesforce sandbox credentials will be manually configured on the cloud platform dashboard initially.
