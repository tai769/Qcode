"""Conversation compaction services."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence, Set

from qcode.providers.base import ChatProvider
from qcode.runtime.context_budgeter import ContextBudgetDecision
from qcode.runtime.session import ConversationSession
from qcode.runtime.types import Message
from qcode.telemetry.events import EventSink, NullEventSink


SUMMARY_MAX_INPUT_CHARS = 80000
SUMMARY_MAX_OUTPUT_CHARS = 2000
PRESERVE_RESULT_TOOLS: Set[str] = {"read_file"}
RECURSIVE_READ_PATH_MARKERS = (
    "/.transcripts/",
    ".transcripts/",
    "/.team/inbox/",
    ".team/inbox/",
)


class ConversationCompactor:
    """Applies layered context compaction to a conversation session."""

    def __init__(
        self,
        summary_provider: ChatProvider,
        transcript_dir: Path,
        token_threshold: int = 50000,
        keep_recent_tool_results: int = 3,
        summary_ratio: float = 0.3,
        preserve_result_tools: Optional[Set[str]] = None,
        event_sink: Optional[EventSink] = None,
    ) -> None:
        self.summary_provider = summary_provider
        self.transcript_dir = transcript_dir
        self.token_threshold = token_threshold
        self.keep_recent_tool_results = keep_recent_tool_results
        self.summary_ratio = min(max(summary_ratio, 0.05), 0.95)
        self.preserve_result_tools = preserve_result_tools or PRESERVE_RESULT_TOOLS
        self.event_sink = event_sink or NullEventSink()

    def estimate_tokens(self, messages: Sequence[Message]) -> int:
        serialized = json.dumps(list(messages), default=str, ensure_ascii=False)
        return len(serialized) // 4

    def should_auto_compact(self, session: ConversationSession) -> bool:
        return self.estimate_tokens(session.messages) > self.token_threshold

    def micro_compact(self, session: ConversationSession) -> bool:
        tool_messages = self._tool_messages(session.messages)
        if len(tool_messages) <= self.keep_recent_tool_results:
            return False

        tool_metadata_map = self._tool_call_metadata_map(session.messages)
        compacted = False
        candidate_tool_messages = (
            tool_messages
            if self.keep_recent_tool_results <= 0
            else tool_messages[:-self.keep_recent_tool_results]
        )

        for tool_message in candidate_tool_messages:
            content = tool_message.get("content")
            if not isinstance(content, str) or len(content) <= 100:
                continue

            tool_metadata = tool_metadata_map.get(
                str(tool_message.get("tool_call_id") or ""),
                {},
            )
            tool_name = str(tool_metadata.get("tool_name") or "unknown")
            if self._should_redact_tool_result(tool_metadata, content):
                tool_message["content"] = self._redacted_tool_result_text(tool_metadata)
                compacted = True
                continue
            if tool_name in self.preserve_result_tools:
                continue

            tool_message["content"] = f"[Previous: used {tool_name}]"
            compacted = True

        if compacted:
            self._emit_event(
                "compaction.micro",
                {
                    "session_id": session.session_id,
                    "tool_messages": len(tool_messages),
                },
            )

        return compacted

    def compact(
        self,
        session: ConversationSession,
        trigger: str,
        focus: Optional[str] = None,
        decision: Optional[ContextBudgetDecision] = None,
    ) -> Path:
        before_tokens = self.estimate_tokens(session.messages)
        transcript_path = self._save_transcript(session)
        working_messages = self._strip_prior_memory_messages(session.messages)
        active_decision = decision or self._fallback_decision(before_tokens)
        preserved_recent = self._recent_messages_for_replay(
            working_messages,
            active_decision.recent_raw_budget_tokens,
        )
        history_messages = self._history_messages_for_summary(
            working_messages,
            preserved_recent,
        )
        summary = self._summarize_messages(
            history_messages,
            session,
            transcript_path,
            focus,
            preserved_recent,
            active_decision.summary_budget_tokens,
        )
        compacted_messages = self._build_compacted_messages(
            transcript_path,
            summary,
            preserved_recent,
        )
        compacted_messages = self._fit_to_budget(
            compacted_messages,
            active_decision.available_message_budget_tokens,
        )
        session.replace_messages(compacted_messages)
        after_tokens = self.estimate_tokens(session.messages)

        self._emit_event(
            "compaction.full",
            {
                "session_id": session.session_id,
                "trigger": trigger,
                "transcript_path": str(transcript_path),
                "summary_chars": len(summary),
                "before_tokens": before_tokens,
                "after_tokens": after_tokens,
                "preserved_messages": max(0, len(compacted_messages) - 1),
                "summary_budget_tokens": active_decision.summary_budget_tokens,
                "recent_raw_budget_tokens": active_decision.recent_raw_budget_tokens,
            },
        )
        return transcript_path

    def _save_transcript(self, session: ConversationSession) -> Path:
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        transcript_path = self.transcript_dir / f"transcript_{timestamp}.jsonl"
        tool_metadata_map = self._tool_call_metadata_map(session.messages)

        with transcript_path.open("w", encoding="utf-8") as handle:
            for message in session.messages:
                archived_message = self._archivable_message(message, tool_metadata_map)
                handle.write(json.dumps(archived_message, default=str, ensure_ascii=False))
                handle.write("\n")

        return transcript_path

    def _summarize_messages(
        self,
        messages: Sequence[Message],
        session: ConversationSession,
        transcript_path: Path,
        focus: Optional[str],
        preserved_recent: Sequence[Message],
        summary_budget_tokens: int,
    ) -> str:
        conversation_text = json.dumps(
            list(messages),
            default=str,
            ensure_ascii=False,
        )[-SUMMARY_MAX_INPUT_CHARS:]
        todo_snapshot = session.todo_manager.render()
        focus_text = (focus or "general continuity").strip()
        preserved_turn_text = (
            f"The most recent {len(preserved_recent)} message(s) remain verbatim after compaction. "
            "Do not waste summary budget repeating them unless they change the long-term plan."
            if preserved_recent
            else "No raw recent messages will be preserved after this compaction."
        )

        prompt = (
            "Summarize this coding-agent conversation for continuity. Preserve only the "
            "information needed to continue the work after compaction.\n\n"
            "Return concise Markdown with exactly these sections:\n"
            "## Goal\n"
            "## Done\n"
            "## Current State\n"
            "## Decisions\n"
            "## Pending\n"
            "## Risks\n\n"
            "Be concrete. Keep file paths, commands, API names, constraints, and user preferences "
            "that materially affect future work. Omit noisy logs and repeated chatter. "
            f"Target summary budget: about {max(1, summary_budget_tokens)} tokens.\n"
            f"Pay extra attention to: {focus_text}.\n\n"
            f"{preserved_turn_text}\n\n"
            f"Current todo state:\n{todo_snapshot}\n\n"
            f"Transcript path: {transcript_path}\n\n"
            f"Conversation excerpt:\n{conversation_text}"
        )

        result = self.summary_provider.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            tools=None,
        )
        content = result.message.get("content")
        if isinstance(content, str) and content.strip():
            max_chars = min(SUMMARY_MAX_OUTPUT_CHARS, max(200, summary_budget_tokens * 4))
            return content[:max_chars]
        return "Conversation compressed, but the summarizer returned no text."

    def _build_compacted_messages(
        self,
        transcript_path: Path,
        summary: str,
        preserved_recent: Sequence[Message],
    ) -> list[Message]:
        memory_message = {
            "role": "user",
            "content": (
                f"[Conversation compressed. Transcript: {transcript_path}]\n"
                "This block is continuity memory, not a new user request.\n\n"
                f"{summary}"
            ),
        }
        return [memory_message, *list(preserved_recent)]

    def _fit_to_budget(
        self,
        messages: list[Message],
        token_budget: int,
    ) -> list[Message]:
        if len(messages) <= 1:
            return messages

        target_tokens = max(1, token_budget)
        fitted_messages = list(messages)

        while self.estimate_tokens(fitted_messages) > target_tokens and len(fitted_messages) > 1:
            fitted_messages = self._drop_oldest_preserved_turn(fitted_messages)
            if len(fitted_messages) <= 1:
                break

        return fitted_messages

    def _recent_messages_for_replay(
        self,
        messages: Sequence[Message],
        raw_budget_tokens: int,
    ) -> list[Message]:
        if not messages or raw_budget_tokens <= 0:
            return []

        user_like_indices = [
            index
            for index, message in enumerate(messages)
            if self._is_user_like(message)
        ]
        if not user_like_indices:
            return self._tail_messages_by_budget(messages, raw_budget_tokens)

        preserved_start_index: Optional[int] = None
        consumed_tokens = 0
        turn_starts = user_like_indices

        for position in range(len(turn_starts) - 1, -1, -1):
            start_index = turn_starts[position]
            end_index = (
                turn_starts[position + 1]
                if position + 1 < len(turn_starts)
                else len(messages)
            )
            turn_messages = list(messages[start_index:end_index])
            turn_tokens = self.estimate_tokens(turn_messages)
            if preserved_start_index is None:
                preserved_start_index = start_index
                consumed_tokens += turn_tokens
                continue
            if consumed_tokens + turn_tokens > raw_budget_tokens:
                break
            preserved_start_index = start_index
            consumed_tokens += turn_tokens

        if preserved_start_index is None:
            return []
        return list(messages[preserved_start_index:])

    def _tail_messages_by_budget(
        self,
        messages: Sequence[Message],
        raw_budget_tokens: int,
    ) -> list[Message]:
        if raw_budget_tokens <= 0:
            return []

        preserved: list[Message] = []
        consumed_tokens = 0
        for block in self._tail_blocks(messages):
            block_tokens = self.estimate_tokens(block)
            if preserved and consumed_tokens + block_tokens > raw_budget_tokens:
                break
            preserved = [*block, *preserved]
            consumed_tokens += block_tokens
        return preserved

    def _tail_blocks(self, messages: Sequence[Message]) -> list[list[Message]]:
        blocks: list[list[Message]] = []
        index = len(messages) - 1
        while index >= 0:
            message = messages[index]
            role = str(message.get("role", "")).strip().lower()

            if role == "tool":
                assistant_index = self._matching_assistant_index(messages, index)
                if assistant_index is not None:
                    blocks.insert(0, list(messages[assistant_index : index + 1]))
                    index = assistant_index - 1
                    continue

            blocks.insert(0, [message])
            index -= 1

        return blocks

    def _matching_assistant_index(
        self,
        messages: Sequence[Message],
        tool_index: int,
    ) -> Optional[int]:
        tool_message = messages[tool_index]
        tool_call_id = str(tool_message.get("tool_call_id") or "").strip()
        if not tool_call_id:
            return None

        for index in range(tool_index - 1, -1, -1):
            message = messages[index]
            if str(message.get("role", "")).strip().lower() != "assistant":
                continue
            tool_calls = message.get("tool_calls")
            if not isinstance(tool_calls, list):
                continue
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                if str(tool_call.get("id") or "").strip() == tool_call_id:
                    return index
        return None

    def _fallback_decision(self, message_tokens: int) -> ContextBudgetDecision:
        available_message_budget_tokens = max(1, self.token_threshold)
        summary_budget_tokens = max(1, int(available_message_budget_tokens * self.summary_ratio))
        recent_raw_budget_tokens = max(0, available_message_budget_tokens - summary_budget_tokens)
        return ContextBudgetDecision(
            max_context_window=self.token_threshold,
            target_ratio=1.0,
            safety_margin_tokens=0,
            reserved_prompt_tokens=0,
            message_tokens=message_tokens,
            available_message_budget_tokens=available_message_budget_tokens,
            overflow_tokens=max(0, message_tokens - available_message_budget_tokens),
            should_compact=True,
            summary_budget_tokens=summary_budget_tokens,
            recent_raw_budget_tokens=recent_raw_budget_tokens,
        )

    @staticmethod
    def _history_messages_for_summary(
        messages: Sequence[Message],
        preserved_recent: Sequence[Message],
    ) -> list[Message]:
        if not preserved_recent:
            return list(messages)
        history_length = max(0, len(messages) - len(preserved_recent))
        return list(messages[:history_length])

    def _drop_oldest_preserved_turn(self, messages: Sequence[Message]) -> list[Message]:
        if len(messages) <= 1:
            return list(messages)

        preserved = list(messages[1:])
        next_user_index = next(
            (index for index, message in enumerate(preserved[1:], start=1) if self._is_user_like(message)),
            None,
        )
        if next_user_index is None:
            return [messages[0]]
        return [messages[0], *preserved[next_user_index:]]

    def _strip_prior_memory_messages(self, messages: Sequence[Message]) -> list[Message]:
        return [
            message
            for message in messages
            if not self._is_compaction_memory_message(message)
            and not self._is_goal_memory_message(message)
        ]

    @staticmethod
    def _is_user_like(message: Message) -> bool:
        return str(message.get("role", "")).strip().lower() in {"user", "developer"}

    @staticmethod
    def _is_compaction_memory_message(message: Message) -> bool:
        if str(message.get("role", "")).strip().lower() != "user":
            return False
        content = message.get("content")
        return isinstance(content, str) and content.startswith("[Conversation compressed.")

    @staticmethod
    def _is_goal_memory_message(message: Message) -> bool:
        if str(message.get("role", "")).strip().lower() != "user":
            return False
        content = message.get("content")
        return isinstance(content, str) and content.startswith("<goal>")

    @staticmethod
    def _tool_messages(messages: Sequence[Message]) -> list[Message]:
        return [message for message in messages if message.get("role") == "tool"]

    @staticmethod
    def _tool_call_metadata_map(messages: Iterable[Message]) -> dict[str, dict[str, Any]]:
        mapping: dict[str, dict[str, Any]] = {}
        for message in messages:
            if message.get("role") != "assistant":
                continue

            tool_calls = message.get("tool_calls")
            if not isinstance(tool_calls, list):
                continue

            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                tool_id = tool_call.get("id")
                function = tool_call.get("function", {})
                tool_name = function.get("name") if isinstance(function, dict) else None
                if tool_id and tool_name:
                    mapping[str(tool_id)] = {
                        "tool_name": str(tool_name),
                        "arguments": ConversationCompactor._tool_arguments(function),
                    }
        return mapping

    @staticmethod
    def _tool_arguments(function: Any) -> dict[str, Any]:
        if not isinstance(function, dict):
            return {}
        arguments = function.get("arguments")
        if isinstance(arguments, dict):
            return arguments
        if not isinstance(arguments, str) or not arguments.strip():
            return {}
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @classmethod
    def _archivable_message(
        cls,
        message: Message,
        tool_metadata_map: dict[str, dict[str, Any]],
    ) -> Message:
        if str(message.get("role", "")).strip().lower() != "tool":
            return message
        content = message.get("content")
        if not isinstance(content, str):
            return message
        tool_metadata = tool_metadata_map.get(str(message.get("tool_call_id") or ""), {})
        if not cls._should_redact_tool_result(tool_metadata, content):
            return message
        archived_message = dict(message)
        archived_message["content"] = cls._redacted_tool_result_text(tool_metadata)
        archived_message["_archived_redaction"] = "recursive_context_guard"
        return archived_message

    @classmethod
    def _should_redact_tool_result(
        cls,
        tool_metadata: dict[str, Any],
        content: str,
    ) -> bool:
        if not content:
            return False
        tool_name = str(tool_metadata.get("tool_name") or "").strip()
        if tool_name != "read_file":
            return False
        arguments = tool_metadata.get("arguments")
        if not isinstance(arguments, dict):
            return False
        path = str(arguments.get("path") or "").replace("\\", "/").strip()
        if not path:
            return False
        return any(marker in path for marker in RECURSIVE_READ_PATH_MARKERS)

    @staticmethod
    def _redacted_tool_result_text(tool_metadata: dict[str, Any]) -> str:
        tool_name = str(tool_metadata.get("tool_name") or "tool").strip() or "tool"
        arguments = tool_metadata.get("arguments")
        path = ""
        if isinstance(arguments, dict):
            path = str(arguments.get("path") or "").strip()
        if path:
            return (
                f"[Archived {tool_name} output omitted for {path} "
                "to avoid recursive context growth]"
            )
        return f"[Archived {tool_name} output omitted to avoid recursive context growth]"

    def _emit_event(self, event_type: str, payload: dict[str, object]) -> None:
        try:
            self.event_sink.emit(event_type, payload)
        except Exception:
            return
