# Feature Specification: Research Data Ingestion & Analysis

**Feature Branch**: `002-research-ingestion`
**Created**: 2026-02-16
**Status**: Draft
**Input**: User description: Build the research data ingestion and analysis layer — ingest SEC filings, earnings transcripts, podcast analysis (Acquired, Stratechery), leadership tracking, and notable investor signals to produce structured research signals for the decision engine.

## User Scenarios & Testing

### User Story 1 - SEC Filings & Earnings Transcript Analysis (Priority: P1)

The user maintains a configurable watchlist of companies (by ticker symbol). When new SEC filings (10-K annual reports, 10-Q quarterly reports, 8-K current events) or earnings call transcripts are published for those companies, the system automatically ingests the documents, persists them locally, and uses AI to produce structured research signals. Each signal captures sentiment, guidance changes, key financial metric shifts, risk factor updates, and notable management commentary. The user can view summaries, compare signals across filing periods, and spot multi-quarter trends without reading every document.

**Why this priority**: SEC filings and earnings transcripts are the most structured, authoritative, and freely available data sources. They form the foundation of any research-driven investment process and directly satisfy the constitution's "Research-Driven Decisions" principle. This is the MVP — it delivers standalone value even without the other sources.

**Independent Test**: Add 3 tickers to the watchlist, run research ingestion, and verify the system downloads filings and transcripts, produces analysis summaries with source references, and allows comparison across at least 2 quarters.

**Acceptance Scenarios**:

1. **Given** a watchlist with ticker "NVDA", **When** the user triggers research ingestion, **Then** the system downloads the most recent 10-K, 10-Q, and 8-K filings from SEC EDGAR plus the latest earnings call transcript, persists them locally, and generates a research signal for each document with sentiment, key metrics, and guidance summary.
2. **Given** research signals exist for NVDA across Q3 and Q4, **When** the user requests a comparison, **Then** the system shows changes in sentiment, revenue guidance, and risk factors between the two periods.
3. **Given** a new 8-K filing is published for a watchlist company, **When** the next research ingestion runs, **Then** the new filing is automatically detected, ingested, and analyzed without re-processing previously analyzed documents.
4. **Given** a filing has been analyzed, **When** the user views the research signal, **Then** the signal clearly indicates which statements are facts extracted from the document versus inferences made by AI analysis.

---

### User Story 2 - Acquired Podcast Research Mining (Priority: P2)

The system ingests Acquired podcast episodes — obtaining transcripts for analysis. Episodes are classified by type: company deep-dives (the primary value) versus interviews and special episodes (secondary value with different analytical treatment). AI analysis extracts investment-relevant insights: what makes the covered company remarkable, competitive advantages, growth catalysts, risk factors, and any referenced data sources worth following up on. Recent episodes are prioritized over older ones. The user can see which companies were covered, key investment takeaways, and cross-reference with their watchlist.

**Why this priority**: The user has observed that companies covered by Acquired (whose hosts are VC investors) frequently experience significant growth afterward. The multi-hour deep-dive format contains research density that most investors never access. This is a differentiated signal source unavailable to typical retail investors.

**Independent Test**: Ingest the 5 most recent Acquired episodes, verify transcripts are obtained and classified by type, and confirm AI analysis produces company-specific investment signals with source references.

**Acceptance Scenarios**:

1. **Given** the Acquired podcast feed, **When** research ingestion runs, **Then** the system retrieves episode metadata (title, date, description) and obtains transcripts for at least the most recent 12 months of episodes.
2. **Given** an episode titled with a company name (e.g., "NVIDIA"), **When** the episode is analyzed, **Then** it is classified as a "company deep-dive" and the analysis extracts investment-relevant signals including competitive advantages, growth catalysts, and risk factors.
3. **Given** an interview-format episode, **When** the episode is analyzed, **Then** it is classified as an "interview" and the analysis focuses on leadership insights and industry perspectives rather than company-specific investment signals.
4. **Given** Acquired analysis is complete, **When** a covered company is also on the user's watchlist, **Then** the Acquired signals are linked to that company's research profile alongside SEC filing signals.

---

### User Story 3 - Stratechery Analysis Integration (Priority: P2)

The system ingests Stratechery content (articles, daily updates, and podcast transcripts) via the user's paid subscription. Content is classified by type: written analysis articles (primary signal — Ben Thompson's strategic analysis), interviews (leadership and industry insights), and podcast episodes (discussion-format analysis). AI extracts insights about company direction, competitive positioning, market structure shifts, and technology adoption trends. Signals are mapped to relevant companies on the watchlist.

**Why this priority**: Stratechery provides uniquely insightful tech industry analysis that consistently identifies company direction and growth trajectories before they're obvious to mainstream investors. The user considers this a high-signal source worth paying for. Combined with SEC filings, it provides both the quantitative (filings) and qualitative (strategic analysis) views of a company.

**Independent Test**: Configure subscription access, ingest the most recent 30 days of Stratechery content, verify classification by type, and confirm AI analysis maps insights to watchlist companies.

