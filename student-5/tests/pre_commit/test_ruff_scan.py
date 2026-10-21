import subprocess
import sys
from pathlib import Path

STUDENT_DIR = Path(__file__).resolve().parents[2]  # .../student-1


def test_ruff_scan_passes():
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--output-format=concise", "."],
        capture_output=True,
        text=True,
        check=False,
        cwd=STUDENT_DIR,
    )
    returncode = result.returncode
    assert returncode == 0, result.stdout + result.stderr