"""Background command execution and notification delivery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import threading
import uuid
from typing import Dict, List, Optional

from qcode.telemetry.events import EventSink, NullEventSink
from qcode.utils.workspace import DANGEROUS_PATTERNS, MAX_OUTPUT_CHARS


@dataclass(frozen=True)
class BackgroundNotification:
    """A completed background task result ready to inject into the session."""

    session_id: str
    task_id: str
    status: str
    command: str
    result_preview: str


class BackgroundManager:
    """Runs shell commands in background threads and queues completion notices."""

    def __init__(
        self,
        workdir: Path,
        timeout_seconds: int = 300,
        result_preview_chars: int = 500,
        event_sink: Optional[EventSink] = None,
    ) -> None:
        self.workdir = workdir.resolve()
        self.timeout_seconds = timeout_seconds
        self.result_preview_chars = result_preview_chars
        self.event_sink = event_sink or NullEventSink()
        self.tasks: Dict[str, Dict[str, str]] = {}
        self._notification_queue: List[BackgroundNotification] = []
        self._lock = threading.Lock()

    def run(self, session_id: str, command: str) -> str:
        """Start a background thread and return immediately with a task id."""
        if any(pattern in command for pattern in DANGEROUS_PATTERNS):
            return "Error: Dangerous command blocked"

        task_id = uuid.uuid4().hex[:8]
        with self._lock:
            self.tasks[task_id] = {
                "session_id": session_id,
                "status": "running",
                "result": "",
                "command": command,
            }

        thread = threading.Thread(
            target=self._execute,
            args=(task_id, session_id, command),
            daemon=True,
        )
        thread.start()

        self._emit_event(
            "background.started",
            {
                "session_id": session_id,
                "task_id": task_id,
                "command": command[:120],
            },
        )
        return f"Background task {task_id} started: {command[:80]}"

    def check(self, session_id: str, task_id: Optional[str] = None) -> str:
        """Check one background task or list all tasks for this session."""
        with self._lock:
            if task_id:
                task = self.tasks.get(task_id)
                if task is None or task.get("session_id") != session_id:
                    return f"Error: Unknown background task {task_id}"
                result = task.get("result") or "(running)"
                return f"[{task['status']}] {task['command'][:60]}\n{result[: self.result_preview_chars]}"

            lines = []
            for current_task_id, task in self.tasks.items():
                if task.get("session_id") != session_id:
                    continue
                lines.append(
                    f"{current_task_id}: [{task['status']}] {task['command'][:60]}"
                )

        return "\n".join(lines) if lines else "No background tasks."

    def drain_notifications(self, session_id: str) -> List[BackgroundNotification]:
        """Return and remove all queued notifications for a session."""
        with self._lock:
            ready = [
                notification
                for notification in self._notification_queue
                if notification.session_id == session_id
            ]
            self._notification_queue = [
                notification
                for notification in self._notification_queue
                if notification.session_id != session_id
            ]

        if ready:
            self._emit_event(
                "background.notifications.drained",
                {
                    "session_id": session_id,
                    "count": len(ready),
                },
            )
        return ready

    def _execute(self, task_id: str, session_id: str, command: str) -> None:
        """Thread body: run the command, update state, queue a notification."""
        try:
            result = subprocess.run(
                ["bash", "-lc", command],
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            output = (result.stdout + result.stderr).strip() or "(no output)"
            if result.returncode != 0:
                output = f"{output}\n[exit code: {result.returncode}]"
            status = "completed"
        except subprocess.TimeoutExpired:
            output = f"Error: Timeout ({self.timeout_seconds}s)"
            status = "timeout"
        except Exception as exc:
            output = f"Error: {exc}"
            status = "error"

        output = output[:MAX_OUTPUT_CHARS]
        notification = BackgroundNotification(
            session_id=session_id,
            task_id=task_id,
            status=status,
            command=command[:80],
            result_preview=output[: self.result_preview_chars],
        )

        with self._lock:
            task = self.tasks.get(task_id)
            if task is not None:
                task["status"] = status
                task["result"] = output
            self._notification_queue.append(notification)

        self._emit_event(
            "background.completed",
            {
                "session_id": session_id,
                "task_id": task_id,
                "status": status,
                "output_chars": len(output),
            },
        )

    def _emit_event(self, event_type: str, payload: Dict[str, object]) -> None:
        try:
            self.event_sink.emit(event_type, payload)
        except Exception:
            return
