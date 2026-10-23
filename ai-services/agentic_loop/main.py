"""Entry point for the shared agentic review loop.

Choose whose microservices to review with an environment variable:

    REVIEW_TARGET=student-5 python agentic_loop.py

If it is not set, the loop asks at startup.
"""

from pathlib import Path

from config.review_config import build_mode_config
from config.targets import available_targets, resolve_target
from core.ai_runner import AIRunner
from core.orchestrator import run_mode
from core.prompt_registry import PromptRegistry
from core.reporter import print_menu, print_prompt_map, print_result, save_log
from dotenv import load_dotenv

MENU = {
    "1": "db",
    "2": "endpoints",
    "3": "architecture",
    "4": "devops",
    "5": "mcp",
    "6": "rag",
    "8": "multi_agent",
    "9": "pre_test",
    "10": "deployment",
    "11": "cicd",
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
        "MCP":          str(app_dir / "prompts" / "mcp" / "review" / "tool_review_prompt.txt"),
        "RAG":          str(app_dir / "prompts" / "rag" / "review" / "integration_review_prompt.txt"),
        "Multi-Agent":  str(app_dir / "prompts" / "multi-agent" / "review" / "multi_agent_review_prompt.txt"),
        "Pre-test":     str(app_dir / "prompts" / "pre_test" / "review" / "pre_test_implementation.txt"),
        "Deployment":   str(app_dir / "prompts" / "deployment" / "review" / "deployment_review.txt"),
        "CICD":         str(app_dir / "prompts" / "cicd" / "review" / "cicd_implementation_prompt.txt"),
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

        keys = list(MENU.values()) if choice == "7" else [MENU.get(choice)]
        if keys == [None]:
            print("Invalid choice. Select 0 to 11.")
            continue

        for key in keys:
            print()
            result = run_mode(mode_config[key], target, repo_root, prompts, ai)
            print_result(mode_config[key].label, result)
            transcript.append((mode_config[key].label, result))