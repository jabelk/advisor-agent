# Advisor Agent: Single-stage Docker build with uv

FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Phase 1: Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Phase 2: Install project
COPY . .
RUN uv sync --frozen --no-dev

# Put venv on PATH
ENV PATH="/app/.venv/bin:$PATH"

# Create data directories for SQLite and research artifacts
RUN mkdir -p /app/data /app/research_data

# Entrypoint script reads Docker secrets and exports as env vars
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-m", "finance_agent.mcp.research_server", "--http"]
