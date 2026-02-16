# Research: Research Data Ingestion & Analysis

**Feature Branch**: `002-research-ingestion`
**Date**: 2026-02-16

## Decision 1: SEC EDGAR Library

**Decision**: Use `edgartools` (v5.16.0) for all SEC EDGAR access.

**Rationale**: Actively maintained (released 2 days ago), MIT license, Python 3.12+ support. Provides:
- Company lookup by ticker (`Company("NVDA")`)
- Filing retrieval with date filtering (`get_filings(form="10-K", filing_date="2025-01-01:")`)
- Markdown export optimized for LLM consumption (`filing.markdown()`)
- Structured section access for 10-K/10-Q (`filing.obj().risk_factors`, `.management_discussion`)
- 13F holdings as pandas DataFrame (`filing.obj().holdings`) with quarter-over-quarter comparison
- Built-in rate limiting (9 req/s) and caching (immutable filings cached forever)
- `EDGAR_IDENTITY` env var required by SEC (name + email)

**Alternatives considered**:
- `sec-edgar-downloader`: Simpler but no structured parsing or LLM-optimized output
- `python-sec-edgar`: Less maintained, fewer features
- Raw SEC EDGAR API: Would require building all parsing ourselves

## Decision 2: Earnings Call Transcripts

**Decision**: Use Finnhub API via `finnhub-python` SDK as primary source. Budget for potential upgrade to paid tier ($50/mo) if free tier restricts transcript access.

**Rationale**: Two-step API (list transcripts → fetch by ID). Clean structured response with speaker names, roles (executive/analyst), session types (management discussion/Q&A). 17+ years of historical data, 170K+ audio files. Free tier allows 60 calls/min.

**Response format**: Each transcript entry has `name`, `session` ("management discussion" or "Q&A"), and `speech` (array of paragraph strings). Participant metadata includes role and affiliation — ideal for separating management commentary from analyst questions.

**New filing detection strategy**:
1. Use earnings calendar endpoint to know when companies report
2. After earnings date, poll `transcripts_list(symbol)` until transcript appears (usually 24-48 hours)
3. Track last-seen transcript ID per ticker in SQLite to avoid reprocessing

**Alternatives considered**:
- Financial Modeling Prep: $149/mo for transcript access — too expensive for current scope
- API Ninjas: Free tier available, but less proven coverage
- Alpha Vantage: Only 25 free calls/day — too limited

## Decision 3: Acquired Podcast Transcripts

**Decision**: Bootstrap with existing Kaggle dataset (200 episodes, CC0 license, ~3.5M words) for historical episodes. Use AssemblyAI API ($0.15/hr) for new episodes going forward. Download audio via RSS feed (`https://feeds.transistor.fm/acquired`).

**Rationale**:
- Kaggle dataset covers episodes through May 2024 — free and immediate
- AssemblyAI offers best accuracy at lowest cost ($0.15/hr vs $0.26/hr Deepgram, $0.36/hr Whisper API)
- Acquired produces ~2-4 episodes/month at 2-4 hours each → ~$1.50/month ongoing cost
- RSS feed provides episode metadata (title, date, description) and audio download URLs
- `feedparser` library handles RSS parsing

**Episode classification**: Parse episode titles and metadata to classify:
- Company deep-dives: Title contains a company name (e.g., "NVIDIA", "Coca-Cola")
- Interviews: Title contains "Interview" or known interview patterns
- Special/ACQ2: Tagged with "ACQ2" season or "Special" category

**Alternative considered**:
- Self-hosted faster-whisper on NUC: Free but slow (~1x real-time on CPU, meaning 3hr episode takes 3+hr to transcribe). Good fallback but not primary.
- PodScripts.co/HappyScribe: Have transcripts but no programmatic API

## Decision 4: Stratechery Content Access

**Decision**: Ingest via authenticated RSS feed from Stratechery Plus subscription. User subscribes (~$150/year), gets personalized RSS URL at `https://stratechery.passport.online/feed/rss/<subscriber-id>`.

**Rationale**: No public API exists. RSS is the only programmatic access method. Full article HTML is included in the feed (not truncated). Parse with `feedparser` + set User-Agent header to avoid Cloudflare bot detection. Convert HTML to text with `beautifulsoup4`.

**Content types in feed**:
- Weekly Articles (free tier)
- Daily Updates (paid only)
- Interview transcripts (paid only)
- Podcast content (paid only)

**Security**: The personalized RSS URL is the authentication token — store it as an environment variable (`STRATECHERY_FEED_URL`), treat like a secret.

**Alternative considered**: Manual copy-paste from website — doesn't scale, defeats automation purpose

## Decision 5: LLM Analysis Strategy

**Decision**: Use Claude Sonnet 4.5 as primary analysis model via Anthropic Python SDK. Use Pydantic models with `client.messages.parse()` for structured signal extraction. Cache system prompt + analytical framework across document analyses.

