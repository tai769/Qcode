import unittest
from pathlib import Path

from qcode.config import AppConfig
from qcode.providers.base import EventType, ResponseAccumulator
from qcode.providers.responses_compatible import ResponsesCompatibleProvider


class ResponsesProviderStreamTests(unittest.TestCase):
    def test_output_text_done_is_ignored_when_delta_for_same_part_exists(self) -> None:
        provider = ResponsesCompatibleProvider(
            AppConfig(
                workdir=Path.cwd(),
                api_base_url="https://example.com/v1",
                api_key="test-key",
                model="test-model",
                max_tokens=1024,
            ),
            system_prompt="test",
        )
        payloads = [
            {
                "type": "response.created",
                "response": {"id": "resp_1"},
            },
            {
                "type": "response.output_text.delta",
                "response": {"id": "resp_1"},
                "output_index": 0,
                "content_index": 0,
                "delta": "你好",
            },
            {
                "type": "response.output_text.done",
                "response": {"id": "resp_1"},
                "output_index": 0,
                "content_index": 0,
                "text": "你好",
            },
            {
                "type": "response.completed",
                "response": {"id": "resp_1", "usage": {}},
            },
        ]

        accumulator = ResponseAccumulator()
        events = list(provider._events_from_sse(payloads))
        for event in events:
            accumulator.consume(event)

        result = accumulator.to_chat_result()

        self.assertEqual(result.message.get("content"), "你好")
        self.assertEqual(
            [event.event_type for event in events],
            [EventType.CREATED, EventType.OUTPUT_TEXT_DELTA, EventType.COMPLETED],
        )

    def test_output_text_done_is_kept_when_no_delta_exists(self) -> None:
        provider = ResponsesCompatibleProvider(
            AppConfig(
                workdir=Path.cwd(),
                api_base_url="https://example.com/v1",
                api_key="test-key",
                model="test-model",
                max_tokens=1024,
            ),
            system_prompt="test",
        )
        payloads = [
            {
                "type": "response.created",
                "response": {"id": "resp_2"},
            },
            {
                "type": "response.output_text.done",
                "response": {"id": "resp_2"},
                "output_index": 0,
                "content_index": 0,
                "text": "只在 done 里出现",
            },
            {
                "type": "response.completed",
                "response": {"id": "resp_2", "usage": {}},
            },
        ]

        accumulator = ResponseAccumulator()
        events = list(provider._events_from_sse(payloads))
        for event in events:
            accumulator.consume(event)

        result = accumulator.to_chat_result()

        self.assertEqual(result.message.get("content"), "只在 done 里出现")


if __name__ == "__main__":
    unittest.main()
