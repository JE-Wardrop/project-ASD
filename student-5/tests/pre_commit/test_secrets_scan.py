import json
import subprocess
import sys
from pathlib import Path

STUDENT_DIR = Path(__file__).resolve().parents[2]  # .../student-1



def test_detect_secrets_scan_passes():
    result = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", "--exclude-files", "legacy-lab3/.*"],
        capture_output=True,
        text=True,
        check=False,
        cwd=STUDENT_DIR,
    )
    returncode = result.returncode  # avoid pytest reprinting the full CompletedProcess in the assert
    assert returncode == 0, result.stderr
    findings = json.loads(result.stdout)
    assert findings.get("results", {}) == {}, "Potential secrets detected"