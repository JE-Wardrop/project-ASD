"""OBSERVE: discover the target's backend routes and probe the safe ones.

Only GET routes without path parameters are called. POST routes are listed
but never invoked - firing them would create real records in the student's
database, which is not something a review tool should do.
"""

import re
from pathlib import Path

import requests

# Matches @bp.get("/x"), @ai_mode_bp.post('/y'), @app.route("/z") ...
ROUTE_PATTERN = re.compile(
    r"@(\w+)\.(get|post|put|delete|route)\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

SAFE_TO_CALL = {"get", "route"}


def _discover_routes(routes_dir: Path) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for python_file in sorted(routes_dir.glob("*.py")):
        content = python_file.read_text(encoding="utf-8")
        for _decorator, method, path in ROUTE_PATTERN.findall(content):
            found.append((method.lower(), path))
    return sorted(set(found))


def _probe(base_url: str, path: str) -> str:
    try:
        response = requests.get(f"{base_url}{path}", timeout=3)
        elapsed_ms = int(response.elapsed.total_seconds() * 1000)
        return f"GET {path} -> {response.status_code} in {elapsed_ms}ms"
    except requests.exceptions.ConnectionError:
        return f"GET {path} -> connection refused"
    except requests.exceptions.Timeout:
        return f"GET {path} -> timed out"
    except requests.RequestException as exc:
        return f"GET {path} -> {type(exc).__name__}"


def collect(target, repo_root: Path) -> tuple[bool, str]:
    routes_dir = target.root / "backend" / "routes"
    if not routes_dir.is_dir():
        return False, f"{target.key}: backend/routes/ not found"

    routes = _discover_routes(routes_dir)
    if not routes:
        return False, f"{target.key}: no Flask routes found in backend/routes/"

    by_method: dict[str, int] = {}
    for method, _path in routes:
        by_method[method] = by_method.get(method, 0) + 1

    findings = [
        f"{len(routes)} route(s) declared: "
        + ", ".join(f"{count} {method.upper()}" for method, count in sorted(by_method.items()))
    ]

    # Probe only what is safe: GET routes with no <path> parameters
    probes = [
        path
        for method, path in routes
        if method in SAFE_TO_CALL and "<" not in path
    ]

    refused = 0
    for path in probes:
        result = _probe(target.backend_url, path)
        findings.append(result)
        if "connection refused" in result:
            refused += 1

    if probes and refused == len(probes):
        return False, (
            f"{target.key}: backend on port {target.backend_port} is not running. "
            "Start the services, then run the loop again."
        )

    skipped = len(routes) - len(probes)
    if skipped:
        findings.append(f"{skipped} route(s) not probed (write methods or path parameters)")

    return True, f"Endpoint evidence for {target.key} ({target.label}): " + "; ".join(findings) + "."