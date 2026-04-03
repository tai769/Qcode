import tempfile
import unittest
from pathlib import Path

from qcode.runtime.task_graph import TaskGraphManager
from qcode.runtime.verification_loops import VerificationLoopManager


class VerificationLoopTests(unittest.TestCase):
    def test_failed_then_passed_verification_updates_messages_and_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            task_graph = TaskGraphManager(root / ".tasks")
            task_graph.create(
                subject="Build login flow",
                required_role="coder",
            )
            task_graph.claim(1, "coder", owner_role="coder")

            sent_messages: list[dict[str, object]] = []

            def fake_sender(
                sender: str,
                recipient: str,
                content: str,
                msg_type: str = "message",
                extra: dict[str, object] | None = None,
            ) -> str:
                sent_messages.append(
                    {
                        "from": sender,
                        "to": recipient,
                        "content": content,
                        "msg_type": msg_type,
                        "extra": dict(extra or {}),
                    }
                )
                return f"Sent {msg_type} to {recipient}"

            manager = VerificationLoopManager(
                root / ".team" / "verification_loops",
                task_graph=task_graph,
                lead_name="ld",
                message_sender=fake_sender,
            )

            record = manager.request_verification(
                owner="coder",
                subject="login-flow",
                details="Please run smoke test for login success + validation errors.",
                tester="tester",
                task_id=1,
            )

            self.assertEqual(record["status"], "awaiting_test")
            self.assertEqual(record["owner"], "coder")
            self.assertEqual(record["tester"], "tester")
            self.assertEqual(record["attempts"][-1]["attempt"], 1)
            self.assertEqual(sent_messages[-1]["to"], "tester")
            self.assertIn("Verification request", str(sent_messages[-1]["content"]))
            self.assertEqual(task_graph.snapshot()["in_progress"][0]["id"], 1)

            failed = manager.report_result(
                loop_id=record["loopId"],
                tester="tester",
                passed=False,
                summary="Login button stays disabled after valid input.",
                details="Open login page, enter valid credentials, button never enables.",
            )

            self.assertEqual(failed["status"], "changes_requested")
            self.assertEqual(failed["attempts"][-1]["result"]["passed"], False)
            self.assertEqual(sent_messages[-1]["to"], "coder")
            self.assertIn("Verification failed", str(sent_messages[-1]["content"]))
            self.assertEqual(task_graph.snapshot()["in_progress"][0]["id"], 1)

            resubmitted = manager.request_verification(
                owner="coder",
                loop_id=record["loopId"],
                details="Fixed disabled-state logic; please retest login flow.",
            )

            self.assertEqual(resubmitted["status"], "awaiting_test")
            self.assertEqual(resubmitted["attempts"][-1]["attempt"], 2)
            self.assertEqual(sent_messages[-1]["to"], "tester")

            passed = manager.report_result(
                loop_id=record["loopId"],
                tester="tester",
                passed=True,
                summary="Smoke passed for login success and validation errors.",
            )

            self.assertEqual(passed["status"], "passed")
            self.assertEqual(passed["attempts"][-1]["result"]["passed"], True)
            self.assertEqual(task_graph.snapshot()["completed"][0]["id"], 1)
            self.assertEqual(sent_messages[-2]["to"], "coder")
            self.assertEqual(sent_messages[-1]["to"], "ld")
            self.assertIn("Verification passed", str(sent_messages[-1]["content"]))


if __name__ == "__main__":
    unittest.main()
