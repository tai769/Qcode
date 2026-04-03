import tempfile
import unittest
from pathlib import Path

from qcode.runtime.context import AgentRunContext
from qcode.runtime.goal_middleware import GoalMiddleware
from qcode.runtime.goal_store import GoalStore
from qcode.runtime.session import ConversationSession


class GoalMiddlewareTests(unittest.TestCase):
    def test_goal_store_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = GoalStore(Path(tmpdir) / "active_goal.md")
            self.assertEqual(store.get(), "")
            saved = store.set("Ship the frontend and keep smoke tests green.")
            self.assertIn("Ship the frontend", saved)
            self.assertIn("smoke tests", store.get())
            store.clear()
            self.assertEqual(store.get(), "")

    def test_goal_middleware_injects_once_per_recent_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = GoalStore(Path(tmpdir) / "active_goal.md")
            store.set("Keep coder/tester handoffs aligned to the same mission.")
            middleware = GoalMiddleware(store)
            session = ConversationSession([
                {"role": "user", "content": "请继续"},
            ])

            middleware.before_model_call(AgentRunContext(session=session))
            goal_messages = [
                message
                for message in session.messages
                if isinstance(message.get("content"), str)
                and str(message.get("content")).startswith("<goal>")
            ]
            self.assertEqual(len(goal_messages), 1)

            middleware.before_model_call(AgentRunContext(session=session))
            goal_messages = [
                message
                for message in session.messages
                if isinstance(message.get("content"), str)
                and str(message.get("content")).startswith("<goal>")
            ]
            self.assertEqual(len(goal_messages), 1)


if __name__ == "__main__":
    unittest.main()
