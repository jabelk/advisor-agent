#!/bin/sh
# Read Docker secrets from /run/secrets/ and export as environment variables.
# This bridges file-based Docker secrets to the env-var-based config module.
# On Railway, env vars are injected directly — these are fallbacks for local Docker.

if [ -f /run/secrets/alpaca_api_key ]; then
    export ALPACA_PAPER_API_KEY="$(cat /run/secrets/alpaca_api_key)"
fi

if [ -f /run/secrets/alpaca_secret_key ]; then
    export ALPACA_PAPER_SECRET_KEY="$(cat /run/secrets/alpaca_secret_key)"
fi

if [ -f /run/secrets/anthropic_api_key ]; then
    export ANTHROPIC_API_KEY="$(cat /run/secrets/anthropic_api_key)"
fi

if [ -f /run/secrets/finnhub_api_key ]; then
    export FINNHUB_API_KEY="$(cat /run/secrets/finnhub_api_key)"
fi

if [ -f /run/secrets/mcp_api_token ]; then
    export MCP_API_TOKEN="$(cat /run/secrets/mcp_api_token)"
fi

if [ -f /run/secrets/sfdc_consumer_key ]; then
    export SFDC_CONSUMER_KEY="$(cat /run/secrets/sfdc_consumer_key)"
fi

if [ -f /run/secrets/sfdc_consumer_secret ]; then
    export SFDC_CONSUMER_SECRET="$(cat /run/secrets/sfdc_consumer_secret)"
fi

if [ -f /run/secrets/edgar_identity ]; then
    export EDGAR_IDENTITY="$(cat /run/secrets/edgar_identity)"
fi

exec "$@"
