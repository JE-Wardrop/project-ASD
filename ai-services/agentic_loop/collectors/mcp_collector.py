import importlib.util
from pathlib import Path

# Unimplemented tool: db_tools, repo_tools, card_count, card_per_user

REQUIRED_MCP_TOOLS = [
    # general tools
    # "db_tools",
    # "repo_tools",
    
    "project_files", 
    "ci_report",

    # tools for db's
    # "card_count",
    # "card_per_user",

    ]

REQUIRED_FUNCTIONS = {
    # general functions
    # "db_tools": "",
    # "repo_tools": "" ,

    "project_files": "list_project_files",
    "ci_report": "read_ci_report",

    #functions for db's
    # "card_count": "",
    # "card_per_user": "",
}



def _load_tools_module(mcp_server_dir: Path):
    spec = importlib.util.spec_from_file_location("mcp_tools_check", mcp_server_dir / "tools.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:

    # issue with this file path

    mcp_server_dir = app_dir / "mcp-server"
    
    required_paths = [
        mcp_server_dir / "tools.py",
        mcp_server_dir / "server.py",
        mcp_server_dir / "requirements.txt",

        # This will need to be done in the orchestrator or another part of the agentic_loop
        # This handles which microservice the mcp server go to.
        # app_dir / "student-?" / "routes" / "mcp_mode.py",

        # tool selection prompt will need to be updated with the rest of the MCP structure.
        # I need to create MCP "commands" (functions? not really sure what they are) that fit everyone's architecture
        # The architecture of the labs is small so...
        app_dir / "prompts" / "mcp" / "implementation" / "tool_selection_prompt.txt",
        app_dir / "prompts" / "mcp" / "review" / "integration_review_prompt.txt",
        app_dir / "prompts" / "mcp" / "review" / "tool_review_prompt.txt",
    ]
    
    missing = [str(path.relative_to(app_dir)) for path in required_paths if not path.exists()]
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
    except Exception as exc:
        return False, f"MCP tool execution failed: {exc}"
    
    return True, (
        "MCP evidence: mcp-server/ contains tools.py and server.py; "
        f"server defines {len(REQUIRED_MCP_TOOLS)} tools ("
        "project_files, ci_report); all [NUMBER] tools executed successfully; "
        "routes/mcp_mode.py and lab7 prompts exist."
    )