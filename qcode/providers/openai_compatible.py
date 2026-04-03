"""OpenAI-compatible chat-completions provider implementation."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterator, List, Optional

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


class OpenAICompatibleProvider(StreamingChatProvider):
    """SSE-first provider for chat-completions style APIs."""

    def __init__(self, config: AppConfig, system_prompt: str) -> None:
        self.config = config
        self.system_prompt = system_prompt

    def stream_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Iterator[ResponseEvent]:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency: requests. Install dependencies with `pip install -e .`."
            ) from exc

        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                *messages,
            ],
            "max_tokens": self.config.max_tokens,
            "stream": True,
        }

        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(
                f"{self.config.api_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.config.request_timeout,
                stream=True,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc

        if response.status_code != 200:
            body = decode_response_text(response)[:1000]
            raise RuntimeError(f"API Error: {response.status_code} - {body}")

        content_type = str(response.headers.get("content-type", "")).lower()
        if "text/event-stream" in content_type:
            yield from self._events_from_sse(iter_sse_events(response))
            return

        response_text = decode_response_text(response)
        if response_text.lstrip().startswith("event:"):
            yield from self._events_from_sse(parse_sse_text(response_text))
            return

        try:
            response_body = json.loads(response_text)
        except ValueError as exc:
            body_preview = response_text[:500].strip() or "<empty body>"
            raise RuntimeError(
                "API returned invalid JSON "
                f"(status={response.status_code}, content_type={content_type}, "
                f"body_preview={body_preview!r})"
            ) from exc

        yield from self._events_from_json_response(response_body)

    def _events_from_sse(
        self,
        payloads: Iterator[Dict[str, Any]] | List[Dict[str, Any]],
    ) -> Iterator[ResponseEvent]:
        saw_created = False
        response_id: Optional[str] = None
        tool_fragments: Dict[int, Dict[str, Any]] = {}
        completion_usage: Optional[UsageInfo] = None
        completion_emitted = False

        for payload in payloads:
            if not isinstance(payload, dict):
                continue

            payload_type = str(payload.get("type", "")).strip().lower()
            if payload_type == "sse.done":
                if response_id and not completion_emitted:
                    for index in sorted(tool_fragments):
                        tool_event = self._tool_call_from_fragment(tool_fragments[index], index)
                        if tool_event is not None:
                            yield ResponseEvent(
                                event_type=EventType.TOOL_CALL_DONE,
                                response_id=response_id,
                                tool_call=tool_event,
                            )
                    yield ResponseEvent(
                        event_type=EventType.COMPLETED,
                        response_id=response_id,
                        usage=completion_usage,
                    )
                return

            current_response_id = payload.get("id")
            if isinstance(current_response_id, str) and current_response_id and not saw_created:
                saw_created = True
                response_id = current_response_id
                yield ResponseEvent(
                    event_type=EventType.CREATED,
                    response_id=response_id,
                )

            choices = payload.get("choices")
            choice = choices[0] if isinstance(choices, list) and choices else {}
            if not isinstance(choice, dict):
                continue

            delta = choice.get("delta")
            if isinstance(delta, dict):
                content = delta.get("content")
                if isinstance(content, str) and content:
                    yield ResponseEvent(
                        event_type=EventType.OUTPUT_TEXT_DELTA,
                        response_id=response_id,
                        delta=content,
                    )

                streamed_tool_calls = delta.get("tool_calls")
                if isinstance(streamed_tool_calls, list):
                    for fragment in streamed_tool_calls:
                        if not isinstance(fragment, dict):
                            continue
                        index = int(fragment.get("index") or 0)
                        existing = dict(tool_fragments.get(index, {}))
                        if fragment.get("id"):
                            existing["id"] = fragment["id"]
                        function = fragment.get("function")
                        if isinstance(function, dict):
                            if isinstance(function.get("name"), str):
                                existing["name"] = (
                                    str(existing.get("name") or "") + function["name"]
                                )
                            if isinstance(function.get("arguments"), str):
                                existing["arguments"] = (
                                    str(existing.get("arguments") or "")
                                    + function["arguments"]
                                )
                                yield ResponseEvent(
                                    event_type=EventType.TOOL_CALL_DELTA,
                                    response_id=response_id,
                                    tool_call=ToolCallEvent(
                                        tool_call_id=str(existing.get("id") or f"call_{index}"),
                                        tool_name=str(existing.get("name") or ""),
                                        arguments_delta=function["arguments"],
                                    ),
                                )
                        tool_fragments[index] = existing

            finish_reason = choice.get("finish_reason")
            if finish_reason is not None:
                completion_emitted = True
                completion_usage = self._usage_from_payload(payload)
                if finish_reason == "tool_calls":
                    for index in sorted(tool_fragments):
                        tool_event = self._tool_call_from_fragment(tool_fragments[index], index)
                        if tool_event is not None:
                            yield ResponseEvent(
                                event_type=EventType.TOOL_CALL_DONE,
                                response_id=response_id,
                                tool_call=tool_event,
                            )
                yield ResponseEvent(
                    event_type=EventType.COMPLETED,
                    response_id=response_id,
                    usage=completion_usage,
                )
                return

    def _events_from_json_response(
        self,
        response_body: Dict[str, Any],
    ) -> Iterator[ResponseEvent]:
        response_id = response_body.get("id")
        if isinstance(response_id, str) and response_id:
            yield ResponseEvent(
                event_type=EventType.CREATED,
                response_id=response_id,
            )

        choices = response_body.get("choices")
        choice = choices[0] if isinstance(choices, list) and choices else {}
        if not isinstance(choice, dict):
            yield ResponseEvent(
                event_type=EventType.ERROR,
                response_id=response_id if isinstance(response_id, str) else None,
                error=ErrorInfo(
                    code="bad_response",
                    message=f"Unexpected chat-completions payload: {response_body}",
                    retryable=False,
                ),
            )
            return

        message = choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content:
                yield ResponseEvent(
                    event_type=EventType.OUTPUT_TEXT_DELTA,
                    response_id=response_id if isinstance(response_id, str) else None,
                    delta=content,
                )

            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list):
                for index, tool_call in enumerate(tool_calls):
                    if not isinstance(tool_call, dict):
                        continue
                    tool_event = self._tool_call_from_dict(tool_call, index)
                    if tool_event is not None:
                        yield ResponseEvent(
                            event_type=EventType.TOOL_CALL_DONE,
                            response_id=response_id if isinstance(response_id, str) else None,
                            tool_call=tool_event,
                        )

        yield ResponseEvent(
            event_type=EventType.COMPLETED,
            response_id=response_id if isinstance(response_id, str) else None,
            usage=self._usage_from_payload(response_body),
        )

    @staticmethod
    def _tool_call_from_fragment(
        fragment: Dict[str, Any],
        index: int,
    ) -> Optional[ToolCallEvent]:
        tool_name = str(fragment.get("name") or "").strip()
        if not tool_name:
            return None
        tool_call_id = str(fragment.get("id") or f"call_{index}")
        arguments = str(fragment.get("arguments") or "{}")
        return ToolCallEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            arguments_done=arguments,
        )

    @staticmethod
    def _tool_call_from_dict(
        tool_call: Dict[str, Any],
        index: int,
    ) -> Optional[ToolCallEvent]:
        function = tool_call.get("function")
        if not isinstance(function, dict):
            return None
        tool_name = str(function.get("name") or "").strip()
        if not tool_name:
            return None
        arguments = function.get("arguments", "{}")
        if isinstance(arguments, dict):
            arguments = stringify_json(arguments)
        return ToolCallEvent(
            tool_call_id=str(tool_call.get("id") or f"call_{index}"),
            tool_name=tool_name,
            arguments_done=str(arguments),
        )

    @staticmethod
    def _usage_from_payload(payload: Dict[str, Any]) -> Optional[UsageInfo]:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return None
        input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        return UsageInfo(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def create_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatResult:
        return super().create_chat_completion(messages, tools)
