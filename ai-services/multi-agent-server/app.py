import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from agents.feature_sources import supported_features
from coordinator import (
    DecisionAlreadyRecorded,
    WorkflowNotFound,
    record_decision,
    run_workflow,
    workflow_status,
)


app = Flask(__name__)
CORS(app)


@app.get("/")
def health():
    return jsonify(
        {
            "service": "multi-agent-server",
            "status": "running",
            "features": supported_features()
        }
    )


# Body: {"user_request": "...", "feature": "accounts", "caller": "student-2"}
# feature is optional when it can be inferred from caller or the request text.
@app.post("/workflow")
def workflow():
    data = request.get_json(
        silent=True
    ) or {}

    user_request = str(data.get(
        "user_request",
        ""
    )).strip()

    if not user_request:
        return jsonify(
            {
                "status": "error",
                "error": "user_request is required"
            }
        ), 400

    try:
        result = run_workflow(
            user_request,
            data.get("feature"),
            data.get("caller")
        )
    except ValueError as exc:
        return jsonify(
            {
                "status": "error",
                "error": str(exc),
                "features": supported_features()
            }
        ), 400

    return jsonify(
        result
    ), 200


# Body: {"decision": "Accept|Partially Accept|Reject", "reason": "...",
#        "correction": "...", "reviewer": "..."}
@app.post("/workflow/<workflow_id>/decision")
def decision(workflow_id):
    data = request.get_json(
        silent=True
    ) or {}

    try:
        record = record_decision(
            workflow_id,
            str(data.get("decision", "")),
            str(data.get("reason", "")),
            str(data.get("correction", "")),
            str(data.get("reviewer", ""))
        )
    except ValueError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400
    except WorkflowNotFound as exc:
        return jsonify({"status": "error", "error": str(exc)}), 404
    except DecisionAlreadyRecorded as exc:
        return jsonify({"status": "error", "error": str(exc)}), 409

    return jsonify(
        {
            "status": "success",
            "human_decision": record
        }
    ), 200


# Optional filters: ?feature=accounts&caller=student-2
@app.get("/workflow/status")
def status():
    return jsonify(
        workflow_status(
            request.args.get("feature"),
            request.args.get("caller")
        )
    ), 200


if __name__ == "__main__":
    app.run(
        # 0.0.0.0 so backend containers can reach it through host.docker.internal
        host="0.0.0.0",  # noqa: S104
        port=int(os.getenv("PORT", "5004")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true"
    )
