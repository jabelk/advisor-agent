"""Unit tests for finance_agent.patterns.event_detection."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from finance_agent.patterns.event_detection import (
    detect_spike_events,
    manual_events_to_detected,
    parse_events_file,
    parse_manual_events,
)
from finance_agent.patterns.models import (
    DetectedEvent,
    EventDetectionConfig,
    ManualEvent,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_bars(
    n: int,
    base_price: float = 100.0,
    base_volume: int = 1_000_000,
) -> list[dict]:
    """Generate *n* bars with stable prices and volumes starting from 2024-01-01.

    Each bar has keys: close, high, low, volume, bar_timestamp.
    Prices stay at *base_price* and volume stays at *base_volume* so that
    tests can surgically modify individual bars to create spikes.
    """
    start = datetime(2024, 1, 1)
    bars: list[dict] = []
    for i in range(n):
        date = start + timedelta(days=i)
        bars.append({
            "close": base_price,
            "high": base_price + 1.0,
            "low": base_price - 1.0,
            "volume": base_volume,
            "bar_timestamp": date.strftime("%Y-%m-%dT00:00:00Z"),
        })
    return bars


# ---------------------------------------------------------------------------
# detect_spike_events
# ---------------------------------------------------------------------------

class TestDetectSpikeEvents:
    """Tests for detect_spike_events."""

    def test_detect_spike_basic(self):
        """One day with +6% price change AND 2x volume should produce 1 event."""
        bars = _make_bars(30)
        # Day 25: +6% close-over-close and 2x average volume
        bars[25]["close"] = bars[24]["close"] * 1.06
        bars[25]["high"] = bars[25]["close"] + 1.0
        bars[25]["volume"] = 2_000_000  # 2x the base

        config = EventDetectionConfig(
            spike_threshold_pct=5.0,
            volume_multiple_min=1.5,
        )
        events = detect_spike_events(bars, "TEST", config)

        assert len(events) == 1
        event = events[0]
        assert event.ticker == "TEST"
        assert event.source == "proxy"
        assert event.price_change_pct == pytest.approx(6.0, abs=0.1)
        assert event.volume_multiple >= 1.5

    def test_detect_spike_volume_filter(self):
        """Price spikes 6% but volume is only 1.2x average -- below 1.5x threshold."""
        bars = _make_bars(30)
        bars[25]["close"] = bars[24]["close"] * 1.06
        bars[25]["high"] = bars[25]["close"] + 1.0
        bars[25]["volume"] = 1_200_000  # only 1.2x

        config = EventDetectionConfig(
            spike_threshold_pct=5.0,
            volume_multiple_min=1.5,
        )
        events = detect_spike_events(bars, "TEST", config)

        assert len(events) == 0

    def test_detect_spike_cooldown(self):
        """Two consecutive spike days should only detect the first (cooldown active)."""
        bars = _make_bars(30)
        # Day 22: +6% with high volume
        bars[22]["close"] = bars[21]["close"] * 1.06
        bars[22]["high"] = bars[22]["close"] + 1.0
        bars[22]["volume"] = 3_000_000

        # Day 23: +8% with high volume (should be suppressed by cooldown)
        bars[23]["close"] = bars[22]["close"] * 1.08
        bars[23]["high"] = bars[23]["close"] + 1.0
        bars[23]["volume"] = 4_000_000

        config = EventDetectionConfig(
            spike_threshold_pct=5.0,
            volume_multiple_min=1.5,
            entry_window_days=2,
        )
        events = detect_spike_events(bars, "TEST", config)

        assert len(events) == 1
        assert events[0].date == bars[22]["bar_timestamp"][:10]

    def test_detect_spike_no_events(self):
        """All bars have <3% daily changes -- no events."""
        bars = _make_bars(30)
        # Slight variation -- nothing over 3%
        for i in range(1, len(bars)):
            bars[i]["close"] = bars[i - 1]["close"] * 1.02  # 2% increase

        config = EventDetectionConfig(
            spike_threshold_pct=5.0,
            volume_multiple_min=1.5,
        )
        events = detect_spike_events(bars, "TEST", config)

        assert len(events) == 0

    def test_detect_spike_insufficient_data(self):
        """Fewer bars than volume_lookback_days + 1 should return empty list."""
        bars = _make_bars(5)

        config = EventDetectionConfig(
            spike_threshold_pct=5.0,
            volume_multiple_min=1.5,
            volume_lookback_days=20,
        )
        events = detect_spike_events(bars, "TEST", config)

        assert events == []


# ---------------------------------------------------------------------------
# parse_manual_events
# ---------------------------------------------------------------------------

class TestParseManualEvents:
    """Tests for parse_manual_events."""

    def test_parse_manual_valid(self):
        """Comma-separated valid dates should produce ManualEvent objects."""
        events = parse_manual_events("2024-08-15,2024-11-02")

        assert len(events) == 2
        assert events[0].date == "2024-08-15"
        assert events[1].date == "2024-11-02"
        assert all(isinstance(e, ManualEvent) for e in events)

    def test_parse_manual_invalid_date(self):
        """Invalid date should raise ValueError mentioning 'Invalid date format'."""
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_manual_events("2024-13-45")

    def test_parse_manual_empty(self):
        """Empty string should return empty list."""
        assert parse_manual_events("") == []


# ---------------------------------------------------------------------------
# parse_events_file
# ---------------------------------------------------------------------------

class TestParseEventsFile:
    """Tests for parse_events_file."""

    def test_parse_file_valid(self, tmp_path):
        """File with date,label and bare date lines should parse correctly."""
        f = tmp_path / "events.csv"
        f.write_text("2024-08-15,FDA approval\n2024-11-02\n")

        events = parse_events_file(str(f))

        assert len(events) == 2
        assert events[0].date == "2024-08-15"
        assert events[0].label == "FDA approval"
        assert events[1].date == "2024-11-02"
        assert events[1].label is None

    def test_parse_file_comments_blanks(self, tmp_path):
        """Comments and blank lines should be skipped."""
        f = tmp_path / "events.csv"
        f.write_text("# comment\n\n2024-08-15\n# another\n2024-11-02\n")

        events = parse_events_file(str(f))

        assert len(events) == 2
        assert events[0].date == "2024-08-15"
        assert events[1].date == "2024-11-02"

    def test_parse_file_not_found(self):
        """Non-existent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_events_file("nonexistent.csv")

    def test_parse_file_labels_parsed(self, tmp_path):
        """Labels should be correctly populated from the file."""
        f = tmp_path / "events.csv"
        f.write_text("2024-03-01,Phase 3 trial results\n2024-06-15,Earnings beat\n")

        events = parse_events_file(str(f))

        assert len(events) == 2
        assert events[0].label == "Phase 3 trial results"
        assert events[1].label == "Earnings beat"


# ---------------------------------------------------------------------------
# manual_events_to_detected
# ---------------------------------------------------------------------------

class TestManualEventsToDetected:
    """Tests for manual_events_to_detected."""

    def test_manual_to_detected_basic(self):
        """ManualEvent for a date that exists in bars should produce a DetectedEvent."""
        bars = _make_bars(30)
        # Pick a date that exists in our synthetic bars (day index 10 = 2024-01-11)
        target_date = "2024-01-11"
        bars[10]["close"] = 105.0
        bars[10]["high"] = 107.0

        manual_events = [ManualEvent(date=target_date, label="Test event")]

        events = manual_events_to_detected(manual_events, bars, "TEST")

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, DetectedEvent)
        assert event.source == "manual"
        assert event.date == target_date
        assert event.close_price == 105.0
        assert event.high_price == 107.0
        assert event.event_label == "Test event"
        assert event.ticker == "TEST"
