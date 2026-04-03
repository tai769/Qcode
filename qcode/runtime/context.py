"""Runtime context objects passed across the harness layers."""

from dataclasses import dataclass
from typing import Optional

from qcode.runtime.session import ConversationSession


@dataclass
class AgentRunContext:
    """Ephemeral state for a single engine run."""

    session: ConversationSession
    rounds_since_todo: int = 0
    todo_reminder_emitted_at_round: Optional[int] = None


@dataclass(frozen=True)
class ToolExecutionContext:
    """Context passed to tool handlers during execution."""

    session: ConversationSession
