"""SSE decoding helpers shared by provider implementations."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Iterator, List, Optional


def decode_response_text(response: Any) -> str:
    """Decode an HTTP response body as text, preferring UTF-8."""

    cached = getattr(response, "_content", None)
    if isinstance(cached, str):
        return cached
    if isinstance(cached, (bytes, bytearray)):
        return decode_bytes(bytes(cached), response=response)

    try:
        raw = getattr(response, "content", b"") or b""
    except Exception:
        raw = b""

    if isinstance(raw, str):
        return raw
    if isinstance(raw, bytearray):
        raw = bytes(raw)

    if not isinstance(raw, bytes):
        text = getattr(response, "text", "")
        return text if isinstance(text, str) else ""

    return decode_bytes(raw, response=response)


def decode_bytes(raw: bytes, response: Any | None = None) -> str:
    """Decode raw bytes with a small set of encoding fallbacks."""

    encodings: List[str] = ["utf-8", "utf-8-sig"]
    if response is not None:
        response_encoding = getattr(response, "encoding", None)
        if isinstance(response_encoding, str) and response_encoding:
            encodings.append(response_encoding)

    seen: set[str] = set()
    for encoding in encodings:
        normalized = encoding.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_sse_text(text: str) -> List[Dict[str, Any]]:
    """Parse a fully buffered SSE payload into JSON event objects."""

    return list(_parse_sse_lines(text.splitlines()))


def iter_sse_events(response: Any) -> Iterator[Dict[str, Any]]:
    """Yield parsed SSE JSON payloads from a streaming HTTP response."""

    try:
        if getattr(response, "raw", None) is None:
            raise AttributeError("Response.raw is unavailable")
        raw_lines = response.iter_lines(decode_unicode=False)
        decoded_lines = (
            decode_bytes(raw_line or b"", response=response)
            for raw_line in raw_lines
        )
        yield from _parse_sse_lines(decoded_lines)
    except AttributeError as exc:
        text = decode_response_text(response)
        if not text:
            raise RuntimeError(
                "SSE response could not be read from streaming handle or buffered body"
            ) from exc
        yield from parse_sse_text(text)


def _parse_sse_lines(lines: Iterable[str]) -> Iterator[Dict[str, Any]]:
    event_name: Optional[str] = None
    data_lines: List[str] = []

    def flush() -> Optional[Dict[str, Any]]:
        nonlocal event_name, data_lines
        if not data_lines:
            event_name = None
            return None
        payload_text = "\n".join(data_lines).strip()
        data_lines = []
        current_event_name = event_name
        event_name = None
        if not payload_text:
            return None
        if payload_text == "[DONE]":
            return {"type": "sse.done"}
        try:
            parsed = json.loads(payload_text)
        except ValueError:
            return {"type": current_event_name or "sse.unknown", "raw": payload_text}
        if not isinstance(parsed, dict):
            return None
        if current_event_name and not parsed.get("type"):
            parsed["type"] = current_event_name
        return parsed

    for raw_line in lines:
        line = raw_line.rstrip("\r")
        if not line:
            parsed = flush()
            if parsed is not None:
                yield parsed
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[6:].lstrip()
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    parsed = flush()
    if parsed is not None:
        yield parsed
