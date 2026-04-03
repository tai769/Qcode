import io
import time
import unittest

from qcode.harness.cli import CliHarness, _CliProgressReporter
from qcode.providers.base import EventType, ResponseEvent, ToolCallEvent
from qcode.runtime.engine import AgentEngine
from qcode.runtime.session import ConversationSession
from qcode.telemetry.events import CallbackEventSink
from qcode.tools.registry import ToolDefinition, ToolRegistry


class ProgressProvider:
    def stream_chat_completion(self, messages, tools=None):
        has_tool_result = any(message.get("role") == "tool" for message in messages)
        yield ResponseEvent(event_type=EventType.CREATED, response_id="resp_progress_1")
        if not has_tool_result:
            yield ResponseEvent(
                event_type=EventType.TOOL_CALL_DONE,
                tool_call=ToolCallEvent(
                    tool_call_id="call_echo_progress",
                    tool_name="echo_tool",
                    arguments_done='{"text": "hello"}',
                ),
            )
            yield ResponseEvent(event_type=EventType.COMPLETED, response_id="resp_progress_1")
            return

        yield ResponseEvent(
            event_type=EventType.OUTPUT_TEXT_DELTA,
            response_id="resp_progress_2",
            delta="工具链路完成",
        )
        yield ResponseEvent(event_type=EventType.COMPLETED, response_id="resp_progress_2")


class CliHarnessProgressTests(unittest.TestCase):
    def test_run_once_shows_working_status_and_tool_progress(self) -> None:
        buffer = io.StringIO()
        event_sink = CallbackEventSink()
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
        engine = AgentEngine(ProgressProvider(), registry, event_sink=event_sink)
        harness = CliHarness(engine, stream=buffer)
        event_sink.set_callback(harness.handle_runtime_event)

        session = ConversationSession()
        harness.run_once("请执行工具并继续回答", session)

        output = buffer.getvalue()
        self.assertIn("[working] 思考中", output)
        self.assertIn("[working] 开始处理请求", output)
        self.assertIn("[working] 请求模型", output)
        self.assertIn("[working] 等待执行工具 echo_tool", output)
        self.assertIn("[working] 运行工具 echo_tool", output)
        self.assertIn("> echo_tool:", output)
        self.assertIn("ECHO:hello", output)
        self.assertIn("工具链路完成", output)

    def test_tty_progress_stop_does_not_erase_streamed_text(self) -> None:
        class FakeTty(io.StringIO):
            def isatty(self) -> bool:
                return True

        buffer = FakeTty()
        reporter = _CliProgressReporter(buffer, interval_seconds=0.01)

        reporter.start("思考中")
        time.sleep(0.03)
        reporter.pause()
        buffer.write("最终回答")
        reporter.stop()

        output = buffer.getvalue()
        self.assertIn("最终回答", output)
        self.assertFalse(output.endswith("\r\033[2K"))


if __name__ == "__main__":
    unittest.main()
