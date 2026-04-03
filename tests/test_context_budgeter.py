import unittest

from qcode.runtime.context_budgeter import ContextBudgeter


class ContextBudgeterTests(unittest.TestCase):
    def test_small_context_does_not_compact(self) -> None:
        budgeter = ContextBudgeter(
            max_context_window=1000,
            target_ratio=0.7,
            safety_margin_tokens=100,
            summary_ratio=0.3,
            reserved_prompt_tokens=40,
        )

        decision = budgeter.decide([
            {"role": "user", "content": "short message"},
        ])

        self.assertFalse(decision.should_compact)
        self.assertGreater(decision.available_message_budget_tokens, 0)

    def test_large_context_triggers_compaction(self) -> None:
        budgeter = ContextBudgeter(
            max_context_window=1000,
            target_ratio=0.7,
            safety_margin_tokens=100,
            summary_ratio=0.3,
            reserved_prompt_tokens=40,
        )

        decision = budgeter.decide([
            {"role": "user", "content": "very long message " * 1000},
        ])

        self.assertTrue(decision.should_compact)
        self.assertGreater(decision.overflow_tokens, 0)
        self.assertGreater(decision.summary_budget_tokens, 0)
        self.assertGreater(decision.recent_raw_budget_tokens, 0)

    def test_force_compaction_overrides_budget(self) -> None:
        budgeter = ContextBudgeter(max_context_window=1000)

        decision = budgeter.decide(
            [{"role": "user", "content": "short"}],
            force_compaction=True,
        )

        self.assertTrue(decision.should_compact)


if __name__ == "__main__":
    unittest.main()
