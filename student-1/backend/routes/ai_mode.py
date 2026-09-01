from flask import Blueprint, request


from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

#why is not importing call_architecture_agent? it is fine it is in the file as normal?
from services.llm_client import OLLAMA_MODEL, call_architecture_agent, create_chat_completion
from services.prompt_loader import load_prompt

ai_mode_bp = Blueprint("ai_mode", __name__)


@ai_mode_bp.post("/ask", methods=["POST"])
def ask_local_agent():

    # Non lab code

    # data = request.json
    # user_prompt = data.get('prompt', '')


    # payload = {
    #     "model":OLLAMA_MODEL,
    #     "prompt": user_prompt,
    #     "stream": False
    # }

    # try:
    #     response = requests.post(OLLAMA_MODEL, json=payload)
    #     response_data = response.json()
    #     return jsonify({"response": response_data.get("response", "No output generated.")})
    # except Exception as e:
    #     return jsonify({"response": f"Backend Error: {str(e)}"}), 500

    # Lab code

    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    try:
        answer = create_chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a concise software engineering assistant. "
                        "Answer in one short paragraph unless asked otherwise."
                    ),
                },
                {"role": "user", "content": question},
            ],
            max_tokens=200,
            temperature=0.2,
            model=OLLAMA_MODEL,
        )
        return f"<p>{answer}</p>", 200

    
    except Exception as exc:
        return (
            "<p>Local AI agent request failed. "
            "Check that Ollama is running and that qwen2.5:0.5b is installed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@ai_mode_bp.post("/ask-with-context")
def ask_with_context():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    try:
        system_prompt = load_prompt("service/implementation/system_prompt.txt")
        task_prompt = load_prompt("service/implementation/task_prompt.txt")
        context_prompt = load_prompt("service/implementation/context_prompt.txt")

        final_prompt = f"""
{task_prompt}

{context_prompt}

User Question:

{question}
"""

        answer = create_chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_prompt},
            ],
            max_tokens=300,
            temperature=0.2,
            model=OLLAMA_MODEL,
        )
        return f"<p>{answer}</p>", 200
    except Exception as exc:
        return (
            "<p>Context-aware request failed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )



