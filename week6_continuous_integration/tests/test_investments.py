"""Unit tests for financekit.investments (rates are decimals: 0.10 = 10%)."""

from __future__ import annotations

import pytest

from financekit import ValidationError
from financekit.investments import cagr, irr, npv, required_monthly_saving, sip_future_value

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "rate, cashflows, expected",
    [
        (0.10, [-1_000, 500, 600], -49.586776859504255),
        (0.0, [-1_000, 500, 600], 100.0),  # no discounting -> plain sum
        (0.25, [-2_000], -2_000.0),  # period-0 flow is undiscounted
        (0.10, [-10_000, 4_000, 5_000, 6_000], 2_276.4838467317777),
    ],
)
def test_npv(rate, cashflows, expected):
    assert npv(rate, cashflows) == pytest.approx(expected)


@pytest.mark.parametrize(
    "cashflows, expected_irr",
    [
        ([-1_000, 1_100], 0.10),
        ([-1_000, 0, 1_210], 0.10),  # sqrt(1.21) - 1
        ([-1_000, 1_000], 0.0),
        ([-10_000, 4_000, 5_000, 6_000], 0.2164778541842899),
    ],
)
def test_irr(cashflows, expected_irr):
    assert irr(cashflows) == pytest.approx(expected_irr, abs=1e-6)


def test_irr_actually_zeroes_the_npv(sample_cashflows):
    """Defining property of IRR, checked independently of the solver."""
    assert npv(irr(sample_cashflows), sample_cashflows) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.edge
@pytest.mark.parametrize(
    "cashflows",
    [
        [100, 200, 300],  # no outflow: no sign change, no IRR
        [-100, -200],  # no inflow
        [],  # nothing at all
        [0, 0, 0],  # no non-zero flow
    ],
)
def test_irr_rejects_cashflows_without_a_root(cashflows):
    with pytest.raises(ValidationError):
        irr(cashflows)


@pytest.mark.parametrize(
    "begin, end, years, expected",
    [
        (100, 121, 2, 0.10),
        (10_000, 14_641, 4, 0.10),
        (1_000, 1_000, 5, 0.0),
        (1_000, 500, 1, -0.50),  # negative growth is a valid answer
    ],
)
def test_cagr(begin, end, years, expected):
    assert cagr(begin, end, years) == pytest.approx(expected)


@pytest.mark.parametrize(
    "monthly, rate_percent, months, expected",
    [
        (1_000, 12, 12, 12_682.503013196976),  # end-of-month contributions
        (5_000, 12, 60, 408_348.3492820457),
        (2_000, 0, 24, 48_000.0),  # zero growth -> plain sum
        (1_000, 12, 1, 1_000.0),  # one contribution, no time to grow
    ],
)
def test_sip_future_value(monthly, rate_percent, months, expected):
    assert sip_future_value(monthly, rate_percent, months) == pytest.approx(expected, abs=0.01)


def test_required_monthly_saving_is_the_inverse_of_sip():
    target = sip_future_value(1_000, 12, 12)
    assert required_monthly_saving(target, 12, 12) == pytest.approx(1_000.0, abs=0.01)
    assert required_monthly_saving(48_000, 0, 24) == pytest.approx(2_000.0)


@pytest.mark.edge
@pytest.mark.parametrize(
    "bad_call",
    [
        lambda: npv(-1.0, [-100, 200]),  # -100% discount rate: division by zero territory
        lambda: npv(-1.5, [-100, 200]),
        lambda: npv(0.1, []),
        lambda: cagr(0, 100, 2),
        lambda: cagr(100, 200, 0),
        lambda: cagr(100, -50, 2),
        lambda: sip_future_value(-100, 12, 12),
        lambda: sip_future_value(100, 12, 0),
        lambda: required_monthly_saving(0, 12, 12),
        lambda: npv(0.1, [100, float("nan")]),
    ],
)
def test_investments_reject_invalid_inputs(bad_call):
    with pytest.raises(ValidationError):
        bad_call()
