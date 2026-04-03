import tempfile
import time
import unittest
from pathlib import Path

from qcode.runtime.task_graph import TaskGraphManager
from qcode.runtime.team import MessageBus, TeammateManager


class IdleEngine:
    def run(self, session, max_iterations=None) -> None:
        session.add_message({"role": "assistant", "content": "standing by"})
        session.request_idle_poll("autonomous")
        session.request_run_stop("idle")


class TeamAutonomyTests(unittest.TestCase):
    def test_idle_timeout_does_not_force_shutdown_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bus = MessageBus(root / ".team" / "inbox")
            task_graph = TaskGraphManager(root / ".tasks")
            manager = TeammateManager(
                team_dir=root / ".team",
                bus=bus,
                task_graph=task_graph,
                engine_factory=lambda name, role: IdleEngine(),
                idle_sleep_seconds=0.05,
                idle_timeout_seconds=0.15,
                idle_shutdown_enabled=False,
            )

            manager.spawn("tester", "tester", "stand by for smoke tests")
            time.sleep(0.35)

            member = manager.get_member("tester")
            self.assertIsNotNone(member)
            self.assertNotEqual(member["status"], "shutdown")

            result = manager.send_message("ld", "tester", "run smoke now")
            self.assertFalse(result.startswith("Error:"))
            manager.mark_shutdown("tester")

    def test_coder_tester_loop_can_complete_without_deadlock(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bus = MessageBus(root / ".team" / "inbox")
            task_graph = TaskGraphManager(root / ".tasks")
            holder = {}
            actions: list[str] = []

            class WorkflowEngine:
                def __init__(self, name: str) -> None:
                    self.name = name

                def run(self, session, max_iterations=None) -> None:
                    manager = holder["manager"]
                    last_user_content = ""
                    for message in reversed(session.messages):
                        if message.get("role") == "user":
                            last_user_content = str(message.get("content") or "")
                            break

                    if self.name == "coder":
                        if "build login flow" in last_user_content:
                            manager.send_message("coder", "tester", "RUN_SMOKE login-flow")
                            actions.append("coder->tester:smoke")
                        elif "BUG_FOUND login-flow" in last_user_content:
                            manager.send_message("coder", "tester", "RETEST login-flow")
                            actions.append("coder->tester:retest")
                    elif self.name == "tester":
                        if "RUN_SMOKE login-flow" in last_user_content:
                            manager.send_message("tester", "coder", "BUG_FOUND login-flow")
                            actions.append("tester->coder:bug")
                        elif "RETEST login-flow" in last_user_content:
                            manager.send_message("tester", "ld", "SMOKE_PASSED login-flow")
                            actions.append("tester->lead:pass")

                    session.add_message(
                        {"role": "assistant", "content": f"{self.name} handled turn"}
                    )
                    session.request_idle_poll("autonomous")
                    session.request_run_stop("idle")

            manager = TeammateManager(
                team_dir=root / ".team",
                bus=bus,
                task_graph=task_graph,
                engine_factory=lambda name, role: WorkflowEngine(name),
                idle_sleep_seconds=0.05,
                idle_timeout_seconds=0.2,
                idle_shutdown_enabled=False,
            )
            holder["manager"] = manager

            manager.spawn("tester", "tester", "stand by for smoke tests")
            manager.spawn("coder", "coder", "please build login flow")

            inbox = []
            deadline = time.time() + 3.0
            while time.time() < deadline:
                inbox.extend(manager.read_inbox("ld"))
                if any("SMOKE_PASSED login-flow" in str(message.get("content")) for message in inbox):
                    break
                time.sleep(0.05)

            self.assertIn("coder->tester:smoke", actions)
            self.assertIn("tester->coder:bug", actions)
            self.assertIn("coder->tester:retest", actions)
            self.assertIn("tester->lead:pass", actions)
            self.assertTrue(
                any("SMOKE_PASSED login-flow" in str(message.get("content")) for message in inbox)
            )

            manager.mark_shutdown("coder")
            manager.mark_shutdown("tester")


if __name__ == "__main__":
    unittest.main()
