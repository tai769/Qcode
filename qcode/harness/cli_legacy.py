"""Interactive CLI harness for Qcode."""

import argparse
import json
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, TextIO

from qcode.config import AppConfig
from qcode.providers.base import EventType, ResponseEvent
from qcode.runtime.engine import AgentEngine
from qcode.runtime.session import ConversationSession

try:
    import readline

    readline.parse_and_bind("set bind-tty-special-chars off")
    readline.parse_and_bind("set input-meta on")
    readline.parse_and_bind("set output-meta on")
    readline.parse_and_bind("set convert-meta off")
    readline.parse_and_bind("set enable-meta-keybindings on")
except ImportError:
    readline = None


class CliHarness:
    """Terminal harness that hosts the runtime engine."""

    def __init__(
        self,
        engine: AgentEngine,
        tool_output_preview_chars: int = 200,
        slash_commands: Optional[Dict[str, Callable[[], str]]] = None,
        stream: Optional[TextIO] = None,
        config: Optional[AppConfig] = None,
        model_lister: Optional[Callable[[], str]] = None,
        model_switcher: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.engine = engine
        self.tool_output_preview_chars = tool_output_preview_chars
        self.slash_commands = slash_commands or {}
        self.stream = stream or sys.stdout
        self.config = config
        self.model_lister = model_lister
        self.model_switcher = model_switcher
        self._streaming_text_active = False
        self._progress = _CliProgressReporter(self.stream)
        self.set_engine(engine)

    def set_engine(self, engine: AgentEngine) -> None:
        self.engine = engine
        self.engine.set_tool_output_handler(self._print_tool_output)
        self.engine.set_response_event_handler(self._handle_response_event)

    def run_interactive(self) -> None:
        self._run_start_time = time.time()  # 开始时间监控
        session = ConversationSession()

        while True:
            self._check_run_time()  # 每5分钟提示一次
            try:
                query = input("\033[36mQcode >> \033[0m")
            except (EOFError, KeyboardInterrupt):
                break

            if query.strip().lower() in {"q", "exit", ""}:
                break

            if query.strip().startswith("/"):
                output = self._handle_slash_command(query.strip())
                if output is not None:
                    print(output, file=self.stream)
                    print(file=self.stream)
                    continue

            try:
                self.run_once(query, session)
            except KeyboardInterrupt:
                print("\nInterrupted.", file=self.stream)
            except Exception as exc:
                print(f"Error: {exc}", file=self.stream)
            print(file=self.stream)

    def run_once(
        self,
        query: str,
        session: Optional[ConversationSession] = None,
    ) -> ConversationSession:
        active_session = session if session is not None else ConversationSession()
        self._streaming_text_active = False
        active_session.add_user_text(query)
        self._progress.start("思考中")
        try:
            self.engine.run(active_session)
        finally:
            self._progress.stop()

        assistant_message = active_session.last_assistant_message()
        response = active_session.last_assistant_content()
        streamed = bool(assistant_message and assistant_message.get("_streamed_output"))
        if response and not streamed:
            print(response, file=self.stream)
        elif streamed and self._streaming_text_active:
            print(file=self.stream)
            self._streaming_text_active = False

        return active_session

    def _print_tool_output(self, function_name: str, output: str) -> None:
        self._progress.pause()
        if self._streaming_text_active:
            print(file=self.stream)
            self._streaming_text_active = False
        print(f"\033[33m> {function_name}:\033[0m", file=self.stream)
        print(output[: self.tool_output_preview_chars], file=self.stream)
        self._progress.resume(f"工具 {function_name} 已完成，继续处理中")

    def _handle_response_event(self, event: ResponseEvent) -> None:
        if event.event_type == EventType.CREATED:
            self._progress.resume("模型已接入，等待输出")
            return

        if event.event_type == EventType.REASONING_DELTA:
            self._progress.resume("推理中")
            return

        if event.event_type == EventType.TOOL_CALL_DELTA and event.tool_call is not None:
            tool_name = event.tool_call.tool_name or "unknown"
            self._progress.resume(f"准备调用工具 {tool_name}")
            return

        if event.event_type == EventType.TOOL_CALL_DONE and event.tool_call is not None:
            tool_name = event.tool_call.tool_name or "unknown"
            self._progress.resume(f"等待执行工具 {tool_name}")
            return

        if event.event_type != EventType.OUTPUT_TEXT_DELTA or not event.delta:
            return

        self._progress.pause()
        print(event.delta, end="", flush=True, file=self.stream)
        self._streaming_text_active = True

    def handle_runtime_event(
        self,
        event_type: str,
        payload: Mapping[str, object],
    ) -> None:
        if event_type == "run.started":
            self._progress.resume("开始处理请求")
            return

        if event_type == "compaction.micro":
            self._progress.resume("整理上下文")
            return

        if event_type == "compaction.full":
            self._progress.resume("压缩长对话上下文")
            return

        if event_type == "model.request":
            self._progress.resume("请求模型")
            return

        if event_type in {"tool.stream.submitted", "tool.call"}:
            tool_name = str(payload.get("tool") or "unknown")
            self._progress.resume(f"运行工具 {tool_name}")

    def _handle_slash_command(self, command: str) -> Optional[str]:
        parts = command.split(maxsplit=1)
        command_name = parts[0]
        command_arg = parts[1].strip() if len(parts) > 1 else ""

        if command_name == "/help":
            available = sorted({"/help", "/model", "/models", *self.slash_commands.keys()})
            return "Available slash commands: " + ", ".join(available)

        if command_name == "/models":
            if self.model_lister is None:
                return "Model profiles are not configured."
            return self.model_lister()

        if command_name == "/model":
            if not command_arg:
                if self.config is None:
                    return "Current model: (unknown)"
                profile_suffix = f", profile={self.config.profile}" if self.config.profile else ""
                return (
                    f"Current model: {self.config.model}"
                    f" [{self.config.api_wire_api}]"
                    f" @ {self.config.api_base_url}{profile_suffix}"
                )
            if self.model_switcher is None:
                return "Model switching is not configured."
            return self.model_switcher(command_arg)

        handler = self.slash_commands.get(command_name)
        if handler is None:
            available = ", ".join(sorted({"/help", "/model", "/models", *self.slash_commands.keys()}))
            return f"Unknown slash command: {command_name}. Available: {available}" if available else None

        result = handler()
        if isinstance(result, (dict, list)):
            return json.dumps(result, indent=2, ensure_ascii=False)
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Qcode CLI coding agent")
    parser.add_argument("--once", help="Run a single prompt and exit")
    parser.add_argument("--workdir", help="Override workspace root")
    parser.add_argument("--profile", help="Select a configured model profile")
    parser.add_argument("--model", help="Override QCODE_MODEL")
    parser.add_argument("--max-tokens", type=int, help="Override QCODE_MAX_TOKENS")
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List configured model profiles and exit",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    args = build_parser().parse_args(argv)

    workdir = Path(args.workdir).expanduser() if args.workdir else None
    overrides = {
        "model": args.model,
        "max_tokens": args.max_tokens,
    }
    try:
        config = AppConfig.from_env(
            workdir=workdir,
            overrides=overrides,
            profile=args.profile,
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return

    if args.list_models:
        from qcode.config_profiles import render_profile_list

        print(render_profile_list(config.workdir, current_profile=config.profile))
        return

    try:
        config.validate()
    except ValueError as exc:
        print(f"Error: {exc}")
        return

    from qcode.app import build_cli_harness

    harness = build_cli_harness(config)
    if args.once:
        harness.run_once(args.once)
        return

    harness.run_interactive()


import time

_start_time: float = time.time()

_last_warning: float = 0

class _CliProgressReporter:
class _CliProgressReporter:

    def _check_run_time(self) -> None:
        elapsed = time.time() - self._run_start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        
        # 每5分钟提示一次
        if elapsed >= self._last_time_warning + 300:
            print(f"[TIME] 已运行 {minutes}分{seconds}秒", file=sys.stderr)
            self._last_time_warning = elapsed
        
        # 超过最大时间警告
        if elapsed >= self._MAX_RUN_TIME_SECONDS:
            print(f"[TIME ERROR] 已超过最大运行时间 {self._MAX_RUN_TIME_SECONDS}s = {self._MAX_RUN_TIME_SECONDS // 60}分钟。请检查是否卡死循环。", file=sys.stderr)
            raise RuntimeError(f"Maximum run time reached")
