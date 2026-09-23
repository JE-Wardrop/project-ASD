"""The Plan -> Act -> Observe -> Adapt loop.

    PLAN     load the prompts that say what to check for this review target
    ACT      run the collector: real HTTP calls, real file reads, real SQL
    OBSERVE  the evidence the collector returned
    ADAPT    the model reads the evidence and recommends what to change next

The model never inspects the project itself. It only ever sees evidence that
Python gathered, which is what stops it inventing findings.
"""

from pathlib import Path

from collectors import (
    architecture_collector,
    db_collector,
    devops_collector,
    endpoints_collector,
    mcp_collector,
    rag_collector,
)
from config.review_config import ModeConfig
from core.ai_runner import AIRunner
from core.prompt_registry import PromptRegistry
from pipelines import (
    architecture_pipeline,
    db_pipeline,
    devops_pipeline,
    endpoints_pipeline,
    mcp_pipeline,
    rag_pipeline,
)

# Once RAG is being implemented we can comment out this line
COLLECTORS = {
    "db": db_collector.collect,
    "endpoints": endpoints_collector.collect,
    "architecture": architecture_collector.collect,
    "devops": devops_collector.collect,
    "mcp": mcp_collector.collect,
    "rag": rag_collector.collect,
}

DUAL_MODEL_MODES = {"architecture", "devops"}

REVIEW_PIPELINES = {
    "architecture": architecture_pipeline,
    "devops": devops_pipeline,
    "mcp": mcp_pipeline,
    "rag": rag_pipeline,
}


def _stage(mode_label: str, phase: str, message: str) -> None:
    print(f"[{mode_label:<12}][{phase:<7}] {message}")


