import importlib.util
from pathlib import Path

import sys

# I believe this is working fine in terms of file pathing

REQUIRED_MCP_TOOLS = [
    # general tools    
    "project_files", 
    "ci_report",

    # tools for db's
    "card_count",
    "card_per_user",

    ]

REQUIRED_FUNCTIONS = {
    # general functions
    "project_files": "list_project_files",
    "ci_report": "read_ci_report",

    #functions for db's
    "card_count": "get_card_count",
    "card_per_user": "get_card_per_user",
}



def _load_tools_module(mcp_server_dir: Path):
    spec = importlib.util.spec_from_file_location("mcp_tools_check", mcp_server_dir / "tools.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect(app_dir:Path, repo_root: Path) -> tuple[bool, str]:
    # print("app_dir:", app_dir.resolve())

    # Debug print statements
    # print("repo_root:", repo_root.resolve())
    # print("mcp_server_dir:", (repo_root / "ai-services" / "mcp-server").resolve())


    mcp_server_dir = repo_root / "ai-services" / "mcp-server"


    required_paths = [
        mcp_server_dir / "tools.py",
        mcp_server_dir / "server.py",
        mcp_server_dir / "requirements.txt",


        repo_root / "ai-services" / "prompts" / "mcp" / "implementation" / "tool_selection_prompt.txt",
        repo_root / "ai-services" / "prompts" / "mcp" / "review" / "integration_review_prompt.txt",
        repo_root / "ai-services" / "prompts" / "mcp" / "review" / "tool_review_prompt.txt",

    ]
    
    missing = [str(path.relative_to(repo_root)) for path in required_paths if not path.exists()]
    if missing:
        return False, "MCP evidence incomplete. Missing: " + ", ".join(missing)
    
    tools_text = (mcp_server_dir / "tools.py").read_text(encoding="utf-8")
    server_text = (mcp_server_dir / "server.py").read_text(encoding="utf-8")
    
    missing_tools = [tool for tool in REQUIRED_MCP_TOOLS if tool not in server_text]
    if missing_tools:
        return False, "MCP server missing required tools: " + ", ".join(missing_tools)
    
    missing_functions = [
        func_name for func_name in REQUIRED_FUNCTIONS.values() if f"def {func_name}" not in tools_text
    ]
    if missing_functions:
        return False, "tools.py missing required function implementations: " + ", ".join(missing_functions)
    
    try:
        tools_module = _load_tools_module(mcp_server_dir)
        tools_module.list_project_files("..")
        tools_module.read_ci_report("../reports/report.json")

        # might have to edit these as these are how the mcp picks up on my tools
        tools_module.get_card_count()
        tools_module.get_card_per_user()
    except Exception as exc:
        return False, f"MCP tool execution failed: {exc}"
    
    return True, (

        # this will have to be edited as more tools are added
        "MCP evidence: mcp-server/ contains tools.py and server.py; "
        f"server defines {len(REQUIRED_MCP_TOOLS)} tools ("
        "project_files, ci_report, card_count, card_per_user); all 4 tools executed successfully; "
        "mcp routes exist and so do the prompts folder"
    )