import logging
import re
from typing import List, Tuple, Set
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)

# Heuristic: a file is binary if its first chunk contains a null byte.
_BINARY_PROBE_BYTES = 8192


# ---------------------------------------------------------------------------
# Internal types
# ---------------------------------------------------------------------------

@dataclass
class _RawMatch:
    """A single matching line before context merging."""
    line_number: int  # 1-indexed
    content: str


@dataclass
class _Block:
    """A merged contiguous block of lines (context + matches)."""
    first_line: int   # 1-indexed
    lines: List[str]  # raw line contents in order
    match_lines: Set[int]  # 1-indexed line numbers that are matches


# ---------------------------------------------------------------------------
# Binary detection
# ---------------------------------------------------------------------------

def is_binary(path: Path) -> bool:
    """Return True if path looks like a binary file.

    Reads up to _BINARY_PROBE_BYTES bytes and checks for a null byte,
    which is absent in virtually all plain-text files.

    Args:
        path: Absolute path to the file.

    Returns:
        True if the file appears to be binary, False otherwise.
    """
    try:
        with path.open("rb") as fh:
            return b"\x00" in fh.read(_BINARY_PROBE_BYTES)
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Context merging
# ---------------------------------------------------------------------------

def _merge_into_blocks(
    raw_matches: List[_RawMatch],
    all_lines: List[str],
    context_lines: int,
) -> List[_Block]:
    """Merge raw matches and their context windows into non-overlapping blocks.

    For each match, a window of context_lines before and after is computed.
    Adjacent or overlapping windows are merged into a single block so that
    no line appears twice, mirroring the behaviour of grep -C.

    Args:
        raw_matches: Matches found in the file, in line order.
        all_lines: Every line of the file (0-indexed).
        context_lines: Number of context lines around each match.

    Returns:
        A list of _Block objects in file order.
    """
    if not raw_matches:
        return []

    total = len(all_lines)
    blocks: list[_Block] = []
    # Each match contributes a [start, end] window (0-indexed, inclusive)
    windows: list[tuple[int, int]] = []

    for m in raw_matches:
        idx = m.line_number - 1  # convert to 0-indexed
        start = max(0, idx - context_lines)
        end = min(total - 1, idx + context_lines)
        windows.append((start, end))

    # Merge overlapping or adjacent windows
    merged: list[tuple[int, int]] = [windows[0]]
    for start, end in windows[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end + 1:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))

    # Build _Block objects from merged windows
    match_line_set = {m.line_number for m in raw_matches}
    for start, end in merged:
        block_lines = all_lines[start : end + 1]
        block_match_lines = {
            ln for ln in match_line_set if start + 1 <= ln <= end + 1
        }
        blocks.append(_Block(
            first_line=start + 1,  # back to 1-indexed
            lines=block_lines,
            match_lines=block_match_lines,
        ))

    return blocks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compile_pattern(pattern: str, use_regex: bool, ignore_case: bool) -> re.Pattern:
    """Compile a search pattern into a regular expression.

    When use_regex is False the pattern is escaped so that it is treated
    as a plain string literal.

    Args:
        pattern: The raw search string or regex pattern.
        use_regex: When False, escape the pattern before compiling.
        ignore_case: Add re.IGNORECASE to the compiled pattern.

    Returns:
        A compiled re.Pattern object.

    Raises:
        re.error: If use_regex is True and pattern is not valid regex.
    """
    flags = re.IGNORECASE if ignore_case else 0
    effective = pattern if use_regex else re.escape(pattern)
    return re.compile(effective, flags)


def search_file(
    path: Path,
    compiled: re.Pattern,
    context_lines: int,
    max_matches: int | None,
) -> Tuple[List[_Block], int, bool, str | None]:
    """Search a single file for matches of a compiled pattern.

    Skips binary files silently. Returns an empty result with a warning
    message if the file cannot be decoded as UTF-8.

    Args:
        path: Absolute path to the file to search.
        compiled: Pre-compiled search pattern.
        context_lines: Lines of context to include around each match.
        max_matches: Stop after this many matches. None means unlimited.

    Returns:
        A four-tuple (blocks, match_count, truncated, warning) where:
        - blocks is the list of merged match blocks.
        - match_count is the number of matching lines found.
        - truncated is True if max_matches was reached before EOF.
        - warning is a non-None string if the file had to be skipped or
          could not be fully read.
    """
    if is_binary(path):
        return [], 0, False, None  # silently skipped

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        warning = f"Could not decode '{path}' as UTF-8; file skipped."
        return [], 0, False, warning
    except OSError as exc:
        warning = f"Could not read '{path}': {exc}"
        return [], 0, False, warning

    all_lines = content.splitlines()
    raw_matches: list[_RawMatch] = []
    truncated = False

    for idx, line in enumerate(all_lines):
        if compiled.search(line):
            raw_matches.append(_RawMatch(line_number=idx + 1, content=line))
            if max_matches is not None and len(raw_matches) >= max_matches:
                truncated = True
                break

    blocks = _merge_into_blocks(raw_matches, all_lines, context_lines)
    return blocks, len(raw_matches), truncated, None