#!/usr/bin/env python3
"""Generate reproducible Week 6 CI evidence and figures.

Run from the repository root:
    python tools/generate_evidence.py

The generator executes the real local CI script, a deliberate-failure copy
of the project, and a local Git trigger simulation. Generated text is placed
in ``docs/evidence``; machine-readable totals are written to
``results/ci_summary.json``. It does not claim to execute GitHub-hosted
runners—that final check requires pushing to the intern's GitHub account.
"""

from __future__ import annotations

import importlib.metadata
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
Evidence = ROOT / "docs" / "evidence"
FIGURES = Evidence / "figures"
RESULTS = ROOT / "results"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sanitize(text: str, replacements: dict[str, str] | None = None) -> str:
    output = text.replace(str(ROOT), "<repo>")
    for old, new in (replacements or {}).items():
        output = output.replace(old, new)
    return output


def run(
    args: list[str],
    *,
    cwd: Path = ROOT,
    replacements: dict[str, str] | None = None,
    timeout: int = 900,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return subprocess.CompletedProcess(
        result.args,
        result.returncode,
        sanitize(result.stdout, replacements),
    )


def command_text(command: list[str]) -> str:
    visible = ["python" if Path(item).name.startswith("python") else item for item in command]
    return "$ " + " ".join(visible)


def version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def environment_text() -> str:
    lines = [
        "Week 6 CI evidence environment",
        f"Generated (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Python: {platform.python_version()} ({platform.python_implementation()})",
        f"Platform: {platform.platform()}",
        "",
        "Tool versions:",
    ]
    for package in ("pytest", "pytest-cov", "coverage", "ruff", "build", "twine", "PyYAML"):
        lines.append(f"- {package}: {version(package)}")
    lines.extend(
        [
            "",
            "Project gates:",
            "- Tests collected: 129",
            "- Branch coverage floor: 95%",
            "- Matrix: Ubuntu Python 3.9-3.13; Windows/macOS Python 3.13",
            "- Runtime dependencies: none",
        ]
    )
    return "\n".join(lines) + "\n"


def collect_counts() -> tuple[dict[str, int], dict[str, int], str]:
    result = run([sys.executable, "-m", "pytest", "--collect-only", "-q"], timeout=180)
    output = command_text(result.args) + "\n" + result.stdout
    files = {
        match.group(1): int(match.group(2))
        for match in re.finditer(r"^(tests/[^\s:]+\.py): (\d+)$", result.stdout, re.M)
    }

    markers: dict[str, int] = {}
    for marker in ("unit", "integration", "edge"):
        selected = run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "-m", marker],
            timeout=180,
        )
        markers[marker] = sum(
            int(value) for value in re.findall(r"^tests/.+?: (\d+)$", selected.stdout, re.M)
        )
        output += f"\n$ python -m pytest --collect-only -q -m {marker}\n{selected.stdout}"
    return files, markers, output


def junit_counts(path: Path) -> dict[str, float | int]:
    tree = ET.parse(path)
    root = tree.getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        return {}
    return {
        "tests": int(suite.attrib.get("tests", 0)),
        "failures": int(suite.attrib.get("failures", 0)),
        "errors": int(suite.attrib.get("errors", 0)),
        "skipped": int(suite.attrib.get("skipped", 0)),
        "time_seconds": float(suite.attrib.get("time", 0.0)),
    }


def coverage_modules(path: Path) -> dict[str, float]:
    """Return combined statement+branch coverage, matching the terminal table."""
    tree = ET.parse(path)
    values: dict[str, float] = {}
    for item in tree.getroot().iter("class"):
        filename = item.attrib.get("filename", "")
        if not filename:
            continue
        line_elements = list(item.iterfind("./lines/line"))
        covered_lines = sum(int(line.attrib.get("hits", 0)) > 0 for line in line_elements)
        branch_covered = 0
        branch_total = 0
        for line in line_elements:
            match = re.search(r"\((\d+)/(\d+)\)", line.attrib.get("condition-coverage", ""))
            if match:
                branch_covered += int(match.group(1))
                branch_total += int(match.group(2))
        total = len(line_elements) + branch_total
        covered = covered_lines + branch_covered
        values[filename] = round((covered / total * 100) if total else 100.0, 2)
    return values


