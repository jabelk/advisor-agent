# Changelog

All notable changes to the finance-agent project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] - 2026-02-16

### Added

- Project scaffolding with `src/` layout and modular architecture layers
- Configuration management via environment variables with paper/live mode detection
- SQLite database with WAL mode, automatic schema migrations via `PRAGMA user_version`
- Append-only audit log with `BEFORE UPDATE/DELETE` trigger enforcement
- `finance-agent health` command validating config, database, and Alpaca broker connectivity
- `finance-agent version` command
- Docker multi-stage build with uv and Docker Compose secrets support
- GitHub Actions deployment workflow for Intel NUC self-hosted runner
- Unit tests for config, database, and audit modules (42 tests)
- Integration test for health check against paper trading API
