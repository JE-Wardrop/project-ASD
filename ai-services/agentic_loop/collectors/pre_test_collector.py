"""Testing Review (pre-commit): the student's local security scans.

Evidence: the three scan tests in <student>/tests/pre_commit/, the student's
hooks in .pre-commit-config.yaml (active, not commented out), and the latest
pre-commit run saved in <student>/tests/reports/pre-commit-report.md.
"""

import re
from pathlib import Path

SCANS = {
    "ruff-scan": "test_ruff_scan.py",
    "detect-secrets-scan": "test_secrets_scan.py",
    "pip-audit-scan": "test_dependency_audit.py",
}


def _active_lines(config_text: str) -> list[str]:
    return [line for line in config_text.splitlines() if not line.lstrip().startswith("#")]


def collect(target, repo_root: Path) -> tuple[bool, str]:
    config_path = repo_root / ".pre-commit-config.yaml"
    tests_dir = target.root / "tests" / "pre_commit"
    reports_dir = target.root / "tests" / "reports"
    # The saved pre-commit output, as .md or .txt (student-5 uses .txt)
    report_path = next(
        (p for p in (reports_dir / "pre-commit-report.md", reports_dir / "pre-commit-report.txt") if p.exists()),
        reports_dir / "pre-commit-report.md",
    )

    required_paths = [config_path] + [tests_dir / name for name in SCANS.values()]
    missing = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing:
        return False, "Pre-test evidence incomplete. Missing: " + ", ".join(missing)

    active = "\n".join(_active_lines(config_path.read_text(encoding="utf-8")))
    hooks = {
        hook: f"id: {target.key}-{hook}" in active
        and f"{target.key}/tests/pre_commit/{test_file}" in active
        for hook, test_file in SCANS.items()
    }
    inactive = [hook for hook, ok in hooks.items() if not ok]
    if inactive:
        return False, (
            f".pre-commit-config.yaml has no active {target.key} hook for: "
            + ", ".join(inactive)
        )

    lines = [
        f"Pre-test evidence for {target.key}: .pre-commit-config.yaml has active hooks "
        f"{', '.join(f'{target.key}-{h}' for h in SCANS)} running "
        f"{target.key}/tests/pre_commit/ (Ruff S security rules, detect-secrets, pip-audit) "
        "at the pre-commit stage; a failing scan blocks the commit."
    ]

    if report_path.exists():
        report = report_path.read_text(encoding="utf-8")
        # pre-commit prints one "<hook name>....Passed|Failed|Skipped" line per hook
        results = re.findall(r"^(.+?)\.{3,}(Passed|Failed|\(no files to check\)Skipped)", report, re.M)
        ran = [f"{name.strip()}: {status.replace('(no files to check)', '')}" for name, status in results
               if target.key in name]
        lines.append(
            f"Latest run ({report_path.relative_to(repo_root)}): "
            + ("; ".join(ran) if ran else "no hook results found in the report")
            + "."
        )
    else:
        lines.append(
            f"No pre-commit run recorded yet ({report_path.relative_to(repo_root)} missing)."
        )

    return True, " ".join(lines)
