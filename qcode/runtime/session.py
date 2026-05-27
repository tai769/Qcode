"""Conversation session state."""

import json
import time
from pathlib import Path
from typing import Iterable, List, Optional
from uuid import uuid4

from qcode.runtime.types import Message, Messages
from qcode.runtime.todos import TodoManager


class ConversationSession:
    """Mutable conversation state for a single harness session."""

    def __init__(
        self,
        messages: Optional[Iterable[Message]] = None,
        session_id: Optional[str] = None,
    ) -> None:
        self.session_id = session_id or uuid4().hex
        self._messages: Messages = list(messages or [])
        self.todo_manager = TodoManager()
        self._compaction_focus: Optional[str] = None
        self._run_stop_reason: Optional[str] = None
        self._idle_poll_mode: Optional[str] = None
        self._last_response_id: Optional[str] = None
        self._cumulative_input_tokens: int = 0
        self.created_at: float = time.time()
        self._recompute_last_response_id()

    @property
    def messages(self) -> Messages:
        return self._messages

    def add_message(self, message: Message) -> Message:
        response_id = message.get("response_id")
        if isinstance(response_id, str) and response_id:
            self._last_response_id = response_id
        self._messages.append(message)
        return message

    def add_user_text(self, text: str) -> Message:
        return self.add_message({"role": "user", "content": text})

    def extend(self, messages: Iterable[Message]) -> None:
        self._messages.extend(messages)

    def replace_messages(self, messages: Iterable[Message]) -> None:
        self._messages = list(messages)
        self._recompute_last_response_id()
        self._cumulative_input_tokens = 0

    def add_input_tokens(self, count: int) -> None:
        self._cumulative_input_tokens += count

    def request_compaction(self, focus: Optional[str] = None) -> None:
        cleaned_focus = (focus or "").strip()
        self._compaction_focus = cleaned_focus or "general continuity"

    def consume_compaction_request(self) -> Optional[str]:
        focus = self._compaction_focus
        self._compaction_focus = None
        return focus

    def request_run_stop(self, reason: Optional[str] = None) -> None:
        cleaned_reason = (reason or "").strip()
        self._run_stop_reason = cleaned_reason or "runtime stop requested"

    def consume_run_stop_request(self) -> Optional[str]:
        reason = self._run_stop_reason
        self._run_stop_reason = None
        return reason

    def request_idle_poll(self, mode: str = "autonomous") -> None:
        cleaned_mode = (mode or "").strip()
        self._idle_poll_mode = cleaned_mode or "autonomous"

    def consume_idle_poll_request(self) -> Optional[str]:
        mode = self._idle_poll_mode
        self._idle_poll_mode = None
        return mode

    @property
    def last_response_id(self) -> Optional[str]:
        return self._last_response_id

    def set_last_response_id(self, response_id: Optional[str]) -> None:
        cleaned = (response_id or "").strip() if isinstance(response_id, str) else ""
        self._last_response_id = cleaned or None

    def _recompute_last_response_id(self) -> None:
        self._last_response_id = None
        for message in reversed(self._messages):
            response_id = message.get("response_id")
            if isinstance(response_id, str) and response_id:
                self._last_response_id = response_id
                return

    def last_assistant_message(self) -> Optional[Message]:
        for message in reversed(self._messages):
            if message.get("role") == "assistant":
                return message
        return None

    def last_assistant_content(self) -> Optional[str]:
        message = self.last_assistant_message()
        if message is not None:
            content = message.get("content")
            if isinstance(content, str) and content:
                return content
        return None

    def __len__(self) -> int:
        return len(self._messages)

    def save(self, sessions_dir: Path) -> Path:
        sessions_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        path = sessions_dir / f"{ts}-{self.session_id[:8]}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            meta = {
                "type": "session_meta",
                "session_id": self.session_id,
                "created_at": self.created_at,
                "message_count": len(self._messages),
            }
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
            for msg in self._messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        return path

    @classmethod
    def load(cls, path: Path) -> "ConversationSession":
        messages: List[Message] = []
        session_id = None
        created_at = None
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if obj.get("type") == "session_meta":
                    session_id = obj.get("session_id")
                    created_at = obj.get("created_at")
                    continue
                messages.append(obj)
        session = cls(messages=messages, session_id=session_id)
        if created_at:
            session.created_at = created_at
        return session

    @staticmethod
    def find_latest(sessions_dir: Path) -> Optional[Path]:
        if not sessions_dir.exists():
            return None
        files = sorted(sessions_dir.glob("*.jsonl"), reverse=True)
        return files[0] if files else None

    @staticmethod
    def list_sessions(sessions_dir: Path, limit: int = 10) -> list[dict]:
        """List recent sessions with metadata and content preview."""
        if not sessions_dir.exists():
            return []

        sessions = []
        files = sorted(sessions_dir.glob("*.jsonl"), reverse=True)

        for path in files[:limit]:
            try:
                with path.open("r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line:
                        meta = json.loads(first_line)
                        if meta.get("type") == "session_meta":
                            # Read messages to get preview
                            messages = []
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    msg = json.loads(line)
                                    if msg.get("role") in ("user", "assistant"):
                                        messages.append(msg)
                                except json.JSONDecodeError:
                                    continue

                            # Get first user message as preview
                            preview = ""
                            for msg in messages:
                                if msg.get("role") == "user":
                                    content = msg.get("content", "")
                                    if isinstance(content, str) and content:
                                        preview = content[:100]
                                        if len(content) > 100:
                                            preview += "..."
                                        break

                            sessions.append({
                                "path": str(path),
                                "session_id": meta.get("session_id", ""),
                                "created_at": meta.get("created_at", 0),
                                "message_count": meta.get("message_count", 0),
                                "filename": path.name,
                                "preview": preview,
                            })
            except Exception:
                continue

        return sessions

    @staticmethod
    def format_session_time(timestamp: float) -> str:
        """Format timestamp to human readable time."""
        import time
        if timestamp:
            return time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))
        return "unknown"
