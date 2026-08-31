from pathlib import Path
import sys

# p = Path.parent() / "agentic_loop" / "main.py"

ENGINE_DIR = Path(__file__).resolve().parent / "agentic_loop"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from main import main #visual error, IDK why it says "main could not be reovled by Pylance"

if __name__ == "__main__":
    main()