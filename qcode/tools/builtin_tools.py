"""Builtin tools available to the agent."""

import json
import time
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
        offset: Optional[int] = None,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return workspace.read_text(path, limit=limit, offset=offset)

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

    def _clean_output_lines(output: str) -> list[str]:
        lines = []
        for line in output.splitlines():
            if not line or line == "(no output)":
                continue
            if line.startswith("[exit code:"):
                continue
            lines.append(line)
        return lines

    def _lsof_available() -> bool:
        result = workspace.run_bash("command -v lsof >/dev/null 2>&1 && echo ok")
        return result.strip() == "ok"

    def _parse_lsof_listeners(lines: list[str]) -> list[dict[str, object]]:
        listeners: list[dict[str, object]] = []
        current: dict[str, object] = {}
        for line in lines:
            if not line:
                continue
            field = line[0]
            value = line[1:]
            if field == "p":
                if current:
                    listeners.append(current)
                current = {"pid": int(value)}
            elif field == "c":
                current["command"] = value
            elif field == "n":
                current["listener"] = value
        if current:
            listeners.append(current)
        return listeners

    def _process_cwd(pid: int) -> str:
        result = workspace.run_bash(f"lsof -p {pid} -a -d cwd -Fn")
        lines = _clean_output_lines(result)
        for line in lines:
            if line.startswith("n"):
                return line[1:]
        return ""

    def _process_command(pid: int) -> str:
        result = workspace.run_bash(f"ps -o command= -p {pid}")
        lines = _clean_output_lines(result)
        return lines[0] if lines else ""

    def _inspect_port(port: int) -> dict[str, object]:
        if port < 1 or port > 65535:
            return {"error": f"Invalid port: {port}"}
        if not _lsof_available():
            return {"error": "lsof not available; port inspection requires lsof"}

        result = workspace.run_bash(f"lsof -nP -iTCP:{port} -sTCP:LISTEN -Fpcn")
        lines = _clean_output_lines(result)
        listeners = _parse_lsof_listeners(lines)
        workdir = str(workspace.root)
        enriched = []
        for listener in listeners:
            pid = int(listener.get("pid", 0))
            cwd = _process_cwd(pid)
            command_line = _process_command(pid)
            in_workspace = False
            if cwd and cwd.startswith(workdir):
                in_workspace = True
            elif command_line and workdir in command_line:
                in_workspace = True
            enriched.append(
                {
                    **listener,
                    "cwd": cwd,
                    "command_line": command_line,
                    "in_workspace": in_workspace,
                }
            )
        return {
            "port": port,
            "listeners": enriched,
        }

    def port_inspect(
        port: int,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        info = _inspect_port(int(port))
        return json.dumps(info, indent=2, ensure_ascii=False)

    def port_kill(
        port: int,
        confirm: bool = False,
        force: bool = False,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        info = _inspect_port(int(port))
        if "error" in info:
            return f"Error: {info['error']}"
        listeners = info.get("listeners", [])
        if not listeners:
            return f"Port {port} is not in use."

        workspace_listeners = [
            entry for entry in listeners if entry.get("in_workspace")
        ]
        foreign_listeners = [
            entry for entry in listeners if not entry.get("in_workspace")
        ]
        stopped: list[int] = []
        signal = "-9" if force else "-15"

        for entry in workspace_listeners:
            pid = int(entry.get("pid", 0))
            if pid:
                workspace.run_bash(f"kill {signal} {pid}")
                stopped.append(pid)

        if foreign_listeners and not confirm:
            return (
                "Port is still held by non-workspace processes. "
                "Set confirm=true to stop them.\n"
                f"Stopped workspace PIDs: {stopped or '(none)'}\n"
                f"Remaining: {json.dumps(foreign_listeners, indent=2, ensure_ascii=False)}"
            )

        for entry in foreign_listeners:
            pid = int(entry.get("pid", 0))
            if pid:
                workspace.run_bash(f"kill {signal} {pid}")
                stopped.append(pid)

        return f"Sent signal {signal} to PIDs: {stopped}"

    def _truncate_text(text: str, limit: int = 300) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + "... (truncated)"

    def ui_check(
        url: str,
        wait_for: str = "",
        timeout_seconds: int = 20,
        screenshot_path: str = "",
        full_page: bool = False,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except Exception:
            return (
                "Error: Playwright is not installed. "
                "Run: pip install playwright && python -m playwright install"
            )

        cleaned_url = url.strip()
        if not cleaned_url:
            return "Error: url is required"

        started_at = time.monotonic()
        report: dict[str, object] = {
            "status": "ok",
            "url": cleaned_url,
            "final_url": "",
            "http_status": None,
            "title": "",
            "wait_for": wait_for.strip(),
            "console_errors": [],
            "page_errors": [],
            "network_errors": [],
            "screenshot_path": "",
            "duration_ms": 0,
        }

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": int(viewport_width), "height": int(viewport_height)}
                )
                page = context.new_page()
                console_errors: list[str] = []
                page_errors: list[str] = []
                network_errors: list[str] = []

                def on_console(msg) -> None:
                    if msg.type == "error":
                        console_errors.append(_truncate_text(msg.text))

                def on_page_error(exc: Exception) -> None:
                    page_errors.append(_truncate_text(str(exc)))

                def on_request_failed(request) -> None:
                    try:
                        failure = request.failure
                        if callable(failure):
                            failure = failure()
                        detail = "request failed"
                        if isinstance(failure, dict):
                            detail = (
                                failure.get("error_text")
                                or failure.get("errorText")
                                or detail
                            )
                        elif hasattr(failure, "error_text"):
                            detail = getattr(failure, "error_text") or detail
                        elif failure:
                            detail = str(failure)
                        network_errors.append(
                            _truncate_text(f"{request.url} :: {detail}")
                        )
                    except Exception as exc:
                        network_errors.append(
                            _truncate_text(f"{request.url} :: failure handler error: {exc}")
                        )

                page.on("console", on_console)
                page.on("pageerror", on_page_error)
                page.on("requestfailed", on_request_failed)

                response = page.goto(
                    cleaned_url,
                    wait_until="load",
                    timeout=int(timeout_seconds) * 1000,
                )
                if wait_for:
                    page.wait_for_selector(wait_for, timeout=int(timeout_seconds) * 1000)

                report["http_status"] = response.status if response is not None else None
                report["final_url"] = page.url
                report["title"] = page.title()

                if screenshot_path:
                    try:
                        screenshot_file = workspace.safe_path(screenshot_path)
                    except ValueError as exc:
                        return f"Error: {exc}"
                    screenshot_file.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(screenshot_file), full_page=full_page)
                    report["screenshot_path"] = str(screenshot_file.relative_to(workspace.root))

                report["console_errors"] = console_errors
                report["page_errors"] = page_errors
                report["network_errors"] = network_errors
                if console_errors or page_errors or network_errors:
                    report["status"] = "warning"
        except PlaywrightTimeoutError:
            report["status"] = "error"
            report["error"] = "Timeout waiting for page load or selector"
        except Exception as exc:
            report["status"] = "error"
            report["error"] = _truncate_text(str(exc), limit=500)
        finally:
            report["duration_ms"] = int((time.monotonic() - started_at) * 1000)

        return json.dumps(report, indent=2, ensure_ascii=False)

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
                        "offset": {
                            "type": "integer",
                            "description": "Starting line offset (optional)",
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
            ToolDefinition(
                name="port_inspect",
                description="Inspect which process is listening on a local TCP port.",
                parameters={
                    "type": "object",
                    "properties": {
                        "port": {
                            "type": "integer",
                            "description": "TCP port to inspect",
                        }
                    },
                    "required": ["port"],
                },
                handler=port_inspect,
            ),
            ToolDefinition(
                name="port_kill",
                description=(
                    "Stop processes listening on a TCP port. Auto-stops workspace-owned "
                    "processes; requires confirm=true for other processes."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "port": {
                            "type": "integer",
                            "description": "TCP port to stop listeners on",
                        },
                        "confirm": {
                            "type": "boolean",
                            "description": "Allow stopping non-workspace processes",
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Send SIGKILL instead of SIGTERM",
                        },
                    },
                    "required": ["port"],
                },
                handler=port_kill,
            ),
            ToolDefinition(
                name="ui_check",
                description=(
                    "Run a headless UI check against a URL and capture console/network errors "
                    "with an optional screenshot."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to open in a headless browser",
                        },
                        "wait_for": {
                            "type": "string",
                            "description": "Optional CSS selector to wait for before capturing evidence",
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "description": "Timeout in seconds for page load/selector wait",
                        },
                        "screenshot_path": {
                            "type": "string",
                            "description": "Optional screenshot path relative to workspace",
                        },
                        "full_page": {
                            "type": "boolean",
                            "description": "Capture full-page screenshot",
                        },
                        "viewport_width": {
                            "type": "integer",
                            "description": "Viewport width in pixels",
                        },
                        "viewport_height": {
                            "type": "integer",
                            "description": "Viewport height in pixels",
                        },
                    },
                    "required": ["url"],
                },
                handler=ui_check,
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
