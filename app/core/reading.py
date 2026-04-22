from typing import List
from pathlib import Path


def read_file(project_dir: Path, relative_path: str | Path) -> List[str]:
    """Read a project file and return its content as a list of lines.

    Lines are returned with their newline characters stripped so that
    callers can format or number them however they need.

    Args:
        project_dir: Absolute path to the project root directory.
        relative_path: Path to the target file relative to project_dir.

    Returns:
        A list of strings, one entry per line in the file.

    Raises:
        FileNotFoundError: If the resolved path does not exist.
        IsADirectoryError: If the resolved path points to a directory.
        PermissionError: If the file cannot be read due to OS permissions.
        UnicodeDecodeError: If the file is not valid UTF-8.
    """
    path = Path(project_dir) / relative_path

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.is_dir():
        raise IsADirectoryError(f"Path is a directory, not a file: {path}")

    return path.read_text(encoding="utf-8").splitlines()