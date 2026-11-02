"""Investment appraisal: NPV, IRR, CAGR and monthly-investment (SIP) maths.

Convention: ``discount_rate`` and growth results are *decimals*
(``0.10`` = 10%), the standard for NPV/IRR work, while the SIP helpers take
an annual rate in percent to match how such products are quoted.
"""

from __future__ import annotations

from collections.abc import Iterable

from .errors import ValidationError
from .validation import (
    ensure_non_negative,
    ensure_positive,
    ensure_positive_int,
    ensure_rate_decimal,
    ensure_series,
)


def npv(discount_rate: float, cashflows: Iterable[float]) -> float:
    """Net present value; ``cashflows[0]`` occurs today (period 0)."""
    rate = ensure_rate_decimal(discount_rate, "discount_rate")
    flows = ensure_series(cashflows, "cashflows", min_length=1)
    return sum(flow / (1 + rate) ** period for period, flow in enumerate(flows))


def irr(cashflows: Iterable[float], *, tolerance: float = 1e-10) -> float:
    """Internal rate of return: the discount rate that makes NPV zero.

    Solved by bisection, which is slower than Newton-Raphson but cannot
    diverge: once a sign-changing bracket is found, the root is trapped.
    Raises :class:`ValidationError` when the cashflows have no sign change
    (no outflow or no inflow), because then no IRR exists.
    """
    flows = ensure_series(cashflows, "cashflows", min_length=2)
    if not (any(flow > 0 for flow in flows) and any(flow < 0 for flow in flows)):
        raise ValidationError(
            "IRR is undefined without both inflows and outflows (no sign change)."
        )

    def value(rate: float) -> float:
        return sum(flow / (1 + rate) ** period for period, flow in enumerate(flows))

    low, high = -0.9999, 1.0
    f_low, f_high = value(low), value(high)
    # Widen the upper end until the NPV changes sign across the bracket.
    while f_low * f_high > 0 and high < 1_000:
        high = high * 2 + 1
        f_high = value(high)
    if f_low * f_high > 0:
        raise ValidationError("IRR could not be bracketed for these cashflows.")
    if f_low == 0:
        return low
    if f_high == 0:
        return high

    for _ in range(200):
        middle = (low + high) / 2
        f_middle = value(middle)
        if abs(f_middle) < tolerance or (high - low) / 2 < tolerance:
            return middle
        if (f_low > 0) == (f_middle > 0):
            low, f_low = middle, f_middle
        else:
            high = middle
    return (low + high) / 2


def cagr(begin_value: float, end_value: float, years: float) -> float:
    """Compound annual growth rate as a decimal (0.10 = 10% per year)."""
    begin = ensure_positive(begin_value, "begin_value")
    end = ensure_non_negative(end_value, "end_value")
    period = ensure_positive(years, "years")
    return (end / begin) ** (1 / period) - 1


def sip_future_value(monthly_amount: float, annual_rate_percent: float, months: int) -> float:
    """Future value of equal *end-of-month* investments (an ordinary annuity)."""
    contribution = ensure_non_negative(monthly_amount, "monthly_amount")
    n = ensure_positive_int(months, "months")
    r = ensure_non_negative(annual_rate_percent, "annual_rate_percent") / 100 / 12
    if r == 0:
        return contribution * n
    return contribution * (((1 + r) ** n - 1) / r)


def required_monthly_saving(target_amount: float, annual_rate_percent: float, months: int) -> float:
    """Monthly saving needed to reach a target (exact inverse of the SIP formula)."""
    target = ensure_positive(target_amount, "target_amount")
    n = ensure_positive_int(months, "months")
    r = ensure_non_negative(annual_rate_percent, "annual_rate_percent") / 100 / 12
    if r == 0:
        return target / n
    return target * r / ((1 + r) ** n - 1)
