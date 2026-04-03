"""Tool definitions for the persistent task graph."""

from typing import Optional

from qcode.runtime.context import ToolExecutionContext
from qcode.runtime.task_graph import TaskGraphManager
from qcode.tools.registry import ToolDefinition


def build_task_graph_tool_definitions(
    task_graph: TaskGraphManager,
) -> list[ToolDefinition]:
    def task_create(
        subject: str,
        description: str = "",
        blockedBy: Optional[list[int]] = None,
        owner: str = "",
        requiredRole: str = "",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return task_graph.create(
            subject=subject,
            description=description,
            blocked_by=blockedBy,
            owner=owner,
            required_role=requiredRole,
        )

    def task_update(
        task_id: int,
        status: Optional[str] = None,
        addBlockedBy: Optional[list[int]] = None,
        removeBlockedBy: Optional[list[int]] = None,
        owner: Optional[str] = None,
        description: Optional[str] = None,
        requiredRole: Optional[str] = None,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return task_graph.update(
            task_id=task_id,
            status=status,
            add_blocked_by=addBlockedBy,
            remove_blocked_by=removeBlockedBy,
            owner=owner,
            description=description,
            required_role=requiredRole,
        )

    def task_get(
        task_id: int,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return task_graph.get(task_id)

    def task_list(
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return task_graph.list_all()

    def claim_task(
        task_id: int,
        owner: str,
        ownerRole: str = "",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return task_graph.claim(task_id, owner, owner_role=ownerRole)

    return [
        ToolDefinition(
            name="task_create",
            description="Create a persistent task in the shared task graph.",
            parameters={
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Short task title",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional longer description",
                    },
                    "blockedBy": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional prerequisite task ids",
                    },
                    "owner": {
                        "type": "string",
                        "description": "Optional owner or teammate name",
                    },
                    "requiredRole": {
                        "type": "string",
                        "description": "Optional role required to claim this task",
                    },
                },
                "required": ["subject"],
            },
            handler=task_create,
        ),
        ToolDefinition(
            name="task_update",
            description="Update task status, dependencies, owner, or description.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task id"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                    },
                    "addBlockedBy": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                    "removeBlockedBy": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                    "owner": {
                        "type": "string",
                        "description": "Optional owner or teammate name",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional replacement description",
                    },
                    "requiredRole": {
                        "type": "string",
                        "description": "Optional role required to claim this task",
                    },
                },
                "required": ["task_id"],
            },
            handler=task_update,
        ),
        ToolDefinition(
            name="task_get",
            description="Get the full JSON representation of one task.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task id"}
                },
                "required": ["task_id"],
            },
            handler=task_get,
        ),
        ToolDefinition(
            name="task_list",
            description=(
                "List the persistent task graph grouped by ready, in-progress, "
                "blocked, and completed tasks."
            ),
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=task_list,
        ),
        ToolDefinition(
            name="claim_task",
            description="Claim an unowned ready task and mark it in progress.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task id"},
                    "owner": {
                        "type": "string",
                        "description": "Owner or teammate name claiming the task",
                    },
                    "ownerRole": {
                        "type": "string",
                        "description": "Role of the teammate claiming the task",
                    },
                },
                "required": ["task_id", "owner"],
            },
            handler=claim_task,
        ),
    ]
