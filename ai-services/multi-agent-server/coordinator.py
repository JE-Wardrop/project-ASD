import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from agents.feature_sources import resolve_feature
from agents.planner_agent import plan_workflow
from agents.worker_agent import generate_output
from agents.reviewer_agent import review_output


BASE_DIR = Path(__file__).resolve().parent

# Tests point this at a scratch folder so they do not touch the real evidence files.
DATA_DIR = Path(os.getenv("MULTI_AGENT_DATA_DIR", str(BASE_DIR)))
HISTORY_PATH = DATA_DIR / "workflow_history.jsonl"
AUDIT_PATH = DATA_DIR / "coordination_audit.jsonl"

# The reviewer may make two model calls (review model, then fallback model),
# so one step must outlast two model timeouts or the reviewer is always cut off.
OLLAMA_TIMEOUT_SECONDS = float(
    os.getenv("OLLAMA_TIMEOUT_SECONDS", "45")
)
AGENT_STEP_TIMEOUT_SECONDS = float(
    os.getenv("AGENT_STEP_TIMEOUT_SECONDS", str(2 * OLLAMA_TIMEOUT_SECONDS + 10))
)

HUMAN_DECISIONS = (
    "Accept",
    "Partially Accept",
    "Reject"
)

# Flask serves requests on several threads; appends and the
# "already decided?" check must not interleave.
_file_lock = threading.Lock()


class WorkflowNotFound(LookupError):
    pass


class DecisionAlreadyRecorded(Exception):
    pass


