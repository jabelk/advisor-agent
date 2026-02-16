# Implementation Plan: Project Scaffolding

**Branch**: `001-project-scaffolding` | **Date**: 2026-02-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-project-scaffolding/spec.md`

## Summary

Scaffold the finance-agent Python project with uv, establishing the modular `src/` layout, configuration management (paper/live switching via env vars), SQLite database with append-only audit log, Docker containerization, and a GitHub Actions deployment workflow to the Intel NUC. This creates the runnable foundation that all subsequent features build on.

## Technical Context

**Language/Version**: Python 3.12+ with type hints throughout
**Primary Dependencies**: alpaca-py (>=0.43), httpx, python-dotenv (local dev only)
**Storage**: SQLite (WAL mode, PRAGMA user_version migrations)
**Testing**: pytest, pytest-cov, ruff (linting), mypy (type checking)
**Target Platform**: Linux (Ubuntu 24.04 LTS on Intel NUC), developed on macOS
**Project Type**: single (src layout with `uv_build` backend)
**Performance Goals**: Health check completes in <5 seconds; container builds in <2 minutes
**Constraints**: Single-process application; no network dependencies for database
**Scale/Scope**: 1 user (operator), ~5-15 database tables total across all features

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety First | PASS | `paper=True` is the alpaca-py default. Config layer defaults to paper mode. Live mode requires explicit env vars + displays prominent warning. |
| II. Research-Driven | N/A | Scaffolding feature — no trading decisions involved. |
| III. Modular Architecture | PASS | Src layout with separate sub-packages per layer: `data/`, `research/`, `engine/`, `execution/`, `audit/`. Empty stubs in this feature. |
| IV. Audit Everything | PASS | SQLite audit_log table with append-only triggers (BEFORE UPDATE/DELETE → RAISE ABORT). Schema initialized at startup. |
| V. Security by Design | PASS | Secrets from env vars only, `.env` in `.gitignore`, separate paper/live key names, Docker secrets via `/run/secrets/`, live keys never in dev env. |
| Development Workflow | PASS | Feature branch, PR to main, spec-kit workflow followed. |
| Quality Gates | PASS | Pre-commit: ruff + pytest. Pre-merge: PR review, all tests pass. |

**Post-Phase 1 re-check**: All gates still pass. No violations introduced by design decisions.

## Project Structure

### Documentation (this feature)

```text
specs/001-project-scaffolding/
├── plan.md              # This file
├── research.md          # Phase 0 output (completed)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI interface contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
└── finance_agent/
    ├── __init__.py          # Package version, top-level exports
    ├── cli.py               # CLI entry point (health check, version)
    ├── config.py            # Configuration loading, validation, env var mapping
    ├── db.py                # SQLite connection factory, migration runner
    ├── data/                # Data ingestion layer (empty stubs)
    │   └── __init__.py
    ├── research/            # Research/analysis layer (empty stubs)
    │   └── __init__.py
    ├── engine/              # Decision engine layer (empty stubs)
    │   └── __init__.py
    ├── execution/           # Execution layer (empty stubs)
    │   └── __init__.py
    └── audit/               # Audit logging
        ├── __init__.py
        └── logger.py        # AuditLogger class (write events to SQLite)

migrations/
├── 001_init.sql             # Initial schema: audit_log table + triggers
└── README.md                # Migration conventions

tests/
├── __init__.py
├── conftest.py              # Shared fixtures (temp DB, mock config)
├── unit/
│   ├── __init__.py
│   ├── test_config.py       # Config loading, validation, mode detection
│   ├── test_db.py           # DB init, migration runner, pragma verification
│   └── test_audit.py        # Audit logger, append-only enforcement
└── integration/
    ├── __init__.py
    └── test_health.py       # Health check against paper trading API (requires keys)

# Project root files
pyproject.toml               # Project metadata, deps, scripts, tool config
uv.lock                      # Lockfile (committed)
.python-version              # "3.12"
.env.example                 # Template with all env vars documented
.gitignore                   # .env, .venv, __pycache__, *.db, secrets/
Dockerfile                   # Multi-stage build with uv
docker-compose.yml           # App service + volume mounts + secrets
.github/workflows/deploy.yml # Self-hosted runner deployment
CLAUDE.md                    # Already exists — will be updated
README.md                    # Setup instructions, prerequisites
```

**Structure Decision**: Single `src/` layout package (`finance_agent`) with sub-packages mirroring the architecture layers from the constitution. This is simpler than workspaces and sufficient for a single-repo project. Each layer sub-package is an empty stub (`__init__.py` only) in this feature — future features populate them.

## Deployment Architecture

```text
┌─────────────────────┐       git push        ┌──────────────────────┐
│  MacBook Air (dev)  │ ───────────────────▶  │  GitHub (remote)     │
│  - Code editing     │                        │  - Actions trigger   │
│  - uv run pytest    │                        └──────────┬───────────┘
│  - Local .env       │                                   │
└─────────────────────┘                                   │ webhook
                                                          ▼
                                               ┌──────────────────────┐
                                               │  Intel NUC (runner)  │
                                               │  - Ubuntu 24.04 LTS  │
                                               │  - Self-hosted runner │
                                               │  - docker compose    │
                                               │  - Secrets in GH     │
                                               │  - SQLite in ./data  │
                                               │  ssh warp-nuc        │
                                               │  192.168.4.152       │
                                               └──────────────────────┘
```

## Complexity Tracking

No constitution violations. No complexity justifications needed.
