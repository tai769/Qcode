"""Persistent task graph stored as JSON files on disk."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any, Optional

from qcode.telemetry.events import EventSink, NullEventSink


VALID_TASK_STATUSES = {"pending", "in_progress", "completed"}
TASK_STATUS_MARKERS = {
    "pending": "[ ]",
    "in_progress": "[>]",
    "completed": "[x]",
}


class TaskGraphManager:
    """File-backed DAG-like task state shared across sessions and teammates."""

    def __init__(
        self,
        tasks_dir: Path,
        event_sink: Optional[EventSink] = None,
    ) -> None:
        self.dir = tasks_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.event_sink = event_sink or NullEventSink()
        self._lock = threading.RLock()
        self._next_id = self._max_id() + 1

    def create(
        self,
        subject: str,
        description: str = "",
        blocked_by: Optional[list[int]] = None,
        owner: str = "",
        required_role: str = "",
    ) -> str:
        cleaned_subject = subject.strip()
        if not cleaned_subject:
            raise ValueError("Task subject is required")

        with self._lock:
            task_id = self._next_id
            dependencies = self._normalize_dependencies(
                task_id,
                blocked_by or [],
            )
            now = self._utc_now()
            task = {
                "id": task_id,
                "subject": cleaned_subject,
                "description": description.strip(),
                "status": "pending",
                "blockedBy": dependencies,
                "owner": owner.strip(),
                "requiredRole": self._normalize_role(required_role),
                "createdAt": now,
                "updatedAt": now,
            }
            self._save_unlocked(task)
            self._next_id += 1

        self._emit_event(
            "task.created",
            {
                "task_id": task_id,
                "blocked_by": dependencies,
                "owner": owner.strip(),
                "required_role": task["requiredRole"],
            },
        )
        return self._render_task(task)

    def get(self, task_id: int) -> str:
        with self._lock:
            task = self._load_unlocked(task_id)
        return self._render_task(task)

    def update(
        self,
        task_id: int,
        status: Optional[str] = None,
        add_blocked_by: Optional[list[int]] = None,
        remove_blocked_by: Optional[list[int]] = None,
        owner: Optional[str] = None,
        description: Optional[str] = None,
        required_role: Optional[str] = None,
    ) -> str:
        with self._lock:
            task = self._load_unlocked(task_id)

            if add_blocked_by:
                merged_dependencies = task.get("blockedBy", []) + add_blocked_by
                task["blockedBy"] = self._normalize_dependencies(task_id, merged_dependencies)

            if remove_blocked_by:
                removal_set = {int(value) for value in remove_blocked_by}
                task["blockedBy"] = [
                    dependency
                    for dependency in task.get("blockedBy", [])
                    if dependency not in removal_set
                ]

            if description is not None:
                task["description"] = description.strip()

            if owner is not None:
                task["owner"] = owner.strip()

            if required_role is not None:
                task["requiredRole"] = self._normalize_role(required_role)

            if status is not None:
                normalized_status = status.strip().lower()
                if normalized_status not in VALID_TASK_STATUSES:
                    valid = ", ".join(sorted(VALID_TASK_STATUSES))
                    raise ValueError(
                        f"Invalid task status '{status}'. Valid: {valid}"
                    )
                if normalized_status in {"in_progress", "completed"} and task.get(
                    "blockedBy"
                ):
                    raise ValueError(
                        f"Task {task_id} is blocked by {task['blockedBy']} and cannot be marked {normalized_status}"
                    )
                task["status"] = normalized_status

            task["updatedAt"] = self._utc_now()
            self._save_unlocked(task)

            if task["status"] == "completed":
                cleared_count = self._clear_dependency_unlocked(task_id)
            else:
                cleared_count = 0

        self._emit_event(
            "task.updated",
            {
                "task_id": task_id,
                "status": task["status"],
                "blocked_by": list(task.get("blockedBy", [])),
                "required_role": str(task.get("requiredRole", "")),
                "cleared_count": cleared_count,
            },
        )
        return self._render_task(task)

    def list_all(self) -> str:
        with self._lock:
            tasks = self._load_all_unlocked()

        if not tasks:
            return "No tasks."

        ready = [task for task in tasks if task["status"] == "pending" and not task["blockedBy"]]
        in_progress = [task for task in tasks if task["status"] == "in_progress"]
        blocked = [task for task in tasks if task["status"] == "pending" and task["blockedBy"]]
        completed = [task for task in tasks if task["status"] == "completed"]

        sections: list[str] = []
        sections.extend(self._render_section("Ready", ready))
        sections.extend(self._render_section("In Progress", in_progress))
        sections.extend(self._render_section("Blocked", blocked))
        sections.extend(self._render_section("Completed", completed))
        return "\n".join(sections)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            tasks = self._load_all_unlocked()

        return {
            "ready": [task for task in tasks if task["status"] == "pending" and not task["blockedBy"]],
            "in_progress": [task for task in tasks if task["status"] == "in_progress"],
            "blocked": [task for task in tasks if task["status"] == "pending" and task["blockedBy"]],
            "completed": [task for task in tasks if task["status"] == "completed"],
        }

    def scan_unclaimed(self, required_role: str = "") -> list[dict[str, Any]]:
        cleaned_required_role = self._normalize_role(required_role)
        with self._lock:
            tasks = self._load_all_unlocked()
        return [
            task
            for task in tasks
            if task.get("status") == "pending"
            and not task.get("owner")
            and not task.get("blockedBy")
            and (
                not cleaned_required_role
                or not self._normalize_role(str(task.get("requiredRole", "")))
                or self._normalize_role(str(task.get("requiredRole", "")))
                == cleaned_required_role
            )
        ]

    def claim(self, task_id: int, owner: str, owner_role: str = "") -> str:
        cleaned_owner = owner.strip()
        if not cleaned_owner:
            raise ValueError("Task owner is required to claim a task")
        cleaned_owner_role = self._normalize_role(owner_role)

        with self._lock:
            task = self._load_unlocked(task_id)
            if task.get("owner"):
                existing_owner = task.get("owner") or "someone else"
                raise ValueError(
                    f"Task {task_id} has already been claimed by {existing_owner}"
                )
            if task.get("status") != "pending":
                raise ValueError(
                    f"Task {task_id} cannot be claimed because its status is '{task.get('status')}'"
                )
            if task.get("blockedBy"):
                raise ValueError(
                    f"Task {task_id} is blocked by {task['blockedBy']} and cannot be claimed yet"
                )
            required_role = self._normalize_role(str(task.get("requiredRole", "")))
            if required_role and required_role != cleaned_owner_role:
                claimant_role = cleaned_owner_role or "unassigned"
                raise ValueError(
                    f"Task {task_id} requires role '{required_role}' and cannot be claimed by role '{claimant_role}'"
                )

            task["owner"] = cleaned_owner
            task["status"] = "in_progress"
            task["updatedAt"] = self._utc_now()
            self._save_unlocked(task)

        self._emit_event(
            "task.claimed",
            {
                "task_id": task_id,
                "owner": cleaned_owner,
                "owner_role": cleaned_owner_role,
                "required_role": str(task.get("requiredRole", "")),
            },
        )
        return self._render_task(task)

    def _render_section(self, title: str, tasks: list[dict[str, Any]]) -> list[str]:
        lines = [f"{title}:"]
        if not tasks:
            lines.append("  (none)")
            return lines

        for task in tasks:
            marker = TASK_STATUS_MARKERS.get(task["status"], "[?]")
            detail_parts = []
            if task.get("owner"):
                detail_parts.append(f"owner: {task['owner']}")
            if task.get("requiredRole"):
                detail_parts.append(f"required role: {task['requiredRole']}")
            if task.get("blockedBy"):
                detail_parts.append(f"blocked by: {task['blockedBy']}")
            suffix = f" ({'; '.join(detail_parts)})" if detail_parts else ""
            lines.append(f"  {marker} #{task['id']}: {task['subject']}{suffix}")
        return lines

    def _max_id(self) -> int:
        ids = []
        for path in self.dir.glob("task_*.json"):
            try:
                ids.append(int(path.stem.split("_")[1]))
            except (IndexError, ValueError):
                continue
        return max(ids) if ids else 0

    def _task_path(self, task_id: int) -> Path:
        return self.dir / f"task_{task_id}.json"

    def _load_unlocked(self, task_id: int) -> dict[str, Any]:
        path = self._task_path(task_id)
        if not path.exists():
            raise ValueError(f"Task {task_id} not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_all_unlocked(self) -> list[dict[str, Any]]:
        tasks = []
        for path in sorted(self.dir.glob("task_*.json"), key=self._task_sort_key):
            try:
                tasks.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return tasks

    def _save_unlocked(self, task: dict[str, Any]) -> None:
        path = self._task_path(int(task["id"]))
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(task, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp_path.replace(path)

    def _normalize_dependencies(
        self,
        task_id: int,
        dependencies: list[int],
    ) -> list[int]:
        normalized: list[int] = []
        seen: set[int] = set()

        for value in dependencies:
            dependency_id = int(value)
            if dependency_id == task_id:
                raise ValueError("A task cannot depend on itself")
            if dependency_id in seen:
                continue
            self._load_unlocked(dependency_id)
            if self._would_create_cycle(task_id, dependency_id):
                raise ValueError(
                    f"Adding dependency {dependency_id} -> {task_id} would create a cycle"
                )
            seen.add(dependency_id)
            normalized.append(dependency_id)

        return sorted(normalized)

    def _would_create_cycle(self, task_id: int, dependency_id: int) -> bool:
        stack = [dependency_id]
        visited: set[int] = set()

        while stack:
            current = stack.pop()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)

            try:
                current_task = self._load_unlocked(current)
            except ValueError:
                continue

            for next_dependency in current_task.get("blockedBy", []):
                stack.append(int(next_dependency))

        return False

    def _clear_dependency_unlocked(self, completed_id: int) -> int:
        cleared_count = 0
        for task in self._load_all_unlocked():
            dependencies = task.get("blockedBy", [])
            if completed_id not in dependencies:
                continue
            task["blockedBy"] = [
                dependency for dependency in dependencies if dependency != completed_id
            ]
            task["updatedAt"] = self._utc_now()
            self._save_unlocked(task)
            cleared_count += 1

        if cleared_count:
            self._emit_event(
                "task.dependencies.cleared",
                {
                    "completed_task_id": completed_id,
                    "cleared_count": cleared_count,
                },
            )
        return cleared_count

    @staticmethod
    def _task_sort_key(path: Path) -> int:
        try:
            return int(path.stem.split("_")[1])
        except (IndexError, ValueError):
            return 0

    @staticmethod
    def _render_task(task: dict[str, Any]) -> str:
        return json.dumps(task, indent=2, ensure_ascii=False)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_role(role: str) -> str:
        return role.strip().lower()

    def _emit_event(self, event_type: str, payload: dict[str, object]) -> None:
        try:
            self.event_sink.emit(event_type, payload)
        except Exception:
            return
