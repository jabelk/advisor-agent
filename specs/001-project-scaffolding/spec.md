# Feature Specification: Project Scaffolding

**Feature Branch**: `001-project-scaffolding`
**Created**: 2026-02-16
**Status**: Draft
**Input**: User description: "Project scaffolding: Python project structure, config management, secrets handling, SQLite schema, Docker setup"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Runs the Agent for the First Time (Priority: P1)

A developer clones the repo, installs dependencies, configures their API keys, and starts the agent in paper trading mode. The system validates that all required configuration is present, connects to the broker's paper trading environment, and confirms readiness by displaying account status.

**Why this priority**: Nothing else works without a runnable project. This is the foundation that every subsequent feature builds on.

**Independent Test**: Can be fully tested by cloning the repo, running the install command, setting environment variables for paper trading, and executing a health check command that confirms connectivity and configuration.

**Acceptance Scenarios**:

1. **Given** a fresh clone of the repository, **When** the developer runs the dependency install command, **Then** all dependencies are installed without errors and the project is ready to run.
2. **Given** dependencies are installed and paper trading API keys are set in environment variables, **When** the developer runs the application entry point, **Then** the system validates all required configuration, reports any missing or invalid settings, and exits cleanly if configuration is incomplete.
3. **Given** valid paper trading configuration, **When** the application starts successfully, **Then** it displays the current account status (cash balance, buying power, account type) confirming connectivity.
4. **Given** no API keys are configured, **When** the developer attempts to start the application, **Then** the system fails immediately with a clear error message listing each missing required setting.

---

### User Story 2 - Developer Manages Configuration Across Environments (Priority: P2)

A developer needs to switch between paper trading and live trading configurations without changing any code. They should be able to maintain separate configuration profiles and switch between them by changing only environment variables.

**Why this priority**: The constitution mandates that paper-to-live switching is purely a configuration change. This must be baked into the project structure from the start.

**Independent Test**: Can be tested by creating two sets of environment variables (paper and live) and verifying the application correctly identifies which mode it is operating in, with live mode requiring additional confirmation.

**Acceptance Scenarios**:

1. **Given** paper trading environment variables are set, **When** the application starts, **Then** it operates in paper trading mode and clearly indicates this in its output.
2. **Given** live trading environment variables are set, **When** the application starts, **Then** it operates in live trading mode and displays a prominent warning that real money is at risk.
3. **Given** both paper and live keys are set simultaneously, **When** the application starts, **Then** it defaults to paper trading mode and warns about the presence of live keys.
4. **Given** a configuration file template exists in the repository, **When** a new developer sets up the project, **Then** they can copy the template and fill in their own credentials without risk of committing secrets.

---

### User Story 3 - System Records Activity to a Local Database (Priority: P2)

The system initializes and maintains a local database for recording trading activity, research artifacts metadata, and audit logs. The database schema supports the append-only audit trail required by the constitution.

**Why this priority**: The audit trail (Constitution Principle IV) is foundational — every subsequent feature needs somewhere to write logs and records.

**Independent Test**: Can be tested by starting the application, verifying the database is created with the correct schema, writing a test audit entry, and confirming it can be queried back.

**Acceptance Scenarios**:

1. **Given** the application starts for the first time, **When** no database exists, **Then** it creates the database file and initializes the schema automatically.
2. **Given** an existing database with data, **When** the application starts, **Then** it connects to the existing database without data loss and applies any pending schema migrations.
3. **Given** the database is initialized, **When** an audit event is recorded, **Then** the event is stored with a timestamp, event type, source component, and structured payload, and it cannot be modified or deleted through the application layer.
4. **Given** audit events exist in the database, **When** the operator queries for events within a time range, **Then** the system returns all matching events in chronological order.

---

### User Story 4 - Agent Runs in an Isolated Container (Priority: P3)

The agent can be built and run as a container image, with secrets injected via environment variables and network access restricted to only necessary external endpoints (broker API, data sources).

**Why this priority**: Containerization supports the Security by Design principle (Constitution Principle V) but is not required for initial development. Developers can run locally first.

