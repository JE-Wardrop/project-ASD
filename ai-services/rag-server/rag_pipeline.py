"""RAG pipeline for the Digital Banking System — adapted from Lab 8.

Same flow and function names as Lab 8:
    REFRESH  -> refresh_corpus()
    RETRIEVE -> retrieve_context()
    ANSWER   -> answer_question()

Every place that differs from Lab 8 is marked with  # CHANGED FROM LAB 8
"""

import json
import os
import re
import time
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
import requests

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"  # CHANGED FROM LAB 8: replaces REPORTS_DIR
CORPUS_PATH = BASE_DIR / "corpus" / "corpus.jsonl"
AUDIT_PATH = BASE_DIR / "rag-audit.jsonl"
CHROMA_PATH = BASE_DIR / "chroma"

# CHANGED FROM LAB 8: Lab 8 opened one SQLite file (DB_PATH_CANDIDATES).
# Here each feature owns its database, so we call its database API over HTTP.
# The RAG server runs on the host, so it uses the ports published in
# docker-compose.yml.
DB_API_URLS = {
    "cards": os.getenv("STUDENT1_DB_URL", "http://localhost:8301"),
    "accounts": os.getenv("STUDENT2_DB_URL", "http://localhost:8302"),
    "users": os.getenv("STUDENT4_DB_URL", "http://localhost:8304"),
    "transactions": os.getenv("STUDENT5_DB_URL", "http://localhost:8305"),
}

# CHANGED FROM LAB 8: which endpoint to read for each feature, and which
# fields go into the corpus. Card numbers, account numbers, emails and
# phone numbers are left out on purpose.
DB_SOURCES = {
    "cards": {
        "path": "/cards",
        "id_field": "card_id",
        "fields": ["card_id", "user_id", "card_type", "status", "expiry_date"],
    },
    "accounts": {
        "path": "/accounts",
        "id_field": "account_id",
        "fields": ["account_id", "user_id", "account_type", "account_status", "balance"],
    },
    "users": {
        "path": "/users",
        "id_field": "user_id",
        "fields": ["user_id", "username", "role"],
    },
    "transactions": {
        "path": "/transactions",
        "id_field": "transaction_id",
        "fields": [
            "transaction_id", "transaction_type", "status", "amount",
            "sender_account_id", "receiver_account_id", "description", "created_at",
        ],
    },
}

OLLAMA_GENERATE_URL = os.getenv("OLLAMA_GENERATE_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

COLLECTION_NAME = "bank_system_enterprise_context"
EMBED_VECTOR_SIZE = 256

INSUFFICIENT_ANSWER = "Insufficient context: no relevant records were found for this question."

# CHANGED FROM LAB 8: common words ignored when checking if a chunk is relevant.
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "what", "which", "who",
    "why", "how", "when", "where", "do", "does", "did", "can", "i", "me", "my",
    "you", "your", "it", "of", "in", "on", "at", "to", "for", "from", "by",
    "with", "about", "and", "or", "there", "this", "that", "any", "all",
    "show", "list", "tell", "give", "please", "many", "much", "have", "has",
    "today", "now",
}

_collection = None
_last_corpus_chunks: list[dict[str, Any]] = []
_unavailable_sources: dict[str, str] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def embed_texts(texts: list[str]) -> list[list[float]]:
    # Same as Lab 8: hash each word into a 256-number vector.
    vectors: list[list[float]] = []

    for text in texts:
        values = [0.0] * EMBED_VECTOR_SIZE
        tokens = (text or "").lower().split()

        if not tokens:
            vectors.append(values)
            continue

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i, byte in enumerate(digest):
                idx = i % EMBED_VECTOR_SIZE
                values[idx] += (byte / 255.0) - 0.5

        norm = sum(v * v for v in values) ** 0.5
        if norm > 0:
            values = [v / norm for v in values]

        vectors.append(values)

    return vectors


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def reset_collection() -> None:
    global _collection
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass
    _collection = client.get_or_create_collection(name=COLLECTION_NAME)


