import fnmatch
import logging
from typing import List, Tuple
from pathlib import Path, PurePosixPath


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gitignore parsing
# ---------------------------------------------------------------------------

def load_gitignore_patterns(project_root: Path, gitignore_path: str) -> List[str]:
    """Parse a gitignore-style file and return its active patterns.

    Comment lines (starting with '#') and blank lines are stripped.
    Negation patterns (starting with '!') are returned as-is so that
    callers can handle them if they choose to; this module does not
    implement negation in matching.

    Args:
        project_root: Absolute path to the project root directory.
        gitignore_path: Path to the gitignore-style file relative to
                        project_root.

    Returns:
        A list of raw pattern strings ready for glob matching.

    Raises:
        FileNotFoundError: If the resolved file does not exist.
        PermissionError: If the file cannot be read.
        UnicodeDecodeError: If the file is not valid UTF-8.
    """
    path = project_root / gitignore_path

    if not path.exists():
        raise FileNotFoundError(
            f"Exclusion file '{gitignore_path}' not found in project root {project_root}."
        )

    patterns: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)

    logger.debug(
        "Loaded %d pattern(s) from '%s'.", len(patterns), gitignore_path
    )
    return patterns


# ---------------------------------------------------------------------------
# Filter set builder
# ---------------------------------------------------------------------------

def build_filter_set(
    project_root: Path,
    include: List[str] | None = None,
    exclude: List[str] | None = None,
    exclude_from: str | None = None,
) -> Tuple[List[str] | None, List[str], List[str]]:
    """Consolidate include, exclude, and exclude_from into ready-to-use filter lists.

    The exclude_from file patterns are merged into the exclude list.
    If the file is missing a warning string is returned instead of raising
    so the tree tool can surface it to the caller without aborting.

    Args:
        project_root: Absolute path to the project root.
        include: Explicit include glob patterns, or None to include everything.
        exclude: Explicit exclude glob patterns, or None.
        exclude_from: Relative path to a gitignore-style file, or None to skip.

    Returns:
        A three-tuple (include_patterns, exclude_patterns, warnings) where:
        - include_patterns is the final include list (None means include all).
        - exclude_patterns is the merged exclude list (may be empty).
        - warnings is a list of non-fatal warning strings (may be empty).
    """
    warnings: List[str] = []
    merged_exclude: List[str] = list(exclude) if exclude else []

    if exclude_from is not None:
        try:
            gitignore_patterns = load_gitignore_patterns(project_root, exclude_from)
            merged_exclude.extend(gitignore_patterns)
        except FileNotFoundError:
            warnings.append(
                f"Exclusion file '{exclude_from}' was not found in the project root. "
                f"No gitignore-style patterns were applied. "
                f"Consider using the 'exclude' parameter directly."
            )
        except PermissionError:
            warnings.append(
                f"Exclusion file '{exclude_from}' could not be read (permission denied). "
                f"No gitignore-style patterns were applied."
            )
        except UnicodeDecodeError:
            warnings.append(
                f"Exclusion file '{exclude_from}' contains invalid UTF-8 and could not be parsed. "
                f"No gitignore-style patterns were applied."
            )

    return include, merged_exclude, warnings


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

def _normalise(rel_path: str | Path) -> str:
    """Return a POSIX-style relative path string with no leading slash.

    Args:
        rel_path: A relative path in any form.

    Returns:
        A forward-slash string such as 'src/app/main.py'.
    """
    return str(PurePosixPath(Path(rel_path)))


def matches_any(rel_path: str | Path, patterns: List[str]) -> bool:
    """Return True if rel_path matches at least one glob pattern.

    Each pattern is tested in two ways:
    - Against the full relative path  (e.g. 'src/app/main.py')
    - Against the bare filename only  (e.g. 'main.py')

    This ensures that simple name patterns ('*.py', '__pycache__') work
    as expected alongside path patterns ('src/**', 'dist/', 'a/b/*.js').

    Trailing slashes on patterns are stripped before matching so that
    directory-only gitignore patterns (e.g. 'dist/') match correctly
    regardless of whether a slash is present.

    Args:
        rel_path: Path relative to the project root, in any OS format.
        patterns: Glob patterns to test against.

    Returns:
        True if at least one pattern matches, False otherwise.
    """
    normalised = _normalise(rel_path)
    name = Path(rel_path).name

    for raw_pattern in patterns:
        pattern = raw_pattern.rstrip("/")
        if fnmatch.fnmatch(normalised, pattern):
            return True
        if fnmatch.fnmatch(name, pattern):
            return True

    return False


def is_file_included(
    rel_path: str | Path,
    include_patterns: List[str] | None,
    exclude_patterns: List[str],
) -> bool:
    """Decide whether a file entry should appear in the tree.

    A file is included when it is not excluded AND matches the include
    whitelist (if one is set). Both filters operate on the relative path.

    Args:
        rel_path: File path relative to the project root.
        include_patterns: Whitelist patterns, or None to allow everything.
        exclude_patterns: Blacklist patterns; checked first.

    Returns:
        True if the file should be included, False otherwise.
    """
    if exclude_patterns and matches_any(rel_path, exclude_patterns):
        return False
    if include_patterns is not None and not matches_any(rel_path, include_patterns):
        return False
    return True


def is_dir_traversable(
    rel_path: str | Path,
    include_patterns: List[str] | None,
    exclude_patterns: List[str],
) -> bool:
    """Decide whether a directory should be traversed.

    A directory is always traversed unless it is explicitly excluded.
    Include patterns are intentionally NOT applied to directories: a
    directory that does not itself match '**/*.py' must still be entered
    to discover the .py files it contains.

    Args:
        rel_path: Directory path relative to the project root.
        include_patterns: Whitelist patterns (ignored for directories).
        exclude_patterns: Blacklist patterns; a match stops traversal.

    Returns:
        True if the directory should be entered, False if it should be skipped.
    """
    if exclude_patterns and matches_any(rel_path, exclude_patterns):
        return False
    return True