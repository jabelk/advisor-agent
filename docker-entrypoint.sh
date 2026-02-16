#!/bin/sh
# Read Docker secrets from /run/secrets/ and export as environment variables.
# This bridges file-based Docker secrets to the env-var-based config module.

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

exec "$@"
