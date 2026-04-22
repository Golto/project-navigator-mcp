from app.mcp import get_mcp
from app.storage import get_project_storage

from .schemas import GetTreeRequest, GetTreeResponse
from .builder import build_tree

mcp = get_mcp()
project_storage = get_project_storage()


@mcp.tool()
def get_project_tree(request: GetTreeRequest) -> GetTreeResponse:
    """Build and return the directory tree of a registered project.

    Explores the project filesystem according to the filtering rules
    specified in the request (depth limit, hidden files, include/exclude
    glob patterns, and an optional gitignore-style exclusion file).

    The response contains either a nested JSON tree or a compact
    branch-style string depending on the as_string flag, along with
    aggregated statistics and any non-fatal warnings raised during
    traversal (e.g. a missing .gitignore).

    Args:
        request: Filtering and formatting parameters for the tree.

    Returns:
        A GetTreeResponse with the tree, stats, and warnings.

    Raises:
        ValueError: If the project_id is not registered.
        FileNotFoundError: If the registered project path does not exist.
    """
    project_root = project_storage.resolve_project_path(request.project_id)
    return build_tree(project_root, request)