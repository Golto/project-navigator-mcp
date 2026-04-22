from typing import Dict
from app.mcp import get_mcp
from app.storage import get_project_storage

from .schemas import ListProjectsRequest, ListProjectsResponse

mcp = get_mcp()
project_storage = get_project_storage()


@mcp.tool()
def list_projects(request: ListProjectsRequest) -> ListProjectsResponse:
    """List all registered projects, with optional path details.

    Returns every project identifier known to the navigator along with
    basic statistics. Pass include_paths=True to also receive the
    filesystem path registered for each project.
    """
    paths: Dict[str, str] = project_storage.list_projects()

    return ListProjectsResponse(
        project_ids=list(paths.keys()),
        total=len(paths),
        paths=paths if request.include_paths else None,
    )