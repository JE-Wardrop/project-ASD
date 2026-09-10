from mcp.server.fastmcp import FastMCP

from tools import (
    get_card_count,
    list_project_files,
    read_ci_report
)


mcp = FastMCP("Student Enrolment MCP")

AVAILABLE_TOOLS = [
    "card_count",
    "project_files",
    "ci_report",
]


@mcp.tool()
def card_count():
    return get_card_count()


# @mcp.tool()
# def students_by_subject(
#     subject_code: str
# ):
#     return get_students_by_subject(subject_code)


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


if __name__ == "__main__":
    print("Starting Student Enrolment MCP Server...")
    print("Server status: RUNNING")
    print("Interact with MCP tools from a second terminal.")
    print("Available tools:")
    for tool in AVAILABLE_TOOLS:
        print(f"- {tool}")
    mcp.run()