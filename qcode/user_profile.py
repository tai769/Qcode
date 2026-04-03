"""Workspace-level user profile loading for persistent collaboration preferences."""

from __future__ import annotations

from pathlib import Path


DEFAULT_USER_PROFILE_PATH = Path(".qcode/user_profile.md")


def load_user_profile(workdir: Path) -> str:
    """Load workspace user preferences if present."""

    path = (workdir / DEFAULT_USER_PROFILE_PATH).resolve()
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def append_user_profile(workdir: Path, prompt: str) -> str:
    """Append the workspace user profile block to a system prompt."""

    profile = load_user_profile(workdir)
    if not profile:
        return prompt
    return (
        f"{prompt}"
        "\nUser profile preferences:\n"
        "<user_profile>\n"
        f"{profile}\n"
        "</user_profile>\n"
    )
