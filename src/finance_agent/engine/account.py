"""Alpaca TradingClient wrapper for account, positions, and order data."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderStatus, QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest

logger = logging.getLogger(__name__)


def create_trading_client(
    api_key: str, secret_key: str, paper: bool = True
) -> TradingClient:
    """Create and return an Alpaca TradingClient."""
    return TradingClient(api_key=api_key, secret_key=secret_key, paper=paper)


def get_account_summary(client: TradingClient) -> dict[str, float | str]:
    """Fetch account summary with equity, buying power, cash, and last_equity.

    All numeric fields are cast from Optional[str] to float with None guards.
    """
    account = client.get_account()

    def _to_float(val: str | None) -> float:
        if val is None:
            return 0.0
        return float(val)

    equity = _to_float(str(account.equity) if account.equity is not None else None)
    buying_power = _to_float(
        str(account.buying_power) if account.buying_power is not None else None
    )
    cash = _to_float(str(account.cash) if account.cash is not None else None)
    last_equity = _to_float(
        str(account.last_equity) if account.last_equity is not None else None
    )

    return {
        "equity": equity,
        "buying_power": buying_power,
        "cash": cash,
        "last_equity": last_equity,
        "status": str(getattr(account, "status", "UNKNOWN")),
    }


def get_positions(client: TradingClient) -> list[dict[str, float | str | int]]:
    """Fetch all open positions as a list of dicts."""
    positions = client.get_all_positions()
    result = []
    for pos in positions:
        def _to_float(val: str | None) -> float:
            if val is None:
                return 0.0
            return float(val)

        result.append({
            "symbol": str(pos.symbol),
            "qty": int(float(str(pos.qty))) if pos.qty is not None else 0,
            "market_value": _to_float(
                str(pos.market_value) if pos.market_value is not None else None
            ),
            "unrealized_pl": _to_float(
                str(pos.unrealized_pl) if pos.unrealized_pl is not None else None
            ),
            "unrealized_intraday_pl": _to_float(
                str(pos.unrealized_intraday_pl)
                if pos.unrealized_intraday_pl is not None
                else None
            ),
            "current_price": _to_float(
                str(pos.current_price) if pos.current_price is not None else None
            ),
            "avg_entry_price": _to_float(
                str(pos.avg_entry_price) if pos.avg_entry_price is not None else None
            ),
            "side": str(getattr(pos, "side", "long")),
        })
    return result


def get_daily_orders(client: TradingClient) -> int:
    """Get today's filled order count from Alpaca."""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    request = GetOrdersRequest(
        status=QueryOrderStatus.CLOSED,
        after=datetime.strptime(today, "%Y-%m-%d").replace(tzinfo=UTC),
    )
    orders = client.get_orders(filter=request)
    filled = [
        o for o in orders
        if getattr(o, "status", None) == OrderStatus.FILLED
    ]
    return len(filled)


def get_daily_pnl(
    client: TradingClient,
    account_summary: dict[str, float | str] | None = None,
    positions: list[dict[str, float | str | int]] | None = None,
) -> dict[str, float]:
    """Compute daily P&L from account data.

    total_change = equity - last_equity
    unrealized = sum of unrealized_intraday_pl from positions
    realized_estimate = total_change - unrealized
    """
    if account_summary is None:
        account_summary = get_account_summary(client)
    if positions is None:
        positions = get_positions(client)

    equity = float(account_summary["equity"])
    last_equity = float(account_summary["last_equity"])
    total_change = equity - last_equity

    unrealized = sum(float(p["unrealized_intraday_pl"]) for p in positions)
    realized_estimate = total_change - unrealized

    return {
        "total_change": round(total_change, 2),
        "unrealized": round(unrealized, 2),
        "realized_estimate": round(realized_estimate, 2),
    }
