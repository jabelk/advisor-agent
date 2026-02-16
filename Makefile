.PHONY: lint test check

# Pre-commit quality gates (run before committing)
check: lint test

lint:
	uv run ruff check src/ tests/
	uv run mypy src/

test:
	uv run pytest tests/unit/

# Full test suite (including integration tests requiring API keys)
test-all:
	uv run pytest

# Coverage report
coverage:
	uv run pytest --cov=finance_agent --cov-report=term-missing
