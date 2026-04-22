from pathlib import Path
from typing import Optional, Dict

from .config import StorageConfig


class ProjectStorage:
    """High-level interface for resolving registered project paths.

    Projects are identified by a short string key (project_id) that maps
    to an absolute filesystem path stored in the configuration managed by
    StorageConfig.

    Attributes:
        config (StorageConfig): Underlying configuration manager.
    """

    def __init__(self, base_path: Optional[Path] = None) -> None:
        """Initialise project storage with an optional custom config directory.

        Args:
            base_path: Override the default configuration directory.
                       Forwarded as-is to StorageConfig.
        """
        self.config = StorageConfig(base_path)

    
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_projects(self) -> Dict[str, str]:
        """Return all registered project identifiers and their paths.

        Returns:
            A dictionary mapping each project_id to its path string,
            exactly as stored in the configuration file.
        """
        return self.config.load_paths()
    

    def resolve_project_path(self, project_id: str) -> Path:
        """Resolve a project identifier to a validated filesystem path.

        Args:
            project_id: Unique identifier for the project.

        Returns:
            The resolved and validated Path for the project root.

        Raises:
            ValueError: If project_id is not registered in the configuration.
            FileNotFoundError: If the registered path does not exist on disk.
        """
        paths = self.config.load_paths()
        path_str = paths.get(project_id)

        if path_str is None:
            available = list(paths.keys())
            if available:
                hint = "\n  - ".join(available)
                raise ValueError(
                    f"Project '{project_id}' is not registered.\n"
                    f"Available projects:\n  - {hint}"
                )
            raise ValueError(
                f"Project '{project_id}' is not registered and no projects "
                f"are currently configured. "
                f"Add entries to {self.config.paths_file}."
            )

        resolved = Path(path_str).expanduser().resolve()

        if not resolved.exists():
            raise FileNotFoundError(
                f"Path '{resolved}' registered for project '{project_id}' "
                f"does not exist. "
                f"Update the entry in {self.config.paths_file}."
            )

        return resolved