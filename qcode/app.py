"""Application composition root for Qcode."""

import json
from typing import Optional

from qcode.config import AppConfig
from qcode.config_profiles import render_profile_list
from qcode.harness.cli import CliHarness
from qcode.prompts import (
    build_compaction_system_prompt,
    build_subagent_system_prompt,
    build_system_prompt,
    build_teammate_system_prompt,
)
from qcode.providers.factory import build_chat_provider
from qcode.runtime.background import BackgroundManager
from qcode.runtime.background_middleware import BackgroundNotificationMiddleware
from qcode.runtime.compaction import ConversationCompactor
from qcode.runtime.compaction_middleware import CompactionMiddleware
from qcode.runtime.context_budgeter import ContextBudgeter, estimate_text_tokens
from qcode.runtime.engine import AgentEngine
from qcode.runtime.goal_middleware import GoalMiddleware
from qcode.runtime.goal_store import GoalStore
from qcode.runtime.middleware import MiddlewarePipeline, SessionMiddleware
from qcode.runtime.subagent import SubagentRunner
from qcode.runtime.task_graph import TaskGraphManager
from qcode.runtime.team import MessageBus, TeammateManager
from qcode.runtime.team_protocols import TeamProtocolManager
from qcode.runtime.team_middleware import TeamInboxMiddleware
from qcode.runtime.todo_middleware import TodoReminderMiddleware
from qcode.runtime.verification_loops import VerificationLoopManager
from qcode.team_defaults import DEFAULT_LEAD_NAME
from qcode.telemetry.events import (
    CallbackEventSink,
    CompositeEventSink,
    EventSink,
    build_event_sink,
)
from qcode.tools.builtin_tools import build_builtin_tool_registry
from qcode.tools.registry import ToolRegistry
from qcode.tools.task_graph_tools import build_task_graph_tool_definitions
from qcode.tools.task_tool import build_task_tool_definition
from qcode.tools.team_tools import (
    build_lead_team_tool_definitions,
    build_teammate_tool_definitions,
)
from qcode.tools.verification_tools import build_verification_tool_definitions


def build_runtime_middleware(
    config: AppConfig,
    system_prompt: str,
    goal_store: GoalStore,
    background_manager: Optional[BackgroundManager] = None,
    event_sink: Optional[EventSink] = None,
    prefix_middlewares: Optional[list[SessionMiddleware]] = None,
) -> MiddlewarePipeline:
    compactor = build_conversation_compactor(config, event_sink)
    budgeter = build_context_budgeter(config, system_prompt)
    middlewares = list(prefix_middlewares or [])
    if background_manager is not None:
        middlewares.append(BackgroundNotificationMiddleware(background_manager))
    middlewares.extend(
        [
            GoalMiddleware(goal_store),
            CompactionMiddleware(compactor, budgeter),
            TodoReminderMiddleware(config.todo_reminder_interval),
        ]
    )
    return MiddlewarePipeline(middlewares)


def build_conversation_compactor(
    config: AppConfig,
    event_sink: Optional[EventSink] = None,
) -> ConversationCompactor:
    provider = build_chat_provider(
        config,
        build_compaction_system_prompt(config.workdir),
    )
    transcript_dir = config.transcript_dir or (config.workdir / ".transcripts")
    return ConversationCompactor(
        provider,
        transcript_dir=transcript_dir,
        token_threshold=config.compaction_token_threshold,
        keep_recent_tool_results=config.compaction_keep_recent_tool_results,
        summary_ratio=config.compaction_summary_ratio,
        event_sink=event_sink,
    )


def build_context_budgeter(
    config: AppConfig,
    system_prompt: str,
) -> ContextBudgeter:
    return ContextBudgeter(
        max_context_window=config.max_context_window,
        target_ratio=config.context_target_ratio,
        safety_margin_tokens=config.context_safety_margin_tokens,
        summary_ratio=config.compaction_summary_ratio,
        reserved_prompt_tokens=estimate_text_tokens(system_prompt),
    )


def build_subagent_runner(
    config: AppConfig,
    event_sink: EventSink,
    task_graph: TaskGraphManager,
    goal_store: GoalStore,
) -> SubagentRunner:
    background_manager = build_background_manager(config, event_sink)

    def build_child_engine() -> AgentEngine:
        system_prompt = build_subagent_system_prompt(config.workdir)
        provider = build_chat_provider(config, system_prompt)
        tool_registry = build_shared_tool_registry(
            config,
            background_manager,
            task_graph,
        )
        return AgentEngine(
            provider,
            tool_registry,
            event_sink=event_sink,
            middleware=build_runtime_middleware(
                config,
                system_prompt,
                goal_store,
                background_manager,
                event_sink,
            ),
        )

    return SubagentRunner(
        build_child_engine,
        max_iterations=config.subagent_max_iterations,
        event_sink=event_sink,
    )


