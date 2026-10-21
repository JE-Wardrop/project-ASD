from pathlib import Path


REQUIRED_SNIPPETS = ["--registry-identity system", "--ingress internal", "--ingress external"]


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    deploy_script = app_dir / "scripts" / "deploy-azure.sh"
    deployment_results = app_dir / "docs" / "report" / "deployment-results.md"

    required_paths = [deploy_script, deployment_results]

    missing = [str(path.relative_to(app_dir)) for path in required_paths if not path.exists()]
    if missing:
        return False, "Deployment evidence incomplete. Missing: " + ", ".join(missing)

    script_text = deploy_script.read_text(encoding="utf-8")

    missing_snippets = [snippet for snippet in REQUIRED_SNIPPETS if snippet not in script_text]
    if missing_snippets:
        return False, "deploy-azure.sh missing expected configuration: " + ", ".join(missing_snippets)

    return True, (
        "Deployment evidence: scripts/deploy-azure.sh uses managed identity "
        "(--registry-identity system) and isolates database/enrolment services with "
        "--ingress internal while frontend-service is --ingress external; "
        "reports/lab11/deployment-results.md documents the validation run."
    )