**Independent Test**: Can be tested by building the container image, running it with paper trading environment variables, and verifying it starts successfully and can reach the broker API.

**Acceptance Scenarios**:

1. **Given** the repository contains a container definition, **When** a developer builds the image, **Then** it builds successfully with all dependencies included.
2. **Given** a built container image, **When** it is run with paper trading environment variables, **Then** the application starts and operates identically to running outside the container.
3. **Given** the container is running, **When** it attempts to connect to endpoints outside the allowed list, **Then** those connections are blocked.

---

### Edge Cases

- What happens when the database file is corrupted or inaccessible? The system should detect this and report a clear error rather than silently failing.
- What happens when API keys are present but invalid (wrong format, expired, revoked)? The system should validate credentials at startup and report the specific issue.
- What happens when the system is started with read-only filesystem access? The system should fail with a clear error indicating it needs write access for the database and log files.
- What happens when multiple instances of the application are started against the same database? The system should either use file-level locking to prevent concurrent access or support concurrent access safely.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a single command to install all dependencies from a lockfile, producing a reproducible environment.
- **FR-002**: System MUST load configuration from environment variables, with an optional `.env` file for local development convenience.
- **FR-003**: System MUST validate all required configuration at startup and fail fast with a clear, actionable error message listing every missing or invalid setting.
- **FR-004**: System MUST distinguish between paper trading mode and live trading mode based solely on which set of API credentials are provided.
- **FR-005**: System MUST default to paper trading mode when both paper and live credentials are present.
- **FR-006**: System MUST display a prominent warning when operating in live trading mode.
- **FR-007**: System MUST create and maintain a local SQLite database for structured data (trades, positions, audit logs).
- **FR-008**: System MUST automatically initialize the database schema on first run and apply migrations on subsequent runs without data loss.
- **FR-009**: System MUST provide an append-only audit log table where records cannot be modified or deleted through the application layer.
- **FR-010**: System MUST store audit entries with at minimum: timestamp, event type, source component, and structured event payload.
- **FR-011**: System MUST include a `.env.example` file documenting all configuration variables with descriptions but no actual secrets.
- **FR-012**: System MUST ensure `.env` files are excluded from version control via `.gitignore`.
- **FR-013**: System MUST provide a container definition that packages the application with all dependencies.
- **FR-014**: System MUST provide a health check command that validates configuration, database connectivity, and broker API connectivity, reporting the status of each.
- **FR-015**: System MUST structure the codebase in a modular layout that separates concerns by architectural layer (data ingestion, research, decision, execution, logging) even if those layers are initially empty.

### Key Entities

- **Configuration**: The set of all runtime settings including API credentials, trading mode, risk parameters, and database location. Distinguished by environment (paper vs. live).
- **AuditEvent**: An immutable record of something that happened in the system. Includes timestamp, event type (e.g., "startup", "config_validated", "order_placed"), source component, and a structured payload containing event-specific details.
- **DatabaseMigration**: A versioned change to the database schema, applied in order, tracked so each migration runs exactly once.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new developer can go from cloning the repository to a running health check in under 5 minutes, following only the README instructions.
- **SC-002**: Switching from paper trading to live trading mode requires changing only environment variables — zero code changes, zero config file edits beyond environment.
- **SC-003**: The system detects and reports 100% of missing required configuration settings at startup, rather than failing later at the point of use.
- **SC-004**: All audit events written to the database are retrievable and in correct chronological order, with no gaps or duplicates.
- **SC-005**: The container image builds and starts successfully, connecting to the paper trading broker API, in under 2 minutes on a standard development machine.

## Assumptions

- The developer has Python 3.12+ and uv already installed on their machine (documented in README as prerequisites).
- The developer has an Alpaca Markets account with paper trading API keys (sign-up instructions will be in README).
- The Intel NUC home server has Docker installed and can run containers.
- SQLite is sufficient for the expected data volume in this experimental phase (no need for a separate database server).
- The Alpaca MCP server is used alongside the SDK — the scaffolding provides the foundation for both access methods.
