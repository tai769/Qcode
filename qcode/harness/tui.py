"""Textual TUI for Qcode — full implementation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Collapsible,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    OptionList,
    RichLog,
    Select,
    Static,
    Tree,
)


# ─── Collapsible Tool Result Widget ────────────────────────────

class CollapsibleToolResult(Static):
    """A collapsible widget for tool results that shows summary by default."""

    DEFAULT_CSS = """
    CollapsibleToolResult {
        height: auto;
        margin: 0 0 1 0;
    }
    .tool-header {
        height: 1;
        background: $surface-darken-1;
        padding: 0 1;
    }
    .tool-content {
        height: auto;
        max-height: 20;
        overflow-y: auto;
        padding: 0 1;
        background: $surface-darken-2;
        display: none;
    }
    .tool-content.expanded {
        display: block;
    }
    """

    def __init__(
        self,
        tool_name: str,
        content: str,
        is_error: bool = False,
        max_preview_chars: int = 200,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.content = content
        self.is_error = is_error
        self.max_preview_chars = max_preview_chars
        self._expanded = False

    def compose(self) -> ComposeResult:
        # Header with toggle button
        preview = self._get_preview()
        icon = self._get_icon()
        error_prefix = "[red]Error: [/]" if self.is_error else ""

        with Vertical():
            yield Static(
                f"{icon} [bold]{self.tool_name}[/] {error_prefix}[dim]{preview}[/]",
                classes="tool-header",
                id=f"header-{id(self)}"
            )
            yield Static(
                self._format_content(),
                classes="tool-content",
                id=f"content-{id(self)}"
            )

    def _get_preview(self) -> str:
        """Get a short preview of the content."""
        if not self.content:
            return "(empty)"
        preview = self.content[:self.max_preview_chars].replace("\n", " ")
        if len(self.content) > self.max_preview_chars:
            preview += "..."
        return preview

    def _get_icon(self) -> str:
        """Get icon for tool type."""
        icons = {
            "bash": "  ", "read_file": "  ", "write_file": "  ",
            "edit_file": "  ✏️", "grep": "  ", "glob": "  ",
            "todo": "  ", "compact": "  ", "task": "  ",
            "git_status": " ", "git_diff": " ", "git_log": " ",
        }
        return icons.get(self.tool_name, "  ")

    def _format_content(self) -> str:
        """Format the full content for display."""
        if not self.content:
            return "(no output)"

        # Truncate very long content
        max_chars = 5000
        content = self.content
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[dim]... ({len(self.content)} chars total)[/]"

        return content

    def on_click(self) -> None:
        """Toggle expand/collapse on click."""
        self._expanded = not self._expanded
        content_widget = self.query_one(f"#content-{id(self)}", Static)
        if self._expanded:
            content_widget.add_class("expanded")
        else:
            content_widget.remove_class("expanded")

from qcode.config import AppConfig
from qcode.harness.completer import (
    extract_at_reference,
    get_file_completions,
    replace_at_reference,
)
from qcode.providers.registry import ProviderRegistry, ProviderEntry, PRESETS, SUGGESTED_MODELS
from qcode.runtime.engine import AgentEngine, EngineEvent
from qcode.runtime.session import ConversationSession
from qcode.runtime.todos import TodoItem, TodoManager


# ─── Permission Dialog ───────────────────────────────────────────

class PermissionScreen(ModalScreen[bool]):
    CSS = """
    PermissionScreen { align: center middle; }
    #perm-dialog {
        width: 70; height: auto; max-height: 20;
        border: thick $warning; background: $surface; padding: 1 2;
    }
    #perm-label { width: 100%; margin-bottom: 1; }
    .perm-buttons { width: 100%; height: 3; align: center middle; }
    .perm-buttons Button { margin: 0 1; }
    """

    def __init__(self, tool_name: str, args_preview: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.args_preview = args_preview

    def compose(self) -> ComposeResult:
        with Vertical(id="perm-dialog"):
            yield Label(
                f"[bold yellow]⚠ Permission required[/]\n\n"
                f"Tool: [cyan]{self.tool_name}[/]\n"
                f"Args: [dim]{self.args_preview[:150]}[/]",
                id="perm-label",
            )
            with Horizontal(classes="perm-buttons"):
                yield Button("[y] Allow", id="allow", variant="success")
                yield Button("[n] Deny", id="deny", variant="error")
                yield Button("[a] Always this session", id="always-session")

    @on(Button.Pressed)
    def on_button(self, event: Button.Pressed) -> None:
        if event.button.id == "allow":
            self.dismiss(True)
        elif event.button.id == "deny":
            self.dismiss(False)
        elif event.button.id == "always-session":
            self.dismiss(True)

    def on_key(self, event) -> None:
        if event.key == "y":
            self.dismiss(True)
        elif event.key == "n":
            self.dismiss(False)
        elif event.key == "a":
            self.dismiss(True)


class ModelPickerScreen(ModalScreen[Optional[str]]):
    """Modal to pick or type a model ID — freeform input."""

    CSS = """
    ModelPickerScreen { align: center middle; }
    #model-dialog {
        width: 70; height: auto; max-height: 25;
        border: thick $primary; background: $surface; padding: 1 2;
    }
    """

    def __init__(self, registry: ProviderRegistry, current_model: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.registry = registry
        self.current_model = current_model

    def compose(self) -> ComposeResult:
        with Vertical(id="model-dialog"):
            yield Label(f"[bold]Switch Model[/] (current: [cyan]{self.current_model}[/])")
            yield Label("[dim]Type any model ID, or pick a suggestion below[/]")
            yield Input(
                placeholder="e.g. gpt-4.1, claude-sonnet-4-20250514, deepseek-chat, ...",
                id="model-input",
            )
            yield Label("[dim]Suggestions:[/]")
            yield OptionList(id="model-suggestions")

    def on_mount(self) -> None:
        opt_list = self.query_one("#model-suggestions", OptionList)
        active = self.registry.active()
        suggestions = self.registry.suggestions_for(active.id if active else "")
        if not suggestions:
            # Show from all providers
            for prov in self.registry.list_all():
                for s in self.registry.suggestions_for(prov.id)[:3]:
                    suggestions.append(s)
        for s in suggestions:
            marker = " ✓" if s == self.current_model else ""
            opt_list.add_option(f"{s}{marker}")
        self.query_one("#model-input", Input).focus()

    @on(OptionList.OptionSelected)
    def on_selected(self, event: OptionList.OptionSelected) -> None:
        active = self.registry.active()
        suggestions = self.registry.suggestions_for(active.id if active else "")
        if not suggestions:
            for prov in self.registry.list_all():
                for s in self.registry.suggestions_for(prov.id)[:3]:
                    suggestions.append(s)
        if event.option_index < len(suggestions):
            self.dismiss(suggestions[event.option_index])

    @on(Input.Submitted, "#model-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        model = event.value.strip()
        if model:
            self.dismiss(model)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class SessionPickerScreen(ModalScreen[Optional[str]]):
    """Modal to pick a previous session to resume."""

    CSS = """
    SessionPickerScreen { align: center middle; }
    #session-dialog {
        width: 80; height: auto; max-height: 30;
        border: thick $primary; background: $surface; padding: 1 2;
    }
    """

    def __init__(self, sessions_dir: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sessions_dir = sessions_dir

    def compose(self) -> ComposeResult:
        with Vertical(id="session-dialog"):
            yield Label("[bold]Resume Session[/]")
            yield Label("[dim]Select a session to resume, or press Esc to cancel[/]")
            yield OptionList(id="session-list")

    def on_mount(self) -> None:
        opt_list = self.query_one("#session-list", OptionList)
        sessions = ConversationSession.list_sessions(self.sessions_dir)

        if not sessions:
            opt_list.add_option("[dim]No saved sessions found[/]")
            return

        for i, session in enumerate(sessions):
            time_str = ConversationSession.format_session_time(session["created_at"])
            msg_count = session["message_count"]
            session_id = session["session_id"][:8]
            opt_list.add_option(
                f"{time_str} - {msg_count} messages ({session_id}...)"
            )
        self._sessions = sessions

    @on(OptionList.OptionSelected)
    def on_selected(self, event: OptionList.OptionSelected) -> None:
        if hasattr(self, '_sessions') and event.option_index < len(self._sessions):
            session_path = self._sessions[event.option_index]["path"]
            self.dismiss(session_path)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class SetupScreen(ModalScreen[bool]):
    """First-run setup: protocol + key + model (freeform)."""

    CSS = """
    SetupScreen { align: center middle; }
    #setup-dialog {
        width: 70; height: auto;
        border: thick $success; background: $surface; padding: 1 2;
    }
    #setup-dialog Label { margin: 0 0 1 0; }
    #setup-dialog Input { margin: 0 0 1 0; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="setup-dialog"):
            yield Label("[bold cyan]Qcode Setup[/]\n")
            yield Label("1. Choose API protocol:")
            yield OptionList(
                "OpenAI Compatible  (OpenAI, DeepSeek, OpenRouter, vLLM, any OpenAI-compatible)",
                "Anthropic Native   (Claude models directly)",
                id="protocol-list",
            )
            yield Label("2. API Key:")
            yield Input(password=True, placeholder="sk-...", id="api-key-input")
            yield Label("3. Base URL (leave empty for default):")
            yield Input(placeholder="https://api.example.com/v1", id="base-url-input")
            yield Label("4. Model ID (any model your provider supports):")
            yield Input(placeholder="e.g. gpt-4.1, claude-sonnet-4-20250514, ...", id="model-input")
            yield Label("[dim]Press Enter on model field to save, Esc to cancel[/]")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)

    @on(Input.Submitted, "#model-input")
    def on_model_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip():
            self._save()

    def _save(self) -> None:
        from qcode.config_toml import QcodeConfig, ProviderConfig as ProvCfg
        from qcode.providers.registry import DEFAULT_URLS

        api_key = self.query_one("#api-key-input", Input).value.strip()
        model = self.query_one("#model-input", Input).value.strip()
        base_url = self.query_one("#base-url-input", Input).value.strip()
        protocol_list = self.query_one("#protocol-list", OptionList)
        protocol_idx = protocol_list.highlighted or 0
        protocol = "anthropic" if protocol_idx == 1 else "openai"

        if not api_key or not model:
            return

        if not base_url:
            base_url = DEFAULT_URLS.get(protocol, "")

        prov_id = f"custom-{protocol}"

        cfg = QcodeConfig.load()
        cfg.provider = prov_id
        cfg.model = model
        cfg.providers[prov_id] = ProvCfg(
            protocol=protocol,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
        cfg.save()
        self.dismiss(True)


# ─── Widgets ─────────────────────────────────────────────────────

class StatusBar(Static):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._model = ""
        self._status = "idle"
        self._provider = ""
        self._input_tokens = 0
        self._output_tokens = 0
        self._cache_creation = 0
        self._cache_read = 0
        self._turn_count = 0

    def render(self) -> str:
        token_str = ""
        if self._input_tokens > 0 or self._output_tokens > 0:
            token_str = f" │ {self._input_tokens:,}→{self._output_tokens:,} tok"
            if self._cache_read > 0 or self._cache_creation > 0:
                cache_parts = []
                if self._cache_read > 0:
                    cache_parts.append(f"read:{self._cache_read:,}")
                if self._cache_creation > 0:
                    cache_parts.append(f"write:{self._cache_creation:,}")
                token_str += f" [green](cache {' '.join(cache_parts)})[/]"
        turn_str = f" │ turn {self._turn_count}" if self._turn_count > 0 else ""
        return f" [bold cyan]Qcode[/] │ {self._provider}/{self._model} │ {self._status}{token_str}{turn_str}"

    def update_info(self, provider: str, model: str) -> None:
        self._provider = provider
        self._model = model
        self.refresh()

    def update_status(self, status: str) -> None:
        self._status = status
        self.refresh()

    def update_tokens(self, input_tokens: int, output_tokens: int, cache_creation: int = 0, cache_read: int = 0) -> None:
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._cache_creation = cache_creation
        self._cache_read = cache_read
        self.refresh()

    def increment_turn(self) -> None:
        self._turn_count += 1
        self.refresh()


class ThinkingPanel(Static):
    """Shows the AI's thinking/reasoning process."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._thinking_text = ""
        self._is_thinking = False
        self._collapsed = True

    def render(self) -> str:
        if not self._is_thinking and not self._thinking_text:
            return "[dim]  No thinking[/]"

        lines = []
        if self._is_thinking:
            lines.append("[bold yellow]  Thinking...[/]")
        else:
            lines.append("[bold]  Thinking[/]")

        if self._collapsed and self._thinking_text:
            # Show only last 3 lines when collapsed
            thinking_lines = self._thinking_text.strip().split("\n")
            if len(thinking_lines) > 3:
                lines.append("[dim]  ...[/]")
                for line in thinking_lines[-3:]:
                    lines.append(f"  [dim]{line[:50]}[/]")
            else:
                for line in thinking_lines:
                    lines.append(f"  [dim]{line[:50]}[/]")
        elif self._thinking_text:
            for line in self._thinking_text.strip().split("\n"):
                lines.append(f"  [dim]{line[:50]}[/]")

        lines.append("")
        if self._is_thinking:
            lines.append("[dim]  Esc to stop[/]")
        else:
            lines.append("[dim]  Click to expand[/]")

        return "\n".join(lines)

    def on_click(self) -> None:
        self._collapsed = not self._collapsed
        self.refresh()

    def start_thinking(self) -> None:
        self._is_thinking = True
        self._thinking_text = ""
        self.refresh()

    def add_thinking(self, text: str) -> None:
        self._thinking_text += text
        self.refresh()

    def stop_thinking(self) -> None:
        self._is_thinking = False
        self.refresh()

    def clear(self) -> None:
        self._thinking_text = ""
        self._is_thinking = False
        self.refresh()


class TodoPanel(Static):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._items: List[TodoItem] = []

    def render(self) -> str:
        if not self._items:
            return "[dim]  No active todos[/]"
        lines = ["[bold]  Todo[/]", "─" * 25]
        for item in self._items:
            if item.status == "completed":
                marker = "[green]✓[/]"
            elif item.status == "in_progress":
                marker = "[yellow]▸[/]"
            else:
                marker = "[dim]○[/]"
            text = item.text[:28]
            lines.append(f" {marker} {text}")
        done = sum(1 for i in self._items if i.status == "completed")
        lines.append("")
        lines.append(f" [dim]{done}/{len(self._items)}[/]")
        return "\n".join(lines)

    def update_items(self, items: List[TodoItem]) -> None:
        self._items = items
        self.refresh()


class SessionPanel(Static):
    """Panel showing session statistics and summary."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._turn_count = 0
        self._message_count = 0
        self._tool_calls = 0
        self._last_activity = ""
        self._session_id = ""

    def render(self) -> str:
        lines = ["[bold]  Session[/]", "─" * 25]

        if self._session_id:
            lines.append(f" [dim]ID:[/] {self._session_id[:8]}...")

        lines.append(f" [dim]Turns:[/] {self._turn_count}")
        lines.append(f" [dim]Messages:[/] {self._message_count}")
        lines.append(f" [dim]Tool calls:[/] {self._tool_calls}")

        if self._last_activity:
            lines.append(f" [dim]Last:[/] {self._last_activity}")

        lines.append("")
        lines.append("[dim]  Ctrl+N: New session[/]")

        return "\n".join(lines)

    def update_stats(
        self,
        turn_count: int = 0,
        message_count: int = 0,
        tool_calls: int = 0,
        last_activity: str = "",
        session_id: str = "",
    ) -> None:
        self._turn_count = turn_count
        self._message_count = message_count
        self._tool_calls = tool_calls
        self._last_activity = last_activity
        self._session_id = session_id
        self.refresh()


class ContextPanel(Static):
    """Panel showing project context information."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._context_info: dict = {}

    def render(self) -> str:
        if not self._context_info:
            return "[dim]  Loading context...[/]"

        lines = ["[bold]  Context[/]", "─" * 25]

        # Git branch
        branch = self._context_info.get("git_branch", "")
        if branch:
            lines.append(f" [cyan] {branch}[/]")

        # Git status
        git_status = self._context_info.get("git_status", "")
        if git_status:
            if "clean" in git_status:
                lines.append(f" [green]{git_status}[/]")
            else:
                lines.append(f" [yellow]{git_status}[/]")

        # Recent files
        recent_files = self._context_info.get("recent_files", [])
        if recent_files:
            lines.append("")
            lines.append(" [dim]Recent files:[/]")
            for f in recent_files[:3]:
                # Shorten path
                if len(f) > 25:
                    f = "..." + f[-22:]
                lines.append(f" [dim]  {f}[/]")

        # Project structure
        structure = self._context_info.get("project_structure", "")
        if structure:
            lines.append("")
            lines.append(" [dim]Project:[/]")
            for line in structure.split('\n')[:5]:
                lines.append(f" [dim]{line}[/]")

        return "\n".join(lines)

    def update_context(self, context_info: dict) -> None:
        self._context_info = context_info
        self.refresh()


class TeamPanel(Static):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._members: List[Dict[str, str]] = []

    def render(self) -> str:
        if not self._members:
            return "[dim]  No teammates[/]"
        lines = ["[bold]  Team[/]", "─" * 25]
        for m in self._members:
            name = m.get("name", "?")
            role = m.get("role", "?")
            status = m.get("status", "idle")
            if status == "working":
                icon = "[yellow]⚙[/]"
            elif status == "idle":
                icon = "[dim]◌[/]"
            else:
                icon = "[red]×[/]"
            lines.append(f" {icon} {name} [dim]{role}[/]")
        return "\n".join(lines)

    def update_members(self, members: List[Dict[str, str]]) -> None:
        self._members = members
        self.refresh()


class ChatPanel(RichLog):
    """Enhanced chat panel with message limiting and collapsible tool results."""

    def __init__(
        self,
        max_visible_messages: int = 100,
        tool_result_preview_chars: int = 200,
        **kwargs
    ) -> None:
        super().__init__(markup=True, wrap=True, highlight=True, auto_scroll=False, **kwargs)
        self._streaming_line = ""
        self._streaming_widget: Optional[Static] = None
        self._stream_dirty = False
        self._message_count = 0
        self._max_visible_messages = max_visible_messages
        self._tool_result_preview_chars = tool_result_preview_chars
        self._turn_count = 0
        self._turn_messages: List[str] = []  # Track messages per turn

    def add_user_message(self, text: str) -> None:
        self._flush_streaming()
        self._turn_count += 1
        self._turn_messages = []
        self._message_count += 1

        # Add separator for new turns
        if self._turn_count > 1:
            self.write("\n" + "─" * 50 + "\n")

        self.write(f"\n[bold green]> [/] {text}")
        self._turn_messages.append(f"user: {text[:50]}...")

    def add_assistant_text(self, text: str) -> None:
        # Clear any accumulated streaming text without writing it
        # (we'll write the complete text below)
        self._streaming_line = ""
        self._stream_dirty = False

        self._message_count += 1
        self._turn_messages.append(f"assistant: {text[:50]}...")

        # Write the complete text at once
        self._write_with_code_highlighting(text)

    def _write_with_code_highlighting(self, text: str) -> None:
        """Write text with syntax highlighting for code blocks."""
        import re

        # Split by code blocks
        parts = re.split(r'(```[\s\S]*?```)', text)

        for part in parts:
            if part.startswith('```') and part.endswith('```'):
                # Extract language and code
                lines = part[3:-3].split('\n', 1)
                lang = lines[0].strip() if lines else ''
                code = lines[1] if len(lines) > 1 else ''

                if lang and code:
                    try:
                        from rich.syntax import Syntax
                        syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
                        self.write(syntax)
                    except Exception:
                        # Fallback to plain text
                        self.write(f"[dim]```{lang}[/]\n{code}\n[dim]```[/]")
                elif code:
                    self.write(f"[dim]```[/]\n{code}\n[dim]```[/]")
            else:
                # Regular markdown
                if part.strip():
                    self.write(Markdown(part))

    def add_streaming_delta(self, text: str) -> None:
        """Accumulate streaming text for typewriter effect."""
        self._streaming_line += text
        self._stream_dirty = True

    def flush_streaming(self) -> None:
        """Flush accumulated streaming text."""
        self._flush_streaming()

    def _flush_streaming(self) -> None:
        if self._streaming_line:
            # Write complete text at once
            self._write_streaming_text(self._streaming_line)
            self._streaming_line = ""
            self._stream_dirty = False

    def _write_streaming_text(self, text: str) -> None:
        """Write streaming text with proper formatting."""
        # Process code blocks
        import re
        parts = re.split(r'(```[\s\S]*?```)', text)

        for part in parts:
            if part.startswith('```') and part.endswith('```'):
                # Code block
                lines = part[3:-3].split('\n', 1)
                lang = lines[0].strip() if lines else ''
                code = lines[1] if len(lines) > 1 else ''

                if lang and code:
                    try:
                        from rich.syntax import Syntax
                        syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
                        self.write(syntax)
                    except Exception:
                        self.write(f"[dim]```{lang}[/]\n{code}\n[dim]```[/]")
                elif code:
                    self.write(f"[dim]```[/]\n{code}\n[dim]```[/]")
            else:
                # Regular text - use Text to preserve formatting
                if part.strip():
                    self.write(Text(part))

    def render_streaming_now(self) -> None:
        """Render streaming text with typewriter effect."""
        if self._stream_dirty and self._streaming_line:
            # Write accumulated text
            self._write_streaming_text(self._streaming_line)
            self._streaming_line = ""
            self._stream_dirty = False

    def add_tool_call(self, tool_name: str, args_preview: str = "") -> None:
        self._flush_streaming()
        icons = {
            "bash": "  ", "read_file": "  ", "write_file": "  ",
            "edit_file": "  ✏️", "grep": "  ", "glob": "  ",
            "todo": "  ", "compact": "  ", "task": "  ",
            "git_status": " ", "git_diff": " ", "git_log": " ",
        }
        icon = icons.get(tool_name, "  ")
        preview = f" [dim]{args_preview[:60]}[/]" if args_preview else ""
        self.write(f"{icon}[bold]{tool_name}[/]{preview}")
        self._turn_messages.append(f"tool_call: {tool_name}")
        self._current_tool = tool_name
        self._current_tool_args = args_preview

    def add_tool_result(self, tool_name: str, output: str, is_error: bool = False) -> None:
        self._flush_streaming()
        self._message_count += 1
        self._turn_messages.append(f"tool_result: {tool_name}")

        # For short results, show inline
        if len(output) <= 150 and not is_error:
            self.write(f"[dim]  → {output}[/]")
            return

        # For longer results, show detailed version
        icon = self._get_tool_icon(tool_name)
        error_prefix = "[red]Error: [/]" if is_error else ""

        # Show result summary with line count
        lines = output.split('\n')
        line_count = len(lines)
        char_count = len(output)

        if is_error:
            # Show error with red highlighting
            self.write(f"  {icon} {error_prefix}")
            self.write(f"[red]{output[:500]}[/]")
            if len(output) > 500:
                self.write(f"[dim]... ({char_count} chars total)[/]")
        elif tool_name == "read_file":
            # Show file content with line numbers
            self.write(f"  {icon} [dim]{line_count} lines, {char_count} chars[/]")
            self._show_file_content(output)
        elif tool_name == "bash":
            # Show command output
            self.write(f"  {icon} [dim]{line_count} lines, {char_count} chars[/]")
            self._show_command_output(output)
        elif tool_name in ("grep", "glob"):
            # Show search results
            self.write(f"  {icon} [dim]{line_count} results[/]")
            self._show_search_results(output, tool_name)
        else:
            # Show generic result
            preview = output[:self._tool_result_preview_chars].replace("\n", " ")
            if len(output) > self._tool_result_preview_chars:
                preview += "..."
            self.write(f"  {icon} {error_prefix}[dim]{preview}[/]")

    def _show_file_content(self, content: str) -> None:
        """Show file content with syntax highlighting."""
        lines = content.split('\n')
        # Show first 20 lines with syntax highlighting
        preview_lines = lines[:20]
        preview_content = '\n'.join(preview_lines)

        if len(lines) > 20:
            preview_content += f"\n# ... ({len(lines)} lines total)"

        try:
            from rich.syntax import Syntax
            # Try to detect language from content
            lang = self._detect_language_from_content(content)
            syntax = Syntax(preview_content, lang, theme="monokai", line_numbers=True)
            self.write(syntax)
        except Exception:
            # Fallback to plain text
            for i, line in enumerate(preview_lines[:10], 1):
                self.write(f"[dim]{i:3}[/] {line}")
            if len(lines) > 10:
                self.write(f"[dim]... ({len(lines)} lines total)[/]")

    def _show_command_output(self, content: str) -> None:
        """Show command output with syntax highlighting."""
        lines = content.split('\n')
        # Show first 30 lines
        preview_lines = lines[:30]
        preview_content = '\n'.join(preview_lines)

        if len(lines) > 30:
            preview_content += f"\n# ... ({len(lines)} lines total)"

        try:
            from rich.syntax import Syntax
            syntax = Syntax(preview_content, "bash", theme="monokai", line_numbers=False)
            self.write(syntax)
        except Exception:
            # Fallback to plain text
            for line in preview_lines[:15]:
                self.write(f"[dim]  {line}[/]")
            if len(lines) > 15:
                self.write(f"[dim]... ({len(lines)} lines total)[/]")

    def _show_search_results(self, content: str, tool_name: str) -> None:
        """Show search results with highlighting."""
        lines = content.split('\n')
        # Show first 20 results
        preview_lines = lines[:20]

        for line in preview_lines:
            # Highlight matches
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    file_path, match = parts
                    # Highlight file path
                    self.write(f"[cyan]{file_path}[/]:{match}")
                    continue
            self.write(f"[dim]  {line}[/]")

        if len(lines) > 20:
            self.write(f"[dim]... ({len(lines)} results total)[/]")

    def _detect_language_from_content(self, content: str) -> str:
        """Detect programming language from file content."""
        # Simple heuristics
        if content.strip().startswith('#!'):
            if 'python' in content[:100]:
                return 'python'
            if 'bash' in content[:100] or 'sh' in content[:100]:
                return 'bash'
            if 'node' in content[:100]:
                return 'javascript'

        # Check for common patterns
        if 'def ' in content and ':' in content:
            return 'python'
        if 'function ' in content and '{' in content:
            return 'javascript'
        if 'class ' in content and '{' in content:
            return 'java'
        if '#include' in content:
            return 'c'
        if 'import ' in content and 'from ' in content:
            return 'python'

        return 'text'

    def _get_tool_icon(self, tool_name: str) -> str:
        """Get icon for tool type."""
        icons = {
            "bash": "  ", "read_file": "  ", "write_file": "  ",
            "edit_file": "  ✏️", "grep": "  ", "glob": "  ",
            "todo": "  ", "compact": "  ", "task": "  ",
            "git_status": " ", "git_diff": " ", "git_log": " ",
        }
        return icons.get(tool_name, "  ")

    def _detect_language(self, tool_name: str, output: str) -> str:
        """Detect programming language for syntax highlighting."""
        if tool_name == "grep":
            # Try to detect from file extensions in grep output
            import re
            match = re.search(r'\.(\w+):', output[:100])
            if match:
                ext = match.group(1).lower()
                lang_map = {
                    "py": "python", "js": "javascript", "ts": "typescript",
                    "jsx": "javascript", "tsx": "typescript", "rs": "rust",
                    "go": "go", "rb": "ruby", "java": "java", "c": "c",
                    "cpp": "cpp", "h": "c", "hpp": "cpp", "sh": "bash",
                    "bash": "bash", "zsh": "zsh", "json": "json", "yaml": "yaml",
                    "yml": "yaml", "toml": "toml", "md": "markdown", "html": "html",
                    "css": "css", "sql": "sql", "xml": "xml",
                }
                return lang_map.get(ext, "")
        return ""

    def add_system(self, text: str) -> None:
        self._flush_streaming()
        self.write(f"[dim italic]{text}[/]")

    def add_error(self, text: str) -> None:
        self._flush_streaming()
        self.write(f"[bold red]Error:[/] {text}")

    def get_turn_summary(self) -> str:
        """Get a summary of the current turn's messages."""
        if not self._turn_messages:
            return ""
        return f"Turn {self._turn_count}: {len(self._turn_messages)} messages"

    def clear_old_messages(self, keep_recent: int = 50) -> None:
        """Clear old messages to free memory (placeholder for future implementation)."""
        # Note: RichLog doesn't support removing old messages easily
        # In a full implementation, we'd maintain a message buffer and rebuild
        pass


# ─── Main App ────────────────────────────────────────────────────

class QcodeApp(App):
    CSS = """
    Screen { layout: vertical; }
    #status-bar {
        height: 1; dock: top;
        background: $primary-background-darken-1; color: $text; padding: 0 1;
    }
    #main-area { height: 1fr; }
    #chat-panel {
        width: 1fr; height: 1fr; border: solid $primary; margin: 0 0 0 1;
    }
    #sidebar {
        width: 32; height: 1fr; border: solid $primary; margin: 0 1 0 0;
        overflow-y: auto;
    }
    #sidebar Collapsible {
        margin: 0;
        border: none;
    }
    #sidebar Collapsible > Title {
        background: $primary-background-darken-1;
        padding: 0 1;
    }
    #thinking-panel {
        height: auto; max-height: 10;
        overflow-y: auto; background: $surface-darken-1;
    }
    #todo-panel {
        height: auto; max-height: 15;
        overflow-y: auto;
    }
    #team-panel { height: auto; max-height: 10; overflow-y: auto; }
    #git-panel { height: auto; padding: 0 1; }
    #input-area { height: auto; max-height: 10; margin: 0 1 1 1; }
    #prompt-input { border: solid $primary; }
    #hint-bar {
        height: 1; dock: bottom;
        background: $primary-background-darken-1; color: $text-muted; padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "interrupt_or_quit", "Quit"),
        Binding("ctrl+n", "new_session", "New"),
        Binding("ctrl+r", "resume_session", "Resume"),
        Binding("ctrl+l", "clear_chat", "Clear"),
        Binding("ctrl+t", "toggle_sidebar", "Sidebar"),
        Binding("ctrl+m", "pick_model", "Model"),
        Binding("ctrl+d", "toggle_detail", "Detail", show=False),
        Binding("ctrl+shift+c", "copy_last", "Copy", show=False),
        Binding("escape", "stop", "Stop", show=False),
    ]

    TITLE = "Qcode"

    def __init__(
        self,
        engine: AgentEngine,
        config: AppConfig,
        provider_registry: ProviderRegistry,
        session: Optional[ConversationSession] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.engine = engine
        self.config = config
        self.registry = provider_registry
        self.session = session or ConversationSession()
        self._streaming_text = ""
        self._is_running = False
        self._always_allow: set = set()
        self._global_always_allow: set = set()
        self._sidebar_visible = True
        self._completions: List[str] = []
        self._completion_index = 0
        self._stream_refresh_task: Optional[asyncio.Task] = None
        self._reasoning_shown = False
        self._last_assistant_message: str = ""
        self._load_global_permissions()

    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        with Horizontal(id="main-area"):
            with Vertical(id="sidebar"):
                with Collapsible(title="Thinking", collapsed=False, id="thinking-collapse"):
                    yield ThinkingPanel(id="thinking-panel")
                with Collapsible(title="Context", collapsed=False, id="context-collapse"):
                    yield ContextPanel(id="context-panel")
                with Collapsible(title="Session", collapsed=False, id="session-collapse"):
                    yield SessionPanel(id="session-panel")
                with Collapsible(title="Todo", collapsed=False, id="todo-collapse"):
                    yield TodoPanel(id="todo-panel")
                with Collapsible(title="Team", collapsed=True, id="team-collapse"):
                    yield TeamPanel(id="team-panel")
                with Collapsible(title="Git", collapsed=True, id="git-collapse"):
                    yield Static("[dim]  Click to refresh[/]", id="git-panel")
            yield ChatPanel(id="chat-panel")
        with Vertical(id="input-area"):
            yield Input(
                placeholder="Type a message... (Tab=@files, Ctrl+M=model, Ctrl+T=sidebar)",
                id="prompt-input",
                suggester=None,
                tooltip="",
            )
        yield Static(
            " [dim]Esc/Ctrl+C=stop  Ctrl+N=new  Ctrl+R=resume  Ctrl+L=clear  Ctrl+M=model  Ctrl+T=sidebar  Ctrl+D=detail  Tab=@file  /=cmd[/]",
            id="hint-bar",
        )

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()
        self._update_status_bar()
        self._refresh_todo_panel()
        self._refresh_team_panel()
        self._refresh_git_panel_async()
        self._refresh_context_panel_async()
        self._load_memory()

    def _refresh_git_panel(self) -> None:
        """Refresh git status in the sidebar (blocking, use _refresh_git_panel_async)."""
        import subprocess
        try:
            panel = self.query_one("#git-panel", Static)
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=self.config.workdir
            ).stdout.strip()

            status = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, cwd=self.config.workdir
            ).stdout.strip()

            if not branch:
                panel.update("[dim]  Not a git repo[/]")
                return

            lines = [f"[bold]  {branch}[/]"]
            if status:
                changed = len(status.split("\n"))
                lines.append(f"[yellow]  {changed} changed[/]")
            else:
                lines.append("[green]  clean[/]")

            panel.update("\n".join(lines))
        except Exception:
            pass

    @work(thread=True)
    def _refresh_git_panel_async(self) -> None:
        """Non-blocking git panel refresh."""
        self._refresh_git_panel()

    def _refresh_context_panel(self) -> None:
        """Refresh context panel with project information."""
        try:
            panel = self.query_one("#context-panel", ContextPanel)
            context_info = self._gather_context_info()
            panel.update_context(context_info)
        except Exception:
            pass

    def _gather_context_info(self) -> dict:
        """Gather project context information."""
        import subprocess
        from pathlib import Path

        info = {
            "git_branch": "",
            "git_status": "",
            "recent_files": [],
            "project_structure": "",
            "current_dir": str(self.config.workdir),
        }

        # Git branch
        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=self.config.workdir
            ).stdout.strip()
            info["git_branch"] = branch
        except Exception:
            pass

        # Git status
        try:
            status = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, cwd=self.config.workdir
            ).stdout.strip()
            if status:
                lines = status.split('\n')
                info["git_status"] = f"{len(lines)} files changed"
            else:
                info["git_status"] = "clean"
        except Exception:
            pass

        # Recent files (from git log)
        try:
            recent = subprocess.run(
                ["git", "log", "--oneline", "-5", "--name-only"],
                capture_output=True, text=True, cwd=self.config.workdir
            ).stdout.strip()
            if recent:
                files = []
                for line in recent.split('\n'):
                    if line and not line.startswith(' '):
                        # This is a commit message line
                        continue
                    if line.strip() and '.' in line:
                        files.append(line.strip())
                info["recent_files"] = files[:5]
        except Exception:
            pass

        # Project structure (top-level)
        try:
            workdir = Path(self.config.workdir)
            items = []
            for item in sorted(workdir.iterdir()):
                if item.name.startswith('.'):
                    continue
                if item.is_dir():
                    items.append(f"  {item.name}/")
                else:
                    items.append(f"  {item.name}")
            info["project_structure"] = '\n'.join(items[:15])
        except Exception:
            pass

        return info

    @work(thread=True)
    def _refresh_context_panel_async(self) -> None:
        """Non-blocking context panel refresh."""
        self._refresh_context_panel()

    # ─── Status bar ──────────────────────────────────────────────

    def _update_status_bar(self) -> None:
        bar = self.query_one("#status-bar", StatusBar)
        active = self.registry.active()
        provider_name = active.name if active else "unknown"
        bar.update_info(provider_name, self.config.model)

    def _update_session_panel(self) -> None:
        """Update the session statistics panel."""
        try:
            panel = self.query_one("#session-panel", SessionPanel)
            chat = self.query_one("#chat-panel", ChatPanel)
            panel.update_stats(
                turn_count=chat._turn_count,
                message_count=chat._message_count,
                tool_calls=sum(1 for m in chat._turn_messages if m.startswith("tool_call:")),
                last_activity=time.strftime("%H:%M"),
                session_id=self.session.session_id,
            )
        except Exception:
            pass

    # ─── Memory (CLAUDE.md equivalent) ───────────────────────────

    def _load_memory(self) -> None:
        """Load ~/.qcode/projects/<hash>/memory.md and inject as system context."""
        memory_path = self._get_memory_path()
        if memory_path.exists():
            content = memory_path.read_text(encoding="utf-8").strip()
            if content:
                chat = self.query_one("#chat-panel", ChatPanel)
                chat.add_system(f"Loaded project memory: {memory_path.name}")

    def _get_memory_path(self) -> Path:
        cwd = str(self.config.workdir)
        h = hashlib.md5(cwd.encode()).hexdigest()[:12]
        return QCODE_HOME / "projects" / h / "memory.md"

    # ─── Input handling ──────────────────────────────────────────

    @on(Input.Changed, "#prompt-input")
    def on_input_changed(self, event: Input.Changed) -> None:
        text = event.value
        cursor = event.input.cursor_position
        partial = extract_at_reference(text, cursor)
        if partial is not None:
            self._completions = get_file_completions(partial, self.config.workdir)
        else:
            self._completions = []

    def on_key(self, event) -> None:
        # Handle Escape explicitly — stop running agent or blur input
        if event.key == "escape":
            if self._is_running:
                self.engine.request_cancel()
            else:
                # Blur the input so focus returns to the app
                self.query_one("#prompt-input", Input).blur()
            event.prevent_default()
            return

        if event.key == "tab" and self._completions:
            event.prevent_default()
            input_widget = self.query_one("#prompt-input", Input)
            text = input_widget.value
            cursor = input_widget.cursor_position
            if self._completions:
                completion = self._completions[self._completion_index % len(self._completions)]
                new_text, new_cursor = replace_at_reference(text, cursor, completion)
                input_widget.value = new_text
                input_widget.cursor_position = new_cursor
                self._completion_index += 1
            return
        self._completion_index = 0

    @on(Input.Submitted, "#prompt-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        self._completions = []
        if text.startswith("/"):
            self._handle_slash_command(text)
            return
        self._run_agent(text)

    # ─── Agent execution ─────────────────────────────────────────

    @work(exclusive=True)
    async def _run_agent(self, user_text: str) -> None:
        if self._is_running:
            return
        self._is_running = True
        self._streaming_text = ""
        self._reasoning_shown = False
        status = self.query_one("#status-bar", StatusBar)
        status.update_status("thinking")
        chat = self.query_one("#chat-panel", ChatPanel)
        thinking = self.query_one("#thinking-panel", ThinkingPanel)
        thinking.clear()
        chat.add_user_message(user_text)
        self.session.add_user_text(user_text)

        # Start streaming refresh task for typewriter effect
        self._stream_refresh_task = asyncio.create_task(self._stream_refresh_loop())

        try:
            async for event in self.engine.run_events(self.session):
                self._handle_engine_event(event)
                if event.type == "tool_result":
                    self._refresh_todo_panel()
                    self._update_session_panel()
                if event.type == "assistant_message":
                    self._update_session_panel()
                if event.type == "stopped":
                    chat.add_system(f"[yellow]Stopped: {event.data.get('reason', 'cancelled')}[/]")
                # Yield to the event loop so UI stays responsive (clicks, key presses)
                await asyncio.sleep(0)
        except Exception as exc:
            chat.add_error(str(exc))
        finally:
            # Cancel streaming refresh task
            if self._stream_refresh_task:
                self._stream_refresh_task.cancel()
                self._stream_refresh_task = None
            # Flush any remaining streaming text
            chat = self.query_one("#chat-panel", ChatPanel)
            chat.flush_streaming()
            self._is_running = False
            self._streaming_text = ""
            status.update_status("idle")
            self._update_session_panel()
            self._auto_save_session()

    async def _stream_refresh_loop(self) -> None:
        """Periodically flush streaming content for typewriter effect."""
        while True:
            await asyncio.sleep(0.05)  # ~20 fps for smooth typewriter effect
            try:
                chat = self.query_one("#chat-panel", ChatPanel)
                # Flush if we have any streaming text
                if self._streaming_text:
                    chat.render_streaming_now()
            except Exception:
                pass

    def _auto_save_session(self) -> None:
        sessions_dir = self.config.workdir / ".qcode" / "sessions"
        self.session.save(sessions_dir)

    def _get_tool_status_text(self, tool_name: str, args: str) -> str:
        """Generate human-readable status text for tool calls."""
        import json

        # Try to parse arguments for better display
        try:
            if isinstance(args, str) and args.startswith('{'):
                args_dict = json.loads(args)
            else:
                args_dict = {}
        except (json.JSONDecodeError, TypeError):
            args_dict = {}

        if tool_name == "read_file":
            path = args_dict.get("path", "")
            if path:
                # Show just filename, not full path
                filename = Path(path).name
                return f"reading {filename}"
            return "reading file"

        elif tool_name == "write_file":
            path = args_dict.get("path", "")
            if path:
                filename = Path(path).name
                return f"writing {filename}"
            return "writing file"

        elif tool_name == "edit_file":
            path = args_dict.get("path", "")
            if path:
                filename = Path(path).name
                return f"editing {filename}"
            return "editing file"

        elif tool_name == "bash":
            command = args_dict.get("command", "")
            if command:
                # Show first 30 chars of command
                cmd_preview = command[:30] + ("..." if len(command) > 30 else "")
                return f"running: {cmd_preview}"
            return "running command"

        elif tool_name == "grep":
            pattern = args_dict.get("pattern", "")
            if pattern:
                return f"searching: {pattern[:20]}"
            return "searching"

        elif tool_name == "glob":
            pattern = args_dict.get("pattern", "")
            if pattern:
                return f"finding: {pattern[:20]}"
            return "finding files"

        elif tool_name == "todo":
            return "managing todos"

        elif tool_name == "compact":
            return "compacting context"

        elif tool_name == "task":
            return "managing tasks"

        elif tool_name == "grep":
            pattern = args_dict.get("pattern", "")
            if pattern:
                return f"searching: {pattern[:20]}"
            return "searching"

        elif tool_name == "glob":
            pattern = args_dict.get("pattern", "")
            if pattern:
                return f"finding: {pattern[:20]}"
            return "finding files"

        elif tool_name == "list_directory":
            path = args_dict.get("path", ".")
            return f"listing {path}"

        elif tool_name == "git_status":
            return "checking git status"

        elif tool_name == "git_diff":
            return "showing git diff"

        elif tool_name == "git_log":
            return "showing git log"

        elif tool_name == "git_commit":
            message = args_dict.get("message", "")
            if message:
                return f"committing: {message[:20]}"
            return "committing"

        elif tool_name == "git_branch":
            return "listing branches"

        else:
            return f"tool: {tool_name}"

    def _handle_engine_event(self, event: EngineEvent) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        status = self.query_one("#status-bar", StatusBar)
        thinking = self.query_one("#thinking-panel", ThinkingPanel)

        if event.type == "text_delta":
            text = event.data.get("text", "")
            self._streaming_text += text
            chat.add_streaming_delta(text)
            status.update_status("responding")
            # Stop thinking indicator when response starts
            if self._reasoning_shown:
                thinking.stop_thinking()
                self._reasoning_shown = False

        elif event.type == "assistant_message":
            content = event.data.get("content", "")
            # Safety: extract text if content is a list of blocks
            if isinstance(content, list):
                text_parts = [
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                content = "".join(text_parts)

            # Use the content from event, or fall back to accumulated streaming text
            if content:
                final_content = content
            elif self._streaming_text:
                final_content = self._streaming_text
            else:
                final_content = ""

            if final_content:
                self._last_assistant_message = final_content
                chat.add_assistant_text(final_content)

            self._streaming_text = ""
            thinking.stop_thinking()
            status.increment_turn()

        elif event.type == "reasoning_delta":
            # Show thinking in the ThinkingPanel
            text = event.data.get("text", "")
            if not self._reasoning_shown:
                self._reasoning_shown = True
                thinking.start_thinking()
                status.update_status("thinking")
            thinking.add_thinking(text)

        elif event.type == "tool_call":
            tool_name = event.data.get("tool_name", "")
            args = event.data.get("arguments", "")
            # Parse arguments for better status display
            args_str = str(args)
            status_text = self._get_tool_status_text(tool_name, args_str)
            status.update_status(status_text)
            chat.add_tool_call(tool_name, args_str[:80])

        elif event.type == "tool_result":
            tool_name = event.data.get("tool_name", "")
            content = event.data.get("content", "")
            if isinstance(content, list):
                content = str(content)
            is_error = content.startswith("Error:") if content else False
            chat.add_tool_result(tool_name, content, is_error)

        elif event.type == "model_request":
            status.update_status("thinking")
            thinking.start_thinking()
            self._reasoning_shown = True

        elif event.type == "usage":
            input_tokens = event.data.get("input_tokens", 0)
            output_tokens = event.data.get("output_tokens", 0)
            cache_creation = event.data.get("cache_creation_tokens", 0)
            cache_read = event.data.get("cache_read_tokens", 0)
            status.update_tokens(input_tokens, output_tokens, cache_creation, cache_read)

        elif event.type == "error":
            chat.add_error(event.data.get("message", "Unknown error"))
            thinking.stop_thinking()

        elif event.type == "stopped":
            # Handled in _run_agent
            thinking.stop_thinking()

    # ─── Slash commands ──────────────────────────────────────────

    def _handle_slash_command(self, command: str) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        parts = command.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/help":
            chat.add_system(
                "**Commands:**\n"
                "  /help          Show this help\n"
                "  /resume        Resume a previous session\n"
                "  /clear         Clear session\n"
                "  /compact       Compress context\n"
                "  /model [id]    Switch model\n"
                "  /todo          Show todo list\n"
                "  /team          Show team status\n"
                "  /task          Show tasks\n"
                "  /save          Save session\n"
                "  /load [id]     Load session\n"
                "  /config        Show config\n"
                "  /memory        Edit memory\n"
                "  /setup         Run setup\n"
                "  /goal [text]   Set/clear goal\n"
                "  /git           Show git status\n"
                "  /diff [file]   Show git diff\n"
                "  /tree [path]   Show file tree\n"
                "  /copy          Copy last message to clipboard\n"
                "  /instructions  Show custom instructions\n"
                "\n**Shortcuts:**\n"
                "  Esc/Ctrl+C     Stop/Quit\n"
                "  Ctrl+N         New session\n"
                "  Ctrl+R         Resume session\n"
                "  Ctrl+M         Switch model\n"
                "  Ctrl+T         Toggle sidebar\n"
                "  Ctrl+L         Clear screen"
            )
        elif cmd == "/clear":
            self.session = ConversationSession()
            chat.add_system("Session cleared.")
        elif cmd == "/compact":
            self.session.request_compaction()
            chat.add_system("Compaction requested.")
        elif cmd == "/model":
            if arg:
                self._switch_model(arg)
            else:
                self._show_model_list()
        elif cmd == "/todo":
            self._show_todo_in_chat()
        elif cmd == "/team":
            self._show_team_in_chat()
        elif cmd == "/task":
            self._show_tasks_in_chat()
        elif cmd == "/save":
            sessions_dir = self.config.workdir / ".qcode" / "sessions"
            path = self.session.save(sessions_dir)
            chat.add_system(f"Saved: {path.name}")
        elif cmd == "/load":
            self._load_session(arg)
        elif cmd == "/cost":
            chat.add_system("Cost tracking not yet implemented.")
        elif cmd == "/config":
            self._show_config()
        elif cmd == "/memory":
            self._edit_memory()
        elif cmd == "/setup":
            self._run_setup()
        elif cmd == "/goal":
            self._handle_goal_command(arg)
        elif cmd == "/instructions":
            self._show_instructions()
        elif cmd == "/git":
            self._show_git_status()
        elif cmd == "/diff":
            self._show_git_diff(arg)
        elif cmd == "/tree":
            self._show_file_tree(arg)
        elif cmd == "/copy":
            self._copy_last_message()
        elif cmd == "/resume":
            self._resume_session()
        else:
            chat.add_system(f"Unknown: {cmd}. Type /help")

    def _switch_model(self, model_id: str) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        # Find which provider has this model or use active provider
        provider = self.registry.active()
        if not provider:
            chat.add_system("No active provider. Run /setup first.")
            return

        # Update provider's model
        provider.model = model_id

        self.config = AppConfig.from_env(
            workdir=self.config.workdir,
            overrides={
                "model": model_id,
                "api_base_url": provider.effective_base_url,
                "api_key": provider.api_key,
                "api_wire_api": provider.protocol,
            },
        )
        from qcode.app import build_engine_for_tui
        self.engine = build_engine_for_tui(self.config)
        self.engine.tool_executor.permission_checker = self._permission_checker
        self._update_status_bar()
        chat.add_system(f"Switched to model: [cyan]{model_id}[/] ({provider.name})")

    def _show_model_list(self) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        active = self.registry.active()
        if not active:
            chat.add_system("No provider configured. Run /setup.")
            return
        suggestions = self.registry.suggestions_for(active.id)
        lines = [f"**Model Selection** (provider: {active.name}, protocol: {active.protocol})"]
        lines.append(f"\nCurrent: `{self.config.model}`")
        if suggestions:
            lines.append(f"\nSuggestions for {active.name}:")
            for s in suggestions:
                marker = " ←" if s == self.config.model else ""
                lines.append(f"  `{s}`{marker}")
        lines.append(f"\nType any model ID: `/model <id>`")
        lines.append(f"Or press Ctrl+M to open the picker.")
        chat.add_assistant_text("\n".join(lines))

    def _show_config(self) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        from qcode.config_toml import QcodeConfig
        cfg = QcodeConfig.load()
        lines = ["**Configuration** (`~/.qcode/config.toml`)"]
        lines.append(f"  provider: `{cfg.provider}`")
        lines.append(f"  model: `{cfg.model}`")
        lines.append(f"  max_tokens: `{cfg.max_tokens}`")
        for name, prov in cfg.providers.items():
            masked = prov.api_key[:8] + "..." if len(prov.api_key) > 8 else "(not set)"
            lines.append(f"  [{name}] key={masked} base_url={prov.base_url}")
        chat.add_assistant_text("\n".join(lines))

    def _edit_memory(self) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        memory_path = self._get_memory_path()
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        if not memory_path.exists():
            memory_path.write_text(
                f"# Project Memory for {self.config.workdir}\n\n"
                "Add project-specific context, conventions, and notes here.\n"
                "This file is automatically loaded into the agent's context.\n",
                encoding="utf-8",
            )
        chat.add_system(f"Memory file: {memory_path}")
        chat.add_system("Edit it with your editor, then restart Qcode to load changes.")

    def _run_setup(self) -> None:
        self.push_screen(SetupScreen(), callback=self._on_setup_complete)

    def _handle_goal_command(self, arg: str) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        goal_store = self.engine.goal_store

        if not goal_store:
            chat.add_system("[yellow]No goal store available.[/]")
            return

        if not arg:
            current = goal_store.get()
            if current:
                chat.add_system(f"**Current goal:** {current}")
                chat.add_system("Use `/goal clear` to remove, or `/goal <text>` to set a new one.")
            else:
                chat.add_system("No active goal. Use `/goal <text>` to set one.")
        elif arg.strip().lower() == "clear":
            goal_store.clear()
            chat.add_system("[green]Goal cleared.[/]")
        else:
            goal_store.set(arg)
            chat.add_system(f"[green]Goal set:[/] {arg}")

    def _show_instructions(self) -> None:
        """Show custom instructions."""
        chat = self.query_one("#chat-panel", ChatPanel)
        from pathlib import Path

        global_path = Path.home() / ".qcode" / "instructions.md"
        project_path = self.config.workdir / ".qcode" / "instructions.md"

        lines = ["**Custom Instructions**"]
        lines.append("")

        if global_path.exists():
            content = global_path.read_text(encoding="utf-8").strip()
            lines.append(f"**Global** (`{global_path}`):")
            lines.append(content if content else "(empty)")
        else:
            lines.append(f"**Global**: Not created yet")
            lines.append(f"  Create `{global_path}` to add global instructions")

        lines.append("")

        if project_path.exists():
            content = project_path.read_text(encoding="utf-8").strip()
            lines.append(f"**Project** (`{project_path}`):")
            lines.append(content if content else "(empty)")
        else:
            lines.append(f"**Project**: Not created yet")
            lines.append(f"  Create `{project_path}` to add project-specific instructions")

        chat.add_assistant_text("\n".join(lines))

    def _show_git_status(self) -> None:
        """Show git status."""
        chat = self.query_one("#chat-panel", ChatPanel)
        import subprocess

        try:
            # Get current branch
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, cwd=self.config.workdir
            ).stdout.strip()

            # Get status
            status = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, cwd=self.config.workdir
            ).stdout.strip()

            # Get recent commits
            log = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True, text=True, cwd=self.config.workdir
            ).stdout.strip()

            lines = [f"**Git Status** (branch: `{branch}`)"]
            lines.append("")

            if status:
                lines.append("**Changes:**")
                for line in status.split("\n")[:20]:
                    lines.append(f"  {line}")
                if status.count("\n") > 20:
                    lines.append(f"  ... and {status.count(chr(10)) - 20} more")
            else:
                lines.append("Working tree clean")

            lines.append("")
            if log:
                lines.append("**Recent commits:**")
                for line in log.split("\n"):
                    lines.append(f"  {line}")

            chat.add_assistant_text("\n".join(lines))
        except Exception as e:
            chat.add_error(f"Git error: {e}")

    def _show_git_diff(self, path: str = "") -> None:
        """Show git diff with syntax highlighting."""
        chat = self.query_one("#chat-panel", ChatPanel)
        import subprocess

        try:
            cmd = ["git", "diff"]
            if path:
                cmd.extend(["--", path])

            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=self.config.workdir
            )

            if not result.stdout.strip():
                chat.add_system("No changes to show.")
                return

            # Show diff with syntax highlighting
            from rich.syntax import Syntax
            diff_syntax = Syntax(result.stdout, "diff", theme="monokai", line_numbers=False)
            chat.write(diff_syntax)
        except Exception as e:
            chat.add_error(f"Git diff error: {e}")

    def _show_file_tree(self, path: str = ".") -> None:
        """Show file tree structure."""
        chat = self.query_one("#chat-panel", ChatPanel)
        import subprocess

        try:
            # Use tree command if available, otherwise use find
            result = subprocess.run(
                ["tree", "-L", "3", "--dirsfirst", "-I", "__pycache__|.git|.venv|node_modules", path],
                capture_output=True, text=True, cwd=self.config.workdir
            )

            if result.returncode != 0:
                # Fallback to find
                result = subprocess.run(
                    ["find", path, "-maxdepth", "3", "-type", "f", "-not", "*/__pycache__/*", "-not", "*/.git/*"],
                    capture_output=True, text=True, cwd=self.config.workdir
                )

            if not result.stdout.strip():
                chat.add_system("No files found.")
                return

            lines = [f"**File Tree** (`{path}`)"]
            lines.append("")
            lines.append(result.stdout)
            chat.add_assistant_text("\n".join(lines))
        except Exception as e:
            chat.add_error(f"Tree error: {e}")

    def _copy_last_message(self) -> None:
        """Copy last assistant message to clipboard."""
        chat = self.query_one("#chat-panel", ChatPanel)

        if not self._last_assistant_message:
            chat.add_system("[yellow]No message to copy.[/]")
            return

        # Try to copy to clipboard
        import subprocess
        try:
            # Try xclip (Linux)
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=self._last_assistant_message.encode(),
                check=True
            )
            chat.add_system("[green]Copied to clipboard![/]")
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                # Try pbcopy (macOS)
                subprocess.run(
                    ["pbcopy"],
                    input=self._last_assistant_message.encode(),
                    check=True
                )
                chat.add_system("[green]Copied to clipboard![/]")
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback: show the message
                chat.add_system("**Last message:**")
                chat.add_assistant_text(self._last_assistant_message)

    def _on_setup_complete(self, result: bool) -> None:
        if result:
            chat = self.query_one("#chat-panel", ChatPanel)
            chat.add_system("Configuration saved. Restart Qcode to apply.")

    def _show_todo_in_chat(self) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        todos = self.session.todo_manager.items
        if not todos:
            chat.add_system("No active todos.")
            return
        lines = ["**Todo List**"]
        for item in todos:
            marker = {"pending": "○", "in_progress": "▸", "completed": "✓"}[item.status]
            lines.append(f"  {marker} #{item.item_id}: {item.text}")
        chat.add_assistant_text("\n".join(lines))

    def _show_team_in_chat(self) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        team_dir = self.config.workdir / ".team"
        config_path = team_dir / "config.json"
        if not config_path.exists():
            chat.add_system("No team configured.")
            return
        data = json.loads(config_path.read_text())
        members = data.get("members", [])
        lines = [f"**Team: {data.get('team_name', 'default')}**"]
        for m in members:
            status = m.get("status", "idle")
            lines.append(f"  {m['name']} ({m.get('role', '?')}): {status}")
        chat.add_assistant_text("\n".join(lines))

    def _show_tasks_in_chat(self) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        task_dir = self.config.workdir / ".tasks"
        if not task_dir.exists():
            chat.add_system("No tasks.")
            return
        tasks = []
        for f in sorted(task_dir.glob("task_*.json")):
            try:
                tasks.append(json.loads(f.read_text()))
            except Exception:
                continue
        if not tasks:
            chat.add_system("No tasks.")
            return
        lines = ["**Task List**"]
        for t in tasks:
            marker = {"pending": "○", "in_progress": "▸", "completed": "✓"}.get(t.get("status"), "?")
            owner = t.get("owner", "")
            owner_str = f" [{owner}]" if owner else ""
            lines.append(f"  {marker} #{t.get('id')}: {t.get('subject', '?')}{owner_str}")
        chat.add_assistant_text("\n".join(lines))

    def _load_session(self, arg: str) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        sessions_dir = self.config.workdir / ".qcode" / "sessions"
        if arg:
            path = sessions_dir / arg
        else:
            path = ConversationSession.find_latest(sessions_dir)
        if path and path.exists():
            self.session = ConversationSession.load(path)
            chat.add_system(f"Loaded: {path.name} ({len(self.session)} messages)")
        else:
            chat.add_system("No session found.")

    def _resume_session(self) -> None:
        """Show session picker to resume a previous session."""
        sessions_dir = self.config.workdir / ".qcode" / "sessions"

        def on_session_selected(path: Optional[str]) -> None:
            if path:
                chat = self.query_one("#chat-panel", ChatPanel)
                try:
                    self.session = ConversationSession.load(Path(path))
                    chat.clear()
                    chat.add_system(f"[green]Session resumed: {len(self.session)} messages loaded[/]")

                    # Re-display recent messages for context
                    recent_messages = self.session.messages[-10:]  # Show last 10 messages
                    for msg in recent_messages:
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        if isinstance(content, str):
                            if role == "user":
                                chat.add_user_message(content[:200])
                            elif role == "assistant":
                                chat.add_assistant_text(content[:200])

                    self._update_session_panel()
                except Exception as e:
                    chat.add_error(f"Failed to load session: {e}")

        self.push_screen(SessionPickerScreen(sessions_dir), on_session_selected)

    # ─── Sidebar refresh ─────────────────────────────────────────

    def _refresh_todo_panel(self) -> None:
        self.query_one("#todo-panel", TodoPanel).update_items(self.session.todo_manager.items)

    def _refresh_team_panel(self) -> None:
        panel = self.query_one("#team-panel", TeamPanel)
        team_dir = self.config.workdir / ".team"
        config_path = team_dir / "config.json"
        if config_path.exists():
            data = json.loads(config_path.read_text())
            panel.update_members(data.get("members", []))

    # ─── Permission ──────────────────────────────────────────────

    def _permission_checker(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Called from ThreadPoolExecutor thread — must use threading primitives."""
        safe_tools = {"read_file", "grep", "glob", "todo", "compact", "bash"}
        if tool_name in safe_tools:
            return "allow"
        if tool_name in self._always_allow:
            return "allow"
        if tool_name in self._global_always_allow:
            return "allow"

        # For now, auto-allow all tools (permission dialog needs Textual threading fix)
        return "allow"

    def _load_global_permissions(self) -> None:
        from qcode.config_toml import QcodeConfig
        cfg = QcodeConfig.load()
        self._global_always_allow = set(cfg.permission.auto_allow)

    # ─── Model picker ────────────────────────────────────────────

    def action_pick_model(self) -> None:
        self.push_screen(
            ModelPickerScreen(self.registry, self.config.model),
            callback=self._on_model_picked,
        )

    def _on_model_picked(self, result: Optional[tuple[str, str]]) -> None:
        if result:
            prov_id, model_id = result
            self._switch_model(model_id)

    # ─── Actions ─────────────────────────────────────────────────

    def action_clear_chat(self) -> None:
        self.query_one("#chat-panel", ChatPanel).clear()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        self._sidebar_visible = not self._sidebar_visible
        sidebar.display = self._sidebar_visible

    def action_stop(self) -> None:
        if self._is_running:
            self.engine.request_cancel()
            # Show immediate feedback
            status = self.query_one("#status-bar", StatusBar)
            status.update_status("stopping...")

    def action_interrupt_or_quit(self) -> None:
        """Ctrl+C: interrupt if running, quit otherwise."""
        if self._is_running:
            self.engine.request_cancel()
            status = self.query_one("#status-bar", StatusBar)
            status.update_status("interrupting...")
        else:
            self.exit()

    def action_new_session(self) -> None:
        """Start a new session (Ctrl+N)."""
        if self._is_running:
            self.engine.request_cancel()
        self.session = ConversationSession()
        if self.engine.goal_store:
            self.engine.goal_store.clear()
        self.query_one("#chat-panel", ChatPanel).clear()
        self._refresh_todo_panel()
        chat = self.query_one("#chat-panel", ChatPanel)
        chat.add_system("[green]New session started.[/]")

    def action_resume_session(self) -> None:
        """Resume a previous session (Ctrl+R)."""
        self._resume_session()

    def action_toggle_detail(self) -> None:
        """Toggle detailed view mode (Ctrl+D)."""
        chat = self.query_one("#chat-panel", ChatPanel)
        # Toggle between compact and detailed view
        if hasattr(chat, '_detailed_mode'):
            chat._detailed_mode = not chat._detailed_mode
        else:
            chat._detailed_mode = True

        mode = "detailed" if chat._detailed_mode else "compact"
        chat.add_system(f"[green]View mode: {mode}[/]")

    def action_copy_last(self) -> None:
        """Copy last assistant message to clipboard (Ctrl+Shift+C)."""
        if not self._last_assistant_message:
            chat = self.query_one("#chat-panel", ChatPanel)
            chat.add_system("[yellow]No message to copy.[/]")
            return

        # Copy to clipboard using xclip or pbcopy
        import subprocess
        try:
            # Try xclip (Linux)
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=self._last_assistant_message.encode(),
                check=True
            )
            chat = self.query_one("#chat-panel", ChatPanel)
            chat.add_system("[green]Copied to clipboard![/]")
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                # Try pbcopy (macOS)
                subprocess.run(
                    ["pbcopy"],
                    input=self._last_assistant_message.encode(),
                    check=True
                )
                chat = self.query_one("#chat-panel", ChatPanel)
                chat.add_system("[green]Copied to clipboard![/]")
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback: show the message
                chat = self.query_one("#chat-panel", ChatPanel)
                chat.add_system("[yellow]Clipboard not available. Use /copy to see the message.[/]")


QCODE_HOME = Path.home() / ".qcode"


# ─── Entry point ─────────────────────────────────────────────────

def run_tui(
    engine: AgentEngine,
    config: AppConfig,
    provider_registry: ProviderRegistry,
    session: Optional[ConversationSession] = None,
) -> None:
    """Launch the Qcode TUI."""
    app = QcodeApp(
        engine=engine,
        config=config,
        provider_registry=provider_registry,
        session=session,
    )
    engine.tool_executor.permission_checker = app._permission_checker
    app.run()
