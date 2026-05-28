from mcp.server.fastmcp import FastMCP

_mcp = FastMCP("ProjectNavigator")

def get_mcp():
    """Get the FastMCP instance."""
    return _mcp

def configure(host: str, port: int) -> None:
    """Override host and port on the shared instance before running.

    Args:
        host: Host to bind when running in SSE mode.
        port: Port to bind when running in SSE mode.
    """
    _mcp.settings.host = host
    _mcp.settings.port = port