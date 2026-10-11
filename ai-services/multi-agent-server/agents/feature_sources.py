"""Where the Multi-Agent workflow gets its evidence from.

Same rule as mcp-server/tools.py: the workflow never opens another feature's
.db file. The Worker Agent reads evidence through that feature's database API
over HTTP. The Multi-Agent Server runs on the host (not in Docker), so it calls
each database container on its published host port (830N).
"""

import os
import re
from typing import Any, Dict, List, Optional

import requests


FEATURES: Dict[str, Dict[str, Any]] = {
    "cards": {
        "label": "Card Management",
        "owner": "student-1",
        "base_url": os.getenv("STUDENT1_DB_URL", "http://localhost:8301"),
        "path": "/cards",
        "items_key": None,
    },
    "accounts": {
        "label": "Bank Account Management",
        "owner": "student-2",
        "base_url": os.getenv("STUDENT2_DB_URL", "http://localhost:8302"),
        "path": "/accounts",
        "items_key": None,
    },
    "users": {
        "label": "User Management",
        "owner": "student-4",
        "base_url": os.getenv("STUDENT4_DB_URL", "http://localhost:8304"),
        "path": "/users",
        "items_key": None,
    },
    "transactions": {
        "label": "Transaction Management",
        "owner": "student-5",
        "base_url": os.getenv("STUDENT5_DB_URL", "http://localhost:8305"),
        "path": "/transactions",
        # student-5 wraps its rows: {"count": n, "transactions": [...]}
        "items_key": "transactions",
    },
}

# Checked in this order, so "card status for user_id 1" is about cards, not users,
# and "transactions for account_id 3" is about transactions, not accounts.
FEATURE_KEYWORDS = (
    ("cards", r"\bcards?\b"),
    ("transactions", r"\btransactions?\b"),
    ("accounts", r"\baccounts?\b"),
    ("users", r"\busers?\b"),
)

# "user_id(1)", "user id 1", "account_id: 3", "card-id 2"
ID_PATTERN = re.compile(r"\b(user|account|card|transaction)[\s_-]?id\W{0,3}(\d+)", re.IGNORECASE)

# Evidence is sent to the models and written to workflow_history.jsonl,
# so secrets are dropped and identifiers are masked before either happens.
DROP_FIELDS = {"password", "password_hash", "cvv", "pin"}
MASK_FIELDS = {"card_number", "account_number", "phone"}

MAX_EVIDENCE_RECORDS = int(os.getenv("MAX_EVIDENCE_RECORDS", "20"))
REQUEST_TIMEOUT_SECONDS = 5


class EvidenceError(Exception):
    """The feature's database API could not supply evidence."""


def supported_features() -> List[str]:
    return sorted(FEATURES)


def resolve_feature(
    feature: Optional[str],
    caller: Optional[str],
    user_request: str
) -> str:
    """Pick the feature: explicit value, then the caller's feature, then keywords.

    Raises ValueError when an explicit feature is unknown or nothing matches.
    """
    explicit = (feature or "").strip().lower()
    if explicit:
        if explicit in FEATURES:
            return explicit
        for key, source in FEATURES.items():
            if explicit == source["owner"]:
                return key
        raise ValueError(
            f"Unknown feature {feature!r}. Choose one of: {', '.join(supported_features())}"
        )

    caller_key = (caller or "").strip().lower()
    for key, source in FEATURES.items():
        if caller_key == source["owner"]:
            return key

    for key, pattern in FEATURE_KEYWORDS:
        if re.search(pattern, user_request, re.IGNORECASE):
            return key

    raise ValueError(
        "feature is required and could not be inferred from the request. "
        f"Choose one of: {', '.join(supported_features())}"
    )


def describe_source(feature: str) -> str:
    source = FEATURES[feature]
    return (
        f"{source['label']} database API "
        f"(GET {source['base_url']}{source['path']})"
    )


def extract_id_filters(user_request: str) -> Dict[str, str]:
    return {
        f"{name.lower()}_id": value
        for name, value in ID_PATTERN.findall(user_request)
    }


def _mask(value: Any) -> str:
    text = str(value)
    return "****" + text[-4:] if len(text) > 4 else "****"


def _mask_email(value: Any) -> str:
    local, _, domain = str(value).partition("@")
    return f"{local[:1]}***@{domain}" if domain else "****"


def redact(record: Dict[str, Any]) -> Dict[str, Any]:
    clean = {}
    for key, value in record.items():
        if key in DROP_FIELDS:
            continue
        if value is not None and key in MASK_FIELDS:
            clean[key] = _mask(value)
        elif value is not None and key == "email":
            clean[key] = _mask_email(value)
        else:
            clean[key] = value
    return clean


def _matching_fields(record: Dict[str, Any], field: str) -> List[str]:
    # account_id also matches sender_account_id / receiver_account_id
    return [key for key in record if key == field or key.endswith("_" + field)]


def apply_filters(
    records: List[Dict[str, Any]],
    filters: Dict[str, str]
) -> tuple[List[Dict[str, Any]], Dict[str, str], Dict[str, str]]:
    """Keep the records matching every applicable id filter.

    A filter is applicable when the feature's records carry that field.
    Returns (matching records, filters applied, filters ignored).
    """
    applied, ignored = {}, {}
    for field, value in filters.items():
        if any(_matching_fields(record, field) for record in records):
            applied[field] = value
        else:
            ignored[field] = value

    matching = [
        record for record in records
        if all(
            any(str(record[key]) == value for key in _matching_fields(record, field))
            for field, value in applied.items()
        )
    ]
    return matching, applied, ignored


def _fetch_records(feature: str) -> List[Dict[str, Any]]:
    source = FEATURES[feature]
    url = f"{source['base_url']}{source['path']}"

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.ConnectionError as exc:
        raise EvidenceError(
            f"Database API unreachable at {source['base_url']}. Is the container running?"
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise EvidenceError(
            f"Database API at {source['base_url']} did not respond in {REQUEST_TIMEOUT_SECONDS}s"
        ) from exc
    except requests.exceptions.HTTPError as exc:
        raise EvidenceError(f"Database API returned {response.status_code} for {url}") from exc
    except ValueError as exc:
        raise EvidenceError(f"Database API at {url} sent a non-JSON reply") from exc

    if source["items_key"] and isinstance(data, dict):
        data = data.get(source["items_key"], [])
    if not isinstance(data, list):
        raise EvidenceError(f"Database API at {url} sent an unexpected reply")

    return [record for record in data if isinstance(record, dict)]


def fetch_evidence(
    feature: str,
    user_request: str
) -> Dict[str, Any]:
    """Read the feature's records, narrow them to the ids named in the request,
    redact them, and cap how many are handed to the models.

    Raises EvidenceError when the database API cannot be read.
    """
    records = _fetch_records(feature)
    matching, applied, ignored = apply_filters(
        records,
        extract_id_filters(user_request)
    )

    return {
        "source": describe_source(feature),
        "total_records": len(records),
        "matched_records": len(matching),
        "filters_applied": applied,
        "filters_ignored": ignored,
        "records": [redact(record) for record in matching[:MAX_EVIDENCE_RECORDS]],
    }
