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


class CoveredCallMonitor(PatternMonitor):
    """Extended monitor for covered call paper trading.

    Handles:
    - Option chain lookup to find real strike/expiration
    - Sell-to-open order submission
    - Roll detection at DTE threshold
    - Assignment detection near expiration
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        audit: AuditLogger,
        settings: Settings,
        pattern_id: int,
        tickers: list[str] | None = None,
        auto_approve: bool = False,
        shares: int = 100,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ) -> None:
        super().__init__(conn, audit, settings, pattern_id, tickers, auto_approve, poll_interval)
        self.shares = shares
        self.contracts = shares // 100

    def run(self) -> None:
        """Main monitoring loop for covered calls."""
        if not self.tickers:
            from finance_agent.data.watchlist import list_companies
            companies = list_companies(self.conn)
            self.tickers = [c["ticker"] for c in companies]

        if not self.tickers:
            print("Error: No tickers to monitor. Use --tickers or add to watchlist.")
            return

        print(f"Monitoring {len(self.tickers)} tickers for covered call opportunities...")
        print(f"Shares: {self.shares} ({self.contracts} contracts)")
        print(f"Poll interval: {self.poll_interval}s")
        print()

        # For covered calls, immediately propose selling calls (calendar trigger)
        for ticker in self.tickers:
            self._propose_covered_call(ticker)

        # Then monitor for roll/assignment
        while True:
            if get_kill_switch(self.conn):
                print("Kill switch is active — halting monitoring")
                break

            self._check_covered_call_positions()
            time.sleep(self.poll_interval)

    def _find_call_contract(
        self, ticker: str, strike_pct_otm: float, expiration_days: int,
    ) -> dict | None:
        """Find the nearest matching call contract from the option chain.

        Uses Alpaca's option chain API to find:
        - Closest strike to target OTM%
        - Nearest monthly expiration to target days

        Returns dict with contract_symbol, strike, expiration, bid, ask, or None.
        """
        try:
            from alpaca.data.historical.option import OptionHistoricalDataClient
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockLatestBarRequest
            from alpaca.data.enums import DataFeed
        except ImportError:
            logger.error("alpaca-py option support required")
            return None

        # Get current stock price
        stock_client = StockHistoricalDataClient(
            self.settings.active_api_key,
            self.settings.active_secret_key,
        )
        try:
            bar_resp = stock_client.get_stock_latest_bar(
                StockLatestBarRequest(symbol_or_symbols=ticker, feed=DataFeed.IEX)
            )
            if ticker not in bar_resp:
                return None
            current_price = float(bar_resp[ticker].close)
        except Exception as e:
            logger.error("Failed to get stock price for %s: %s", ticker, e)
            return None

        target_strike = current_price * (1 + strike_pct_otm)

        # Try to get option chain from Alpaca
        try:
            option_client = OptionHistoricalDataClient(
                self.settings.active_api_key,
                self.settings.active_secret_key,
            )

            from alpaca.data.requests import OptionChainRequest
            from datetime import timedelta

            target_expiry = datetime.now(UTC) + timedelta(days=expiration_days)

            request = OptionChainRequest(
                underlying_symbol=ticker,
                expiration_date_gte=target_expiry.strftime("%Y-%m-%d"),
                expiration_date_lte=(target_expiry + timedelta(days=14)).strftime("%Y-%m-%d"),
                strike_price_gte=str(round(target_strike - 5, 0)),
                strike_price_lte=str(round(target_strike + 5, 0)),
                type="call",
            )

            chain = option_client.get_option_chain(request)

            if not chain:
                logger.warning("No option chain data for %s", ticker)
                return self._estimate_contract(ticker, current_price, target_strike, expiration_days)

            # Find closest match
            best_match = None
            best_diff = float("inf")

            for symbol, snapshots in chain.items():
                # Parse strike from symbol
                snapshot = snapshots[-1] if isinstance(snapshots, list) else snapshots
                strike = float(getattr(snapshot, "strike_price", target_strike))
                diff = abs(strike - target_strike)
                if diff < best_diff:
                    best_diff = diff
                    bid = float(getattr(snapshot, "bid_price", 0))
                    ask = float(getattr(snapshot, "ask_price", 0))
                    exp = getattr(snapshot, "expiration_date", target_expiry.strftime("%Y-%m-%d"))
                    best_match = {
                        "contract_symbol": symbol,
                        "strike": strike,
                        "expiration": str(exp),
                        "bid": bid,
                        "ask": ask,
                        "mid": (bid + ask) / 2 if bid and ask else 0,
                        "current_price": current_price,
                    }

            return best_match

        except Exception as e:
            logger.warning("Option chain lookup failed for %s: %s — using estimate", ticker, e)
            return self._estimate_contract(ticker, current_price, target_strike, expiration_days)

    def _estimate_contract(
        self, ticker: str, current_price: float, target_strike: float, expiration_days: int,
    ) -> dict:
        """Fallback: estimate premium when option chain is unavailable."""
        from finance_agent.patterns.option_pricing import estimate_call_premium

        premium = estimate_call_premium(
            spot_price=current_price,
            strike_price=target_strike,
            days_to_expiration=expiration_days,
            historical_volatility=0.25,  # Default estimate
        )

        from datetime import timedelta as td
        target_expiry = datetime.now(UTC) + td(days=expiration_days)
        return {
            "contract_symbol": f"{ticker}_estimated",
            "strike": round(target_strike, 2),
            "expiration": target_expiry.strftime("%Y-%m-%d"),
            "bid": round(premium * 0.95, 2),
            "ask": round(premium * 1.05, 2),
            "mid": round(premium, 2),
            "current_price": current_price,
            "estimated": True,
        }

    def _propose_covered_call(self, ticker: str) -> None:
        """Propose selling a covered call for the given ticker."""
        action = self.rule_set.action

        # Get OTM percentage
        strike_pct_otm = 0.05  # default
        if action.strike_strategy.value == "otm_5":
            strike_pct_otm = 0.05
        elif action.strike_strategy.value == "otm_10":
            strike_pct_otm = 0.10
        elif action.strike_strategy.value == "custom" and action.custom_strike_offset_pct:
            strike_pct_otm = action.custom_strike_offset_pct / 100.0

        contract = self._find_call_contract(ticker, strike_pct_otm, action.expiration_days)
        if not contract:
            print(f"  Could not find option contract for {ticker}")
            return

        estimated_premium = contract["mid"] * self.contracts * 100
        max_profit = estimated_premium + (contract["strike"] - contract["current_price"]) * self.shares

        print(f"\nPROPOSE: Sell {self.contracts}x {ticker} {contract['expiration']} ${contract['strike']:.0f} Call @ ${contract['mid']:.2f}")
        print(f"  Estimated premium: ${estimated_premium:,.2f}")
        print(f"  Max profit: ${max_profit:,.2f} (premium + stock gain to strike)")
        if contract.get("estimated"):
            print(f"  NOTE: Premium is estimated (option chain unavailable)")

        option_details = {
            "type": "sell_call",
            "contract_symbol": contract["contract_symbol"],
            "strike": contract["strike"],
            "expiration": contract["expiration"],
            "premium_per_share": contract["mid"],
            "estimated": contract.get("estimated", False),
        }

        trade_id = create_paper_trade(
            self.conn,
            self.pattern_id,
            ticker,
            "sell",
            "sell_call",
            self.contracts,
            option_details,
        )

        self.audit.log("covered_call_proposed", "pattern_lab", {
            "pattern_id": self.pattern_id,
            "trade_id": trade_id,
            "ticker": ticker,
            "strike": contract["strike"],
            "premium": contract["mid"],
        })

        if self.auto_approve:
            print(f"  Auto-approving trade #{trade_id}...")
            self._execute_covered_call(trade_id, ticker, contract)
        else:
            try:
                choice = input(f"  Approve? [Y/n]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n  Trade cancelled.")
                return

            if choice in ("y", "yes", ""):
                self._execute_covered_call(trade_id, ticker, contract)
            else:
                print("  Trade cancelled.")

    def _execute_covered_call(self, trade_id: int, ticker: str, contract: dict) -> None:
        """Execute a covered call sell-to-open via Alpaca."""
        if contract.get("estimated"):
            # Can't submit estimated contracts — mark as simulated execution
            premium = contract["mid"]
            update_paper_trade_executed(self.conn, trade_id, "simulated", premium)
            print(f"  Trade #{trade_id} simulated (no real contract available)")
            self.audit.log("covered_call_sold", "pattern_lab", {
                "trade_id": trade_id,
                "ticker": ticker,
                "simulated": True,
            })
            return

        try:
            from alpaca.trading.client import TradingClient
            from alpaca.trading.requests import LimitOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce
        except ImportError:
            logger.error("alpaca-py required for trade execution")
            return

        client = TradingClient(
            self.settings.active_api_key,
            self.settings.active_secret_key,
            paper=not self.settings.is_live,
        )

        try:
            # Submit sell-to-open order for the call contract
            order_request = LimitOrderRequest(
                symbol=contract["contract_symbol"],
                qty=self.contracts,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
                limit_price=contract["bid"],  # Sell at bid
            )
            order = client.submit_order(order_request)
            entry_price = float(order.filled_avg_price) if order.filled_avg_price else contract["mid"]
            update_paper_trade_executed(self.conn, trade_id, str(order.id), entry_price)
            print(f"  Trade #{trade_id} executed: order {order.id}")

            self.audit.log("covered_call_sold", "pattern_lab", {
                "trade_id": trade_id,
                "order_id": str(order.id),
                "ticker": ticker,
                "premium": entry_price,
            })
        except Exception as e:
            logger.error("Covered call execution failed: %s", e)
            print(f"  Trade execution failed: {e}")

    def _check_covered_call_positions(self) -> None:
        """Check open covered call trades for roll or assignment conditions."""
        from finance_agent.patterns.storage import get_paper_trades

        open_trades = get_paper_trades(self.conn, self.pattern_id, status="executed")
        exit_criteria = self.rule_set.exit_criteria
        action = self.rule_set.action
        roll_threshold_dte = action.expiration_days - (exit_criteria.max_hold_days or action.expiration_days)
        if roll_threshold_dte <= 0:
            roll_threshold_dte = 21

        for trade in open_trades:
            if trade.get("action_type") != "sell_call":
                continue

            ticker = trade["ticker"]
            option_details = json.loads(trade.get("option_details_json") or "{}")
            expiration_str = option_details.get("expiration")
            strike = option_details.get("strike", 0)

            if not expiration_str:
                continue

            try:
                expiration = datetime.strptime(expiration_str, "%Y-%m-%d")
            except ValueError:
                continue

            now = datetime.now(UTC).replace(tzinfo=None)
            dte = (expiration - now).days

            # Get current stock price
            try:
                from alpaca.data.historical import StockHistoricalDataClient
                from alpaca.data.requests import StockLatestBarRequest
                from alpaca.data.enums import DataFeed

                client = StockHistoricalDataClient(
                    self.settings.active_api_key,
                    self.settings.active_secret_key,
                )
                bar_resp = client.get_stock_latest_bar(
                    StockLatestBarRequest(symbol_or_symbols=ticker, feed=DataFeed.IEX)
                )
                if ticker not in bar_resp:
                    continue
                current_price = float(bar_resp[ticker].close)
            except Exception as e:
                logger.error("Failed to get price for %s: %s", ticker, e)
                continue

            now_str = datetime.now(UTC).strftime("%H:%M:%S")

            # Check for assignment near expiration
            if dte <= 1 and current_price >= strike:
                entry_price = trade.get("entry_price", 0)
                premium_collected = entry_price * self.contracts * 100 if entry_price else 0
                stock_gain = (strike - option_details.get("current_price", current_price)) * self.shares
                total_pnl = premium_collected + stock_gain

                update_paper_trade_closed(self.conn, trade["id"], current_price, total_pnl)
                print(f"\n[{now_str}] ASSIGNED: {ticker} trade #{trade['id']}")
                print(f"  Stock called away at ${strike:.2f}")
                print(f"  Premium collected: ${premium_collected:,.2f}")
                print(f"  Stock gain: ${stock_gain:,.2f}")
                print(f"  Total P&L: ${total_pnl:,.2f}")

                self.audit.log("covered_call_assigned", "pattern_lab", {
                    "trade_id": trade["id"],
                    "ticker": ticker,
                    "strike": strike,
                    "pnl": total_pnl,
                })

            # Check for roll threshold
            elif 0 < dte <= roll_threshold_dte:
                print(f"\n[{now_str}] ROLL ALERT: {ticker} trade #{trade['id']}")
                print(f"  {dte} DTE remaining (roll threshold: {roll_threshold_dte} DTE)")
                print(f"  Current price: ${current_price:.2f} vs Strike: ${strike:.2f}")

                # Look up next month's contract
                next_contract = self._find_call_contract(
                    ticker,
                    (strike / current_price - 1.0) if current_price > 0 else 0.05,
                    action.expiration_days,
                )
                if next_contract:
                    print(f"  Proposed roll: BUY_TO_CLOSE current, SELL_TO_OPEN {next_contract['contract_symbol']}")
                    print(f"  New premium: ${next_contract['mid']:.2f}/share")

                self.audit.log("covered_call_roll_alert", "pattern_lab", {
                    "trade_id": trade["id"],
                    "ticker": ticker,
                    "dte": dte,
                })

            # Check for expiration worthless
            elif dte <= 0 and current_price < strike:
                entry_price = trade.get("entry_price", 0)
                premium_collected = entry_price * self.contracts * 100 if entry_price else 0

                update_paper_trade_closed(self.conn, trade["id"], current_price, premium_collected)
                print(f"\n[{now_str}] EXPIRED WORTHLESS: {ticker} trade #{trade['id']}")
                print(f"  Premium kept: ${premium_collected:,.2f}")

                self.audit.log("covered_call_expired", "pattern_lab", {
                    "trade_id": trade["id"],
                    "ticker": ticker,
                    "premium_kept": premium_collected,
                })


class NewsPatternMonitor(PatternMonitor):
    """Extended monitor for news-driven (qualitative) patterns.

    Requires human confirmation when a price spike is detected,
    since qualitative triggers need human judgment about whether
    the spike was caused by actual news vs. noise.
    """

    def _evaluate_trigger(self, ticker: str) -> bool:
        """Check for price spike + volume matching trigger thresholds."""
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

        from datetime import timedelta
        end = datetime.now(UTC)
        start = end - timedelta(days=30)  # Need 20+ days for volume average

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

        # Calculate price change
        if previous.close <= 0:
            return False
        price_change_pct = ((latest.close - previous.close) / previous.close) * 100

        # Calculate volume multiple vs 20-day average
        lookback_bars = bars[:-1]  # All bars except latest
        if not lookback_bars:
            return False
        avg_volume = sum(b.volume for b in lookback_bars) / len(lookback_bars)
        if avg_volume <= 0:
            return False
        volume_multiple = latest.volume / avg_volume

        # Check thresholds from trigger conditions
        spike_threshold = 5.0
        volume_threshold = 1.5
        for condition in self.rule_set.trigger_conditions:
            if condition.field == "price_change_pct":
                spike_threshold = float(condition.value)
            elif condition.field == "volume_spike":
                volume_threshold = float(condition.value)

        if price_change_pct < spike_threshold or volume_multiple < volume_threshold:
            return False

        # Store trigger details for the confirmation prompt
        self._pending_trigger = {
            "ticker": ticker,
            "prev_price": previous.close,
            "curr_price": latest.close,
            "price_change_pct": price_change_pct,
            "volume": latest.volume,
            "volume_multiple": volume_multiple,
            "date": latest.timestamp.strftime("%Y-%m-%d") if hasattr(latest.timestamp, "strftime") else str(latest.timestamp)[:10],
        }
        return True

    def _propose_trade(self, ticker: str) -> None:
        """Display trigger confirmation prompt before proposing a trade."""
        trigger = getattr(self, "_pending_trigger", None)
        if not trigger:
            return

        # Display confirmation prompt per contracts/cli.md
        print()
        print("\u2550" * 51)
        print(f"  \u26a1 TRIGGER DETECTED: {ticker}")
        print(f"  Price: ${trigger['prev_price']:.2f} \u2192 ${trigger['curr_price']:.2f} (+{trigger['price_change_pct']:.1f}%)")
        print(f"  Volume: {trigger['volume']:,.0f} ({trigger['volume_multiple']:.1f}x average)")
        print(f"  Date: {trigger['date']}")
        print()
        print("  This looks like a significant pharma event.")

        try:
            choice = input("  Confirm this is real news? (y/n/skip): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Skipped.")
            return

        if choice == "y":
            # Confirmed \u2014 proceed to propose trade via parent class
            super()._propose_trade(ticker)
        elif choice == "n":
            # Rejected \u2014 mark as false positive
            now = datetime.now(UTC).strftime("%H:%M:%S")
            print(f"  [{now}] Marked as false positive. Resuming monitoring.")
            self.audit.log("news_trigger_rejected", "pattern_lab", {
                "pattern_id": self.pattern_id,
                "ticker": ticker,
                "price_change_pct": trigger["price_change_pct"],
                "volume_multiple": trigger["volume_multiple"],
            })
        else:
            # Skip \u2014 continue monitoring
            print("  Skipped. Continuing to monitor.")

        print("\u2550" * 51)
        self._pending_trigger = None
