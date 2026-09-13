#!/usr/bin/env bash
# Run the pytest suites for every student that has one.
#
# Usage:
#   ./scripts/test.sh              run every student's tests
#   ./scripts/test.sh student-5    run one student's tests
set -uo pipefail

cd "$(dirname "$0")/.."
# ROOT = the root directory of the project
ROOT="$(pwd)"

# Choose a Python interpreter, in order of preference:
#   1. a virtual environment the user has already activated
#   2. a .venv at the repository root
#   3. a .venv inside the student folder being tested
#   4. whatever python3 is on PATH
# Each student keeps their own .venv, so there is no single shared one to activate.
# On Windows (Git Bash / WSL) a venv puts the interpreter in Scripts/python.exe
# instead of bin/python, so both layouts are checked.
venv_python() {
    if [ -x "$1/bin/python" ]; then
        echo "$1/bin/python"
    elif [ -x "$1/Scripts/python.exe" ]; then
        echo "$1/Scripts/python.exe"
    fi
}

pick_python() {
    local dir="${1:-}" found=""
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        found="$(venv_python "$VIRTUAL_ENV")"
    fi
    [ -z "$found" ] && found="$(venv_python "$ROOT/.venv")"
    [ -n "$dir" ] && [ -z "$found" ] && found="$(venv_python "$ROOT/$dir/.venv")"
    if [ -n "$found" ]; then
        echo "$found"
    elif command -v python3 >/dev/null 2>&1; then
        echo "python3"
    else
        echo "python"
    fi
}

# Students with a pytest suite. Add yours here once you have one.
TARGETS=("student-2" "student-5")

if [ $# -gt 0 ]; then
    TARGETS=("$@")
fi

failed=()

for target in "${TARGETS[@]}"; do
    if [ ! -d "$ROOT/$target/tests" ]; then
        echo "SKIP  $target - no tests/ directory"
        continue
    fi

    PY="$(pick_python "$target")"

    echo
    echo "=============================================="
    echo "  $target"
    echo "  python: $PY"
    echo "=============================================="

    if ! "$PY" -c "import pytest" 2>/dev/null; then
        echo "ERROR: pytest is not installed for this interpreter."
        failed+=("$target")
        continue
    fi

    if ! (cd "$ROOT/$target" && "$PY" -m pytest tests/ -v); then
        failed+=("$target")
    fi
done

echo
if [ ${#failed[@]} -eq 0 ]; then
    echo "All suites passed."
else
    echo "FAILED: ${failed[*]}"
    exit 1
fi
