"""Unit tests for financekit.interest (rates are percentages: 12 = 12%)."""

from __future__ import annotations

import math

import pytest

from financekit import ValidationError
from financekit.interest import (
    compound_amount,
    compound_interest,
    effective_annual_rate,
    future_value,
    present_value,
    rule_of_72,
    simple_interest,
    years_to_double,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "principal, rate, years, expected",
    [
        (10_000, 5, 2, 1_000.0),  # textbook example
        (5_000, 6, 3, 900.0),
        (10_000, 0, 5, 0.0),  # zero rate -> no interest
        (0, 10, 5, 0.0),  # zero principal
        (10_000, 10, 0, 0.0),  # zero time
        (1_500, 4.5, 0.5, 33.75),  # fractional years are legitimate
    ],
)
def test_simple_interest(principal, rate, years, expected):
    assert simple_interest(principal, rate, years) == pytest.approx(expected)


@pytest.mark.parametrize(
    "principal, rate, years, n, expected_amount",
    [
        (10_000, 10, 2, 1, 12_100.0),  # annual compounding
        (10_000, 12, 1, 12, 11_268.250301319698),  # monthly compounding
        (10_000, 0, 10, 12, 10_000.0),  # zero rate never grows
        (1_000, 100, 1, 1, 2_000.0),  # 100% doubles in a year
    ],
)
def test_compound_amount(principal, rate, years, n, expected_amount):
    assert compound_amount(principal, rate, years, n) == pytest.approx(expected_amount)


def test_compound_interest_is_amount_minus_principal():
    assert compound_interest(10_000, 10, 2) == pytest.approx(2_100.0)
    amount = compound_amount(7_500, 8, 3, 4)
    assert compound_interest(7_500, 8, 3, 4) == pytest.approx(amount - 7_500)


def test_more_frequent_compounding_never_earns_less():
    annual = compound_amount(10_000, 12, 5, 1)
    monthly = compound_amount(10_000, 12, 5, 12)
    assert monthly > annual


def test_effective_annual_rate():
    assert effective_annual_rate(12, 12) == pytest.approx(12.682503013196978)
    assert effective_annual_rate(12, 1) == pytest.approx(12.0)
    assert effective_annual_rate(0, 12) == pytest.approx(0.0)


@pytest.mark.parametrize(
    "principal, rate, years, n",
    [
        (10_000, 10, 2, 1),
        (25_000, 7.5, 4, 12),
        (1_000, 3, 0.5, 2),
    ],
)
def test_present_and_future_value_are_inverses(principal, rate, years, n):
    """Property-style check: discounting a compounded amount returns the start."""
    grown = future_value(principal, rate, years, n)
    assert present_value(grown, rate, years, n) == pytest.approx(principal)


def test_present_value_known_example():
    assert present_value(12_100, 10, 2) == pytest.approx(10_000.0)


def test_rule_of_72_and_exact_years_to_double():
    assert rule_of_72(8) == pytest.approx(9.0)
    assert years_to_double(8) == pytest.approx(math.log(2) / math.log(1.08))
    # The rule of thumb should land close to the exact answer around 8%.
    assert rule_of_72(8) == pytest.approx(years_to_double(8), abs=0.1)
    assert years_to_double(12) == pytest.approx(6.116255374199699)


@pytest.mark.edge
@pytest.mark.parametrize(
    "bad_call",
    [
        lambda: simple_interest(-1, 5, 2),
        lambda: simple_interest(100, -5, 2),
        lambda: simple_interest(100, 5, -1),
        lambda: compound_amount(100, 5, 2, 0),
        lambda: compound_amount(100, 5, 2, 2.5),
        lambda: compound_amount(100, 5, 2, True),
        lambda: simple_interest("10000", 5, 2),
        lambda: simple_interest(float("nan"), 5, 2),
        lambda: simple_interest(float("inf"), 5, 2),
        lambda: rule_of_72(0),
        lambda: years_to_double(-3),
    ],
)
def test_interest_rejects_invalid_inputs(bad_call):
    with pytest.raises(ValidationError):
        bad_call()
