# CLI Contracts: Research Data Ingestion & Analysis

**Feature Branch**: `002-research-ingestion`
**Date**: 2026-02-16

## Commands

### `finance-agent watchlist add <TICKER>`

Add a company to the research watchlist.

**Input**: Ticker symbol (e.g., `NVDA`, `AAPL`)

**Behavior**:
1. Resolve ticker to company name and CIK via SEC EDGAR
2. If ticker already exists and active: print "Already on watchlist" and exit 0
3. If ticker was previously removed (active=0): reactivate and exit 0
4. Insert new company record
5. Log `watchlist_add` audit event

**Output**:
```
Added NVDA (NVIDIA Corporation, CIK: 0001045810) to watchlist
```

**Errors**:
- Unknown ticker: `Error: Could not resolve ticker "ZZZZ" — verify the symbol is correct`
- Database unavailable: `Error: Database unavailable — run 'finance-agent health' first`

**Exit codes**: 0 success, 1 error

---

### `finance-agent watchlist remove <TICKER>`

Remove a company from the research watchlist (soft delete).

**Input**: Ticker symbol

**Behavior**:
1. Set `active=0` on matching company record
2. Existing signals and documents are preserved
3. Log `watchlist_remove` audit event

**Output**:
```
Removed NVDA from watchlist (existing research data preserved)
```

**Errors**:
- Not on watchlist: `Error: NVDA is not on the watchlist`

**Exit codes**: 0 success, 1 error

---

### `finance-agent watchlist list`

Display the active watchlist with summary stats.

**Output**:
```
Research Watchlist (5 companies):

  NVDA  NVIDIA Corporation        12 signals  (last: 2026-02-15)
  AAPL  Apple Inc                  8 signals  (last: 2026-02-14)
  MSFT  Microsoft Corporation      6 signals  (last: 2026-02-14)
  GOOG  Alphabet Inc               4 signals  (last: 2026-02-10)
  AMZN  Amazon.com Inc             0 signals  (never)
```

**Empty watchlist**:
```
Research Watchlist (0 companies):

  No companies on watchlist. Add one with: finance-agent watchlist add <TICKER>
```

**Exit codes**: 0 always

---

### `finance-agent investors add <NAME> <CIK>`

Add a notable investor to track via 13F filings.

**Input**: Investor name (quoted if spaces) and CIK number

**Output**:
```
Added "Berkshire Hathaway" (CIK: 0001067983) to investor tracking
```

**Exit codes**: 0 success, 1 error

---

### `finance-agent investors remove <NAME>`

Stop tracking a notable investor.

**Output**:
```
Removed "Berkshire Hathaway" from investor tracking
```

**Exit codes**: 0 success, 1 error

---

### `finance-agent investors list`

Display tracked investors.

**Output**:
```
Tracked Investors (2):

  Berkshire Hathaway    CIK: 0001067983    last 13F: 2025-11-14
  ARK Investment Mgmt   CIK: 0001803994    last 13F: 2025-11-15
```

**Exit codes**: 0 always

---

### `finance-agent research [--source SOURCE] [--ticker TICKER] [--full]`

Run research ingestion and analysis pipeline.

**Options**:
- `--source`: Limit to specific source (`sec`, `transcripts`, `acquired`, `stratechery`, `investors`). Default: all enabled sources.
- `--ticker`: Limit to specific ticker (must be on watchlist). Default: entire watchlist.
- `--full`: Force re-analysis of all documents (ignore dedup). Default: incremental only.

**Behavior**:
1. Load watchlist and configuration
2. For each enabled source (in order): SEC filings → earnings transcripts → Acquired → Stratechery → 13F investor holdings
3. Per source: detect new documents → download and persist → analyze with LLM → store signals
4. Log all activity to audit trail
5. Print progress and summary

**Output** (incremental run):
```
Research Ingestion — 2026-02-16T10:30:00Z
Watchlist: 5 companies | Sources: sec, transcripts, acquired

SEC Filings:
  NVDA: 1 new 8-K ingested, 2 signals generated
  AAPL: 0 new filings
  MSFT: 1 new 10-Q ingested, 5 signals generated
  GOOG: 0 new filings
  AMZN: 0 new filings

Earnings Transcripts:
  NVDA: 1 new transcript (Q4 2025), 4 signals generated
  AAPL: 0 new transcripts
  ...

Acquired Podcast:
  2 new episodes ingested
  "NVIDIA" (deep-dive): 6 signals for NVDA
  "Great CEOs" (interview): 3 signals across 2 companies

Summary:
  Documents: 5 new (3 filings, 1 transcript, 2 episodes)
  Signals: 20 new
  Errors: 0
  Duration: 4m 32s
```

**Error handling**:
- Source unavailable: print warning, continue with other sources
- API rate limit: retry with backoff, log if exhausted
- LLM analysis failure: mark document as `failed`, continue with next

