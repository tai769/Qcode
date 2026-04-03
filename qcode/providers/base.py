"""Provider interfaces and canonical streaming events."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Protocol


Message = Dict[str, Any]
ToolSpec = Dict[str, Any]
JsonDict = Dict[str, Any]


class EventType(str, Enum):
    """Canonical model-stream events used inside the runtime."""

    CREATED = "created"
    OUTPUT_TEXT_DELTA = "output_text_delta"
    OUTPUT_TEXT_DONE = "output_text_done"
    REASONING_DELTA = "reasoning_delta"
    TOOL_CALL_DELTA = "tool_call_delta"
    TOOL_CALL_DONE = "tool_call_done"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass(frozen=True)
class ToolCallEvent:
    """Incremental or completed tool-call payload."""

    tool_call_id: str
    tool_name: str
    arguments_delta: Optional[str] = None
    arguments_done: Optional[str] = None


@dataclass(frozen=True)
class ErrorInfo:
    """Provider-level error surfaced through the event stream."""

    code: str
    message: str
    retryable: bool


@dataclass(frozen=True)
class UsageInfo:
    """Normalized token usage."""

    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class ResponseEvent:
    """Canonical event emitted by all providers."""

    event_type: EventType
    response_id: Optional[str] = None
    delta: Optional[str] = None
    tool_call: Optional[ToolCallEvent] = None
    usage: Optional[UsageInfo] = None
    error: Optional[ErrorInfo] = None


@dataclass(frozen=True)
class ChatResult:
    """Normalized model response used by the runtime engine."""

    message: Message
    finish_reason: Optional[str]
    raw_response: Optional[JsonDict] = None
    response_id: Optional[str] = None
    streamed_output: bool = False


class ProviderProtocolError(RuntimeError):
    """Raised when a provider stream violates the expected contract."""


class ProviderStreamError(RuntimeError):
    """Raised when the provider emits a structured error event."""

    def __init__(self, error: ErrorInfo) -> None:
        super().__init__(error.message)
        self.error = error


@dataclass
class _ToolCallAccumulator:
    tool_call_id: str
    tool_name: str = ""
    argument_chunks: List[str] = field(default_factory=list)
    arguments_done: Optional[str] = None

    def update(self, tool_call: ToolCallEvent) -> None:
        if tool_call.tool_name:
            self.tool_name = tool_call.tool_name
        if tool_call.arguments_delta:
            self.argument_chunks.append(tool_call.arguments_delta)
        if tool_call.arguments_done is not None:
            self.arguments_done = tool_call.arguments_done

    def to_tool_call(self) -> Optional[JsonDict]:
        if not self.tool_name:
            return None
        arguments = self.arguments_done
        if arguments is None:
            arguments = "".join(self.argument_chunks)
        if not arguments:
            arguments = "{}"
        return {
            "id": self.tool_call_id,
            "type": "function",
            "function": {
                "name": self.tool_name,
                "arguments": arguments,
            },
        }


class ResponseAccumulator:
    """Consumes canonical events and produces the engine-facing result."""

    def __init__(self) -> None:
        self.response_id: Optional[str] = None
        self.finish_reason: Optional[str] = None
        self.usage: Optional[UsageInfo] = None
        self.completed = False
        self._text_fragments: List[str] = []
        self._tool_order: List[str] = []
        self._tool_calls: Dict[str, _ToolCallAccumulator] = {}

    def consume(self, event: ResponseEvent) -> None:
        if event.response_id:
            self.response_id = event.response_id

        if event.event_type == EventType.ERROR:
            raise ProviderStreamError(
                event.error
                or ErrorInfo(
                    code="provider_error",
                    message="Provider emitted an error event",
                    retryable=False,
                )
            )

        if event.event_type in {EventType.OUTPUT_TEXT_DELTA, EventType.OUTPUT_TEXT_DONE} and event.delta:
            self._text_fragments.append(event.delta)
            return

        if event.event_type in {EventType.TOOL_CALL_DELTA, EventType.TOOL_CALL_DONE}:
            tool_call = event.tool_call
            if tool_call is None:
                return
            accumulator = self._tool_calls.get(tool_call.tool_call_id)
            if accumulator is None:
                accumulator = _ToolCallAccumulator(tool_call_id=tool_call.tool_call_id)
                self._tool_calls[tool_call.tool_call_id] = accumulator
                self._tool_order.append(tool_call.tool_call_id)
            accumulator.update(tool_call)
            return

        if event.event_type == EventType.COMPLETED:
            self.completed = True
            self.finish_reason = "tool_calls" if self._tool_order else "completed"
            self.usage = event.usage or self.usage

    def to_chat_result(self) -> ChatResult:
        if not self.completed:
            raise ProviderProtocolError("Stream ended without a completed event")

        text = "".join(self._text_fragments)
        message: Message = {
            "role": "assistant",
            "content": text,
        }
        if self.response_id:
            message["response_id"] = self.response_id

        tool_calls: List[JsonDict] = []
        for tool_call_id in self._tool_order:
            tool_call = self._tool_calls[tool_call_id].to_tool_call()
            if tool_call is not None:
                tool_calls.append(tool_call)
        if tool_calls:
            message["tool_calls"] = tool_calls

        raw_response: JsonDict = {}
        if self.response_id:
            raw_response["response_id"] = self.response_id
        if self.usage:
            raw_response["usage"] = {
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
            }

        return ChatResult(
            message=message,
            finish_reason=self.finish_reason,
            raw_response=raw_response or None,
            response_id=self.response_id,
            streamed_output=bool(text),
        )


class ChatProvider(Protocol):
    """Protocol implemented by chat-capable providers."""

    def stream_chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[ToolSpec]] = None,
    ) -> Iterator[ResponseEvent]:
        ...

    def create_chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[ToolSpec]] = None,
    ) -> ChatResult:
        ...


class StreamingChatProvider:
    """Mixin that builds final chat results from canonical events."""

    def create_chat_completion(
        self,
        messages: List[Message],
        tools: Optional[List[ToolSpec]] = None,
    ) -> ChatResult:
        accumulator = ResponseAccumulator()
        for event in self.stream_chat_completion(messages, tools):
            accumulator.consume(event)
        return accumulator.to_chat_result()


def stringify_json(data: Any) -> str:
    """Stable JSON serialization for tool arguments and content."""

    if isinstance(data, str):
        return data
    return json.dumps(data, ensure_ascii=False)
