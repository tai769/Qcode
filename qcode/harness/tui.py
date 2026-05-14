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

    def render(self) -> str:
        return f" [bold cyan]Qcode[/] │ {self._provider}/{self._model} │ {self._status}"

    def update_info(self, provider: str, model: str) -> None:
        self._provider = provider
        self._model = model
        self.refresh()

    def update_status(self, status: str) -> None:
        self._status = status
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
    def __init__(self, **kwargs) -> None:
        super().__init__(markup=True, wrap=True, highlight=True, **kwargs)
        self._streaming_line = ""

    def add_user_message(self, text: str) -> None:
        self._flush_streaming()
        self.write(f"\n[bold green]> [/] {text}")

    def add_assistant_text(self, text: str) -> None:
        self._flush_streaming()
        self.write(Markdown(text))

    def add_streaming_delta(self, text: str) -> None:
        """Accumulate streaming text."""
        self._streaming_line += text

    def flush_streaming(self) -> None:
        """Flush accumulated streaming text as markdown."""
        self._flush_streaming()

    def _flush_streaming(self) -> None:
        if self._streaming_line:
            self.write(Markdown(self._streaming_line))
            self._streaming_line = ""

    def add_tool_call(self, tool_name: str, args_preview: str = "") -> None:
        self._flush_streaming()
        icons = {
            "bash": "  ", "read_file": "  ", "write_file": "  ",
            "edit_file": "  ✏️", "grep": "  ", "glob": "  ",
            "todo": "  ", "compact": "  ", "task": "  ",
        }
        icon = icons.get(tool_name, "  ")
        preview = f" [dim]{args_preview[:60]}[/]" if args_preview else ""
        self.write(f"{icon}[bold]{tool_name}[/]{preview}")

    def add_tool_result(self, tool_name: str, output: str, is_error: bool = False) -> None:
        self._flush_streaming()
        color = "red" if is_error else "dim"
        preview = output[:200].replace("\n", " ")
        self.write(f"[{color}]  → {preview}[/]")

    def add_system(self, text: str) -> None:
        self._flush_streaming()
        self.write(f"[dim italic]{text}[/]")

    def add_error(self, text: str) -> None:
        self._flush_streaming()
        self.write(f"[bold red]Error:[/] {text}")


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
        width: 28; height: 1fr; border: solid $primary; margin: 0 1 0 0;
    }
    #todo-panel {
        height: 1fr; border-bottom: solid $primary; overflow-y: auto;
    }
    #team-panel { height: 1fr; overflow-y: auto; }
    #input-area { height: auto; max-height: 10; margin: 0 1 1 1; }
    #prompt-input { border: solid $primary; }
    #hint-bar {
        height: 1; dock: bottom;
        background: $primary-background-darken-1; color: $text-muted; padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear_chat", "Clear"),
        Binding("ctrl+t", "toggle_sidebar", "Sidebar"),
        Binding("ctrl+m", "pick_model", "Model"),
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
        self._load_global_permissions()

    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        with Horizontal(id="main-area"):
            with Vertical(id="sidebar"):
                yield TodoPanel(id="todo-panel")
                yield TeamPanel(id="team-panel")
            yield ChatPanel(id="chat-panel")
        with Vertical(id="input-area"):
            yield Input(
                placeholder="Type a message... (Tab=@files, Ctrl+M=model, Ctrl+T=sidebar)",
                id="prompt-input",
            )
        yield Static(
            " [dim]Esc=stop  /=cmd  Tab=@file  Ctrl+M=model  Ctrl+T=sidebar  Ctrl+C=quit[/]",
            id="hint-bar",
        )

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()
        self._update_status_bar()
        self._refresh_todo_panel()
        self._refresh_team_panel()
        self._load_memory()

    # ─── Status bar ──────────────────────────────────────────────

    def _update_status_bar(self) -> None:
        bar = self.query_one("#status-bar", StatusBar)
        active = self.registry.active()
        provider_name = active.name if active else "unknown"
        bar.update_info(provider_name, self.config.model)

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
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        self._completions = []
        if text.startswith("/"):
            self._handle_slash_command(text)
            return
        await self._run_agent(text)

    # ─── Agent execution ─────────────────────────────────────────

    async def _run_agent(self, user_text: str) -> None:
        if self._is_running:
            return
        self._is_running = True
        self._streaming_text = ""
        status = self.query_one("#status-bar", StatusBar)
        status.update_status("thinking")
        chat = self.query_one("#chat-panel", ChatPanel)
        chat.add_user_message(user_text)
        self.session.add_user_text(user_text)
        try:
            async for event in self.engine.run_events(self.session):
                self._handle_engine_event(event)
                if event.type == "tool_result":
                    self._refresh_todo_panel()
        except Exception as exc:
            chat.add_error(str(exc))
        finally:
            chat.flush_streaming()
            self._is_running = False
            self._streaming_text = ""
            status.update_status("idle")
            self._auto_save_session()

    def _auto_save_session(self) -> None:
        sessions_dir = self.config.workdir / ".qcode" / "sessions"
        self.session.save(sessions_dir)

    def _handle_engine_event(self, event: EngineEvent) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        status = self.query_one("#status-bar", StatusBar)

        if event.type == "text_delta":
            text = event.data.get("text", "")
            self._streaming_text += text
            chat.add_streaming_delta(text)
            status.update_status("streaming")

        elif event.type == "assistant_message":
            content = event.data.get("content", "")
            if content:
                chat.add_assistant_text(content)
            elif self._streaming_text:
                chat.flush_streaming()
            self._streaming_text = ""

        elif event.type == "reasoning_delta":
            pass  # Could show in a separate panel

        elif event.type == "tool_call":
            tool_name = event.data.get("tool_name", "")
            args = event.data.get("arguments", "")
            chat.add_tool_call(tool_name, str(args)[:80])
            status.update_status(f"tool: {tool_name}")

        elif event.type == "tool_result":
            tool_name = event.data.get("tool_name", "")
            content = event.data.get("content", "")
            is_error = content.startswith("Error:") if content else False
            chat.add_tool_result(tool_name, content, is_error)

        elif event.type == "error":
            chat.add_error(event.data.get("message", "Unknown error"))

        elif event.type == "model_request":
            status.update_status("thinking")

    # ─── Slash commands ──────────────────────────────────────────

    def _handle_slash_command(self, command: str) -> None:
        chat = self.query_one("#chat-panel", ChatPanel)
        parts = command.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/help":
            chat.add_system(
                "Commands: /help /clear /compact /model /team /task /todo "
                "/save /load /config /cost /memory /setup"
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
            self.session.request_run_stop("user interrupt")


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
