# GitHub upload and hosted CI verification guide

This guide uploads the Week 6 project **at the repository root** and verifies
that GitHub Actions actually triggers. Repository-root placement matters:
GitHub only reads workflows from `.github/workflows/` at the root, and the
README's relative links assume that layout.

Suggested repository name: `week6_continuous_integration`  
Suggested URL: `https://github.com/Vaibhav41-cmd/week6_continuous_integration`

## 1. Use the correct ZIP

Use `week6_continuous_integration_github_root.zip`. It extracts files such as:

```text
.github/workflows/ci.yml
README.md
financekit/
tests/
docs/
```

Do **not** upload the normal submission ZIP's outer folder as the repository
root. If extraction creates a folder named
`week6_continuous_integration_github_root`, enter that folder and use its
contents as the repository contents.

Do not use GitHub's “Upload files” page for the whole project: it can hide
the `.github` directory and creates an unhelpful single bulk commit. Use Git
locally so the project history shows the CI work being built in stages.

## 2. Create the empty GitHub repository

1. Open <https://github.com/new>.
2. Owner: `Vaibhav41-cmd`.
3. Repository name: `week6_continuous_integration`.
4. Description: `GitHub Actions CI for the FinanceKit Python library: Ruff, 129-test matrix, 95% coverage gate and package builds.`
5. Select **Public**.
6. Leave “Add a README”, `.gitignore` and licence unchecked—the project
   already contains them.
7. Create the repository.

## 3. Initialise Git locally

From the extracted repository-root directory:

```bash
git init -b main
git config user.name "Vaibhav Desale"
git config user.email "YOUR-GITHUB-EMAIL"
git remote add origin https://github.com/Vaibhav41-cmd/week6_continuous_integration.git
git status
```

Confirm `.github/workflows/ci.yml` is visible in the status output.
On Windows, hidden folders can be checked with:

```powershell
Get-ChildItem -Force
Test-Path .github\workflows\ci.yml
```

## 4. Make staged, meaningful commits

### Commit 1 — library and tests

```bash
git add financekit tests examples data pyproject.toml LICENSE
git add requirements.txt requirements-ci.txt requirements-dev.txt requirements-evidence.txt
git commit -m "feat: add FinanceKit 1.1.0 and 129-test suite"
```

### Commit 2 — CI workflow and local tooling

```bash
git add .github scripts Makefile .gitignore
git commit -m "ci: add GitHub Actions quality gates and local CI runner"
```

### Commit 3 — documentation and evidence

```bash
git add README.md SUBMISSION_DESCRIPTION.md docs tools results
git commit -m "docs: document CI pipeline evidence and replication"
```

Check history:

```bash
git log --oneline --decorate -5
git status
```

## 5. Push and verify the first hosted run

```bash
git push -u origin main
```

Immediately open:

<https://github.com/Vaibhav41-cmd/week6_continuous_integration/actions>

Expected **CI** run:

| Job | Expected |
|---|---|
| Lint and format (Ruff) | Success |
| Test (ubuntu-latest, Python 3.9) | Success |
| Test (ubuntu-latest, Python 3.10) | Success |
| Test (ubuntu-latest, Python 3.11) | Success |
| Test (ubuntu-latest, Python 3.12) | Success |
| Test (ubuntu-latest, Python 3.13) | Success |
| Test (windows-latest, Python 3.13) | Success |
| Test (macos-latest, Python 3.13) | Success |
| Coverage quality gate | Success, at least 95% |
| Build distributions | Success |
| Publish GitHub Release | Skipped on a branch push |

Open the run and confirm artifacts include:

- `test-results-...` for matrix jobs;
- `coverage-report`;
- `python-distributions`.

Delete the GitHub “no workflow runs” concern only after this page shows a
run. Save a screenshot of the run summary and copy the run URL into the
submission notes. The README badge should change from “no status” to
“passing” after the run completes.

## 6. Configure branch protection

After the first green run, choose **Settings → Branches → Add classic branch
protection rule**:

- Branch name pattern: `main`
- Require a pull request before merging: on
- Require status checks to pass before merging: on
- Require branches to be up to date before merging: on
- Select the lint, all seven test, coverage and build checks
- Block force pushes: on

This converts CI from an informational dashboard into a merge gate.

## 7. Verify the “every commit” trigger with a small change

Make a genuine small improvement, for example add the first hosted run URL to
a local note or correct a documentation detail. A safe documentation-only
change is acceptable because the workflow deliberately has no path filter.

```bash
git checkout -b docs/verify-ci-trigger
# Edit README.md or another documentation file.
git add README.md
git commit -m "docs: verify CI runs on a new commit"
git push -u origin docs/verify-ci-trigger
```

Verify a **new** Actions run appears for the branch-tip SHA. Then open a pull
request into `main`; the same checks should appear at the bottom of the PR.
Merge only when they pass. This verifies both `push` and `pull_request`.

## 8. Optionally verify a red run

Use a throwaway branch, never `main`:

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

Expected: test jobs fail, JUnit artifacts still upload, and coverage/build do
not succeed. Save the red-run URL/screenshot, then remove the branch:

```bash
git checkout main
git branch -D experiment/failing-ci
git push origin --delete experiment/failing-ci
```

The same experiment is already proven locally in
`docs/evidence/negative_ci.txt`, so this hosted step is supporting evidence,
not a requirement for the code to be correct.

## 9. Test a release tag (after the repository is accepted)

Only tag when ready to create a public GitHub Release:

```bash
git checkout main
git pull
git tag -a v1.1.0 -m "FinanceKit 1.1.0: continuous-integration release"
git push origin v1.1.0
```

The release job should run after the build and attach the tested sdist/wheel
to a GitHub Release. Do not reuse or move the tag if the release succeeds.

## 10. Fresh-clone verification

In a different directory:

```bash
git clone https://github.com/Vaibhav41-cmd/week6_continuous_integration.git fresh-week6
cd fresh-week6
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install --editable .
python scripts/run_ci_locally.py
```

Expected: workflow validator, Ruff, byte compilation, 129 tests, 98%+
coverage, distribution build and Twine all pass.

On Windows, replace the virtual-environment activation line with:

```powershell
.venv\Scripts\Activate.ps1
```

## 11. Final repository checklist

- [ ] README renders at the repository root.
- [ ] Figure 1 loads in the README.
- [ ] `.github/workflows/ci.yml` is at the root.
- [ ] First push produced a green Actions run.
- [ ] README badge says passing.
- [ ] Artifacts are visible on the run page.
- [ ] Branch protection requires the CI checks on `main`.
- [ ] A second small commit created a second run.
- [ ] Optional red branch was deleted after the experiment.
- [ ] Fresh clone passes local CI.
- [ ] Submission URL points to the exact repository, not a profile or nested folder.
