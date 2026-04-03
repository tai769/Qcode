import os
import unittest
from dataclasses import replace
from pathlib import Path

from qcode.app import build_cli_harness
from qcode.config import AppConfig
from qcode.runtime.session import ConversationSession


@unittest.skipUnless(
    os.getenv("QCODE_RUN_REAL_PROVIDER_SMOKE") == "1",
    "Set QCODE_RUN_REAL_PROVIDER_SMOKE=1 to run real-provider smoke tests.",
)
class RealProviderSmokeTests(unittest.TestCase):
    def test_multi_turn_memory(self) -> None:
        config = AppConfig.from_env()
        harness = build_cli_harness(config)
        session = ConversationSession()

        harness.run_once(
            "请记住：我要做一个前端需求设计页面。先只回复‘收到需求1’。",
            session,
        )
        harness.run_once(
            "继续第二轮：补充要求，页面需要团队面板、任务看板、对话区。先只回复‘收到需求2’。",
            session,
        )
        harness.run_once(
            "第三轮检查：请只回答我目前记住了哪些要点，用中文 3 条。",
            session,
        )

        answer = session.last_assistant_content() or ""
        self.assertTrue(
            any(fragment in answer for fragment in ("前端需求设计", "前端需求", "需求设计"))
        )
        self.assertIn("团队面板", answer)
        self.assertIn("任务看板", answer)

    def test_real_tool_use(self) -> None:
        log_path = Path('.qcode/test_real_provider_smoke.jsonl')
        if log_path.exists():
            log_path.unlink()

        config = replace(AppConfig.from_env(), event_log_path=log_path)
        harness = build_cli_harness(config)
        session = ConversationSession()

        harness.run_once(
            "请务必使用 read_file 工具读取 README.md 的开头内容，再用中文一句话总结项目定位。不要凭空回答。",
            session,
        )

        answer = session.last_assistant_content() or ""
        self.assertIn("CLI Coding Agent", answer)
        self.assertTrue(log_path.exists())


if __name__ == "__main__":
    unittest.main()
