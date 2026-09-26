"""MCP validation collector for the shared agentic loop.

Unlike the lab's collector (one fixed set of tools for one app), the MCP
server here is shared across 5 features, and not every feature has tools
registered yet — so this checks only the tools belonging to whichever
Target is currently under review.
"""

import importlib.util
from pathlib import Path

# target.key -> {tool name registered on the shared MCP server: (tools.py
# function name, sample positional args, sample keyword args)}
TARGET_MCP_TOOLS = {
    "student-1": {
        "card_count": ("get_card_count", (), {}),
        "cards_by_user": ("get_cards_by_user", (1,), {}),
    },
    "student-5": {
        "transactions_list": ("list_transactions", (), {"limit": 5}),
        "transaction_detail": ("get_transaction", (1,), {}),
        "account_activity_summary": ("summarize_account_activity", (1,), {}),
    },
}


def _load_tools_module(mcp_server_dir: Path):
    spec = importlib.util.spec_from_file_location("mcp_tools_check", mcp_server_dir / "tools.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect(target, repo_root: Path) -> tuple[bool, str]:
    mcp_server_dir = repo_root / "ai-services" / "mcp-server"
    mcp_mode_route = target.root / "backend" / "routes" / "mcp_mode.py"

    required_tools = TARGET_MCP_TOOLS.get(target.key)
    if not required_tools:
        return False, f"No MCP tools registered yet for {target.label} ({target.key})"

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

    server_text = (mcp_server_dir / "server.py").read_text(encoding="utf-8")
    tools_text = (mcp_server_dir / "tools.py").read_text(encoding="utf-8")

    missing_tools = [name for name in required_tools if name not in server_text]
    if missing_tools:
        return False, "MCP server missing required tools: " + ", ".join(missing_tools)

    missing_functions = [
        func_name for func_name, _, _ in required_tools.values() if f"def {func_name}" not in tools_text
    ]
    if missing_functions:
        return False, "tools.py missing required function implementations: " + ", ".join(missing_functions)

    # Run each tool's real function directly (same "Terminal B" pattern as
    # the lab), then check the RETURN VALUE. Our tools.py never raises on a
    # failed HTTP call — it always returns {"error": ...} instead — so
    # catching only exceptions here would silently pass even when the
    # underlying database API is unreachable.
    try:
        tools_module = _load_tools_module(mcp_server_dir)
        for tool_name, (func_name, args, kwargs) in required_tools.items():
            func = getattr(tools_module, func_name)
            result = func(*args, **kwargs)
            if isinstance(result, dict) and "error" in result:
                return False, f"Tool '{tool_name}' ({func_name}) returned an error: {result['error']}"
    except Exception as exc:
        return False, f"MCP tool execution failed: {exc}"

    return True, (
        f"MCP evidence for {target.label}: mcp-server/ contains tools.py and server.py; "
        f"server defines {len(required_tools)} tool(s) ({', '.join(required_tools)}); "
        "all tools executed successfully against their database API; "
        f"{mcp_mode_route.relative_to(repo_root)} and MCP prompts exist."
    )