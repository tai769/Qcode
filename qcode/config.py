"""Application configuration loading."""

from dataclasses import dataclass, replace
import os
from pathlib import Path
from typing import Any, Dict, Optional

from qcode.config_profiles import resolve_profile
from qcode.utils.env_loader import load_dotenv_file


def _resolve_optional_path(value: Optional[str], workdir: Path) -> Optional[Path]:
    if not value:
        return None

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = workdir / path
    return path.resolve()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration for the Qcode harness."""

    workdir: Path
    api_base_url: str
    api_key: str
    model: str
    max_tokens: int
    api_wire_api: str = "chat_completions"
    model_reasoning_effort: str = ""
    model_verbosity: str = ""
    disable_response_storage: bool = False
    request_timeout: int = 60
    shell_timeout: int = 120
    tool_output_preview_chars: int = 200
    todo_reminder_interval: int = 3
    subagent_max_iterations: int = 30
    background_timeout: int = 300
    background_notification_preview_chars: int = 500
    max_context_window: int = 128000
    context_target_ratio: float = 0.7
    context_safety_margin_tokens: int = 12000
    compaction_token_threshold: int = 50000
    compaction_keep_recent_tool_results: int = 3
    compaction_summary_ratio: float = 0.3
    teammate_max_iterations: int = 50
    team_idle_sleep_seconds: float = 0.5
    team_idle_timeout_seconds: float = 60.0
    transcript_dir: Optional[Path] = None
    task_dir: Optional[Path] = None
    team_dir: Optional[Path] = None
    event_log_path: Optional[Path] = None
    profile: str = ""

    @classmethod
    def from_env(
        cls,
        workdir: Optional[Path] = None,
        overrides: Optional[Dict[str, Any]] = None,
        profile: Optional[str] = None,
    ) -> "AppConfig":
        resolved_workdir = (workdir or Path.cwd()).resolve()
        load_dotenv_file(resolved_workdir / ".env")

        config = cls(
            workdir=resolved_workdir,
            api_base_url=os.getenv("QCODE_API_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("QCODE_API_KEY", ""),
            model=os.getenv("QCODE_MODEL", "gpt-4"),
            api_wire_api=os.getenv("QCODE_API_WIRE_API", "chat_completions"),
            model_reasoning_effort=os.getenv(
                "QCODE_MODEL_REASONING_EFFORT",
                "",
            ),
            model_verbosity=os.getenv("QCODE_MODEL_VERBOSITY", ""),
            disable_response_storage=_env_bool(
                "QCODE_DISABLE_RESPONSE_STORAGE",
                False,
            ),
            max_tokens=int(os.getenv("QCODE_MAX_TOKENS", "8000")),
            request_timeout=int(os.getenv("QCODE_REQUEST_TIMEOUT", "60")),
            shell_timeout=int(os.getenv("QCODE_SHELL_TIMEOUT", "120")),
            tool_output_preview_chars=int(
                os.getenv("QCODE_TOOL_OUTPUT_PREVIEW_CHARS", "200")
            ),
            todo_reminder_interval=int(
                os.getenv("QCODE_TODO_REMINDER_INTERVAL", "3")
            ),
            subagent_max_iterations=int(
                os.getenv("QCODE_SUBAGENT_MAX_ITERATIONS", "30")
            ),
            background_timeout=int(
                os.getenv("QCODE_BACKGROUND_TIMEOUT", "300")
            ),
            background_notification_preview_chars=int(
                os.getenv("QCODE_BACKGROUND_NOTIFICATION_PREVIEW_CHARS", "500")
            ),
            max_context_window=int(
                os.getenv("QCODE_MAX_CONTEXT_WINDOW", "128000")
            ),
            context_target_ratio=float(
                os.getenv("QCODE_CONTEXT_TARGET_RATIO", "0.7")
            ),
            context_safety_margin_tokens=int(
                os.getenv("QCODE_CONTEXT_SAFETY_MARGIN_TOKENS", "12000")
            ),
            compaction_token_threshold=int(
                os.getenv("QCODE_COMPACTION_TOKEN_THRESHOLD", "50000")
            ),
            compaction_keep_recent_tool_results=int(
                os.getenv("QCODE_COMPACTION_KEEP_RECENT_TOOL_RESULTS", "3")
            ),
            compaction_summary_ratio=float(
                os.getenv("QCODE_COMPACTION_SUMMARY_RATIO", "0.3")
            ),
            teammate_max_iterations=int(
                os.getenv("QCODE_TEAMMATE_MAX_ITERATIONS", "50")
            ),
            team_idle_sleep_seconds=float(
                os.getenv("QCODE_TEAM_IDLE_SLEEP_SECONDS", "0.5")
            ),
            team_idle_timeout_seconds=float(
                os.getenv("QCODE_TEAM_IDLE_TIMEOUT_SECONDS", "60")
            ),
            transcript_dir=_resolve_optional_path(
                os.getenv("QCODE_TRANSCRIPT_DIR", ".transcripts"),
                resolved_workdir,
            ),
            task_dir=_resolve_optional_path(
                os.getenv("QCODE_TASK_DIR", ".tasks"),
                resolved_workdir,
            ),
            team_dir=_resolve_optional_path(
                os.getenv("QCODE_TEAM_DIR", ".team"),
                resolved_workdir,
            ),
            event_log_path=_resolve_optional_path(
                os.getenv("QCODE_EVENT_LOG_PATH"),
                resolved_workdir,
            ),
            profile="",
        )

        profile_resolution = resolve_profile(resolved_workdir, requested_profile=profile)
        if profile_resolution is not None:
            config = replace(
                config,
                profile=profile_resolution.name,
                **profile_resolution.overrides,
            )

        if not overrides:
            return config

        filtered_overrides = {
            key: value for key, value in overrides.items() if value is not None
        }
        return replace(config, **filtered_overrides) if filtered_overrides else config

    def validate(self) -> None:
        if self.api_key:
            return

        raise ValueError(
            "QCODE_API_KEY not set. Copy .env.example to .env and fill in your key."
        )
