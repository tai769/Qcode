"""Event sinks for runtime telemetry."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Protocol


class EventSink(Protocol):
    """Minimal telemetry sink interface."""

    def emit(self, event_type: str, payload: Mapping[str, Any]) -> None:
        ...


class NullEventSink:
    """No-op telemetry sink."""

    def emit(self, event_type: str, payload: Mapping[str, Any]) -> None:
        return


class JsonlEventSink:
    """Append-only JSONL telemetry sink."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def emit(self, event_type: str, payload: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "payload": dict(payload),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write("\n")


class CompositeEventSink:
    """Fan-out sink that emits the same event to multiple sinks."""

    def __init__(self, sinks: Iterable[EventSink]) -> None:
        self.sinks = list(sinks)

    def emit(self, event_type: str, payload: Mapping[str, Any]) -> None:
        for sink in self.sinks:
            sink.emit(event_type, payload)


class CallbackEventSink:
    """In-memory sink that forwards events to a callback when present."""

    def __init__(
        self,
        callback: Optional[Callable[[str, Mapping[str, Any]], None]] = None,
    ) -> None:
        self.callback = callback

    def set_callback(
        self,
        callback: Optional[Callable[[str, Mapping[str, Any]], None]],
    ) -> None:
        self.callback = callback

    def emit(self, event_type: str, payload: Mapping[str, Any]) -> None:
        if self.callback is None:
            return
        self.callback(event_type, payload)


def build_event_sink(path: Optional[Path]) -> EventSink:
    if path is None:
        return NullEventSink()
    return JsonlEventSink(path)