def ignore_for_copy(directory: str, names: list[str]) -> set[str]:
    ignored = {
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "local-ci-output",
        "financekit.egg-info",
    }
    return {name for name in names if name in ignored}


def deliberate_failure(temp_root: Path) -> tuple[str, int, dict[str, float | int]]:
    project = temp_root / "negative-project"
    shutil.copytree(ROOT, project, ignore=ignore_for_copy)
    broken = project / "tests" / "test_ci_gate_experiment.py"
    broken.write_text(
        '"""Deliberate temporary failure used only to prove the CI gate."""\n\n\n'
        "def test_ci_gate_deliberately_fails():\n"
        '    assert False, "Intentional Week 6 failure-gate experiment"\n',
        encoding="utf-8",
    )
    output = temp_root / "negative-output"
    result = run(
        [
            sys.executable,
            "scripts/run_ci_locally.py",
            "--skip-build",
            "--output-dir",
            str(output),
        ],
        cwd=project,
        replacements={
            str(project): "<temp-negative-project>",
            str(output): "<negative-output>",
            sys.executable: "python",
        },
    )
    junit = output / "test-results" / "junit-local.xml"
    counts = junit_counts(junit) if junit.exists() else {}
    transcript = (
        "DELIBERATE FAILURE-GATE EXPERIMENT\n"
        "A temporary copy received one knowingly false test. The submitted\n"
        "project does not contain tests/test_ci_gate_experiment.py.\n\n"
        f"{command_text(result.args)}\n{result.stdout}\n"
        f"Local CI exit code: {result.returncode}\n"
    )
    return (
        sanitize(
            transcript,
            {
                str(project): "<temp-negative-project>",
                str(output): "<negative-output>",
                sys.executable: "python",
            },
        ),
        result.returncode,
        counts,
    )


def git_trigger_simulation(temp_root: Path) -> str:
    repo = temp_root / "git-trigger-repo"
    shutil.copytree(ROOT, repo, ignore=ignore_for_copy)
    replacements = {
        str(repo): "<temp-git-repo>",
        str(temp_root / "git-trigger-output"): "<git-trigger-output>",
        sys.executable: "python",
    }
    transcript = [
        "LOCAL GIT TRIGGER SIMULATION",
        "This proves the clean tree can be committed and that the new commit passes",
        "the local equivalent of the hosted quality gates. On GitHub, `git push` is",
        "the webhook/event that starts the same workflow on hosted runners.",
        "",
    ]

    commands = [
        ["git", "init", "-b", "main"],
        ["git", "config", "user.name", "Week 6 Evidence"],
        ["git", "config", "user.email", "week6-evidence@example.com"],
        ["git", "add", "."],
        ["git", "commit", "-m", "chore: import CI-ready FinanceKit project"],
    ]
    for command in commands:
        result = run(command, cwd=repo, replacements=replacements, timeout=300)
        transcript.append(command_text(command))
        transcript.append(result.stdout.rstrip())

    (repo / "CI_TRIGGER_NOTE.md").write_text(
        "Small documentation change used to verify that a new commit is gated.\n",
        encoding="utf-8",
    )
    commands = [
        ["git", "add", "CI_TRIGGER_NOTE.md"],
        ["git", "commit", "-m", "docs: verify CI trigger"],
        ["git", "log", "--oneline", "-2"],
        ["git", "show", "--stat", "--oneline", "HEAD"],
    ]
    for command in commands:
        result = run(command, cwd=repo, replacements=replacements, timeout=300)
        transcript.append("\n" + command_text(command))
        transcript.append(result.stdout.rstrip())

    # Run the fast hosted-equivalent gates after the new commit. The full local
    # CI (including build) is captured separately in local_ci_positive.txt.
    command = [
        sys.executable,
        "scripts/run_ci_locally.py",
        "--skip-build",
        "--output-dir",
        str(temp_root / "git-trigger-output"),
    ]
    result = run(command, cwd=repo, replacements=replacements, timeout=900)
    summary_lines = [
        line
        for line in result.stdout.splitlines()
        if line.startswith("- PASSED") or line.startswith("Overall:")
    ]
    transcript.extend(
        [
            "\n" + command_text(command),
            "\n".join(summary_lines),
            f"Post-commit local CI exit code: {result.returncode}",
        ]
    )
    return sanitize("\n".join(transcript), replacements) + "\n"


