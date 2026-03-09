"""Unit tests for CLI sandbox tasks/log/outreach argparse wiring (022-sfdc-task-logging)."""

from __future__ import annotations

import argparse
from unittest.mock import patch

import pytest

from finance_agent.cli import main


class _CaptureArgs(Exception):
    """Raised to capture the parsed args namespace and abort before side effects."""

    def __init__(self, ns: argparse.Namespace) -> None:
        super().__init__("captured")
        self.ns = ns


def _raise_capture(a: argparse.Namespace) -> None:
    raise _CaptureArgs(a)


def _parse(argv: list[str]) -> argparse.Namespace:
    """Run main() with *argv*, intercept cmd_sandbox to capture parsed args."""
    with patch("finance_agent.cli.cmd_sandbox", side_effect=_raise_capture):
        try:
            main(argv)
        except _CaptureArgs as cap:
            return cap.ns
    pytest.fail("cmd_sandbox was never called — argparse routing failed")


# ---------------------------------------------------------------------------
# sandbox tasks create
# ---------------------------------------------------------------------------


class TestTasksCreate:
    def test_all_flags(self):
        args = _parse([
            "sandbox", "tasks", "create",
            "--client", "Jane", "--subject", "Test", "--due", "2026-03-15", "--priority", "High",
        ])
        assert args.command == "sandbox"
        assert args.sandbox_command == "tasks"
        assert args.tasks_command == "create"
        assert args.client == "Jane"
        assert args.subject == "Test"
        assert args.due == "2026-03-15"
        assert args.priority == "High"

    def test_defaults(self):
        args = _parse([
            "sandbox", "tasks", "create",
            "--client", "Jane", "--subject", "Test",
        ])
        assert args.tasks_command == "create"
        assert args.client == "Jane"
        assert args.subject == "Test"
        assert args.due is None
        assert args.priority == "Normal"


# ---------------------------------------------------------------------------
# sandbox tasks show
# ---------------------------------------------------------------------------


class TestTasksShow:
    def test_no_filters(self):
        args = _parse(["sandbox", "tasks", "show"])
        assert args.tasks_command == "show"
        assert args.overdue is False
        assert args.client is None
        assert args.summary is False

    def test_all_flags(self):
        args = _parse(["sandbox", "tasks", "show", "--overdue", "--client", "Jane", "--summary"])
        assert args.tasks_command == "show"
        assert args.overdue is True
        assert args.client == "Jane"
        assert args.summary is True


# ---------------------------------------------------------------------------
# sandbox tasks complete
# ---------------------------------------------------------------------------


class TestTasksComplete:
    def test_positional_subject(self):
        args = _parse(["sandbox", "tasks", "complete", "Review portfolio"])
        assert args.tasks_command == "complete"
        assert args.subject == "Review portfolio"


# ---------------------------------------------------------------------------
# sandbox log
# ---------------------------------------------------------------------------


class TestLog:
    def test_required_flags(self):
        args = _parse([
            "sandbox", "log",
            "--client", "Jane", "--subject", "Call", "--type", "call",
        ])
        assert args.sandbox_command == "log"
        assert args.client == "Jane"
        assert args.subject == "Call"
        assert args.activity_type == "call"
        assert args.activity_date is None

    def test_with_date(self):
        args = _parse([
            "sandbox", "log",
            "--client", "Jane", "--subject", "Meeting", "--type", "meeting", "--date", "2026-03-07",
        ])
        assert args.sandbox_command == "log"
        assert args.activity_type == "meeting"
        assert args.activity_date == "2026-03-07"


# ---------------------------------------------------------------------------
# sandbox outreach
# ---------------------------------------------------------------------------


class TestOutreach:
    def test_required_days(self):
        args = _parse(["sandbox", "outreach", "--days", "90"])
        assert args.sandbox_command == "outreach"
        assert args.days == 90
        assert args.min_value == 0
        assert args.create_tasks is False

    def test_all_flags(self):
        args = _parse(["sandbox", "outreach", "--days", "90", "--min-value", "250000", "--create-tasks"])
        assert args.sandbox_command == "outreach"
        assert args.days == 90
        assert args.min_value == 250000.0
        assert args.create_tasks is True
