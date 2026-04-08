"""Agent runtime engine."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from qcode.providers.base import ChatProvider, EventType, ResponseAccumulator, ResponseEvent
from qcode.runtime.context import AgentRunContext
from qcode.runtime.middleware import MiddlewarePipeline
from qcode.runtime.session import ConversationSession
from qcode.runtime.tool_executor import (
    StreamingToolExecutor,
    ToolCallExecutor,
    ToolExecutionResult,
    ToolOutputHandler,
)
from qcode.telemetry.events import EventSink, NullEventSink
from qcode.tools.registry import ToolRegistry


ResponseEventHandler = Callable[[ResponseEvent], None]


class AgentEngine:
    """Coordinates model calls, tool execution, and runtime hooks."""

    def __init__(
        self,
        provider: ChatProvider,
        tool_registry: ToolRegistry,
        event_sink: Optional[EventSink] = None,
        middleware: Optional[MiddlewarePipeline] = None,
        tool_output_handler: Optional[ToolOutputHandler] = None,
        response_event_handler: Optional[ResponseEventHandler] = None,
    ) -> None:
        self.provider = provider
        self.tool_registry = tool_registry
        self.event_sink = event_sink or NullEventSink()
        self.middleware = middleware or MiddlewarePipeline()
        self.tool_output_handler = tool_output_handler
        self.response_event_handler = response_event_handler
        self.tool_executor = ToolCallExecutor(
            tool_registry,
            event_sink=self.event_sink,
            output_handler=tool_output_handler,
        )
        self.streaming_tool_executor = StreamingToolExecutor(
            self.tool_executor,
            event_sink=self.event_sink,
        )

    def set_tool_output_handler(self, handler: ToolOutputHandler) -> None:
        self.tool_output_handler = handler
        self.tool_executor.output_handler = handler

    def set_response_event_handler(self, handler: ResponseEventHandler) -> None:
        self.response_event_handler = handler

    def run(
        self,
        session: ConversationSession,
        max_iterations: Optional[int] = None,
    ) -> None:
        run_context = AgentRunContext(session=session)
        iteration_count = 0

        self._emit_event(
            "run.started",
            {
                "session_id": session.session_id,
                "message_count": len(session),
            },
        )

        while True:
            if max_iterations is not None and iteration_count >= max_iterations:
                self._emit_event(
                    "run.max_iterations_reached",
                    {
                        "session_id": session.session_id,
                        "max_iterations": max_iterations,
                    },
                )
                raise RuntimeError(f"Max iterations reached ({max_iterations})")

            iteration_count += 1
            self.middleware.before_model_call(run_context)
            self._emit_event(
                "model.request",
                {
                    "session_id": session.session_id,
                    "message_count": len(session),
                    "tool_count": len(self.tool_registry),
                },
            )

            accumulator = ResponseAccumulator()
            self.streaming_tool_executor.begin_turn(session)
            try:
                for event in self.provider.stream_chat_completion(
                    session.messages,
                    self.tool_registry.definitions(),
                ):
                    self._handle_response_event(session, event)
                    self.streaming_tool_executor.observe_event(event)
                    accumulator.consume(event)
            except Exception:
                self.streaming_tool_executor.discard(wait_running=True)
                raise

            result = accumulator.to_chat_result()
            if result.response_id:
                session.set_last_response_id(result.response_id)
            if result.streamed_output:
                result.message["_streamed_output"] = True
            session.add_message(result.message)

            self._emit_event(
                "model.response",
                {
                    "session_id": session.session_id,
                    "finish_reason": result.finish_reason,
                    "has_tool_calls": bool(result.message.get("tool_calls")),
                    "response_id": result.response_id,
                },
            )

            if "tool_calls" not in result.message or result.finish_reason != "tool_calls":
                self._emit_event(
                    "assistant.message",
                    {
                        "session_id": session.session_id,
                        "has_content": bool(result.message.get("content")),
                    },
                )
                return

            tool_result = self.streaming_tool_executor.finalize(
                result.message["tool_calls"],
            )
            session.extend(tool_result.messages)

            if tool_result.used_todo:
                run_context.rounds_since_todo = 0
                run_context.todo_reminder_emitted_at_round = None
            else:
                run_context.rounds_since_todo += 1

            self._emit_event(
                "todo.rounds.updated",
                {
                    "session_id": session.session_id,
                    "rounds_since_todo": run_context.rounds_since_todo,
                    "used_todo": tool_result.used_todo,
                },
            )

            stop_reason = session.consume_run_stop_request()
            if stop_reason:
                self._emit_event(
                    "run.stopped",
                    {
                        "session_id": session.session_id,
                        "reason": stop_reason,
                    },
                )
                return

    def _handle_response_event(
        self,
        session: ConversationSession,
        event: ResponseEvent,
    ) -> None:
        self._emit_event(
            "model.response.event",
            {
                "session_id": session.session_id,
                "type": event.event_type.value,
                "response_id": event.response_id,
                "has_delta": bool(event.delta),
                "has_tool_call": event.tool_call is not None,
            },
        )
        if self.response_event_handler is not None:
            self.response_event_handler(event)

    def _emit_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        try:
            self.event_sink.emit(event_type, payload)
        except Exception:
            return