def run_mode(mode: ModeConfig, target, repo_root: Path,
             prompts: PromptRegistry, ai: AIRunner) -> str:
    
    """Run one review target through the four phases."""

    _stage(mode.label, "PLAN", f"Reviewing {target.key} ({target.label}) for {target.owner}")
    _stage(mode.label, "PLAN", f"Loading prompt family: {mode.prompt_family}")

    try:
        # MCP Plan code ------------------
        if mode.key == "mcp":
            _stage(mode.label, "PROMPTS", f"Loading prompt family: {mode.prompt_family}")
            task_prompt = prompts.read(mode.prompt_family, mode.implementation_prompts[0])
            system_prompt = (
                "You are a precise MCP integration validator. "
                "Use only supplied evidence and reply in at most 40 words."
            )
         
        # RAG Plan code ---------------------------------------

        elif mode.key == "rag":
            _stage(mode.label, "PROMPTS", f"Loading prompt family: {mode.prompt_family}")
            task_prompt = prompts.read(mode.prompt_family, mode.implementation_prompts[0])
            system_prompt = (
                "You are a precise RAG pipeline validator. "
                "Use only supplied evidence and reply in at most 40 words."
            )

        # Code for other loops ----------------------------------------

        else: 
            system_prompt = prompts.read(mode.prompt_family, mode.implementation_prompts[0])
            task_prompt = prompts.read(mode.prompt_family, mode.implementation_prompts[1])


    except FileNotFoundError as exc:
        _stage(mode.label, "PLAN", "Failed")
        return f"PLAN FAILED: {exc}"


    # ---------------------------------------------------------------- ACT
    _stage(mode.label, "ACT", "Gathering evidence from the running system")
    collector = COLLECTORS[mode.key]
    
    ok, evidence = collector(target, repo_root)

    if not ok:
        _stage(mode.label, "ACT", "Failed")
        return f"ACT FAILED: {evidence}"

        # --------------------------------------------------------- MCP ACT
    if mode.key == "mcp":
        implementation_user_prompt = mcp_pipeline.build_implementation_prompt(task_prompt, evidence)
        _stage(mode.label, "PROMPTS", "Loaded MCP implementation prompt")

        _stage(mode.label, "LLM", "Running MCP implementation model")
        implementation_output, err = ai.call(system_prompt, implementation_user_prompt, review=False)
        if err:
            _stage(mode.label, "LLM", "Failed")
            return f"MODEL FAILED: {err}"
        _stage(mode.label, "LLM", "MCP implementation model complete")

        # ------------------------------------------------------------- RAG ACT
    if mode.key == 'rag':
        # Causing same issues with RAG pipeline.
        implementation_user_prompt = rag_pipeline.build_implementation_prompt(task_prompt, evidence)
        _stage(mode.label, "PROMPTS", "Loaded RAG implementation prompt")

        _stage(mode.label, "LLM", "Running RAG implementation model")
        implementation_output, err = ai.call(system_prompt, implementation_user_prompt, review=False)
        if err:
            _stage(mode.label, "LLM", "Failed")
            return f"MODEL FAILED: {err}"
        _stage(mode.label, "LLM", "RAG implementation model complete")

    # ------------------------------------------------------------ OBSERVE
    _stage(mode.label, "OBSERVE", evidence)

    # -------------------------------------------------------------- ADAPT
    if mode.key in {"db", "endpoints"}:
        context_prompt = prompts.read(mode.prompt_family, mode.implementation_prompts[2])

        builder = db_pipeline if mode.key == "db" else endpoints_pipeline
        user_prompt = builder.build_user_prompt(task_prompt, context_prompt, evidence)

        _stage(mode.label, "ADAPT", f"Asking {ai.implementation_model} what to change")
        output, err = ai.call(system_prompt, user_prompt, review=False)
        if err:
            _stage(mode.label, "ADAPT", "Failed")
            return f"MODEL FAILED: {err}"

        _stage(mode.label, "DONE", "Review complete")
        return f"OBSERVE: {evidence}\n\nADAPT: {output}"

    if mode.key in DUAL_MODEL_MODES:
        pipeline = REVIEW_PIPELINES[mode.key]
        user_prompt = pipeline.build_implementation_prompt(task_prompt, evidence)

        _stage(mode.label, "ADAPT", f"Asking {ai.implementation_model} what to change")
        first_output, err = ai.call(system_prompt, user_prompt, review=False)
        if err:
            _stage(mode.label, "ADAPT", "Failed")
            return f"MODEL FAILED: {err}"

        
        review_system_prompt = prompts.read(mode.prompt_family, mode.review_prompts[0])
        review_user_prompt = pipeline.build_review_prompt(first_output, evidence)

        _stage(mode.label, "ADAPT", f"Second pass with {ai.review_model}")
        review_output, review_err = ai.call(review_system_prompt, review_user_prompt, review=True)
        if review_err:
            review_output = f"(review model unavailable: {review_err})"
            _stage(mode.label, "ADAPT", "Review model unavailable, keeping first pass")

        _stage(mode.label, "DONE", "Review complete")
        return (
            f"OBSERVE: {evidence}\n\n"
            f"ADAPT: {first_output}\n\n"
            f"SECOND OPINION: {review_output}"
        )


    # -------------------------------------------------------- MCP ADAPT

    if mode.key in {"mcp"}:
        pass

        # Causing errors (full error message):
            #   File "/home/juno/Desktop/ASD 2026/project-ASD/ai-services/agentic_loop/core/orchestrator.py", line 245, in run_mode
            # review_prompt_text = prompts.read(mode.prompt_family, mode.review_prompts[0])
            #           File "/home/juno/Desktop/ASD 2026/project-ASD/ai-services/agentic_loop/core/prompt_registry.py", line 17, in read
            #     return self.resolve(family, relative_file).read_text(encoding="utf-8").strip()
            #            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            #   File "/home/juno/Desktop/ASD 2026/project-ASD/ai-services/agentic_loop/core/prompt_registry.py", line 13, in resolve
            #     raise FileNotFoundError(f"Missing prompt file: {rel}")
            # FileNotFoundError: Missing prompt file: prompts/mcp/review/tool_review_prompts.txt

        # This is a file path error. 
            # It could be that for whatever reason the file path is:
            # {repo_root}/prompts/mcp/review/tool_review_prompts.txt
            # and not
            # {repo_root}/ai-services/prompts/mcp/review/tool_review_prompts.txt


        # This needs to be fixed to make it so it goes to the review_prompt_text using the file paths.
        # So instead of copying and pasting the entire txt file it should be:
        # review_prompt_text = prompts.read(mode.prompt_family, mode.review_prompts[0])


        # Debugging
        # print(f"mode.prompt_family: ", {mode.prompt_family} 
        #       , "mode.review_prompts[0]: ", {mode.review_prompts[0]}
        #       , "mode.review_prompts[1]: ", {mode.review_prompts[1]}

        #       )

        review_prompt_text = (
            "You are a CONCISE MCP TOOL REVIEW AGENT."

            "Your role: Review one MCP tool improvement proposal using execution evidence only."

            "Input:"
            "{{IMPROVEMENT_PROPOSAL}} - The proposed tool improvement"
            "{{TOOL_EVIDENCE_BEFORE}} - Tool execution evidence before improvement"
            "{{TOOL_EVIDENCE_AFTER}} - Tool execution evidence after improvement (if available)"

            "Strict Rules:"
            " 1. Use ONLY the provided {{TOOL_EVIDENCE_BEFORE}} and {{TOOL_EVIDENCE_AFTER}}"
            " 2. Validate improvement addresses a specific, observable issue"
            " 3. Confirm correction is feasible within tool scope"
            " 4. Ensure retest step is measurable"
            " 5. Reject proposals without evidence"

            " Validation Checks:"

            " **Risk Specificity:**"
            " - Is the stated risk based on actual evidence?"
            " Can the risk be reproduced?"
            " Is the risk severity clear?"

            " **Correction Feasibility:**"
            " Does correction stay within tool boundaries?"
            " Is correction implementable?"
            " Does correction avoid breaking existing functionality?"

            " **Retest Measurability:**"
            " Can retest be executed?"
            " Is success criteria clear?"
            " Is evidence capture defined?"

            " **Evidence Match:**"
            " Do claims match available evidence?"
            " Is before/after comparison valid?"
            " Are all assertions testable?"

            " Output Format:"

            "Risk: [specific risk with evidence - max 20 words]"
            "Correction: [feasible fix - max 20 words]"
            "Retest: [measurable verification step - max 20 words]"

            "Maximum 60 words total."

            "Forbidden:"
            "- Accepting proposals without evidence"
            "- Approving changes outside tool scope"
            "- Vague retest steps"
            ,

            
        )

        review_user_prompt = mcp_pipeline.build_review_prompt(implementation_output, evidence)

        _stage(mode.label, "PROMPTS", "Loaded MCP review prompt")

        _stage(mode.label, "LLM", "Running MCP review model")

        review_output, review_err = ai.call(review_prompt_text, review_user_prompt, review=True)

        if review_err:
            review_output = review_err
            _stage(mode.label, "LLM", "Review model failed")
        else:
            _stage(mode.label, "LLM", "Review model complete")

        _stage(mode.label, "DONE", "Review complete")


        return (
            f"OBSERVE: {evidence}\n\n"
            f"IMPLEMENTATION: {implementation_output}\n"
            f"REVIEW: {review_output}"
        )
    # ------------------------------------------------------------- RAG ADAPT


    if mode.key == "rag":
        # These lines will give the same errors as MCP, as they are programmed in the same way. 

        review_prompt_text = prompts.read(mode.prompt_family, mode.review_prompts[0])
        reasoning_prompt_text = prompts.read(mode.prompt_family, mode.review_prompts[1])



        review_system_prompt = f"{review_prompt_text}\n\n{reasoning_prompt_text}"
        review_user_prompt = rag_pipeline.build_review_prompt(implementation_output, evidence)
        _stage(mode.label, "PROMPTS", "Loaded RAG review and reasoning prompts")
        _stage(mode.label, "LLM", "Running RAG review model")
        review_output, review_err = ai.call(review_system_prompt, review_user_prompt, review=True)
        if review_err:
            review_output = review_err
            _stage(mode.label, "LLM", "Review model failed")
        else:
            _stage(mode.label, "LLM", "Review model complete")

        _stage(mode.label, "DONE", "Review complete")

        return (
            f"OBSERVE: {evidence}\n\n"
            f"IMPLEMENTATION: {implementation_output}\n"
            f"REVIEW: {review_output}"
        )



    return "Unknown mode."