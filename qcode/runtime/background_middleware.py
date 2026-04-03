"""Background-result notification injection middleware."""

from qcode.runtime.background import BackgroundManager
from qcode.runtime.context import AgentRunContext


class BackgroundNotificationMiddleware:
    """Inject completed background results before the next model call."""

    def __init__(self, background_manager: BackgroundManager) -> None:
        self.background_manager = background_manager

    def before_model_call(self, run_context: AgentRunContext) -> None:
        notifications = self.background_manager.drain_notifications(
            run_context.session.session_id
        )
        if not notifications:
            return

        body = "\n".join(
            f"[bg:{notification.task_id}] {notification.status}: {notification.result_preview}"
            for notification in notifications
        )
        run_context.session.add_message(
            {
                "role": "user",
                "content": f"<background-results>\n{body}\n</background-results>",
            }
        )
