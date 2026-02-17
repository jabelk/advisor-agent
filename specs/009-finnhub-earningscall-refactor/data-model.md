# Data Model: Finnhub Free-Tier Refactor & EarningsCall Transcript Source

**Feature**: 009-finnhub-earningscall-refactor | **Date**: 2026-02-17

---

## Content Type Mappings

All data flows through the existing `SourceDocumentMeta` model and `source_document` table — no schema changes required.

### Finnhub Market Signals (US1)

| Content Type | Source Type | Source ID Format | Storage Path |
|-------------|------------|-----------------|--------------|
| `analyst_ratings` | `finnhub_data` | `finnhub:{ticker}:recommendation_trends:{date}` | `market_data/finnhub/{ticker}/` |
| `earnings_history` | `finnhub_data` | `finnhub:{ticker}:company_earnings:{date}` | `market_data/finnhub/{ticker}/` |
| `insider_activity` | `finnhub_data` | `finnhub:{ticker}:insider_transactions:{date}` | `market_data/finnhub/{ticker}/` |
| `insider_sentiment` | `finnhub_data` | `finnhub:{ticker}:insider_sentiment:{date}` | `market_data/finnhub/{ticker}/` |
| `company_news` | `finnhub_data` | `finnhub:{ticker}:company_news:{date}` | `market_data/finnhub/{ticker}/` |

**Dedup key**: `(source_type, source_id)` — date in source_id prevents re-ingestion on the same day.

### EarningsCall Transcripts (US2)

| Content Type | Source Type | Source ID Format | Storage Path |
|-------------|------------|-----------------|--------------|
| `earnings_call` | `earnings_transcript` | `earningscall:{ticker}:{year}:Q{quarter}` | `transcripts/{ticker}/` |

**Dedup key**: `(source_type, source_id)` — year+quarter ensures one transcript per earnings period.

---

## Entity Relationships

```text
company (watchlist)
  └─ source_document (1:N per company)
       ├─ source_type: "finnhub_data" | "earnings_transcript"
       ├─ content_type: one of the 6 types above
       ├─ source_id: unique per source+period
       └─ research_signal (1:N per document)
            ├─ signal_type: sentiment, financial_metric, investor_activity, etc.
            └─ evidence_type: fact | inference
```

---

## Finnhub Endpoint → SDK Method Mapping

| Endpoint Name | SDK Method | Required Params | Lookback |
|--------------|-----------|----------------|----------|
| `recommendation_trends` | `client.recommendation_trends(symbol)` | symbol | All available |
| `company_earnings` | `client.company_earnings(symbol, limit=8)` | symbol, limit | 8 quarters |
| `insider_transactions` | `client.stock_insider_transactions(symbol, from, to)` | symbol, from, to | 90 days |
| `insider_sentiment` | `client.stock_insider_sentiment(symbol, from, to)` | symbol, from, to | 12 months |
| `company_news` | `client.company_news(symbol, _from=, to=)` | symbol, _from, to | 30 days |

---

## EarningsCall Transcript Levels

| Level | Content | Requires Paid Key |
|-------|---------|-------------------|
| 1 | `transcript.text` — plain text string | No (demo: AAPL/MSFT only) |
| 2 | `transcript.speakers` — Speaker objects with name/title/text | Yes |
| 3 | Level 2 + word-level timestamps | Yes |
| 4 | `prepared_remarks` + `questions_and_answers` as separate strings | Yes |

**Fallback strategy**: Try level=2, catch `InsufficientApiAccessError`, retry with level=1.

---

## Analysis Prompt → Content Type Mapping (US3)

| Content Type | Prompt Constant | Key Extractions |
|-------------|----------------|-----------------|
| `analyst_ratings` | `ANALYST_RATINGS_PROMPT` | Consensus direction, upgrade/downgrade trends, price target movement |
| `earnings_history` | `EARNINGS_HISTORY_PROMPT` | Beat/miss patterns, surprise magnitude trends, estimate accuracy |
| `insider_activity` | `INSIDER_ACTIVITY_PROMPT` | Net buying/selling by role, cluster activity, transaction codes |
| `insider_sentiment` | `INSIDER_SENTIMENT_PROMPT` | Monthly MSPR direction, sustained buying/selling periods |
| `company_news` | `COMPANY_NEWS_PROMPT` | Key themes, sentiment, material events, catalysts |
| `earnings_call` | `EARNINGS_TRANSCRIPT_PROMPT` | Management commentary, guidance, Q&A tone (existing prompt) |

All prompts require fact-vs-inference classification per constitution Principle II.
