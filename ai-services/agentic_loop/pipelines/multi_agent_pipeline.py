def build_implementation_prompt(task_prompt: str, evidence: str) -> str:
    return f"""
{task_prompt}

Review Scope:
Multi-Agent Workflow Coordination

Observed Evidence:
{evidence}

Validate that:
1. Planner, Worker, and Reviewer agents are each implemented with their required entry function
2. The Coordinator wires all three agents into a single workflow
3. The Multi-Agent API and enrolment-service route are present for UI integration

Reply in at most 40 words and stay evidence-based.
""".strip()


def build_review_prompt(implementation_output: str, evidence: str) -> str:
    return f"""
Implementation Recommendation:
{implementation_output}

Observed Evidence:
{evidence}

Validate the multi-agent coordination assessment against the evidence.
Identify any gaps or risks in agent sequencing, evidence grounding, or human approval gating.

Reply in at most 40 words and stay evidence-based.
""".strip()