import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from qcode.providers.base import EventType, ResponseEvent
from qcode.runtime.compaction import ConversationCompactor
from qcode.runtime.compaction_middleware import CompactionMiddleware
from qcode.runtime.context_budgeter import ContextBudgeter, estimate_text_tokens
from qcode.runtime.context import AgentRunContext
from qcode.runtime.engine import AgentEngine
from qcode.runtime.middleware import MiddlewarePipeline
from qcode.runtime.session import ConversationSession
from qcode.tools.registry import ToolRegistry


class FakeSummaryProvider:
    def create_chat_completion(self, messages, tools=None):
        return type(
            "Result",
            (),
            {
                "message": {
                    "role": "assistant",
                    "content": (
                        "## Goal\nG\n"
                        "## Done\nD\n"
                        "## Current State\nS\n"
                        "## Decisions\nC\n"
                        "## Pending\nP\n"
                        "## Risks\nR"
                    ),
                }
            },
        )()


class FakeChatProvider:
    def __init__(self):
        self.turn = 0

    def stream_chat_completion(self, messages, tools=None):
        self.turn += 1
        latest_user = [message for message in messages if message.get("role") == "user"][-1]["content"]
        yield ResponseEvent(
            event_type=EventType.OUTPUT_TEXT_DELTA,
            delta=f"收到第{self.turn}轮:{str(latest_user)[:20]}",
        )
        yield ResponseEvent(event_type=EventType.COMPLETED)


class CompactionTests(unittest.TestCase):
    def test_compaction_preserves_latest_user_turns(self) -> None:
        with TemporaryDirectory() as tmp:
            compactor = ConversationCompactor(
                FakeSummaryProvider(),
                transcript_dir=Path(tmp),
                token_threshold=999999,
                summary_ratio=0.3,
            )
            budgeter = ContextBudgeter(
                max_context_window=700,
                target_ratio=0.7,
                safety_margin_tokens=80,
                summary_ratio=0.3,
                reserved_prompt_tokens=estimate_text_tokens("system prompt"),
            )
            middleware = MiddlewarePipeline([
                CompactionMiddleware(compactor, budgeter),
            ])
            engine = AgentEngine(FakeChatProvider(), ToolRegistry([]), middleware=middleware)
            session = ConversationSession()

            for index in range(4):
                session.add_user_text(f"第{index}轮需求：" + "说明很长。" * 80)
                engine.run(session)

            raw_users = [
                message["content"]
                for message in session.messages
                if message.get("role") == "user"
                and isinstance(message.get("content"), str)
                and not message["content"].startswith("[Conversation compressed.")
            ]
            has_memory = any(
                isinstance(message.get("content"), str)
                and message["content"].startswith("[Conversation compressed.")
                for message in session.messages
            )

            self.assertTrue(has_memory)
            self.assertTrue(any("第3轮需求" in text for text in raw_users))

    def test_tail_budget_preserves_assistant_tool_pair(self) -> None:
        with TemporaryDirectory() as tmp:
            compactor = ConversationCompactor(
                FakeSummaryProvider(),
                transcript_dir=Path(tmp),
                summary_ratio=0.3,
            )
            messages = [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "todo", "arguments": "{}"},
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "content": "todo result",
                },
            ]

            preserved = compactor._recent_messages_for_replay(messages, raw_budget_tokens=20)

            self.assertEqual(len(preserved), 2)
            self.assertEqual(preserved[0].get("role"), "assistant")
            self.assertEqual(preserved[1].get("role"), "tool")

    def test_micro_compact_redacts_recursive_transcript_read_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            compactor = ConversationCompactor(
                FakeSummaryProvider(),
                transcript_dir=Path(tmp),
                keep_recent_tool_results=0,
                summary_ratio=0.3,
            )
            session = ConversationSession([
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_read_transcript",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path":".transcripts/transcript_1.jsonl","limit":400}',
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_read_transcript",
                    "content": "nested transcript line\n" * 40,
                },
            ])

            compacted = compactor.micro_compact(session)

            self.assertTrue(compacted)
            self.assertIn("recursive context growth", session.messages[1].get("content", ""))
            self.assertIn(".transcripts/transcript_1.jsonl", session.messages[1].get("content", ""))

    def test_save_transcript_redacts_recursive_transcript_tool_output(self) -> None:
        with TemporaryDirectory() as tmp:
            compactor = ConversationCompactor(
                FakeSummaryProvider(),
                transcript_dir=Path(tmp),
                summary_ratio=0.3,
            )
            session = ConversationSession([
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_read_transcript",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path":".transcripts/transcript_1.jsonl","limit":400}',
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_read_transcript",
                    "content": '{"role":"user","content":"deeply nested transcript content"}',
                },
            ])

            transcript_path = compactor._save_transcript(session)
            transcript_text = transcript_path.read_text(encoding="utf-8")

            self.assertIn("recursive_context_guard", transcript_text)
            self.assertIn("recursive context growth", transcript_text)
            self.assertNotIn("deeply nested transcript content", transcript_text)


if __name__ == "__main__":
    unittest.main()
