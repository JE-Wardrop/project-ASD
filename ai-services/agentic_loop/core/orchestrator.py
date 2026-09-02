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
)
from config.review_config import ModeConfig
from core.ai_runner import AIRunner
from core.prompt_registry import PromptRegistry
from pipelines import (
    architecture_pipeline,
    db_pipeline,
    devops_pipeline,
    endpoints_pipeline,
)


COLLECTORS = {
    "db": db_collector.collect,
    "endpoints": endpoints_collector.collect,
    "architecture": architecture_collector.collect,
    "devops": devops_collector.collect,
}

# Modes that run a second, larger model to review the first model's output
DUAL_MODEL_MODES = {"architecture", "devops"}

REVIEW_PIPELINES = {
    "architecture": architecture_pipeline,
    "devops": devops_pipeline,
}


def _stage(mode_label: str, phase: str, message: str) -> None:
    print(f"[{mode_label:<12}][{phase:<7}] {message}")


def run_mode(mode: ModeConfig, target, repo_root: Path,
             prompts: PromptRegistry, ai: AIRunner) -> str:
    """Run one review target through the four phases."""

    _stage(mode.label, "PLAN", f"Reviewing {target.key} ({target.label}) for {target.owner}")
    _stage(mode.label, "PLAN", f"Loading prompt family: {mode.prompt_family}")

    try:
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

    return "Unknown mode."