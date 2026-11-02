# Week 6 work log

**Project:** Continuous integration for FinanceKit 1.1.0  
**Base:** Week 3 automated-testing project  
**CI platform:** GitHub Actions

The log records implementation order, failures found while the pipeline was
being made reliable, and the evidence accepted at the end. It distinguishes
local command parity from the final hosted GitHub run, which requires the
repository owner's GitHub account.

## Session 1 — Baseline selection and audit

- Reviewed the earlier weekly projects and selected Week 3 FinanceKit because
  it already had the strongest test suite: 129 tests, known-answer financial
  oracles, integration tests and high branch coverage.
- Confirmed the library has no third-party runtime dependency and declares
  Python 3.9+ support, making a multi-version matrix meaningful.
- Copied the package, tests, examples and sample data into a clean Week 6
  repository layout rather than embedding one weekly folder inside another.
- Installed the CI toolchain: pytest, pytest-cov, Ruff, build, Twine and
  PyYAML.

## Session 2 — Lint policy and inherited-code cleanup

- Added Ruff configuration to `pyproject.toml`, targeting Python 3.9 and a
  100-character line length.
- The first run found 9 lint errors and 10 files requiring formatting. Most
  were safe modernizations: `collections.abc.Iterable`, import ordering and
  sorted `__all__` entries.
- One pytest regular-expression match triggered Ruff's `RUF043`; it was
  simplified to `match="volatility"` because that wording appears in every
  expected error message.
- Formatted the inherited code once, then reran the complete test suite to
  prove the cleanup did not change financial behaviour.

## Session 3 — Version synchronization

- Bumped package metadata to FinanceKit 1.1.0 because Week 6 is a maintenance
  and CI release of the same library.
- The first run after the bump produced one genuine test failure: the public
  report test still expected version 1.0.0.
- Updated `financekit.__version__` and the regression expectation together.
  This small failure was useful evidence that version metadata is actually
  covered by an automated check.

## Session 4 — GitHub Actions workflow design

Created `.github/workflows/ci.yml` with:

- push, pull-request, manual and weekly scheduled triggers;
- read-only default token permissions;
- same-ref concurrency cancellation;
- Ruff lint/format plus a semantic workflow validator;
- a seven-combination test matrix;
- a 95% branch-coverage quality gate;
- JUnit and coverage artifacts;
- sdist/wheel build and Twine validation;
- a tag-only GitHub Release using the already-built artifacts;
- Dependabot for GitHub Actions and pip updates.

Design decisions to defend:

- Ubuntu carries all five supported Python versions.
- Windows and macOS run current Python only, avoiding a 15-job full
  cross-product for a pure-Python package.
- `fail-fast: false` keeps all matrix results visible.
- No path filter is used, so documentation/configuration-only commits are
  also built and tested.

## Session 5 — Workflow defects found before hosting

- A draft command used `python -m Twine`; module names are case-sensitive on
  Linux. It was corrected to `python -m twine`, and the validator now checks
  that exact wording.
- PyYAML interprets the workflow key `on` as boolean `True`. The semantic
  validator accepts both representations so local validation matches GitHub's
  interpretation.
- The validator grew to 29 checks covering triggers, jobs, matrix contents,
  artifacts, coverage settings and release-permission scope.

## Session 6 — Local CI parity runner

- Built `scripts/run_ci_locally.py` with Bash and PowerShell wrappers.
- It runs workflow validation, Ruff, byte compilation, pytest/JUnit,
  coverage, distribution build and Twine in hosted order.
- First smoke run crashed when the output directory was outside the repo:
  the runner assumed `log_path.relative_to(ROOT)` would always work. It now
  falls back to an absolute display path.
- An early byte-compile warning exposed that the planned `tools/` directory
  did not exist yet. The evidence generator now occupies that directory and
  is itself linted/compiled.
- Displayed interpreter paths were normalized to `python` so logs are useful
  as portable evidence.

## Session 7 — Failure-gate proof

- Copied the project to a temporary directory and added a knowingly false
  test.
- Result: workflow validation, Ruff and byte compilation passed; pytest
  reported `1 failed, 129 passed`; the local CI returned exit code 1.
- Coverage/build did not run in default fail-fast mode.
- This test file is absent from the submitted suite, but the raw transcript
  remains in `docs/evidence/negative_ci.txt`.

## Session 8 — Build and packaging hardening

- Built `financekit-1.1.0.tar.gz` and
  `financekit-1.1.0-py3-none-any.whl` in an isolated build environment.
- Twine accepted both distributions.
- Setuptools warned that table-form license metadata is deprecated. The
  project moved to SPDX `license = "MIT"`, requires setuptools 77+, removed
  the deprecated license classifier and added the full `LICENSE` file.

## Session 9 — Evidence and documentation

- Wrote the root README, detailed pipeline guide, testing guide, evidence
  index and GitHub upload guide.
- Created `tools/generate_evidence.py`, which reruns:
  - test collection by file/marker;
  - full positive local CI;
  - the deliberate-failure copy;
  - a local Git repository and second small commit;
  - the user demo;
  - figure and JSON summary generation.
- Sanitized temporary and workspace paths from saved logs.
- During one edit sequence, parallel patches to the evidence generator left a
  duplicated file tail and an indentation error. The file was inspected,
  repaired sequentially and then passed Ruff. Later edits to the same file
  were kept sequential.

## Session 10 — Final local verification

Accepted local results:

| Check | Result |
|---|---|
| Ruff lint | 0 findings |
| Ruff formatting | All Python files formatted |
| Workflow semantic validation | 29/29 checks passed |
| Tests | 129 passed, 0 failed |
| Branch coverage | 98.44% against a 95% gate |
| Local CI stages | 8/8 passed |
| Deliberate failure | Exit code 1 with 1 failed/129 passed |
| Distributions | sdist and wheel built; Twine passed |
| Demo | Passed |

## Session 11 — Archive verification

- Cleaned caches, bytecode, `.coverage`, egg-info and other generated local
  outputs, leaving 65 intended project files.
- Built a normal submission ZIP with the project under
  `week6_continuous_integration/` and a GitHub-root ZIP whose contents extract
  directly at repository root.
- Fresh-extracted the GitHub-root archive and confirmed
  `.github/workflows/ci.yml`, `README.md`, `financekit/` and `tests/` are at
  the root with no nested weekly folder. Full local CI passed all eight
  stages and the demo completed.
- Fresh-extracted the normal archive; its 129 tests, workflow validator and
  demo passed.
- Final archives are rebuilt after this log entry so the verification record
  itself is included, and the rebuilt GitHub-root archive is extracted and
  retested before delivery.

## Remaining hosted step

The sandbox cannot authenticate to the intern's GitHub account and has no
Docker/`act` installation. Therefore no hosted pass is claimed in the local
evidence. `docs/GITHUB_UPLOAD_GUIDE.md` gives the repository-root upload,
staged commits, first/second push, optional failing-branch run, branch
protection and `v1.1.0` tag checks needed to complete hosted verification.