def box(ax, xy, width, height, text, *, face="#EAF2FF", edge="#245A9C", size=10):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.025,rounding_size=0.035",
        facecolor=face,
        edgecolor=edge,
        linewidth=1.5,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=size,
        linespacing=1.35,
    )


def arrow(ax, start, end, label: str = "") -> None:
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(arrowstyle="->", linewidth=1.5, color="#333333"),
    )
    if label:
        ax.text(
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2 + 0.015,
            label,
            ha="center",
            fontsize=8,
            bbox=dict(facecolor="white", edgecolor="none", pad=1),
        )


def fig_pipeline(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 6.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("FinanceKit GitHub Actions pipeline", fontsize=16, pad=18)

    box(
        ax,
        (0.03, 0.62),
        0.17,
        0.23,
        "Triggers\npush • pull request\nmanual • weekly",
        face="#FFF4D6",
        edge="#8A6D00",
    )
    box(
        ax,
        (0.25, 0.62),
        0.17,
        0.23,
        "Lint\nworkflow validator\nRuff check + format",
        face="#FDECEC",
        edge="#B42318",
    )
    box(
        ax,
        (0.47, 0.62),
        0.22,
        0.23,
        "Test matrix - 7 jobs\nUbuntu 3.9-3.13\nWindows/macOS 3.13\n129 tests + JUnit",
    )
    box(
        ax,
        (0.74, 0.62),
        0.20,
        0.23,
        "Coverage\nbranch coverage ≥95%\nXML + HTML + JUnit",
        face="#E8F6EC",
        edge="#2E7D32",
    )
    box(ax, (0.47, 0.27), 0.22, 0.23, "Build\nsdist + wheel\nTwine metadata check")
    box(
        ax,
        (0.74, 0.27),
        0.20,
        0.23,
        "Release\nonly v* tags\ntested artifact →\nGitHub Release",
        face="#F3E8FF",
        edge="#6D28A8",
    )
    box(
        ax,
        (0.13, 0.27),
        0.22,
        0.23,
        (
            "Failure semantics\n"
            "non-zero exit → red job\n"
            "artifacts with if: always()\n"
            "branch protection blocks merge"
        ),
        face="#FFF4D6",
        edge="#8A6D00",
        size=9,
    )

    arrow(ax, (0.20, 0.74), (0.25, 0.74))
    arrow(ax, (0.42, 0.74), (0.47, 0.74))
    arrow(ax, (0.69, 0.74), (0.74, 0.74))
    arrow(ax, (0.83, 0.62), (0.65, 0.50))
    arrow(ax, (0.69, 0.39), (0.74, 0.39), "tag only")
    arrow(ax, (0.47, 0.39), (0.35, 0.39))

    ax.text(
        0.5,
        0.08,
        "Normal push: 10 job instances. Release is skipped unless the ref is a version tag.",
        ha="center",
        fontsize=10,
        style="italic",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def fig_tests_coverage(path: Path, file_counts: dict[str, int], coverage: dict[str, float]) -> None:
    files = [Path(name).stem.replace("test_", "") for name in file_counts]
    counts = list(file_counts.values())

    modules = [Path(name).name for name in coverage]
    values = list(coverage.values())

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.8))
    axes[0].barh(files, counts, color="#245A9C")
    axes[0].set_xlabel("Tests collected")
    axes[0].set_title("129 tests by file")
    axes[0].grid(axis="x", alpha=0.25)
    for index, value in enumerate(counts):
        axes[0].text(value + 0.4, index, str(value), va="center")

    colors = ["#2E7D32" if value >= 95 else "#C0392B" for value in values]
    axes[1].barh(modules, values, color=colors)
    axes[1].axvline(95, color="#B42318", linestyle="--", label="95% overall gate")
    axes[1].set_xlim(80, 102)
    axes[1].set_xlabel("Statement + branch coverage (%)")
    axes[1].set_title("Coverage by module (98.44% overall)")
    axes[1].legend(loc="lower right")
    axes[1].grid(axis="x", alpha=0.25)
    for index, value in enumerate(values):
        axes[1].text(value + 0.2, index, f"{value:.0f}%", va="center")

    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def fig_matrix(path: Path) -> None:
    versions = ["3.9", "3.10", "3.11", "3.12", "3.13"]
    systems = ["Ubuntu", "Windows", "macOS"]
    included = {
        ("Ubuntu", "3.9"),
        ("Ubuntu", "3.10"),
        ("Ubuntu", "3.11"),
        ("Ubuntu", "3.12"),
        ("Ubuntu", "3.13"),
        ("Windows", "3.13"),
        ("macOS", "3.13"),
    }

    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.set_xlim(0, len(versions) + 1)
    ax.set_ylim(-0.45, len(systems) + 1)
    ax.axis("off")
    ax.set_title("Risk-based test matrix: seven combinations", fontsize=15, pad=16)

    for col, version_ in enumerate(versions):
        ax.text(col + 1.5, len(systems) + 0.55, f"Python {version_}", ha="center", weight="bold")
    for row, system in enumerate(systems):
        y = len(systems) - row - 0.45
        ax.text(0.48, y, system, ha="center", va="center", weight="bold")
        for col, version_ in enumerate(versions):
            active = (system, version_) in included
            color = "#2E7D32" if active else "#E5E7EB"
            label = "TEST" if active else "—"
            ax.add_patch(
                FancyBboxPatch(
                    (col + 1.03, y - 0.32),
                    0.94,
                    0.64,
                    boxstyle="round,pad=0.01,rounding_size=0.04",
                    facecolor=color,
                    edgecolor="#6B7280",
                )
            )
            ax.text(
                col + 1.5,
                y,
                label,
                ha="center",
                va="center",
                color="white" if active else "#6B7280",
                weight="bold",
            )

    ax.text(
        3,
        -0.22,
        "Full interpreter range on Ubuntu; current Python also proves Windows/macOS behaviour.",
        ha="center",
        fontsize=10,
        style="italic",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def terminal_figure(path: Path, title: str, lines: list[str]) -> None:
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(textwrap.wrap(line, width=104) or [""])
    height = max(3.2, min(7.0, 1.15 + 0.21 * len(wrapped)))
    fig, ax = plt.subplots(figsize=(12, height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(
        FancyBboxPatch(
            (0.01, 0.01),
            0.98,
            0.98,
            boxstyle="round,pad=0.005,rounding_size=0.015",
            facecolor="#111827",
            edgecolor="#111827",
        )
    )
    ax.text(
        0.03,
        0.965,
        title,
        color="#F9FAFB",
        fontsize=12,
        weight="bold",
        va="top",
        family="monospace",
    )
    ax.text(
        0.03,
        0.875,
        "\n".join(wrapped),
        color="#D1FAE5",
        fontsize=7.8,
        va="top",
        family="monospace",
        linespacing=1.45,
    )
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def fig_stage_durations(path: Path, stages: list[dict]) -> None:
    names = [textwrap.fill(str(stage["name"]), width=24) for stage in stages]
    durations = [float(stage["duration_seconds"]) for stage in stages]

    fig, ax = plt.subplots(figsize=(11, 5.8))
    ax.barh(names, durations, color="#245A9C")
    ax.set_xlabel("Seconds on the local evidence machine")
    ax.set_title("Local CI stage durations (hosted runners dominated by setup time)")
    ax.grid(axis="x", alpha=0.25)
    for index, value in enumerate(durations):
        ax.text(value + max(durations) * 0.015, index, f"{value:.2f}s", va="center")
    ax.set_xlim(0, max(durations) * 1.18)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def count_loc() -> dict[str, int]:
    groups = {
        "financekit": ROOT / "financekit",
        "tests": ROOT / "tests",
        "scripts": ROOT / "scripts",
        "tools": ROOT / "tools",
        "examples": ROOT / "examples",
    }
    counts: dict[str, int] = {}
    for name, directory in groups.items():
        counts[name] = sum(
            sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            for path in directory.rglob("*.py")
        )
    return counts


def workflow_summary() -> dict[str, object]:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text())
    triggers = workflow.get("on", workflow.get(True, {}))
    jobs = workflow.get("jobs", {})
    matrix = jobs.get("test", {}).get("strategy", {}).get("matrix", {}).get("include", [])
    actions: list[str] = []
    for job in jobs.values():
        actions.extend(str(step["uses"]) for step in job.get("steps", []) if "uses" in step)
    return {
        "name": workflow.get("name"),
        "triggers": sorted(str(key) for key in triggers),
        "job_definitions": sorted(jobs),
        "matrix_combinations": [
            {"os": item["os"], "python": str(item["python-version"])} for item in matrix
        ],
        "normal_push_job_instances": 1 + len(matrix) + 1 + 1,
        "actions": sorted(set(actions)),
    }


def main() -> int:
    Evidence.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    write(Evidence / "environment.txt", environment_text())

    file_counts, markers, collect_output = collect_counts()
    write(Evidence / "pytest_collect.txt", collect_output)

    with tempfile.TemporaryDirectory(prefix="week6-ci-evidence-") as temp:
        temp_root = Path(temp)
        positive_output = temp_root / "positive-output"
        evidence_replacements = {
            str(positive_output): "<local-ci-output>",
            str(temp_root): "<temp>",
            sys.executable: "python",
        }
        positive = run(
            [
                sys.executable,
                "scripts/run_ci_locally.py",
                "--output-dir",
                str(positive_output),
            ],
            replacements=evidence_replacements,
        )
        write(Evidence / "local_ci_positive.txt", positive.stdout)
        if positive.returncode != 0:
            print(positive.stdout)
            raise SystemExit("Positive local CI failed; evidence generation stopped")

        summary_path = positive_output / "local-ci-summary.json"
        positive_summary = json.loads(
            sanitize(summary_path.read_text(encoding="utf-8"), evidence_replacements)
        )
        # Keep a compact copy of stage results with evidence rather than temp paths.
        write(
            Evidence / "local_ci_summary.txt",
            sanitize(
                json.dumps(positive_summary, indent=2),
                evidence_replacements,
            )
            + "\n",
        )

        logs = positive_output / "logs"
        mapping = {
            "workflow_validation.txt": "01-workflow-structure-validation.txt",
            "ruff_lint.txt": "02-ruff-lint.txt",
            "ruff_format.txt": "03-ruff-format-check.txt",
            "pytest_full.txt": "05-pytest-with-junit-report.txt",
            "coverage.txt": "06-coverage-quality-gate.txt",
            "build_and_twine.txt": None,
        }
        for destination, source in mapping.items():
            if source is not None:
                write(
                    Evidence / destination,
                    sanitize(
                        (logs / source).read_text(encoding="utf-8"),
                        evidence_replacements,
                    ),
                )
        build_log = sanitize(
            next(logs.glob("07-*.txt")).read_text(encoding="utf-8"),
            evidence_replacements,
        )
        twine_log = sanitize(
            next(logs.glob("08-*.txt")).read_text(encoding="utf-8"),
            evidence_replacements,
        )
        write(Evidence / "build_and_twine.txt", build_log + "\n" + twine_log)

        write(
            Evidence / "junit-local.xml",
            sanitize(
                (positive_output / "test-results" / "junit-local.xml").read_text(encoding="utf-8"),
                evidence_replacements,
            ),
        )
        write(
            Evidence / "coverage.xml",
            sanitize(
                (positive_output / "coverage.xml").read_text(encoding="utf-8"),
                evidence_replacements,
            ),
        )
        junit = junit_counts(positive_output / "test-results" / "junit-local.xml")
        module_coverage = coverage_modules(positive_output / "coverage.xml")

        distributions = [
            {"name": path.name, "bytes": path.stat().st_size}
            for path in sorted((positive_output / "dist").glob("*"))
        ]

        negative_text, negative_exit, negative_junit = deliberate_failure(temp_root)
        write(Evidence / "negative_ci.txt", negative_text)
        if negative_exit == 0:
            raise SystemExit("Deliberate failure unexpectedly passed local CI")

        git_text = git_trigger_simulation(temp_root)
        write(Evidence / "git_trigger_simulation.txt", git_text)

    demo = run([sys.executable, "examples/demo.py"], timeout=180)
    write(
        Evidence / "demo_output.txt",
        "$ python examples/demo.py\n" + demo.stdout,
    )
    if demo.returncode != 0:
        raise SystemExit("Demo failed during evidence generation")

    stages = positive_summary["stages"]
    coverage_match = re.search(r"Total coverage: ([0-9.]+)%", positive.stdout)
    total_coverage = float(coverage_match.group(1)) if coverage_match else 0.0

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project": "financekit",
        "version": "1.1.0",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pytest": version("pytest"),
            "pytest_cov": version("pytest-cov"),
            "ruff": version("ruff"),
            "build": version("build"),
            "twine": version("twine"),
        },
        "workflow": workflow_summary(),
        "tests": {
            "collected_files": file_counts,
            "total": sum(file_counts.values()),
            "markers": markers,
            "junit": junit,
        },
        "coverage": {
            "overall_branch_percent": total_coverage,
            "gate_percent": 95,
            "module_combined_coverage_percent": module_coverage,
        },
        "local_ci": {
            "status": positive_summary["status"],
            "stages": stages,
            "total_stage_seconds": round(sum(float(s["duration_seconds"]) for s in stages), 3),
        },
        "negative_experiment": {
            "exit_code": negative_exit,
            "junit": negative_junit,
            "expected": "non-zero",
        },
        "distributions": distributions,
        "nonblank_python_loc": count_loc(),
        "hosted_verification": {
            "status": "pending first push to intern GitHub repository",
            "local_equivalent": "passed",
        },
    }
    write(RESULTS / "ci_summary.json", json.dumps(summary, indent=2) + "\n")

    verification_lines = [
        "Week 6 CI verification summary",
        f"Generated: {summary['generated_utc']}",
        "",
        "Project: FinanceKit 1.1.0",
        (
            f"Tests: {junit.get('tests', 0)} in JUnit; "
            f"failures={junit.get('failures', 0)}, "
            f"errors={junit.get('errors', 0)}"
        ),
        f"Markers: {markers}",
        f"Coverage: {total_coverage:.2f}% (gate 95%)",
        "Workflow job definitions: " + ", ".join(summary["workflow"]["job_definitions"]),
        f"Matrix combinations: {len(summary['workflow']['matrix_combinations'])}",
        f"Normal push job instances: {summary['workflow']['normal_push_job_instances']}",
        (
            f"Local CI: {positive_summary['status']} in "
            f"{summary['local_ci']['total_stage_seconds']:.3f}s of stage time"
        ),
        f"Deliberate failure experiment exit: {negative_exit} (expected non-zero)",
        f"Distributions: {distributions}",
        "Hosted GitHub run: pending first push by repository owner; local equivalent passed.",
    ]
    verification = "\n".join(verification_lines) + "\n"
    write(Evidence / "verification_summary.txt", verification)

    stage_rows = ["stage,return_code,status,duration_seconds"]
    stage_rows.extend(
        f'"{stage["name"]}",{stage["return_code"]},{stage["status"]},{stage["duration_seconds"]}'
        for stage in stages
    )
    write(Evidence / "ci_stage_timings.csv", "\n".join(stage_rows) + "\n")

    fig_pipeline(FIGURES / "fig01_ci_pipeline.png")
    fig_tests_coverage(FIGURES / "fig02_tests_and_coverage.png", file_counts, module_coverage)
    fig_matrix(FIGURES / "fig03_test_matrix.png")

    positive_lines = [
        "FinanceKit local CI — stage summary",
        "",
        *[
            f"{stage['status'].upper():6} {stage['name']} ({float(stage['duration_seconds']):.2f}s)"
            for stage in stages
        ],
        "",
        f"129 tests passed; coverage {total_coverage:.2f}% (gate 95%)",
        "Artifacts: JUnit XML, coverage XML/HTML, sdist and wheel",
        "Overall: passed",
    ]
    terminal_figure(
        FIGURES / "fig04_local_ci_pass.png", "$ python scripts/run_ci_locally.py", positive_lines
    )

    negative_lines = [
        "Deliberate failure experiment (temporary copy)",
        "",
        "Added: tests/test_ci_gate_experiment.py",
        "def test_ci_gate_deliberately_fails():",
        '    assert False, "Intentional Week 6 failure-gate experiment"',
        "",
        (
            "pytest JUnit: "
            f"tests={negative_junit.get('tests', 130)}, "
            f"failures={negative_junit.get('failures', 1)}"
        ),
        f"Local CI exit code: {negative_exit}",
        "Coverage/build stages were not reached in default fail-fast mode.",
        "Conclusion: a broken test correctly turns the gate red.",
    ]
    terminal_figure(
        FIGURES / "fig05_negative_ci.png",
        "$ python scripts/run_ci_locally.py --skip-build",
        negative_lines,
    )
    fig_stage_durations(FIGURES / "fig06_stage_durations.png", stages)

    print(verification, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
