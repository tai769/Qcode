"""Runtime middleware for layered context compaction."""

from qcode.runtime.compaction import ConversationCompactor
from qcode.runtime.context import AgentRunContext
from qcode.runtime.context_budgeter import ContextBudgeter


class CompactionMiddleware:
    """Runs micro compaction every turn and full compaction when needed."""

    def __init__(
        self,
        compactor: ConversationCompactor,
        budgeter: ContextBudgeter,
    ) -> None:
        self.compactor = compactor
        self.budgeter = budgeter

    def before_model_call(self, run_context: AgentRunContext) -> None:
        session = run_context.session
        self.compactor.micro_compact(session)
        decision = self.budgeter.decide(session.messages)

        manual_focus = session.consume_compaction_request()
        if manual_focus is not None:
            manual_decision = self.budgeter.decide(
                session.messages,
                force_compaction=True,
            )
            self.compactor.compact(
                session,
                trigger="manual",
                focus=manual_focus,
                decision=manual_decision,
            )
            return

        if decision.should_compact:
            self.compactor.compact(
                session,
                trigger="auto",
                focus="preserve continuity for continued execution",
                decision=decision,
            )
