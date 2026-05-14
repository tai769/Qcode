"""File path completer for @ references in the TUI input."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional


def get_file_completions(
    partial: str,
    workdir: Path,
    max_results: int = 20,
) -> List[str]:
    """Get file path completions for @ references.

    Args:
        partial: The text after @ (e.g., "src/agen")
        workdir: Project root directory
        max_results: Maximum number of results

    Returns:
        List of matching file paths relative to workdir
    """
    if not partial:
        # Show top-level files/dirs
        return _list_directory(workdir, workdir, max_results)

    # Resolve the partial path
    if "/" in partial:
        dir_part, name_part = partial.rsplit("/", 1)
        search_dir = workdir / dir_part
    else:
        dir_part = ""
        name_part = partial
        search_dir = workdir

    if not search_dir.exists():
        return []

    results = []
    try:
        for entry in sorted(search_dir.iterdir()):
            if entry.name.startswith(".") and not name_part.startswith("."):
                continue
            if entry.name.startswith(name_part):
                rel = entry.relative_to(workdir)
                display = str(rel)
                if entry.is_dir():
                    display += "/"
                results.append(display)
                if len(results) >= max_results:
                    break
    except PermissionError:
        pass

    return results


def _list_directory(directory: Path, workdir: Path, max_results: int) -> List[str]:
    """List directory contents as relative paths."""
    results = []
    try:
        for entry in sorted(directory.iterdir()):
            if entry.name.startswith("."):
                continue
            rel = entry.relative_to(workdir)
            display = str(rel)
            if entry.is_dir():
                display += "/"
            results.append(display)
            if len(results) >= max_results:
                break
    except PermissionError:
        pass
    return results


def extract_at_reference(text: str, cursor_pos: int) -> Optional[str]:
    """Extract the @ reference being typed.

    Returns the partial path after @, or None if not in an @ reference.
    """
    # Find the last @ before cursor
    at_pos = text.rfind("@", 0, cursor_pos)
    if at_pos == -1:
        return None

    # Make sure @ is at start or preceded by whitespace
    if at_pos > 0 and not text[at_pos - 1].isspace():
        return None

    # Extract the partial path (from @ to cursor, no spaces)
    partial = text[at_pos + 1:cursor_pos]
    if " " in partial:
        return None

    return partial


def replace_at_reference(text: str, cursor_pos: int, completion: str) -> tuple[str, int]:
    """Replace the @ reference with a completion.

    Returns (new_text, new_cursor_pos).
    """
    at_pos = text.rfind("@", 0, cursor_pos)
    if at_pos == -1:
        return text, cursor_pos

    new_text = text[:at_pos] + "@" + completion + " " + text[cursor_pos:]
    new_cursor_pos = at_pos + 1 + len(completion) + 1
    return new_text, new_cursor_pos
