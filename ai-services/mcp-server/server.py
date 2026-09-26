from mcp.server.fastmcp import FastMCP, Context
from flask import Flask, jsonify, request
from typing import Any
from tools import (
    card_count,
    cards_per_user,
    # list_project_files,
    # read_ci_report,
    # Transaction Management (student-5)
    list_transactions,
    get_transaction,
    summarize_account_activity,
)

#  Gia made change  here
mcp = FastMCP(
    "Bank Account System MCP",
    host="0.0.0.0",
    port=5500,)

AVAILABLE_TOOLS = [
    "project_files",
    "ci_report",

    # Card Management (student-1)
    "card_per_user",
    "card_count",
    
    # Transaction Management (student-5)
    "list_transactions",
    "get_transaction",
    "summarize_account_activity",
]



# @mcp.tool()
# def health(){
#     return jsonify({'status': 'mcp healthy'}), 200
# }

# @mcp.tool()
# def project_files(
#     directory_path: str = ".."
# ):
#     return list_project_files(directory_path)


# @mcp.tool()
# def ci_report(
#     report_path: str = "../reports/report.json"
# ):
#     return read_ci_report(report_path)





# Card Management (student-1)
@mcp.tool()
def card_count() -> dict[str, Any]:
    return card_count()


@mcp.tool()
def card_per_user(user_id: int) -> dict[str, Any]:
   return card_per_user(user_id)


# Transaction Management (student-5)
@mcp.tool()
def transactions_list(
     account_id: int | None = None,
     transaction_type: str | None = None,
     status: str | None = None,
     limit: int = 20,) -> dict[str, Any]:
    return list_transactions(account_id, transaction_type, status, limit)


@mcp.tool()
def transaction_detail(transaction_id: int) -> dict[str, Any]:
    return get_transaction(transaction_id)


@mcp.tool()
def account_activity_summary(account_id: int)-> dict[str, Any]:
    return summarize_account_activity(account_id)


if __name__ == "__main__":

    print("Starting Bacnk Account System MCP Server...")
    print("Server status: RUNNING")
    print("Interact with MCP tools from a second terminal.")
    print("Available tools:")
    for tool in AVAILABLE_TOOLS:
        print(f"- {tool}")

    # Gia made change here
    mcp.run(transport="streamable-http")

    # I will make it so that MCP runs on port 5500
    # mcp.run(transport="sse", port=5500)