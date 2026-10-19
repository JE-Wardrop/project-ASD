import subprocess
import sys
from pathlib import Path

import pytest

STUDENT_DIR = Path(__file__).resolve().parents[2]  # .../student-2
# Audits the requirements each student-2 service is built from, not the whole
# local Python environment (which also holds unrelated packages).
REQUIREMENTS_FILES = sorted(
    path for path in STUDENT_DIR.rglob("requirements*.txt") if ".venv" not in path.parts
)


def test_requirements_files_found():
    # parametrize silently skips on an empty list, so this guards against a glob that matches nothing
    assert REQUIREMENTS_FILES, f"No requirements files found under {STUDENT_DIR}"


@pytest.mark.parametrize(
    "req_file",
    REQUIREMENTS_FILES,
    ids=lambda p: str(p.relative_to(STUDENT_DIR)),
)
def test_pip_audit_passes(req_file):
    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "-r", str(req_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    returncode = result.returncode  # avoid pytest reprinting the full CompletedProcess in the assert
    assert returncode == 0, result.stdout + result.stderr
