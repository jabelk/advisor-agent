# Feature Specification: Finnhub Free-Tier Refactor & EarningsCall Transcript Source

**Feature Branch**: `009-finnhub-earningscall-refactor`
**Created**: 2026-02-17
**Status**: Draft
**Input**: User description: "Refactor Finnhub to use free-tier market signal endpoints (analyst ratings, earnings history, insider activity, news) instead of premium transcripts, and add EarningsCall.biz as a dedicated earnings call transcript source with speaker attribution. Update all tests, config, and CLI accordingly."

## User Scenarios & Testing

### User Story 1 - Finnhub Market Signals via Free Tier (Priority: P1)

The operator runs the research pipeline with Finnhub as a source and receives structured market signals from 5 free-tier endpoints: analyst consensus ratings, earnings beat/miss history, insider buy/sell activity, insider sentiment (MSPR), and recent company news. Each endpoint produces a distinct signal type that feeds into the research analysis.

**Why this priority**: The current Finnhub integration attempts to fetch earnings transcripts, which returns a 403 error on the free tier ($3,000/mo premium required). This blocks Finnhub from contributing any data to research. Repurposing Finnhub for its genuinely free endpoints unlocks 5 valuable market signal categories at zero cost.

**Independent Test**: Run the research pipeline with `--source finnhub` for a watchlist company and verify that 5 distinct document types are ingested, each with the correct content type and structured markdown content.

**Acceptance Scenarios**:

1. **Given** a company on the watchlist and a valid Finnhub API key, **When** the operator runs research with the finnhub source, **Then** the system ingests analyst ratings, earnings history, insider activity, insider sentiment, and company news as separate documents.
2. **Given** previously ingested Finnhub data for a company, **When** the operator re-runs research with the finnhub source, **Then** only new or updated data is ingested (no duplicates).
3. **Given** no Finnhub API key configured, **When** the operator runs research, **Then** the finnhub source is skipped with a clear message indicating the key is missing.
4. **Given** a Finnhub API rate limit or temporary error, **When** one endpoint fails, **Then** the remaining endpoints continue processing and the error is logged.

---

### User Story 2 - EarningsCall.biz Transcript Source (Priority: P1)

The operator runs the research pipeline with `--source transcripts` and receives earnings call transcripts from EarningsCall.biz instead of Finnhub. Transcripts include speaker attribution (name, title, spoken text) formatted as readable markdown. The existing `earnings_call` content type and analysis prompt are reused so transcript analysis works unchanged.

**Why this priority**: Earnings transcripts are a core research input — management commentary, forward guidance, and Q&A tone are critical signals. Without a working transcript source, the research pipeline has a major gap. EarningsCall.biz fills this gap with a clean dedicated service.

**Independent Test**: Run `--source transcripts` for a watchlist company and verify a transcript is ingested with speaker-attributed content in markdown format, and that the existing earnings call analysis prompt produces valid signals from it.

**Acceptance Scenarios**:

1. **Given** a watchlist company with available earnings transcripts, **When** the operator runs research with the transcripts source, **Then** the system fetches the most recent transcript with speaker names, titles, and text formatted as markdown.
2. **Given** a previously ingested transcript for a company/quarter, **When** the operator re-runs research, **Then** the transcript is skipped (dedup by source ID).
3. **Given** a transcript request for detailed speaker-level data that requires a paid tier, **When** the service returns an access error, **Then** the system falls back to a basic transcript format and logs a warning.
4. **Given** no API key configured, **When** the operator runs research with transcripts source, **Then** the system operates in demo mode (limited companies) or skips with a clear message.

---

### User Story 3 - Analysis of New Market Signal Types (Priority: P2)

The operator receives meaningful research analysis for each new Finnhub content type. Each signal type has a tailored analysis prompt that extracts investment-relevant insights: analyst consensus trends, earnings surprise patterns, insider trading signals, and news sentiment.

**Why this priority**: Ingesting raw data (US1) is necessary but not sufficient. The value comes from structured analysis that highlights actionable patterns — e.g., "insiders have been net buyers for 3 consecutive months" or "analyst consensus shifted from hold to buy."

**Independent Test**: After ingesting Finnhub market signals for a company, run the analysis pipeline and verify each content type produces structured signals with fact-vs-inference classification.

**Acceptance Scenarios**:

