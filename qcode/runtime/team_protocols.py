"""Structured request-response protocols for team coordination."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import uuid
from typing import Any, Optional

from qcode.telemetry.events import EventSink, NullEventSink


VALID_PROTOCOL_KINDS = {"shutdown", "plan_approval"}
VALID_PROTOCOL_STATUSES = {"pending", "approved", "rejected"}


class TeamProtocolManager:
    """Persistent request-response tracker keyed by request_id."""

    def __init__(
        self,
        protocol_dir: Path,
        event_sink: Optional[EventSink] = None,
    ) -> None:
        self.dir = protocol_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.event_sink = event_sink or NullEventSink()
        self._lock = threading.RLock()

    def create_request(
        self,
        kind: str,
        requester: str,
        target: str,
        content: str = "",
        payload: Optional[dict[str, object]] = None,
    ) -> dict[str, Any]:
        normalized_kind = kind.strip().lower()
        if normalized_kind not in VALID_PROTOCOL_KINDS:
            valid = ", ".join(sorted(VALID_PROTOCOL_KINDS))
            raise ValueError(f"Invalid protocol kind '{kind}'. Valid: {valid}")

        request_id = uuid.uuid4().hex[:8]
        now = self._utc_now()
        record = {
            "request_id": request_id,
            "kind": normalized_kind,
            "requester": requester,
            "target": target,
            "status": "pending",
            "content": content,
            "payload": dict(payload or {}),
            "response": None,
            "createdAt": now,
            "updatedAt": now,
        }

        with self._lock:
            self._save_unlocked(record)

        self._emit_event(
            "team.protocol.created",
            {
                "request_id": request_id,
                "kind": normalized_kind,
                "requester": requester,
                "target": target,
            },
        )
        return record

    def respond(
        self,
        request_id: str,
        responder: str,
        approve: bool,
        content: str = "",
        payload: Optional[dict[str, object]] = None,
    ) -> dict[str, Any]:
        with self._lock:
            record = self._load_unlocked(request_id)
            if record["status"] != "pending":
                raise ValueError(
                    f"Request {request_id} is already {record['status']}"
                )

            record["status"] = "approved" if approve else "rejected"
            record["response"] = {
                "responder": responder,
                "approve": bool(approve),
                "content": content,
                "payload": dict(payload or {}),
                "respondedAt": self._utc_now(),
            }
            record["updatedAt"] = self._utc_now()
            self._save_unlocked(record)

        self._emit_event(
            "team.protocol.responded",
            {
                "request_id": request_id,
                "kind": record["kind"],
                "status": record["status"],
                "responder": responder,
            },
        )
        return record

    def get(self, request_id: str) -> dict[str, Any]:
        with self._lock:
            return self._load_unlocked(request_id)

    def list_requests(
        self,
        kind: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        normalized_kind = (kind or "").strip().lower()
        normalized_status = (status or "").strip().lower()

        with self._lock:
            records = []
            for path in sorted(self.dir.glob("request_*.json"), key=lambda current: current.name):
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                if normalized_kind and record.get("kind") != normalized_kind:
                    continue
                if normalized_status and record.get("status") != normalized_status:
                    continue
                records.append(record)
        return records

    def _path(self, request_id: str) -> Path:
        return self.dir / f"request_{request_id}.json"

    def _load_unlocked(self, request_id: str) -> dict[str, Any]:
        path = self._path(request_id)
        if not path.exists():
            raise ValueError(f"Protocol request {request_id} not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_unlocked(self, record: dict[str, Any]) -> None:
        path = self._path(record["request_id"])
        temp = path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(record, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp.replace(path)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _emit_event(self, event_type: str, payload: dict[str, object]) -> None:
        try:
            self.event_sink.emit(event_type, payload)
        except Exception:
            return
