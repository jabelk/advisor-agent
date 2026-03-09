"""Option pricing utilities for covered call backtesting.

Uses simplified Black-Scholes with historical volatility.
No scipy dependency — uses math.erf for normal CDF.
"""

from __future__ import annotations

import math


def norm_cdf(x: float) -> float:
    """Cumulative normal distribution using math.erf (no scipy needed)."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def calculate_historical_volatility(
    bars: list[dict],
    lookback_days: int = 20,
) -> float:
    """Calculate annualized historical volatility from daily price bars.

    Args:
        bars: List of OHLCV dicts with 'close' field
        lookback_days: Number of days for the calculation window

    Returns:
        Annualized volatility as decimal (e.g., 0.25 for 25%)
    """
    closes = [b["close"] for b in bars[-lookback_days:] if b.get("close", 0) > 0]

    if len(closes) < 3:
        return 0.20  # Default 20% if insufficient data

    # Log returns
    log_returns = [
        math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0
    ]

    if len(log_returns) < 2:
        return 0.20

    mean_ret = sum(log_returns) / len(log_returns)
    variance = sum((r - mean_ret) ** 2 for r in log_returns) / (len(log_returns) - 1)
    daily_vol = math.sqrt(variance) if variance > 0 else 0.0

    # Annualize: daily vol * sqrt(252 trading days)
    return daily_vol * math.sqrt(252)


def estimate_call_premium(
    spot_price: float,
    strike_price: float,
    days_to_expiration: int,
    historical_volatility: float,
    risk_free_rate: float = 0.045,
) -> float:
    """Estimate call option premium using Black-Scholes with historical volatility.

    For backtesting covered calls where actual option chain data isn't available.
    Applies a 15% IV premium (implied vol typically exceeds realized vol).

    Args:
        spot_price: Current stock price
        strike_price: Call strike price
        days_to_expiration: Days until expiration
        historical_volatility: Annualized historical vol (decimal)
        risk_free_rate: Risk-free rate (default 4.5%)

    Returns:
        Estimated call premium per share
    """
    if spot_price <= 0 or strike_price <= 0 or days_to_expiration <= 0:
        return 0.0

    # Apply IV premium (implied vol typically ~15% higher than realized)
    sigma = historical_volatility * 1.15

    if sigma <= 0:
        sigma = 0.20  # Floor at 20%

    t = days_to_expiration / 365.0

    d1 = (math.log(spot_price / strike_price) + (risk_free_rate + 0.5 * sigma**2) * t) / (
        sigma * math.sqrt(t)
    )

    d2 = d1 - sigma * math.sqrt(t)

    call_price = spot_price * norm_cdf(d1) - strike_price * math.exp(
        -risk_free_rate * t
    ) * norm_cdf(d2)

    return max(call_price, 0.01)  # Floor at $0.01


def estimate_premium_at_age(
    initial_premium: float,
    days_elapsed: int,
    total_days: int,
) -> float:
    """Estimate remaining premium value using time decay approximation.

    Options decay roughly proportional to sqrt of time remaining.

    Args:
        initial_premium: Premium collected at sale
        days_elapsed: Trading days since call was sold
        total_days: Total days to expiration

    Returns:
        Estimated current premium value
    """
    if total_days <= 0 or days_elapsed >= total_days:
        return 0.0

    remaining_ratio = (total_days - days_elapsed) / total_days
    # Theta decay is roughly sqrt-proportional
    return initial_premium * math.sqrt(remaining_ratio)
