from typing import Optional
from pathlib import Path

# Mapping of file extensions to programming / markup languages
EXTENSION_TO_LANGUAGE = {
    # Documents
    ".txt": "text",

    # Python
    ".py": "python",
    ".pyw": "python",
    ".pyx": "python",
    
    # JavaScript / TypeScript
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    
    # Web
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    
    # Compiled languages
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".scala": "scala",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    
    # Systems programming
    ".rs": "rust",
    ".go": "go",
    ".zig": "zig",
    
    # Scripting
    ".rb": "ruby",
    ".php": "php",
    ".pl": "perl",
    ".lua": "lua",
    ".r": "r",
    
    # Shell
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".fish": "shell",
    
    # Config / Data
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".ini": "ini",
    
    # Documentation
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".tex": "latex",
}


def detect_language(file_path: Path) -> Optional[str]:
    """
    Detect the programming or markup language of a file based on its extension.

    Args:
        file_path (Path): Path to the file.

    Returns:
        Optional[str]: The detected language name if the extension is known,
        otherwise None.
    """
    ext = file_path.suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(ext)