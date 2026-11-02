"""Statistics for return and price series (decimals: ``0.02`` = +2%)."""

from __future__ import annotations

import math
from collections.abc import Iterable

from .errors import ValidationError
from .validation import ensure_number, ensure_series


def mean_return(returns: Iterable[float]) -> float:
    """Arithmetic mean of a return series."""
    values = ensure_series(returns, "returns", min_length=1)
    return math.fsum(values) / len(values)


def returns_variance(returns: Iterable[float], sample: bool = True) -> float:
    """Variance of returns.

    ``sample=True`` (the default) divides by ``n - 1`` (Bessel's
    correction, for estimating a population from a sample) and therefore
    needs at least two observations; population variance divides by ``n``.
    """
    values = ensure_series(returns, "returns", min_length=2 if sample else 1)
    mean = math.fsum(values) / len(values)
    squared = math.fsum((value - mean) ** 2 for value in values)
    return squared / (len(values) - 1 if sample else len(values))


def returns_stdev(returns: Iterable[float], sample: bool = True) -> float:
    """Standard deviation (volatility) of returns."""
    return math.sqrt(returns_variance(returns, sample=sample))


def cumulative_return(returns: Iterable[float]) -> float:
    """Compound a series of periodic returns into one total return.

    An empty series means “no periods elapsed” and returns 0.0 by
    definition here (documented and tested).  A single return below -100%
    is economically impossible and is rejected.
    """
    values = ensure_series(returns, "returns", min_length=0)
    growth = 1.0
    for value in values:
        if value < -1:
            raise ValidationError(f"A return cannot be below -100%, got {value}.")
        growth *= 1 + value
    return growth - 1


def sharpe_ratio(returns: Iterable[float], risk_free_rate: float = 0.0) -> float:
    """(Mean excess return) / volatility, using the sample standard deviation."""
    values = ensure_series(returns, "returns", min_length=2)
    free = ensure_number(risk_free_rate, "risk_free_rate")
    volatility = returns_stdev(values, sample=True)
    if volatility == 0:
        raise ValidationError(
            "Sharpe ratio is undefined when volatility (standard deviation) is zero."
        )
    return (math.fsum(values) / len(values) - free) / volatility


def max_drawdown(prices: Iterable[float]) -> float:
    """Largest peak-to-trough decline, as a fraction (0.25 = a 25% fall)."""
    values = ensure_series(prices, "prices", min_length=1)
    if any(value <= 0 for value in values):
        raise ValidationError("prices must all be positive.")
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        worst = max(worst, (peak - value) / peak)
    return worst


def correlation(xs: Iterable[float], ys: Iterable[float]) -> float:
    """Pearson correlation coefficient between two equal-length series."""
    x_values = ensure_series(xs, "xs", min_length=2)
    y_values = ensure_series(ys, "ys", min_length=2)
    if len(x_values) != len(y_values):
        raise ValidationError(
            f"Series must have the same length, got {len(x_values)} and {len(y_values)}."
        )
    x_mean = math.fsum(x_values) / len(x_values)
    y_mean = math.fsum(y_values) / len(y_values)
    numerator = math.fsum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = math.sqrt(
        math.fsum((x - x_mean) ** 2 for x in x_values)
        * math.fsum((y - y_mean) ** 2 for y in y_values)
    )
    if denominator == 0:
        raise ValidationError("Correlation is undefined for a constant series (zero variance).")
    return numerator / denominator
