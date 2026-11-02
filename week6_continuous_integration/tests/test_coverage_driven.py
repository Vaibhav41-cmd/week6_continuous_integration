"""Coverage-driven tests added in the final TDD cycle.

After the first GREEN run, branch coverage stood at 94% and the missing
lines pointed at *behaviour that existed but had never been exercised*:
IRR roots above 100% (the bracket-widening loop), empty / malformed CSV
files, a project that never pays back, and series validation reached only
via non-sequence inputs.  These tests close those specific gaps; the few
remaining defensive lines are analysed in TEST_DOCUMENTATION.md.
"""

from __future__ import annotations

import pytest

from financekit import ValidationError
from financekit.investments import irr, npv
from financekit.io import load_cashflows
from financekit.reports import build_investment_report

pytestmark = pytest.mark.edge


def test_irr_above_one_hundred_percent_widens_the_bracket():
    """-1 then +3 is a 200% return: NPV is still positive at r=100%."""
    assert irr([-1, 3]) == pytest.approx(2.0, abs=1e-6)


def test_irr_exactly_one_hundred_percent():
    assert irr([-100, 200]) == pytest.approx(1.0, abs=1e-9)


def test_investment_report_for_a_project_that_never_pays_back():
    report = build_investment_report([-1_000, 100, 100], discount_rate=0.10)
    assert report["payback_period"] is None
    assert report["recommendation"] == "reject"
    assert report["net_cashflow"] == pytest.approx(-800.0)


@pytest.mark.parametrize(
    "file_text, message",
    [
        ("", "empty"),
        ("cashflow\n10,20\n", "expected one value"),
        ("cashflow\nnan\n", "not a finite number"),
        ("cashflow\ninf\n", "not a finite number"),
    ],
)
def test_load_cashflows_rejects_structurally_bad_files(tmp_path, file_text, message):
    path = tmp_path / "broken.csv"
    path.write_text(file_text, encoding="utf-8")
    with pytest.raises(ValidationError, match=message):
        load_cashflows(path)


@pytest.mark.parametrize("bad_series", ["123", 123, None, b"123"])
def test_series_validation_rejects_non_sequences(bad_series):
    with pytest.raises(ValidationError):
        npv(0.10, bad_series)  # type: ignore[arg-type]
