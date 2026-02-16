"""Unit tests for watchlist CRUD operations."""

from __future__ import annotations

import sqlite3

import pytest

from finance_agent.data.watchlist import (
    add_company,
    get_company_by_ticker,
    list_companies,
    reactivate_company,
    remove_company,
)


class TestAddCompany:
    def test_add_company(self, tmp_db: sqlite3.Connection) -> None:
        company_id = add_company(tmp_db, "NVDA", "NVIDIA Corporation", "0001045810", "Technology")
        assert company_id > 0
        row = tmp_db.execute("SELECT * FROM company WHERE id = ?", (company_id,)).fetchone()
        assert row["ticker"] == "NVDA"
        assert row["name"] == "NVIDIA Corporation"
        assert row["cik"] == "0001045810"
        assert row["sector"] == "Technology"
        assert row["active"] == 1

    def test_add_duplicate_raises(self, tmp_db: sqlite3.Connection) -> None:
        add_company(tmp_db, "NVDA", "NVIDIA Corporation")
        with pytest.raises(ValueError, match="already on the watchlist"):
            add_company(tmp_db, "NVDA", "NVIDIA Corporation")

    def test_add_reactivates_soft_deleted(self, tmp_db: sqlite3.Connection) -> None:
        company_id = add_company(tmp_db, "NVDA", "NVIDIA Corporation")
        remove_company(tmp_db, "NVDA")
        new_id = add_company(tmp_db, "NVDA", "NVIDIA Corp Updated")
        assert new_id == company_id
        row = tmp_db.execute("SELECT * FROM company WHERE id = ?", (company_id,)).fetchone()
        assert row["active"] == 1
        assert row["name"] == "NVIDIA Corp Updated"

    def test_ticker_uppercased(self, tmp_db: sqlite3.Connection) -> None:
        add_company(tmp_db, "nvda", "NVIDIA Corporation")
        row = get_company_by_ticker(tmp_db, "NVDA")
        assert row is not None
        assert row["ticker"] == "NVDA"

    def test_add_without_optional_fields(self, tmp_db: sqlite3.Connection) -> None:
        company_id = add_company(tmp_db, "AAPL", "Apple Inc")
        row = tmp_db.execute("SELECT * FROM company WHERE id = ?", (company_id,)).fetchone()
        assert row["cik"] is None
        assert row["sector"] is None


class TestRemoveCompany:
    def test_remove_sets_inactive(self, tmp_db: sqlite3.Connection) -> None:
        add_company(tmp_db, "NVDA", "NVIDIA Corporation")
        result = remove_company(tmp_db, "NVDA")
        assert result is True
        row = tmp_db.execute("SELECT active FROM company WHERE ticker = 'NVDA'").fetchone()
        assert row["active"] == 0

    def test_remove_nonexistent_returns_false(self, tmp_db: sqlite3.Connection) -> None:
        result = remove_company(tmp_db, "ZZZZ")
        assert result is False

    def test_remove_already_removed_returns_false(self, tmp_db: sqlite3.Connection) -> None:
        add_company(tmp_db, "NVDA", "NVIDIA Corporation")
        remove_company(tmp_db, "NVDA")
        result = remove_company(tmp_db, "NVDA")
        assert result is False


class TestListCompanies:
    def test_list_active_only(self, tmp_db: sqlite3.Connection) -> None:
        add_company(tmp_db, "NVDA", "NVIDIA Corporation")
        add_company(tmp_db, "AAPL", "Apple Inc")
        remove_company(tmp_db, "AAPL")
        companies = list_companies(tmp_db, active_only=True)
        assert len(companies) == 1
        assert companies[0]["ticker"] == "NVDA"

    def test_list_all(self, tmp_db: sqlite3.Connection) -> None:
        add_company(tmp_db, "NVDA", "NVIDIA Corporation")
        add_company(tmp_db, "AAPL", "Apple Inc")
        remove_company(tmp_db, "AAPL")
        companies = list_companies(tmp_db, active_only=False)
        assert len(companies) == 2

    def test_list_empty(self, tmp_db: sqlite3.Connection) -> None:
        companies = list_companies(tmp_db)
        assert companies == []


class TestGetCompanyByTicker:
    def test_get_existing(self, tmp_db: sqlite3.Connection) -> None:
        add_company(tmp_db, "NVDA", "NVIDIA Corporation", "0001045810")
        company = get_company_by_ticker(tmp_db, "NVDA")
        assert company is not None
        assert company["ticker"] == "NVDA"
        assert company["name"] == "NVIDIA Corporation"

    def test_get_nonexistent(self, tmp_db: sqlite3.Connection) -> None:
        company = get_company_by_ticker(tmp_db, "ZZZZ")
        assert company is None

    def test_get_inactive_returns_none(self, tmp_db: sqlite3.Connection) -> None:
        add_company(tmp_db, "NVDA", "NVIDIA Corporation")
        remove_company(tmp_db, "NVDA")
        company = get_company_by_ticker(tmp_db, "NVDA")
        assert company is None


class TestReactivateCompany:
    def test_reactivate(self, tmp_db: sqlite3.Connection) -> None:
        add_company(tmp_db, "NVDA", "NVIDIA Corporation")
        remove_company(tmp_db, "NVDA")
        result = reactivate_company(tmp_db, "NVDA")
        assert result is True
        company = get_company_by_ticker(tmp_db, "NVDA")
        assert company is not None

    def test_reactivate_already_active(self, tmp_db: sqlite3.Connection) -> None:
        add_company(tmp_db, "NVDA", "NVIDIA Corporation")
        result = reactivate_company(tmp_db, "NVDA")
        assert result is False
