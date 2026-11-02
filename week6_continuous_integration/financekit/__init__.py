"""financekit - a small, dependency-free personal-finance mathematics library.

Conventions used across the whole package (stated once, here, and tested):
  * ``interest`` / ``loans`` modules take rates as *percentages* (12 = 12%).
  * ``investments`` / ``statistics`` take rates and returns as *decimals*
    (0.12 = 12%) - the standard convention for NPV/IRR and return series.
"""

from __future__ import annotations

from .errors import ValidationError
from .interest import (
    compound_amount,
    compound_interest,
    effective_annual_rate,
    future_value,
    present_value,
    rule_of_72,
    simple_interest,
    years_to_double,
)
from .investments import cagr, irr, npv, required_monthly_saving, sip_future_value
from .io import load_cashflows, save_amortization_schedule
from .loans import AmortizationRow, amortization_schedule, loan_summary, monthly_payment
from .reports import analyze_cashflow_file, build_investment_report, build_loan_report
from .statistics import (
    correlation,
    cumulative_return,
    max_drawdown,
    mean_return,
    returns_stdev,
    returns_variance,
    sharpe_ratio,
)

__version__ = "1.1.0"

__all__ = [
    "AmortizationRow",
    "ValidationError",
    "__version__",
    "amortization_schedule",
    "analyze_cashflow_file",
    "build_investment_report",
    "build_loan_report",
    "cagr",
    "compound_amount",
    "compound_interest",
    "correlation",
    "cumulative_return",
    "effective_annual_rate",
    "future_value",
    "irr",
    "load_cashflows",
    "loan_summary",
    "max_drawdown",
    "mean_return",
    "monthly_payment",
    "npv",
    "present_value",
    "required_monthly_saving",
    "returns_stdev",
    "returns_variance",
    "rule_of_72",
    "save_amortization_schedule",
    "sharpe_ratio",
    "simple_interest",
    "sip_future_value",
    "years_to_double",
]
