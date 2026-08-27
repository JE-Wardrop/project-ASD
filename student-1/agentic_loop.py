from pathlib import Path
import sys
from main import main


ENGINE_DIR = Path(__file__).resolve().parent / "agentic_loop"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))


if __name__ == "__main__":
    main()