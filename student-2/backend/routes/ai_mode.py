from flask import Blueprint, request

from services.llm_client import OLLAMA_MODEL, create_chat_completion
from services.prompt_loader import load_service_prompt

ai_mode_bp = Blueprint("ai_mode", __name__)


@ai_mode_bp.post("/ask")
def ask_local_agent():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    try:
        answer = create_chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a concise banking assistant for the Bank Account "
                        "Management service. Answer in one short paragraph unless "
                        "asked otherwise."
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
            "Check that Ollama is running and that the configured model is installed.</p>"
            f"<pre>{exc}</pre>",
            503,
        )


@ai_mode_bp.post("/ask-with-context")
def ask_with_context():
    question = request.form.get("question", "").strip()

    if not question:
        return "<p>Question is required.</p>", 400

    try:
        context_qa_prompt = load_service_prompt("context_qa_task_prompt.txt")
        context_prompt = load_service_prompt("context_prompt.txt")

        final_prompt = f"""
{context_qa_prompt}

{context_prompt}

User Question:

{question}
"""

        answer = create_chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a concise banking assistant for the Bank Account "
                        "Management service. Answer the user's question directly "
                        "using only the supplied context."
                    ),
                },
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
