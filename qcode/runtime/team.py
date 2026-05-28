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
        self._heartbeat: Dict[str, Dict[str, object]] = {}  # name -> {ts, phase, detail}
        self._activity_log: Dict[str, List[Dict[str, object]]] = {}  # name -> [{ts, action, detail}]
        self._max_activity_entries = 20
        self._workflow_dir = team_dir / "workflow"
        self._workflow_dir.mkdir(parents=True, exist_ok=True)
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
        session = self.load_checkpoint(name) or ConversationSession()
        idle_mode = "autonomous"
        consecutive_failures = 0
        max_consecutive_failures = 3
        run_timeout = 120.0  # Hard timeout for a single engine run

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
            self._update_heartbeat(name, "starting_engine")
            engine = self.engine_factory(name, role)

            # Log tool calls to activity feed
            def _on_response_event(event):
                if hasattr(event, 'tool_call') and event.tool_call:
                    tc = event.tool_call
                    fn_name = tc.get("function", {}).get("name", "") if isinstance(tc, dict) else getattr(tc, 'name', '')
                    if fn_name:
                        self._log_activity(name, "tool_call", fn_name)
                elif hasattr(event, 'event_type'):
                    et = str(event.event_type)
                    if 'TEXT' in et:
                        pass  # Skip text deltas to reduce noise
                    elif 'DONE' in et or 'CREATED' in et:
                        self._log_activity(name, "model_response", et)
            engine.set_response_event_handler(_on_response_event)

            # Run engine in a worker thread
            exc_holder: list[Optional[BaseException]] = [None]
            def _run_engine() -> None:
                try:
                    engine.run(
                        session,
                        max_iterations=self.max_iterations,
                        timeout_seconds=run_timeout - 10,
                    )
                except BaseException as exc:
                    exc_holder[0] = exc

            worker = threading.Thread(target=_run_engine, daemon=True)
            worker.start()

            # Watchdog: poll every 5s, force-cancel after run_timeout
            cancel_sent = False
            deadline = time.monotonic() + run_timeout
            while worker.is_alive():
                elapsed = run_timeout - (deadline - time.monotonic()) if not cancel_sent else 0
                self._update_heartbeat(
                    name, "running",
                    f"elapsed={elapsed:.0f}s" + (" (cancelling)" if cancel_sent else ""),
                )
                worker.join(timeout=5.0)
                if not worker.is_alive():
                    break
                if time.monotonic() > deadline and not cancel_sent:
                    self._emit_event(
                        "team.teammate.hard_timeout",
                        {
                            "name": name,
                            "role": role,
                            "timeout_seconds": run_timeout,
                        },
                    )
                    self._update_heartbeat(name, "timeout_cancel", f"after {run_timeout:.0f}s")
                    # Force-cancel: close HTTP connection via provider
                    engine.request_cancel()
                    cancel_sent = True
                    # Give 15 more seconds for cancel to take effect
                    deadline = time.monotonic() + 15.0
                elif cancel_sent and time.monotonic() > deadline:
                    # Still stuck after cancel — abandon this run
                    self._emit_event(
                        "team.teammate.force_killed",
                        {"name": name, "role": role},
                    )
                    self._update_heartbeat(name, "force_killed")
                    break

            exc = exc_holder[0]
            if worker.is_alive():
                # Thread still alive after all timeouts — mark failure
                consecutive_failures += 1
                self._set_status(name, "idle")
                if consecutive_failures >= max_consecutive_failures:
                    consecutive_failures = 0
                continue

            if exc is not None:
                consecutive_failures += 1
                self._update_heartbeat(name, "error", str(exc)[:100])
                if isinstance(exc, RuntimeError):
                    self._emit_event(
                        "team.teammate.run_stopped",
                        {
                            "name": name,
                            "role": role,
                            "error": str(exc),
                            "consecutive_failures": consecutive_failures,
                        },
                    )
                else:
                    self._emit_event(
                        "team.teammate.failed",
                        {
                            "name": name,
                            "role": role,
                            "error": str(exc),
                            "consecutive_failures": consecutive_failures,
                        },
                    )
                if consecutive_failures >= max_consecutive_failures:
                    # Try checkpoint recovery before giving up
                    checkpoint = self.load_checkpoint(name)
                    if checkpoint and len(checkpoint) > len(session):
                        self._log_activity(name, "recovering_from_checkpoint")
                        session.replace_messages(checkpoint.messages)
                        consecutive_failures = 0
                        continue
                    # Notify lead that teammate is stuck
                    self.bus.send(
                        name, self.lead_name,
                        f"I'm stuck after {consecutive_failures} failures. Last error: {str(exc)[:200]}. Please review and provide guidance.",
                        msg_type="message",
                    )
                    self._set_status(name, "idle")
                    consecutive_failures = 0
                    continue
                break
            else:
                consecutive_failures = 0
                self._update_heartbeat(name, "completed")
                self.save_checkpoint(name, session)

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

        # Reset all 'working' teammates to 'idle' on startup
        # This prevents stuck teammates from previous sessions
        self._reset_working_on_startup()

    def _reset_working_on_startup(self) -> None:
        """Reset all non-idle teammates to 'idle' on startup."""
        with self._config_lock:
            changed = False
            for member in self._config.get("members", []):
                if member.get("status") != "idle":
                    member["status"] = "idle"
                    changed = True
            if changed:
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

    def _update_heartbeat(self, name: str, phase: str, detail: str = "") -> None:
        self._heartbeat[name] = {
            "ts": time.time(),
            "phase": phase,
            "detail": detail,
        }
        self._log_activity(name, phase, detail)

    def approve_plan(self, name: str) -> None:
        """Mark a teammate's plan as approved (workflow gate)."""
        flag = self._workflow_dir / f"{name}_plan_approved"
        flag.write_text(str(time.time()), encoding="utf-8")
        self._log_activity(name, "plan_approved")

    def is_plan_approved(self, name: str) -> bool:
        """Check if a teammate's plan has been approved."""
        flag = self._workflow_dir / f"{name}_plan_approved"
        return flag.exists()

    def clear_plan_approval(self, name: str) -> None:
        """Clear plan approval (e.g., on new task)."""
        flag = self._workflow_dir / f"{name}_plan_approved"
        if flag.exists():
            flag.unlink()

    def save_checkpoint(self, name: str, session) -> None:
        """Save session checkpoint after successful run."""
        checkpoint_dir = self.dir / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        path = checkpoint_dir / f"{name}.jsonl"
        try:
            session.save(checkpoint_dir)
            # Rename to teammate-specific name
            latest = sorted(checkpoint_dir.glob("*.jsonl"), reverse=True)
            if latest and latest[0].name != f"{name}.jsonl":
                latest[0].rename(path)
        except Exception:
            pass

    def load_checkpoint(self, name: str):
        """Load last checkpoint for a teammate, or return None."""
        checkpoint_dir = self.dir / "checkpoints"
        path = checkpoint_dir / f"{name}.jsonl"
        if not path.exists():
            return None
        try:
            from qcode.runtime.session import ConversationSession
            return ConversationSession.load(path)
        except Exception:
            return None

    def _log_activity(self, name: str, action: str, detail: str = "") -> None:
        if name not in self._activity_log:
            self._activity_log[name] = []
        log = self._activity_log[name]
        log.append({"ts": time.time(), "action": action, "detail": detail[:200]})
        # Keep only last N entries
        if len(log) > self._max_activity_entries:
            self._activity_log[name] = log[-self._max_activity_entries:]

    def check_stuck_teammates(self, timeout_seconds: float = 30.0) -> list[str]:
        """Check for teammates that are stuck in 'working' state.

        A teammate is considered stuck if:
        1. Status is 'working' AND
        2. Thread is not alive OR no activity for timeout_seconds
        """
        import time
        stuck = []
        now = time.time()

        with self._config_lock:
            for member in self._config["members"]:
                name = member["name"]
                status = member["status"]
                if status == "working":
                    thread = self._threads.get(name)
                    # Check if thread is dead
                    if thread is None or not thread.is_alive():
                        stuck.append(name)
                        continue

                    # Check if teammate has been working too long without output
                    # Check inbox for recent activity
                    inbox_path = self.dir / "inbox" / f"{name}.jsonl"
                    if inbox_path.exists():
                        mtime = inbox_path.stat().st_mtime
                        if now - mtime > timeout_seconds:
                            # No activity for too long
                            stuck.append(name)

        return stuck

    def reset_stuck_teammates(self, timeout_seconds: float = 30.0) -> list[str]:
        """Reset stuck teammates to idle status."""
        stuck = self.check_stuck_teammates(timeout_seconds)
        for name in stuck:
            self._set_status(name, "idle")
            self._emit_event(
                "team.teammate.reset",
                {
                    "name": name,
                    "reason": "stuck detection",
                },
            )
        return stuck

    def get_teammate_status(self, name: str) -> dict[str, object]:
        """Get detailed status of a teammate."""
        import time
        member = self.get_member(name)
        if member is None:
            return {"error": f"Unknown teammate '{name}'"}

        thread = self._threads.get(name)
        has_pending = self.bus.has_pending(name)

        # Check last activity
        inbox_path = self.dir / "inbox" / f"{name}.jsonl"
        last_activity = None
        if inbox_path.exists():
            mtime = inbox_path.stat().st_mtime
            last_activity = time.time() - mtime

        # Check if lead has pending messages from this teammate
        lead_inbox_path = self.dir / "inbox" / f"{self.lead_name}.jsonl"
        has_reply = False
        if lead_inbox_path.exists():
            try:
                content = lead_inbox_path.read_text(encoding="utf-8")
                if f'"from": "{name}"' in content:
                    has_reply = True
            except Exception:
                pass

        # Get recent activity (last 5 entries)
        activity = self._activity_log.get(name, [])[-5:]

        return {
            "name": name,
            "role": member.get("role", ""),
            "status": member.get("status", "unknown"),
            "thread_alive": thread.is_alive() if thread else False,
            "has_pending_messages": has_pending,
            "last_activity_seconds": last_activity,
            "has_reply_to_lead": has_reply,
            "heartbeat": self._heartbeat.get(name),
            "recent_activity": activity,
        }
