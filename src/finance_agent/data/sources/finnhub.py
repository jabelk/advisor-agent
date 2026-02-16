"""Finnhub market signals ingestion via free-tier API endpoints."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

from finance_agent.data.models import SourceDocumentMeta
from finance_agent.data.sources import BaseSource
from finance_agent.data.storage import StorageManager
from finance_agent.research.signals import check_document_exists

logger = logging.getLogger(__name__)


class FinnhubMarketSource(BaseSource):
    """Ingest market signals from Finnhub free-tier endpoints."""

    @property
    def name(self) -> str:
        return "finnhub"

    def __init__(self, storage: StorageManager, api_key: str) -> None:
        self.storage = storage
        self.api_key = api_key

    def _get_client(self) -> Any:
        import finnhub

        return finnhub.Client(api_key=self.api_key)

    def ingest(
        self,
        conn: sqlite3.Connection,
        watchlist: list[dict[str, str | int]],
        since_date: str | None = None,
    ) -> list[SourceDocumentMeta]:
        client = self._get_client()
        documents: list[SourceDocumentMeta] = []
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        for company in watchlist:
            ticker = str(company["ticker"])

            # Each endpoint produces a separate document
            endpoints: list[tuple[str, str, str]] = [
                ("recommendation_trends", "analyst_ratings", "finnhub_data"),
                ("company_earnings", "earnings_history", "finnhub_data"),
                ("insider_transactions", "insider_activity", "finnhub_data"),
                ("insider_sentiment", "insider_sentiment", "finnhub_data"),
                ("company_news", "company_news", "finnhub_data"),
            ]

            for endpoint_name, content_type, source_type in endpoints:
                source_id = f"finnhub:{ticker}:{endpoint_name}:{today}"

                if check_document_exists(conn, source_type, source_id):
                    logger.debug("Skipping already ingested: %s", source_id)
                    continue

                try:
                    data = self._fetch_endpoint(client, endpoint_name, ticker, today)
                    if data is None or (isinstance(data, list) and len(data) == 0):
                        logger.debug("No data for %s/%s", ticker, endpoint_name)
                        continue

                    content = self._format_endpoint_data(
                        endpoint_name, data, ticker, today
                    )

                    # Persist raw JSON
                    raw_json = json.dumps(data, indent=2, default=str)
                    filename = f"{ticker}_{endpoint_name}_{today}.json"
                    self.storage.persist_document(
                        source_type=source_type,
                        content=raw_json,
                        filename=filename,
                        ticker=ticker,
                        content_type=content_type,
                    )

                    title = f"{ticker} {_endpoint_label(endpoint_name)} ({today})"
                    published_at = f"{today}T00:00:00Z"

                    doc = SourceDocumentMeta(
                        source_type=source_type,
                        content_type=content_type,
                        source_id=source_id,
                        title=title,
                        published_at=published_at,
                        content=content,
                        company_ticker=ticker,
                        metadata={"endpoint": endpoint_name, "date": today},
                    )
                    documents.append(doc)
                    logger.info("Ingested %s for %s", endpoint_name, ticker)

                except Exception as e:
                    logger.warning(
                        "Failed %s for %s: %s", endpoint_name, ticker, e
                    )
                    continue

        return documents

    def _fetch_endpoint(
        self, client: Any, endpoint: str, ticker: str, today: str
    ) -> Any:
        """Fetch data from a specific Finnhub endpoint."""
        if endpoint == "recommendation_trends":
            return client.recommendation_trends(ticker)
        elif endpoint == "company_earnings":
            return client.company_earnings(ticker, limit=8)
        elif endpoint == "insider_transactions":
            from_date = (datetime.now(UTC) - timedelta(days=90)).strftime("%Y-%m-%d")
            result = client.stock_insider_transactions(ticker, from_date, today)
            return result.get("data", []) if isinstance(result, dict) else result
        elif endpoint == "insider_sentiment":
            from_date = (datetime.now(UTC) - timedelta(days=365)).strftime("%Y-%m-%d")
            result = client.stock_insider_sentiment(ticker, from_date, today)
            return result.get("data", []) if isinstance(result, dict) else result
        elif endpoint == "company_news":
            from_date = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
            return client.company_news(ticker, _from=from_date, to=today)
        return None

    @staticmethod
    def _format_endpoint_data(
        endpoint: str, data: Any, ticker: str, date: str
    ) -> str:
        """Format endpoint data into readable markdown."""
        if endpoint == "recommendation_trends":
            return _format_analyst_ratings(data, ticker, date)
        elif endpoint == "company_earnings":
            return _format_earnings_history(data, ticker)
        elif endpoint == "insider_transactions":
            return _format_insider_activity(data, ticker)
        elif endpoint == "insider_sentiment":
            return _format_insider_sentiment(data, ticker)
        elif endpoint == "company_news":
            return _format_company_news(data, ticker, date)
        return json.dumps(data, indent=2, default=str)


def _endpoint_label(endpoint: str) -> str:
    """Human-readable label for an endpoint."""
    labels = {
        "recommendation_trends": "Analyst Ratings",
        "company_earnings": "Earnings History",
        "insider_transactions": "Insider Activity",
        "insider_sentiment": "Insider Sentiment",
        "company_news": "Company News",
    }
    return labels.get(endpoint, endpoint)


def _format_analyst_ratings(data: list[dict[str, Any]], ticker: str, date: str) -> str:
    """Format analyst recommendation trends."""
    lines = [f"# {ticker} Analyst Ratings (as of {date})", ""]

    if not data:
        lines.append("No analyst ratings available.")
        return "\n".join(lines)

    lines.append("| Period | Strong Buy | Buy | Hold | Sell | Strong Sell |")
    lines.append("|--------|-----------|-----|------|------|-------------|")

    for entry in data[:6]:
        period = entry.get("period", "?")
        sb = entry.get("strongBuy", 0)
        b = entry.get("buy", 0)
        h = entry.get("hold", 0)
        s = entry.get("sell", 0)
        ss = entry.get("strongSell", 0)
        lines.append(f"| {period} | {sb} | {b} | {h} | {s} | {ss} |")

    # Summary of latest
    if data:
        latest = data[0]
        total = sum(
            latest.get(k, 0)
            for k in ["strongBuy", "buy", "hold", "sell", "strongSell"]
        )
        bullish = latest.get("strongBuy", 0) + latest.get("buy", 0)
        bearish = latest.get("sell", 0) + latest.get("strongSell", 0)
        lines.append("")
        lines.append(
            f"**Latest consensus**: {bullish} bullish, "
            f"{latest.get('hold', 0)} hold, {bearish} bearish "
            f"(out of {total} analysts)"
        )

    return "\n".join(lines)


def _format_earnings_history(data: list[dict[str, Any]], ticker: str) -> str:
    """Format earnings beat/miss history."""
    lines = [f"# {ticker} Earnings History (Last {len(data)} Quarters)", ""]

    if not data:
        lines.append("No earnings data available.")
        return "\n".join(lines)

    lines.append("| Period | Actual EPS | Estimate EPS | Surprise | Surprise % |")
    lines.append("|--------|-----------|-------------|----------|-----------|")

    beats = 0
    misses = 0
    for entry in data:
        period = entry.get("period", "?")
        actual = entry.get("actual", "N/A")
        estimate = entry.get("estimate", "N/A")
        surprise = entry.get("surprise", "N/A")
        surprise_pct = entry.get("surprisePercent", "N/A")
        if isinstance(surprise_pct, (int, float)):
            surprise_pct_str = f"{surprise_pct:+.1f}%"
            if surprise_pct > 0:
                beats += 1
            elif surprise_pct < 0:
                misses += 1
        else:
            surprise_pct_str = str(surprise_pct)
        lines.append(
            f"| {period} | {actual} | {estimate} | {surprise} | {surprise_pct_str} |"
        )

    lines.append("")
    lines.append(
        f"**Track record**: {beats} beats, {misses} misses "
        f"out of {len(data)} quarters"
    )

    return "\n".join(lines)


def _format_insider_activity(data: list[dict[str, Any]], ticker: str) -> str:
    """Format insider transaction activity."""
    lines = [f"# {ticker} Insider Transactions (Last 90 Days)", ""]

    if not data:
        lines.append("No insider transactions in this period.")
        return "\n".join(lines)

    total_buys = 0
    total_sells = 0
    buy_value = 0.0
    sell_value = 0.0

    lines.append("| Date | Name | Transaction | Shares | Value |")
    lines.append("|------|------|-------------|--------|-------|")

    for txn in data[:20]:  # Limit to 20 most recent
        date = txn.get("transactionDate", "?")
        name = txn.get("name", "Unknown")
        change = txn.get("change", 0)
        price = txn.get("transactionPrice", 0)
        value = abs(change * price) if change and price else 0

        if change > 0:
            txn_type = "BUY"
            total_buys += 1
            buy_value += value
        else:
            txn_type = "SELL"
            total_sells += 1
            sell_value += value

        value_str = f"${value:,.0f}" if value else "N/A"
        lines.append(
            f"| {date} | {name} | {txn_type} | {abs(change):,.0f} | {value_str} |"
        )

    lines.append("")
    lines.append(
        f"**Summary**: {total_buys} buys (${buy_value:,.0f}), "
        f"{total_sells} sells (${sell_value:,.0f})"
    )

    return "\n".join(lines)


def _format_insider_sentiment(data: list[dict[str, Any]], ticker: str) -> str:
    """Format monthly insider sentiment (MSPR)."""
    lines = [f"# {ticker} Insider Sentiment (Monthly MSPR)", ""]

    if not data:
        lines.append("No insider sentiment data available.")
        return "\n".join(lines)

    lines.append("| Month | Year | MSPR | Change |")
    lines.append("|-------|------|------|--------|")

    for entry in data[:12]:
        month = entry.get("month", "?")
        year = entry.get("year", "?")
        mspr = entry.get("mspr", 0)
        change = entry.get("change", 0)
        lines.append(f"| {month} | {year} | {mspr:.4f} | {change} |")

    # Overall sentiment
    positive = sum(1 for e in data if e.get("mspr", 0) > 0)
    negative = sum(1 for e in data if e.get("mspr", 0) < 0)
    lines.append("")
    lines.append(
        f"**Sentiment**: {positive} positive months, "
        f"{negative} negative months (out of {len(data)})"
    )

    return "\n".join(lines)


def _format_company_news(data: list[dict[str, Any]], ticker: str, date: str) -> str:
    """Format recent company news headlines."""
    lines = [f"# {ticker} Recent News (as of {date})", ""]

    if not data:
        lines.append("No recent news.")
        return "\n".join(lines)

    for i, article in enumerate(data[:15], 1):
        headline = article.get("headline", "No headline")
        source = article.get("source", "Unknown")
        summary = article.get("summary", "")
        dt = article.get("datetime", 0)
        category = article.get("category", "")

        # Convert unix timestamp to date
        if isinstance(dt, (int, float)) and dt > 0:
            from datetime import datetime as dt_cls

            date_str = dt_cls.fromtimestamp(dt, tz=UTC).strftime("%Y-%m-%d %H:%M")
        else:
            date_str = "?"

        lines.append(f"## {i}. {headline}")
        lines.append(f"*{source}* — {date_str}")
        if category:
            lines.append(f"Category: {category}")
        if summary:
            lines.append(f"\n{summary[:500]}")
        lines.append("")

    return "\n".join(lines)
