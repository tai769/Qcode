"""Persistent mission/goal storage for lead-directed runs."""

from __future__ import annotations

from pathlib import Path


class GoalStore:
    """Stores the active project goal in a workspace-local file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def get(self) -> str:
        try:
            if not self.path.exists():
                return ""
            return self.path.read_text(encoding="utf-8").strip()
        except Exception:
            return ""

    def set(self, goal: str) -> str:
        cleaned_goal = goal.strip()
        if not cleaned_goal:
            raise ValueError("Goal cannot be empty")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(cleaned_goal, encoding="utf-8")
        return cleaned_goal

    def clear(self) -> None:
        try:
            if self.path.exists():
                self.path.unlink()
        except Exception:
            return