def build_cli_harness(config: AppConfig) -> CliHarness:
    event_log_sink = build_event_sink(config.event_log_path)
    cli_event_sink = CallbackEventSink()
    event_sink = CompositeEventSink([event_log_sink, cli_event_sink])
    current_config = {"value": config}

    def build_runtime(active_config: AppConfig) -> tuple[AgentEngine, dict[str, object]]:
        system_prompt = build_system_prompt(active_config.workdir)
        provider = build_chat_provider(active_config, system_prompt)
        goal_store = build_goal_store(active_config)
        background_manager = build_background_manager(active_config, event_sink)
        task_graph = build_task_graph_manager(active_config, event_sink)
        message_bus = build_message_bus(active_config, event_sink)
        protocol_manager = build_team_protocol_manager(active_config, event_sink)
        verification_manager = build_verification_loop_manager(
            active_config,
            task_graph,
            event_sink,
        )
        team_manager = build_teammate_manager(
            active_config,
            task_graph,
            message_bus,
            protocol_manager,
            verification_manager,
            background_manager,
            event_sink,
            goal_store,
        )
        verification_manager.set_message_sender(team_manager.send_message)
        base_tool_registry = build_shared_tool_registry(
            active_config,
            background_manager,
            task_graph,
        )
        subagent_runner = build_subagent_runner(
            active_config,
            event_sink,
            task_graph,
            goal_store,
        )
        tool_registry = ToolRegistry(
            [
                *base_tool_registry.tool_definitions(),
                build_task_tool_definition(subagent_runner),
                *build_lead_team_tool_definitions(
                    team_manager,
                    protocol_manager,
                    goal_store,
                    lead_name=team_manager.lead_name,
                ),
                *build_verification_tool_definitions(
                    verification_manager,
                    team_manager.lead_name,
                ),
            ]
        )
        engine = AgentEngine(
            provider,
            tool_registry,
            event_sink=event_sink,
            middleware=build_runtime_middleware(
                active_config,
                system_prompt,
                goal_store,
                background_manager,
                event_sink,
                prefix_middlewares=[
                    TeamInboxMiddleware(message_bus, team_manager.lead_name)
                ],
            ),
        )
        slash_commands: dict[str, object] = {
            "/team": team_manager.list_all,
            "/inbox": lambda: json.dumps(
                team_manager.read_inbox(team_manager.lead_name),
                indent=2,
                ensure_ascii=False,
            ),
            "/tasks": task_graph.list_all,
            "/goal": lambda: goal_store.get() or "(no active goal)",
            "/loops": lambda: json.dumps(
                verification_manager.list_loops(),
                indent=2,
                ensure_ascii=False,
            ),
            "/protocols": lambda: json.dumps(
                protocol_manager.list_requests(),
                indent=2,
                ensure_ascii=False,
            ),
        }
        return engine, slash_commands

    engine, slash_commands = build_runtime(config)
    harness = CliHarness(
        engine,
        tool_output_preview_chars=config.tool_output_preview_chars,
        slash_commands=slash_commands,
        config=config,
        model_lister=lambda: render_profile_list(
            current_config["value"].workdir,
            current_profile=current_config["value"].profile,
        ),
    )

    def switch_model(selection: str) -> str:
        active_config = current_config["value"]
        try:
            next_config = AppConfig.from_env(
                workdir=active_config.workdir,
                overrides=None,
                profile=selection,
            )
            next_config.validate()
        except ValueError as exc:
            return f"Error: {exc}"
        next_engine, next_slash_commands = build_runtime(next_config)
        harness.config = next_config
        harness.slash_commands = next_slash_commands
        harness.tool_output_preview_chars = next_config.tool_output_preview_chars
        harness.set_engine(next_engine)
        current_config["value"] = next_config
        profile_suffix = f", profile={next_config.profile}" if next_config.profile else ""
        return (
            f"Switched model to {next_config.model}"
            f" [{next_config.api_wire_api}]"
            f" @ {next_config.api_base_url}{profile_suffix}"
        )

    harness.model_switcher = switch_model
    cli_event_sink.set_callback(harness.handle_runtime_event)
    return harness


