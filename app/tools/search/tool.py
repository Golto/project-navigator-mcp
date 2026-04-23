from typing import List

from app.mcp import get_mcp
from app.storage import get_project_storage
from app.core.language import detect_language
from app.core.filtering import build_filter_set
from app.core.walker import walk_files
from app.core.search import compile_pattern, search_file

from .schemas import (
    SearchProjectContentRequest,
    SearchProjectContentResponse,
    FileMatches,
    MatchBlock,
    MatchLine,
)

mcp = get_mcp()
project_storage = get_project_storage()


@mcp.tool()
def search_project_content(request: SearchProjectContentRequest) -> SearchProjectContentResponse:
    """Search for a pattern across all files of a registered project.

    Walks the project tree according to the include/exclude rules, searches
    each eligible file for the given pattern, and returns merged match blocks
    with surrounding context. Supports plain string and regex matching.

    Args:
        request: Search parameters including pattern, file filters, and limits.

    Returns:
        A SearchProjectContentResponse with per-file match blocks, aggregated
        statistics, and any non-fatal warnings encountered during the search.

    Raises:
        ValueError: If the project_id is not registered.
        FileNotFoundError: If the registered project path does not exist.
        re.error: If use_regex is True and pattern is not a valid regular expression.
    """
    project_root = project_storage.resolve_project_path(request.project_id)

    # Compile once: re.error propagates naturally for invalid regex
    compiled = compile_pattern(request.pattern, request.use_regex, request.ignore_case)

    include_patterns, exclude_patterns, warnings = build_filter_set(
        project_root=project_root,
        include=request.include,
        exclude=request.exclude,
        exclude_from=request.exclude_from,
    )

    results: List[FileMatches] = []
    total_files_searched = 0
    total_matches = 0
    response_truncated = False

    for abs_path in walk_files(project_root, include_patterns, exclude_patterns, request.include_hidden):
        total_files_searched += 1

        blocks_raw, match_count, file_truncated, warning = search_file(
            path=abs_path,
            compiled=compiled,
            context_lines=request.context_lines,
            max_matches=request.max_matches_per_file,
        )

        if warning:
            warnings.append(warning)

        if not blocks_raw:
            continue

        # Convert internal _Block objects to schema MatchBlock
        schema_blocks: List[MatchBlock] = []
        for block in blocks_raw:
            schema_lines = [
                MatchLine(
                    line_number=block.first_line + i,
                    content=line,
                    is_match=(block.first_line + i) in block.match_lines,
                )
                for i, line in enumerate(block.lines)
            ]
            schema_blocks.append(MatchBlock(
                start_line=block.first_line,
                end_line=block.first_line + len(block.lines) - 1,
                match_count=len(block.match_lines),
                lines=schema_lines,
            ))

        rel_path = abs_path.relative_to(project_root)

        results.append(FileMatches(
            relative_path=rel_path.as_posix(),
            language=detect_language(abs_path),
            match_count=match_count,
            blocks=schema_blocks,
            truncated=file_truncated,
        ))

        total_matches += match_count

        if request.max_files is not None and len(results) >= request.max_files:
            response_truncated = True
            break

    return SearchProjectContentResponse(
        results=results,
        total_files_searched=total_files_searched,
        total_files_matched=len(results),
        total_matches=total_matches,
        truncated=response_truncated,
        warnings=warnings,
    )