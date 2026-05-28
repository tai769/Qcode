"""Agent runtime engine."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Callable, Dict, Optional

from qcode.providers.base import ChatProvider, EventType, ResponseAccumulator, ResponseEvent
from qcode.runtime.context import AgentRunContext

_SENTINEL = object()  # Queue terminator
from qcode.runtime.middleware import MiddlewarePipeline
from qcode.runtime.session import ConversationSession
from qcode.runtime.tool_executor import (
    PermissionChecker,
    StreamingToolExecutor,
    ToolCallExecutor,
    ToolExecutionResult,
    ToolOutputHandler,
)
from qcode.telemetry.events import EventSink, NullEventSink
from qcode.tools.registry import ToolRegistry


# Tools that are "no-op" when they return empty results
_NOOP_TOOLS = {"read_inbox"}
_MAX_CONSECUTIVE_NOOPS = 5
_DEFAULT_RUN_TIMEOUT_SECONDS = 120.0


ResponseEventHandler = Callable[[ResponseEvent], None]


@dataclass(frozen=True)
class EngineEvent:
    """Event emitted by the async engine for UI consumption."""

    type: str  # "model_request", "tool_call", "tool_result", "text_delta", "done", "error"
    data: Dict[str, Any]


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
        permission_checker: Optional[PermissionChecker] = None,
        goal_store: Optional[Any] = None,
    ) -> None:
        self.provider = provider
        self.tool_registry = tool_registry
        self.event_sink = event_sink or NullEventSink()
        self.middleware = middleware or MiddlewarePipeline()
        self.tool_output_handler = tool_output_handler
        self.response_event_handler = response_event_handler
        self.goal_store = goal_store
        self.tool_executor = ToolCallExecutor(
            tool_registry,
            event_sink=self.event_sink,
            output_handler=tool_output_handler,
            permission_checker=permission_checker,
        )
        self.streaming_tool_executor = StreamingToolExecutor(
            self.tool_executor,
            event_sink=self.event_sink,
        )
        self._cancel_requested = False

    def request_cancel(self) -> None:
        """Request cancellation of the current run."""
        self._cancel_requested = True
        # Also cancel the provider's HTTP request if it supports it
        if hasattr(self.provider, 'request_cancel'):
            self.provider.request_cancel()

    def reset_cancel(self) -> None:
        """Reset cancellation flag."""
        self._cancel_requested = False
        # Reset the provider's cancel state if it supports it
        if hasattr(self.provider, 'reset_cancel'):
            self.provider.reset_cancel()

    def set_tool_output_handler(self, handler: ToolOutputHandler) -> None:
        self.tool_output_handler = handler
        self.tool_executor.output_handler = handler

    def set_response_event_handler(self, handler: ResponseEventHandler) -> None:
        self.response_event_handler = handler

    def run(
        self,
        session: ConversationSession,
        max_iterations: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        run_context = AgentRunContext(session=session)
        iteration_count = 0
        consecutive_noops = 0
        run_start = time.monotonic()
        effective_timeout = timeout_seconds or _DEFAULT_RUN_TIMEOUT_SECONDS

        self._emit_event(
            "run.started",
            {
                "session_id": session.session_id,
                "message_count": len(session),
            },
        )

        while True:
            # Check cancellation
            if self._cancel_requested:
                self._emit_event(
                    "run.cancelled",
                    {"session_id": session.session_id},
                )
                raise RuntimeError("Run cancelled by request")

            # Wall-clock timeout
            elapsed = time.monotonic() - run_start
            if elapsed > effective_timeout:
                self._emit_event(
                    "run.timeout",
                    {
                        "session_id": session.session_id,
                        "elapsed_seconds": round(elapsed, 1),
                        "timeout_seconds": effective_timeout,
                    },
                )
                raise RuntimeError(
                    f"Run timed out after {elapsed:.0f}s (limit: {effective_timeout:.0f}s)"
                )

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
            tools = self.tool_registry.definitions()
            try:
                for event in self.provider.stream_chat_completion(
                    session.messages,
                    tools,
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
            if result.usage:
                session.add_input_tokens(result.usage.input_tokens)

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

            # Detect consecutive no-op tool calls (e.g., empty read_inbox)
            turn_was_noop = self._check_noop_turn(result.message["tool_calls"], tool_result)
            if turn_was_noop:
                consecutive_noops += 1
            else:
                consecutive_noops = 0
            if consecutive_noops >= _MAX_CONSECUTIVE_NOOPS:
                self._emit_event(
                    "run.stuck_detected",
                    {
                        "session_id": session.session_id,
                        "consecutive_noops": consecutive_noops,
                    },
                )
                raise RuntimeError(
                    f"Stuck: {consecutive_noops} consecutive no-op tool calls "
                    f"(e.g., empty read_inbox). Teammate should use idle()."
                )

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

    def _check_noop_turn(
        self,
        tool_calls: list[dict],
        tool_result: ToolExecutionResult,
    ) -> bool:
        """Check if all tool calls in this turn were no-ops (empty results)."""
        if not tool_calls:
            return False
        results = tool_result.messages
        for tc, msg in zip(tool_calls, results):
            fn_name = tc.get("function", {}).get("name", "")
            if fn_name not in _NOOP_TOOLS:
                return False
            content = msg.get("content", "")
            if isinstance(content, str):
                # read_inbox returns "[]" when empty
                stripped = content.strip()
                if stripped and stripped != "[]":
                    return False
            else:
                return False
        return True

    async def run_events(
        self,
        session: ConversationSession,
        max_iterations: Optional[int] = None,
    ) -> AsyncGenerator[EngineEvent, None]:
        """Async generator that yields EngineEvents for UI consumption."""
        self._cancel_requested = False
        # Reset provider cancel state at the start of each run
        if hasattr(self.provider, 'reset_cancel'):
            self.provider.reset_cancel()
        run_context = AgentRunContext(session=session)
        iteration_count = 0

        yield EngineEvent("run_started", {
            "session_id": session.session_id,
            "message_count": len(session),
        })

        while True:
            if self._cancel_requested:
                yield EngineEvent("stopped", {"reason": "user_cancel"})
                return

            if max_iterations is not None and iteration_count >= max_iterations:
                yield EngineEvent("error", {
                    "message": f"Max iterations reached ({max_iterations})",
                })
                return

            iteration_count += 1
            self.middleware.before_model_call(run_context)

            yield EngineEvent("model_request", {
                "session_id": session.session_id,
                "message_count": len(session),
                "tool_count": len(self.tool_registry),
            })

            accumulator = ResponseAccumulator()
            self.streaming_tool_executor.begin_turn(session)

            # Run synchronous streaming in a thread to avoid blocking the event loop
            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def _producer():
                try:
                    tools = self.tool_registry.definitions()
                    for event in self.provider.stream_chat_completion(
                        session.messages,
                        tools,
                    ):
                        if self._cancel_requested:
                            break
                        loop.call_soon_threadsafe(queue.put_nowait, event)
                except Exception as exc:
                    loop.call_soon_threadsafe(queue.put_nowait, exc)
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, _SENTINEL)

            producer_task = asyncio.create_task(asyncio.to_thread(_producer))

            try:
                while True:
                    item = await queue.get()
                    if item is _SENTINEL:
                        break
                    if isinstance(item, Exception):
                        raise item
                    event: ResponseEvent = item

                    if self._cancel_requested:
                        await asyncio.to_thread(self.streaming_tool_executor.discard, wait_running=True)
                        yield EngineEvent("stopped", {"reason": "user_cancel"})
                        return

                    self._handle_response_event(session, event)
                    self.streaming_tool_executor.observe_event(event)
                    accumulator.consume(event)

                    if event.event_type == EventType.OUTPUT_TEXT_DELTA and event.delta:
                        yield EngineEvent("text_delta", {"text": event.delta})

                    if event.event_type == EventType.TOOL_CALL_DELTA and event.tool_call:
                        yield EngineEvent("tool_call_delta", {
                            "tool_call_id": event.tool_call.tool_call_id,
                            "tool_name": event.tool_call.tool_name,
                        })

                    if event.event_type == EventType.REASONING_DELTA and event.delta:
                        yield EngineEvent("reasoning_delta", {"text": event.delta})

            except Exception as exc:
                await asyncio.to_thread(self.streaming_tool_executor.discard, wait_running=True)
                yield EngineEvent("error", {"message": str(exc)})
                return
            finally:
                producer_task.cancel()

            result = accumulator.to_chat_result()
            if result.response_id:
                session.set_last_response_id(result.response_id)
            if result.streamed_output:
                result.message["_streamed_output"] = True
            session.add_message(result.message)
            if result.usage:
                session.add_input_tokens(result.usage.input_tokens)

            yield EngineEvent("model_response", {
                "finish_reason": result.finish_reason,
                "has_tool_calls": bool(result.message.get("tool_calls")),
                "response_id": result.response_id,
            })

            # Emit usage information if available
            if result.usage:
                yield EngineEvent("usage", {
                    "input_tokens": result.usage.input_tokens,
                    "output_tokens": result.usage.output_tokens,
                    "cache_creation_tokens": result.usage.cache_creation_tokens,
                    "cache_read_tokens": result.usage.cache_read_tokens,
                })

            if "tool_calls" not in result.message or result.finish_reason != "tool_calls":
                content = result.message.get("content", "")
                # Extract text from content blocks if needed (e.g. thinking + text)
                if isinstance(content, list):
                    text_parts = [
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    ]
                    content = "".join(text_parts)
                yield EngineEvent("assistant_message", {
                    "content": content,
                })
                return

            if self._cancel_requested:
                yield EngineEvent("stopped", {"reason": "user_cancel"})
                return

            tool_calls = result.message["tool_calls"]
            for tc in tool_calls:
                fn = tc.get("function", {})
                yield EngineEvent("tool_call", {
                    "tool_call_id": tc.get("id"),
                    "tool_name": fn.get("name"),
                    "arguments": fn.get("arguments"),
                })

            tool_result = await asyncio.to_thread(
                self.streaming_tool_executor.finalize,
                tool_calls,
            )
            session.extend(tool_result.messages)

            for i, tc in enumerate(tool_calls):
                fn = tc.get("function", {})
                msg = tool_result.messages[i] if i < len(tool_result.messages) else {}
                yield EngineEvent("tool_result", {
                    "tool_call_id": tc.get("id"),
                    "tool_name": fn.get("name"),
                    "content": msg.get("content", ""),
                })

            if tool_result.used_todo:
                run_context.rounds_since_todo = 0
                run_context.todo_reminder_emitted_at_round = None
            else:
                run_context.rounds_since_todo += 1

            stop_reason = session.consume_run_stop_request()
            if stop_reason:
                yield EngineEvent("stopped", {"reason": stop_reason})
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
