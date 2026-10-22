from pathlib import Path


def collect(target, app_dir: Path, repo_root: Path) -> tuple[bool, str]:

    student_dir_post_commit = target.root / "tests" / "post_commit"
    student_dir_pre_commit = target.root / "tests" / "pre_commit"
    reports_dir = target.root / "tests" / "reports"

    required_paths = [
        student_dir_post_commit / "test_api_students.py",
        student_dir_post_commit / "test_token_auth.py",
        reports_dir / "post-commit-report.md",
        reports_dir / "test-audit.jsonl",
    ]

    missing = [str(path.relative_to(app_dir)) for path in required_paths if not path.exists()]
    if missing:
        return False, "CI/CD test evidence incomplete. Missing: " + ", ".join(missing)

    audit_lines = (reports_dir / "test-audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    if not audit_lines:
        return False, "reports/lab11/test-audit.jsonl is empty. Run the post-commit tests first."

    last_status = "PASS" in audit_lines[-1]

    return True, (
        "CI/CD test evidence: tests/post_commit/ contains API and token-auth tests; "
        f"reports/test-results.md and test-audit.jsonl exist "
        f"(latest audit entry status: {'PASS' if last_status else 'FAIL'})."
    )