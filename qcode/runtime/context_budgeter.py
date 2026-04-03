"""Context budget calculation for history-replay sessions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence

from qcode.runtime.types import Message


@dataclass(frozen=True)
class ContextBudgetDecision:
    """Token-budget decision produced before a model call."""

    max_context_window: int
    target_ratio: float
    safety_margin_tokens: int
    reserved_prompt_tokens: int
    message_tokens: int
    available_message_budget_tokens: int
    overflow_tokens: int
    should_compact: bool
    summary_budget_tokens: int
    recent_raw_budget_tokens: int


class ContextBudgeter:
    """Calculates whether history replay must be compacted before a turn."""

    def __init__(
        self,
        *,
        max_context_window: int,
        target_ratio: float = 0.7,
        safety_margin_tokens: int = 12000,
        summary_ratio: float = 0.3,
        reserved_prompt_tokens: int = 0,
    ) -> None:
        self.max_context_window = max(1, max_context_window)
        self.target_ratio = min(max(target_ratio, 0.1), 1.0)
        self.safety_margin_tokens = max(0, safety_margin_tokens)
        self.summary_ratio = min(max(summary_ratio, 0.05), 0.95)
        self.reserved_prompt_tokens = max(0, reserved_prompt_tokens)

    def decide(
        self,
        messages: Sequence[Message],
        *,
        force_compaction: bool = False,
    ) -> ContextBudgetDecision:
        message_tokens = self.estimate_tokens(messages)
        target_context_tokens = int(self.max_context_window * self.target_ratio)
        available_message_budget_tokens = max(
            0,
            target_context_tokens - self.reserved_prompt_tokens - self.safety_margin_tokens,
        )
        overflow_tokens = max(0, message_tokens - available_message_budget_tokens)
        should_compact = force_compaction or overflow_tokens > 0
        summary_budget_tokens = max(1, int(available_message_budget_tokens * self.summary_ratio))
        recent_raw_budget_tokens = max(0, available_message_budget_tokens - summary_budget_tokens)

        return ContextBudgetDecision(
            max_context_window=self.max_context_window,
            target_ratio=self.target_ratio,
            safety_margin_tokens=self.safety_margin_tokens,
            reserved_prompt_tokens=self.reserved_prompt_tokens,
            message_tokens=message_tokens,
            available_message_budget_tokens=available_message_budget_tokens,
            overflow_tokens=overflow_tokens,
            should_compact=should_compact,
            summary_budget_tokens=summary_budget_tokens,
            recent_raw_budget_tokens=recent_raw_budget_tokens,
        )

    @staticmethod
    def estimate_tokens(messages: Sequence[Message]) -> int:
        serialized = json.dumps(list(messages), default=str, ensure_ascii=False)
        return len(serialized) // 4


def estimate_text_tokens(text: str) -> int:
    """Cheap token estimate for fixed prompt segments."""

    return max(0, len(text) // 4)
