from pathlib import Path

# BASE_DIR = Path(__file__).resolve().parent.parent
# APP_DIR = BASE_DIR.parent
# PROMPT_DIR = APP_DIR / "prompts"
# # ARCHITECTURE_IMPLEMENTATION_PROMPT_DIR = PROMPT_DIR / "architecture" / "implementation"
# # ARCHITECTURE_REVIEW_PROMPT_DIR = PROMPT_DIR / "architecture" / "review"


# def load_prompt(filename):
#     return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


# def load_architecture_prompt(filename):
#     prompt_dirs = [ARCHITECTURE_IMPLEMENTATION_PROMPT_DIR, ARCHITECTURE_REVIEW_PROMPT_DIR]

#     for prompt_dir in prompt_dirs:
#         candidate = prompt_dir / filename
#         if candidate.exists():
#             return candidate.read_text(encoding="utf-8").strip()

#     return (ARCHITECTURE_IMPLEMENTATION_PROMPT_DIR / filename).read_text(encoding="utf-8").strip()



# __file__ is /backend/services/prompt_loader.py
# .parent is /backend/services
# .parent.parent is /backend
BASE_DIR = Path(__file__).resolve().parent.parent

# prompts is in backend therefore it is here
PROMPT_DIR = BASE_DIR / "prompts"


def load_prompt(filename):
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()