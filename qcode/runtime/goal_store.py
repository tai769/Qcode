"""Persistent mission/goal storage for lead-directed runs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class GoalStore:
    """Stores the active project goal.

    When ``persist=True`` (resume mode), the goal is read/written to a file
    so it survives across sessions.  When ``persist=False`` (fresh start,
    the default), the goal lives in memory only — like Claude Code's
    per-conversation model.
    """

    def __init__(self, path: Path, *, persist: bool = False) -> None:
        self.path = path
        self.persist = persist
        self._memory: str = ""

    def get(self) -> str:
        if not self.persist:
            return self._memory
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
        self._memory = cleaned_goal
        if self.persist:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(cleaned_goal, encoding="utf-8")
        return cleaned_goal

    def clear(self) -> None:
        self._memory = ""
        if self.persist:
            try:
                if self.path.exists():
                    self.path.unlink()
            except Exception:
                return
