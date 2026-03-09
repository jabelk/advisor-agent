"""Event detection for news-driven patterns: spike detection, cooldown, manual event parsing."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from finance_agent.patterns.models import (
    DetectedEvent,
    EventDetectionConfig,
    ManualEvent,
)

logger = logging.getLogger(__name__)


def detect_spike_events(
    bars: list[dict],
    ticker: str,
    config: EventDetectionConfig,
) -> list[DetectedEvent]:
    """Detect price spike events in historical bar data using price-action proxy.

    Scans bars for single-day price increases >= spike_threshold_pct on volume
    >= volume_multiple_min * 20-day average volume. Enforces per-ticker cooldown:
    after a trigger fires, no new triggers until cooldown_days have passed or
    the current trade lifecycle resolves.

    Args:
        bars: Historical price bars sorted by date (list of dicts with close, high, low, volume, bar_timestamp)
        ticker: Stock ticker symbol
        config: Event detection configuration

    Returns:
        List of DetectedEvent objects, sorted by date
    """
    if not bars or len(bars) < config.volume_lookback_days + 1:
        return []

    events: list[DetectedEvent] = []
    cooldown_until: str | None = None  # Date string until which triggers are suppressed

    for i in range(1, len(bars)):
        bar = bars[i]
        prev_bar = bars[i - 1]
        bar_date = bar["bar_timestamp"][:10]

        # Check cooldown
        if cooldown_until and bar_date <= cooldown_until:
            continue

        # Calculate single-day price change
        if prev_bar["close"] <= 0:
            continue
        price_change_pct = ((bar["close"] - prev_bar["close"]) / prev_bar["close"]) * 100

        # Check spike threshold
        if price_change_pct < config.spike_threshold_pct:
            continue

        # Calculate volume multiple vs lookback average
        lookback_start = max(0, i - config.volume_lookback_days)
        lookback_bars = bars[lookback_start:i]
        if not lookback_bars:
            continue
        avg_volume = sum(b["volume"] for b in lookback_bars) / len(lookback_bars)
        if avg_volume <= 0:
            continue
        volume_multiple = bar["volume"] / avg_volume

        # Check volume threshold
        if volume_multiple < config.volume_multiple_min:
            continue

        # Event detected
        events.append(
            DetectedEvent(
                date=bar_date,
                ticker=ticker,
                price_change_pct=round(price_change_pct, 2),
                volume_multiple=round(volume_multiple, 2),
                close_price=bar["close"],
                high_price=bar["high"],
                event_label=None,
                source="proxy",
            )
        )

        # Set cooldown: suppress for entry window days (default 2 trading bars)
        # We look ahead to find the cooldown end date
        cooldown_end_idx = min(i + config.entry_window_days, len(bars) - 1)
        cooldown_until = bars[cooldown_end_idx]["bar_timestamp"][:10]

        logger.info(
            "Spike event detected: %s on %s (%.1f%% price change, %.1fx volume)",
            ticker,
            bar_date,
            price_change_pct,
            volume_multiple,
        )

    return events


def parse_manual_events(events_str: str) -> list[ManualEvent]:
    """Parse comma-separated event dates from CLI --events flag.

    Args:
        events_str: Comma-separated dates, e.g. "2024-08-15,2024-11-02"

    Returns:
        List of ManualEvent objects

    Raises:
        ValueError: If any date is not valid YYYY-MM-DD format
    """
    if not events_str or not events_str.strip():
        return []

    events: list[ManualEvent] = []
    for part in events_str.split(","):
        date_str = part.strip()
        if not date_str:
            continue
        # Validate date format
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.")
        events.append(ManualEvent(date=date_str))

    return events


def parse_events_file(file_path: str) -> list[ManualEvent]:
    """Parse event dates from a file (one per line, optional label).

    File format:
        # Comments start with #
        2024-08-15,FDA approval
        2024-11-02,Phase 3 trial results
        2025-01-20

    Args:
        file_path: Path to events file

    Returns:
        List of ManualEvent objects

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If any date is not valid YYYY-MM-DD format
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Events file not found: {file_path}")

    events: list[ManualEvent] = []
    for line_num, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Split on first comma for date + optional label
        parts = line.split(",", maxsplit=1)
        date_str = parts[0].strip()
        label = parts[1].strip() if len(parts) > 1 else None

        # Validate date
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Invalid date format on line {line_num}: '{date_str}'. Expected YYYY-MM-DD."
            )

        events.append(ManualEvent(date=date_str, label=label))

    if not events:
        raise ValueError(
            f"No valid dates found in {file_path}. Expected one date per line (YYYY-MM-DD)."
        )

    return events


def manual_events_to_detected(
    manual_events: list[ManualEvent],
    bars: list[dict],
    ticker: str,
) -> list[DetectedEvent]:
    """Convert manual event dates to DetectedEvent objects using bar data for prices.

    For each manual event date, finds the matching bar and extracts price/volume data.
    If no bar matches exactly, uses the nearest available bar.

    Args:
        manual_events: User-provided event dates
        bars: Historical price bars
        ticker: Stock ticker symbol

    Returns:
        List of DetectedEvent objects
    """
    if not bars or not manual_events:
        return []

    # Build date->bar lookup
    bar_by_date: dict[str, dict] = {}
    for bar in bars:
        bar_by_date[bar["bar_timestamp"][:10]] = bar

    events: list[DetectedEvent] = []
    for me in manual_events:
        bar = bar_by_date.get(me.date)
        if not bar:
            # Find nearest bar after the event date
            for b in bars:
                if b["bar_timestamp"][:10] >= me.date:
                    bar = b
                    break
        if not bar:
            logger.warning("No bar data found for event date %s, skipping", me.date)
            continue

        # Calculate price change if previous bar exists
        bar_date = bar["bar_timestamp"][:10]
        bar_idx = next((i for i, b in enumerate(bars) if b["bar_timestamp"][:10] == bar_date), None)
        price_change_pct = 0.0
        volume_multiple = 1.0
        if bar_idx is not None and bar_idx > 0:
            prev = bars[bar_idx - 1]
            if prev["close"] > 0:
                price_change_pct = ((bar["close"] - prev["close"]) / prev["close"]) * 100

        events.append(
            DetectedEvent(
                date=bar_date,
                ticker=ticker,
                price_change_pct=round(price_change_pct, 2),
                volume_multiple=round(volume_multiple, 2),
                close_price=bar["close"],
                high_price=bar["high"],
                event_label=me.label,
                source="manual",
            )
        )

    return events
