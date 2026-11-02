"""Integration-leaning tests for financekit.io using real temp files."""

from __future__ import annotations

import csv

import pytest

from financekit import ValidationError
from financekit.io import load_cashflows, save_amortization_schedule
from financekit.loans import amortization_schedule

pytestmark = pytest.mark.integration


def test_load_cashflows_happy_path(write_cashflow_csv, sample_cashflows):
    path = write_cashflow_csv(sample_cashflows)
    assert load_cashflows(path) == sample_cashflows


def test_load_cashflows_tolerates_blank_lines_and_spaces(tmp_path):
    path = tmp_path / "messy.csv"
    path.write_text("cashflow\n-1000\n\n 500 \n600\n\n", encoding="utf-8")
    assert load_cashflows(path) == [-1000.0, 500.0, 600.0]


@pytest.mark.edge
def test_load_cashflows_reports_the_offending_line(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("cashflow\n-1000\nnot-a-number\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="line 3"):
        load_cashflows(path)


@pytest.mark.edge
def test_load_cashflows_rejects_a_wrong_header(tmp_path):
    path = tmp_path / "wrong.csv"
    path.write_text("amount\n100\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="header"):
        load_cashflows(path)


@pytest.mark.edge
def test_load_cashflows_missing_file_and_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_cashflows(tmp_path / "does-not-exist.csv")
    with pytest.raises(OSError):
        load_cashflows(tmp_path)  # a directory is not a CSV file


def test_save_amortization_schedule_round_trip(tmp_path, standard_loan):
    schedule = amortization_schedule(**standard_loan)
    path = tmp_path / "schedule.csv"
    save_amortization_schedule(schedule, path)

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 12
    assert rows[0]["month"] == "1"
    assert float(rows[0]["payment"]) == pytest.approx(8884.88, abs=0.01)
    assert float(rows[-1]["balance"]) == pytest.approx(0.0, abs=0.01)
    total_principal = sum(float(r["principal"]) for r in rows)
    assert total_principal == pytest.approx(100_000, abs=0.01)
