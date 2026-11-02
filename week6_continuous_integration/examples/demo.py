#!/usr/bin/env python3
"""Runnable tour of financekit - every printed value is asserted by the tests.

python examples/demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import financekit as fk


def main() -> int:
    print(f"financekit {fk.__version__} demo")
    print("-" * 60)

    print("Simple interest 10,000 @ 5% for 2y :", fk.simple_interest(10_000, 5, 2))
    print("Compound amount 10,000 @12% monthly:", round(fk.compound_amount(10_000, 12, 1, 12), 2))
    print(
        "Years to double @ 8% (exact)      :",
        round(fk.years_to_double(8), 2),
        "| rule of 72:",
        fk.rule_of_72(8),
    )

    report = fk.build_loan_report(100_000, 12, 12)
    print(
        "\nLoan Rs.1,00,000 @12% x 12 months  : EMI",
        report["monthly_payment"],
        "| total interest",
        report["total_interest"],
    )
    print("First instalment                  :", report["schedule"][0])
    print("Last instalment                   :", report["schedule"][-1])

    sample = Path(__file__).resolve().parents[1] / "data" / "sample_cashflows.csv"
    decision = fk.analyze_cashflow_file(sample, discount_rate=0.10)
    print("\nProject in data/sample_cashflows.csv")
    print("NPV @10%                          :", round(decision["npv"], 2))
    print("IRR                               :", f"{decision['irr']:.2%}")
    print("Payback period                    :", decision["payback_period"])
    print("Recommendation                    :", decision["recommendation"].upper())

    returns = [0.02, -0.01, 0.03, 0.005]
    print("\nMonthly returns                   :", returns)
    print("Cumulative return                 :", f"{fk.cumulative_return(returns):.2%}")
    print("Sharpe ratio                      :", round(fk.sharpe_ratio(returns), 3))
    print(
        "Max drawdown of demo prices       :",
        f"{fk.max_drawdown([100, 110, 105, 120, 90, 95]):.0%}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
