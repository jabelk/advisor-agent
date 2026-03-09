# MCP Tool Contracts: Pattern Lab Tools

**Feature**: 015-mcp-pattern-tools
**Date**: 2026-03-08

## New Tools

### run_backtest

Run a multi-ticker backtest for a pattern, returning per-ticker breakdown and combined aggregate metrics.

**Parameters**:
- `pattern_id` (int, required): Pattern ID to backtest
- `tickers` (str, optional): Comma-separated ticker list. Default: watchlist tickers.
- `start_date` (str, optional): Start date YYYY-MM-DD. Default: 1 year ago.
- `end_date` (str, optional): End date YYYY-MM-DD. Default: today.

**Returns** (success):
```json
{
  "pattern_id": 1,
  "pattern_name": "Pharma News Spike Dip",
  "date_range_start": "2024-01-01",
  "date_range_end": "2025-12-31",
  "tickers": ["ABBV", "MRNA", "PFE"],
  "ticker_breakdowns": [
    {"ticker": "ABBV", "events_detected": 1, "trades_entered": 1, "win_count": 0, "win_rate": 0.0, "avg_return_pct": -50.0, "total_return_pct": -50.0},
    {"ticker": "MRNA", "events_detected": 9, "trades_entered": 8, "win_count": 1, "win_rate": 0.125, "avg_return_pct": -31.2, "total_return_pct": -249.6}
  ],
  "combined": {
    "trigger_count": 12,
    "trade_count": 10,
    "win_count": 2,
    "win_rate": 0.2,
    "avg_return_pct": -27.8,
    "total_return_pct": -277.9,
    "max_drawdown_pct": 327.9,
    "sharpe_ratio": -0.55,
    "sample_size_warning": true,
    "regimes": [...]
  },
  "no_entry_events": [
    {"ticker": "MRNA", "date": "2025-05-16", "reason": "No 2.0% pullback within 2-day window"}
  ]
}
```

**Returns** (error):
```json
{"error": "Pattern #99 not found."}
{"error": "No price data available for any ticker."}
{"error": "Alpaca API keys not configured. Set ALPACA_PAPER_API_KEY and ALPACA_PAPER_SECRET_KEY."}
```

**Behavior**:
- Single ticker: runs single-ticker backtest, returns same structure with one breakdown entry
- Multiple tickers: runs multi-ticker aggregation via `run_multi_ticker_news_dip_backtest`
- Quantitative patterns: uses `run_backtest` from the standard engine
- Qualitative patterns: uses `run_news_dip_backtest` / `run_multi_ticker_news_dip_backtest`
- Results are saved via `save_backtest_result` (same as CLI)

---

### run_ab_test

Compare 2+ pattern variants on identical data with statistical significance testing.

**Parameters**:
- `pattern_ids` (str, required): Comma-separated pattern IDs (e.g., "1,2,3")
- `tickers` (str, required): Comma-separated ticker list
- `start_date` (str, optional): Start date YYYY-MM-DD. Default: 1 year ago.
- `end_date` (str, optional): End date YYYY-MM-DD. Default: today.

**Returns** (success):
```json
{
  "pattern_ids": [1, 2],
  "tickers": ["ABBV", "MRNA"],
  "date_range_start": "2024-01-01",
  "date_range_end": "2025-12-31",
  "variants": [
    {"pattern_id": 1, "name": "Pharma News Spike Dip", "events": 10, "trades": 9, "win_rate": 0.111, "avg_return_pct": -33.3},
    {"pattern_id": 2, "name": "Biotech Spike Pullback", "events": 10, "trades": 9, "win_rate": 0.222, "avg_return_pct": -2.3}
  ],
  "comparisons": [
    {"variant_a_id": 1, "variant_b_id": 2, "win_rate_p_value": 1.0, "win_rate_significant": false, "avg_return_p_value": 0.18, "avg_return_significant": false}
  ],
  "best_variant_id": 2,
  "best_is_significant": false,
  "sample_size_warnings": ["! Pattern #1 has only 9 trades. Results may not be statistically reliable."]
}
```

**Returns** (error):
```json
{"error": "A/B test requires at least 2 pattern IDs."}
{"error": "Pattern #5 is in draft status. Confirm the pattern first."}
{"error": "--tickers is required for A/B testing."}
```

---

### export_backtest

Export backtest results for a pattern to a markdown file.

**Parameters**:
- `pattern_id` (int, required): Pattern ID to export
- `backtest_id` (int, optional): Specific backtest result ID. Default: most recent.
- `output_dir` (str, optional): Directory for export. Default: current directory.

**Returns** (success):
```json
{
  "file_path": "/Users/jordan/pattern-1-backtest-2026-03-08.md",
  "pattern_id": 1,
  "backtest_id": 7
}
```

**Returns** (error):
```json
{"error": "No backtest results found for pattern #15. Run a backtest first."}
{"error": "Pattern #99 not found."}
```

---

## Existing Tools (Unchanged)

The existing 11 MCP tools are not modified:
1. `get_signals` — Query research signals by ticker
2. `list_documents` — List ingested research documents
3. `get_watchlist` — List tracked companies
4. `get_safety_state` — Read kill switch and risk limits
5. `get_audit_log` — Query audit trail
6. `get_pipeline_status` — Research pipeline run status
7. `read_document` — Read full document content
8. `list_patterns` — List trading patterns
9. `get_pattern_detail` — Full pattern details with rules
10. `get_backtest_results` — Backtest history for a pattern
11. `get_paper_trade_summary` — Paper trading performance
