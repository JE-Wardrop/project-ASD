# The agentic loop is a shared team tool, so nothing here is hardcoded to one
# feature. Each run targets one student folder, chosen with an environment
# variable:

#     REVIEW_TARGET=student-5 python agentic_loop.py

# Ports follow the team convention: frontend 810N, backend 820N, database 830N.
# 

import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Target:
    key: str                # "student-5"
    label: str              # "Transaction Management"
    owner: str
    frontend_port: int
    backend_port: int
    database_port: int
    root: Path              # <repo>/student-5

    @property
    def backend_url(self) -> str:
        return f"http://localhost:{self.backend_port}"

    @property
    def database_url(self) -> str:
        return f"http://localhost:{self.database_port}"

    @property
    def workflow_file(self) -> str:
        return f".github/workflows/{self.key}.yml"


_REGISTRY = {
    "student-1": ("Card Management",         "Juno", 8101, 8201, 8301),
    "student-2": ("Bank Account Management", "Binh", 8102, 8202, 8302),
    "student-3": ("Notification Management", "Ivan", 8103, 8203, 8303),
    "student-4": ("User Management",         "Sang", 8104, 8204, 8304),
    "student-5": ("Transaction Management",  "Gia",  8105, 8205, 8305),
}
def available_targets() -> list[str]:
    return sorted(_REGISTRY)


def resolve_target(repo_root: Path, key: str | None = None) -> Target:
    key = (key or os.getenv("REVIEW_TARGET", "")).strip()

    if key not in _REGISTRY:
        raise ValueError(
            f"Unknown review target: {key!r}. "
            f"Choose one of: {', '.join(available_targets())}"
        )

    label, owner, frontend, backend, database = _REGISTRY[key]
    return Target(
        key=key,
        label=label,
        owner=owner,
        frontend_port=frontend,
        backend_port=backend,
        database_port=database,
        root=repo_root / key,
    )