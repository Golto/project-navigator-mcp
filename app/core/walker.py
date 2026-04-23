import logging
from collections.abc import Generator
from pathlib import Path

from app.core.filtering import is_dir_traversable, is_file_included


logger = logging.getLogger(__name__)


def walk_files(
    project_root: Path,
    include_patterns: list[str] | None,
    exclude_patterns: list[str],
    include_hidden: bool,
) -> Generator[Path, None, None]:
    """Yield absolute paths of every file that passes the filter rules.

    Directories are traversed depth-first. A directory that is excluded or
    hidden is not entered and none of its descendants are visited. Files that
    do not pass the include/exclude filters are silently skipped.

    Symbolic links are followed for files but not for directories, to avoid
    infinite loops.

    PermissionError on any entry is logged as a warning and the entry is
    skipped.

    Args:
        project_root: Absolute path to the project root.
        include_patterns: Whitelist glob patterns for files, or None to
                          accept all files.
        exclude_patterns: Blacklist glob patterns applied to both files and
                          directories.
        include_hidden: When False, hidden entries (names starting with '.')
                        are skipped entirely; a hidden directory suppresses
                        its whole subtree.

    Yields:
        Absolute Path objects for each file that should be visited.
    """
    def _recurse(directory: Path, rel_dir: Path) -> Generator[Path, None, None]:
        try:
            entries = sorted(directory.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
        except PermissionError:
            logger.warning("Permission denied reading directory: %s", directory)
            return

        for entry in entries:
            entry_rel = rel_dir / entry.name

            # Hidden check
            if not include_hidden and entry.name.startswith("."):
                continue

            if entry.is_dir() and not entry.is_symlink():
                if not is_dir_traversable(entry_rel, include_patterns, exclude_patterns):
                    continue
                yield from _recurse(entry, entry_rel)

            elif entry.is_file():
                if not is_file_included(entry_rel, include_patterns, exclude_patterns):
                    continue
                yield entry

    yield from _recurse(project_root, Path(project_root.name))