def append_audit(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_output: dict[str, Any],
    validation_status: str,
    outcome: str,
    start_time: float,
) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int((time.time() - start_time) * 1000)
    record = {
        "request_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_output": tool_output,
        "timestamp": now_iso(),
        "duration_ms": duration_ms,
        "validation_status": validation_status,
        "outcome": outcome,
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def chunk_text(text: str, max_words: int = 80) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def load_database_chunks() -> list[dict[str, Any]]:
    # CHANGED FROM LAB 8: loops over every feature's database API instead of
    # reading one SQLite file. A database that is down is recorded in
    # _unavailable_sources and skipped — its error never becomes a chunk.
    _unavailable_sources.clear()
    chunks: list[dict[str, Any]] = []

    for feature, source in DB_SOURCES.items():
        url = DB_API_URLS[feature] + source["path"]
        try:
            response = requests.get(url, params={"limit": 500}, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            _unavailable_sources[feature] = str(exc)
            continue

        # /transactions returns {"transactions": [...]}; the others return a list.
        records = data.get(feature, []) if isinstance(data, dict) else data

        chunks.append(
            {
                "chunk_id": f"{feature}_count",
                "source_id": url,
                "authority_tier": "tier_1",
                "text": f"{feature.capitalize()} count is {len(records)}.",
                "metadata": {"source_type": "database", "feature": feature, "metric": "count"},
                "indexed_at": now_iso(),
            }
        )

        for record in records[:500]:
            fields = ", ".join(f"{name}={record.get(name)}" for name in source["fields"])
            record_id = record.get(source["id_field"])
            chunks.append(
                {
                    "chunk_id": f"{feature}_{record_id}",
                    "source_id": url,
                    "authority_tier": "tier_1",
                    "text": f"{feature.capitalize()} record: {fields}.",
                    "metadata": {"source_type": "database", "feature": feature},
                    "indexed_at": now_iso(),
                }
            )

    return chunks


def load_knowledge_chunks() -> list[dict[str, Any]]:
    # CHANGED FROM LAB 8: replaces load_report_chunks(). Reads the business
    # rules each student writes in knowledge/<feature>.md (tier_2, like
    # Lab 8's reports).
    chunks: list[dict[str, Any]] = []
    if not KNOWLEDGE_DIR.exists():
        return chunks

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        feature = path.stem
        text = path.read_text(encoding="utf-8", errors="ignore")
        for i, chunk in enumerate(chunk_text(text), start=1):
            chunks.append(
                {
                    "chunk_id": f"knowledge_{feature}_{i}",
                    "source_id": f"knowledge/{path.name}",
                    "authority_tier": "tier_2",
                    "text": chunk,
                    "metadata": {"source_type": "knowledge", "feature": feature},
                    "indexed_at": now_iso(),
                }
            )

    return chunks


def build_corpus() -> list[dict[str, Any]]:
    # CHANGED FROM LAB 8: load_repository_chunks() was removed. It added one
    # long list of file names that matched almost any question.
    chunks: list[dict[str, Any]] = []
    chunks.extend(load_database_chunks())
    chunks.extend(load_knowledge_chunks())
    return chunks


def write_corpus(chunks: list[dict[str, Any]]) -> None:
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CORPUS_PATH.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")


def read_corpus() -> list[dict[str, Any]]:
    if not CORPUS_PATH.exists():
        return []

    chunks: list[dict[str, Any]] = []
    with CORPUS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return chunks


def keywords(text: str) -> set[str]:
    # CHANGED FROM LAB 8 (new helper): meaningful words of a text, with a
    # simple plural strip so "transactions" matches "transaction".
    words = set()
    for word in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if len(word) > 3 and word.endswith("s"):
            word = word[:-1]
        if word not in STOPWORDS:
            words.add(word)
    return words


def keep_relevant(query: str, rows: list[dict[str, Any]], k: int) -> list[dict[str, Any]]:
    # CHANGED FROM LAB 8 (new helper): Lab 8 always returned the top k chunks,
    # even for unrelated questions. Here a chunk must share at least one
    # keyword with the question; the best matches come first.
    query_words = keywords(query)
    tier_weight = {"tier_1": 3, "tier_2": 2, "tier_3": 1}

    relevant = []
    for row in rows:
        overlap = len(query_words & keywords(row.get("text", "")))
        if overlap > 0:
            relevant.append({**row, "_score": overlap})

    relevant.sort(
        key=lambda r: (r["_score"], tier_weight.get(r.get("authority_tier"), 0)),
        reverse=True,
    )

    top = relevant[: max(k, 1)]
    for i, row in enumerate(top, start=1):
        row["rank"] = i
        row.pop("_score", None)
    return top


def lexical_fallback_retrieve(query: str, k: int, feature: str | None = None) -> list[dict[str, Any]]:
    corpus = _last_corpus_chunks or read_corpus()
    rows = [
        {
            "chunk_id": chunk.get("chunk_id"),
            "source_id": chunk.get("source_id"),
            "authority_tier": chunk.get("authority_tier"),
            "feature": chunk.get("metadata", {}).get("feature"),
            "distance": None,
            "text": chunk.get("text", ""),
        }
        for chunk in corpus
        if feature is None or chunk.get("metadata", {}).get("feature") == feature
    ]
    return keep_relevant(query, rows, k)


def refresh_corpus(caller: str = "student") -> dict[str, Any]:
    global _last_corpus_chunks
    start = time.time()
    try:
        chunks = build_corpus()
        _last_corpus_chunks = chunks
        write_corpus(chunks)
        vector_store_status = "ready"
        vector_store_error = None

        try:
            reset_collection()
            collection = get_collection()

            if chunks:
                ids = [c["chunk_id"] for c in chunks]
                docs = [c["text"] for c in chunks]
                metas = [
                    {
                        "source_id": c["source_id"],
                        "authority_tier": c["authority_tier"],
                        "feature": c["metadata"]["feature"],
                        "indexed_at": c["indexed_at"],
                    }
                    for c in chunks
                ]
                embeddings = embed_texts(docs)
                collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
        except Exception as exc:
            vector_store_status = "degraded"
            vector_store_error = str(exc)

        output = {
            "status": "success",
            "caller": caller,
            "chunk_count": len(chunks),
            "unavailable_sources": dict(_unavailable_sources),  # CHANGED FROM LAB 8
            "collection": COLLECTION_NAME,
            "corpus_path": str(CORPUS_PATH),
            "vector_store_status": vector_store_status,
        }
        if vector_store_error:
            output["vector_store_error"] = vector_store_error
        append_audit("refresh_corpus", {"caller": caller}, output, "pass", "corpus_refreshed", start)
        return output
    except Exception as exc:
        output = {"status": "error", "error": str(exc)}
        append_audit("refresh_corpus", {"caller": caller}, output, "fail", "error", start)
        return output


def retrieve_context(
    query: str, k: int = 5, caller: str = "student", feature: str | None = None
) -> dict[str, Any]:
    # CHANGED FROM LAB 8: optional `feature` limits the search to one
    # feature's records (cards, accounts, users, transactions).
    start = time.time()
    try:
        retrieval_mode = "vector"
        ranked = []

        try:
            collection = get_collection()
            if collection.count() == 0:
                refreshed = refresh_corpus(caller="auto_refresh")
                if refreshed.get("status") != "success":
                    raise RuntimeError("empty_collection")
                # CHANGED FROM LAB 8: refresh_corpus() deletes and recreates
                # the collection, so the old reference is stale. Fetch it again.
                collection = get_collection()
                if collection.count() == 0:
                    raise RuntimeError("empty_collection")

            query_embedding = embed_texts([query])
            # CHANGED FROM LAB 8: ask Chroma for every chunk, then keep only
            # the relevant ones. The corpus is small, so this is cheap.
            query_args = {"query_embeddings": query_embedding, "n_results": collection.count()}
            if feature:
                query_args["where"] = {"feature": feature}
            results = collection.query(**query_args)

            ids = (results.get("ids") or [[]])[0]
            docs = (results.get("documents") or [[]])[0]
            metas = (results.get("metadatas") or [[]])[0]
            distances = (results.get("distances") or [[]])[0]

            rows = []
            for i, chunk_id in enumerate(ids):
                row_meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
                rows.append(
                    {
                        "chunk_id": chunk_id,
                        "source_id": row_meta.get("source_id"),
                        "authority_tier": row_meta.get("authority_tier"),
                        "feature": row_meta.get("feature"),
                        "distance": distances[i] if i < len(distances) else None,
                        "text": docs[i] if i < len(docs) else "",
                    }
                )
            ranked = keep_relevant(query, rows, k)
        except Exception:
            retrieval_mode = "lexical_fallback"
            if not _last_corpus_chunks and not CORPUS_PATH.exists():
                refreshed = refresh_corpus(caller="auto_refresh")
                if refreshed.get("status") != "success":
                    return {"status": "error", "error": "corpus_unavailable"}
            ranked = lexical_fallback_retrieve(query, k, feature)

        output = {
            "status": "success",
            "query": query,
            "caller": caller,
            "feature": feature,
            "k": k,
            "retrieval_mode": retrieval_mode,
            "results": ranked,
        }

        append_audit(
            "retrieve_context",
            {"query": query, "k": k, "caller": caller, "feature": feature},
            {"result_count": len(ranked), "chunk_ids": [r["chunk_id"] for r in ranked]},
            "pass",
            "context_retrieved",
            start,
        )
        return output
    except Exception as exc:
        output = {"status": "error", "error": str(exc), "query": query}
        append_audit(
            "retrieve_context",
            {"query": query, "k": k, "caller": caller},
            output,
            "fail",
            "error",
            start,
        )
        return output


def confidence_from_results(results: list[dict[str, Any]]) -> str:
    # Same rules as Lab 8. CHANGED FROM LAB 8: no results -> "Insufficient"
    # (Lab 8 said "Unknown"). Because keep_relevant() already removed
    # unrelated chunks, these rules now only count relevant evidence.
    if not results:
        return "Insufficient"
    tier_1 = sum(1 for r in results if r.get("authority_tier") == "tier_1")
    tier_2 = sum(1 for r in results if r.get("authority_tier") == "tier_2")
    if tier_1 >= 2 and len(results) >= 3:
        return "High"
    if tier_1 >= 1 or tier_2 >= 2:
        return "Medium"
    return "Low"


def deterministic_answer(query: str, results: list[dict[str, Any]]) -> str | None:
    # Same idea as Lab 8: answer simple questions in Python, not with the LLM.
    # CHANGED FROM LAB 8: "how many X" is answered from the "<feature>_count"
    # chunk, so the model never has to count.
    q = (query or "").lower()
    if "how many" not in q and "count" not in q and "number of" not in q:
        return None
    for r in results:
        if str(r.get("chunk_id", "")).endswith("_count"):
            return f"Answer:\n{r.get('text')}"
    return None


# CHANGED FROM LAB 8: small models (qwen2.5:0.5b) echoed the old prompt's
# <answer>/<summary> placeholders back verbatim instead of filling them in.
# This strips leftover template artifacts and the "Answer:" label so the
# field holds just the answer text.
def clean_ollama_response(text: str) -> str:
    text = (text or "").strip()
    for tag in ("<answer>", "</answer>", "<summary>", "</summary>"):
        text = text.replace(tag, "")
    text = text.strip()
    if text.lower().startswith("answer:"):
        text = text[len("answer:"):].strip()
    return text


def generate_with_ollama(query: str, context: str) -> str:
    prompt = f"""You are a retrieval-grounded assistant for a digital banking system.
Answer the question using only the facts in CONTEXT. Do not guess.

CONTEXT:
{context}

QUESTION:
{query}

Reply with one short answer starting with "Answer:". If CONTEXT does not
contain the facts needed to answer, reply exactly: Answer: Insufficient evidence.
"""

    try:
        resp = requests.post(
            OLLAMA_GENERATE_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "Insufficient evidence.")
        return clean_ollama_response(raw) or "Insufficient evidence."
    except Exception as exc:
        return f"Ollama unavailable: {exc}"


def answer_question(
    query: str, k: int = 5, caller: str = "student", feature: str | None = None
) -> dict[str, Any]:
    start = time.time()
    retrieval = retrieve_context(query=query, k=k, caller=caller, feature=feature)
    if retrieval.get("status") != "success":
        output = {"status": "error", "query": query, "error": retrieval.get("error", "retrieval_failed")}
        append_audit(
            "answer_question",
            {"query": query, "k": k, "caller": caller},
            output,
            "fail",
            "retrieval_failed",
            start,
        )
        return output

    results = retrieval.get("results", [])
    confidence = confidence_from_results(results)

    # CHANGED FROM LAB 8: when nothing relevant was retrieved, return the
    # insufficient-context answer directly instead of asking the LLM.
    if confidence == "Insufficient":
        answer = INSUFFICIENT_ANSWER
    else:
        context = "\n\n".join(r.get("text", "") for r in results)
        answer = deterministic_answer(query, results)
        if answer is None:
            answer = generate_with_ollama(query, context)
            # CHANGED FROM LAB 8: confidence was computed from retrieval alone,
            # so a model reply of "Insufficient evidence" could still be
            # labelled High. The answer contract says an unsupported answer is
            # reported as insufficient, and a failed generation as Unknown.
            if answer.startswith("Ollama unavailable"):
                confidence = "Unknown"
            elif "insufficient evidence" in answer.lower():
                confidence = "Insufficient"
                answer = INSUFFICIENT_ANSWER

    citations = [
        {
            "chunk_id": r.get("chunk_id"),
            "source_id": r.get("source_id"),
            "authority_tier": r.get("authority_tier"),
        }
        for r in results
    ]

    output = {
        "status": "success",
        "query": query,
        "answer": answer,
        "citations": citations,
        "confidence_category": confidence,
        "retrieval_summary": {
            "k": k,
            "feature": feature,
            "retrieved_count": len(results),
            "top_chunk": results[0].get("chunk_id") if results else None,
        },
    }

    append_audit(
        "answer_question",
        {"query": query, "k": k, "caller": caller, "feature": feature},
        {"confidence_category": confidence, "citation_count": len(citations)},
        "pass",
        "answer_generated",
        start,
    )
    return output


if __name__ == "__main__":
    print(json.dumps(refresh_corpus(), indent=2))
    print(json.dumps(retrieve_context("failed transactions", 5), indent=2))
    print(json.dumps(answer_question("How many transactions are there?", 5), indent=2))
    print(json.dumps(answer_question("What is the weather in Sydney today?", 5), indent=2))