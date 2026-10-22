"""Testing Review (post-commit CI/CD): the student's endpoint tests.

Evidence: the tests in <student>/tests/post_commit/, which of them call the
student's backend/API, whether .github/workflows/<student>.yml runs them, and
the latest results in <student>/tests/reports/ (report + audit trail).
"""

import json
import re
from pathlib import Path


def collect(target, repo_root: Path) -> tuple[bool, str]:
    tests_dir = target.root / "tests" / "post_commit"
    reports_dir = target.root / "tests" / "reports"
    report_path = reports_dir / "post-commit-report.md"
    audit_path = reports_dir / "test-audit.jsonl"
    workflow_path = repo_root / target.workflow_file

    test_files = sorted(tests_dir.glob("test_*.py")) if tests_dir.is_dir() else []
    if not test_files:
        return False, f"CI/CD test evidence incomplete. No test_*.py in {tests_dir.relative_to(repo_root)}"

    total_tests = 0
    backend_tests = []
    for path in test_files:
        text = path.read_text(encoding="utf-8")
        names = re.findall(r"^def (test_\w+)", text, re.M)
        total_tests += len(names)
        # A backend/API test targets the student's backend port (820N).
        if str(target.backend_port) in text:
            backend_tests.append(f"{path.name} ({len(names)} tests)")

    lines = [
        f"CI/CD test evidence for {target.key}: {len(test_files)} post-commit test files, "
        f"{total_tests} tests ({', '.join(p.name for p in test_files)}).",
        "Files calling the backend/API on port "
        f"{target.backend_port}: " + (", ".join(backend_tests) if backend_tests else "none") + ".",
    ]

    if workflow_path.exists():
        runs_tests = f"{target.key}/tests/post_commit" in workflow_path.read_text(encoding="utf-8")
        lines.append(
            f"{target.workflow_file} "
            + ("runs tests/post_commit after push." if runs_tests
               else "does NOT run tests/post_commit, so these tests are not executed in CI.")
        )
    else:
        lines.append(f"{target.workflow_file} is missing.")

    if report_path.exists():
        summary = re.findall(r"=+ (.*(?:passed|failed|error).*) =+", report_path.read_text(encoding="utf-8"))
        lines.append(f"Latest report: {summary[-1] if summary else 'no pytest summary line found'}.")
    else:
        lines.append(f"No report at {report_path.relative_to(repo_root)}.")

    if audit_path.exists():
        entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if entries:
            last = entries[-1]
            lines.append(
                f"Audit trail: {len(entries)} runs, latest {last.get('status', '?')} at {last.get('timestamp', '?')}."
            )
        else:
            lines.append("Audit trail is empty.")
    else:
        lines.append("No test-audit.jsonl audit trail.")

    return True, " ".join(lines)
