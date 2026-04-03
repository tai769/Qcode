"""Inbox injection middleware for team mailboxes."""

import json

from qcode.runtime.context import AgentRunContext
from qcode.runtime.team import MessageBus


class TeamInboxMiddleware:
    """Drain one mailbox and inject its messages before the next model call."""

    def __init__(self, bus: MessageBus, recipient: str) -> None:
        self.bus = bus
        self.recipient = recipient

    def before_model_call(self, run_context: AgentRunContext) -> None:
        inbox = self.bus.read_inbox(self.recipient)
        if not inbox:
            return

        body = json.dumps(inbox, indent=2, ensure_ascii=False)
        run_context.session.add_message(
            {
                "role": "user",
                "content": f"<inbox>\n{body}\n</inbox>",
            }
        )
