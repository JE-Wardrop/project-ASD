from pathlib import Path


REQUIRED_RAG_TOOLS = [
    "refresh_corpus", 
    "retrieve_context", 
    "answer_question"
]

def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    rag_server_dir = repo_root / "rag-server"

    required_paths = [
        rag_server_dir / "rag_pipeline.py",
        rag_server_dir / "rag_server.py",
        rag_server_dir / "requirements.txt",
    ]

    missing = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing:
        return False, "RAG evidence incomplete. Missing: " + ", ".join(missing)

    pipeline_text = (rag_server_dir / "rag_pipeline.py").read_text(encoding="utf-8")

    missing_tools = [tool for tool in REQUIRED_RAG_TOOLS if f"def {tool}" not in pipeline_text]
    if missing_tools:
        return False, "rag_pipeline.py missing required tools: " + ", ".join(missing_tools)

    return True, (
        "RAG evidence: rag-server/ contains rag_pipeline.py and rag_server.py; "
        f"{len(REQUIRED_RAG_TOOLS)} tools defined (refresh_corpus, retrieve_context, answer_question)."
    )