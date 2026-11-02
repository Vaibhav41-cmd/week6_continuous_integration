# Week 6 evidence index

This page links every Week 6 requirement to the configuration or generated
evidence that demonstrates it. Paths are relative to the repository root.

## Requirement traceability

| Week 6 requirement | Evidence |
|---|---|
| Start from a previous or new Python project with automated tests | FinanceKit 1.1.0 under `financekit/`; 129 tests under `tests/`; `docs/evidence/pytest_collect.txt` |
| Select a public CI platform | GitHub Actions workflow `.github/workflows/ci.yml` |
| Automate code linting | `ruff check` + `ruff format --check`; `docs/evidence/ruff_lint.txt`; `docs/evidence/ruff_format.txt` |
| Run the test suite automatically | GitHub matrix in `.github/workflows/ci.yml`; `docs/evidence/pytest_full.txt`; `docs/evidence/local_ci_positive.txt` |
| Generate a test report | JUnit XML in every matrix job; local sample `docs/evidence/junit-local.xml`; coverage `docs/evidence/coverage.xml` |
| Pipeline fails when a test fails | `docs/evidence/negative_ci.txt`: 129 passed, 1 deliberately failed, local CI exit code 1 |
| Trigger on every commit/push | `push` and `pull_request` workflow triggers; `docs/evidence/git_trigger_simulation.txt`; hosted screenshot/log after first push |
| Explain setup and replication | `README.md`; `docs/CI_PIPELINE.md`; `docs/GITHUB_UPLOAD_GUIDE.md` |
| Document challenges | `docs/CI_PIPELINE.md` §13 and `docs/WORK_LOG.md` |
| Final verification and logs/screenshots | Figures 1–6 under `docs/evidence/figures/` plus raw text logs listed below |
| Submit codebase, CI config and documentation | Project ZIP / GitHub-root ZIP prepared for this week's submission |

## Figures

| File | Contents |
|---|---|
| `docs/evidence/figures/fig01_ci_pipeline.png` | Trigger → lint → matrix → coverage → build → tag-only release flow |
| `docs/evidence/figures/fig02_tests_and_coverage.png` | 129 tests by file and combined coverage by module |
| `docs/evidence/figures/fig03_test_matrix.png` | Seven OS/Python matrix combinations |
| `docs/evidence/figures/fig04_local_ci_pass.png` | Positive local CI stage summary |
| `docs/evidence/figures/fig05_negative_ci.png` | Deliberate-failure experiment and exit code 1 |
| `docs/evidence/figures/fig06_stage_durations.png` | Local stage duration profile |

These are generated evidence panels, not decorative mock-ups. Their numbers
come from `results/ci_summary.json` and the raw logs below.

## Raw evidence files

| File | What it proves |
|---|---|
| `environment.txt` | Python/platform and tool versions used for local evidence |
| `workflow_validation.txt` | 29 semantic workflow checks passed |
| `ruff_lint.txt` | Ruff reports no lint findings |
| `ruff_format.txt` | All project Python files satisfy the formatter |
| `pytest_collect.txt` | 129 total tests and marker counts (104 unit, 14 integration, 58 edge) |
| `pytest_full.txt` | Named 129-test run with JUnit generation |
| `junit-local.xml` | Machine-readable positive test report (`tests=129`, `failures=0`) |
| `coverage.txt` | Branch coverage run: 98.44%, gate 95% |
| `coverage.xml` | Machine-readable coverage report equivalent to the hosted artifact |
| `local_ci_positive.txt` | Complete positive local CI output, including build and Twine |
| `local_ci_summary.txt` | Sanitized stage-by-stage local CI summary |
| `ci_stage_timings.csv` | Durations used in Figure 6 |
| `build_and_twine.txt` | sdist/wheel creation and Twine `PASSED` checks |
| `negative_ci.txt` | Temporary broken test, `1 failed, 129 passed`, overall local CI failed |
| `git_trigger_simulation.txt` | Clean local Git commits and post-commit local CI pass |
| `demo_output.txt` | FinanceKit user-journey demo still works after CI maintenance |
| `verification_summary.txt` | One-page numeric summary |

Machine-readable totals are consolidated in `results/ci_summary.json`.

## Reproduce everything

From a clean clone:

```bash
python -m pip install -r requirements-evidence.txt
python -m pip install --editable .
python tools/generate_evidence.py
```

The generator is intentionally transparent: it executes the local CI, creates
a temporary broken copy, creates a temporary Git repository, and renders the
figures from those actual results. Temporary paths are replaced with labels
such as `<local-ci-output>` in saved logs.

## Hosted evidence after upload

The authoring sandbox has no GitHub credentials or Docker/`act`, so it does
not fabricate a GitHub Actions screenshot. After following
`docs/GITHUB_UPLOAD_GUIDE.md`, add or retain the following hosted evidence in
the submission:

1. Actions run URL for the first push.
2. Screenshot showing lint, seven test jobs, coverage and build.
3. Actions run URL for a second small commit.
4. Artifact list showing JUnit, coverage and Python distributions.
5. If convenient, a red run URL from the throwaway failing branch.

The local evidence proves the commands and failure semantics; the hosted run
proves GitHub's webhook and runners accepted the same workflow.
