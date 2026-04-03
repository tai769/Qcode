"""Todo-related runtime middleware."""

from qcode.runtime.context import AgentRunContext


class TodoReminderMiddleware:
    """Injects a reminder when the model stops updating its todo list."""

    def __init__(
        self,
        reminder_interval: int = 3,
        reminder_text: str = "<reminder>Update your todos.</reminder>",
    ) -> None:
        self.reminder_interval = reminder_interval
        self.reminder_text = reminder_text

    def before_model_call(self, run_context: AgentRunContext) -> None:
        if not run_context.session.messages:
            return
        if run_context.rounds_since_todo < self.reminder_interval:
            return
        if run_context.todo_reminder_emitted_at_round == run_context.rounds_since_todo:
            return

        run_context.session.add_message(
            {
                "role": "user",
                "content": self.reminder_text,
            }
        )
        run_context.todo_reminder_emitted_at_round = run_context.rounds_since_todo