def now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def append_jsonl(
    path: Path,
    record: Dict[str, Any]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(
        "a",
        encoding="utf-8"
    ) as file:
        file.write(
            json.dumps(record) + "\n"
        )


def read_jsonl(
    path: Path
) -> list[Dict[str, Any]]:
    if not path.exists():
        return []

    records = []

    with path.open(
        "r",
        encoding="utf-8"
    ) as file:
        for line in file:
            if line.strip():
                records.append(
                    json.loads(line)
                )

    return records


def overall_status(
    planner_result: Dict[str, Any],
    worker_result: Dict[str, Any],
    reviewer_result: Dict[str, Any]
) -> str:
    """completed: every agent ran on its model and the worker had evidence.
    failed: the worker produced nothing usable (no evidence or timed out).
    degraded: anything in between (fallback text, timeout, zero records).
    """
    if worker_result.get("status") not in ("success", "fallback"):
        return "failed"

    if (
        planner_result.get("status") == "success"
        and worker_result.get("status") == "success"
        and reviewer_result.get("status") == "success"
        and worker_result.get("evidence_count", 0) > 0
    ):
        return "completed"

    return "degraded"


def run_workflow(
    user_request: str,
    feature: Optional[str] = None,
    caller: Optional[str] = None
) -> Dict[str, Any]:
    """Planner + Worker (in parallel) -> Reviewer (sees plan and worker output)
    -> pending human decision.

    Raises ValueError if no feature can be resolved for the request.
    """
    feature = resolve_feature(
        feature,
        caller,
        user_request
    )
    caller = (caller or "").strip() or "unknown"

    start_time = time.time()
    workflow_id = str(
        uuid.uuid4()
    )

    # Planner and worker do not depend on each other; run them concurrently.
    executor = ThreadPoolExecutor(max_workers=2)
    planner_future = executor.submit(
        plan_workflow,
        user_request,
        feature
    )
    worker_future = executor.submit(
        generate_output,
        user_request,
        feature
    )

    try:
        try:
            planner_result = planner_future.result(
                timeout=AGENT_STEP_TIMEOUT_SECONDS
            )
        except FutureTimeoutError:
            planner_future.cancel()
            planner_result = {
                "status": "timeout",
                "agent": "planner_agent",
                "plan": "Planner timed out. Continue with worker evidence and human review.",
                "human_approval_required": True
            }

        try:
            worker_result = worker_future.result(
                timeout=AGENT_STEP_TIMEOUT_SECONDS
            )
        except FutureTimeoutError:
            worker_future.cancel()
            worker_result = {
                "status": "timeout",
                "agent": "worker_agent",
                "feature": feature,
                "evidence_count": 0,
                "evidence": [],
                "output": "Worker timed out before generating output.",
                "human_approval_required": True
            }
    finally:
        # Do not wait for straggler model calls after timeout.
        executor.shutdown(wait=False, cancel_futures=True)

    # The reviewer checks the worker's output against the planner's plan.
    reviewer_executor = ThreadPoolExecutor(max_workers=1)
    reviewer_future = reviewer_executor.submit(
        review_output,
        user_request,
        worker_result,
        planner_result.get("plan")
    )

    try:
        try:
            reviewer_result = reviewer_future.result(
                timeout=AGENT_STEP_TIMEOUT_SECONDS
            )
        except FutureTimeoutError:
            reviewer_future.cancel()
            reviewer_result = {
                "status": "timeout",
                "agent": "reviewer_agent",
                "review": "Reviewer timed out. Human must decide based on available evidence.",
                "human_approval_required": True
            }
    finally:
        reviewer_executor.shutdown(wait=False, cancel_futures=True)

    duration_ms = int(
        (time.time() - start_time) * 1000
    )

    status = overall_status(
        planner_result,
        worker_result,
        reviewer_result
    )

    workflow_result = {
        "status": status,
        "workflow_id": workflow_id,
        "timestamp": now_iso(),
        "duration_ms": duration_ms,
        "user_request": user_request,
        "feature": feature,
        "caller": caller,
        "participating_agents": [
            "planner_agent",
            "worker_agent",
            "reviewer_agent"
        ],
        "planner_result": planner_result,
        "worker_result": worker_result,
        "reviewer_result": reviewer_result,
        "human_decision": {
            "required": True,
            "status": "pending",
            "allowed_values": list(HUMAN_DECISIONS),
            "submit_to": f"/workflow/{workflow_id}/decision"
        }
    }

    audit_record = {
        "event": "workflow_run",
        "workflow_id": workflow_id,
        "timestamp": workflow_result["timestamp"],
        "duration_ms": duration_ms,
        "status": status,
        "feature": feature,
        "caller": caller,
        "participating_agents": workflow_result["participating_agents"],
        "human_approval_required": True,
        "planner_status": planner_result.get("status"),
        "worker_status": worker_result.get("status"),
        "reviewer_status": reviewer_result.get("status"),
        "reviewer_model": reviewer_result.get("model"),
        "evidence_count": worker_result.get("evidence_count", 0)
    }

    with _file_lock:
        append_jsonl(
            HISTORY_PATH,
            workflow_result
        )

        append_jsonl(
            AUDIT_PATH,
            audit_record
        )

    return workflow_result


def _decisions_by_workflow(
    audit: list[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    return {
        record["workflow_id"]: record
        for record in audit
        if record.get("event") == "human_decision"
    }


def record_decision(
    workflow_id: str,
    decision: str,
    reason: str,
    correction: str = "",
    reviewer: str = ""
) -> Dict[str, Any]:
    """Record the human's final call on a workflow, once.

    Raises ValueError (bad input), WorkflowNotFound, DecisionAlreadyRecorded.
    """
    matched = [
        value for value in HUMAN_DECISIONS
        if value.lower() == (decision or "").strip().lower()
    ]
    if not matched:
        raise ValueError(
            f"decision must be one of: {', '.join(HUMAN_DECISIONS)}"
        )
    decision = matched[0]

    reason = (reason or "").strip()
    correction = (correction or "").strip()
    if not reason:
        raise ValueError("reason is required")
    if decision == "Partially Accept" and not correction:
        raise ValueError("correction is required for Partially Accept")

    with _file_lock:
        workflow = next(
            (
                record for record in read_jsonl(HISTORY_PATH)
                if record.get("workflow_id") == workflow_id
            ),
            None
        )
        if workflow is None:
            raise WorkflowNotFound(f"Workflow not found: {workflow_id}")

        if workflow_id in _decisions_by_workflow(read_jsonl(AUDIT_PATH)):
            raise DecisionAlreadyRecorded(
                f"A human decision is already recorded for {workflow_id}"
            )

        decision_record = {
            "event": "human_decision",
            "workflow_id": workflow_id,
            "timestamp": now_iso(),
            "feature": workflow.get("feature"),
            "caller": workflow.get("caller"),
            "decision": decision,
            "reason": reason,
            "correction": correction,
            "reviewer": (reviewer or "").strip() or "unknown",
            "workflow_status": workflow.get("status")
        }

        append_jsonl(
            AUDIT_PATH,
            decision_record
        )

    return decision_record


def _summary(
    workflow: Dict[str, Any],
    decision: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    return {
        "workflow_id": workflow.get("workflow_id"),
        "timestamp": workflow.get("timestamp"),
        "feature": workflow.get("feature"),
        "caller": workflow.get("caller"),
        "status": workflow.get("status"),
        "planner_status": workflow.get("planner_result", {}).get("status"),
        "worker_status": workflow.get("worker_result", {}).get("status"),
        "reviewer_status": workflow.get("reviewer_result", {}).get("status"),
        "reviewer_model": workflow.get("reviewer_result", {}).get("model"),
        "evidence_count": workflow.get("worker_result", {}).get("evidence_count", 0),
        "human_decision": decision.get("decision") if decision else "pending"
    }


def workflow_status(
    feature: Optional[str] = None,
    caller: Optional[str] = None,
    recent: int = 5
) -> Dict[str, Any]:
    history = read_jsonl(
        HISTORY_PATH
    )

    audit = read_jsonl(
        AUDIT_PATH
    )

    decisions = _decisions_by_workflow(audit)

    selected = [
        record for record in history
        if (not feature or record.get("feature") == feature)
        and (not caller or record.get("caller") == caller)
    ]
    latest = selected[-1] if selected else None

    status_counts: Dict[str, int] = {}
    for record in selected:
        status_counts[record.get("status")] = status_counts.get(record.get("status"), 0) + 1

    return {
        "status": "success",
        "filter": {
            "feature": feature,
            "caller": caller
        },
        "workflow_history_count": len(history),
        "audit_record_count": len(audit),
        "matching_workflow_count": len(selected),
        "workflow_status_counts": status_counts,
        "human_decision_count": sum(
            1 for record in selected if record.get("workflow_id") in decisions
        ),
        "recent_workflows": [
            _summary(record, decisions.get(record.get("workflow_id")))
            for record in selected[-recent:]
        ],
        "latest_workflow": latest,
        "latest_human_decision": decisions.get(latest.get("workflow_id")) if latest else None
    }


if __name__ == "__main__":
    result = run_workflow(
        "Generate a card status summary for user_id(1).",
        "cards",
        "terminal"
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )
