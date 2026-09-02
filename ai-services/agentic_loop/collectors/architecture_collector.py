"""OBSERVE: check the target follows the required microservices architecture.

The strongest check here is the cross-feature rule: a backend must reach
another feature's data through that feature's API, never by opening its
SQLite file.
"""

from pathlib import Path

REQUIRED_TIERS = ("frontend", "backend", "database")


def collect(target, repo_root: Path) -> tuple[bool, str]:
    findings: list[str] = []

    # --- three tiers present, each containerised -------------------------
    missing_tiers = [tier for tier in REQUIRED_TIERS if not (target.root / tier).is_dir()]
    if missing_tiers:
        return False, f"{target.key}: missing tier(s) {', '.join(missing_tiers)}"

    for tier in REQUIRED_TIERS:
        has_dockerfile = (target.root / tier / "Dockerfile").exists()
        findings.append(f"{tier}: Dockerfile {'present' if has_dockerfile else 'MISSING'}")

    # --- cross-feature rule ----------------------------------------------
    backend_dir = target.root / "backend"
    direct_sqlite = [
        str(path.relative_to(target.root))
        for path in backend_dir.rglob("*.py")
        if "sqlite3" in path.read_text(encoding="utf-8")
    ]
    if direct_sqlite:
        findings.append(
            "VIOLATION - backend opens SQLite directly in: " + ", ".join(direct_sqlite)
        )
    else:
        findings.append("backend contains no direct SQLite access (data reached through APIs)")

    # --- who does this feature depend on? --------------------------------
    services_dir = backend_dir / "services"
    if services_dir.is_dir():
        clients = sorted(p.stem for p in services_dir.glob("*_api.py"))
        findings.append(
            "service clients: " + (", ".join(clients) if clients else "none found")
        )

    # --- declared in the shared compose file? ----------------------------
    compose_path = repo_root / "docker-compose.yml"
    if not compose_path.exists():
        findings.append("docker-compose.yml MISSING at repository root")
    else:
        compose_text = compose_path.read_text(encoding="utf-8")
        number = target.key.split("-")[1]
        expected = [f"student{number}-frontend", f"student{number}-backend", f"student{number}-db"]
        declared = [name for name in expected if name in compose_text]
        findings.append(
            f"compose declares {len(declared)}/3 services for {target.key}"
            + ("" if len(declared) == 3 else f" (missing: {', '.join(set(expected) - set(declared))})")
        )

    return True, f"Architecture evidence for {target.key} ({target.label}): " + "; ".join(findings) + "."