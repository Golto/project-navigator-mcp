import logging
from pathlib import Path, PurePosixPath
from typing import Optional

import pathspec


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gitignore parsing
# ---------------------------------------------------------------------------

def load_gitignore_patterns(project_root: Path, gitignore_path: str) -> list[str]:
    """Parse a gitignore-style file and return its active patterns.

    Comment lines (starting with '#') and blank lines are stripped.
    Negation patterns (starting with '!') are passed through as-is;
    pathspec handles their semantics during matching.

    Args:
        project_root: Absolute path to the project root directory.
        gitignore_path: Path to the gitignore-style file relative to project_root.

    Returns:
        A list of raw pattern strings ready to be compiled by pathspec.

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

    patterns: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)

    logger.debug("Loaded %d pattern(s) from '%s'.", len(patterns), gitignore_path)
    return patterns


# ---------------------------------------------------------------------------
# Filter set builder
# ---------------------------------------------------------------------------

def build_filter_set(
    project_root: Path,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    exclude_from: str | None = None,
) -> tuple[list[str] | None, list[str], list[str]]:
    """Consolidate include, exclude, and exclude_from into ready-to-use filter lists.

    Patterns from exclude_from are merged into the exclude list.
    If the file is missing or unreadable, a warning is appended instead of
    raising, so callers can surface it without aborting the operation.

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
    warnings: list[str] = []
    merged_exclude: list[str] = list(exclude) if exclude else []

    if exclude_from is not None:
        try:
            merged_exclude.extend(load_gitignore_patterns(project_root, exclude_from))
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

def _to_posix_rel(rel_path: str | Path) -> str:
    """Strip the project root prefix and return a clean POSIX-style relative path.

    walker.py builds paths as '<project_root_name>/<rest>', for example
    'my-project/src/main.py'. pathspec expects paths relative to the root
    itself ('src/main.py'), so the leading component must be removed.

    Args:
        rel_path: Path as produced by the walker, in any OS format.

    Returns:
        A forward-slash string with the root prefix removed, such as
        'src/main.py' or 'app/core/filtering.py'.
    """
    posix = str(PurePosixPath(Path(rel_path)))
    # Remove the first path component (project root name)
    if "/" in posix:
        return posix.split("/", 1)[1]
    # Entry is the root itself; return empty string
    return ""


def _build_spec(patterns: list[str]) -> pathspec.PathSpec:
    """Compile a list of patterns into a pathspec.PathSpec object.

    Uses GitWildMatchPattern for full gitignore semantics: leading slash
    anchoring, trailing slash directory markers, ** globbing, and negation.

    Args:
        patterns: Raw pattern strings.

    Returns:
        A compiled PathSpec ready for match_file calls.
    """
    return pathspec.PathSpec.from_lines(
        pathspec.patterns.GitWildMatchPattern, patterns
    )


def matches_any(rel_path: str | Path, patterns: list[str]) -> bool:
    """Return True if rel_path matches at least one pattern.

    Matching uses pathspec with GitWildMatchPattern, which provides full
    gitignore semantics: ** globbing, trailing slash directory markers,
    leading slash anchoring, and negation. The path is normalised to a
    POSIX string relative to the project root before matching.

    Args:
        rel_path: Path relative to the project root, as produced by the
                  walker (includes the root name as the first component).
        patterns: Glob patterns to compile and test against.

    Returns:
        True if the compiled spec matches the normalised path.
    """
    normalised = _to_posix_rel(rel_path)
    return _build_spec(patterns).match_file(normalised)


def is_file_included(
    rel_path: str | Path,
    include_patterns: list[str] | None,
    exclude_patterns: list[str],
) -> bool:
    """Decide whether a file entry should appear in the tree.

    A file is included when it is not matched by any exclude pattern AND
    matches at least one include pattern (if a whitelist is set).
    Exclude is evaluated first.

    Args:
        rel_path: File path relative to the project root.
        include_patterns: Whitelist patterns, or None to allow everything.
        exclude_patterns: Blacklist patterns; checked before include.

    Returns:
        True if the file should be included, False otherwise.
    """
    if exclude_patterns and matches_any(rel_path, exclude_patterns):
        return False
    if include_patterns is not None and not matches_any(rel_path, include_patterns):
        return False
    return True


def _dir_could_contain_match(rel_path: str | Path, patterns: list[str]) -> bool:
    """Return True if this directory could contain files matching at least one include pattern.

    A directory is a candidate when its normalised path is a strict path prefix
    of at least one include pattern, or when it matches a pattern directly
    (e.g. a trailing-slash or ** pattern that covers the directory itself).

    Args:
        rel_path: Directory path relative to the project root.
        patterns: Include glob patterns to check against.

    Returns:
        True if the directory should be entered, False if it can be pruned.
    """
    normalised = _to_posix_rel(rel_path)
    if not normalised:
        return True  # root is always a candidate

    for pattern in patterns:
        # Direct match: pattern covers the directory itself (e.g. "src/**")
        if _build_spec([pattern]).match_file(normalised):
            return True
        # Prefix match: directory is an ancestor of the pattern target.
        # Strip a leading slash if present (anchored gitignore pattern).
        clean = pattern.lstrip("/")
        if clean.startswith(normalised + "/"):
            return True

    return False


def is_dir_traversable(
    rel_path: str | Path,
    include_patterns: list[str] | None,
    exclude_patterns: list[str],
) -> bool:
    if exclude_patterns and matches_any(rel_path, exclude_patterns):
        return False
    if include_patterns is not None and not _dir_could_contain_match(rel_path, include_patterns):
        return False
    return True
