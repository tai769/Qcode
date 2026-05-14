"""CLI entry point for Qcode — TUI, one-shot, resume, setup."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from qcode.config import AppConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qcode",
        description="Qcode — AI coding agent with team collaboration",
    )
    parser.add_argument("prompt", nargs="?", help="One-shot prompt")
    parser.add_argument("-p", "--prompt-flag", help="One-shot prompt via flag")
    parser.add_argument("-c", "--continue-session", action="store_true", help="Resume last session")
    parser.add_argument("--cwd", type=str, default=None, help="Working directory")
    parser.add_argument("--model", type=str, default=None, help="Override model ID")
    parser.add_argument("--provider", type=str, default=None, help="Override provider ID")
    parser.add_argument("--max-tokens", type=int, default=None, help="Override max tokens")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--setup", action="store_true", help="Run first-time setup wizard")
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    args = build_parser().parse_args(argv)

    # Setup wizard
    if args.setup:
        from qcode.harness.setup import run_setup
        run_setup()
        return

    workdir = Path(args.cwd).expanduser().resolve() if args.cwd else None

    # Load config
    from qcode.config_toml import QcodeConfig
    from qcode.providers.registry import ProviderRegistry

    toml_cfg = QcodeConfig.load()
    registry = ProviderRegistry.from_config_toml()

    # Auto-setup if no providers configured
    if not registry.list_all():
        print("No providers configured. Starting setup...\n", file=sys.stderr)
        from qcode.harness.setup import run_setup
        run_setup()
        toml_cfg = QcodeConfig.load()
        registry = ProviderRegistry.from_config_toml()
        if not registry.list_all():
            print("Setup incomplete.", file=sys.stderr)
            sys.exit(1)

    # Resolve active provider
    prov_id = args.provider or toml_cfg.provider
    provider = registry.get(prov_id) if prov_id else registry.active()
    if not provider:
        provider = registry.active()
    if not provider:
        print("Error: No active provider. Run 'qcode --setup'.", file=sys.stderr)
        sys.exit(1)

    # Resolve model
    model_id = args.model or toml_cfg.model or provider.model
    if not model_id:
        print("Error: No model specified. Run 'qcode --setup' or use --model.", file=sys.stderr)
        sys.exit(1)

    # Build AppConfig with provider connection details
    overrides = {
        "model": model_id,
        "api_base_url": provider.effective_base_url,
        "api_key": provider.api_key,
        "api_wire_api": provider.protocol,
    }
    if args.max_tokens:
        overrides["max_tokens"] = args.max_tokens

    try:
        config = AppConfig.from_env(workdir=workdir, overrides=overrides)
        config.validate()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Determine mode
    one_shot_prompt = args.prompt_flag or args.prompt

    if one_shot_prompt == "-":
        if sys.stdin.isatty():
            print("Error: '-' requires piped input", file=sys.stderr)
            sys.exit(1)
        one_shot_prompt = sys.stdin.read().strip()
        if not one_shot_prompt:
            print("Error: empty stdin", file=sys.stderr)
            sys.exit(1)

    if one_shot_prompt:
        _run_one_shot(config, one_shot_prompt, as_json=args.json)
    else:
        _run_tui(config, registry, resume=args.continue_session)


def _run_one_shot(config: AppConfig, prompt: str, *, as_json: bool = False) -> None:
    from qcode.app import build_engine_for_tui
    from qcode.runtime.session import ConversationSession

    engine = build_engine_for_tui(config)
    session = ConversationSession()
    session.add_user_text(prompt)

    import asyncio

    async def _run() -> str:
        response_text = ""
        async for event in engine.run_events(session):
            if event.type == "text_delta":
                response_text += event.data.get("text", "")
            elif event.type == "assistant_message":
                content = event.data.get("content", "")
                if content:
                    response_text = content
        return response_text

    response = asyncio.run(_run())

    if as_json:
        import json
        print(json.dumps({"response": response, "session_id": session.session_id}, ensure_ascii=False))
    else:
        print(response)


def _run_tui(config: AppConfig, registry, *, resume: bool = False) -> None:
    from qcode.app import build_engine_for_tui
    from qcode.harness.tui import run_tui
    from qcode.runtime.session import ConversationSession

    engine = build_engine_for_tui(config)

    session = None
    if resume:
        sessions_dir = config.workdir / ".qcode" / "sessions"
        latest = ConversationSession.find_latest(sessions_dir)
        if latest:
            session = ConversationSession.load(latest)

    run_tui(engine, config, provider_registry=registry, session=session)


if __name__ == "__main__":
    main()
