"""Entry point for the shared agentic review loop.

Choose whose microservices to review with an environment variable:

    REVIEW_TARGET=student-5 python agentic_loop.py

If it is not set, the loop asks at startup.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from config.review_config import build_mode_config
from config.targets import available_targets, resolve_target
from core.ai_runner import AIRunner
from core.orchestrator import run_mode
from core.prompt_registry import PromptRegistry
from core.reporter import print_menu, print_prompt_map, print_result, save_log


MENU = {
    "1": "db",
    "2": "endpoints",
    "3": "architecture",
    "4": "devops",
}


def _resolve_roots() -> tuple[Path, Path]:
    module_dir = Path(__file__).resolve().parent    # ai-services/agentic_loop
    app_dir = module_dir.parent                      # ai-services
    repo_root = app_dir.parent                       # repository root
    return app_dir, repo_root


def _ask_for_target(repo_root: Path):
    """REVIEW_TARGET is missing, so ask rather than guessing someone's feature."""
    print("Available review targets: " + ", ".join(available_targets()))
    while True:
        choice = input("Which student's services should be reviewed? ").strip()
        try:
            return resolve_target(repo_root, choice)
        except ValueError as exc:
            print(exc)


def _print_mode_mapping(app_dir: Path) -> None:
    print_prompt_map({
        "Database":     str(app_dir / "prompts" / "service" / "implementation" / "task_prompt.txt"),
        "Endpoints":    str(app_dir / "prompts" / "service" / "implementation" / "task_prompt.txt"),
        "Architecture": str(app_dir / "prompts" / "architecture" / "implementation" / "architecture_task_prompt.txt"),
        "DevOps":       str(app_dir / "prompts" / "devops" / "implementation" / "devops_task_prompt.txt"),
    })


def main() -> None:
    app_dir, repo_root = _resolve_roots()
    load_dotenv(dotenv_path=repo_root / ".env")

    try:
        target = resolve_target(repo_root)
    except ValueError:
        target = _ask_for_target(repo_root)

    if not target.root.is_dir():
        print(f"Target folder not found: {target.root}")
        return

    mode_config = build_mode_config()
    prompts = PromptRegistry(app_dir)
    ai = AIRunner()

    print()
    print(f"AGENTIC LOOP - reviewing {target.key}: {target.label} ({target.owner})")
    _print_mode_mapping(app_dir)

    transcript: list[tuple[str, str]] = []

    while True:
        print_menu(f"{target.key} - {target.label}")
        choice = input("Choose a review target: ").strip()

        if choice == "0":
            if transcript:
                log_path = save_log(repo_root, target.key, transcript)
                print(f"Log written to {log_path.relative_to(repo_root)}")
            print("Loop closed.")
            break

        keys = list(MENU.values()) if choice == "5" else [MENU.get(choice)]
        if keys == [None]:
            print("Invalid choice. Select 0 to 5.")
            continue

        for key in keys:
            print()
            result = run_mode(mode_config[key], target, repo_root, prompts, ai)
            print_result(mode_config[key].label, result)
            transcript.append((mode_config[key].label, result))