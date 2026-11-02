"""Unit tests for financekit.loans (EMI and amortization)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from financekit import ValidationError
from financekit.loans import amortization_schedule, loan_summary, monthly_payment

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "principal, rate, months, expected",
    [
        (100_000, 12, 12, 8_884.878867834166),  # reference loan
        (500_000, 9, 60, 10_379.177613176937),  # 5-year loan
        (12_000, 0, 12, 1_000.0),  # zero interest: straight division
        (1_000, 12, 1, 1_010.0),  # single month: principal + 1% interest
        (50_000, 0, 1, 50_000.0),  # zero rate AND single month
    ],
)
def test_monthly_payment(principal, rate, months, expected):
    assert monthly_payment(principal, rate, months) == pytest.approx(expected, abs=0.01)


def test_schedule_shape_and_first_rows(standard_loan):
    schedule = amortization_schedule(**standard_loan)
    assert len(schedule) == 12
    assert [row.month for row in schedule] == list(range(1, 13))

    first = schedule[0]
    assert first.payment == pytest.approx(8_884.88, abs=0.01)
    assert first.interest_component == pytest.approx(1_000.00, abs=0.01)
    assert first.principal_component == pytest.approx(7_884.88, abs=0.01)
    assert first.balance == pytest.approx(92_115.12, abs=0.01)


def test_schedule_fully_repay_the_loan(standard_loan):
    """Key invariants: principal components sum to the loan; balance ends at 0."""
    schedule = amortization_schedule(**standard_loan)
    assert sum(row.principal_component for row in schedule) == pytest.approx(100_000, abs=0.01)
    assert schedule[-1].balance == pytest.approx(0.0, abs=0.01)
    balances = [row.balance for row in schedule]
    assert balances == sorted(balances, reverse=True)  # strictly paying down
    for row in schedule:
        assert row.payment == pytest.approx(
            row.principal_component + row.interest_component, abs=0.01
        )
        assert row.balance >= 0


def test_schedule_interest_share_declines_over_time(standard_loan):
    schedule = amortization_schedule(**standard_loan)
    interests = [row.interest_component for row in schedule]
    assert interests == sorted(interests, reverse=True)


def test_zero_interest_schedule(standard_loan):
    schedule = amortization_schedule(12_000, 0, 12)
    assert all(row.interest_component == 0 for row in schedule)
    assert all(row.payment == pytest.approx(1_000.0) for row in schedule)
    assert schedule[-1].balance == pytest.approx(0.0)


def test_schedule_rows_are_immutable_and_serialisable(standard_loan):
    row = amortization_schedule(**standard_loan)[0]
    with pytest.raises(FrozenInstanceError):
        row.balance = 0  # type: ignore[misc]
    as_dict = row.to_dict()
    assert set(as_dict) == {"month", "payment", "principal", "interest", "balance"}
    assert as_dict["month"] == 1


def test_loan_summary_is_internally_consistent(standard_loan):
    summary = loan_summary(**standard_loan)
    assert summary["monthly_payment"] == pytest.approx(8_884.88, abs=0.01)
    assert summary["number_of_payments"] == 12
    assert summary["total_payment"] == pytest.approx(
        standard_loan["principal"] + summary["total_interest"], abs=0.01
    )
    assert summary["total_interest"] == pytest.approx(6_618.55, abs=1.0)


@pytest.mark.edge
@pytest.mark.parametrize(
    "bad_call",
    [
        lambda: monthly_payment(100_000, 12, 0),
        lambda: monthly_payment(100_000, 12, -12),
        lambda: monthly_payment(0, 12, 12),
        lambda: monthly_payment(-500, 12, 12),
        lambda: monthly_payment(100_000, -1, 12),
        lambda: monthly_payment(100_000, 12, 12.5),
        lambda: amortization_schedule(100_000, 12, True),
    ],
)
def test_loans_reject_invalid_inputs(bad_call):
    with pytest.raises(ValidationError):
        bad_call()
