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

_MAX_EVIDENCE_OUTPUT_CHARS = 2000

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
        test_plan: str = "",
        requires_ui_check: Optional[bool] = None,
        task_id: Optional[int] = None,
        loop_id: str = "",
    ) -> dict[str, Any]:
        cleaned_owner = owner.strip()
        cleaned_subject = subject.strip()
        cleaned_tester = tester.strip() or "tester"
        cleaned_loop_id = loop_id.strip()
        cleaned_details = details.strip()
        cleaned_test_plan = test_plan.strip()

        if not cleaned_owner:
            raise ValueError("Verification owner is required")

        with self._lock:
            if cleaned_loop_id:
                record = self._load_unlocked(cleaned_loop_id)
                if record["owner"] != cleaned_owner:
                    raise ValueError(
                        f"Loop {cleaned_loop_id} belongs to '{record['owner']}', not '{cleaned_owner}'"
                    )
                if requires_ui_check is not None:
                    record["requiresUiCheck"] = bool(requires_ui_check)
                if "requiresUiCheck" not in record:
                    record["requiresUiCheck"] = False
                if cleaned_test_plan:
                    record["testPlan"] = cleaned_test_plan
                if not record.get("testPlan"):
                    raise ValueError("Test plan is required for verification requests")
                if task_id is not None:
                    record["taskId"] = int(task_id)
                if cleaned_subject:
                    record["subject"] = cleaned_subject
                if cleaned_tester:
                    record["tester"] = cleaned_tester
            else:
                if not cleaned_subject:
                    raise ValueError("Subject is required when starting a new verification loop")
                if not cleaned_test_plan:
                    raise ValueError("Test plan is required for verification requests")
                loop_id_value = uuid.uuid4().hex[:8]
                now = self._utc_now()
                record = {
                    "loopId": loop_id_value,
                    "subject": cleaned_subject,
                    "owner": cleaned_owner,
                    "tester": cleaned_tester,
                    "lead": self.lead_name,
                    "testPlan": cleaned_test_plan,
                    "requiresUiCheck": bool(requires_ui_check),
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
                "evidence": [],
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

    def record_evidence(
        self,
        loop_id: str,
        reporter: str,
        evidence_type: str = "",
        command: str = "",
        output: str = "",
        url: str = "",
        exit_code: Optional[int] = None,
        notes: str = "",
    ) -> dict[str, Any]:
        cleaned_loop_id = loop_id.strip()
        cleaned_reporter = reporter.strip()
        cleaned_type = evidence_type.strip().lower() or "command"
        cleaned_command = command.strip()
        cleaned_output = output.strip()
        cleaned_url = url.strip()
        cleaned_notes = notes.strip()

        if not cleaned_loop_id:
            raise ValueError("Verification loop id is required")
        if not cleaned_reporter:
            raise ValueError("Reporter name is required")
        if not any([cleaned_command, cleaned_output, cleaned_url, cleaned_notes]):
            raise ValueError(
                "Evidence must include at least one of command, output, url, or notes"
            )

        with self._lock:
            record = self._load_unlocked(cleaned_loop_id)
            allowed_reporters = {
                str(record.get("owner", "")),
                str(record.get("tester", "")),
                str(record.get("lead", "")),
            }
            if cleaned_reporter not in allowed_reporters:
                raise ValueError(
                    f"Reporter '{cleaned_reporter}' is not authorized for loop {cleaned_loop_id}"
                )

            attempts = record.get("attempts") or []
            if not attempts:
                raise ValueError(f"Loop {cleaned_loop_id} has no pending verification attempts")

            attempt = dict(attempts[-1])
            if attempt.get("result") is not None:
                raise ValueError(
                    f"Loop {cleaned_loop_id} attempt {attempt.get('attempt')} already has a result"
                )

            evidence = list(attempt.get("evidence") or [])
            entry = {
                "type": cleaned_type,
                "command": cleaned_command,
                "output": self._normalize_evidence_output(cleaned_output),
                "url": cleaned_url,
                "exitCode": int(exit_code) if exit_code is not None else None,
                "notes": cleaned_notes,
                "reportedBy": cleaned_reporter,
                "reportedAt": self._utc_now(),
            }
            evidence.append(entry)
            attempt["evidence"] = evidence
            attempts[-1] = attempt
            record["attempts"] = attempts
            record["updatedAt"] = self._utc_now()
            self._save_unlocked(record)

        self._emit_event(
            "verification.evidence.recorded",
            {
                "loop_id": cleaned_loop_id,
                "attempt": attempt.get("attempt"),
                "reporter": cleaned_reporter,
                "evidence_type": cleaned_type,
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

            evidence = list(attempt.get("evidence") or [])
            if passed:
                tester_evidence = [
                    entry for entry in evidence if entry.get("reportedBy") == cleaned_tester
                ]
                if not tester_evidence:
                    raise ValueError(
                        "Passing verification requires evidence recorded by the tester. "
                        "Use record_test_evidence before reporting pass."
                    )
                requires_ui_check = bool(record.get("requiresUiCheck"))
                if requires_ui_check:
                    ui_evidence = [
                        entry for entry in tester_evidence
                        if str(entry.get("type", "")).lower() == "ui_check"
                    ]
                    if not ui_evidence:
                        raise ValueError(
                            "Passing frontend verification requires ui_check evidence. "
                            "Run ui_check and record_test_evidence with evidence_type='ui_check'."
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
                "evidence_count": len(evidence),
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
        test_plan = str(record.get("testPlan") or "").strip()
        plan_block = f"\nTest plan: {test_plan}" if test_plan else ""
        ui_flag = "yes" if record.get("requiresUiCheck") else "no"
        ui_block = f"\nRequires ui_check: {ui_flag}"
        task_id = record.get("taskId")
        task_block = f"\nTask: #{task_id}" if task_id is not None else ""
        return (
            f"Verification request loop={record['loopId']} attempt={attempt['attempt']}\n"
            f"Subject: {record['subject']}"
            f"{task_block}"
            f"{detail_block}"
            f"{plan_block}"
            f"{ui_block}"
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
        evidence_count = len(attempt.get("evidence") or [])
        return (
            f"Verification passed loop={record['loopId']} attempt={attempt['attempt']}\n"
            f"Subject: {record['subject']}\n"
            f"Summary: {result.get('summary', '')}\n"
            f"Evidence items: {evidence_count}"
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
    def _normalize_evidence_output(output: str) -> str:
        if not output:
            return ""
        if len(output) <= _MAX_EVIDENCE_OUTPUT_CHARS:
            return output
        return output[:_MAX_EVIDENCE_OUTPUT_CHARS] + "... (truncated)"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
