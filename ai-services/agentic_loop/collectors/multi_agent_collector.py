# from pathlib import Path

# REQUIRED_AGENT_FUNCTIONS = {
#     "planner_agent.py": "plan_workflow",
#     "worker_agent.py": "generate_output",
#     "reviewer_agent.py": "review_output",
# }


# def collect(target, repo_root: Path) -> tuple[bool, str]:
#     multi_agent_server_dir = repo_root / "ai-services" / "multi-agent-server"
#     multi_agent_agentic_loop = repo_root / "ai-services" / "prompts" / "multi_agent" 
#     multi_agent_mode_route = target.root / "backend" / "routes" / "multi_agent_mode.py"

#     required_paths = [
#         multi_agent_server_dir / "agents" / "planner_agent.py",
#         multi_agent_server_dir / "agents" / "worker_agent.py",
#         multi_agent_server_dir / "agents" / "reviewer_agent.py",
#         multi_agent_server_dir / "coordinator.py",
#         multi_agent_server_dir / "app.py",
#         multi_agent_server_dir / "requirements.txt",
#         multi_agent_mode_route / "backend" / "routes" / "multi_agent_mode.py",
#         multi_agent_agentic_loop /"implementation" / "multi_agent_implementation_prompt.txt",
#         multi_agent_agentic_loop / "review" / "multi_agent_review_prompt.txt",
#     ]

#     missing = [str(path.relative_to(multi_agent_server_dir)) for path in required_paths if not path.exists()]
#     if missing:
#         return False, "Multi-agent evidence incomplete. Missing: " + ", ".join(missing)

#     coordinator_text = (multi_agent_server_dir / "coordinator.py").read_text(encoding="utf-8")

#     missing_calls = [
#         func for func in REQUIRED_AGENT_FUNCTIONS.values() if func not in coordinator_text
#     ]
#     if missing_calls:
#         return False, "coordinator.py missing calls to: " + ", ".join(missing_calls)

#     return True, (
#         "Multi-agent evidence: multi-agent-server/ contains planner_agent.py, worker_agent.py, "
#         "reviewer_agent.py, coordinator.py, and app.py; coordinator wires plan_workflow, "
#         "generate_output, and review_output into a single workflow."
#     )


import json
from collections import Counter
from pathlib import Path

REQUIRED_AGENT_FUNCTIONS = {
    "planner_agent.py": "plan_workflow",
    "worker_agent.py": "generate_output",
    "reviewer_agent.py": "review_output",
}

MULTI_AGENT_SERVICE_URL = os.getenv("MULTI_AGENT_SERVICE_URL", "http://localhost:5004")

def _display(path: Path, root: Path) -> str:
    """Show a path relative to root, or in full if it lives elsewhere."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def collect(target, repo_root: Path) -> tuple[bool, str]:
    multi_agent_server_dir = repo_root / "ai-services" / "multi-agent-server"
    multi_agent_mode_route = target.root / "backend" / "routes" / "multi_agent_mode.py"

    required_paths = [
        multi_agent_server_dir / "agents" / "planner_agent.py",
        multi_agent_server_dir / "agents" / "worker_agent.py",
        multi_agent_server_dir / "agents" / "reviewer_agent.py",
        multi_agent_server_dir / "coordinator.py",
        multi_agent_server_dir / "app.py",
        multi_agent_server_dir / "requirements.txt",
        multi_agent_mode_route,
    ]

    missing = [_display(path, repo_root) for path in required_paths if not path.exists()]
    if missing:
        return False, "Multi-agent evidence incomplete. Missing: " + ", ".join(missing)

    coordinator_text = (server_dir / "coordinator.py").read_text(encoding="utf-8")

    missing_calls = [
        func for func in REQUIRED_AGENT_FUNCTIONS.values() if func not in coordinator_text
    ]
    if missing_calls:
        return False, "coordinator.py missing calls to: " + ", ".join(missing_calls)

    structure = (
        "Multi-agent evidence: multi-agent-server/ contains planner_agent.py, worker_agent.py, "
        "reviewer_agent.py, coordinator.py, and app.py; coordinator wires plan_workflow, "
        "generate_output, and review_output into a single workflow."
    )
    return True, structure + " " + _workflow_evidence(target, multi_agent_server_dir)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            records.append(json.loads(line))
        except ValueError:
            continue  # a half-written line is skipped, not fatal
    return records


def _workflow_evidence(target, server_dir: Path) -> str:
    """This student's runs (workflow_history.jsonl) and human decisions (coordination_audit.jsonl)."""
    runs = [r for r in _read_jsonl(server_dir / "workflow_history.jsonl")
            if r.get("caller") == target.key]
    decisions = [r for r in _read_jsonl(server_dir / "coordination_audit.jsonl")
                 if r.get("event") == "human_decision" and r.get("caller") == target.key]

    if not runs:
        return (f"No workflow runs from {target.key} in workflow_history.jsonl: "
                "the Planner -> Worker -> Reviewer -> Human Review flow has not been exercised from this feature.")

    statuses = Counter(r.get("status", "?") for r in runs)
    with_evidence = sum(1 for r in runs if (r.get("worker_result") or {}).get("evidence_count", 0) > 0)
    latest = runs[-1]
    decided = Counter(d.get("decision", "?") for d in decisions)
    return (
        f"{target.key} workflow history: {len(runs)} runs "
        f"({', '.join(f'{n} {s}' for s, n in statuses.items())}); "
        f"{with_evidence}/{len(runs)} had Worker database evidence. "
        f"Latest run {latest.get('workflow_id', '?')[:8]} for \"{latest.get('user_request', '')}\" "
        f"took {latest.get('duration_ms', '?')} ms. "
        f"Human decisions recorded in coordination_audit.jsonl: {len(decisions)}"
        + (f" ({', '.join(f'{n} {d}' for d, n in decided.items())})" if decisions else "")
        + f"; {max(len(runs) - len(decisions), 0)} runs still awaiting human review."
    )