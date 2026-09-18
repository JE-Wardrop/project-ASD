def build_implementation_prompt(task_prompt: str, evidence: str) -> str:
    return f"""
{task_prompt}

Review Scope:
MCP Tool Integration

Observed Evidence:
{evidence}

Validate that:
1. All 4 MCP tools are defined and callable
2. Tool boundaries are clear (what each tool does and does not do)
3. MCP endpoints exist in routes/mcp_mode.py
4. Prompts exist for tool selection and integration review

Reply in at most 40 words and stay evidence-based.
""".strip()


def build_review_prompt(implementation_output: str, evidence: str) -> str:
    return f"""
Implementation Recommendation:
{implementation_output}

Observed Evidence:
{evidence}

Validate the MCP integration assessment against the evidence.
Identify any gaps or risks in tool definitions or boundaries.

Reply in at most 40 words and stay evidence-based.
""".strip()