from typing import Optional, List
from pydantic import BaseModel, Field


class SearchProjectContentRequest(BaseModel):
    """Input schema for the search_project_content tool.

    Attributes:
        project_id: Identifier of the registered project to search.
        pattern: The search term or regular expression to look for.
        use_regex: When True, pattern is compiled as a regular expression.
                   When False, pattern is treated as a plain string literal.
                   Defaults to False.
        ignore_case: Perform case-insensitive matching. Defaults to True.
        include: Glob patterns restricting which files are searched.
                 None means search all files.
        exclude: Glob patterns excluding files from the search.
        exclude_from: Gitignore-style exclusion file relative to the project
                      root. Defaults to '.gitignore'. Set to None to disable.
        include_hidden: Search hidden files and directories. Defaults to False.
        context_lines: Number of lines of context to include before and after
                       each match. Adjacent or overlapping context windows are
                       merged into a single block. Defaults to 2.
        max_matches_per_file: Stop collecting matches in a file after this
                              limit. None means unlimited. Defaults to 50.
        max_files: Stop searching after this many matched files. None means
                   unlimited. Defaults to 100.
    """

    project_id: str = Field(description="Registered project identifier.")
    pattern: str = Field(description="Search term or regular expression.")
    use_regex: bool = Field(
        default=False,
        description="Interpret pattern as a regular expression.",
    )
    ignore_case: bool = Field(
        default=True,
        description="Case-insensitive matching.",
    )
    include: Optional[List[str]] = Field(
        default=None,
        description="Glob patterns to restrict which files are searched.",
    )
    exclude: Optional[List[str]] = Field(
        default=None,
        description="Glob patterns to exclude files from the search.",
    )
    exclude_from: Optional[str] = Field(
        default=".gitignore",
        description="Gitignore-style exclusion file relative to the project root.",
    )
    include_hidden: bool = Field(
        default=False,
        description="Search hidden files and directories.",
    )
    context_lines: int = Field(
        default=2,
        ge=0,
        description="Lines of context before and after each match. Overlapping windows are merged.",
    )
    max_matches_per_file: Optional[int] = Field(
        default=50,
        ge=1,
        description="Maximum matches collected per file before truncation.",
    )
    max_files: Optional[int] = Field(
        default=100,
        ge=1,
        description="Maximum number of matched files before truncation.",
    )


class MatchLine(BaseModel):
    """A single line inside a match block.

    Attributes:
        line_number: 1-indexed line number in the file.
        content: Raw content of the line.
        is_match: True if this line contains a match, False if it is context.
    """

    line_number: int
    content: str
    is_match: bool


class MatchBlock(BaseModel):
    """A contiguous block of lines containing one or more matches plus context.

    Overlapping context windows from adjacent matches are merged so that
    each line appears at most once per block.

    Attributes:
        start_line: 1-indexed line number of the first line in the block.
        end_line: 1-indexed line number of the last line in the block.
        match_count: Number of matching lines in this block.
        lines: Ordered list of all lines in the block (context and matches).
    """

    start_line: int
    end_line: int
    match_count: int
    lines: List[MatchLine]


class FileMatches(BaseModel):
    """All matches found inside a single file.

    Attributes:
        relative_path: File path relative to the project root.
        language: Detected programming language of the file, if any.
        match_count: Total number of matching lines in this file.
        blocks: Merged contiguous match blocks, in file order.
        truncated: True if max_matches_per_file was reached before EOF.
    """

    relative_path: str
    language: Optional[str]
    match_count: int
    blocks: List[MatchBlock]
    truncated: bool


class SearchProjectContentResponse(BaseModel):
    """Output schema for the search_project_content tool.

    Attributes:
        results: One FileMatches entry per file that contained at least one match.
        total_files_searched: Total number of files examined.
        total_files_matched: Number of files that contained at least one match.
        total_matches: Sum of all matching lines across all files.
        truncated: True if max_files was reached before all files were searched.
        warnings: Non-fatal issues such as unreadable files or a missing
                  gitignore. Empty list when there are no warnings.
    """

    results: List[FileMatches]
    total_files_searched: int
    total_files_matched: int
    total_matches: int
    truncated: bool
    warnings: List[str] = Field(default_factory=list)