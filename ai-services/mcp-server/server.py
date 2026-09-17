from mcp.server.fastmcp import FastMCP, Context
from flask import Flask, jsonify, request


from tools import (
    get_card_count,
    get_card_per_user,
    list_project_files,
    read_ci_report
)


mcp = FastMCP("Bank Account System MCP")

AVAILABLE_TOOLS = [
    "db_tools",
    "repo_tools",
    "project_files",
    "ci_report",

    # for each database
    "get_card_per_user",
    "card_count",
]



# @mcp.tool()
# def health(){
#     return jsonify({'status': 'mcp healthy'}), 200
# }


@mcp.tool()
def project_files(
    directory_path: str = ".."
):
    return list_project_files(directory_path)


@mcp.tool()
def ci_report(
    report_path: str = "../reports/report.json"
):
    return read_ci_report(report_path)




# For each database

@mcp.tool()
def card_count():
    return get_card_count()



    # will update this later to make it work properly
@mcp.tool()
def card_per_user():
    return get_card_per_user()


# @mcp.tool()
# def card_per_user(card : int, user_id: int):
#     return get_card_per_user(user_id)



# Do I need to define a port for MCP to run on here?

if __name__ == "__main__":

    print("Starting Bacnk Account System MCP Server...")
    print("Server status: RUNNING")
    print("Interact with MCP tools from a second terminal.")
    print("Available tools:")
    for tool in AVAILABLE_TOOLS:
        print(f"- {tool}")


    # edited mcp.run() to make sure it runs on port 5500
    # mcp.run()
    mcp.run(transport="sse", port=5500)