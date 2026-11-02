"""Simple and compound interest.

Convention: rates in this module are *percentages* (``12`` means 12% per
year) and money amounts are plain floats in whatever currency the caller
uses - the functions are currency-agnostic.
"""

from __future__ import annotations

import math

from .validation import ensure_non_negative, ensure_positive, ensure_positive_int


def _growth_factor(annual_rate_percent: float, years: float, compounds_per_year: int) -> float:
    """Validated ``(1 + r/n) ** (n*t)`` shared by the compound formulas."""
    rate = ensure_non_negative(annual_rate_percent, "annual_rate_percent")
    period = ensure_non_negative(years, "years")
    n = ensure_positive_int(compounds_per_year, "compounds_per_year")
    return (1 + rate / 100 / n) ** (n * period)


def simple_interest(principal: float, annual_rate_percent: float, years: float) -> float:
    """Interest earned under simple interest: ``P * r * t / 100``."""
    amount = ensure_non_negative(principal, "principal")
    rate = ensure_non_negative(annual_rate_percent, "annual_rate_percent")
    period = ensure_non_negative(years, "years")
    return amount * rate * period / 100


def compound_amount(
    principal: float,
    annual_rate_percent: float,
    years: float,
    compounds_per_year: int = 1,
) -> float:
    """Final amount (principal + interest) under compound interest."""
    amount = ensure_non_negative(principal, "principal")
    return amount * _growth_factor(annual_rate_percent, years, compounds_per_year)


def compound_interest(
    principal: float,
    annual_rate_percent: float,
    years: float,
    compounds_per_year: int = 1,
) -> float:
    """Interest portion only: compound amount minus the starting principal."""
    amount = ensure_non_negative(principal, "principal")
    return compound_amount(amount, annual_rate_percent, years, compounds_per_year) - amount


def effective_annual_rate(nominal_rate_percent: float, compounds_per_year: int) -> float:
    """Convert a nominal annual rate to the effective annual rate (percent)."""
    rate = ensure_non_negative(nominal_rate_percent, "nominal_rate_percent")
    n = ensure_positive_int(compounds_per_year, "compounds_per_year")
    return ((1 + rate / 100 / n) ** n - 1) * 100


def future_value(
    present_value_amount: float,
    annual_rate_percent: float,
    years: float,
    compounds_per_year: int = 1,
) -> float:
    """Grow a present amount forward (identical to :func:`compound_amount`)."""
    return compound_amount(present_value_amount, annual_rate_percent, years, compounds_per_year)


def present_value(
    future_value_amount: float,
    annual_rate_percent: float,
    years: float,
    compounds_per_year: int = 1,
) -> float:
    """Discount a future amount back to today (inverse of growth)."""
    amount = ensure_non_negative(future_value_amount, "future_value_amount")
    return amount / _growth_factor(annual_rate_percent, years, compounds_per_year)


def rule_of_72(annual_rate_percent: float) -> float:
    """Rule-of-thumb years for money to double: ``72 / rate_percent``."""
    rate = ensure_positive(annual_rate_percent, "annual_rate_percent")
    return 72 / rate


def years_to_double(annual_rate_percent: float) -> float:
    """Exact years for money to double: ``ln(2) / ln(1 + r)``."""
    rate = ensure_positive(annual_rate_percent, "annual_rate_percent")
    return math.log(2) / math.log1p(rate / 100)
