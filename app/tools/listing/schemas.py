from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class ListProjectsRequest(BaseModel):
    """Input schema for the list_projects tool.

    Attributes:
        include_paths: When True, the response will include the filesystem
                       path registered for each project in addition to the
                       project identifiers. Defaults to False.
    """

    include_paths: bool = Field(
        default=False,
        description="Include the registered filesystem path for each project.",
    )


class ListProjectsResponse(BaseModel):
    """Output schema for the list_projects tool.

    Attributes:
        project_ids: Ordered list of every registered project identifier.
        total: Total number of registered projects.
        paths: Mapping of project_id to its registered path string.
               Only populated when include_paths was set to True in the request.
    """

    project_ids: List[str] = Field(
        description="List of all registered project identifiers."
    )
    total: int = Field(
        description="Total number of registered projects."
    )
    paths: Optional[Dict[str, str]] = Field(
        default=None,
        description="Registered path for each project. None when include_paths is False.",
    )