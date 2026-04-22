from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class ExpansionStatus(str, Enum):
    """Reason why a directory node was or was not expanded.

    Attributes:
        EXPANDED: The directory was fully explored.
        DEPTH_LIMIT: Expansion stopped because max_depth was reached.
        EXCLUDED: The directory matched an exclude pattern or gitignore rule.
        HIDDEN: The directory is hidden (name starts with '.') and
                include_hidden is False. The entire subtree is suppressed.
    """

    EXPANDED = "expanded"
    DEPTH_LIMIT = "depth_limit"
    EXCLUDED = "excluded"
    HIDDEN = "hidden"


class TreeNode(BaseModel):
    """A single node in the project directory tree.

    Attributes:
        name: Name of the file or directory.
        path: Path relative to the project root.
        is_dir: True if this node is a directory, False if it is a file.
        size: File size in bytes. None for directories.
        extension: File extension including the dot (e.g. '.py'). None for directories.
        children: Child nodes. None for files, and for directories that were
                  not expanded (check expansion_status in that case).
        expansion_status: For directories only -- indicates whether the node
                          was expanded and if not, why. None for file nodes.
    """

    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None
    extension: Optional[str] = None
    children: Optional[list["TreeNode"]] = None
    expansion_status: Optional[ExpansionStatus] = None


class TreeStats(BaseModel):
    """Aggregated statistics for the returned tree.

    Attributes:
        files: Total number of file nodes in the returned tree.
        directories: Total number of directory nodes in the returned tree.
        total_size: Sum of all file sizes in bytes.
        by_extension: Mapping of file extension to file count.
        max_depth_requested: The max_depth value passed in the request.
                             None means unlimited was requested.
        max_depth_reached: The deepest level actually present in the returned tree.
        depth_is_real: True when max_depth_reached reflects the true bottom of
                       the project (no depth_limit cutoff was encountered).
                       False means at least one directory was cut off by max_depth,
                       so the real depth of the project may be greater.
    """

    files: int
    directories: int
    total_size: int
    by_extension: Dict[str, int]
    max_depth_requested: Optional[int]
    max_depth_reached: int
    depth_is_real: bool


class GetTreeRequest(BaseModel):
    """Input schema for the get_project_tree tool.

    Attributes:
        project_id: Identifier of the registered project to explore.
        max_depth: Maximum depth to recurse into. 0 means the root only,
                   None means unlimited.
        include_hidden: Include hidden files and directories (names starting
                        with a dot). When False, a hidden directory suppresses
                        its entire subtree regardless of the contents.
                        Defaults to False.
        include: Glob patterns. Only entries matching at least one pattern are
                 explored. None means include everything.
        exclude: Glob patterns. Entries matching any pattern are excluded after
                 the include filter. None means exclude nothing.
        exclude_from: Path to a gitignore-style file relative to the project
                      root. Its patterns are merged into the exclude list.
                      Defaults to '.gitignore'. Set to None to disable.
        as_string: When True, the tree is returned as a compact string using
                   classic branch characters (├──, └──, │) instead of a nested
                   JSON object. Defaults to False.
    """

    project_id: str = Field(description="Registered project identifier.")
    max_depth: Optional[int] = Field(
        default=None,
        ge=0,
        description="Maximum recursion depth. 0 = root only, None = unlimited.",
    )
    include_hidden: bool = Field(
        default=False,
        description="Include hidden files and directories (starting with '.').",
    )
    include: Optional[List[str]] = Field(
        default=None,
        description="Glob patterns to include. None means include everything.",
    )
    exclude: Optional[List[str]] = Field(
        default=None,
        description="Glob patterns to exclude, applied after include.",
    )
    exclude_from: Optional[str] = Field(
        default=".gitignore",
        description=(
            "Gitignore-style exclusion file relative to the project root. "
            "Merged with exclude. Set to None to disable."
        ),
    )
    as_string: bool = Field(
        default=False,
        description="Return the tree as a compact branch-style string instead of a JSON object.",
    )


class GetTreeResponse(BaseModel):
    """Output schema for the get_project_tree tool.

    Exactly one of tree or tree_string is populated depending on the
    as_string flag in the request.

    Attributes:
        tree: Root TreeNode of the nested structure. None when as_string is True.
        tree_string: Compact branch-style string. None when as_string is False.
        stats: Aggregated statistics for the returned tree.
        warnings: Non-fatal issues encountered during tree building, such as
                  a missing exclude_from file or unreadable directories.
                  Empty list when there are no warnings.
    """

    tree: Optional[TreeNode] = Field(
        default=None,
        description="Nested tree object. Populated when as_string is False.",
    )
    tree_string: Optional[str] = Field(
        default=None,
        description="Compact branch-style string. Populated when as_string is True.",
    )
    stats: TreeStats
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal warnings raised during tree construction.",
    )