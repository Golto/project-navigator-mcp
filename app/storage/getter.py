from .project import ProjectStorage

_project_storage = ProjectStorage()

def get_project_storage() -> ProjectStorage:
    """Get the Project Storage instance."""
    return _project_storage