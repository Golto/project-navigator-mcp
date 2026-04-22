from app.mcp import get_mcp
from app.storage import get_project_storage
from app.core.language import detect_language
from app.core.reading import read_file

from .schemas import ReadFileRequest, ReadFileResponse

mcp = get_mcp()
project_storage = get_project_storage()


@mcp.tool()
def read_project_file(request: ReadFileRequest) -> ReadFileResponse:
    """Read a file from a registered project, with optional line range and numbering.

    Resolves the project root from the registry, reads the requested file,
    and returns a slice of its content. Line numbers are 1-indexed throughout.
    """
    project_path = project_storage.resolve_project_path(request.project_id)
    lines = read_file(project_path, request.relative_path)

    total = len(lines)

    # Resolve the effective range (convert to 0-indexed for slicing)
    start = (request.start_line - 1) if request.start_line is not None else 0
    end = request.end_line if request.end_line is not None else total

    # Clamp to actual file boundaries
    start = max(0, min(start, total))
    end = max(start, min(end, total))

    selected = lines[start:end]

    if request.include_line_numbers:
        width = len(str(total))

        content = "\n".join(
            f"{start + i + 1:>{width}} │ {line}"
            for i, line in enumerate(selected)
        )
    else:
        content = "\n".join(selected)

    file_path = (project_path / request.relative_path).resolve()

    return ReadFileResponse(
        content=content,
        language=detect_language(file_path),
        total_lines=total,
        returned_lines=len(selected),
        start_line=start + 1,
        end_line=start + len(selected),
    )