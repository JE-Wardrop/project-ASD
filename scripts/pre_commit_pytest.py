"""Pre-commit hook launcher: cd into the repository root, then run pytest.

Same idea as Lab 11's scripts/lab11/pre_commit_pytest.py. A hook cannot run a
test file directly with `python test_x.py` (that defines test functions but
never calls them), so every hook runs pytest through this launcher instead.
It works the same on macOS, Linux and Windows.
"""
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    os.chdir(REPO_ROOT)
    return subprocess.call([sys.executable, "-m", "pytest", *sys.argv[1:]])  # noqa: S603 - fixed pytest call


if __name__ == "__main__":
    sys.exit(main())