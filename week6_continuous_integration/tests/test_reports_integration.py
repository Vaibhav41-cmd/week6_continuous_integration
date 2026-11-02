"""Integration tests: modules combined, files on disk, public package API."""

from __future__ import annotations

import pytest

import financekit
from financekit import ValidationError
from financekit.io import save_amortization_schedule
from financekit.loans import amortization_schedule
from financekit.reports import (
    analyze_cashflow_file,
    build_investment_report,
    build_loan_report,
)

pytestmark = pytest.mark.integration


def test_package_public_api_and_version():
    assert financekit.__version__ == "1.1.0"
    for name in financekit.__all__:
        assert hasattr(financekit, name), f"financekit.{name} missing"


def test_build_loan_report_combines_payment_schedule_and_summary(standard_loan):
    report = build_loan_report(**standard_loan)
    assert report["principal"] == 100_000
    assert report["monthly_payment"] == pytest.approx(8884.88, abs=0.01)
    assert len(report["schedule"]) == 12
    assert report["schedule"][-1]["balance"] == pytest.approx(0.0, abs=0.01)
    assert report["total_interest"] == pytest.approx(6618.55, abs=1.0)
    assert report["total_payment"] == pytest.approx(100_000 + report["total_interest"], abs=0.01)


def test_build_investment_report_accepts_a_good_project(sample_cashflows):
    report = build_investment_report(sample_cashflows, discount_rate=0.10)
    assert report["npv"] == pytest.approx(2276.4838467317777)
    assert report["irr"] == pytest.approx(0.2164778541842899, abs=1e-6)
    assert report["total_inflows"] == pytest.approx(15_000)
    assert report["total_outflows"] == pytest.approx(10_000)
    assert report["net_cashflow"] == pytest.approx(5_000)
    assert report["payback_period"] == 3  # cumulative turns positive in period 3
    assert report["recommendation"] == "accept"


def test_build_investment_report_rejects_a_bad_project():
    report = build_investment_report([-1_000, 500, 600], discount_rate=0.10)
    assert report["npv"] == pytest.approx(-49.586776859504255)
    assert report["recommendation"] == "reject"


def test_build_investment_report_without_an_irr():
    """All-positive flows have no IRR; the report must degrade, not explode."""
    report = build_investment_report([100, 200], discount_rate=0.10)
    assert report["irr"] is None
    assert report["npv"] > 0
    assert report["payback_period"] == 0


def test_analyze_cashflow_file_end_to_end(write_cashflow_csv, sample_cashflows):
    path = write_cashflow_csv(sample_cashflows)
    report = analyze_cashflow_file(path, discount_rate=0.10)
    assert report["recommendation"] == "accept"
    assert report["irr"] == pytest.approx(0.2164778541842899, abs=1e-6)


def test_full_user_journey(tmp_path, write_cashflow_csv, sample_cashflows, standard_loan):
    """CSV in -> investment decision; loan report -> schedule CSV out."""
    decision = analyze_cashflow_file(write_cashflow_csv(sample_cashflows), 0.10)
    assert decision["recommendation"] == "accept"

    schedule = amortization_schedule(**standard_loan)
    out_path = tmp_path / "emi_schedule.csv"
    save_amortization_schedule(schedule, out_path)
    text = out_path.read_text(encoding="utf-8")
    assert text.startswith("month,payment,principal,interest,balance")
    assert text.count("\n") >= 12


@pytest.mark.edge
def test_reports_propagate_validation_errors():
    with pytest.raises(ValidationError):
        build_loan_report(-100, 12, 12)
    with pytest.raises(ValidationError):
        build_investment_report([], 0.10)