1. **Given** ingested analyst ratings data, **When** the analysis pipeline runs, **Then** the system produces signals identifying consensus direction, rating distribution shifts, and upgrade/downgrade momentum.
2. **Given** ingested earnings history data, **When** the analysis pipeline runs, **Then** the system produces signals identifying beat/miss patterns, surprise magnitude trends, and EPS trajectory.
3. **Given** ingested insider activity data, **When** the analysis pipeline runs, **Then** the system produces signals identifying net buying/selling trends, notable transactions by executives, and cluster activity.
4. **Given** ingested company news, **When** the analysis pipeline runs, **Then** the system produces signals summarizing key themes, sentiment, and material events.

---

### Edge Cases

- What happens when a Finnhub free-tier endpoint returns empty data for a company (e.g., no analyst coverage for a small-cap)?
- How does the system handle EarningsCall.biz returning no transcript for a recent quarter (earnings call hasn't happened yet or isn't transcribed)?
- What if the Finnhub API key is valid but rate-limited (60 calls/min on free tier)? How are 5 endpoints x N companies managed?
- What happens when EarningsCall.biz speaker attribution data is incomplete (missing names or titles)?
- How does the system handle the transition from old Finnhub transcript data already in the database to the new EarningsCall source?

## Requirements

### Functional Requirements

- **FR-001**: The system MUST ingest data from 5 Finnhub free-tier endpoints per watchlist company: analyst consensus, earnings history, insider transactions, insider sentiment, and company news.
- **FR-002**: Each Finnhub endpoint MUST produce a separate document with a distinct content type for targeted analysis.
- **FR-003**: The system MUST provide a new dedicated transcript source that fetches earnings call transcripts with speaker attribution (name, title, spoken text).
- **FR-004**: The transcript source MUST reuse the existing `earnings_call` content type so existing analysis prompts work without modification.
- **FR-005**: The system MUST fall back gracefully when transcript detail levels are unavailable (paid tier features), using a basic format instead.
- **FR-006**: The system MUST deduplicate ingested documents — re-running a source for the same company/period MUST NOT create duplicate records.
- **FR-007**: The system MUST handle per-endpoint errors independently — one Finnhub endpoint failing MUST NOT prevent other endpoints from being ingested.
- **FR-008**: The system MUST provide analysis prompts tailored to each new content type that extract investment-relevant structured signals.
- **FR-009**: The existing `--source transcripts` CLI option MUST continue to work, now backed by the new transcript provider instead of Finnhub.
- **FR-010**: The system MUST add `--source finnhub` as a new valid source option in the CLI for market signal ingestion.

### Key Entities

- **Market Signal Document**: A structured markdown document produced from a Finnhub free-tier endpoint, tagged with a specific content type (analyst_ratings, earnings_history, insider_activity, insider_sentiment, company_news).
- **Earnings Transcript**: A speaker-attributed transcript document from EarningsCall.biz, formatted as markdown with speaker names, titles, and text sections.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Finnhub source produces 5 distinct document types per company when all endpoints return data, compared to 0 usable documents today (due to 403 on transcripts).
- **SC-002**: Earnings transcripts include speaker names and titles for at least the most recent quarter of any S&P 500 company.
- **SC-003**: All existing unit and integration tests continue to pass after the refactor (no regressions).
- **SC-004**: Analysis of each new content type produces at least one structured signal with fact-vs-inference classification.
- **SC-005**: Research pipeline completes successfully with `--source finnhub --source transcripts` for a watchlist company without errors.

## Assumptions

- The Finnhub free-tier rate limit (60 API calls/minute) is sufficient for a watchlist of 10-20 companies when calls are made sequentially.
- EarningsCall.biz provides a demo/free mode that works for at least a few major companies (AAPL, etc.) for testing purposes.
- Previously ingested Finnhub transcript documents in the database are left as-is (historical data preserved, not deleted or migrated).
- The existing `earnings_call` analysis prompt works for EarningsCall.biz transcripts without modification since the content format (speaker-attributed text) is compatible.

## Out of Scope

- Adding new database tables or schema migrations — the existing document and signal tables are sufficient.
- Modifying the LLM analyzer core logic — only new prompts are added, not new analysis patterns.
- Changing other data sources (SEC EDGAR, Acquired, Stratechery, investor 13F) — those are unaffected.
- Paid-tier features of EarningsCall.biz beyond what the free/demo tier provides.
