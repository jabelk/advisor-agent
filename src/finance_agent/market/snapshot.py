"""Real-time price snapshot queries via Alpaca."""

from __future__ import annotations

import logging
from typing import Any

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockSnapshotRequest

logger = logging.getLogger(__name__)


def get_snapshots(
    client: StockHistoricalDataClient,
    tickers: list[str],
) -> dict[str, dict[str, Any]]:
    """Get real-time price snapshots for one or more tickers.

    Returns a dict mapping ticker -> snapshot data with keys:
    last_price, bid_price, bid_size, ask_price, ask_size,
    volume, vwap.
    """
    request = StockSnapshotRequest(symbol_or_symbols=tickers)

    try:
        response = client.get_stock_snapshot(request)
    except Exception as e:
        logger.error("Snapshot API error: %s", e)
        raise

    results: dict[str, dict[str, Any]] = {}

    if isinstance(response, dict):
        snapshot_items = response.items()
    else:
        # Single ticker returns a Snapshot object directly
        snapshot_items = [(tickers[0], response)]

    for ticker, snap in snapshot_items:
        data: dict[str, Any] = {}

        if hasattr(snap, "latest_trade") and snap.latest_trade:
            data["last_price"] = float(snap.latest_trade.price)
        else:
            data["last_price"] = None

        if hasattr(snap, "latest_quote") and snap.latest_quote:
            data["bid_price"] = float(snap.latest_quote.bid_price)
            data["bid_size"] = int(snap.latest_quote.bid_size)
            data["ask_price"] = float(snap.latest_quote.ask_price)
            data["ask_size"] = int(snap.latest_quote.ask_size)
        else:
            data["bid_price"] = None
            data["bid_size"] = None
            data["ask_price"] = None
            data["ask_size"] = None

        if hasattr(snap, "daily_bar") and snap.daily_bar:
            data["volume"] = float(snap.daily_bar.volume)
            data["vwap"] = float(snap.daily_bar.vwap) if snap.daily_bar.vwap else None
        else:
            data["volume"] = None
            data["vwap"] = None

        results[ticker] = data

    return results
