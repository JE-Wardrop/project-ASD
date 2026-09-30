"""MCP validation collector for the shared agentic loop.

Unlike the lab's collector (one fixed set of tools for one app), the MCP
server here is shared across 5 features, and not every feature has tools
registered yet — so this checks only the tools belonging to whichever
Target is currently under review.
"""

import importlib.util
from pathlib import Path


def _load_tools_module(mcp_server_dir: Path):
    spec = importlib.util.spec_from_file_location("mcp_tools_check", mcp_server_dir / "tools.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_tools_for_target(target, tools_module) -> dict | None:
    """Call each MCP tool's real function directly, by name, for this target.

    Returns {tool name on server: return value}, or None if this target has
    no MCP tools registered yet.
    """
    # student 1
    if target.key == "student-1":
        return {
            "card_count": tools_module.card_count(),
            "cards_by_user": tools_module.cards_per_user(1),
        }
    # studeny 5
    if target.key == "student-5":
        return {
            "transactions_list": tools_module.list_transactions(limit=5),
            "transaction_detail": tools_module.get_transaction(1),
            "account_activity_summary": tools_module.summarize_account_activity(1),
        }

    
    return None


def collect(target, repo_root: Path) -> tuple[bool, str]:
    mcp_server_dir = repo_root / "ai-services" / "mcp-server"
    mcp_mode_route = target.root / "backend" / "routes" / "mcp_mode.py"

    required_paths = [
        mcp_server_dir / "tools.py",
        mcp_server_dir / "server.py",
        mcp_server_dir / "requirements.txt",
        mcp_mode_route,
        repo_root / "ai-services" / "prompts" / "mcp" / "implementation" / "tool_selection_prompt.txt",
        repo_root / "ai-services" / "prompts" / "mcp" / "review" / "integration_review_prompt.txt",
    ]

    missing = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing:
        return False, "MCP evidence incomplete. Missing: " + ", ".join(missing)

    # Run each tool's real function directly (same "Terminal B" pattern as
    # the lab), then check the RETURN VALUE. Our tools.py never raises on a
    # failed HTTP call — it always returns {"error": ...} instead — so
    # catching only exceptions here would silently pass even when the
    # underlying database API is unreachable.
    try:
        tools_module = _load_tools_module(mcp_server_dir)
        results = _run_tools_for_target(target, tools_module)
    except Exception as exc:
        return False, f"MCP tool execution failed: {exc}"

    if results is None:
        return False, f"No MCP tools registered yet for {target.label} ({target.key})"

    for tool_name, result in results.items():
        if "error" in result:
            return False, f"Tool '{tool_name}' returned an error: {result['error']}"

    return True, (
        f"MCP evidence for {target.label}: mcp-server/ contains tools.py and server.py; "
        f"server defines {len(results)} tool(s) ({', '.join(results)}); "
        "all tools executed successfully against their database API; "
        f"{mcp_mode_route.relative_to(repo_root)} and MCP prompts exist."
    )
