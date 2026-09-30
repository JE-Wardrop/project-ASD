"""MCP client wrapper for student-2 (Bank Account Management) routes.

Same wrapper student-1 and student-5 use: open a streamable-HTTP session to
the shared MCP server on the host, call one tool, return its structured
result. Never raises, so a route can always render the outcome.
"""

import asyncio
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://host.docker.internal:5500/mcp")


async def _call_tool(name: str, arguments: dict) -> dict:
    async with streamable_http_client(MCP_SERVER_URL) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()  # required handshake before any call_tool()
            result = await session.call_tool(name, arguments)

            if result.isError:
                text = " ".join(c.text for c in result.content if hasattr(c, "text"))
                return {"error": text or "MCP tool call failed"}

            if result.structuredContent is not None:
                return result.structuredContent
            return {"result": [c.text for c in result.content if hasattr(c, "text")]}


def call_mcp_tool(name: str, arguments: dict | None = None) -> dict:
    """Synchronous entry point for Flask routes."""
    try:
        return asyncio.run(_call_tool(name, arguments or {}))
    except BaseException as exc:
        print(f"[mcp_client] calling '{name}' failed: {type(exc).__name__}: {exc}")
        return {"error": f"Could not reach MCP server at {MCP_SERVER_URL}: {exc}"}