def build_shared_tool_registry(
    config: AppConfig,
    background_manager: BackgroundManager,
    task_graph: TaskGraphManager,
) -> ToolRegistry:
    base_tool_registry = build_builtin_tool_registry(
        config.workdir,
        shell_timeout=config.shell_timeout,
        background_manager=background_manager,
    )
    return ToolRegistry(
        [
            *base_tool_registry.tool_definitions(),
            *build_task_graph_tool_definitions(task_graph),
        ]
    )


def build_background_manager(
    config: AppConfig,
    event_sink: Optional[EventSink] = None,
) -> BackgroundManager:
    return BackgroundManager(
        config.workdir,
        timeout_seconds=config.background_timeout,
        result_preview_chars=config.background_notification_preview_chars,
        event_sink=event_sink,
    )


def build_message_bus(
    config: AppConfig,
    event_sink: Optional[EventSink] = None,
) -> MessageBus:
    team_dir = config.team_dir or (config.workdir / ".team")
    inbox_dir = team_dir / "inbox"
    return MessageBus(inbox_dir, event_sink=event_sink)


def build_team_protocol_manager(
    config: AppConfig,
    event_sink: Optional[EventSink] = None,
) -> TeamProtocolManager:
    team_dir = config.team_dir or (config.workdir / ".team")
    protocol_dir = team_dir / "protocols"
    return TeamProtocolManager(protocol_dir, event_sink=event_sink)


def build_task_graph_manager(
    config: AppConfig,
    event_sink: Optional[EventSink] = None,
) -> TaskGraphManager:
    task_dir = config.task_dir or (config.workdir / ".tasks")
    return TaskGraphManager(task_dir, event_sink=event_sink)


def build_teammate_manager(
    config: AppConfig,
    task_graph: TaskGraphManager,
    message_bus: MessageBus,
    protocol_manager: TeamProtocolManager,
    verification_manager: VerificationLoopManager,
    background_manager: BackgroundManager,
    event_sink: EventSink,
    goal_store: GoalStore,
) -> TeammateManager:
    def build_teammate_engine(name: str, role: str) -> AgentEngine:
        system_prompt = build_teammate_system_prompt(config.workdir, name, role)
        provider = build_chat_provider(config, system_prompt)
        base_tool_registry = build_shared_tool_registry(
            config,
            background_manager,
            task_graph,
        )
        teammate_tool_registry = ToolRegistry(
            [
                *base_tool_registry.tool_definitions(),
                *build_teammate_tool_definitions(
                    team_manager,
                    task_graph,
                    protocol_manager,
                    goal_store,
                    name,
                ),
                *build_verification_tool_definitions(
                    verification_manager,
                    name,
                ),
            ]
        )
        engine = AgentEngine(
            provider,
            teammate_tool_registry,
            event_sink=event_sink,
            middleware=build_runtime_middleware(
                config,
                system_prompt,
                goal_store,
                background_manager,
                event_sink,
                prefix_middlewares=[TeamInboxMiddleware(message_bus, name)],
            ),
        )
        engine.set_tool_output_handler(
            lambda function_name, output: print(
                f"\033[35m[{name}] {function_name}:\033[0m\n"
                f"{output[: config.tool_output_preview_chars]}"
            )
        )
        return engine

    team_dir = config.team_dir or (config.workdir / ".team")
    team_manager = TeammateManager(
        team_dir=team_dir,
        bus=message_bus,
        task_graph=task_graph,
        engine_factory=build_teammate_engine,
        max_iterations=config.teammate_max_iterations,
        idle_sleep_seconds=config.team_idle_sleep_seconds,
        idle_timeout_seconds=config.team_idle_timeout_seconds,
        idle_shutdown_enabled=False,
        event_sink=event_sink,
    )
    return team_manager


def build_goal_store(config: AppConfig) -> GoalStore:
    return GoalStore(config.workdir / ".qcode" / "active_goal.md")


def build_verification_loop_manager(
    config: AppConfig,
    task_graph: TaskGraphManager,
    event_sink: Optional[EventSink] = None,
) -> VerificationLoopManager:
    team_dir = config.team_dir or (config.workdir / ".team")
    return VerificationLoopManager(
        team_dir / "verification_loops",
        task_graph=task_graph,
        lead_name=DEFAULT_LEAD_NAME,
        event_sink=event_sink,
    )
