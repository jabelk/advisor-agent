"""Integration test for the health command against paper trading API.

Requires ALPACA_PAPER_API_KEY and ALPACA_PAPER_SECRET_KEY in environment.
"""

from __future__ import annotations

import os
import subprocess

import pytest

# Skip if no API keys configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("ALPACA_PAPER_API_KEY") or not os.environ.get("ALPACA_PAPER_SECRET_KEY"),
    reason="Paper trading API keys not configured",
)


class TestHealthCommand:
    """Integration tests for finance-agent health."""

    def test_health_succeeds_with_paper_keys(self) -> None:
        result = subprocess.run(
            ["uv", "run", "finance-agent", "health"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "[PAPER MODE]" in result.stdout
        assert "Configuration: OK" in result.stdout
        assert "Database: OK" in result.stdout
        assert "Broker API: OK" in result.stdout

    def test_health_shows_version(self) -> None:
        result = subprocess.run(
            ["uv", "run", "finance-agent", "health"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert "Finance Agent v" in result.stdout

    def test_version_command(self) -> None:
        result = subprocess.run(
            ["uv", "run", "finance-agent", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "finance-agent" in result.stdout
