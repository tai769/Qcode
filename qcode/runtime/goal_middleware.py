"""Runtime middleware that re-injects the active mission/goal."""

from __future__ import annotations

from qcode.runtime.context import AgentRunContext
from qcode.runtime.goal_store import GoalStore


class GoalMiddleware:
    """Injects the active mission so the lead/team do not drift from it."""

    def __init__(
        self,
        goal_store: GoalStore,
        lookback_messages: int = 6,
    ) -> None:
        self.goal_store = goal_store
        self.lookback_messages = max(1, lookback_messages)

    def before_model_call(self, run_context: AgentRunContext) -> None:
        goal = self.goal_store.get()
        if not goal:
            return
        if self._has_recent_goal_message(run_context):
            return

        run_context.session.add_message(
            {
                "role": "user",
                "content": (
                    "<goal>\n"
                    f"{goal}\n"
                    "</goal>\n"
                    "This is the active mission. Keep planning, delegation, coding, "
                    "review, and testing aligned to it. Treat it as sticky project "
                    "intent, not a new user request."
                ),
            }
        )

    def _has_recent_goal_message(self, run_context: AgentRunContext) -> bool:
        for message in run_context.session.messages[-self.lookback_messages :]:
            if str(message.get("role", "")).strip().lower() != "user":
                continue
            content = message.get("content")
            if isinstance(content, str) and content.startswith("<goal>"):
                return True
        return False
