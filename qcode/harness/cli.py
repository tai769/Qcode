"""Interactive CLI harness for Qcode."""

import argparse
import json
import os
import select
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

    readline.parse_and_bind("set bind-tty-special-chars on")
    readline.parse_and_bind("set input-meta on")
    readline.parse_and_bind("set output-meta on")
    readline.parse_and_bind("set convert-meta off")
    readline.parse_and_bind("set enable-meta-keybindings on")
except ImportError:
    readline = None

try:
    import fcntl
except ImportError:
    fcntl = None


_RUN_TIME_WARNING_INTERVAL_SECONDS = 300.0
_PASTE_BURST_READ_SECONDS = 0.5
_PASTE_BURST_POLL_SECONDS = 0.01


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
        session = ConversationSession()
        self._disable_bracketed_paste()

        while True:
            try:
                query = self._read_query()
            except KeyboardInterrupt:
                print("\nInput canceled.", file=self.stream)
                continue
            except EOFError:
                break

            if query is None:
                break

            normalized = query.strip().lower()
            if normalized in {"q", "exit"}:
                break
            if not normalized:
                continue

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

    def _read_query(self) -> Optional[str]:
        self._disable_bracketed_paste()
        line = input("Qcode >> ")
        extra = self._drain_paste_burst()
        if not extra:
            return line
        return f"{line}\n{extra}"

    def _drain_paste_burst(self) -> str:
        if not getattr(sys.stdin, "isatty", lambda: False)():
            return ""
        if fcntl is None:
            return self._drain_paste_burst_select()
        return self._drain_paste_burst_nonblocking()

    def _drain_paste_burst_nonblocking(self) -> str:
        fd = sys.stdin.fileno()
        try:
            original_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        except Exception:
            return ""

        buffer = bytearray()
        try:
            fcntl.fcntl(fd, fcntl.F_SETFL, original_flags | os.O_NONBLOCK)
            deadline = time.monotonic() + _PASTE_BURST_READ_SECONDS
            while time.monotonic() < deadline:
                try:
                    chunk = os.read(fd, 4096)
                except BlockingIOError:
                    time.sleep(_PASTE_BURST_POLL_SECONDS)
                    continue
                if not chunk:
                    break
                buffer.extend(chunk)
                deadline = time.monotonic() + _PASTE_BURST_READ_SECONDS
        finally:
            try:
                fcntl.fcntl(fd, fcntl.F_SETFL, original_flags)
            except Exception:
                pass

        if not buffer:
            return ""
        text = buffer.decode(errors="replace")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return "\n".join(text.splitlines())

    def _drain_paste_burst_select(self) -> str:
        if not self._stdin_ready(0.0):
            return ""

        deadline = time.monotonic() + _PASTE_BURST_READ_SECONDS
        chunks: List[str] = []
        while True:
            if time.monotonic() >= deadline:
                break
            if not self._stdin_ready(_PASTE_BURST_POLL_SECONDS):
                continue
            extra = sys.stdin.readline()
            if extra == "":
                break
            chunks.append(extra.rstrip("\n"))
            deadline = time.monotonic() + _PASTE_BURST_READ_SECONDS
        return "\n".join(chunks)

    @staticmethod
    def _stdin_ready(timeout_seconds: float) -> bool:
        try:
            ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
        except (ValueError, OSError):
            return False
        return bool(ready)

    def _disable_bracketed_paste(self) -> None:
        is_tty = bool(getattr(self.stream, "isatty", lambda: False)())
        if not is_tty:
            return
        try:
            self.stream.write("\x1b[?2004l")
            self.stream.flush()
        except Exception:
            pass

    def run_once(
        self,
        query: str,
        session: Optional[ConversationSession] = None,
    ) -> ConversationSession:
        active_session = session if session is not None else ConversationSession()
        self._streaming_text_active = False
        active_session.add_user_text(query)
        self._progress.start("思考中")
        runtime_monitor = _RunTimeMonitor(
            stream=sys.stderr,
            interval_seconds=_RUN_TIME_WARNING_INTERVAL_SECONDS,
        )
        runtime_monitor.start()
        try:
            self.engine.run(active_session)
        finally:
            runtime_monitor.stop()
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


class _CliProgressReporter:
    """Minimal terminal progress reporter for model/tool activity."""

    _FRAMES = ("|", "/", "-", "\\")

    def __init__(
        self,
        stream: TextIO,
        interval_seconds: float = 0.1,
    ) -> None:
        self.stream = stream
        self.interval_seconds = interval_seconds
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._active = False
        self._paused = False
        self._status = ""
        self._started_at = 0.0
        self._frame_index = 0
        self._last_printed_status = ""
        self._use_tty = bool(getattr(stream, "isatty", lambda: False)())
        self._line_visible = False

    def start(self, status: str) -> None:
        self.stop()
        with self._lock:
            self._active = True
            self._paused = False
            self._status = status
            self._started_at = time.monotonic()
            self._frame_index = 0
            self._last_printed_status = ""
            self._line_visible = False
            if self._use_tty:
                self._ensure_thread_locked()
            else:
                self._write_line_locked(f"[working] {status}")
                self._last_printed_status = status

    def resume(self, status: Optional[str] = None) -> None:
        with self._lock:
            if not self._active:
                return
            if status is not None:
                self._status = status
            self._paused = False
            if not self._use_tty and self._status != self._last_printed_status:
                self._write_line_locked(f"[working] {self._status}")
                self._last_printed_status = self._status

    def pause(self) -> None:
        with self._lock:
            if not self._active:
                return
            self._paused = True
            if self._use_tty and self._line_visible:
                self._clear_line_locked()
                self._line_visible = False

    def stop(self) -> None:
        thread: Optional[threading.Thread] = None
        with self._lock:
            if not self._active and self._thread is None:
                return
            self._active = False
            thread = self._thread
            self._thread = None
            if self._use_tty and self._line_visible:
                self._clear_line_locked()
                self._line_visible = False
        if thread is not None and thread.is_alive():
            thread.join(timeout=self.interval_seconds * 4)

    def _ensure_thread_locked(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            with self._lock:
                if not self._active:
                    return
                if not self._paused:
                    elapsed = time.monotonic() - self._started_at
                    frame = self._FRAMES[self._frame_index % len(self._FRAMES)]
                    self._frame_index += 1
                    self.stream.write(
                        f"\r\033[2K[{frame}] {self._status} {elapsed:0.1f}s"
                    )
                    self.stream.flush()
                    self._line_visible = True
            time.sleep(self.interval_seconds)

    def _clear_line_locked(self) -> None:
        self.stream.write("\r\033[2K")
        self.stream.flush()

    def _write_line_locked(self, text: str) -> None:
        self.stream.write(text)
        self.stream.write("\n")
        self.stream.flush()


class _RunTimeMonitor:
    def __init__(self, stream: TextIO, interval_seconds: float) -> None:
        self.stream = stream
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._started_at = 0.0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._started_at = time.monotonic()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            elapsed = time.monotonic() - self._started_at
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            print(f"[TIME] 已运行 {minutes}分{seconds}秒", file=self.stream, flush=True)
