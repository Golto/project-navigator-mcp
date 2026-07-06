import os
from pathlib import Path
from typing import Optional

from .project import ProjectStorage

ENV_PATHS_DIR = "MCP_PROJECT_PATHS_DIR"

_project_storage: Optional[ProjectStorage] = None


def configure_storage(base_path: Optional[Path] = None) -> None:
    """Explicitly (re)configure the global ProjectStorage singleton.

    Must be called before the first get_project_storage() call made by any
    tool module -- i.e. before `import app.tools` in main.py -- otherwise
    it has no effect on tools that already grabbed a reference.

    Args:
        base_path: Directory containing (or that will contain) paths.json.
                   Forwarded as-is to ProjectStorage. None uses the
                   platform-default directory.
    """
    global _project_storage
    _project_storage = ProjectStorage(base_path)


def get_project_storage() -> ProjectStorage:
    """Get the Project Storage instance.

    Lazily configured on first access if configure_storage() was not
    called explicitly beforehand. In that fallback case, the
    MCP_PROJECT_PATHS_DIR environment variable is honoured,
    falling back to the platform-default config directory.
    """
    global _project_storage
    if _project_storage is None:
        env_value = os.environ.get(ENV_PATHS_DIR)
        configure_storage(Path(env_value) if env_value else None)
    return _project_storage
