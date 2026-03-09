# Scanner & Alerts Contracts

**Feature**: 017-live-pattern-alerts
**Date**: 2026-03-08

## Internal Functions

### run_scan

Run the pattern scanner: evaluate all paper_trading patterns against recent market data.

**Parameters**:
- `conn` (db connection, required): Database connection for alert storage and pattern lookup
- `api_key` (str, required): Broker API key for market data
- `secret_key` (str, required): Broker secret key
- `cooldown_hours` (int, optional): Deduplication window. Default: 24.

**Returns**: `ScanResult` dict with scan_timestamp, patterns_evaluated, tickers_scanned, alerts_generated, alerts list, auto_executions count, auto_executions_blocked count.

**Behavior**:
- Fetches all patterns with status `paper_trading`
- For each pattern, determines tickers from the pattern's watchlist or configured tickers
- Fetches recent bars (last 10 trading days) for each ticker via fetch_and_cache_bars
- Evaluates trigger conditions against latest bars
- Creates alert if triggered and no duplicate exists within cooldown window
- If pattern has auto_execute enabled: checks safety, submits paper trade, records result
- Logs scan to audit log

---

### evaluate_triggers

Evaluate a pattern's trigger conditions against recent bars for a ticker.

**Parameters**:
- `rule_set` (RuleSet, required): Parsed pattern rules
- `bars` (list[dict], required): Recent OHLCV bars (at least 2 bars required)

**Returns** (triggered):
```json
{
  "triggered": true,
  "price_change_pct": 7.2,
  "volume_multiple": 2.1,
  "conditions_met": ["price_change_pct >= 5.0", "volume_spike >= 1.5"],
  "latest_price": 45.30,
  "previous_close": 42.26
}
```

**Returns** (not triggered):
```json
{
  "triggered": false
}
```

---

### create_alert

Persist a new alert to the pattern_alert table.

**Parameters**:
- `conn` (db connection, required)
- `pattern_id` (int, required)
- `pattern_name` (str, required)
- `ticker` (str, required)
- `trigger_date` (str, required): YYYY-MM-DD
- `trigger_details` (dict, required): From evaluate_triggers result
- `recommended_action` (str, required): Action type from rule set
- `pattern_win_rate` (float, optional): Win rate from latest backtest

**Returns**: `int` — alert ID

**Behavior**:
- Inserts into pattern_alert with status='new'
- Uses INSERT OR IGNORE with unique index to prevent duplicates
- Returns 0 if duplicate (already exists within cooldown)

---

### list_alerts

Retrieve alerts with optional filtering.

**Parameters**:
- `conn` (db connection, required)
- `status` (str, optional): Filter by status (new, acknowledged, acted_on, dismissed)
- `pattern_id` (int, optional): Filter by pattern
- `ticker` (str, optional): Filter by ticker
- `days` (int, optional): Only alerts from last N days. Default: 7.

**Returns**: `list[dict]` — Alert records sorted by created_at descending.

---

### update_alert_status

Change an alert's lifecycle status.

**Parameters**:
- `conn` (db connection, required)
- `alert_id` (int, required)
- `new_status` (str, required): One of: acknowledged, acted_on, dismissed

**Returns**: `bool` — True if updated, False if alert not found.

---

## CLI Commands

### `finance-agent pattern scan`

Run the pattern scanner.

**Arguments**:
- `--watch N` (optional): Repeat scan every N minutes. Default: one-shot.
- `--cooldown N` (optional): Deduplication cooldown in hours. Default: 24.

**Output**: Summary of scan results, list of new alerts generated.

---

### `finance-agent pattern alerts`

List and manage alerts.

**Arguments**:
- `--status STATUS` (optional): Filter by status (new, acknowledged, acted_on, dismissed)
- `--pattern-id ID` (optional): Filter by pattern
- `--ticker TICKER` (optional): Filter by ticker
- `--days N` (optional): Show last N days. Default: 7.

**Output**: Tabular list of alerts with pattern name, ticker, trigger time, details, status.

---

### `finance-agent pattern alerts ack ID`

Acknowledge an alert.

### `finance-agent pattern alerts dismiss ID`

Dismiss an alert.

### `finance-agent pattern alerts acted ID`

Mark an alert as acted on.

---

## MCP Tool Contract

### get_pattern_alerts

Retrieve recent pattern alerts for Claude Desktop.

**Parameters**:
- `status` (str, optional): Filter by status. Default: all.
- `pattern_id` (int, optional): Filter by pattern.
- `ticker` (str, optional): Filter by ticker.
- `days` (int, optional): Show last N days. Default: 7.

**Returns** (success):
```json
{
  "alerts": [
    {
      "id": 1,
      "pattern_name": "Pharma News Spike Dip",
      "ticker": "MRNA",
      "trigger_date": "2026-03-08",
      "trigger_details": {
        "price_change_pct": 7.2,
        "volume_multiple": 2.1,
        "latest_price": 45.30
      },
      "recommended_action": "buy_call",
      "pattern_win_rate": 0.50,
      "status": "new",
      "auto_executed": false,
      "created_at": "2026-03-08T14:30:00Z"
    }
  ],
  "total": 1
}
```

**Returns** (no alerts):
```json
{
  "alerts": [],
  "total": 0
}
```
