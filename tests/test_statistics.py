"""Unit tests for financekit.statistics (returns are decimals)."""

from __future__ import annotations

import pytest

from financekit import ValidationError
from financekit.statistics import (
    correlation,
    cumulative_return,
    max_drawdown,
    mean_return,
    returns_stdev,
    returns_variance,
    sharpe_ratio,
)

pytestmark = pytest.mark.unit


def test_mean_return(sample_returns):
    assert mean_return(sample_returns) == pytest.approx(0.01125)
    assert mean_return([0.05]) == pytest.approx(0.05)
    assert mean_return([0.10, -0.10]) == pytest.approx(0.0)


def test_variance_and_stdev_sample_vs_population(sample_returns):
    assert returns_variance(sample_returns, sample=True) == pytest.approx(0.00030625)
    assert returns_variance(sample_returns, sample=False) == pytest.approx(0.0002296875)
    assert returns_stdev(sample_returns, sample=True) == pytest.approx(0.0175)
    assert returns_stdev(sample_returns, sample=False) == pytest.approx(0.015155444566227676)
    # Population variance of a single observation is defined (0); sample is not.
    assert returns_variance([0.03], sample=False) == pytest.approx(0.0)
    with pytest.raises(ValidationError):
        returns_variance([0.03], sample=True)


@pytest.mark.parametrize(
    "returns, expected",
    [
        ([0.10, -0.10], -0.01),  # +10% then -10% does NOT break even
        ([0.10, 0.10], 0.21),
        ([0.0, 0.0], 0.0),
        ([], 0.0),  # no periods -> no return (documented)
    ],
)
def test_cumulative_return(returns, expected):
    assert cumulative_return(returns) == pytest.approx(expected)


def test_cumulative_return_fixture_series(sample_returns):
    assert cumulative_return(sample_returns) == pytest.approx(0.04529447, abs=1e-6)


def test_sharpe_ratio(sample_returns):
    assert sharpe_ratio(sample_returns) == pytest.approx(0.6428571428571429)
    assert sharpe_ratio(sample_returns, risk_free_rate=0.005) == pytest.approx(0.35714285714285715)


@pytest.mark.edge
def test_sharpe_ratio_with_zero_volatility_is_undefined():
    with pytest.raises(ValidationError, match="volatility"):
        sharpe_ratio([0.01, 0.01, 0.01])


@pytest.mark.parametrize(
    "prices, expected",
    [
        ([100, 110, 105, 120, 90, 95], 0.25),  # 120 -> 90
        ([100, 101, 102, 103], 0.0),  # never falls
        ([100], 0.0),  # single observation
        ([100, 50], 0.50),
        ([100, 80, 120, 60], 0.50),  # worst is 120 -> 60, not 100 -> 80
    ],
)
def test_max_drawdown(prices, expected):
    assert max_drawdown(prices) == pytest.approx(expected)


def test_correlation_perfect_and_inverse():
    assert correlation([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert correlation([1, 2, 3, 4], [8, 6, 4, 2]) == pytest.approx(-1.0)
    unrelated = correlation([1, 2, 3, 4], [1, 3, 2, 4])
    assert -1.0 < unrelated < 1.0


@pytest.mark.edge
@pytest.mark.parametrize(
    "bad_call",
    [
        lambda: mean_return([]),
        lambda: returns_stdev([]),
        lambda: max_drawdown([]),
        lambda: max_drawdown([100, 0, 50]),  # prices must be positive
        lambda: max_drawdown([100, -5]),
        lambda: correlation([1, 2], [1, 2, 3]),  # mismatched lengths
        lambda: correlation([1], [1]),  # need at least two points
        lambda: correlation([2, 2, 2], [1, 2, 3]),  # constant series: undefined
        lambda: cumulative_return([0.1, "0.2"]),
        lambda: cumulative_return([-1.5]),  # a < -100% return is impossible
    ],
)
def test_statistics_reject_invalid_inputs(bad_call):
    with pytest.raises(ValidationError):
        bad_call()
