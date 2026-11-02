"""Shared pytest fixtures for the financekit suite.

Fixtures live here (rather than being copied into test modules) so that the
*arrange* step of dozens of tests is defined exactly once - itself one of
the maintainability points this Week 3 exercise is meant to demonstrate.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_cashflows() -> list[float]:
    """A conventional project: outflow first, then three inflows."""
    return [-10_000.0, 4_000.0, 5_000.0, 6_000.0]


@pytest.fixture
def sample_returns() -> list[float]:
    """Four monthly returns (decimals) with hand-computable statistics."""
    return [0.02, -0.01, 0.03, 0.005]


@pytest.fixture
def sample_prices() -> list[float]:
    """Price path with an obvious 25% peak-to-trough drawdown (120 -> 90)."""
    return [100.0, 110.0, 105.0, 120.0, 90.0, 95.0]


@pytest.fixture
def standard_loan() -> dict[str, float | int]:
    """Rs. 1,00,000 at 12% for 12 months - the suite's reference loan."""
    return {"principal": 100_000.0, "annual_rate_percent": 12.0, "months": 12}


@pytest.fixture
def write_cashflow_csv(tmp_path: Path):
    """Factory fixture: write cashflows to a real temp CSV and return its path."""

    def _write(cashflows, name: str = "cashflows.csv") -> Path:
        path = tmp_path / name
        lines = ["cashflow"] + [str(value) for value in cashflows]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    return _write
