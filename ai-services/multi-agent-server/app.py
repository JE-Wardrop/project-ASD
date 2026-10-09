import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from coordinator import run_workflow, workflow_status


app = Flask(__name__)
CORS(app)


@app.get("/")
def health():
    return jsonify(
        {
            "service": "multi-agent-server",
            "status": "running"
        }
    )

# Doesn't work on my end: 405 error
# Try testing this as a normal POST reuquest and see what happens

@app.post("/workflow")
def workflow():


    # DEBUG 1
    return jsonify(
        workflow_status()
    ), 200


    # DEBUG 2
    # data = request.get_json(
    #     silent=True
    # ) or {}

    # user_request = data.get(
    #     "user_request",
    #     ""
    # ).strip()

    # return user_request


    # CODE

    # data = request.get_json(
    #     silent=True
    # ) or {}

    # user_request = data.get(
    #     "user_request",
    #     ""
    # ).strip()

    # if not user_request:
    #     return jsonify(
    #         {
    #             "status": "error",
    #             "error": "user_request is required"
    #         }
    #     ), 400

    # result = run_workflow(
    #     user_request
    # )

    # return jsonify(
    #     result
    # ), 200


# This route is working
@app.get("/workflow/status")
def status():
    return jsonify(
        workflow_status()
    ), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5004")),
        debug=True
    )