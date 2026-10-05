from pathlib import Path


REQUIRED_AGENT_FUNCTIONS = {
    "planner_agent.py": "plan_workflow",
    "worker_agent.py": "generate_output",
    "reviewer_agent.py": "review_output",
}


def collect(target, repo_root: Path) -> tuple[bool, str]:
    multi_agent_server_dir = repo_root / "ai-services" / "multi-agent-server"
    multi_agent_agentic_loop = repo_root / "ai-services" / "prompts" / "multi_agent" 
    multi_agent_mode_route = target.root / "backend" / "routes" / "multi_agent_mode.py"

    required_paths = [
        multi_agent_server_dir / "agents" / "planner_agent.py",
        multi_agent_server_dir / "agents" / "worker_agent.py",
        multi_agent_server_dir / "agents" / "reviewer_agent.py",
        multi_agent_server_dir / "coordinator.py",
        multi_agent_server_dir / "app.py",
        multi_agent_server_dir / "requirements.txt",
        multi_agent_mode_route / "backend" / "routes" / "multi_agent_mode.py",
        multi_agent_agentic_loop /"implementation" / "multi_agent_implementation_prompt.txt",
        multi_agent_agentic_loop / "review" / "multi_agent_review_prompt.txt",
    ]

    missing = [str(path.relative_to(multi_agent_server_dir)) for path in required_paths if not path.exists()]
    if missing:
        return False, "Multi-agent evidence incomplete. Missing: " + ", ".join(missing)

    coordinator_text = (multi_agent_server_dir / "coordinator.py").read_text(encoding="utf-8")

    missing_calls = [
        func for func in REQUIRED_AGENT_FUNCTIONS.values() if func not in coordinator_text
    ]
    if missing_calls:
        return False, "coordinator.py missing calls to: " + ", ".join(missing_calls)

    return True, (
        "Multi-agent evidence: multi-agent-server/ contains planner_agent.py, worker_agent.py, "
        "reviewer_agent.py, coordinator.py, and app.py; coordinator wires plan_workflow, "
        "generate_output, and review_output into a single workflow."
    )