"""Inbox injection middleware for team mailboxes."""

import json
import time

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

        session = run_context.session
        interrupted_at = session._interrupted_at
        now = time.time()

        stale_msgs = []
        fresh_msgs = []
        for msg in inbox:
            msg_ts = msg.get("timestamp", 0)
            if interrupted_at and msg_ts < interrupted_at:
                stale_msgs.append(msg)
            else:
                fresh_msgs.append(msg)

        parts = []
        if stale_msgs:
            parts.append(
                "<stale-inbox reason=\"user interrupted before these were sent\">\n"
                + json.dumps(stale_msgs, indent=2, ensure_ascii=False)
                + "\n</stale-inbox>"
            )
        if fresh_msgs:
            parts.append(
                "<inbox>\n"
                + json.dumps(fresh_msgs, indent=2, ensure_ascii=False)
                + "\n</inbox>"
            )

        for part in parts:
            session.add_message({"role": "user", "content": part})
