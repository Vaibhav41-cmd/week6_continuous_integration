# FinanceKit CI pipeline documentation

## 1. Purpose

Week 6 turns the Week 3 test-driven FinanceKit library into a project with a
repeatable, hosted quality gate. The selected CI provider is **GitHub
Actions**, configured in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

The pipeline answers five questions on every relevant change:

1. Is the code lint-clean and consistently formatted?
2. Do all 129 tests pass on the supported Python/OS combinations?
3. Does branch coverage remain at or above 95%?
4. Can a clean source distribution and wheel be built and validated?
5. If the commit is a version tag, can the tested distributions be released?

A green run means all required answers are yes. A failing command returns a
non-zero exit code, its GitHub Actions step fails, dependent jobs do not
proceed as though the gate had passed, and branch protection can prevent the
change from merging.

## 2. Pipeline at a glance

```text
push / pull request / manual / weekly schedule
                         │
                         ▼
                 Lint and format
              workflow validator + Ruff
                         │
                         ▼
        ┌────────────────────────────────┐
        │ Test matrix: 7 combinations    │
        │ Ubuntu 3.9, 3.10, 3.11, 3.12, │
        │ 3.13; Windows 3.13; macOS 3.13 │
        └────────────────────────────────┘
                         │
                         ▼
              Coverage quality gate
                 branch ≥ 95%
                         │
                         ▼
          Build sdist + wheel, Twine check
                         │
                 only for v* tags
                         ▼
                 GitHub Release
```

A normal non-tag push creates **10 job instances**: one lint, seven test,
one coverage and one build. The release job is skipped unless the ref is a
version tag.

## 3. Why GitHub Actions?

| Consideration | Reason for the choice |
|---|---|
| Repository integration | The internship already requires a GitHub repository, so no separate CI account/webhook is needed |
| Matrix support | Multiple Python versions and operating systems are first-class workflow features |
| Artifacts | JUnit, coverage and distribution files can be attached directly to each run |
| Permissions | The built-in token can default to read-only and be widened only for release |
| Local parity | Every command is an ordinary Python/Ruff/pytest/build invocation that can be reproduced locally |
| Cost/availability | Public repositories can use hosted runners without maintaining a CI server |

Travis CI or CircleCI could implement the same gates, but would add another
service and separate status integration for no functional advantage here.

## 4. Workflow anatomy

### 4.1 Triggers

```yaml
on:
  push:
  pull_request:
  workflow_dispatch:
  schedule:
    - cron: "17 3 * * 1"
```

- **Push** is the primary Week 6 requirement: each pushed commit starts CI.
- **Pull request** gives reviewers the same result before merge.
- **Manual dispatch** helps diagnose infrastructure or rerun after a transient
  hosted-runner issue.
- **Schedule** runs every Monday at 03:17 UTC to catch dependency or runner
  drift even when nobody commits. The build job is skipped for scheduled
  runs because their purpose is regression detection.

No `paths:` filter is used. That costs a little runner time on a
documentation-only change, but it makes “every commit is verified” literally
true and also validates documentation examples, packaging metadata and the
workflow itself whenever they change.

### 4.2 Concurrency and permissions

```yaml
permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

If a developer pushes three commits quickly to the same branch, obsolete
in-progress runs are cancelled and only the newest ref state must finish.
This saves time without weakening the final gate.

The workflow token starts read-only. Only the release job receives
`contents: write`, and only after its tag condition and build dependency are
satisfied. Lint/test/coverage/build do not need repository write access.

### 4.3 Lint and format job

**Runner:** `ubuntu-latest`  
**Python:** 3.13  
**Timeout:** 10 minutes

Commands, in order:

```bash
python -m pip install "ruff==0.17.3" "PyYAML==6.0.3"
python scripts/validate_workflow.py
ruff check --output-format=github .
ruff format --check .
```

Ruff configuration lives in `pyproject.toml`:

- target Python 3.9, the oldest supported interpreter;
- line length 100;
- rule families `E`, `F`, `I`, `UP`, `B`, `SIM` and `RUF`;
- quote style and formatting are deterministic;
- the demo has a narrow per-file allowance for its path bootstrap import.

`ruff check` catches unused imports, syntax/style errors, import ordering,
outdated Python idioms and common bug patterns. `ruff format --check` never
rewrites code in CI; it fails when the committed formatting would change,
forcing the developer to run the formatter locally and commit the result.

The workflow validator checks semantics that YAML syntax alone cannot: the
required triggers/jobs exist, the matrix includes the intended combinations,
JUnit is produced, artifacts upload on failure, coverage is set to 95%, and
release write permission remains scoped.

### 4.4 Test matrix job

Combinations:

| Operating system | Python versions | Rationale |
|---|---|---|
| Ubuntu | 3.9, 3.10, 3.11, 3.12, 3.13 | Full supported interpreter range on the fastest/common Linux runner |
| Windows | 3.13 | Current-version path/filesystem compatibility |
| macOS | 3.13 | Current-version Unix/macOS compatibility |

This is a seven-combination **risk-based matrix**, not a 15-combination full
cross-product. FinanceKit is pure Python with no compiled extensions, so the
highest-value variation is interpreter version first and current-version OS
behaviour second.

Important settings:

- `fail-fast: false` — if Python 3.9 fails, Windows and macOS still report,
  making version-specific versus platform-specific failures visible.
- pip caching keys on `requirements-ci.txt`.
- the package itself is installed editable, so tests import the checkout.
- `compileall` catches syntax errors in examples/scripts/tools that pytest
  collection might not import.
- pytest writes one JUnit XML report per matrix combination.

Representative command:

```bash
python -m pytest -vv \
  --junitxml=test-results/junit-ubuntu-latest-3.13.xml
