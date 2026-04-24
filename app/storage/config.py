import json
import logging
import sys
from pathlib import Path
from typing import Optional, Dict


logger = logging.getLogger(__name__)


def _default_config_folder() -> Path:
    """Return the platform-appropriate configuration directory.

    On Windows, configuration is stored under %APPDATA%\\mcp-project-navigator.
    On all other platforms, the XDG-style ~/.config/scripts/mcp-project-navigator
    is used.

    Returns:
        An absolute Path to the configuration directory.
    """
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming"
        return base / "mcp-project-navigator"
    return Path.home() / ".config" / "scripts" / "mcp-project"


class StorageConfig:
    """Manages the on-disk configuration layout for the MCP project navigator.

    The configuration is stored under a single base directory and currently
    consists of one JSON file that maps project identifiers to their
    filesystem paths.

    The default directory is platform-dependent:
        Linux / macOS: `~/.config/scripts/mcp-project-navigator/`
        Windows: `%APPDATA%\\mcp-project\\`

    Attributes:
        base_path (Path): Root directory of the configuration.
        paths_file (Path): Path to the JSON file that stores project paths.
    """

    def __init__(self, base_path: Optional[Path] = None) -> None:
        """Initialise the configuration, creating missing directories and files.

        Args:
            base_path: Override the default configuration directory.
                       When None, the platform-appropriate default is used.
        """
        self.base_path = Path(base_path) if base_path is not None else _default_config_folder()
        self.paths_file = self.base_path / "paths.json"
        self._ensure_structure()


    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_structure(self) -> None:
        """Create the configuration directory and seed missing files."""
        self.base_path.mkdir(parents=True, exist_ok=True)

        if not self.paths_file.exists():
            self.paths_file.write_text("{}", encoding="utf-8")
            logger.debug("Created empty paths file at %s", self.paths_file)


    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_paths(self) -> Dict[str, str]:
        """Load the project-id-to-path mapping from disk.

        Returns:
            A dictionary mapping each project identifier to its absolute
            path string. Returns an empty dict if the file is missing or
            malformed.
        """
        if not self.paths_file.exists():
            return {}

        try:
            with self.paths_file.open(encoding="utf-8") as fh:
                data = json.load(fh)

            if not isinstance(data, dict):
                logger.warning(
                    "Paths file %s does not contain a JSON object; ignoring.",
                    self.paths_file,
                )
                return {}

            return data

        except json.JSONDecodeError as exc:
            logger.error(
                "Paths file %s is malformed and could not be parsed: %s",
                self.paths_file,
                exc,
            )
            return {}
        except OSError as exc:
            logger.error("Could not read paths file %s: %s", self.paths_file, exc)
            return {}