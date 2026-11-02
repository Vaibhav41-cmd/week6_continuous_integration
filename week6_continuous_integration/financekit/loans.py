"""Loan instalments (EMI) and amortization schedules.

Convention: the interest rate is an *annual percentage* (``12`` = 12% per
year), converted internally to a monthly rate of ``rate / 100 / 12``.
Schedule amounts are rounded to 2 decimal places (paise/cents) and the
final instalment absorbs any rounding residue, so a schedule always ends
at a balance of exactly 0.00 and its principal components always sum to
the amount borrowed - both properties are asserted by the tests.
"""

from __future__ import annotations

from dataclasses import dataclass

from .validation import ensure_non_negative, ensure_positive, ensure_positive_int


def _round_money(value: float) -> float:
    """Round to paise/cents. Single helper = one rounding policy (REFACTOR)."""
    return round(value + 0.0, 2)  # "+ 0.0" normalises -0.00 to 0.00


@dataclass(frozen=True)
class AmortizationRow:
    """One month of an amortization schedule (immutable on purpose)."""

    month: int
    payment: float
    principal_component: float
    interest_component: float
    balance: float

    def to_dict(self) -> dict[str, float | int]:
        """Plain-dict view used by reports and CSV export."""
        return {
            "month": self.month,
            "payment": self.payment,
            "principal": self.principal_component,
            "interest": self.interest_component,
            "balance": self.balance,
        }


def _monthly_rate(annual_rate_percent: float) -> float:
    return ensure_non_negative(annual_rate_percent, "annual_rate_percent") / 100 / 12


def monthly_payment(principal: float, annual_rate_percent: float, months: int) -> float:
    """Equated monthly instalment for a loan.

    Uses the standard annuity formula ``P*r*(1+r)^n / ((1+r)^n - 1)``;
    at a 0% rate that formula divides by zero, so the payment degrades to
    plain ``principal / months``.
    """
    amount = ensure_positive(principal, "principal")
    n = ensure_positive_int(months, "months")
    r = _monthly_rate(annual_rate_percent)
    if r == 0:
        return amount / n
    factor = (1 + r) ** n
    return amount * r * factor / (factor - 1)


def amortization_schedule(
    principal: float, annual_rate_percent: float, months: int
) -> list[AmortizationRow]:
    """Month-by-month repayment schedule ending at a 0.00 balance."""
    amount = ensure_positive(principal, "principal")
    n = ensure_positive_int(months, "months")
    r = _monthly_rate(annual_rate_percent)
    instalment = _round_money(monthly_payment(amount, annual_rate_percent, n))

    schedule: list[AmortizationRow] = []
    balance = _round_money(amount)
    for month in range(1, n + 1):
        interest = _round_money(balance * r)
        if month == n:
            # Final instalment clears whatever remains, absorbing rounding.
            principal_component = balance
            payment = _round_money(principal_component + interest)
        else:
            payment = instalment
            principal_component = _round_money(payment - interest)
        balance = _round_money(balance - principal_component)
        schedule.append(
            AmortizationRow(
                month=month,
                payment=payment,
                principal_component=principal_component,
                interest_component=interest,
                balance=balance,
            )
        )
    return schedule


def _summarize_schedule(
    schedule: list[AmortizationRow], principal: float, instalment: float
) -> dict[str, float | int]:
    """Headline figures from an already-computed schedule.

    Extracted in the REFACTOR phase: ``loan_summary`` and the integrated
    loan report previously derived the same totals in two places, and the
    report recomputed the whole schedule a second time to do so.
    """
    return {
        "principal": _round_money(ensure_positive(principal, "principal")),
        "monthly_payment": _round_money(instalment),
        "number_of_payments": len(schedule),
        "total_payment": _round_money(sum(row.payment for row in schedule)),
        "total_interest": _round_money(sum(row.interest_component for row in schedule)),
    }


def loan_summary(
    principal: float, annual_rate_percent: float, months: int
) -> dict[str, float | int]:
    """Headline figures for a loan, derived from its schedule (computed once)."""
    schedule = amortization_schedule(principal, annual_rate_percent, months)
    return _summarize_schedule(
        schedule, principal, monthly_payment(principal, annual_rate_percent, months)
    )