**Rationale**:
- Sonnet 4.5 offers best cost/quality tradeoff at $3/$15 per MTok input/output
- `messages.parse()` with Pydantic gives type-safe constrained decoding (guaranteed valid JSON)
- Most documents fit in 200K context window without chunking (10-Q: ~90K tokens, 8-K: ~15K, earnings transcript: ~35K, podcast: ~120K)
- Large 10-Ks (~180-250K tokens) use section-based map-reduce: analyze each section with specialized prompt, then synthesize
- Prompt caching saves ~19% by caching the system prompt + few-shot examples (10K+ tokens) across batch analyses
- Batch API available for 50% discount on bulk historical ingestion

**Cost estimate**: ~$40-80/year for 20-company watchlist with all sources at Sonnet 4.5 rates.

**Section-specific analysis**: Different prompts for different filing sections:
- Risk Factors: Classify risk types, detect new/changed/intensified risks
- MD&A: Extract metrics, identify tone, flag guidance changes
- Financial Statements: Extract key metrics with YoY/QoQ comparisons
- Earnings transcripts: Separate management discussion from Q&A, track sentiment

**Fact vs inference**: Built into the Pydantic schema as `EvidenceType` enum on every signal — satisfies constitution principle II.

**Alternative considered**:
- Haiku 4.5: 3x cheaper but lower quality — use for classification/triage only
- Opus: Higher quality but $15/$75 per MTok — reserve for final synthesis if needed
- OpenAI GPT-4: Would work but user prefers Claude ecosystem

## Decision 6: Document Storage Strategy

**Decision**: Store source documents on filesystem in structured directory hierarchy. Track metadata in SQLite (extends existing DB). Use content hashing for deduplication.

**Rationale**: Constitution requires raw documents persisted locally before analysis (Principle II: NFR-002). Filesystem is natural for large text documents. SQLite tracks metadata (document hash, analysis status, source URL) for efficient querying and dedup detection.

**Directory structure**:
```
research_data/
├── filings/
│   └── {ticker}/
│       ├── 10-K/
│       │   └── {filing_date}_{accession}.md
│       ├── 10-Q/
│       └── 8-K/
├── transcripts/
│   └── {ticker}/
│       └── {year}_Q{quarter}_{transcript_id}.json
├── podcasts/
│   └── acquired/
│       └── {episode_date}_{slug}.json
└── articles/
    └── stratechery/
        └── {date}_{slug}.html
```

**Alternative considered**:
- Store everything in SQLite BLOBs: Bad for large documents, harder to inspect/debug
- S3/cloud storage: Adds dependency and cost, NUC has plenty of local disk

## Decision 7: New Dependencies

**Decision**: Add the following to `pyproject.toml`:

| Package | Version | Purpose |
|---------|---------|---------|
| `edgartools` | `>=5.16` | SEC EDGAR filings & 13F access |
| `finnhub-python` | `>=2.4` | Earnings call transcripts |
| `anthropic` | `>=0.45` | Claude API for LLM analysis |
| `feedparser` | `>=6.0` | RSS feed parsing (Acquired, Stratechery) |
| `beautifulsoup4` | `>=4.12` | HTML → text conversion (Stratechery articles) |
| `pydantic` | `>=2.0` | Structured output schemas for research signals |

**New environment variables**:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes (for research) | - | Claude API key |
| `FINNHUB_API_KEY` | Yes (for transcripts) | - | Finnhub API key |
| `EDGAR_IDENTITY` | Yes (for filings) | - | SEC EDGAR identity (name + email) |
| `STRATECHERY_FEED_URL` | No | - | Stratechery Plus RSS feed URL |
| `ASSEMBLYAI_API_KEY` | No | - | AssemblyAI API key (for podcast transcription) |
| `RESEARCH_DATA_DIR` | No | `research_data/` | Local storage for source documents |

## Decision 8: Research Pipeline Architecture

**Decision**: Single CLI command `finance-agent research` that orchestrates all ingestion sources sequentially with independent error handling. Each source is a pluggable ingestion module.

**Rationale**: Sequential execution is simpler and sufficient for a 20-company watchlist (~30 min target). Each source module has a consistent interface: `ingest(watchlist, since_date) → list[SourceDocument]`. Source failures are isolated — one source failing doesn't block others.

**Pipeline stages**:
1. Load watchlist from config
2. For each enabled source: ingest new documents → persist locally → analyze with LLM → store signals
3. Log all activity to audit trail
4. Report summary (documents processed, signals generated, errors)

**Alternative considered**:
- Async/parallel ingestion: More complex, not needed at this scale
- Separate commands per source: Less convenient for scheduled runs
- Background daemon: Overkill — cron on NUC handles scheduling
