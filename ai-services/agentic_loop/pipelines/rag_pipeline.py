def build_implementation_prompt(task_prompt: str, evidence: str) -> str:
    return f"""
{task_prompt}

Review Scope:
RAG Pipeline Integration

Observed Evidence:
{evidence}

Validate that:
1. All 3 RAG tools are defined and callable
2. refresh_corpus, retrieve_context, and answer_question follow their contracts
3. Answers are expected to include citations and a confidence category

Reply in at most 40 words and stay evidence-based.
""".strip()


def build_review_prompt(implementation_output: str, evidence: str) -> str:
    return f"""
Implementation Recommendation:
{implementation_output}

Observed Evidence:
{evidence}

Validate the RAG integration assessment against the evidence.
Identify any gaps or risks in retrieval quality or citation grounding.

Reply in at most 40 words and stay evidence-based.
""".strip()