**Acceptance Scenarios**:

1. **Given** valid Stratechery subscription credentials are configured, **When** research ingestion runs, **Then** the system retrieves and persists articles, daily updates, and podcast content from the subscription.
2. **Given** a Stratechery article analyzes a specific company's strategy, **When** that company is on the user's watchlist, **Then** the analysis produces a research signal linked to that company with insights about competitive positioning and strategic direction.
3. **Given** Stratechery content references multiple companies, **When** the article is analyzed, **Then** each referenced company receives its own research signal with the relevant extracted insights.
4. **Given** Stratechery credentials are missing or invalid, **When** research ingestion runs, **Then** the system logs a warning and skips Stratechery ingestion without affecting other sources.

---

### User Story 4 - Leadership & Investor Intelligence (Priority: P3)

The system tracks executive leadership changes at watchlist companies — CEO, CTO, CFO, and key product leaders. Leadership data is sourced from SEC filings (8-K filings report executive changes) and from mentions in the qualitative sources (Acquired, Stratechery). Additionally, the system monitors notable investors with strong long-term track records by ingesting institutional holdings disclosures (13F filings). Leadership changes and significant investor position changes are flagged as research signals. The user believes (per John Maxwell's "21 Laws of Leadership") that leadership quality is a leading indicator of company success that most retail investors overlook.

**Why this priority**: Leadership tracking and investor monitoring are valuable but depend on the foundational data sources (SEC filings, qualitative content) already being operational. These signals layer on top of the core research pipeline.

**Independent Test**: After US1 is operational, verify that 8-K filings mentioning executive appointments produce leadership-change signals, and that 13F filings for selected notable investors produce position-change signals.

**Acceptance Scenarios**:

1. **Given** an 8-K filing reports a CEO change at a watchlist company, **When** the filing is analyzed, **Then** a "leadership_change" signal is generated with the executive's name, role, and whether it's an appointment or departure.
2. **Given** notable investors are configured for tracking (e.g., by CIK number), **When** new 13F quarterly holdings are filed, **Then** the system generates signals for significant position changes (new positions, exits, or >25% size changes) in watchlist companies.
3. **Given** an Acquired episode or Stratechery article discusses a company's leadership, **When** the content is analyzed, **Then** leadership-relevant insights are tagged and linked to that company's leadership profile.

---

### User Story 5 - Research Signal History & Cross-Source Comparison (Priority: P3)

All research signals across all sources are stored with full provenance (source document, timestamp, content type, fact-vs-inference classification). The user can query signal history for any watchlist company, compare signals across time periods, and see how signals from different sources (filings, transcripts, podcasts, articles) align or diverge. A company research profile aggregates all available signals into a unified view. The system tracks which documents have been processed to avoid duplicate analysis.

**Why this priority**: This is the integration layer that makes the individual data sources greater than the sum of their parts. It depends on at least US1 being operational and becomes more valuable as additional sources are added.

**Independent Test**: After ingesting data from at least 2 sources for the same company, verify the user can view a unified research profile showing signals from all sources sorted chronologically, and that querying by time range returns correctly filtered results.

**Acceptance Scenarios**:

1. **Given** a company has signals from SEC filings and Acquired podcast analysis, **When** the user views the company's research profile, **Then** all signals are displayed in chronological order with source type clearly labeled.
2. **Given** signals exist across multiple quarters, **When** the user requests a time-range query, **Then** only signals within the specified range are returned.
3. **Given** research ingestion runs multiple times, **When** the same document has already been analyzed, **Then** it is skipped (no duplicate signals produced) and only new documents are processed.
4. **Given** any research signal, **When** the user inspects its details, **Then** the signal includes: source document reference, extraction timestamp, content classification (filing/transcript/podcast/article), and fact-vs-inference label for each claim.

---

### Edge Cases

- What happens when SEC EDGAR is temporarily unavailable? The system retries with backoff and logs the failure without blocking other sources.
- What happens when an earnings transcript is not available for a quarter? The system notes the gap and continues analysis with available data.
- What happens when an Acquired episode covers a company not on the watchlist? The signal is still generated and stored (the user may add the company later).
- What happens when Stratechery subscription expires mid-ingestion? The system detects the authentication failure, logs a warning, and continues with other sources.
- What happens when AI analysis produces contradictory signals from different sources? Both signals are preserved with their sources — the decision engine (not this feature) resolves conflicts.
- What happens when a filing is amended (e.g., 10-K/A)? The amended filing is ingested as a new document linked to the original, and analysis notes it as an amendment.
- What happens when the watchlist is empty? Research ingestion completes immediately with a warning that no companies are configured.

## Requirements

### Functional Requirements

- **FR-001**: System MUST maintain a configurable watchlist of companies identified by ticker symbol, supporting add, remove, and list operations.
- **FR-002**: System MUST ingest SEC filings (10-K, 10-Q, 8-K) for all watchlist companies (per NFR-002, raw documents are persisted locally before analysis).
- **FR-003**: System MUST ingest earnings call transcripts for all watchlist companies (per NFR-002, raw documents are persisted locally before analysis).
- **FR-004**: System MUST analyze each ingested document using AI to produce structured research signals containing: company identifier, signal type, sentiment assessment, key findings, source reference, and fact-vs-inference classification.
- **FR-005**: System MUST support time-series comparison of research signals across filing periods for the same company. *(Fully satisfied by US5; US1 MVP provides signal storage and query but not period-to-period comparison UI.)*
- **FR-006**: System MUST ingest Acquired podcast episode metadata and transcripts, classify episodes by type (company deep-dive, interview, special), and produce investment-relevant research signals.
- **FR-007**: System MUST ingest Stratechery content (articles, daily updates, podcasts) via authenticated subscription access and produce research signals mapped to relevant companies.
- **FR-008**: System MUST detect executive leadership changes from SEC 8-K filings and generate leadership-change signals.
- **FR-009**: System MUST ingest 13F institutional holdings filings for configured notable investors and generate signals for significant position changes in watchlist companies.
- **FR-010**: System MUST classify all content by type (SEC filing, earnings transcript, podcast deep-dive, podcast interview, analysis article) and treat each type with appropriate analytical focus.
- **FR-011**: System MUST track which documents have been ingested and analyzed to prevent duplicate processing on subsequent runs.
- **FR-012**: System MUST provide a unified company research profile aggregating signals from all sources in chronological order.
- **FR-013**: System MUST support querying research signals by company, time range, source type, and signal type.
- **FR-014**: System MUST log all ingestion and analysis activity to the audit trail with source references.
- **FR-015**: System MUST handle source unavailability gracefully — failure of one source must not block ingestion from other sources.
- **FR-016**: System MUST distinguish between facts extracted directly from source documents and inferences generated by AI analysis in every research signal.

### Non-Functional Requirements

- **NFR-001**: Research ingestion for a 20-company watchlist should complete within 30 minutes for incremental runs (processing only new documents).
- **NFR-002**: Raw source documents must be persisted before AI analysis begins (no analysis of transient data).
- **NFR-003**: All research signals must include a traceable reference to the specific source document and section that produced them.

### Key Entities

- **Company**: A tracked entity on the watchlist, identified by ticker symbol. Has a name, sector, and a collection of research signals from all sources.
- **Source Document**: A raw ingested document (filing, transcript, episode transcript, article). Has a source type, publication date, retrieval timestamp, content hash (for deduplication), and local storage path.
- **Research Signal**: The core output — a structured finding from AI analysis of a source document. Contains company reference, signal type (sentiment, guidance_change, leadership_change, competitive_insight, investor_activity, risk_factor), confidence level, fact-vs-inference classification, a human-readable summary, and a reference to the source document.
- **Content Classification**: Categorization of source material — SEC filing (10-K, 10-Q, 8-K), earnings transcript, podcast deep-dive, podcast interview, analysis article, holdings disclosure (13F).
- **Notable Investor**: A tracked institutional investor, identified by name and CIK number, whose 13F holdings changes generate research signals.

## Success Criteria

### Measurable Outcomes

- **SC-001**: System successfully ingests and analyzes SEC filings and earnings transcripts for all watchlist companies, with new filings processed within 4 hours of availability.
- **SC-002**: 100% of research signals include traceable source references and fact-vs-inference classification.
- **SC-003**: User can retrieve a complete research profile for any watchlist company — aggregating all sources — in under 5 seconds.
- **SC-004**: Time-series comparison is available for at least 4 quarters of historical filing data per company.
- **SC-005**: Acquired podcast analysis covers at least the most recent 12 months of episodes with correct episode type classification.
- **SC-006**: Research ingestion from one source does not fail or block when another source is unavailable.
- **SC-007**: Duplicate document detection prevents re-analysis on 100% of previously processed documents during incremental runs.
- **SC-008**: The user can identify actionable investment insights (guidance changes, sentiment shifts, leadership moves, or investor activity) from research signals without reading the underlying source documents.

## Assumptions

- The user starts with a focused watchlist of 10-20 companies, biased toward technology and AI-related companies per their investment thesis.
- Research ingestion is triggered via CLI command (`finance-agent research`) with the option for automated scheduled runs (e.g., daily via cron on the NUC).
- For the Acquired podcast, transcripts are obtained from episode pages or via a transcription service if not directly available. The specific method is an implementation detail.
- The user will subscribe to Stratechery Plus for full content access, which provides authenticated feed access.
- "Notable investors" are manually configured (e.g., Berkshire Hathaway, ARK Invest) and tracked via their public 13F filings, not via paid data feeds.
- The decision engine (a separate future feature) consumes research signals — this feature produces signals but does not make trade recommendations.
- AI analysis cost per document is acceptable given the user's willingness to pay for data services and tools.

## Out of Scope

- Trade execution or recommendations (that's the decision engine feature)
- Real-time market data or price alerts
- Portfolio tracking or position management
- Backtesting research signals against historical returns
- Social media sentiment analysis (Twitter/Reddit/StockTwits)
- Scraping paywalled content without a valid subscription
