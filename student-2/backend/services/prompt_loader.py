from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR.parent
PROMPT_DIR = APP_DIR / "prompts"
IMPLEMENTATION_PROMPT_DIR = PROMPT_DIR / "service" / "implementation"
REVIEW_PROMPT_DIR = PROMPT_DIR / "service" / "review"


def load_prompt(filename):
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


def load_service_prompt(filename):
    for prompt_dir in (IMPLEMENTATION_PROMPT_DIR, REVIEW_PROMPT_DIR):
        candidate = prompt_dir / filename
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()

    return (IMPLEMENTATION_PROMPT_DIR / filename).read_text(encoding="utf-8").strip()
