from datetime import datetime
from pathlib import Path


def print_prompt_map(mapping: dict[str, str]) -> None:
    print("PROMPT PATH MAP")
    for label, path in mapping.items():
        print(f"- {label}: {path}")


def print_menu(target_label: str) -> None:
    print()
    print("=" * 72)
    print(f"AGENTIC REVIEW MENU   -   target: {target_label}")
    print("1 - Database")
    print("2 - Endpoints")
    print("3 - Architecture")
    print("4 - DevOps")
    print("5 - Run all four")
    print("0 - Exit")
    print("=" * 72)


def print_result(title: str, text: str) -> None:
    print()
    print(f"RESULT: {title}")
    print("-" * 72)
    print(text)
    print("-" * 72)


def save_log(repo_root: Path, target_key: str, entries: list[tuple[str, str]]) -> Path:
    """Write the session transcript for the technical report."""
    log_dir = repo_root / "docs" / "agentic-logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = log_dir / f"loop-{target_key}-{stamp}.md"

    lines = [
        f"# Agentic loop - {target_key}",
        "",
        f"Run at {datetime.now().strftime('%d %B %Y, %H:%M')}",
        "",
        "Workflow: Plan -> Act -> Observe -> Adapt",
        "",
    ]
    for title, text in entries:
        lines += [f"## {title}", "", "```", text, "```", ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path