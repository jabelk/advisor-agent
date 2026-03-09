# Option Data Contracts

**Feature**: 016-real-options-data
**Date**: 2026-03-08

## Internal Functions

### build_occ_symbol

Construct an OCC-format option symbol from components.

**Parameters**:
- `ticker` (str, required): Underlying stock ticker (e.g., "ABBV")
- `expiration_date` (date, required): Contract expiration date
- `strike_price` (float, required): Strike price in dollars
- `option_type` (str, required): "call" or "put"

**Returns**: `str` — OCC symbol (e.g., "ABBV240315C00170000")

---

### find_nearest_expiration

Find the nearest standard monthly expiration date to a target date.

**Parameters**:
- `target_date` (date, required): The ideal expiration date
- `prefer_monthly` (bool, optional): Prefer 3rd Friday monthlies. Default: True.

**Returns**: `date` — The nearest standard expiration date

---

### select_option_contract

Select the best-matching option contract for a backtest trade, then fetch its historical bars.

**Parameters**:
- `conn` (db connection, required): Database connection for cache reads/writes
- `underlying_ticker` (str, required): Stock ticker
- `underlying_price` (float, required): Stock price at the entry date
- `entry_date` (date, required): When the trade would be entered
- `exit_date` (date, required): When the trade would be exited
- `strike_strategy` (str, required): "atm", "otm_5", "otm_10", "itm_5", "custom"
- `custom_strike_offset_pct` (float, optional): Offset for "custom" strategy
- `expiration_days` (int, required): Target days to expiration
- `option_type` (str, required): "call" or "put"
- `api_key` (str, required): Broker API key
- `secret_key` (str, required): Broker secret key

**Returns** (success):
```json
{
  "option_symbol": "ABBV240315C00170000",
  "strike": 170.0,
  "expiration": "2024-03-15",
  "entry_premium": 4.50,
  "exit_premium": 2.10,
  "volume_at_entry": 1523,
  "pricing": "real"
}
```

**Returns** (fallback):
```json
{
  "option_symbol": null,
  "strike": 170.0,
  "expiration": "2024-03-15",
  "entry_premium": null,
  "exit_premium": null,
  "volume_at_entry": null,
  "pricing": "estimated"
}
```

---

### fetch_and_cache_option_bars

Fetch historical bars for an option symbol from the broker and cache them locally.

**Parameters**:
- `conn` (db connection, required): Database connection for caching
- `option_symbol` (str, required): OCC-format symbol
- `start_date` (str, required): Start of date range (YYYY-MM-DD)
- `end_date` (str, required): End of date range (YYYY-MM-DD)
- `api_key` (str, required): Broker API key
- `secret_key` (str, required): Broker secret key

**Returns**: `list[dict]` — Cached bars for the symbol (same as stock bars: timestamp, open, high, low, close, volume)

**Behavior**:
- Check cache first; only fetch from broker for uncached date ranges
- Write fetched bars to `option_price_cache` table
- Return empty list if broker has no data for this symbol

---

## MCP Tool Contract

### get_option_chain_history

Look up historical option contracts for a ticker around a specific date.

**Parameters**:
- `ticker` (str, required): Underlying stock ticker
- `date` (str, required): Target date (YYYY-MM-DD)
- `option_type` (str, optional): "call" or "put". Default: "call"
- `strike_min` (float, optional): Minimum strike price filter
- `strike_max` (float, optional): Maximum strike price filter
- `expiration_within_days` (int, optional): Only contracts expiring within N days of target date. Default: 45.

**Returns** (success):
```json
{
  "ticker": "ABBV",
  "date": "2024-03-15",
  "contracts": [
    {
      "symbol": "ABBV240315C00165000",
      "strike": 165.0,
      "expiration": "2024-03-15",
      "type": "call",
      "close_price": 7.20,
      "volume": 2341,
      "pricing": "real"
    },
    {
      "symbol": "ABBV240315C00170000",
      "strike": 170.0,
      "expiration": "2024-03-15",
      "type": "call",
      "close_price": 4.50,
      "volume": 1523,
      "pricing": "real"
    }
  ]
}
```

**Returns** (error):
```json
{"error": "No option data found for ABBV around 2024-03-15."}
```

**Behavior**:
- Constructs candidate OCC symbols for strikes in the range
- Fetches bars for each via `fetch_and_cache_option_bars`
- Returns contracts that had trading activity on or near the target date
- Uses read-write DB connection (writes to option cache)
