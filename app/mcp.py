from mcp.server.fastmcp import FastMCP

_mcp = FastMCP("ProjectNavigator")

def get_mcp():
    """Get the FastMCP instance."""
    return _mcp