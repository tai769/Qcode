"""Subagent execution with fresh conversation context."""

from typing import Callable, Optional

from qcode.runtime.engine import AgentEngine
from qcode.runtime.session import ConversationSession
from qcode.telemetry.events import EventSink, NullEventSink


EngineFactory = Callable[[], AgentEngine]


class SubagentRunner:
    """Runs a child agent in a fresh session and returns only its summary."""

    def __init__(
        self,
        engine_factory: EngineFactory,
        max_iterations: int = 30,
        event_sink: Optional[EventSink] = None,
    ) -> None:
        self.engine_factory = engine_factory
        self.max_iterations = max_iterations
        self.event_sink = event_sink or NullEventSink()

    def run(
        self,
        prompt: str,
        description: str = "subtask",
        parent_session_id: Optional[str] = None,
    ) -> str:
        session = ConversationSession()
        session.add_user_text(prompt)

        self._emit_event(
            "subagent.started",
            {
                "parent_session_id": parent_session_id,
                "child_session_id": session.session_id,
                "description": description,
            },
        )

        engine = self.engine_factory()
        try:
            engine.run(session, max_iterations=self.max_iterations)
        except RuntimeError as exc:
            summary = f"Subagent stopped: {exc}"
            self._emit_event(
                "subagent.failed",
                {
                    "parent_session_id": parent_session_id,
                    "child_session_id": session.session_id,
                    "error": str(exc),
                },
            )
            return summary

        summary = session.last_assistant_content() or "(no summary)"
        self._emit_event(
            "subagent.completed",
            {
                "parent_session_id": parent_session_id,
                "child_session_id": session.session_id,
                "summary_chars": len(summary),
            },
        )
        return summary

    def _emit_event(self, event_type: str, payload: dict[str, object]) -> None:
        try:
            self.event_sink.emit(event_type, payload)
        except Exception:
            return
