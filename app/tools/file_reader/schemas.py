from typing import Optional
from pydantic import BaseModel, Field


class ReadFileRequest(BaseModel):
    """Input schema for the read_project_file tool.

    Attributes:
        project_id: Identifier of the registered project to read from.
        relative_path: Path to the file relative to the project root.
        start_line: First line to include, 1-indexed. Defaults to the
                    beginning of the file.
        end_line: Last line to include, 1-indexed and inclusive. Defaults
                  to the end of the file.
        include_line_numbers: When True, each line in the response is
                              prefixed with its 1-indexed line number.
                              Defaults to False.
    """

    project_id: str = Field(description="Registered project identifier.")
    relative_path: str = Field(
        description="Path to the file relative to the project root (e.g. 'app/core/reading.py')."
    )
    start_line: Optional[int] = Field(
        default=None,
        ge=1,
        description="First line to return, 1-indexed. Defaults to line 1.",
    )
    end_line: Optional[int] = Field(
        default=None,
        ge=1,
        description="Last line to return, 1-indexed inclusive. Defaults to the last line.",
    )
    include_line_numbers: bool = Field(
        default=False,
        description="Prefix every returned line with its 1-indexed line number.",
    )


class ReadFileResponse(BaseModel):
    """Output schema for the read_project_file tool.

    Attributes:
        content: File content as a single string, respecting the requested
                 line range and numbering options.
        language: Detected programming language of the file, if any.
        total_lines: Total number of lines in the full file.
        returned_lines: Number of lines actually returned in content.
        start_line: Effective first line returned, 1-indexed.
        end_line: Effective last line returned, 1-indexed.
    """

    content: str = Field(description="File content, optionally line-numbered and sliced.")
    language: Optional[str] = Field(
        default=None,
        description="Detected language of the file (e.g. 'python', 'typescript').",
    )
    total_lines: int = Field(description="Total number of lines in the full file.")
    returned_lines: int = Field(description="Number of lines present in content.")
    start_line: int = Field(description="Effective first line returned, 1-indexed.")
    end_line: int = Field(description="Effective last line returned, 1-indexed.")