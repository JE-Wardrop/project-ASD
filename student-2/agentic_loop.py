"""Entry point for reviewing the Bank Account Management microservice
(student-2) through the shared agentic review engine.

This is a thin wrapper, same pattern as the repo root's agentic_loop.py:
all PLAN/ACT/OBSERVE/ADAPT logic lives in ai-services/agentic_loop, shared
by every student. Running this file just presets which target it reviews.

    python agentic_loop.py                            # reviews student-2
    REVIEW_TARGET=student-4 python agentic_loop.py     # reviews someone else
"""

import os
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent / "ai-services" / "agentic_loop"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

os.environ.setdefault("REVIEW_TARGET", "student-2")

from main import main

if __name__ == "__main__":
    main()
