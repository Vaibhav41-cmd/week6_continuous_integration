"""Exceptions raised by financekit."""

from __future__ import annotations


class ValidationError(ValueError):
    """Raised when an input violates a financial or mathematical constraint.

    Subclassing ValueError keeps the library idiomatic: existing code that
    catches ValueError keeps working, while callers who care can catch the
    more specific type.
    """
