"""TOML-based configuration for Qcode (~/.qcode/config.toml)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


QCODE_HOME = Path.home() / ".qcode"


@dataclass
class ProviderConfig:
    """A configured provider entry in config.toml."""
    protocol: str = "openai"  # "openai" | "anthropic"
    api_key: str = ""
    base_url: str = ""
    model: str = ""


@dataclass
class PermissionConfig:
    auto_allow: List[str] = field(default_factory=lambda: ["read_file", "grep", "glob", "todo", "compact"])
    always_ask: List[str] = field(default_factory=lambda: ["bash", "write", "edit"])


@dataclass
class UIConfig:
    theme: str = "monokai"
    auto_compact_at: float = 0.8


@dataclass
class QcodeConfig:
    provider: str = ""  # active provider id
    model: str = ""  # active model id
    max_tokens: int = 8000
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    permission: PermissionConfig = field(default_factory=PermissionConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "QcodeConfig":
        config_path = path or QCODE_HOME / "config.toml"
        if not config_path.exists():
            return cls()

        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return cls._load_fallback(config_path)

        with config_path.open("rb") as f:
            data = tomllib.load(f)

        config = cls()
        default = data.get("default", {})
        if isinstance(default, dict):
            config.provider = default.get("provider", "")
            config.model = default.get("model", "")
            config.max_tokens = default.get("max_tokens", 8000)

        for name, prov_data in data.get("provider", {}).items():
            if isinstance(prov_data, dict):
                config.providers[name] = ProviderConfig(
                    protocol=prov_data.get("protocol", "openai"),
                    api_key=prov_data.get("api_key", ""),
                    base_url=prov_data.get("base_url", ""),
                    model=prov_data.get("model", ""),
                )

        perm = data.get("permission", {})
        if isinstance(perm, dict):
            config.permission.auto_allow = perm.get("auto_allow", config.permission.auto_allow)
            config.permission.always_ask = perm.get("always_ask", config.permission.always_ask)

        ui = data.get("ui", {})
        if isinstance(ui, dict):
            config.ui.theme = ui.get("theme", config.ui.theme)
            config.ui.auto_compact_at = ui.get("auto_compact_at", config.ui.auto_compact_at)

        return config

    @classmethod
    def _load_fallback(cls, path: Path) -> "QcodeConfig":
        config = cls()
        try:
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("["):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key == "model":
                        config.model = value
                    elif key == "provider":
                        config.provider = value
                    elif key == "max_tokens":
                        config.max_tokens = int(value)
        except Exception:
            pass
        return config

    def save(self, path: Optional[Path] = None) -> Path:
        config_path = path or QCODE_HOME / "config.toml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Qcode configuration",
            "# protocol: \"openai\" (OpenAI-compatible) or \"anthropic\" (Anthropic-native)",
            "# model: any model ID your provider supports",
            "",
            "[default]",
        ]

        if self.provider:
            lines.append(f'provider = "{self.provider}"')
        if self.model:
            lines.append(f'model = "{self.model}"')
        lines.append(f"max_tokens = {self.max_tokens}")
        lines.append("")

        for name, prov in self.providers.items():
            lines.append(f"[provider.{name}]")
            lines.append(f'protocol = "{prov.protocol}"')
            if prov.api_key:
                lines.append(f'api_key = "{prov.api_key}"')
            if prov.base_url:
                lines.append(f'base_url = "{prov.base_url}"')
            if prov.model:
                lines.append(f'model = "{prov.model}"')
            lines.append("")

        lines.append("[permission]")
        lines.append(f"auto_allow = {self.permission.auto_allow}")
        lines.append(f"always_ask = {self.permission.always_ask}")
        lines.append("")
        lines.append("[ui]")
        lines.append(f'theme = "{self.ui.theme}"')
        lines.append(f"auto_compact_at = {self.ui.auto_compact_at}")

        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return config_path
