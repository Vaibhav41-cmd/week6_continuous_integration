"""CSV input/output helpers.

Cashflow file format (one column, header required)::

    cashflow
    -10000
    4000
    5000
    6000
"""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable
from pathlib import Path

from .errors import ValidationError
from .loans import AmortizationRow

CASHFLOW_HEADER = "cashflow"
SCHEDULE_FIELDS = ("month", "payment", "principal", "interest", "balance")


def load_cashflows(path: str | Path) -> list[float]:
    """Load a one-column cashflow CSV into a list of floats.

    Blank lines are ignored.  A malformed value raises
    :class:`ValidationError` naming the offending line, so a user can fix
    their file without guessing.  A missing file raises the natural
    ``FileNotFoundError`` (deliberately not wrapped - it is already clear).
    """
    csv_path = Path(path)
    cashflows: list[float] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            raise ValidationError(
                f"{csv_path}: file is empty; expected header {CASHFLOW_HEADER!r}."
            ) from None
        if [cell.strip().lower() for cell in header] != [CASHFLOW_HEADER]:
            raise ValidationError(
                f"{csv_path}: expected header {CASHFLOW_HEADER!r}, got {header!r}."
            )
        for line_number, row in enumerate(reader, start=2):
            if not row or all(not cell.strip() for cell in row):
                continue  # tolerate blank lines anywhere in the file
            if len(row) != 1:
                raise ValidationError(
                    f"{csv_path} line {line_number}: expected one value, got {row!r}."
                )
            raw = row[0].strip()
            try:
                value = float(raw)
            except ValueError:
                raise ValidationError(
                    f"{csv_path} line {line_number}: {raw!r} is not a number."
                ) from None
            if not math.isfinite(value):
                raise ValidationError(
                    f"{csv_path} line {line_number}: {raw!r} is not a finite number."
                )
            cashflows.append(value)
    return cashflows


def save_amortization_schedule(schedule: Iterable[AmortizationRow], path: str | Path) -> None:
    """Write an amortization schedule as CSV with 2-decimal amounts."""
    csv_path = Path(path)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SCHEDULE_FIELDS))
        writer.writeheader()
        for row in schedule:
            writer.writerow(
                {
                    "month": row.month,
                    "payment": f"{row.payment:.2f}",
                    "principal": f"{row.principal_component:.2f}",
                    "interest": f"{row.interest_component:.2f}",
                    "balance": f"{row.balance:.2f}",
                }
            )
