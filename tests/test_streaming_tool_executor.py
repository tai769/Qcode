import unittest

from qcode.providers.base import EventType, ResponseEvent, ToolCallEvent
from qcode.runtime.engine import AgentEngine
from qcode.runtime.session import ConversationSession
from qcode.tools.registry import ToolDefinition, ToolRegistry


class FakeToolProvider:
    def stream_chat_completion(self, messages, tools=None):
        has_tool_result = any(message.get("role") == "tool" for message in messages)
        if not has_tool_result:
            yield ResponseEvent(
                event_type=EventType.TOOL_CALL_DELTA,
                tool_call=ToolCallEvent(
                    tool_call_id="call_echo_1",
                    tool_name="echo_tool",
                    arguments_delta='{"text": "he',
                ),
            )
            yield ResponseEvent(
                event_type=EventType.TOOL_CALL_DONE,
                tool_call=ToolCallEvent(
                    tool_call_id="call_echo_1",
                    tool_name="echo_tool",
                    arguments_done='{"text": "hello"}',
                ),
            )
            yield ResponseEvent(event_type=EventType.COMPLETED)
            return

        yield ResponseEvent(event_type=EventType.OUTPUT_TEXT_DELTA, delta="工具已执行完毕")
        yield ResponseEvent(event_type=EventType.COMPLETED)


class StreamingToolExecutorTests(unittest.TestCase):
    def test_engine_executes_streamed_tool_and_continues(self) -> None:
        registry = ToolRegistry([
            ToolDefinition(
                name="echo_tool",
                description="Echo text.",
                parameters={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
                handler=lambda text, context=None: f"ECHO:{text}",
            )
        ])
        engine = AgentEngine(FakeToolProvider(), registry)
        session = ConversationSession([
            {"role": "user", "content": "请调用工具"},
        ])

        engine.run(session)

        self.assertEqual(
            [message.get("role") for message in session.messages],
            ["user", "assistant", "tool", "assistant"],
        )
        self.assertEqual(session.messages[2].get("content"), "ECHO:hello")
        self.assertIn("工具已执行完毕", session.last_assistant_content() or "")


if __name__ == "__main__":
    unittest.main()
