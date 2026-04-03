"""Task delegation tool backed by a subagent runner."""

from typing import Optional

from qcode.runtime.context import ToolExecutionContext
from qcode.runtime.subagent import SubagentRunner
from qcode.tools.registry import ToolDefinition


def build_task_tool_definition(subagent_runner: SubagentRunner) -> ToolDefinition:
    """Build the parent-only task tool that delegates work to a subagent."""

    def task(
        prompt: str,
        description: str = "subtask",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        parent_session_id = context.session.session_id if context else None
        return subagent_runner.run(
            prompt=prompt,
            description=description,
            parent_session_id=parent_session_id,
        )

    return ToolDefinition(
        name="task",
        description=(
            "Spawn a subagent with fresh context. It shares the workspace but not "
            "the current conversation history, and returns only a summary."
        ),
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The subtask prompt for the child agent.",
                },
                "description": {
                    "type": "string",
                    "description": "Short human-readable description of the subtask.",
                },
            },
            "required": ["prompt"],
        },
        handler=task,
    )
