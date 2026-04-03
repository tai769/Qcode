"""Responses-API-compatible provider implementation."""

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


class ResponsesCompatibleProvider(StreamingChatProvider):
    """SSE-first provider for OpenAI-style Responses APIs."""

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

        effective_messages = list(messages)

        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "instructions": self.system_prompt,
            "input": self._messages_to_input(effective_messages),
            "max_output_tokens": self.config.max_tokens,
            "stream": True,
        }

        if tools:
            payload["tools"] = self._tools_to_responses(tools)

        if self.config.model_reasoning_effort:
            payload["reasoning"] = {
                "effort": self.config.model_reasoning_effort,
            }

        if self.config.model_verbosity:
            payload["text"] = {
                "verbosity": self.config.model_verbosity,
            }

        if self.config.disable_response_storage and not tools:
            payload["store"] = False

        try:
            response = self._post_responses_request(
                requests,
                headers=headers,
                payload=payload,
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

    def _post_responses_request(
        self,
        requests_module: Any,
        *,
        headers: Dict[str, str],
        payload: Dict[str, Any],
    ) -> Any:
        return requests_module.post(
            f"{self.config.api_base_url.rstrip('/')}/responses",
            headers=headers,
            json=payload,
            timeout=self.config.request_timeout,
            stream=True,
        )

    def _events_from_sse(
        self,
        payloads: Iterator[Dict[str, Any]] | List[Dict[str, Any]],
    ) -> Iterator[ResponseEvent]:
        function_items: Dict[str, Dict[str, Any]] = {}
        text_delta_keys_seen: set[str] = set()
        saw_completed = False

        for payload in payloads:
            if not isinstance(payload, dict):
                continue

            payload_type = str(payload.get("type", "")).strip().lower()
            response_id = self._response_id_from_payload(payload)

            if payload_type == "sse.done":
                continue

            if payload_type == "response.created":
                yield ResponseEvent(
                    event_type=EventType.CREATED,
                    response_id=response_id,
                )
                continue

            if payload_type in {
                "response.reasoning_summary_text.delta",
                "response.reasoning_text.delta",
                "response.reasoning.delta",
            }:
                delta = str(payload.get("delta") or "")
                if delta:
                    yield ResponseEvent(
                        event_type=EventType.REASONING_DELTA,
                        response_id=response_id,
                        delta=delta,
                    )
                continue

            if payload_type == "response.output_text.delta":
                delta = str(payload.get("delta") or "")
                if delta:
                    text_delta_keys_seen.add(self._text_stream_key(payload))
                    yield ResponseEvent(
                        event_type=EventType.OUTPUT_TEXT_DELTA,
                        response_id=response_id,
                        delta=delta,
                    )
                continue

            if payload_type == "response.output_text.done":
                if self._text_stream_key(payload) in text_delta_keys_seen:
                    continue
                text_value = self._extract_text(payload.get("text"))
                if text_value:
                    yield ResponseEvent(
                        event_type=EventType.OUTPUT_TEXT_DONE,
                        response_id=response_id,
                        delta=text_value,
                    )
                continue

            if payload_type in {"response.output_item.added", "response.output_item.done"}:
                item = payload.get("item")
                if not isinstance(item, dict):
                    continue
                item_type = str(item.get("type", "")).strip().lower()
                if item_type != "function_call":
                    continue

                item_key = str(item.get("id") or payload.get("item_id") or item.get("call_id") or "")
                if not item_key:
                    continue
                existing = dict(function_items.get(item_key, {}))
                existing.update(item)
                function_items[item_key] = existing

                if payload_type == "response.output_item.done":
                    tool_event = self._tool_call_from_item(
                        existing,
                        require_arguments=True,
                    )
                    if tool_event is not None:
                        yield ResponseEvent(
                            event_type=EventType.TOOL_CALL_DONE,
                            response_id=response_id,
                            tool_call=tool_event,
                        )
                continue

            if payload_type == "response.function_call_arguments.delta":
                item_id = str(payload.get("item_id") or payload.get("call_id") or "")
                delta = str(payload.get("delta") or "")
                if not item_id or not delta:
                    continue
                item = function_items.get(item_id, {})
                tool_call_id = str(item.get("call_id") or item.get("id") or item_id)
                tool_name = str(item.get("name") or payload.get("name") or "")
                yield ResponseEvent(
                    event_type=EventType.TOOL_CALL_DELTA,
                    response_id=response_id,
                    tool_call=ToolCallEvent(
                        tool_call_id=tool_call_id,
                        tool_name=tool_name,
                        arguments_delta=delta,
                    ),
                )
                continue

            if payload_type == "response.function_call_arguments.done":
                item_id = str(payload.get("item_id") or payload.get("call_id") or "")
                if not item_id:
                    continue
                item = dict(function_items.get(item_id, {}))
                if isinstance(payload.get("arguments"), str):
                    item["arguments"] = payload["arguments"]
                function_items[item_id] = item
                tool_event = self._tool_call_from_item(item, fallback_item_id=item_id)
                if tool_event is not None:
                    yield ResponseEvent(
                        event_type=EventType.TOOL_CALL_DONE,
                        response_id=response_id,
                        tool_call=tool_event,
                    )
                continue

            if payload_type == "response.completed":
                saw_completed = True
                yield ResponseEvent(
                    event_type=EventType.COMPLETED,
                    response_id=response_id,
                    usage=self._usage_from_payload(payload),
                )
                continue

            if payload_type in {"response.failed", "response.incomplete"}:
                error = payload.get("error") or payload.get("response") or payload
                yield ResponseEvent(
                    event_type=EventType.ERROR,
                    response_id=response_id,
                    error=ErrorInfo(
                        code="responses_error",
                        message=f"Responses API error: {error}",
                        retryable=False,
                    ),
                )
                return

        if not saw_completed:
            return

    @staticmethod
    def _text_stream_key(payload: Dict[str, Any]) -> str:
        item_id = str(payload.get("item_id") or payload.get("content_part_id") or "").strip()
        if item_id:
            return item_id
        output_index = str(payload.get("output_index") or "").strip()
        content_index = str(payload.get("content_index") or "").strip()
        if output_index or content_index:
            return f"{output_index}:{content_index}"
        return "default"

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

        status = str(response_body.get("status") or "").strip().lower()
        if status in {"failed", "incomplete"}:
            yield ResponseEvent(
                event_type=EventType.ERROR,
                response_id=response_id if isinstance(response_id, str) else None,
                error=ErrorInfo(
                    code="responses_error",
                    message=f"Responses API error: {response_body}",
                    retryable=False,
                ),
            )
            return

        output = response_body.get("output")
        output_items = output if isinstance(output, list) else []
        saw_text = False
        for item in output_items:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type", "")).strip().lower()
            if item_type == "function_call":
                tool_event = self._tool_call_from_item(item)
                if tool_event is not None:
                    yield ResponseEvent(
                        event_type=EventType.TOOL_CALL_DONE,
                        response_id=response_id if isinstance(response_id, str) else None,
                        tool_call=tool_event,
                    )
                continue
            if item_type != "message":
                continue
            content_items = item.get("content")
            if not isinstance(content_items, list):
                continue
            for content_item in content_items:
                if not isinstance(content_item, dict):
                    continue
                content_type = str(content_item.get("type", "")).strip().lower()
                if content_type not in {"output_text", "text"}:
                    continue
                text = self._extract_text(content_item.get("text"))
                if not text:
                    continue
                saw_text = True
                yield ResponseEvent(
                    event_type=EventType.OUTPUT_TEXT_DELTA,
                    response_id=response_id if isinstance(response_id, str) else None,
                    delta=text,
                )

        if not saw_text and isinstance(response_body.get("output_text"), str):
            yield ResponseEvent(
                event_type=EventType.OUTPUT_TEXT_DELTA,
                response_id=response_id if isinstance(response_id, str) else None,
                delta=str(response_body["output_text"]),
            )

        yield ResponseEvent(
            event_type=EventType.COMPLETED,
            response_id=response_id if isinstance(response_id, str) else None,
            usage=self._usage_from_response(response_body),
        )

    @staticmethod
    def _response_id_from_payload(payload: Dict[str, Any]) -> Optional[str]:
        response = payload.get("response")
        if isinstance(response, dict):
            response_id = response.get("id")
            if isinstance(response_id, str) and response_id:
                return response_id
        direct_response_id = payload.get("response_id") or payload.get("id")
        if isinstance(direct_response_id, str) and direct_response_id:
            return direct_response_id
        return None

    @staticmethod
    def _tool_call_from_item(
        item: Dict[str, Any],
        fallback_item_id: str = "",
        require_arguments: bool = False,
    ) -> Optional[ToolCallEvent]:
        tool_name = str(item.get("name") or "").strip()
        if not tool_name:
            return None
        tool_call_id = str(item.get("call_id") or item.get("id") or fallback_item_id).strip()
        if not tool_call_id:
            return None
        if require_arguments and "arguments" not in item:
            return None
        arguments = item.get("arguments", "{}")
        if isinstance(arguments, dict):
            arguments = stringify_json(arguments)
        return ToolCallEvent(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            arguments_done=str(arguments),
        )

    @staticmethod
    def _usage_from_payload(payload: Dict[str, Any]) -> Optional[UsageInfo]:
        response = payload.get("response")
        if isinstance(response, dict):
            return ResponsesCompatibleProvider._usage_from_response(response)
        return None

    @staticmethod
    def _usage_from_response(response: Dict[str, Any]) -> Optional[UsageInfo]:
        usage = response.get("usage")
        if not isinstance(usage, dict):
            return None
        input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        return UsageInfo(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _messages_to_input(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        converted: List[Dict[str, Any]] = []
        for message in messages:
            role = str(message.get("role", "")).strip().lower()
            content = message.get("content")

            if role == "tool":
                call_id = str(message.get("tool_call_id", "")).strip()
                if call_id:
                    converted.append(
                        {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": self._stringify_content(content),
                        }
                    )
                continue

            if role == "assistant":
                text = self._stringify_content(content)
                if text:
                    converted.append(
                        {
                            "type": "message",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": text,
                                }
                            ],
                        }
                    )

                tool_calls = message.get("tool_calls")
                if isinstance(tool_calls, list):
                    for tool_call in tool_calls:
                        if not isinstance(tool_call, dict):
                            continue
                        function = tool_call.get("function", {})
                        if not isinstance(function, dict):
                            continue
                        name = str(function.get("name", "")).strip()
                        if not name:
                            continue
                        arguments = function.get("arguments", "{}")
                        if isinstance(arguments, dict):
                            arguments = stringify_json(arguments)
                        converted.append(
                            {
                                "type": "function_call",
                                "call_id": str(
                                    tool_call.get("id") or function.get("name") or "call"
                                ),
                                "name": name,
                                "arguments": str(arguments),
                            }
                        )
                continue

            normalized_role = role if role in {"user", "assistant", "developer"} else "user"
            text = self._stringify_content(content)
            if not text:
                continue
            converted.append(
                {
                    "type": "message",
                    "role": normalized_role,
                    "content": [
                        {
                            "type": "input_text",
                            "text": text,
                        }
                    ],
                }
            )
        return converted

    @staticmethod
    def _tools_to_responses(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        converted: List[Dict[str, Any]] = []
        for tool in tools:
            if tool.get("type") != "function":
                continue
            function = tool.get("function", {})
            if not isinstance(function, dict):
                continue
            converted.append(
                {
                    "type": "function",
                    "name": function.get("name"),
                    "description": function.get("description", ""),
                    "parameters": function.get("parameters", {}),
                }
            )
        return converted

    @staticmethod
    def _extract_text(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            if isinstance(value.get("value"), str):
                return str(value["value"])
            if isinstance(value.get("text"), str):
                return str(value["text"])
        return ""

    @staticmethod
    def _stringify_content(content: Any) -> str:
        if content is None:
            return ""
        return stringify_json(content)

    def create_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatResult:
        return super().create_chat_completion(messages, tools)
