#!/usr/bin/env bash
# Run the shared agentic loop (Plan -> Act -> Observe -> Adapt) against one student.
#
# The loop makes live HTTP calls to the target's services, so start the
# application first with ./scripts/run.sh
#
# Usage:
#   ./scripts/agentic-loop.sh student-5
#   ./scripts/agentic-loop.sh            prompts for a target
#
# Press 0 to quit the menu - the log is only written to docs/agentic-logs/
# when you exit with 0.
set -euo pipefail

cd "$(dirname "$0")/.."
# Root directory of the project
ROOT="$(pwd)"

# Prefer an activated virtual environment, then a .venv at the repository root,
# then python3 from PATH.
# On Windows (Git Bash / WSL) a venv puts the interpreter in Scripts/python.exe
# instead of bin/python, so both layouts are checked.
venv_python() {
    if [ -x "$1/bin/python" ]; then
        echo "$1/bin/python"
    elif [ -x "$1/Scripts/python.exe" ]; then
        echo "$1/Scripts/python.exe"
    fi
}

PY=""
[ -n "${VIRTUAL_ENV:-}" ] && PY="$(venv_python "$VIRTUAL_ENV")"
[ -z "$PY" ] && PY="$(venv_python "$ROOT/.venv")"
if [ -z "$PY" ]; then
    if command -v python3 >/dev/null 2>&1; then PY="python3"; else PY="python"; fi
fi

echo "python: $PY"

if ! "$PY" -c "import openai, dotenv, requests" 2>/dev/null; then
    echo "ERROR: the agentic loop's dependencies are missing for this interpreter."
    exit 1
fi

if [ $# -gt 0 ]; then
    export REVIEW_TARGET="$1"
fi

"$PY" agentic_loop.py
