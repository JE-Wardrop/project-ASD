"""RAG tools exposed over MCP (stdio) — same as Lab 8.

This is NOT what the feature backends call; they use rag_http_server.py on
port 5003. This file lets an MCP client (for example Claude Desktop, via
mcp-config.json) use the same RAG pipeline as MCP tools.

Every place that differs from Lab 8 is marked with  # CHANGED FROM LAB 8
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from rag_pipeline import answer_question as answer_question_impl
from rag_pipeline import refresh_corpus as refresh_corpus_impl
from rag_pipeline import retrieve_context as retrieve_context_impl

mcp = FastMCP("Bank Management RAG MCP")
AVAILABLE_TOOLS = ["refresh_corpus", "retrieve_context", "answer_question"]


# CHANGED FROM LAB 8: every tool declares "-> dict[str, Any]" so FastMCP
# returns structuredContent (clean JSON) instead of one escaped text string.

@mcp.tool()
def refresh_corpus(caller: str = "student") -> dict[str, Any]:
    return refresh_corpus_impl(caller=caller)


# CHANGED FROM LAB 8: optional "feature" (cards, accounts, users,
# transactions) limits the search to one feature, same as the HTTP server.

@mcp.tool()
def retrieve_context(
    query: str, k: int = 5, caller: str = "student", feature: str | None = None
) -> dict[str, Any]:
    return retrieve_context_impl(query=query, k=k, caller=caller, feature=feature)


@mcp.tool()
def answer_question(
    query: str, k: int = 5, caller: str = "student", feature: str | None = None
) -> dict[str, Any]:
    return answer_question_impl(query=query, k=k, caller=caller, feature=feature)


if __name__ == "__main__":
    print("Starting Bank Management RAG MCP Server...")
    print("Server status: RUNNING")
    print("Interact with RAG tools from a second terminal.")
    print("Available tools:")
    for tool in AVAILABLE_TOOLS:
        print(f"- {tool}")
    mcp.run()