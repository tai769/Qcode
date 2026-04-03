"""Workspace-local model profile configuration loaded from TOML and auth JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import os

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib


CONFIG_PATH = Path(".qcode/config.toml")
AUTH_PATH = Path(".qcode/auth.json")

_DIRECT_APP_FIELDS = {
    "api_base_url",
    "api_key",
    "model",
    "max_tokens",
    "api_wire_api",
    "model_reasoning_effort",
    "model_verbosity",
    "disable_response_storage",
    "request_timeout",
    "shell_timeout",
    "tool_output_preview_chars",
    "todo_reminder_interval",
    "subagent_max_iterations",
    "background_timeout",
    "background_notification_preview_chars",
    "max_context_window",
    "context_target_ratio",
    "context_safety_margin_tokens",
    "compaction_token_threshold",
    "compaction_keep_recent_tool_results",
    "compaction_summary_ratio",
    "teammate_max_iterations",
    "team_idle_sleep_seconds",
    "team_idle_timeout_seconds",
    "transcript_dir",
    "task_dir",
    "team_dir",
    "event_log_path",
}

_ALIASES = {
    "base_url": "api_base_url",
    "reasoning_effort": "model_reasoning_effort",
    "verbosity": "model_verbosity",
}

_PATH_FIELDS = {
    "transcript_dir",
    "task_dir",
    "team_dir",
    "event_log_path",
}


@dataclass(frozen=True)
class ProfileSummary:
    name: str
    model: str
    api_base_url: str
    api_wire_api: str
    auth_name: str
    is_active: bool = False


@dataclass(frozen=True)
class ProfileResolution:
    name: str
    overrides: Dict[str, Any]


def config_paths(workdir: Path) -> tuple[Path, Path]:
    root = workdir.resolve()
    return root / CONFIG_PATH, root / AUTH_PATH


def has_profile_config(workdir: Path) -> bool:
    config_path, _ = config_paths(workdir)
    return config_path.exists()


def list_profile_summaries(workdir: Path) -> list[ProfileSummary]:
    config = _load_toml_config(workdir)
    active_name = _default_profile_name(config)
    auth_map = _load_auth_map(workdir)
    profiles = config.get("profiles")
    if not isinstance(profiles, dict):
        return []

    summaries: list[ProfileSummary] = []
    for name in sorted(profiles):
        raw_profile = profiles.get(name)
        if not isinstance(raw_profile, dict):
            continue
        merged = _merged_profile_dict(config, str(name))
        auth_name = str(merged.get("auth") or name)
        summaries.append(
            ProfileSummary(
                name=str(name),
                model=str(merged.get("model") or ""),
                api_base_url=str(
                    merged.get("api_base_url") or merged.get("base_url") or ""
                ),
                api_wire_api=str(merged.get("api_wire_api") or "chat_completions"),
                auth_name=auth_name if auth_name in auth_map else "",
                is_active=str(name) == active_name,
            )
        )
    return summaries


def resolve_profile(
    workdir: Path,
    requested_profile: Optional[str] = None,
) -> Optional[ProfileResolution]:
    config = _load_toml_config(workdir)
    profiles = config.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        return None

    selection = (requested_profile or os.getenv("QCODE_PROFILE") or "").strip()
    if not selection:
        selection = _default_profile_name(config)
    if not selection:
        return None

    profile_name = _resolve_profile_name(config, selection)
    if profile_name is None:
        available = ", ".join(sorted(str(name) for name in profiles))
        raise ValueError(
            f"Unknown profile or model '{selection}'. Available profiles: {available}"
        )

    merged = _merged_profile_dict(config, profile_name)
    auth_map = _load_auth_map(workdir)
    overrides = _map_profile_overrides(workdir, merged)
    auth_name = str(merged.get("auth") or profile_name)
    auth_entry = auth_map.get(auth_name) or auth_map.get(profile_name) or {}
    api_key = _resolve_api_key(auth_entry)
    if api_key:
        overrides["api_key"] = api_key
    return ProfileResolution(name=profile_name, overrides=overrides)


def render_profile_list(workdir: Path, current_profile: str = "") -> str:
    summaries = list_profile_summaries(workdir)
    if not summaries:
        return "No TOML model profiles configured. Still using `.env` / CLI overrides."

    lines = ["Available model profiles:"]
    active_name = current_profile.strip()
    for summary in summaries:
        marker = "*" if summary.name == active_name or (not active_name and summary.is_active) else "-"
        model = summary.model or "(no model)"
        wire_api = summary.api_wire_api or "chat_completions"
        base_url = summary.api_base_url or "(no base_url)"
        lines.append(f"{marker} {summary.name}: {model} [{wire_api}] @ {base_url}")
    return "\n".join(lines)


def scaffold_profile_files(
    workdir: Path,
    *,
    api_base_url: str,
    model: str,
    api_wire_api: str,
    model_reasoning_effort: str,
    model_verbosity: str,
    disable_response_storage: bool,
    max_tokens: int,
    request_timeout: int,
    shell_timeout: int,
    tool_output_preview_chars: int,
    todo_reminder_interval: int,
    subagent_max_iterations: int,
    background_timeout: int,
    background_notification_preview_chars: int,
    max_context_window: int,
    context_target_ratio: float,
    context_safety_margin_tokens: int,
    compaction_token_threshold: int,
    compaction_keep_recent_tool_results: int,
    compaction_summary_ratio: float,
    teammate_max_iterations: int,
    team_idle_sleep_seconds: float,
    team_idle_timeout_seconds: float,
    api_key: str = "",
) -> tuple[Path, Path]:
    config_path, auth_path = config_paths(workdir)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_text = "\n".join(
        [
            'version = 1',
            'active_profile = "default"',
            "",
            "[defaults]",
            f"max_tokens = {max_tokens}",
            f"request_timeout = {request_timeout}",
            f"shell_timeout = {shell_timeout}",
            f"tool_output_preview_chars = {tool_output_preview_chars}",
            f"todo_reminder_interval = {todo_reminder_interval}",
            f"subagent_max_iterations = {subagent_max_iterations}",
            f"background_timeout = {background_timeout}",
            f"background_notification_preview_chars = {background_notification_preview_chars}",
            f"max_context_window = {max_context_window}",
            f"context_target_ratio = {context_target_ratio}",
            f"context_safety_margin_tokens = {context_safety_margin_tokens}",
            f"compaction_token_threshold = {compaction_token_threshold}",
            f"compaction_keep_recent_tool_results = {compaction_keep_recent_tool_results}",
            f"compaction_summary_ratio = {compaction_summary_ratio}",
            f"teammate_max_iterations = {teammate_max_iterations}",
            f"team_idle_sleep_seconds = {team_idle_sleep_seconds}",
            f"team_idle_timeout_seconds = {team_idle_timeout_seconds}",
            "",
            "[profiles.default]",
            f'base_url = {json.dumps(api_base_url)}',
            f'model = {json.dumps(model)}',
            f'api_wire_api = {json.dumps(api_wire_api)}',
            f'reasoning_effort = {json.dumps(model_reasoning_effort)}',
            f'verbosity = {json.dumps(model_verbosity)}',
            f"disable_response_storage = {'true' if disable_response_storage else 'false'}",
            'auth = "default"',
            "",
            "[profiles.fast]",
            f'base_url = {json.dumps(api_base_url)}',
            'model = "gpt-4o-mini"',
            f'api_wire_api = {json.dumps(api_wire_api)}',
            'reasoning_effort = "low"',
            'verbosity = "low"',
            f"disable_response_storage = {'true' if disable_response_storage else 'false'}",
            'auth = "default"',
        ]
    ) + "\n"
    auth_payload = {
        "version": 1,
        "auth": {
            "default": {
                "api_key": api_key,
            }
        },
    }
    config_path.write_text(config_text, encoding="utf-8")
    auth_path.write_text(
        json.dumps(auth_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return config_path, auth_path


def _load_toml_config(workdir: Path) -> dict[str, Any]:
    config_path, _ = config_paths(workdir)
    if not config_path.exists():
        return {}
    with config_path.open("rb") as handle:
        loaded = tomllib.load(handle)
    return loaded if isinstance(loaded, dict) else {}


def _load_auth_map(workdir: Path) -> dict[str, dict[str, Any]]:
    _, auth_path = config_paths(workdir)
    if not auth_path.exists():
        return {}
    try:
        loaded = json.loads(auth_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid auth file: {auth_path}: {exc}") from exc
    if not isinstance(loaded, dict):
        return {}
    auth = loaded.get("auth")
    if isinstance(auth, dict):
        return {
            str(name): value
            for name, value in auth.items()
            if isinstance(value, dict)
        }
    profiles = loaded.get("profiles")
    if isinstance(profiles, dict):
        return {
            str(name): value
            for name, value in profiles.items()
            if isinstance(value, dict)
        }
    return {}


def _default_profile_name(config: dict[str, Any]) -> str:
    active_profile = config.get("active_profile")
    return str(active_profile).strip() if isinstance(active_profile, str) else ""


def _resolve_profile_name(config: dict[str, Any], selection: str) -> Optional[str]:
    profiles = config.get("profiles")
    if not isinstance(profiles, dict):
        return None
    if selection in profiles:
        return selection

    matches = []
    for name in profiles:
        merged = _merged_profile_dict(config, str(name))
        model = str(merged.get("model") or "").strip()
        if model == selection:
            matches.append(str(name))
    if len(matches) == 1:
        return matches[0]
    return None


def _merged_profile_dict(config: dict[str, Any], profile_name: str) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    defaults = config.get("defaults")
    if isinstance(defaults, dict):
        merged.update(defaults)
    profiles = config.get("profiles")
    if isinstance(profiles, dict):
        profile = profiles.get(profile_name)
        if isinstance(profile, dict):
            merged.update(profile)
    return merged


def _map_profile_overrides(workdir: Path, raw_profile: dict[str, Any]) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    for raw_key, raw_value in raw_profile.items():
        key = _ALIASES.get(str(raw_key), str(raw_key))
        if key == "auth":
            continue
        if key not in _DIRECT_APP_FIELDS:
            continue
        if key in _PATH_FIELDS:
            if raw_value in (None, ""):
                overrides[key] = None
            else:
                value = Path(str(raw_value)).expanduser()
                if not value.is_absolute():
                    value = workdir / value
                overrides[key] = value.resolve()
            continue
        overrides[key] = raw_value
    return overrides


def _resolve_api_key(auth_entry: dict[str, Any]) -> str:
    direct_api_key = auth_entry.get("api_key")
    if isinstance(direct_api_key, str) and direct_api_key.strip():
        return direct_api_key.strip()

    api_key_env = auth_entry.get("api_key_env")
    if isinstance(api_key_env, str) and api_key_env.strip():
        return os.getenv(api_key_env.strip(), "").strip()
    return ""
