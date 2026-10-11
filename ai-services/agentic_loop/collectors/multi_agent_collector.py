import os
from pathlib import Path

import requests


REQUIRED_AGENT_FUNCTIONS = {
    "planner_agent.py": "plan_workflow",
    "worker_agent.py": "generate_output",
    "reviewer_agent.py": "review_output",
}

MULTI_AGENT_SERVICE_URL = os.getenv("MULTI_AGENT_SERVICE_URL", "http://localhost:5004")

# Which Multi-Agent feature (agents/feature_sources.py FEATURES) belongs to
# each review target. Workflows are filtered by feature, so runs from a
# backend that does not send "caller" are still counted.
TARGET_FEATURES = {
    "student-1": "cards",
    "student-2": "accounts",
    "student-4": "users",
    "student-5": "transactions",
}


def _static_check(target, repo_root: Path) -> tuple[bool, str]:
    server_dir = repo_root / "ai-services" / "multi-agent-server"
    prompts_dir = repo_root / "ai-services" / "prompts" / "multi-agent"

    required_paths = [
        server_dir / "agents" / "planner_agent.py",
        server_dir / "agents" / "worker_agent.py",
        server_dir / "agents" / "reviewer_agent.py",
        server_dir / "coordinator.py",
        server_dir / "app.py",
        server_dir / "workflow_runner.py",
        server_dir / "requirements.txt",
        target.root / "backend" / "routes" / "multi_agent_mode.py",
        prompts_dir / "implementation" / "multi_agent_implementation_prompt.txt",
        prompts_dir / "review" / "multi_agent_review_prompt.txt",
    ]

    missing = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing:
        return False, "Multi-agent evidence incomplete. Missing: " + ", ".join(missing)

    coordinator_text = (server_dir / "coordinator.py").read_text(encoding="utf-8")

    missing_calls = [
        func for func in REQUIRED_AGENT_FUNCTIONS.values() if func not in coordinator_text
    ]
    if missing_calls:
        return False, "coordinator.py missing calls to: " + ", ".join(missing_calls)

    return True, ""


def _live_check(target) -> tuple[bool, str]:
    """OBSERVE the workflow evidence the running Multi-Agent Server has recorded."""
    feature = TARGET_FEATURES.get(target.key)
    if feature is None:
        return False, f"no Multi-Agent feature mapped for {target.key}"

    try:
        status = requests.get(
            f"{MULTI_AGENT_SERVICE_URL}/workflow/status",
            params={"feature": feature},
            timeout=10,
        ).json()
    except requests.RequestException as exc:
        return False, f"Multi-Agent Server not reachable at {MULTI_AGENT_SERVICE_URL}: {exc}"
    except ValueError:
        return False, f"Multi-Agent Server at {MULTI_AGENT_SERVICE_URL} returned a non-JSON reply"

    runs = status.get("matching_workflow_count", 0)
    if not runs:
        return False, (
            f"no workflow runs recorded for feature={feature}; run one from the "
            f"{target.key} Multi-Agent tab or multi-agent-server/workflow_runner.py first"
        )

    latest = status["recent_workflows"][-1]
    decision = status.get("latest_human_decision")
    decision_text = (
        f"{decision['decision']} by {decision['reviewer']} (reason: {decision['reason']!r})"
        if decision else "none recorded (pending)"
    )

    return True, (
        f"{runs} workflow run(s) for feature={feature}, statuses {status.get('workflow_status_counts')}, "
        f"{status.get('human_decision_count', 0)} with a human decision. "
        f"Latest {latest['workflow_id']}: overall={latest['status']}, "
        f"planner={latest['planner_status']}, worker={latest['worker_status']} "
        f"(evidence_count={latest['evidence_count']}), "
        f"reviewer={latest['reviewer_status']} ({latest['reviewer_model']}); "
        f"human decision: {decision_text}"
    )


def collect(target, repo_root: Path) -> tuple[bool, str]:
    ok, message = _static_check(target, repo_root)
    if not ok:
        return False, message

    ok, live = _live_check(target)
    if not ok:
        return False, live

    return True, (
        "Multi-agent evidence: multi-agent-server/ contains planner_agent.py, worker_agent.py, "
        "reviewer_agent.py, coordinator.py, app.py and workflow_runner.py; coordinator wires "
        "plan_workflow, generate_output, and review_output into a single workflow; "
        f"{target.key}/backend/routes/multi_agent_mode.py exists. Live: {live}"
    )
