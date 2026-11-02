"""Shared input validation for financekit.

Every public function validates at its boundary through these helpers, so a
bad input always produces the same exception type
(:class:`~financekit.errors.ValidationError`, a ``ValueError``) with the
offending parameter named.  Centralising the rules was the main REFACTOR
step of the TDD cycle: each rule exists exactly once and is therefore
testable through any public function.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from .errors import ValidationError


def ensure_number(value: object, name: str) -> float:
    """Return *value* as a finite float, rejecting bools/strings/NaN/inf."""
    # bool is a subclass of int - True silently becoming 1.0 is never intended.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number, got {type(value).__name__}.")
    number = float(value)
    if not math.isfinite(number):
        raise ValidationError(f"{name} must be finite, got {value!r}.")
    return number


def ensure_non_negative(value: object, name: str) -> float:
    """Return *value* as a float, requiring ``value >= 0``."""
    number = ensure_number(value, name)
    if number < 0:
        raise ValidationError(f"{name} must not be negative, got {number}.")
    return number


def ensure_positive(value: object, name: str) -> float:
    """Return *value* as a float, requiring ``value > 0``."""
    number = ensure_number(value, name)
    if number <= 0:
        raise ValidationError(f"{name} must be positive, got {number}.")
    return number


def ensure_positive_int(value: object, name: str) -> int:
    """Return *value* unchanged, requiring a genuine positive ``int``."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{name} must be a positive integer, got {value!r}.")
    if value <= 0:
        raise ValidationError(f"{name} must be a positive integer, got {value}.")
    return value


def ensure_series(values: Iterable[float], name: str, *, min_length: int = 1) -> list[float]:
    """Materialise *values* into a list of finite floats of a minimum length."""
    if isinstance(values, (str, bytes)):
        raise ValidationError(f"{name} must be a sequence of numbers, not a string.")
    try:
        items = list(values)
    except TypeError:
        raise ValidationError(f"{name} must be a sequence of numbers.") from None
    if len(items) < min_length:
        raise ValidationError(
            f"{name} must contain at least {min_length} value(s), got {len(items)}."
        )
    return [ensure_number(item, f"{name}[{index}]") for index, item in enumerate(items)]


def ensure_rate_decimal(rate: object, name: str = "rate") -> float:
    """Return a decimal rate, requiring ``rate > -1``.

    At a rate of -1 (-100%) the discount factor ``1 + rate`` is zero and
    every NPV-style formula divides by zero; below -1 it changes sign each
    period, which is meaningless for discounting.
    """
    number = ensure_number(rate, name)
    if number <= -1:
        raise ValidationError(f"{name} must be greater than -1 (-100%), got {number}.")
    return number
