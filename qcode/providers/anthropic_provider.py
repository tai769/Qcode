"""Anthropic Messages API provider implementation."""

from __future__ import annotations

import json
import threading
from typing import Any, Callable, Dict, Iterator, List, Optional

from qcode.config import AppConfig
from qcode.providers.base import (
    ChatResult,
    ErrorInfo,
    EventType,
    ResponseEvent,
    StreamingChatProvider,
    ToolCallEvent,
    UsageInfo,
    stringify_json,
)
from qcode.providers.sse import decode_response_text, iter_sse_events, parse_sse_text


class AnthropicProvider(StreamingChatProvider):
    """Provider for Anthropic's native Messages API (/v1/messages)."""

    def __init__(self, config: AppConfig, system_prompt: str) -> None:
        self.config = config
        self.system_prompt = system_prompt
        self._cancel_event = threading.Event()
        self._current_response = None

    def request_cancel(self) -> None:
        """Request cancellation of the current HTTP request."""
        self._cancel_event.set()
        # Close the current response to interrupt the streaming
        if self._current_response is not None:
            try:
                self._current_response.close()
            except Exception:
                pass

    def reset_cancel(self) -> None:
        """Reset cancellation state for a new request."""
        self._cancel_event.clear()
        self._current_response = None

    def stream_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Iterator[ResponseEvent]:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Missing dependency: requests.") from exc

        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
        }

        # Build Anthropic-format messages
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls")
            tool_call_id = msg.get("tool_call_id")

            if role == "system":
                continue  # handled separately
            elif role == "tool":
                # Tool result message
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_call_id or "",
                        "content": content,
                    }],
                })
            elif role == "assistant" and tool_calls:
                # Assistant message with tool use
                content_blocks = []
                # Preserve existing content blocks (e.g. thinking) or wrap as text
                if isinstance(content, list):
                    content_blocks.extend(content)
                elif content:
                    content_blocks.append({"type": "text", "text": content})
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    try:
                        args = json.loads(fn.get("arguments", "{}"))
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": fn.get("name", ""),
                        "input": args,
                    })
                anthropic_messages.append({"role": "assistant", "content": content_blocks})
            elif role == "assistant" and isinstance(content, list):
                # Assistant message with content blocks (e.g. thinking + text)
                anthropic_messages.append({"role": "assistant", "content": content})
            else:
                anthropic_messages.append({"role": role, "content": content})

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": self.system_prompt,
            "messages": anthropic_messages,
            "stream": True,
        }

        # Convert OpenAI tool format to Anthropic format
        if tools:
            anthropic_tools = []
            for tool in tools:
                fn = tool.get("function", {})
                anthropic_tools.append({
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                })
            payload["tools"] = anthropic_tools

        base = self.config.api_base_url.rstrip("/")
        # Auto-detect if user already included /v1 in the URL
        if base.endswith("/v1"):
            url = f"{base}/messages"
        elif "/v1/" in base:
            url = f"{base}/messages"
        else:
            url = f"{base}/v1/messages"

        # Reset cancel state for this request
        self._cancel_event.clear()

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.config.request_timeout,
                stream=True,
            )
            self._current_response = response
        except requests.RequestException as exc:
            raise RuntimeError(f"Anthropic request failed: {exc}") from exc

        if self._cancel_event.is_set():
            response.close()
            return

        if response.status_code != 200:
            body = decode_response_text(response)[:1000]
            raise RuntimeError(f"Anthropic API Error: {response.status_code} - {body}")

        content_type = str(response.headers.get("content-type", "")).lower()
        if "text/event-stream" in content_type:
            yield from self._events_from_sse(iter_sse_events(response))
            return

        response_text = decode_response_text(response)
        try:
            response_body = json.loads(response_text)
        except ValueError:
            body_preview = response_text[:500]
            raise RuntimeError(f"Anthropic returned invalid JSON: {body_preview}")

        yield from self._events_from_json_response(response_body)

    def _events_from_sse(
        self, payloads: Iterator[Dict[str, Any]] | List[Dict[str, Any]],
    ) -> Iterator[ResponseEvent]:
        """Parse Anthropic SSE events into ResponseEvent stream."""
        response_id: Optional[str] = None
        current_tool_id: Optional[str] = None
        current_tool_name: Optional[str] = None
        tool_input_chunks: Dict[str, str] = {}
        content_text = ""

        for event_data in payloads:
            # Check cancel flag before processing each event
            if self._cancel_event.is_set():
                return
            event_type = event_data.get("type", "")

            if event_type == "message_start":
                message = event_data.get("message", {})
                response_id = message.get("id")
                yield ResponseEvent(
                    event_type=EventType.CREATED,
                    response_id=response_id,
                )

            elif event_type == "content_block_start":
                block = event_data.get("content_block", {})
                block_type = block.get("type")
                if block_type == "tool_use":
                    current_tool_id = block.get("id")
                    current_tool_name = block.get("name")
                    tool_input_chunks[current_tool_id] = ""

            elif event_type == "content_block_delta":
                delta = event_data.get("delta", {})
                delta_type = delta.get("type")

                if delta_type == "text_delta":
                    text = delta.get("text", "")
                    content_text += text
                    yield ResponseEvent(
                        event_type=EventType.OUTPUT_TEXT_DELTA,
                        response_id=response_id,
                        delta=text,
                    )

                elif delta_type == "input_json_delta":
                    partial = delta.get("partial_json", "")
                    if current_tool_id:
                        tool_input_chunks[current_tool_id] = tool_input_chunks.get(current_tool_id, "") + partial
                        yield ResponseEvent(
                            event_type=EventType.TOOL_CALL_DELTA,
                            response_id=response_id,
                            tool_call=ToolCallEvent(
                                tool_call_id=current_tool_id,
                                tool_name=current_tool_name or "",
                                arguments_delta=partial,
                            ),
                        )

                elif delta_type == "thinking_delta":
                    thinking = delta.get("thinking", "")
                    yield ResponseEvent(
                        event_type=EventType.REASONING_DELTA,
                        response_id=response_id,
                        delta=thinking,
                    )

            elif event_type == "content_block_stop":
                if current_tool_id:
                    full_args = tool_input_chunks.get(current_tool_id, "")
                    yield ResponseEvent(
                        event_type=EventType.TOOL_CALL_DONE,
                        response_id=response_id,
                        tool_call=ToolCallEvent(
                            tool_call_id=current_tool_id,
                            tool_name=current_tool_name or "",
                            arguments_done=full_args,
                        ),
                    )
                    current_tool_id = None
                    current_tool_name = None

            elif event_type == "message_delta":
                delta = event_data.get("delta", {})
                stop_reason = delta.get("stop_reason")
                usage = event_data.get("usage", {})
                yield ResponseEvent(
                    event_type=EventType.COMPLETED,
                    response_id=response_id,
                    usage=UsageInfo(
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                    ),
                )

            elif event_type == "message_stop":
                pass  # Already handled by message_delta

            elif event_type == "error":
                error = event_data.get("error", {})
                yield ResponseEvent(
                    event_type=EventType.ERROR,
                    response_id=response_id,
                    error=ErrorInfo(
                        code=error.get("type", "unknown"),
                        message=error.get("message", "Unknown error"),
                        retryable=False,
                    ),
                )

    def _events_from_json_response(self, body: Dict[str, Any]) -> Iterator[ResponseEvent]:
        """Parse a non-streaming Anthropic response."""
        response_id = body.get("id")
        yield ResponseEvent(event_type=EventType.CREATED, response_id=response_id)

        content = body.get("content", [])
        for block in content:
            block_type = block.get("type")
            if block_type == "text":
                yield ResponseEvent(
                    event_type=EventType.OUTPUT_TEXT_DELTA,
                    response_id=response_id,
                    delta=block.get("text", ""),
                )
            elif block_type == "tool_use":
                args_str = json.dumps(block.get("input", {}))
                yield ResponseEvent(
                    event_type=EventType.TOOL_CALL_DONE,
                    response_id=response_id,
                    tool_call=ToolCallEvent(
                        tool_call_id=block.get("id", ""),
                        tool_name=block.get("name", ""),
                        arguments_done=args_str,
                    ),
                )

        usage = body.get("usage", {})
        yield ResponseEvent(
            event_type=EventType.COMPLETED,
            response_id=response_id,
            usage=UsageInfo(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
            ),
        )
