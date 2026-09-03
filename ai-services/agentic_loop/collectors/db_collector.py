# OBSERVE: gather real evidence about the target's database microservice.

# Nothing here is specific to one feature. It checks what the specification
# requires of every student: an owned schema, at least ten seeded records,
# and a database service that answers /health.


import re
import sqlite3
from pathlib import Path

import requests

MIN_SEED_ROWS = 10          # required by the project specification


def _load_schema_in_memory(schema_sql: str, seed_sql: str) -> tuple[dict[str, int], str | None]:
    """Run schema.sql and seed.sql against an in-memory database.

    This proves the SQL actually works, and gives a real row count per table
    without touching the developer's own database file.
    """
    try:
        connection = sqlite3.connect(":memory:")
        connection.executescript(schema_sql)
        connection.executescript(seed_sql)
    except sqlite3.Error as exc:
        return {}, f"SQL failed to execute: {exc}"

    tables = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    ]
    counts = {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in tables
    }
    connection.close()
    return counts, None


def collect(target, repo_root: Path) -> tuple[bool, str]:
    database_dir = target.root / "database"
    schema_path = database_dir / "schema.sql"
    seed_path = database_dir / "seed.sql"

    findings: list[str] = []

    # --- schema and seed files -------------------------------------------
    missing = [p.name for p in (schema_path, seed_path) if not p.exists()]
    if missing:
        return False, f"{target.key}: missing {', '.join(missing)} in database/"

    schema_sql = schema_path.read_text(encoding="utf-8")
    seed_sql = seed_path.read_text(encoding="utf-8")

    check_constraints = len(re.findall(r"\bCHECK\s*\(", schema_sql, re.IGNORECASE))
    findings.append(f"schema.sql defines {check_constraints} CHECK constraint(s)")

    # --- do the schema and seed actually run? ----------------------------
    counts, error = _load_schema_in_memory(schema_sql, seed_sql)
    if error:
        return False, f"{target.key}: {error}"

    for table, count in counts.items():
        state = "meets" if count >= MIN_SEED_ROWS else "BELOW"
        findings.append(f"table '{table}' seeded with {count} rows ({state} the minimum of {MIN_SEED_ROWS})")

    # --- is the live database service answering? -------------------------
    try:
        response = requests.get(f"{target.database_url}/health", timeout=3)
        findings.append(
            f"database service on port {target.database_port} "
            f"returned {response.status_code} for /health"
        )
    except requests.RequestException:
        findings.append(
            f"database service on port {target.database_port} is not running "
            "(file evidence only)"
        )

    return True, f"Database evidence for {target.key} ({target.label}): " + "; ".join(findings) + "."