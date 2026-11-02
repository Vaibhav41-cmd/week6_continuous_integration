#!/usr/bin/env python3
"""Validate the semantic contract of the GitHub Actions workflow.

PyYAML confirms syntax, while these checks confirm the parts that matter to
this project: push/PR triggers, Ruff, the test matrix, non-fail-fast matrix
behaviour, JUnit artifacts, the 95% coverage gate, distribution build and
tag-only release permissions.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def step_runs(job: dict) -> list[str]:
    return [str(step.get("run", "")) for step in job.get("steps", [])]


def expect(condition: bool, message: str, failures: list[str]) -> None:
    if condition:
        print(f"PASS  {message}")
    else:
        print(f"FAIL  {message}")
        failures.append(message)


def main() -> int:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    failures: list[str] = []

    # YAML 1.1 parsers interpret the unquoted key `on` as boolean True.
    triggers = workflow.get("on", workflow.get(True, {}))
    jobs = workflow.get("jobs", {})

    expect(workflow.get("name") == "CI", "workflow is named CI", failures)
    expect("push" in triggers, "push trigger is enabled", failures)
    expect("pull_request" in triggers, "pull_request trigger is enabled", failures)
    expect("workflow_dispatch" in triggers, "manual trigger is enabled", failures)
    expect("schedule" in triggers, "weekly scheduled trigger is enabled", failures)
    expect(
        workflow.get("permissions", {}).get("contents") == "read",
        "default token permission is read-only",
        failures,
    )

    for job_name in ("lint", "test", "coverage", "build", "release"):
        expect(job_name in jobs, f"job exists: {job_name}", failures)

    lint_runs = "\n".join(step_runs(jobs.get("lint", {})))
    expect("ruff check" in lint_runs, "lint job runs Ruff check", failures)
    expect("ruff format --check" in lint_runs, "lint job checks formatting", failures)
    expect(
        "validate_workflow.py" in lint_runs,
        "lint job validates workflow semantics",
        failures,
    )

    test_job = jobs.get("test", {})
    matrix_include = test_job.get("strategy", {}).get("matrix", {}).get("include", [])
    combinations = {(item.get("os"), str(item.get("python-version"))) for item in matrix_include}
    expect(
        test_job.get("strategy", {}).get("fail-fast") is False,
        "matrix uses fail-fast: false",
        failures,
    )
    expect(len(combinations) == 7, "matrix contains seven combinations", failures)
    expect(
        ("ubuntu-latest", "3.9") in combinations,
        "oldest supported Python is tested on Ubuntu",
        failures,
    )
    expect(
        ("windows-latest", "3.13") in combinations,
        "current Python is tested on Windows",
        failures,
    )
    expect(
        ("macos-latest", "3.13") in combinations,
        "current Python is tested on macOS",
        failures,
    )

    test_runs = "\n".join(step_runs(test_job))
    expect("python -m pytest" in test_runs, "test job runs pytest", failures)
    expect("--junitxml=" in test_runs, "test job creates a JUnit report", failures)
    test_steps = test_job.get("steps", [])
    expect(
        any(step.get("if") == "always()" for step in test_steps),
        "test artifact uploads even when tests fail",
        failures,
    )

    coverage_runs = "\n".join(step_runs(jobs.get("coverage", {})))
    expect(
        "--cov-fail-under=95" in coverage_runs,
        "coverage job enforces the 95% gate",
        failures,
    )
    expect("--cov-branch" in coverage_runs, "coverage uses branch measurement", failures)

    build_job = jobs.get("build", {})
    build_runs = "\n".join(step_runs(build_job))
    expect(
        "coverage" in build_job.get("needs", []),
        "build waits for the coverage gate",
        failures,
    )
    expect("python -m build" in build_runs, "build job builds distributions", failures)
    expect(
        "python -m twine check" in build_runs,
        "build job validates distribution metadata with twine",
        failures,
    )

    release_job = jobs.get("release", {})
    expect(
        "refs/tags/v" in str(release_job.get("if", "")),
        "release job is restricted to version tags",
        failures,
    )
    expect(
        release_job.get("permissions", {}).get("contents") == "write",
        "write permission is scoped to the release job",
        failures,
    )

    if failures:
        print(f"\nWorkflow validation failed with {len(failures)} issue(s).")
        return 1

    print("\nWorkflow validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
