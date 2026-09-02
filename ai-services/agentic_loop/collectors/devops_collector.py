"""OBSERVE: check the target's DevOps pipeline artefacts.

The specification requires one workflow file per student, one Dockerfile per
microservice, and the services declared in the shared compose file.
"""

import re
from pathlib import Path


def collect(target, repo_root: Path) -> tuple[bool, str]:
    findings: list[str] = []

    # --- CI workflow ------------------------------------------------------
    workflow_path = repo_root / target.workflow_file
    if not workflow_path.exists():
        findings.append(f"{target.workflow_file} MISSING")
    else:
        content = workflow_path.read_text(encoding="utf-8")
        if not content.strip():
            findings.append(f"{target.workflow_file} exists but is EMPTY")
        else:
            steps = len(re.findall(r"^\s*-\s+(name|uses):", content, re.MULTILINE))
            runs_tests = "pytest" in content
            builds_images = "docker build" in content
            findings.append(
                f"{target.workflow_file}: {steps} step(s), "
                f"pytest {'yes' if runs_tests else 'NO'}, "
                f"docker build {'yes' if builds_images else 'NO'}"
            )

    # --- Dockerfiles ------------------------------------------------------
    present = [
        tier for tier in ("frontend", "backend", "database")
        if (target.root / tier / "Dockerfile").exists()
    ]
    findings.append(f"Dockerfiles present: {len(present)}/3 ({', '.join(present) or 'none'})")

    # --- tests ------------------------------------------------------------
    tests_dir = target.root / "tests"
    if not tests_dir.is_dir():
        findings.append("tests/ directory MISSING")
    else:
        test_count = 0
        for test_file in tests_dir.rglob("test_*.py"):
            test_count += len(re.findall(r"^def test_", test_file.read_text(encoding="utf-8"), re.MULTILINE))
        findings.append(f"{test_count} test function(s) found in tests/")

    # --- .gitignore hygiene ----------------------------------------------
    gitignore_path = repo_root / ".gitignore"
    if gitignore_path.exists():
        ignored = gitignore_path.read_text(encoding="utf-8")
        wanted = ["*.db", "__pycache__", ".env", ".venv"]
        absent = [rule for rule in wanted if rule not in ignored]
        findings.append(
            "gitignore covers generated files" if not absent
            else f"gitignore missing rules: {', '.join(absent)}"
        )

    return True, f"DevOps evidence for {target.key} ({target.label}): " + "; ".join(findings) + "."