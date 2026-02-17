"""Decision engine layer: combines research signals and market data to generate trade proposals.

Modules:
    scoring   — Hybrid confidence scoring (signal + indicator + momentum + LLM adjustment)
    risk      — Risk control checks and settings management
    proposals — Proposal generation, lifecycle management, and queries
    account   — Alpaca TradingClient wrapper for account/positions/orders
    state     — Kill switch and engine state persistence
"""
