"""Conversation session state."""

from typing import Iterable, Optional
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
