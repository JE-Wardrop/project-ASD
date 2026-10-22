"""Cloud Deployment Review: the group's Azure deployment, seen from one student.

Evidence: the reusable scripts in scripts/clouddeployment/, the
cloud-deployment.yml workflow, whether this student is deployed and validated,
and the latest validation results in docs/cloud-deployment/deployment-results.md.
"""

import re
from pathlib import Path

SCRIPTS = ["env-setup.sh", "deploy-azure-env.sh", "deploy-azure.sh", "deployment-testing.sh"]
AI_FLAGS_OFF = ["AI_MODE_ENABLED=false", "MCP_ENABLED=false", "RAG_ENABLED=false", "MULTI_AGENT_ENABLED=false"]


def collect(target, repo_root: Path) -> tuple[bool, str]:
    scripts_dir = repo_root / "scripts" / "clouddeployment"
    workflow_path = repo_root / ".github" / "workflows" / "cloud-deployment.yml"
    results_path = repo_root / "docs" / "cloud-deployment" / "deployment-results.md"

    required_paths = [scripts_dir / name for name in SCRIPTS] + [workflow_path]
    missing = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing:
        return False, "Deployment evidence incomplete. Missing: " + ", ".join(missing)

    deploy_text = (scripts_dir / "deploy-azure.sh").read_text(encoding="utf-8")
    workflow_text = workflow_path.read_text(encoding="utf-8")

    deployed = re.search(r'STUDENTS="\$\{STUDENTS:-([^}]*)\}"', deploy_text)
    deployed_students = deployed.group(1).split() if deployed else []

    lines = [
        "Deployment evidence: Azure Container Apps via scripts/clouddeployment/ "
        f"({', '.join(SCRIPTS)}).",
        f"{target.key} {'is' if target.key in deployed_students else 'is NOT'} in the default STUDENTS list "
        f"({' '.join(deployed_students) or 'not found'}).",
        "Registry pull credentials: "
        + ("managed identity (--registry-identity system)" if "--registry-identity system" in deploy_text
           else "registry admin username/password (--registry-password)" if "--registry-password" in deploy_text
           else "not found") + ".",
        # deploy_app "<app>" "<image>" "<port>" <ingress> ... : database and backend
        # are deployed internal, the frontend external (the only public app).
        "Ingress: database and backend internal, frontend external: "
        + ("yes" if deploy_text.count('" internal ') >= 2 and '" external ' in deploy_text
           else "not confirmed") + ".",
        "AI services disabled by default in the cloud: "
        + ("yes (" + ", ".join(AI_FLAGS_OFF) + ")" if all(f in deploy_text for f in AI_FLAGS_OFF)
           else "missing: " + ", ".join(f for f in AI_FLAGS_OFF if f not in deploy_text)) + ".",
        "cloud-deployment.yml gates on student CI results before deploying: "
        + ("yes" if "ci-gate" in workflow_text and "needs: [ci-gate]" in workflow_text else "no") + ".",
    ]

    if results_path.exists():
        results = results_path.read_text(encoding="utf-8")
        row = next((line for line in results.splitlines() if line.startswith(f"| {target.key} ")), None)
        lines.append(
            f"Latest validation ({results_path.relative_to(repo_root)}): "
            + (row.strip() if row else f"no row for {target.key}") + "."
        )
    else:
        lines.append(
            f"No validation results yet ({results_path.relative_to(repo_root)} missing): "
            "the deployment has not been run and validated with deployment-testing.sh."
        )

    return True, " ".join(lines)
