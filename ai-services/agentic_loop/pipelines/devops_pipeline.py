def build_implementation_prompt(task_prompt: str, evidence: str) -> str:
    return f"""
{task_prompt}

Evidence:
{evidence}
""".strip()


def build_review_prompt(implementation_output: str, evidence: str) -> str:
    return f"""
Proposed DevOps improvements:
{implementation_output}

Evidence they were based on:
{evidence}
""".strip()