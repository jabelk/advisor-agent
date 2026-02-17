# Phase 0 Research: Finnhub Free-Tier Refactor & EarningsCall Transcript Source

**Feature**: 009-finnhub-earningscall-refactor | **Date**: 2026-02-17

---

## Research Area 1: EarningsCall.biz Python Library

### Decision: Use `earningscall` v1.4.0 for transcript ingestion

**Key Findings**:

- **Version**: 1.4.0 (MIT license, Python 3.8-3.13)
- **Dependencies**: dataclasses-json, requests, requests-cache
- **API key**: Set via `earningscall.api_key`, `ECALL_API_KEY` env var, or `EARNINGSCALL_API_KEY` env var. Falls back to `"demo"` if unset.

**Demo Mode Limitations**:
- Only 2 companies: AAPL and MSFT
- Only level=1 transcripts (plain text, no speaker attribution)
- Calendar restricted to 2025-01-10
- Raises `InsufficientApiAccessError` for anything else

**Transcript Levels**:

| Level | Content | Paid? |
|-------|---------|-------|
| 1 (default) | `transcript.text` — full text as single string | No (demo for AAPL/MSFT) |
| 2 | `transcript.speakers` — list of Speaker objects with name/title/text | Yes |
| 3 | Level 2 + word-level timestamps | Yes |
| 4 | `prepared_remarks` and `questions_and_answers` as separate strings | Yes |

**Speaker Attribution** (level=2):
- `Speaker.speaker` — label like "spk_0"
- `Speaker.speaker_info.name` — e.g., "Tim Cook"
- `Speaker.speaker_info.title` — e.g., "Chief Executive Officer"
- `Speaker.text` — what they said
- `speaker_name_map_v2` may be None for some transcripts (experimental)

**Usage Pattern**:
```python
from earningscall import get_company
company = get_company("aapl")  # returns Company or None
transcript = company.get_transcript(year=2024, quarter=3, level=2)
for spk in transcript.speakers:
    if spk.speaker_info:
        print(f"{spk.speaker_info.name} ({spk.speaker_info.title}): {spk.text[:100]}")
```

**Error Handling**: Catch `InsufficientApiAccessError` for level fallback (try level=2, fall back to level=1).

### Implementation Notes

- Use `EARNINGSCALL_API_KEY` env var (matches our existing naming convention)
- `source_id` format: `"earningscall:{ticker}:{year}:Q{quarter}"`
- `content_type`: `"earnings_call"` (reuses existing analysis prompt)
- Dedup: check `source_document` table before fetching
- Level fallback: try level=2 first, catch `InsufficientApiAccessError`, retry with level=1
- Format as markdown with speaker sections for level=2, plain text for level=1

---

## Research Area 2: Finnhub Free-Tier Endpoints

### Decision: Use 5 free-tier endpoints for market signals

**Rate Limit**: 60 calls/min shared across all endpoints (30 calls/sec hard cap). For 10 companies x 5 endpoints = 50 calls, fits in under 1 minute with sequential execution.

### Endpoint Details

#### 1. `recommendation_trends(symbol)` → analyst_ratings

Returns `list[dict]` — monthly analyst consensus snapshots.

```json
[{"buy": 24, "hold": 7, "period": "2026-02-01", "sell": 0, "strongBuy": 13, "strongSell": 0, "symbol": "AAPL"}]
```

Fields: `strongBuy`, `buy`, `hold`, `sell`, `strongSell`, `period`, `symbol`. Several months of history.

#### 2. `company_earnings(symbol, limit=8)` → earnings_history

Returns `list[dict]` — quarterly earnings surprises.

```json
[{"actual": 2.18, "estimate": 2.11, "period": "2025-12-31", "quarter": 4, "surprise": 0.07, "surprisePercent": 3.32, "symbol": "TSLA", "year": 2025}]
```

Fields: `actual`, `estimate`, `surprise`, `surprisePercent`, `period`, `quarter`, `year`. Up to 4 quarters on free tier.

#### 3. `stock_insider_transactions(symbol)` → insider_activity

Returns `dict` with `data` list of transactions.

```json
{"symbol": "AAPL", "data": [{"name": "WILLIAMS JEFFREY E", "share": 489944, "change": -100000, "transactionDate": "2025-04-01", "transactionCode": "S", "transactionPrice": 223.45}]}
```

Key transaction codes: `P` (purchase), `S` (sale), `M` (exercise), `A` (grant). Focus on P and S for signals.

#### 4. `stock_insider_sentiment(symbol, _from, to)` → insider_sentiment

Returns `dict` with `data` list of monthly MSPR values. `_from` and `to` are **required**.

```json
{"symbol": "AAPL", "data": [{"year": 2025, "month": 4, "change": 3934, "mspr": 42.07}]}
```

MSPR range: -100 (all selling) to +100 (all buying). Positive = bullish. Only months with activity appear.

#### 5. `company_news(symbol, _from, to)` → company_news

Returns `list[dict]` — news articles. `_from` and `to` are **required**.

```json
[{"id": 127849523, "headline": "Apple Vision Pro 2...", "source": "MarketWatch", "summary": "...", "datetime": 1739750400, "url": "..."}]
```

`datetime` is UNIX timestamp. `id` useful for dedup.

### Implementation Notes

- Each endpoint → separate `SourceDocumentMeta` with distinct `content_type`
- `source_id` format: `"finnhub:{ticker}:{endpoint}:{date}"` (date = today for snapshots, period for historical)
- Rate limiting: sequential calls with watchlist, 50 calls for 10 companies fits in 60/min budget
- Error handling: per-endpoint try/catch, log failures, continue with remaining endpoints
- Date params for insider_sentiment and company_news: use 12-month lookback from today

---

## Sources

- [earningscall on PyPI](https://pypi.org/project/earningscall/) | [GitHub](https://github.com/EarningsCall/earningscall-python)
- [EarningsCall API Pricing](https://earningscall.biz/api-pricing)
- [Finnhub Python SDK](https://github.com/Finnhub-Stock-API/finnhub-python) | [Docs](https://finnhub.io/docs/api)
- [Finnhub Rate Limits](https://finnhub.io/docs/api/rate-limit)
- [Finnhub Pricing](https://finnhub.io/pricing)
