"""Unit tests for scan schedule management and market hours detection."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from finance_agent.scheduling.scan_schedule import (
    PLIST_LABEL,
    PLIST_PATH,
    is_market_open,
)

ET = ZoneInfo("America/New_York")


class TestIsMarketOpen:
    """Tests for is_market_open()."""

    def test_weekday_during_market_hours(self):
        # Wednesday 2026-03-04 at 10:00 ET
        dt = datetime(2026, 3, 4, 10, 0, tzinfo=ET)
        assert is_market_open(dt) is True

    def test_weekday_at_open(self):
        # Monday at exactly 9:30 ET
        dt = datetime(2026, 3, 2, 9, 30, tzinfo=ET)
        assert is_market_open(dt) is True

    def test_weekday_just_before_open(self):
        # Monday at 9:29 ET
        dt = datetime(2026, 3, 2, 9, 29, tzinfo=ET)
        assert is_market_open(dt) is False

    def test_weekday_at_close(self):
        # Monday at exactly 16:00 ET — market is closed
        dt = datetime(2026, 3, 2, 16, 0, tzinfo=ET)
        assert is_market_open(dt) is False

    def test_weekday_just_before_close(self):
        # Monday at 15:59 ET
        dt = datetime(2026, 3, 2, 15, 59, tzinfo=ET)
        assert is_market_open(dt) is True

    def test_weekday_after_close(self):
        # Wednesday at 17:00 ET
        dt = datetime(2026, 3, 4, 17, 0, tzinfo=ET)
        assert is_market_open(dt) is False

    def test_saturday(self):
        # Saturday 2026-03-07 at 12:00 ET
        dt = datetime(2026, 3, 7, 12, 0, tzinfo=ET)
        assert is_market_open(dt) is False

    def test_sunday(self):
        # Sunday 2026-03-08 at 12:00 ET
        dt = datetime(2026, 3, 8, 12, 0, tzinfo=ET)
        assert is_market_open(dt) is False

    def test_us_holiday_new_years(self):
        # Thursday 2026-01-01 (New Year's Day) at 12:00 ET
        dt = datetime(2026, 1, 1, 12, 0, tzinfo=ET)
        assert is_market_open(dt) is False

    def test_us_holiday_thanksgiving(self):
        # Thursday 2026-11-26 (Thanksgiving) at 12:00 ET
        dt = datetime(2026, 11, 26, 12, 0, tzinfo=ET)
        assert is_market_open(dt) is False

    def test_timezone_conversion_from_utc(self):
        # 2026-03-04 15:00 UTC = 10:00 ET (market open)
        dt = datetime(2026, 3, 4, 15, 0, tzinfo=ZoneInfo("UTC"))
        assert is_market_open(dt) is True

    def test_timezone_conversion_from_pacific(self):
        # 2026-03-04 07:00 PT = 10:00 ET (market open)
        dt = datetime(2026, 3, 4, 7, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
        assert is_market_open(dt) is True

    def test_naive_datetime_treated_as_et(self):
        # Naive datetime at 10:00 on a Wednesday — treated as ET
        dt = datetime(2026, 3, 4, 10, 0)
        assert is_market_open(dt) is True


class TestInstallScanSchedule:
    """Tests for schedule install/management with mocked subprocess."""

    @patch("finance_agent.scheduling.scan_schedule.platform")
    @patch("finance_agent.scheduling.scan_schedule.subprocess")
    @patch("finance_agent.scheduling.scan_schedule.PLIST_PATH")
    def test_install_launchd_creates_plist(self, mock_path, mock_subprocess, mock_platform):
        from finance_agent.scheduling.scan_schedule import install_scan_schedule

        mock_platform.system.return_value = "Darwin"
        mock_path.exists.return_value = False
        mock_path.parent.mkdir = MagicMock()
        mock_path.__str__ = lambda self: "/Users/test/Library/LaunchAgents/com.advisor-agent.scanner.plist"

        # Mock open for plist writing
        mock_subprocess.run.return_value = MagicMock(returncode=0, stderr="")

        with patch("builtins.open", MagicMock()):
            result = install_scan_schedule(15, cooldown_hours=24)

        assert result["status"] == "active"

    @patch("finance_agent.scheduling.scan_schedule.platform")
    @patch("finance_agent.scheduling.scan_schedule.subprocess")
    @patch("finance_agent.scheduling.scan_schedule.PLIST_PATH")
    def test_get_schedule_no_plist(self, mock_path, mock_subprocess, mock_platform):
        from finance_agent.scheduling.scan_schedule import get_scan_schedule

        mock_platform.system.return_value = "Darwin"
        mock_path.exists.return_value = False

        result = get_scan_schedule()
        assert result is None

    @patch("finance_agent.scheduling.scan_schedule.platform")
    @patch("finance_agent.scheduling.scan_schedule.subprocess")
    @patch("finance_agent.scheduling.scan_schedule.PLIST_PATH")
    def test_pause_unloads_launchd(self, mock_path, mock_subprocess, mock_platform):
        from finance_agent.scheduling.scan_schedule import pause_scan_schedule

        mock_platform.system.return_value = "Darwin"
        mock_path.exists.return_value = True
        mock_path.__str__ = lambda self: "/tmp/test.plist"
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        assert pause_scan_schedule() is True
        mock_subprocess.run.assert_called_once()

    @patch("finance_agent.scheduling.scan_schedule.platform")
    @patch("finance_agent.scheduling.scan_schedule.subprocess")
    @patch("finance_agent.scheduling.scan_schedule.PLIST_PATH")
    def test_resume_loads_launchd(self, mock_path, mock_subprocess, mock_platform):
        from finance_agent.scheduling.scan_schedule import resume_scan_schedule

        mock_platform.system.return_value = "Darwin"
        mock_path.exists.return_value = True
        mock_path.__str__ = lambda self: "/tmp/test.plist"
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        assert resume_scan_schedule() is True

    @patch("finance_agent.scheduling.scan_schedule.platform")
    @patch("finance_agent.scheduling.scan_schedule.subprocess")
    @patch("finance_agent.scheduling.scan_schedule.PLIST_PATH")
    def test_remove_deletes_plist(self, mock_path, mock_subprocess, mock_platform):
        from finance_agent.scheduling.scan_schedule import remove_scan_schedule

        mock_platform.system.return_value = "Darwin"
        mock_path.exists.return_value = True
        mock_path.__str__ = lambda self: "/tmp/test.plist"
        mock_path.unlink = MagicMock()
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        assert remove_scan_schedule() is True
        mock_path.unlink.assert_called_once_with(missing_ok=True)

    @patch("finance_agent.scheduling.scan_schedule.platform")
    @patch("finance_agent.scheduling.scan_schedule.PLIST_PATH")
    def test_remove_no_plist_returns_false(self, mock_path, mock_platform):
        from finance_agent.scheduling.scan_schedule import remove_scan_schedule

        mock_platform.system.return_value = "Darwin"
        mock_path.exists.return_value = False

        assert remove_scan_schedule() is False

    @patch("finance_agent.scheduling.scan_schedule.platform")
    @patch("finance_agent.scheduling.scan_schedule.PLIST_PATH")
    def test_pause_no_plist_returns_false(self, mock_path, mock_platform):
        from finance_agent.scheduling.scan_schedule import pause_scan_schedule

        mock_platform.system.return_value = "Darwin"
        mock_path.exists.return_value = False

        assert pause_scan_schedule() is False
