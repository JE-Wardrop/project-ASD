import json
import subprocess
import sys
from pathlib import Path

STUDENT_DIR = Path(__file__).resolve().parents[2]  # .../student-2


def test_detect_secrets_scan_passes():
    # Inside a git repo detect-secrets only scans tracked files, so the
    # git-ignored student-2/.env is never read or reported.
    result = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", "--exclude-files", r"\.pytest_cache/.*"],
        capture_output=True,
        text=True,
        check=False,
        cwd=STUDENT_DIR,
    )
    returncode = result.returncode  # avoid pytest reprinting the full CompletedProcess in the assert
    assert returncode == 0, result.stderr
    findings = json.loads(result.stdout)
    assert findings.get("results", {}) == {}, f"Potential secrets detected: {list(findings['results'])}"
