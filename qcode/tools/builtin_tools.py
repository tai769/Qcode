"""Builtin tools available to the agent."""

from pathlib import Path
from typing import Optional

from qcode.runtime.background import BackgroundManager
from qcode.runtime.context import ToolExecutionContext
from qcode.tools.registry import ToolDefinition, ToolRegistry
from qcode.utils.workspace import Workspace


def build_builtin_tool_registry(
    workdir: Path,
    shell_timeout: int = 120,
    background_manager: Optional[BackgroundManager] = None,
) -> ToolRegistry:
    workspace = Workspace(workdir, shell_timeout=shell_timeout)

    def bash(
        command: str,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return workspace.run_bash(command)

    def read_file(
        path: str,
        limit: Optional[int] = None,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return workspace.read_text(path, limit)

    def write_file(
        path: str,
        content: str,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return workspace.write_text(path, content)

    def edit_file(
        path: str,
        old_text: str,
        new_text: str,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return workspace.replace_text(path, old_text, new_text)

    def todo(
        items: list[dict[str, object]],
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        if context is None:
            return "Error: Todo tool requires session context"

        return context.session.todo_manager.update(items)

    def compact(
        focus: str = "general continuity",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        if context is None:
            return "Error: Compact tool requires session context"

        context.session.request_compaction(focus)
        return f"Compression requested. Focus: {focus}"

    def background_run(
        command: str,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        if context is None:
            return "Error: Background tool requires session context"
        if background_manager is None:
            return "Error: Background execution is not configured"

        return background_manager.run(context.session.session_id, command)

    def check_background(
        task_id: Optional[str] = None,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        if context is None:
            return "Error: Background tool requires session context"
        if background_manager is None:
            return "Error: Background execution is not configured"

        return background_manager.check(context.session.session_id, task_id)

    tool_definitions = [
            ToolDefinition(
                name="bash",
                description="Run a shell command.",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute",
                        }
                    },
                    "required": ["command"],
                },
                handler=bash,
            ),
            ToolDefinition(
                name="read_file",
                description="Read file contents from workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to workspace",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max lines to read (optional)",
                        },
                    },
                    "required": ["path"],
                },
                handler=read_file,
            ),
            ToolDefinition(
                name="write_file",
                description="Write content to a file in workspace.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to workspace",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write",
                        },
                    },
                    "required": ["path", "content"],
                },
                handler=write_file,
            ),
            ToolDefinition(
                name="edit_file",
                description="Replace exact text in a file.",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path relative to workspace",
                        },
                        "old_text": {
                            "type": "string",
                            "description": "Text to replace",
                        },
                        "new_text": {
                            "type": "string",
                            "description": "New text",
                        },
                    },
                    "required": ["path", "old_text", "new_text"],
                },
                handler=edit_file,
            ),
            ToolDefinition(
                name="todo",
                description=(
                    "Update the structured task list. Use it for multi-step tasks "
                    "and keep at most one item in_progress."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "description": "Ordered todo items for the current task.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Stable todo identifier",
                                    },
                                    "text": {
                                        "type": "string",
                                        "description": "Task description",
                                    },
                                    "status": {
                                        "type": "string",
                                        "enum": ["pending", "in_progress", "completed"],
                                    },
                                },
                                "required": ["id", "text", "status"],
                            },
                        }
                    },
                    "required": ["items"],
                },
                handler=todo,
            ),
            ToolDefinition(
                name="compact",
                description=(
                    "Request conversation compression to keep the working context small "
                    "while preserving continuity."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "focus": {
                            "type": "string",
                            "description": "What the compressed summary should preserve.",
                        }
                    },
                },
                handler=compact,
            ),
        ]

    if background_manager is not None:
        tool_definitions.extend(
            [
                ToolDefinition(
                    name="background_run",
                    description=(
                        "Run a shell command in the background and return immediately "
                        "with a task id."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Long-running shell command to execute",
                            }
                        },
                        "required": ["command"],
                    },
                    handler=background_run,
                ),
                ToolDefinition(
                    name="check_background",
                    description=(
                        "Check one background task or list all background tasks for the "
                        "current session."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "Optional background task id",
                            }
                        },
                    },
                    handler=check_background,
                ),
            ]
        )

    return ToolRegistry(tool_definitions)
