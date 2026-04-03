"""Persistent coder/tester verification loops for multi-agent delivery."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import uuid
from typing import Any, Callable, Optional

from qcode.runtime.task_graph import TaskGraphManager
from qcode.telemetry.events import EventSink, NullEventSink


VALID_VERIFICATION_STATUSES = {
    "awaiting_test",
    "changes_requested",
    "passed",
}

MessageSender = Callable[[str, str, str, str, Optional[dict[str, object]]], str]


class VerificationLoopManager:
    """Tracks implementation->test->fix cycles with durable state."""

    def __init__(
        self,
        loop_dir: Path,
        task_graph: TaskGraphManager,
        lead_name: str,
        event_sink: Optional[EventSink] = None,
        message_sender: Optional[MessageSender] = None,
    ) -> None:
        self.dir = loop_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.task_graph = task_graph
        self.lead_name = lead_name.strip() or "ld"
        self.event_sink = event_sink or NullEventSink()
        self.message_sender = message_sender
        self._lock = threading.RLock()

    def set_message_sender(self, message_sender: MessageSender) -> None:
        self.message_sender = message_sender

    def request_verification(
        self,
        owner: str,
        subject: str = "",
        details: str = "",
        tester: str = "tester",
        task_id: Optional[int] = None,
        loop_id: str = "",
    ) -> dict[str, Any]:
        cleaned_owner = owner.strip()
        cleaned_subject = subject.strip()
        cleaned_tester = tester.strip() or "tester"
        cleaned_loop_id = loop_id.strip()
        cleaned_details = details.strip()

        if not cleaned_owner:
            raise ValueError("Verification owner is required")

        with self._lock:
            if cleaned_loop_id:
                record = self._load_unlocked(cleaned_loop_id)
                if record["owner"] != cleaned_owner:
                    raise ValueError(
                        f"Loop {cleaned_loop_id} belongs to '{record['owner']}', not '{cleaned_owner}'"
                    )
                if task_id is not None:
                    record["taskId"] = int(task_id)
                if cleaned_subject:
                    record["subject"] = cleaned_subject
                if cleaned_tester:
                    record["tester"] = cleaned_tester
            else:
                if not cleaned_subject:
                    raise ValueError("Subject is required when starting a new verification loop")
                loop_id_value = uuid.uuid4().hex[:8]
                now = self._utc_now()
                record = {
                    "loopId": loop_id_value,
                    "subject": cleaned_subject,
                    "owner": cleaned_owner,
                    "tester": cleaned_tester,
                    "lead": self.lead_name,
                    "taskId": int(task_id) if task_id is not None else None,
                    "status": "awaiting_test",
                    "createdAt": now,
                    "updatedAt": now,
                    "attempts": [],
                }

            next_attempt = len(record["attempts"]) + 1
            attempt = {
                "attempt": next_attempt,
                "submittedBy": cleaned_owner,
                "requestedAt": self._utc_now(),
                "details": cleaned_details,
                "result": None,
            }
            record["attempts"].append(attempt)
            record["status"] = "awaiting_test"
            record["updatedAt"] = self._utc_now()
            self._save_unlocked(record)

        task_id_value = record.get("taskId")
        if task_id_value is not None:
            try:
                self.task_graph.update(
                    int(task_id_value),
                    status="in_progress",
                    owner=cleaned_owner,
                )
            except ValueError:
                pass

        message = self._verification_request_message(record, attempt)
        self._send_message(
            cleaned_owner,
            str(record["tester"]),
            message,
            extra={
                "verification_loop_id": record["loopId"],
                "attempt": next_attempt,
                "task_id": record.get("taskId"),
            },
        )
        self._emit_event(
            "verification.requested",
            {
                "loop_id": record["loopId"],
                "attempt": next_attempt,
                "owner": cleaned_owner,
                "tester": str(record["tester"]),
                "task_id": record.get("taskId"),
            },
        )
        return record

    def report_result(
        self,
        loop_id: str,
        tester: str,
        passed: bool,
        summary: str,
        details: str = "",
    ) -> dict[str, Any]:
        cleaned_loop_id = loop_id.strip()
        cleaned_tester = tester.strip()
        cleaned_summary = summary.strip()
        cleaned_details = details.strip()
        if not cleaned_loop_id:
            raise ValueError("Verification loop id is required")
        if not cleaned_tester:
            raise ValueError("Tester name is required")
        if not cleaned_summary:
            raise ValueError("Verification summary is required")

        with self._lock:
            record = self._load_unlocked(cleaned_loop_id)
            if record["tester"] != cleaned_tester:
                raise ValueError(
                    f"Loop {cleaned_loop_id} belongs to tester '{record['tester']}', not '{cleaned_tester}'"
                )
            if not record.get("attempts"):
                raise ValueError(f"Loop {cleaned_loop_id} has no pending verification attempts")

            attempt = dict(record["attempts"][-1])
            if attempt.get("result") is not None:
                raise ValueError(
                    f"Loop {cleaned_loop_id} attempt {attempt['attempt']} already has a result"
                )

            attempt["result"] = {
                "passed": bool(passed),
                "summary": cleaned_summary,
                "details": cleaned_details,
                "reportedBy": cleaned_tester,
                "reportedAt": self._utc_now(),
            }
            record["attempts"][-1] = attempt
            record["status"] = "passed" if passed else "changes_requested"
            record["updatedAt"] = self._utc_now()
            self._save_unlocked(record)

        task_id_value = record.get("taskId")
        if task_id_value is not None:
            try:
                self.task_graph.update(
                    int(task_id_value),
                    status="completed" if passed else "in_progress",
                    owner=str(record["owner"]),
                )
            except ValueError:
                pass

        if passed:
            result_message = self._verification_pass_message(record, attempt)
            self._send_message(
                cleaned_tester,
                str(record["owner"]),
                result_message,
                extra={
                    "verification_loop_id": record["loopId"],
                    "attempt": attempt["attempt"],
                    "passed": True,
                },
            )
            self._send_message(
                cleaned_tester,
                str(record["lead"]),
                result_message,
                extra={
                    "verification_loop_id": record["loopId"],
                    "attempt": attempt["attempt"],
                    "passed": True,
                },
            )
        else:
            result_message = self._verification_fail_message(record, attempt)
            self._send_message(
                cleaned_tester,
                str(record["owner"]),
                result_message,
                extra={
                    "verification_loop_id": record["loopId"],
                    "attempt": attempt["attempt"],
                    "passed": False,
                },
            )

        self._emit_event(
            "verification.reported",
            {
                "loop_id": record["loopId"],
                "attempt": attempt["attempt"],
                "passed": bool(passed),
                "owner": str(record["owner"]),
                "tester": cleaned_tester,
                "task_id": record.get("taskId"),
            },
        )
        return record

    def get(self, loop_id: str) -> dict[str, Any]:
        with self._lock:
            return self._load_unlocked(loop_id.strip())

    def list_loops(
        self,
        status: str = "",
        owner: str = "",
        tester: str = "",
    ) -> list[dict[str, Any]]:
        cleaned_status = status.strip().lower()
        cleaned_owner = owner.strip()
        cleaned_tester = tester.strip()
        with self._lock:
            records = []
            for path in sorted(self.dir.glob("loop_*.json"), key=lambda current: current.name):
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                if cleaned_status and str(record.get("status", "")).lower() != cleaned_status:
                    continue
                if cleaned_owner and str(record.get("owner", "")) != cleaned_owner:
                    continue
                if cleaned_tester and str(record.get("tester", "")) != cleaned_tester:
                    continue
                records.append(record)
            return records

    def _send_message(
        self,
        sender: str,
        recipient: str,
        content: str,
        msg_type: str = "message",
        extra: Optional[dict[str, object]] = None,
    ) -> None:
        if self.message_sender is None:
            return
        result = self.message_sender(sender, recipient, content, msg_type, extra)
        if isinstance(result, str) and result.startswith("Error:"):
            raise ValueError(result)

    @staticmethod
    def _verification_request_message(record: dict[str, Any], attempt: dict[str, Any]) -> str:
        detail = str(attempt.get("details") or "").strip()
        detail_block = f"\nDetails: {detail}" if detail else ""
        task_id = record.get("taskId")
        task_block = f"\nTask: #{task_id}" if task_id is not None else ""
        return (
            f"Verification request loop={record['loopId']} attempt={attempt['attempt']}\n"
            f"Subject: {record['subject']}"
            f"{task_block}"
            f"{detail_block}"
        )

    @staticmethod
    def _verification_fail_message(record: dict[str, Any], attempt: dict[str, Any]) -> str:
        result = attempt.get("result") or {}
        details = str(result.get("details") or "").strip()
        detail_block = f"\nDetails: {details}" if details else ""
        return (
            f"Verification failed loop={record['loopId']} attempt={attempt['attempt']}\n"
            f"Subject: {record['subject']}\n"
            f"Summary: {result.get('summary', '')}"
            f"{detail_block}\n"
            "Please fix the issues and resubmit for verification."
        )

    @staticmethod
    def _verification_pass_message(record: dict[str, Any], attempt: dict[str, Any]) -> str:
        result = attempt.get("result") or {}
        return (
            f"Verification passed loop={record['loopId']} attempt={attempt['attempt']}\n"
            f"Subject: {record['subject']}\n"
            f"Summary: {result.get('summary', '')}"
        )

    def _path(self, loop_id: str) -> Path:
        return self.dir / f"loop_{loop_id}.json"

    def _load_unlocked(self, loop_id: str) -> dict[str, Any]:
        path = self._path(loop_id)
        if not path.exists():
            raise ValueError(f"Verification loop {loop_id} not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_unlocked(self, record: dict[str, Any]) -> None:
        path = self._path(str(record["loopId"]))
        temp = path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(record, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp.replace(path)

    def _emit_event(self, event_type: str, payload: dict[str, object]) -> None:
        try:
            self.event_sink.emit(event_type, payload)
        except Exception:
            return

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
