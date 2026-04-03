"""Persistent teammate runtime with file-backed inboxes."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from qcode.runtime.engine import AgentEngine
from qcode.runtime.session import ConversationSession
from qcode.runtime.task_graph import TaskGraphManager
from qcode.team_defaults import (
    DEFAULT_LEAD_NAME,
    DEFAULT_LEAD_ROLE,
    DEFAULT_TEAM_MEMBERS,
    DEFAULT_TEAM_NAME,
)
from qcode.telemetry.events import EventSink, NullEventSink


VALID_TEAM_MESSAGE_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_request",
    "plan_approval_response",
}


class MessageBus:
    """Append-only JSONL inboxes with drain-on-read semantics."""

    def __init__(
        self,
        inbox_dir: Path,
        event_sink: Optional[EventSink] = None,
    ) -> None:
        self.dir = inbox_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.event_sink = event_sink or NullEventSink()
        self._lock = threading.Lock()

    def send(
        self,
        sender: str,
        recipient: str,
        content: str,
        msg_type: str = "message",
        extra: Optional[dict[str, object]] = None,
    ) -> str:
        if msg_type not in VALID_TEAM_MESSAGE_TYPES:
            valid = ", ".join(sorted(VALID_TEAM_MESSAGE_TYPES))
            return f"Error: Invalid type '{msg_type}'. Valid: {valid}"

        message: dict[str, object] = {
            "type": msg_type,
            "from": sender,
            "to": recipient,
            "content": content,
            "timestamp": time.time(),
        }
        if extra:
            message.update(extra)

        inbox_path = self.dir / f"{recipient}.jsonl"
        encoded = json.dumps(message, ensure_ascii=False)

        with self._lock:
            with inbox_path.open("a", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.write("\n")

        self._emit_event(
            "team.message.sent",
            {
                "from": sender,
                "to": recipient,
                "type": msg_type,
                "content_chars": len(content),
            },
        )
        return f"Sent {msg_type} to {recipient}"

    def read_inbox(self, name: str) -> list[dict[str, object]]:
        inbox_path = self.dir / f"{name}.jsonl"

        with self._lock:
            if not inbox_path.exists():
                return []

            raw = inbox_path.read_text(encoding="utf-8")
            inbox_path.write_text("", encoding="utf-8")

        messages: list[dict[str, object]] = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        if messages:
            self._emit_event(
                "team.inbox.drained",
                {
                    "name": name,
                    "count": len(messages),
                },
            )
        return messages

    def has_pending(self, name: str) -> bool:
        inbox_path = self.dir / f"{name}.jsonl"
        with self._lock:
            return inbox_path.exists() and inbox_path.stat().st_size > 0

    def broadcast(self, sender: str, content: str, recipients: list[str]) -> str:
        count = 0
        for recipient in recipients:
            if recipient == sender:
                continue
            result = self.send(sender, recipient, content, msg_type="broadcast")
            if not result.startswith("Error:"):
                count += 1
        return f"Broadcast to {count} teammates"

    def _emit_event(self, event_type: str, payload: dict[str, object]) -> None:
        try:
            self.event_sink.emit(event_type, payload)
        except Exception:
            return


TeamEngineFactory = Callable[[str, str], AgentEngine]


class TeammateManager:
    """Persistent named teammates coordinated through inbox files."""

    def __init__(
        self,
        team_dir: Path,
        bus: MessageBus,
        task_graph: TaskGraphManager,
        engine_factory: TeamEngineFactory,
        max_iterations: int = 50,
        idle_sleep_seconds: float = 0.5,
        idle_timeout_seconds: float = 60.0,
        idle_shutdown_enabled: bool = False,
        lead_name: str = DEFAULT_LEAD_NAME,
        event_sink: Optional[EventSink] = None,
    ) -> None:
        self.dir = team_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.dir / "config.json"
        self.bus = bus
        self.task_graph = task_graph
        self.engine_factory = engine_factory
        self.max_iterations = max_iterations
        self.idle_sleep_seconds = idle_sleep_seconds
        self.idle_timeout_seconds = idle_timeout_seconds
        self.idle_shutdown_enabled = idle_shutdown_enabled
        self.lead_name = lead_name
        self.event_sink = event_sink or NullEventSink()
        self._config_lock = threading.Lock()
        self._threads: Dict[str, threading.Thread] = {}
        self._load_or_create_config()

    def spawn(self, name: str, role: str, prompt: str) -> str:
        with self._config_lock:
            member = self._find_member_unlocked(name)
            if member is not None and member["status"] not in {"idle", "shutdown"}:
                return f"Error: '{name}' is currently {member['status']}"

            if member is None:
                member = {"name": name, "role": role, "status": "working"}
                self._config["members"].append(member)
            else:
                member["role"] = role
                member["status"] = "working"

            self._save_config_unlocked()

        self.bus.send(
            self.lead_name,
            name,
            prompt,
            msg_type="message",
            extra={"kind": "assignment"},
        )
        self._ensure_thread(name)
        self._emit_event(
            "team.teammate.spawned",
            {
                "name": name,
                "role": role,
            },
        )
        return f"Spawned teammate '{name}' (role: {role})"

    def send_message(
        self,
        sender: str,
        recipient: str,
        content: str,
        msg_type: str = "message",
        extra: Optional[dict[str, object]] = None,
    ) -> str:
        if msg_type not in VALID_TEAM_MESSAGE_TYPES:
            valid = ", ".join(sorted(VALID_TEAM_MESSAGE_TYPES))
            return f"Error: Invalid type '{msg_type}'. Valid: {valid}"

        if recipient != self.lead_name:
            member = self.get_member(recipient)
            if member is None:
                return f"Error: Unknown teammate '{recipient}'"
            if member["status"] == "shutdown":
                return f"Error: '{recipient}' is shutdown"
            if member["status"] == "idle":
                self._set_status(recipient, "working")
            self._ensure_thread(recipient)

        return self.bus.send(
            sender,
            recipient,
            content,
            msg_type=msg_type,
            extra=extra,
        )

    def read_inbox(self, name: str) -> list[dict[str, object]]:
        return self.bus.read_inbox(name)

    def broadcast(self, sender: str, content: str) -> str:
        recipients = self.member_names()
        for recipient in recipients:
            if recipient == sender:
                continue
            if self.get_member(recipient) is not None:
                self._ensure_thread(recipient)
                self._set_status_if_idle(recipient, "working")
        return self.bus.broadcast(sender, content, recipients)

    def list_all(self) -> str:
        with self._config_lock:
            members = list(self._config["members"])
            team_name = self._config["team_name"]

        lines = [
            f"Team: {team_name}",
            f"Lead: {self.lead_name} ({DEFAULT_LEAD_ROLE})",
        ]
        if not members:
            lines.append("  (no teammates)")
            return "\n".join(lines)

        for member in members:
            lines.append(
                f"  {member['name']} ({member['role']}): {member['status']}"
            )
        return "\n".join(lines)

    def mark_shutdown(self, name: str) -> None:
        with self._config_lock:
            member = self._find_member_unlocked(name)
            if member is None:
                return
            member["status"] = "shutdown"
            self._save_config_unlocked()

    def member_names(self) -> list[str]:
        with self._config_lock:
            return [member["name"] for member in self._config["members"]]

    def get_member(self, name: str) -> Optional[dict[str, str]]:
        with self._config_lock:
            member = self._find_member_unlocked(name)
            return dict(member) if member is not None else None

    def _ensure_thread(self, name: str) -> None:
        thread = self._threads.get(name)
        if thread is not None and thread.is_alive():
            return

        thread = threading.Thread(
            target=self._teammate_loop,
            args=(name,),
            daemon=True,
        )
        self._threads[name] = thread
        thread.start()

    def _teammate_loop(self, name: str) -> None:
        session = ConversationSession()
        idle_mode = "autonomous"

        while True:
            member = self.get_member(name)
            if member is None or member["status"] == "shutdown":
                break

            role = member["role"]
            if not self._resume_from_idle(name, role, session, idle_mode):
                self._emit_event(
                    "team.teammate.idle_timeout",
                    {
                        "name": name,
                        "role": role,
                        "shutdown_enabled": self.idle_shutdown_enabled,
                    },
                )
                if self.idle_shutdown_enabled:
                    self.mark_shutdown(name)
                    break
                idle_mode = "autonomous"
                continue

            self._set_status(name, "working")
            self._ensure_identity_context(session, name, role)
            engine = self.engine_factory(name, role)
            try:
                engine.run(session, max_iterations=self.max_iterations)
            except RuntimeError as exc:
                self._emit_event(
                    "team.teammate.run_stopped",
                    {
                        "name": name,
                        "role": role,
                        "error": str(exc),
                    },
                )
            except Exception as exc:
                self._emit_event(
                    "team.teammate.failed",
                    {
                        "name": name,
                        "role": role,
                        "error": str(exc),
                    },
                )
                break

            member = self.get_member(name)
            if member is None or member["status"] == "shutdown":
                break

            idle_mode = session.consume_idle_poll_request() or "autonomous"
            self._set_status_if_idle(name, "idle")

        self._emit_event(
            "team.teammate.exited",
            {
                "name": name,
            },
        )

    def _resume_from_idle(
        self,
        name: str,
        role: str,
        session: ConversationSession,
        idle_mode: str,
    ) -> bool:
        if self._inject_inbox_messages(name, session):
            return True

        allow_auto_claim = idle_mode != "approval_wait"
        if allow_auto_claim and self._auto_claim_task(name, role, session):
            return True

        self._set_status_if_idle(name, "idle")
        polls = max(1, int(self.idle_timeout_seconds / max(self.idle_sleep_seconds, 0.1)))
        for _ in range(polls):
            time.sleep(self.idle_sleep_seconds)
            if self._inject_inbox_messages(name, session):
                return True
            if allow_auto_claim and self._auto_claim_task(name, role, session):
                return True
        return False

    def _inject_inbox_messages(self, name: str, session: ConversationSession) -> bool:
        inbox = self.bus.read_inbox(name)
        if not inbox:
            return False

        for message in inbox:
            session.add_message(
                {
                    "role": "user",
                    "content": json.dumps(message, ensure_ascii=False),
                }
            )
        return True

    def _auto_claim_task(
        self,
        name: str,
        role: str,
        session: ConversationSession,
    ) -> bool:
        unclaimed = self.task_graph.scan_unclaimed(role)
        if not unclaimed:
            return False

        for task in unclaimed:
            try:
                self.task_graph.claim(int(task["id"]), name, owner_role=role)
            except ValueError:
                continue

            description = str(task.get("description", "")).strip()
            detail = f"\n{description}" if description else ""
            session.add_message(
                {
                    "role": "user",
                    "content": (
                        f"<auto-claimed>Task #{task['id']}: {task['subject']}"
                        f"{detail}</auto-claimed>"
                    ),
                }
            )
            session.add_message(
                {
                    "role": "assistant",
                    "content": f"Claimed task #{task['id']}. Continuing work.",
                }
            )
            self._emit_event(
                "team.teammate.auto_claimed",
                {
                    "name": name,
                    "task_id": int(task["id"]),
                },
            )
            return True
        return False

    def _ensure_identity_context(
        self,
        session: ConversationSession,
        name: str,
        role: str,
    ) -> None:
        if len(session) > 3:
            return

        team_name = self._team_name()
        identity_user = {
            "role": "user",
            "content": (
                f"<identity>You are '{name}', role: {role}, team: {team_name}. "
                "Continue your work.</identity>"
            ),
        }
        identity_assistant = {
            "role": "assistant",
            "content": f"I am {name}. Continuing.",
        }

        messages = list(session.messages)
        if messages:
            first_content = messages[0].get("content")
            if isinstance(first_content, str) and first_content.startswith("<identity>"):
                return

        session.replace_messages([identity_user, identity_assistant, *messages])

    def _team_name(self) -> str:
        with self._config_lock:
            return str(self._config.get("team_name", "default"))

    def _load_or_create_config(self) -> None:
        with self._config_lock:
            if self.config_path.exists():
                self._config = json.loads(
                    self.config_path.read_text(encoding="utf-8")
                )
                changed = self._merge_default_members_unlocked()
                if changed:
                    self._save_config_unlocked()
            else:
                self._config = {
                    "team_name": DEFAULT_TEAM_NAME,
                    "members": [dict(member) for member in DEFAULT_TEAM_MEMBERS],
                }
                self._save_config_unlocked()

    def _merge_default_members_unlocked(self) -> bool:
        changed = False
        members = self._config.get("members")
        if not isinstance(members, list):
            members = []
            self._config["members"] = members
            changed = True

        existing_names = {
            str(member.get("name"))
            for member in members
            if isinstance(member, dict) and member.get("name")
        }
        for default_member in DEFAULT_TEAM_MEMBERS:
            default_name = str(default_member.get("name", "")).strip()
            if not default_name or default_name in existing_names:
                continue
            members.append(dict(default_member))
            existing_names.add(default_name)
            changed = True

        if not self._config.get("team_name"):
            self._config["team_name"] = DEFAULT_TEAM_NAME
            changed = True

        return changed

    def _save_config_unlocked(self) -> None:
        self.config_path.write_text(
            json.dumps(self._config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _find_member_unlocked(self, name: str) -> Optional[dict[str, str]]:
        for member in self._config["members"]:
            if member["name"] == name:
                return member
        return None

    def _set_status(self, name: str, status: str) -> None:
        with self._config_lock:
            member = self._find_member_unlocked(name)
            if member is None:
                return
            if member["status"] == "shutdown":
                return
            member["status"] = status
            self._save_config_unlocked()

    def _set_status_if_idle(self, name: str, status: str) -> None:
        with self._config_lock:
            member = self._find_member_unlocked(name)
            if member is None:
                return
            if member["status"] == "shutdown":
                return
            if status == "idle" and self.bus.has_pending(name):
                return
            member["status"] = status
            self._save_config_unlocked()

    def _emit_event(self, event_type: str, payload: dict[str, object]) -> None:
        try:
            self.event_sink.emit(event_type, payload)
        except Exception:
            return
