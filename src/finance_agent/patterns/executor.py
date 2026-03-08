"""Pattern executor: real-time trigger detection and paper trade management."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import UTC, datetime

from finance_agent.audit.logger import AuditLogger
from finance_agent.config import Settings
from finance_agent.patterns.models import RuleSet
from finance_agent.patterns.storage import (
    create_paper_trade,
    get_pattern,
    update_paper_trade_closed,
    update_paper_trade_executed,
)
from finance_agent.safety.guards import get_kill_switch, get_risk_settings

logger = logging.getLogger(__name__)

# Default polling interval in seconds (5 minutes)
DEFAULT_POLL_INTERVAL = 300


class PatternMonitor:
    """Monitors market data for pattern triggers and proposes paper trades."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        audit: AuditLogger,
        settings: Settings,
        pattern_id: int,
        tickers: list[str] | None = None,
        auto_approve: bool = False,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ) -> None:
        self.conn = conn
        self.audit = audit
        self.settings = settings
        self.pattern_id = pattern_id
        self.tickers = tickers
        self.auto_approve = auto_approve
        self.poll_interval = poll_interval

        pattern = get_pattern(conn, pattern_id)
        if not pattern:
            raise ValueError(f"Pattern #{pattern_id} not found")
        self.pattern = pattern
        self.rule_set = RuleSet.model_validate_json(pattern["rule_set_json"])

    def run(self) -> None:
        """Main monitoring loop. Runs until interrupted."""
        if not self.tickers:
            # Use watchlist tickers
            from finance_agent.data.watchlist import list_companies
            companies = list_companies(self.conn)
            self.tickers = [c["ticker"] for c in companies]

        if not self.tickers:
            print("Error: No tickers to monitor. Use --tickers or add to watchlist.")
            return

        print(f"Monitoring {len(self.tickers)} tickers every {self.poll_interval}s...")

        while True:
            # Safety check
            if get_kill_switch(self.conn):
                print("Kill switch is active — halting monitoring")
                break

            self._check_triggers()
            self._check_open_positions()

            time.sleep(self.poll_interval)

    def _check_triggers(self) -> None:
        """Check each ticker for pattern trigger conditions."""
        for ticker in self.tickers or []:
            try:
                triggered = self._evaluate_trigger(ticker)
                if triggered:
                    self._propose_trade(ticker)
            except Exception as e:
                logger.error("Error checking trigger for %s: %s", ticker, e)

    def _evaluate_trigger(self, ticker: str) -> bool:
        """Evaluate trigger conditions against current market data for a ticker."""
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            from alpaca.data.enums import DataFeed
        except ImportError:
            logger.error("alpaca-py required for live monitoring")
            return False

        client = StockHistoricalDataClient(
            self.settings.active_api_key,
            self.settings.active_secret_key,
        )

        # Get last 5 days of data for trigger evaluation
        from datetime import timedelta
        end = datetime.now(UTC)
        start = end - timedelta(days=7)

        request = StockBarsRequest(
            symbol_or_symbols=ticker,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            feed=DataFeed.IEX,
        )

        try:
            response = client.get_stock_bars(request)
        except Exception as e:
            logger.error("Failed to fetch bars for %s: %s", ticker, e)
            return False

        if ticker not in response.data or len(response.data[ticker]) < 2:
            return False

        bars = response.data[ticker]
        latest = bars[-1]
        previous = bars[-2]

        # Check each trigger condition
        for condition in self.rule_set.trigger_conditions:
            if condition.field == "price_change_pct":
                if previous.close == 0:
                    return False
                change_pct = ((latest.close - previous.close) / previous.close) * 100
                threshold = float(condition.value)
                if condition.operator == "gte" and change_pct < threshold:
                    return False
                elif condition.operator == "lte" and change_pct > threshold:
                    return False

            elif condition.field == "volume_spike":
                avg_vol = sum(b.volume for b in bars[:-1]) / max(1, len(bars) - 1)
                if avg_vol == 0:
                    return False
                spike_ratio = latest.volume / avg_vol
                threshold = float(condition.value)
                if condition.operator == "gte" and spike_ratio < threshold:
                    return False

        return True

    def _propose_trade(self, ticker: str) -> None:
        """Create a paper trade proposal for a triggered pattern."""
        # Check safety limits
        risk_settings = get_risk_settings(self.conn)

        # Calculate position size (simplified)
        quantity = 1  # Default to 1 share/contract

        action = self.rule_set.action
        direction = "buy" if "buy" in action.action_type.value else "sell"

        option_details = None
        if "call" in action.action_type.value or "put" in action.action_type.value:
            option_details = {
                "type": action.action_type.value,
                "strike_strategy": action.strike_strategy.value,
                "expiration_days": action.expiration_days,
            }

        trade_id = create_paper_trade(
            self.conn,
            self.pattern_id,
            ticker,
            direction,
            action.action_type.value,
            quantity,
            option_details,
        )

        now = datetime.now(UTC).strftime("%H:%M:%S")
        print(f"\n[{now}] TRIGGER: {ticker} matched pattern #{self.pattern_id}")
        print(f"  Action: {direction} {quantity}x {action.action_type.value}")
        if option_details:
            print(f"  Strike: {action.strike_strategy.value}, Exp: {action.expiration_days} days")

        self.audit.log("paper_trade_proposed", "pattern_lab", {
            "pattern_id": self.pattern_id,
            "trade_id": trade_id,
            "ticker": ticker,
        })

        if self.auto_approve:
            print(f"  Auto-approving trade #{trade_id}...")
            self._execute_trade(trade_id, ticker)
        else:
            try:
                choice = input(f"  Approve trade #{trade_id}? [Y/n]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n  Trade cancelled.")
                return

            if choice in ("y", "yes", ""):
                self._execute_trade(trade_id, ticker)
            else:
                print("  Trade cancelled.")

    def _execute_trade(self, trade_id: int, ticker: str) -> None:
        """Execute a paper trade via Alpaca."""
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce
        except ImportError:
            logger.error("alpaca-py required for trade execution")
            return

        client = TradingClient(
            self.settings.active_api_key,
            self.settings.active_secret_key,
            paper=not self.settings.is_live,
        )

        action = self.rule_set.action
        side = OrderSide.BUY if "buy" in action.action_type.value else OrderSide.SELL

        order_request = MarketOrderRequest(
            symbol=ticker,
            qty=1,
            side=side,
            time_in_force=TimeInForce.DAY,
        )

        try:
            order = client.submit_order(order_request)
            entry_price = float(order.filled_avg_price) if order.filled_avg_price else 0.0
            update_paper_trade_executed(self.conn, trade_id, str(order.id), entry_price)
            print(f"  Trade #{trade_id} executed: order {order.id}")

            self.audit.log("paper_trade_executed", "pattern_lab", {
                "trade_id": trade_id,
                "order_id": str(order.id),
                "ticker": ticker,
                "entry_price": entry_price,
            })
        except Exception as e:
            logger.error("Trade execution failed: %s", e)
            print(f"  Trade execution failed: {e}")

    def _check_open_positions(self) -> None:
        """Check open paper trades for exit conditions."""
        from finance_agent.patterns.storage import get_paper_trades

        open_trades = get_paper_trades(self.conn, self.pattern_id, status="executed")
        exit_criteria = self.rule_set.exit_criteria

        for trade in open_trades:
            entry_price = trade.get("entry_price")
            if not entry_price:
                continue

            ticker = trade["ticker"]

            # Get current price
            try:
                from alpaca.data.historical import StockHistoricalDataClient
                from alpaca.data.requests import StockLatestBarRequest
                from alpaca.data.enums import DataFeed

                client = StockHistoricalDataClient(
                    self.settings.active_api_key,
                    self.settings.active_secret_key,
                )
                request = StockLatestBarRequest(
                    symbol_or_symbols=ticker,
                    feed=DataFeed.IEX,
                )
                response = client.get_stock_latest_bar(request)

                if ticker not in response:
                    continue

                current_price = float(response[ticker].close)
            except Exception as e:
                logger.error("Failed to get current price for %s: %s", ticker, e)
                continue

            # Check profit target / stop loss
            change_pct = ((current_price - entry_price) / entry_price) * 100

            should_close = False
            reason = ""

            if change_pct >= exit_criteria.profit_target_pct:
                should_close = True
                reason = f"profit target ({change_pct:.1f}%)"
            elif change_pct <= -exit_criteria.stop_loss_pct:
                should_close = True
                reason = f"stop loss ({change_pct:.1f}%)"

            if should_close:
                pnl = current_price - entry_price  # Per share/contract
                update_paper_trade_closed(self.conn, trade["id"], current_price, pnl)
                now = datetime.now(UTC).strftime("%H:%M:%S")
                print(f"\n[{now}] CLOSED: {ticker} trade #{trade['id']} — {reason}, P&L: ${pnl:.2f}")

                self.audit.log("paper_trade_closed", "pattern_lab", {
                    "trade_id": trade["id"],
                    "ticker": ticker,
                    "pnl": pnl,
                    "reason": reason,
                })