```

`pyproject.toml` contains `addopts = "-q --strict-markers"`. Local/hosted
commands use `-vv`, resulting in named test output while retaining strict
marker checking.

### 4.5 Coverage job

The coverage job depends on both lint and the full test matrix. It reruns the
suite on Ubuntu/Python 3.13 with branch coverage:

```bash
python -m pytest -vv \
  --cov=financekit \
  --cov-branch \
  --cov-fail-under=95 \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml \
  --cov-report=html:htmlcov \
  --junitxml=test-results/junit-coverage.xml
```

Current verified result:

```text
TOTAL  311 statements, 3 missed, 74 branches, 3 partial
Required test coverage of 95% reached. Total coverage: 98.44%
```

Coverage is a floor against untested growth, not a claim that 98.44% of all
possible behaviour is correct. The inherited suite contains known-value,
inverse-property, boundary and integration tests, which are required to make
the percentage meaningful.

### 4.6 Build job

After lint, tests and coverage pass:

```bash
python -m build
python -m twine check dist/*
```

This produces:

- `financekit-1.1.0.tar.gz` (source distribution);
- `financekit-1.1.0-py3-none-any.whl` (wheel).

`python -m build` uses an isolated build environment, reducing “works because
my laptop already had setuptools/plugins installed” risk. Twine validates
distribution metadata/readme rendering without uploading anything.

### 4.7 Release job

Condition:

```yaml
if: startsWith(github.ref, 'refs/tags/v')
```

For a tag such as `v1.1.0`, the job downloads the already-tested
`python-distributions` artifact and creates a GitHub Release with generated
notes. It does **not** rebuild from a different checkout state, and it does
not publish to PyPI. PyPI deployment would require a separate trusted
publisher/credential decision.

## 5. How failure propagates

GitHub Actions does not need a special “fail pipeline” instruction. Ordinary
process semantics provide it:

```text
pytest finds a failed assertion
        ↓
pytest exits 1
        ↓
the Run test suite step is marked failed
        ↓
that matrix job is failed; workflow is failed
        ↓
coverage/build dependent jobs do not run as successful gates
        ↓
branch protection blocks merge
```

The deliberate-failure experiment in the evidence generator copies the
project to a temporary directory, adds a knowingly false test, and runs the
local CI. The captured result is:

- workflow validation: passed;
- Ruff checks: passed;
- pytest stage: **failed with exit code 1**;
- local CI overall: **failed**;
- coverage/build stages: not reached in default fail-fast local mode.

The broken file is not present in the submitted project. To repeat it on
GitHub, use a throwaway branch and delete that branch afterwards, as described
in §10.

## 6. Run CI locally

### 6.1 One-command equivalent

```bash
python -m pip install -r requirements-dev.txt
python -m pip install --editable .
python scripts/run_ci_locally.py
```

Or let the runner install first:

```bash
python scripts/run_ci_locally.py --install
```

The runner writes:

```text
local-ci-output/
├── local-ci-summary.json
├── logs/
├── test-results/
├── coverage.xml
├── htmlcov/
└── dist/
```

Options:

| Option | Effect |
|---|---|
| `--skip-build` | Stop after coverage; useful during a quick edit |
| `--keep-going` | Continue after a failed stage for diagnostics; final exit remains non-zero |
| `--output-dir PATH` | Put logs/reports somewhere else |
| `--install` | Install development requirements and editable package first |

### 6.2 Why local CI is not identical to GitHub Actions

The local runner proves the exact quality-gate commands but cannot reproduce:

- GitHub's Windows/macOS hosted images;
- multiple Python installations unless they exist locally;
- GitHub token permissions and artifact-service behaviour;
- webhook delivery/concurrency.

Docker/`act` was not available in the internship sandbox. Therefore the
submission distinguishes **local command evidence** from the final hosted
check after upload. This is more honest than generating a fake GitHub
screenshot.

## 7. Replicate the environment from a clean clone

Prerequisites: Git and Python 3.9 or newer.

```bash
git clone https://github.com/Vaibhav41-cmd/week6_continuous_integration.git
cd week6_continuous_integration
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install --editable .
python scripts/run_ci_locally.py
```

Windows activation:

```powershell
.venv\Scripts\Activate.ps1
```

No application secrets are required. FinanceKit has no runtime dependency;
CI tools are development-only. The only hosted credential is GitHub's
automatic `GITHUB_TOKEN`, used read-only except in the tag release job.

## 8. View hosted logs and artifacts

### GitHub web interface

1. Open the repository.
2. Select **Actions**.
3. Select workflow **CI**.
4. Open the run for the commit SHA.
5. Select a job, then expand a step to read its log.
6. Scroll to **Artifacts** to download JUnit, coverage or distributions.

A red test step retains its pytest traceback in the log and its JUnit XML in
the artifact because upload uses `if: always()`.

### GitHub CLI

After installing/authenticating `gh`:

```bash
gh run list --workflow CI --limit 10
gh run view <run-id>
gh run view <run-id> --log-failed
gh run download <run-id> --name coverage-report --dir downloaded-coverage
gh run rerun <run-id> --failed
```

Use a rerun only for a suspected transient runner/network failure. A real
test or lint failure should be fixed in a new commit so history shows the
correction.

## 9. Trigger the pipeline deliberately

### Normal small change

```bash
git checkout -b docs/ci-verification
# Make a small README or documentation correction.
git add README.md
git commit -m "docs: verify CI trigger"
git push -u origin docs/ci-verification
```

Open **Actions → CI** and record:

- triggering branch and commit SHA;
- event (`push`);
- all job names and conclusions;
- total duration;
- artifact names.

Then open a pull request if you also want to verify the `pull_request` event
and branch-protection checks.

### Manual run

In **Actions → CI → Run workflow**, choose the branch and run it. This is
`workflow_dispatch`; it is useful for infrastructure diagnosis but does not
replace a push-trigger verification.

## 10. Deliberate failure on a throwaway branch

Do not do this on `main`.

```bash
git checkout -b experiment/failing-ci
cat > tests/test_ci_gate_experiment.py <<'PY'
def test_ci_gate_deliberately_fails():
    assert False, "Intentional Week 6 failure-gate experiment"
PY
git add tests/test_ci_gate_experiment.py
git commit -m "test: deliberately verify red CI gate"
git push -u origin experiment/failing-ci
```

Expected hosted result:

- lint may pass if the file is formatted;
- each test matrix job fails at pytest;
- JUnit artifacts still upload;
- coverage/build do not complete successfully;
- the workflow conclusion is **failure**.

Restore by deleting the branch locally and remotely:

```bash
git checkout main
git branch -D experiment/failing-ci
git push origin --delete experiment/failing-ci
```

The local equivalent is already captured in `docs/evidence/negative_ci.txt`,
without polluting the submitted test suite.

## 11. Branch protection

After the first hosted run, configure **Settings → Branches → Add classic
branch protection rule** for `main`:

- Require a pull request before merging.
- Require status checks to pass before merging.
- Require branches to be up to date before merging.
- Select: `Lint and format (Ruff)`, all seven `Test (...)` jobs,
  `Coverage quality gate`, and `Build distributions`.
- Block force pushes.

Without this step, CI is advisory. With it, a red run becomes a merge gate.

## 12. Dependency maintenance

`.github/dependabot.yml` proposes weekly updates for:

- GitHub Actions versions;
- pip development/CI requirements.

The workflow pins Ruff, build and Twine in their install steps for
reproducibility. Pip requirement ranges preserve the Python 3.9 floor:

- pytest 8.x on Python 3.9, pytest 9.x on 3.10+;
- pytest-cov compatible ranges by interpreter.

That compatibility marker is intentional. Installing the newest pytest
unconditionally would silently abandon the declared Python 3.9 support.

## 13. Challenges encountered and resolutions

| Challenge | Symptom | Resolution / lesson |
|---|---|---|
| Ruff's default 88-column style conflicted with inherited code | Many purely formatting diffs before any semantic issue | Set an explicit 100-column project policy, ran the formatter once, then treated future drift as a gate |
| Inherited lint findings | Unsorted `__all__`, `typing.Iterable`, unused directives and a regex-match warning | Applied safe fixes and simplified one pytest match; no mathematical behaviour changed |
| Version synchronization | `pyproject.toml` was bumped to 1.1.0 while the public API/test expected 1.0.0 | Updated `financekit.__version__` and its regression test together; CI immediately caught the mismatch |
| YAML `on:` parsing | PyYAML interpreted the trigger key as boolean `True` in the validator | Validator accepts both `workflow["on"]` and `workflow[True]`; GitHub itself parses the workflow correctly |
| Twine module case | A draft used `python -m Twine`; Linux module names are case-sensitive | Corrected to `python -m twine` and added the exact string to workflow validation |
| Python 3.9 tool floor | Latest pytest/pytest-cov lines target newer interpreters | Used environment markers in `requirements-ci.txt` and tested 3.9 explicitly |
| Matrix cost | A full 3-OS × 5-Python matrix would create 15 jobs for a pure-Python library | Used seven risk-based combinations: all versions on Ubuntu, current version on all OSes |
| Build metadata deprecation | Setuptools warned about table-form license metadata | Modernized to SPDX `license = "MIT"`, setuptools ≥77 and added `LICENSE` |
| Local output outside repo | First local-runner version failed when `--output-dir` was `/tmp` because it assumed a repo-relative log path | Display path now falls back to an absolute path; the bug was found by a smoke run |
| `compileall` warning | A planned `tools/` path did not yet exist | The final project includes `tools/generate_evidence.py`; CI byte-compiles it |
| No Docker/`act` or GitHub credentials in sandbox | Hosted workflow could not be executed from the authoring environment | Built local parity runner, semantic validator and Git simulation; hosted push remains the documented final check rather than a fabricated screenshot |
| Pytest verbosity interaction | Project `addopts` already contains `-q` | CI/local commands use `-vv`, yielding individual test names in logs while strict markers remain enabled |

## 14. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Workflow does not appear | `.github` was nested or not pushed | Confirm `.github/workflows/ci.yml` is at repository root and committed |
| CI badge is grey/no status | Wrong owner/repo/workflow filename or no run yet | Push a commit; update the badge URL if the repo name differs |
| Ruff format job fails | Code was not formatted before commit | Run `python -m ruff format .`, inspect diff, rerun check and commit |
| One Python version fails only | Interpreter compatibility or tool range issue | Open that matrix job; check `requires-python`, syntax and requirements markers |
| Windows-only failure | Path separator/newline assumption | Run the specific test locally if possible; use `pathlib` and explicit encodings |
| Coverage job fails at 94.x% | New uncovered branches | Open `htmlcov/index.html` from the artifact and add tests; do not lower the gate reflexively |
| Build cannot fetch setuptools | Transient network/runner issue | Inspect the isolated-build log and rerun failed jobs once |
| Release job skipped | Ref is a branch, not a `v*` tag, or build failed | Push an annotated version tag after fixing required jobs |
| Release already exists | Tag/release was created previously | Use a new version tag; do not overwrite published release assets casually |
| JUnit artifact missing | Pytest failed before writing reports or path changed | Check the test step working directory and `--junitxml` path; artifact step warns rather than hides this |

## 15. Security and reliability practices in the workflow

- Read-only default token permission.
- Write permission scoped to tag release.
- No third-party release action; GitHub CLI uses the automatic token.
- Official GitHub actions are version-pinned by major release and maintained
  through Dependabot.
- Timeouts prevent a hung job from consuming a runner indefinitely.
- Concurrency cancels superseded runs for the same ref.
- Isolated distribution builds reduce dependence on runner preinstalled
  packaging tools.
- Artifacts have finite retention.

## 16. What “done” means for Week 6

The hosted setup is complete when a fresh push shows:

- one green lint job;
- seven green test jobs;
- one green coverage job at or above 95%;
- one green build job with `python-distributions` artifact;
- JUnit/coverage artifacts downloadable from the run;
- a second small push creating a second run;
- optionally, a red run on a throwaway failing branch; and
- branch protection requiring these checks on `main`.
