from pathlib import Path

# backend/
BASE_DIR = Path(__file__).resolve().parent.parent

# backend/prompts/
PROMPT_DIR = BASE_DIR /"prompts"

def load_prompt(filename):
    return (PROMPT_DIR / filename).read_text(encoding="utf-8")