**Exit codes**: 0 all sources succeeded, 1 any source had errors (partial success still produces output)

---

### `finance-agent research status`

Show research pipeline status and recent activity.

**Output**:
```
Research Status:

Last run: 2026-02-16T10:30:00Z (completed, 4m 32s)
Documents: 147 total (142 analyzed, 3 pending, 2 failed)
Signals: 523 total across 5 companies

Sources:
  SEC EDGAR:    OK (last: 2026-02-16, 89 documents)
  Finnhub:      OK (last: 2026-02-16, 34 transcripts)
  Acquired:     OK (last: 2026-02-15, 18 episodes)
  Stratechery:  DISABLED (STRATECHERY_FEED_URL not configured)
  13F Holdings: OK (last: 2026-02-14, 6 filings)

Failed documents (2):
  MSFT 8-K 2026-02-10: LLM analysis timeout
  GOOG 10-Q 2026-01-28: EDGAR download failed (HTTP 503)
```

**Exit codes**: 0 always

---

### `finance-agent signals <TICKER> [--type TYPE] [--since DATE] [--until DATE] [--source SOURCE]`

Query research signals for a company.

**Options**:
- `--type`: Filter by signal type (`sentiment`, `guidance_change`, `leadership_change`, `competitive_insight`, `risk_factor`, `financial_metric`, `investor_activity`)
- `--since`: Start date (ISO 8601)
- `--until`: End date (ISO 8601)
- `--source`: Filter by source type (`sec_filing`, `earnings_transcript`, `podcast_episode`, `article`, `holdings_13f`)

**Output**:
```
Research Signals for NVDA (12 total):

2026-02-15  sentiment         [FACT]   HIGH   Revenue grew 94% YoY to $22.1B, beating guidance
            Source: 10-Q Q4 2025 (Item 7: MD&A)

2026-02-15  guidance_change   [FACT]   HIGH   Q1 2026 guidance raised to $24B±2%, up from $20B
            Source: Earnings Call Q4 2025 (management discussion)

2026-02-14  competitive_insight [INFERENCE] MED  Blackwell GPU demand suggests 2+ year AI infrastructure cycle
            Source: Acquired Episode "NVIDIA" (2026-01-26)

2026-02-10  risk_factor       [FACT]   MED    New risk: China export restrictions expanded to cover H20
            Source: 8-K 2026-02-08

2026-02-01  investor_activity [FACT]   HIGH   Berkshire Hathaway increased NVDA position by 45%
            Source: 13F-HR Q3 2025 (Berkshire Hathaway)
```

**Exit codes**: 0 success, 1 error (unknown ticker, etc.)

---

### `finance-agent profile <TICKER>`

Display unified research profile for a company — aggregating all signals.

**Output**:
```
Research Profile: NVDA (NVIDIA Corporation)
Sector: Semiconductors | CIK: 0001045810 | On watchlist since: 2026-02-01

Overall Sentiment: Bullish (based on 12 signals from 4 sources)

Latest Signals:
  [2026-02-15] Revenue grew 94% YoY — guidance raised (10-Q, Earnings Call)
  [2026-02-14] Blackwell demand suggests multi-year AI infra cycle (Acquired)
  [2026-02-10] China export risk expanded (8-K)
  [2026-02-01] Berkshire increased position 45% (13F)

Signal Summary:
  Sentiment:          3 bullish, 0 neutral, 0 bearish
  Guidance Changes:   1 raised, 0 maintained, 0 lowered
  Risk Factors:       2 identified (1 new this quarter)
  Leadership:         0 changes
  Investor Activity:  1 significant (Berkshire +45%)

Sources Contributing:
  SEC Filings:        5 documents (3 signals)
  Earnings Calls:     2 transcripts (4 signals)
  Acquired Podcast:   1 episode (3 signals)
  Stratechery:        0 articles
  13F Holdings:       1 filing (2 signals)

Data Coverage: Q1 2025 — Q4 2025 (4 quarters)
```

**Exit codes**: 0 success, 1 error

## Signal Output Schema

Each research signal conforms to this structure (used internally and in CLI output):

```
{
  "company_ticker": "NVDA",
  "signal_type": "guidance_change",
  "evidence_type": "fact",
  "confidence": "high",
  "summary": "Q1 2026 revenue guidance raised to $24B±2%, up from prior $20B guidance",
  "details": "Management cited strong Blackwell demand and data center expansion...",
  "source_section": "Management Discussion",
  "metrics": [
    {"name": "Revenue Guidance", "value": "$24B", "prior_value": "$20B", "change_pct": "+20%", "period": "Q1 FY2026"}
  ],
  "source_document": {
    "type": "earnings_transcript",
    "title": "NVIDIA Q4 2025 Earnings Call",
    "published_at": "2026-02-12T21:00:00Z"
  }
}
```
