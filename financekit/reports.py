"""Integrated reports that combine several financekit modules.

These functions are the *integration* surface exercised by
``tests/test_reports_integration.py``: each one composes at least two
lower-level modules, so their tests verify that the pieces agree with
each other, not merely that each piece works alone.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .investments import irr, npv
from .io import load_cashflows
from .loans import _summarize_schedule, amortization_schedule, monthly_payment
from .validation import ensure_series


def build_loan_report(principal: float, annual_rate_percent: float, months: int) -> dict[str, Any]:
    """Loan summary plus its full schedule, as plain serialisable data."""
    # REFACTOR: build the schedule once and summarise *that* object,
    # instead of letting loan_summary recompute an identical schedule.
    schedule = amortization_schedule(principal, annual_rate_percent, months)
    report: dict[str, Any] = dict(
        _summarize_schedule(
            schedule, principal, monthly_payment(principal, annual_rate_percent, months)
        )
    )
    report["schedule"] = [row.to_dict() for row in schedule]
    return report


def _payback_period(cashflows: list[float]) -> int | None:
    """First period index at which cumulative cashflow reaches >= 0."""
    cumulative = 0.0
    for period, flow in enumerate(cashflows):
        cumulative += flow
        if cumulative >= 0:
            return period
    return None


def build_investment_report(cashflows: Iterable[float], discount_rate: float) -> dict[str, Any]:
    """Appraise a project: NPV, IRR (or None), totals, payback, decision.

    The recommendation follows the textbook NPV rule - accept when NPV is
    positive at the required discount rate, reject otherwise.  Cashflows
    without a sign change have no IRR; the report records ``None`` instead
    of failing, because NPV alone still supports a decision.
    """
    flows = ensure_series(cashflows, "cashflows", min_length=1)
    value = npv(discount_rate, flows)
    try:
        rate_of_return: float | None = irr(flows)
    except ValidationError:
        rate_of_return = None
    return {
        "npv": value,
        "irr": rate_of_return,
        "total_inflows": sum(flow for flow in flows if flow > 0),
        "total_outflows": abs(sum(flow for flow in flows if flow < 0)),
        "net_cashflow": sum(flows),
        "payback_period": _payback_period(flows),
        "recommendation": "accept" if value > 0 else "reject",
    }


def analyze_cashflow_file(path: str | Path, discount_rate: float) -> dict[str, Any]:
    """Load a cashflow CSV and appraise it (io + investments integration)."""
    return build_investment_report(load_cashflows(path), discount_rate)
