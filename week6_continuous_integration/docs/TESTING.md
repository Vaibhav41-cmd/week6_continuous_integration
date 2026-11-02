# FinanceKit test suite and CI test strategy

## Purpose

Week 6 deliberately reuses the mature Week 3 FinanceKit test suite instead of
writing a small demonstration suite merely to make a pipeline turn green.
That gives CI something meaningful to protect: 129 tests covering financial
formulas, validation, file I/O and end-to-end reports, with 98.44% branch
coverage.

## Suite inventory

| Test file | Tests | Main behaviour |
|---|---:|---|
| `test_interest.py` | 29 | Simple/compound interest, present/future value, effective rate, doubling time and invalid inputs |
| `test_investments.py` | 32 | NPV, IRR, CAGR, SIP/required saving and invalid cashflows |
| `test_loans.py` | 18 | EMI, amortization schedule invariants, zero interest and invalid terms |
| `test_statistics.py` | 25 | Mean, variance/standard deviation, cumulative return, Sharpe, drawdown and correlation |
| `test_io.py` | 6 | Cashflow CSV parsing and amortization CSV round-trip |
| `test_reports_integration.py` | 8 | Public API, combined loan/investment reports and full user journey |
| `test_coverage_driven.py` | 11 | Additional IRR/file/series branches found through coverage analysis |
| **Total** | **129** |  |

Marker collection (markers overlap):

| Marker | Collected | Meaning |
|---|---:|---|
| `unit` | 104 | Isolated function behaviour |
| `integration` | 14 | Multiple modules or real file I/O |
| `edge` | 58 | Boundary/error conditions |

Run subsets with:

```bash
python -m pytest -m unit -q
python -m pytest -m integration -q
python -m pytest -m edge -q
```

CI runs the complete suite; markers are for developer diagnosis, not for
excluding inconvenient tests from the hosted gate.

## Why these tests are suitable for CI

### Deterministic and fast

The library uses no network, random data, current date, external service or
large fixture generation. The full suite takes well under one second of test
execution on the evidence machine, excluding environment startup. That makes
a seven-combination matrix practical.

### Known answers, not only “does not crash”

Examples include:

- ₹10,000 at 5% simple interest for two years returns ₹1,000;
- a ₹100,000, 12%, 12-month loan has an EMI of approximately ₹8,884.88;
- schedule principal components sum back to the loan principal and the final
  balance is zero;
- +10% followed by −10% gives a cumulative return of −1%, not zero;
- the IRR result is substituted back into NPV and shown to zero it;
- present value and future value are inverse operations.

These test oracles catch formula regressions that a smoke test would miss.

### Boundary and error behaviour

Invalid values are expected to raise `ValidationError`, including negative
principal/rates where appropriate, zero months, non-integer terms, NaN cashflows,
mismatched series, impossible returns and malformed CSV files. In CI this is
important because a refactor can preserve happy paths while silently weakening
validation.

### Integration path

The full-journey test writes a cashflow CSV, analyzes it, builds a loan report
and writes a schedule CSV. It exercises the package in the sequence a user
would, including temporary filesystem paths that are relevant to Windows and
macOS matrix runs.

## Coverage

Command:

```bash
python -m pytest \
  --cov=financekit \
  --cov-branch \
  --cov-fail-under=95 \
  --cov-report=term-missing
```

Current result:

| Module | Branch coverage |
|---|---:|
| `__init__.py` | 100% |
| `errors.py` | 100% |
| `interest.py` | 100% |
| `investments.py` | 92% |
| `io.py` | 100% |
| `loans.py` | 100% |
| `reports.py` | 100% |
| `statistics.py` | 100% |
| `validation.py` | 100% |
| **Total** | **98.44%** |

The uncovered investment lines are retained in reports rather than hidden by
`skip_covered`. CI's 95% floor allows a small, reviewed margin while preventing
a substantial untested change from landing unnoticed.

## CI test reports

Every matrix job writes JUnit XML:

```bash
python -m pytest -vv \
  --junitxml=test-results/junit-<os>-<python>.xml
```

The workflow uploads these files with `if: always()`. A developer can therefore
download the report for the exact failing OS/interpreter combination instead
of relying only on a copied console snippet.

The local runner writes equivalent files under:

```text
local-ci-output/test-results/
```

## Failure-gate experiment

The evidence generator creates a temporary copy and adds:

```python
def test_ci_gate_deliberately_fails():
    assert False, "Intentional Week 6 failure-gate experiment"
```

It then runs `scripts/run_ci_locally.py --skip-build`. Expected result:

```text
Workflow structure validation: passed
Ruff lint:                     passed
Ruff format check:             passed
Byte-compile sources:          passed
Pytest with JUnit report:      failed (exit 1; 129 passed, 1 failed)
Overall:                       failed
```

This proves the runner and test command do not swallow pytest's exit code.
On GitHub, that same non-zero pytest process marks the step/job/run failed.

## Adding a test

1. Put unit tests beside the corresponding module test file.
2. Prefer a known value, algebraic inverse or invariant as the oracle.
3. Add an invalid-input case when a new validation branch is introduced.
4. Use existing markers; `--strict-markers` makes a typo fail collection.
5. Run the focused test, then the full local CI:

```bash
python -m pytest tests/test_interest.py -vv
python scripts/run_ci_locally.py
```

6. Check whether coverage reports identify a missed branch before pushing.

## Limits

- Tests are not property-based; selected examples and invariants dominate.
- Only the current Python version is exercised on Windows/macOS.
- Coverage does not measure whether assertions are strong. Mutation testing
  was explored in Week 3 as spot checks but is not a continuous Week 6 gate.
- Hosted performance can vary with GitHub runner load; the suite is fast
  enough that installation dominates elapsed job time.
