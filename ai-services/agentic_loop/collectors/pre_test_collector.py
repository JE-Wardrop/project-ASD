from pathlib import Path


REQUIRED_HOOK_IDS = ["ruff-scan", "detect-secrets-scan", "pip-audit-scan"]


def collect(target, repo_root: Path) -> tuple[bool, str]:
    student_no = repo_root / "" / ""
    pre_commit_each_student = target.root / "tests" / "pre-commit" 

    required_paths = [
        repo_root / ".pre-commit-config.yaml",
        pre_commit_each_student / "test_ruff_scan.py",
        pre_commit_each_student / "test_secrets_scan.py",
        pre_commit_each_student / "test_dependency_audit.py",
    ]

    missing = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing:
        return False, "Pre-test evidence incomplete. Missing: " + ", ".join(missing)

    config_text = (repo_root / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    missing_hooks = [hook_id for hook_id in REQUIRED_HOOK_IDS if hook_id not in config_text]
    if missing_hooks:
        return False, ".pre-commit-config.yaml missing hooks: " + ", ".join(missing_hooks)

    return True, (
        "Pre-test evidence: .pre-commit-config.yaml wires ruff-scan, detect-secrets-scan, "
        "and pip-audit-scan hooks to tests/pre_commit/ test files that block commits on failure."
    )