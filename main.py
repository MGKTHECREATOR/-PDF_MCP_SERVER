"""
main.py
MCP server entrypoint for the PDF report generator.
Stage 1: connectivity check only — no PDF/LLM logic wired in yet.
"""

from mcp.server.fastmcp import FastMCP

# Initialize the MCP server with a name — this is what shows up
# when a host (VS Code, an orchestrator, MCP Inspector) lists servers.
mcp = FastMCP("pdf-report-server")


@mcp.tool()
def ping() -> str:
    """
    Simple connectivity check. Call this to confirm the server
    is running and reachable before testing real tools.
    """
    return "pong"


@mcp.tool()
def health_check() -> dict:
    """
    Returns basic server status info. Useful once you start wiring
    in dependencies (Azure Blob, LLM client) — you can extend this
    to report whether those are configured/reachable.
    """
    return {
        "status": "ok",
        "server": "pdf-report-server",
        "stage": "connectivity-check"
    }


if __name__ == "__main__":
    mcp.run()