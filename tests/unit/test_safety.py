"""Tests for the safety guardrails module."""

from __future__ import annotations

import sqlite3

import pytest

from finance_agent.safety.guards import (
    DEFAULT_RISK_SETTINGS,
    RISK_SETTING_RANGES,
    get_kill_switch,
    get_risk_settings,
    set_kill_switch,
    update_risk_setting,
)


class TestKillSwitch:
    """Kill switch toggle tests."""

    def test_kill_switch_default_off(self, tmp_db: sqlite3.Connection) -> None:
        """Kill switch should be off by default."""
        assert get_kill_switch(tmp_db) is False

    def test_activate_kill_switch(self, tmp_db: sqlite3.Connection) -> None:
        """Activating kill switch should return True (state changed)."""
        changed = set_kill_switch(tmp_db, active=True)
        assert changed is True
        assert get_kill_switch(tmp_db) is True

    def test_deactivate_kill_switch(self, tmp_db: sqlite3.Connection) -> None:
        """Deactivating an active kill switch should return True."""
        set_kill_switch(tmp_db, active=True)
        changed = set_kill_switch(tmp_db, active=False)
        assert changed is True
        assert get_kill_switch(tmp_db) is False

    def test_no_change_returns_false(self, tmp_db: sqlite3.Connection) -> None:
        """Toggling to same state should return False."""
        assert set_kill_switch(tmp_db, active=False) is False

    def test_kill_switch_records_toggler(self, tmp_db: sqlite3.Connection) -> None:
        """Kill switch should record who toggled it."""
        set_kill_switch(tmp_db, active=True, toggled_by="test_user")
        row = tmp_db.execute(
            "SELECT value FROM safety_state WHERE key = 'kill_switch'"
        ).fetchone()
        import json
        state = json.loads(row["value"])
        assert state["toggled_by"] == "test_user"
        assert state["toggled_at"] is not None


class TestRiskSettings:
    """Risk settings CRUD tests."""

    def test_get_default_risk_settings(self, tmp_db: sqlite3.Connection) -> None:
        """Default risk settings should match data-model.md values."""
        settings = get_risk_settings(tmp_db)
        assert settings["max_position_pct"] == 0.10
        assert settings["max_daily_loss_pct"] == 0.05
        assert settings["max_trades_per_day"] == 20
        assert settings["max_positions_per_symbol"] == 2

    def test_only_four_settings_returned(self, tmp_db: sqlite3.Connection) -> None:
        """Only the four core safety settings should be returned."""
        settings = get_risk_settings(tmp_db)
        assert len(settings) == 4
        assert set(settings.keys()) == set(DEFAULT_RISK_SETTINGS.keys())

    def test_update_risk_setting(self, tmp_db: sqlite3.Connection) -> None:
        """Updating a risk setting should return old and new values."""
        old, new = update_risk_setting(tmp_db, "max_position_pct", 0.25)
        assert old == 0.10
        assert new == 0.25
        settings = get_risk_settings(tmp_db)
        assert settings["max_position_pct"] == 0.25

    def test_update_integer_setting(self, tmp_db: sqlite3.Connection) -> None:
        """Integer settings should be stored as integers."""
        _, new = update_risk_setting(tmp_db, "max_trades_per_day", 50)
        assert new == 50
        assert isinstance(new, int)

    def test_reject_unknown_key(self, tmp_db: sqlite3.Connection) -> None:
        """Unknown risk setting keys should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown risk setting"):
            update_risk_setting(tmp_db, "nonexistent_key", 0.5)

    def test_reject_out_of_range_low(self, tmp_db: sqlite3.Connection) -> None:
        """Values below minimum should raise ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            update_risk_setting(tmp_db, "max_position_pct", 0.001)

    def test_reject_out_of_range_high(self, tmp_db: sqlite3.Connection) -> None:
        """Values above maximum should raise ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            update_risk_setting(tmp_db, "max_daily_loss_pct", 0.99)

    def test_validation_ranges_match_data_model(self) -> None:
        """Validation ranges should match data-model.md specification."""
        assert RISK_SETTING_RANGES["max_position_pct"] == (0.01, 0.50)
        assert RISK_SETTING_RANGES["max_daily_loss_pct"] == (0.01, 0.20)
        assert RISK_SETTING_RANGES["max_trades_per_day"] == (1, 100)
        assert RISK_SETTING_RANGES["max_positions_per_symbol"] == (1, 10)


class TestModuleIndependence:
    """Verify safety module has no imports from engine/market/execution."""

    def test_no_engine_imports(self) -> None:
        """Safety module should not import from finance_agent.engine."""
        import finance_agent.safety.guards as guards
        source = open(guards.__file__).read()
        assert "finance_agent.engine" not in source
        assert "finance_agent.execution" not in source
        assert "finance_agent.market" not in source
