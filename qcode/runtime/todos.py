"""Structured todo state for multi-step agent work."""

from dataclasses import dataclass
from typing import Iterable, List, Mapping


VALID_TODO_STATUSES = ("pending", "in_progress", "completed")
TODO_MARKERS = {
    "pending": "[ ]",
    "in_progress": "[>]",
    "completed": "[x]",
}


@dataclass(frozen=True)
class TodoItem:
    """A single todo item tracked by the agent."""

    item_id: str
    text: str
    status: str


class TodoManager:
    """Validates and renders the todo list written by the model."""

    def __init__(self) -> None:
        self._items: List[TodoItem] = []

    @property
    def items(self) -> List[TodoItem]:
        return list(self._items)

    def update(self, items: Iterable[Mapping[str, object]]) -> str:
        candidate_items = list(items)
        if len(candidate_items) > 20:
            raise ValueError("Max 20 todos allowed")

        validated: List[TodoItem] = []
        in_progress_count = 0

        for index, item in enumerate(candidate_items, start=1):
            item_id = str(item.get("id", index)).strip()
            text = str(item.get("text", "")).strip()
            status = str(item.get("status", "pending")).strip().lower()

            if not text:
                raise ValueError(f"Item {item_id}: text required")
            if status not in VALID_TODO_STATUSES:
                raise ValueError(f"Item {item_id}: invalid status '{status}'")

            if status == "in_progress":
                in_progress_count += 1

            validated.append(TodoItem(item_id=item_id, text=text, status=status))

        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress at a time")

        self._items = validated
        return self.render()

    def render(self) -> str:
        if not self._items:
            return "No todos."

        lines = []
        for item in self._items:
            marker = TODO_MARKERS[item.status]
            lines.append(f"{marker} #{item.item_id}: {item.text}")

        completed_count = sum(1 for item in self._items if item.status == "completed")
        lines.append(f"\n({completed_count}/{len(self._items)} completed)")
        return "\n".join(lines)
