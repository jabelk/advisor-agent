# Research: Project Scaffolding

**Feature**: 001-project-scaffolding
**Date**: 2026-02-16

## Decision 1: Python Project Structure with uv

**Decision**: Use `uv init --package` with `src/` layout and `uv_build` backend.

**Rationale**: The src layout isolates the package from project root, ensures tests import the installed package (catching packaging issues early), and cleanly separates source from tooling. The `--package` flag provides a build system and `[project.scripts]` for CLI entry points.

**Alternatives considered**:
- Flat layout (`uv init --app`): Simpler but doesn't support console_scripts or proper test isolation. Not suitable for a multi-module project.
- Workspace monorepo: Overkill for a single application. Workspaces are for multiple independently-releasable packages.

**Key details**:
- Module name: `finance_agent` (Python normalizes dashes to underscores)
- Entry point: `finance-agent = "finance_agent.cli:main"` in `[project.scripts]`
- Build system: `uv_build>=0.10.3,<0.11.0`
- Dev deps use PEP 735 `[dependency-groups]` (not deprecated `[tool.uv.dev-dependencies]`)
- `uv sync --frozen --no-dev` for production/Docker installs
- `uv sync --locked` in CI to catch stale lockfiles

## Decision 2: SQLite Migration Strategy

**Decision**: Hand-rolled migrations using `PRAGMA user_version` with numbered `.sql` files in a `migrations/` directory.

**Rationale**: Zero external dependencies beyond Python's built-in `sqlite3`. The entire migration runner is ~40 lines. For a project that will have <20 migrations total, a library adds complexity without proportional benefit. `PRAGMA user_version` is a first-class SQLite feature stored in the database file header.

**Alternatives considered**:
- `fastmigrate` (Answer.AI): Good fallback if we want CLI tooling and backup support later. Installs via `uv add fastmigrate`. Three-function API.
- Alembic: Pulls in SQLAlchemy, has pain points with SQLite's limited ALTER TABLE. Overkill.
- yoyo-migrations: Multi-database support we don't need. Dependency graph features we won't use.

**Key details**:
- Migration files: `migrations/001_init.sql`, `migrations/002_add_xyz.sql`, etc.
- Each migration sets `PRAGMA user_version = N` at the end
- Migrations run inside a transaction for atomicity
- Append-only enforcement via BEFORE UPDATE/DELETE triggers with `RAISE(ABORT, ...)`

## Decision 3: SQLite Connection Configuration

**Decision**: Use WAL mode with recommended PRAGMAs for performance and safety.

**Rationale**: WAL mode allows concurrent readers with one writer, is significantly faster than rollback journal, and is the standard recommendation for any non-trivial SQLite usage.

**Per-connection PRAGMAs (set on every `sqlite3.connect()`)**:
- `PRAGMA journal_mode = WAL` (persistent once set, but verify)
- `PRAGMA synchronous = NORMAL` (safe for WAL mode, avoids unnecessary sync)
- `PRAGMA busy_timeout = 5000` (prevents immediate SQLITE_BUSY)
- `PRAGMA foreign_keys = ON` (disabled by default in SQLite)
- `PRAGMA cache_size = -64000` (64 MB page cache)

**On connection close**: `PRAGMA analysis_limit = 400; PRAGMA optimize;`

## Decision 4: Alpaca SDK Configuration

**Decision**: Use `alpaca-py` (v0.43.2) with explicit credential passing from environment variables. Our config layer reads env vars; the SDK receives them as constructor parameters.

**Rationale**: The new `alpaca-py` SDK does NOT auto-read environment variables (unlike the deprecated `alpaca-trade-api`). Credentials must be passed explicitly to `TradingClient(api_key=..., secret_key=..., paper=True)`. The `paper` parameter defaults to `True`, which is a safe default.

**Environment variable naming** (follows Alpaca ecosystem convention):
- `ALPACA_PAPER_API_KEY` / `ALPACA_PAPER_SECRET_KEY` — paper trading
- `ALPACA_LIVE_API_KEY` / `ALPACA_LIVE_SECRET_KEY` — live trading
- Paper and live keys are separate in Alpaca — they cannot be used interchangeably

**Key URLs** (from `BaseURL` enum):
- Paper trading: `https://paper-api.alpaca.markets`
- Live trading: `https://api.alpaca.markets`
- Market data: `https://data.alpaca.markets` (same for both)

**Health check**: `TradingClient.get_account()` → returns `TradeAccount` with `.status == 'ACTIVE'`

**Exceptions**: `APIError` (with `.status_code`, `.code`, `.message`) and `ValueError` for missing credentials.

## Decision 5: Docker Build Pattern

**Decision**: Multi-stage build with `python:3.12-slim` base + COPY uv binary from `ghcr.io/astral-sh/uv:latest`. Two-phase `uv sync` for layer caching.

**Rationale**: Official Astral-recommended pattern. Builder stage installs all dependencies, runtime stage gets only `.venv`. Two-phase sync (deps first, project second) maximizes Docker layer cache hits.

**Key environment variables in Dockerfile**:
- `UV_COMPILE_BYTECODE=1` — faster container startup
- `UV_LINK_MODE=copy` — required with cache mounts
- `--locked` in build, `--frozen` in runtime

**Secrets**: Docker Compose `secrets:` directive, mounted at `/run/secrets/`. Never use `ENV` or `ARG` for secrets in Dockerfile.

## Decision 6: Deployment Workflow (Mac → NUC)

**Decision**: Develop locally on MacBook Air, push to GitHub, self-hosted runner on NUC runs `docker compose build && docker compose up -d`.

**Rationale**: The NUC already has a GitHub Actions runner. No SSH needed — the runner executes directly on the NUC. This is the simplest possible deployment path.

**Workflow**: Push to `main` → GitHub Actions triggers on NUC runner → build Docker image → restart container.

**NUC details**:
- Ubuntu 24.04.3 LTS, accessible via `ssh warp-nuc` (192.168.4.152)
- Docker Compose v2 (plugin, not standalone binary)
- Self-hosted runner already installed for other projects
- Secrets stored as GitHub Actions secrets, written to `./secrets/` during deploy, cleaned up after

## Decision 7: Network Isolation (Docker)

**Decision**: Start without network isolation. Add internal network + nginx proxy sidecars in a later feature.

**Rationale**: Network isolation requires one nginx sidecar per allowed domain, which adds operational complexity. For the scaffolding feature, we should get the basic Docker setup working first. Network isolation is a P3 concern (User Story 4).

**Future pattern**: Docker Compose `internal: true` network. App container on restricted network, nginx proxy containers bridging to internet for each allowed domain (api.alpaca.markets, data.alpaca.markets, efts.sec.gov, api.anthropic.com).
