import subprocess
import sys
from pathlib import Path

STUDENT_DIR = Path(__file__).resolve().parents[2]  # .../student-2


def test_ruff_scan_passes():
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--output-format=concise", "."],
        capture_output=True,
        text=True,
        check=False,
        cwd=STUDENT_DIR,  # picks up student-2/pyproject.toml (security "S" rules only)
    )
    returncode = result.returncode  # avoid pytest reprinting the full CompletedProcess in the assert
    assert returncode == 0, result.stdout + result.stderr
