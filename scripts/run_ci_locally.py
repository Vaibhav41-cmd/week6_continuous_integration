#!/usr/bin/env python3
"""Run the same quality gates locally that GitHub Actions runs in CI.

Examples:
    python scripts/run_ci_locally.py
    python scripts/run_ci_locally.py --install
    python scripts/run_ci_locally.py --skip-build
    python scripts/run_ci_locally.py --keep-going

Every stage is captured in ``local-ci-output/logs``. JUnit, coverage and
distribution artifacts are written beneath ``local-ci-output`` so a local run
does not pollute the repository root. By default the runner stops at the
first failed stage and returns that stage's non-zero exit code, matching the
quality-gate behaviour expected from hosted CI.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Stage:
    def __init__(self, name: str, command: list[str]) -> None:
        self.name = name
        self.command = command


def display_command(command: list[str]) -> str:
    visible = [
        "python" if Path(part).resolve() == Path(sys.executable).resolve() else part
        for part in command
    ]
    return " ".join(visible)


def run_stage(stage: Stage, logs_dir: Path, index: int) -> dict[str, object]:
    print(f"\n[{index}] {stage.name}")
    print("$", display_command(stage.command))
    started = time.perf_counter()
    result = subprocess.run(
        stage.command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    elapsed = time.perf_counter() - started
    print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    status = "passed" if result.returncode == 0 else "failed"
    print(f"-> {status} in {elapsed:.2f}s (exit {result.returncode})")

    safe_name = stage.name.lower().replace(" ", "-").replace("/", "-")
    log_path = logs_dir / f"{index:02d}-{safe_name}.txt"
    log_path.write_text(
        f"$ {display_command(stage.command)}\n{result.stdout}",
        encoding="utf-8",
    )
    try:
        displayed_log = str(log_path.relative_to(ROOT))
    except ValueError:
        displayed_log = str(log_path)

    return {
        "name": stage.name,
        "command": stage.command,
        "return_code": result.returncode,
        "status": status,
        "duration_seconds": round(elapsed, 3),
        "log": displayed_log,
    }


def build_stages(args: argparse.Namespace, output: Path) -> list[Stage]:
    python = sys.executable
    stages: list[Stage] = []

    if args.install:
        stages.extend(
            [
                Stage(
                    "Install development dependencies",
                    [
                        python,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        "requirements-dev.txt",
                    ],
                ),
                Stage(
                    "Install package in editable mode",
                    [python, "-m", "pip", "install", "--editable", "."],
                ),
            ]
        )

    stages.extend(
        [
            Stage("Workflow structure validation", [python, "scripts/validate_workflow.py"]),
            Stage("Ruff lint", [python, "-m", "ruff", "check", "."]),
            Stage("Ruff format check", [python, "-m", "ruff", "format", "--check", "."]),
            Stage(
                "Byte-compile sources",
                [
                    python,
                    "-m",
                    "compileall",
                    "-q",
                    "financekit",
                    "tests",
                    "examples",
                    "scripts",
                    "tools",
                ],
            ),
            Stage(
                "Pytest with JUnit report",
                [
                    python,
                    "-m",
                    "pytest",
                    "-vv",
                    f"--junitxml={output / 'test-results' / 'junit-local.xml'}",
                ],
            ),
            Stage(
                "Coverage quality gate",
                [
                    python,
                    "-m",
                    "pytest",
                    "-vv",
                    "--cov=financekit",
                    "--cov-branch",
                    "--cov-fail-under=95",
                    "--cov-report=term-missing",
                    f"--cov-report=xml:{output / 'coverage.xml'}",
                    f"--cov-report=html:{output / 'htmlcov'}",
                    f"--junitxml={output / 'test-results' / 'junit-coverage.xml'}",
                ],
            ),
        ]
    )

    if not args.skip_build:
        stages.extend(
            [
                Stage(
                    "Build source distribution and wheel",
                    [
                        python,
                        "-m",
                        "build",
                        "--outdir",
                        str(output / "dist"),
                    ],
                ),
                Stage(
                    "Validate distribution metadata",
                    [
                        python,
                        "-m",
                        "twine",
                        "check",
                        *[str(p) for p in sorted((output / "dist").glob("*"))],
                    ]
                    if (output / "dist").exists()
                    else [python, "-m", "twine", "check", str(output / "dist" / "*")],
                ),
            ]
        )

    return stages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "local-ci-output",
        help="Directory for logs and generated reports",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install development dependencies and the package first",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip sdist/wheel build and twine validation",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Run later stages even after a failure (for diagnostics)",
    )
    args = parser.parse_args()

    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    logs_dir = output / "logs"
    (output / "test-results").mkdir(parents=True, exist_ok=True)
    (output / "dist").mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    print("FinanceKit local CI")
    print(f"Python: {platform.python_version()} ({sys.executable})")
    print(f"Platform: {platform.platform()}")
    print(f"Repository: {ROOT}")
    print(f"Output: {output}")

    records: list[dict[str, object]] = []
    first_failure = 0

    # The distribution list for twine is resolved immediately before its stage,
    # after the build stage has populated the output directory.
    stages = build_stages(args, output)
    for index, stage in enumerate(stages, start=1):
        if stage.name == "Validate distribution metadata":
            artifacts = sorted((output / "dist").glob("*"))
            stage.command = [
                sys.executable,
                "-m",
                "twine",
                "check",
                *[str(path) for path in artifacts],
            ]
        record = run_stage(stage, logs_dir, index)
        records.append(record)
        if record["return_code"] != 0:
            first_failure = int(record["return_code"])
            if not args.keep_going:
                break

    summary = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "repository": str(ROOT),
        "output": str(output),
        "status": "passed" if first_failure == 0 else "failed",
        "first_failure_exit_code": first_failure,
        "stages": records,
    }
    (output / "local-ci-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\nLocal CI summary")
    for record in records:
        print(f"- {record['status'].upper():6} {record['name']}")
    print(f"Overall: {summary['status']}")
    return first_failure


if __name__ == "__main__":
    raise SystemExit(main())
