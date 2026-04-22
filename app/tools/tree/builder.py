import logging
from typing import List, Dict
from dataclasses import dataclass, field
from pathlib import Path

from app.core.filtering import build_filter_set, is_file_included, is_dir_traversable
from .schemas import (
    ExpansionStatus,
    GetTreeRequest,
    GetTreeResponse,
    TreeNode,
    TreeStats,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal accumulator
# ---------------------------------------------------------------------------

@dataclass
class _Stats:
    """Mutable statistics accumulated during tree traversal."""

    files: int = 0
    directories: int = 0
    total_size: int = 0
    by_extension: Dict[str, int] = field(default_factory=dict)
    max_depth_reached: int = 0
    depth_is_real: bool = True  # flipped to False on first DEPTH_LIMIT hit

    def record_file(self, size: int, extension: str | None, depth: int) -> None:
        self.files += 1
        self.total_size += size
        if extension:
            self.by_extension[extension] = self.by_extension.get(extension, 0) + 1
        if depth > self.max_depth_reached:
            self.max_depth_reached = depth

    def record_dir(self, depth: int) -> None:
        self.directories += 1
        if depth > self.max_depth_reached:
            self.max_depth_reached = depth


# ---------------------------------------------------------------------------
# Core recursive walk
# ---------------------------------------------------------------------------

def _walk(
    abs_path: Path,
    rel_path: Path,
    depth: int,
    max_depth: int | None,
    include_hidden: bool,
    include_patterns: List[str] | None,
    exclude_patterns: List[str],
    stats: _Stats,
) -> TreeNode:
    """Recursively build a TreeNode for abs_path.

    Args:
        abs_path: Absolute path to the current entry.
        rel_path: Path of the current entry relative to the project root.
        depth: Current recursion depth (root = 0).
        max_depth: Maximum depth to recurse into, None for unlimited.
        include_hidden: Whether to explore hidden entries.
        include_patterns: Whitelist glob patterns applied to files only.
        exclude_patterns: Blacklist glob patterns applied to both files and dirs.
        stats: Mutable stats accumulator shared across the whole traversal.

    Returns:
        A fully populated TreeNode for the current entry.
    """
    name = abs_path.name
    rel_str = rel_path.as_posix()

    # ---- File node --------------------------------------------------------
    if abs_path.is_file():
        size = abs_path.stat().st_size
        ext = abs_path.suffix if abs_path.suffix else None
        stats.record_file(size, ext, depth)
        return TreeNode(
            name=name,
            path=rel_str,
            is_dir=False,
            size=size,
            extension=ext,
        )

    # ---- Directory node ---------------------------------------------------
    stats.record_dir(depth)

    # Depth limit: do not descend, signal with DEPTH_LIMIT
    if max_depth is not None and depth >= max_depth:
        try:
            has_content = any(abs_path.iterdir())
        except PermissionError:
            has_content = False

        if has_content:
            stats.depth_is_real = False

        return TreeNode(
            name=name,
            path=rel_str,
            is_dir=True,
            expansion_status=ExpansionStatus.DEPTH_LIMIT if has_content else ExpansionStatus.EXPANDED,
            children=None if has_content else [],
        )

    # Descend into the directory
    children: list[TreeNode] = []

    try:
        entries = sorted(abs_path.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    except PermissionError:
        logger.warning("Permission denied reading directory: %s", abs_path)
        return TreeNode(
            name=name,
            path=rel_str,
            is_dir=True,
            expansion_status=ExpansionStatus.EXCLUDED,
        )

    for entry in entries:
        entry_rel = rel_path / entry.name

        # Hidden check: for directories the entire subtree is suppressed.
        if not include_hidden and entry.name.startswith("."):
            if entry.is_dir():
                children.append(TreeNode(
                    name=entry.name,
                    path=entry_rel.as_posix(),
                    is_dir=True,
                    expansion_status=ExpansionStatus.HIDDEN,
                ))
            # Hidden files are silently omitted
            continue

        if entry.is_dir():
            # Directories: exclude filter only, never the include whitelist.
            if not is_dir_traversable(entry_rel, include_patterns, exclude_patterns):
                children.append(TreeNode(
                    name=entry.name,
                    path=entry_rel.as_posix(),
                    is_dir=True,
                    expansion_status=ExpansionStatus.EXCLUDED,
                ))
                continue
        else:
            # Files: both include and exclude filters apply.
            if not is_file_included(entry_rel, include_patterns, exclude_patterns):
                # Excluded files are silently omitted
                continue

        children.append(_walk(
            abs_path=entry,
            rel_path=entry_rel,
            depth=depth + 1,
            max_depth=max_depth,
            include_hidden=include_hidden,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            stats=stats,
        ))

    return TreeNode(
        name=name,
        path=rel_str,
        is_dir=True,
        expansion_status=ExpansionStatus.EXPANDED,
        children=children,
    )


# ---------------------------------------------------------------------------
# String renderer
# ---------------------------------------------------------------------------

def _render_string(node: TreeNode, prefix: str = "", is_last: bool = True) -> str:
    """Render a TreeNode tree as a classic branch-style string.

    Args:
        node: The node to render.
        prefix: Accumulated prefix string for indentation (used in recursion).
        is_last: Whether this node is the last child of its parent.

    Returns:
        A multi-line string representing the subtree rooted at node.
    """
    connector = "└── " if is_last else "├── "
    line = f"{prefix}{connector}{node.name}" if prefix else node.name

    if node.is_dir:
        status = node.expansion_status
        if status == ExpansionStatus.DEPTH_LIMIT:
            line += "/ [...]"
        elif status == ExpansionStatus.EXCLUDED:
            line += "/ [excluded]"
        elif status == ExpansionStatus.HIDDEN:
            line += "/ [hidden]"
        else:
            line += "/"

    lines = [line]

    if node.children:
        extension_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(node.children):
            child_is_last = i == len(node.children) - 1
            lines.append(_render_string(child, extension_prefix, child_is_last))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_tree(project_root: Path, request: GetTreeRequest) -> GetTreeResponse:
    """Build a filtered project tree and return a ready-to-return response.

    Args:
        project_root: Absolute validated path to the project root.
        request: Incoming tool request carrying all filtering parameters.

    Returns:
        A GetTreeResponse with either a TreeNode tree or a string, plus
        stats and any non-fatal warnings.
    """
    include_patterns, exclude_patterns, warnings = build_filter_set(
        project_root=project_root,
        include=request.include,
        exclude=request.exclude,
        exclude_from=request.exclude_from,
    )

    stats = _Stats()

    root_node = _walk(
        abs_path=project_root,
        rel_path=Path(project_root.name),
        depth=0,
        max_depth=request.max_depth,
        include_hidden=request.include_hidden,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        stats=stats,
    )

    tree_stats = TreeStats(
        files=stats.files,
        directories=stats.directories,
        total_size=stats.total_size,
        by_extension=stats.by_extension,
        max_depth_requested=request.max_depth,
        max_depth_reached=stats.max_depth_reached,
        depth_is_real=stats.depth_is_real,
    )

    return GetTreeResponse(
        tree=root_node if not request.as_string else None,
        tree_string=_render_string(root_node) if request.as_string else None,
        stats=tree_stats,
        warnings=warnings,
    )