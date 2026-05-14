"""Provider registry — protocol-driven, freeform model IDs.

Design: only two protocols exist:
  - "openai"    → OpenAI-compatible API (chat/completions)
  - "anthropic" → Anthropic-native API (messages)

Model ID is whatever the user types. No enforced list.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ProviderEntry:
    """A configured provider instance."""

    id: str                  # unique key (e.g. "openai", "anthropic", "my-vllm")
    protocol: str            # "openai" | "anthropic"
    api_key: str = ""
    base_url: str = ""
    model: str = ""          # default model ID (freeform)
    name: str = ""           # display name

    @property
    def effective_base_url(self) -> str:
        if self.base_url:
            return self.base_url
        return DEFAULT_URLS.get(self.protocol, "")


# Default base URLs per protocol
DEFAULT_URLS: Dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
}

# Well-known provider presets (just convenience, not enforced)
PRESETS: Dict[str, Dict[str, str]] = {
    "openai":     {"protocol": "openai",    "name": "OpenAI",     "base_url": "https://api.openai.com/v1",      "env": "OPENAI_API_KEY"},
    "anthropic":  {"protocol": "anthropic", "name": "Anthropic",  "base_url": "https://api.anthropic.com/v1",   "env": "ANTHROPIC_API_KEY"},
    "openrouter": {"protocol": "openai",    "name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1",  "env": "OPENROUTER_API_KEY"},
    "deepseek":   {"protocol": "openai",    "name": "DeepSeek",   "base_url": "https://api.deepseek.com/v1",   "env": "DEEPSEEK_API_KEY"},
}

# Suggested model IDs per provider (UI hints only)
SUGGESTED_MODELS: Dict[str, List[str]] = {
    "openai":     ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini", "o3-mini"],
    "anthropic":  ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
    "openrouter": ["anthropic/claude-sonnet-4", "openai/gpt-4.1", "google/gemini-2.5-pro-preview"],
    "deepseek":   ["deepseek-chat", "deepseek-reasoner"],
}


class ProviderRegistry:
    """Manages configured providers."""

    def __init__(self) -> None:
        self._providers: Dict[str, ProviderEntry] = {}
        self._active_id: Optional[str] = None

    def add(self, provider: ProviderEntry) -> None:
        self._providers[provider.id] = provider

    def get(self, provider_id: str) -> Optional[ProviderEntry]:
        return self._providers.get(provider_id)

    def active(self) -> Optional[ProviderEntry]:
        if self._active_id and self._active_id in self._providers:
            return self._providers[self._active_id]
        return next(iter(self._providers.values()), None)

    def set_active(self, provider_id: str) -> None:
        self._active_id = provider_id

    def list_all(self) -> List[ProviderEntry]:
        return list(self._providers.values())

    def suggestions_for(self, provider_id: str) -> List[str]:
        """Get suggested model IDs for a provider."""
        # Check if it's a well-known provider
        if provider_id in SUGGESTED_MODELS:
            return SUGGESTED_MODELS[provider_id]
        # Check if it maps to a preset
        entry = self.get(provider_id)
        if entry and entry.protocol in SUGGESTED_MODELS:
            return SUGGESTED_MODELS[entry.protocol]
        return []

    @classmethod
    def from_config_toml(cls, path: Optional[Path] = None) -> "ProviderRegistry":
        """Load from ~/.qcode/config.toml."""
        from qcode.config_toml import QcodeConfig
        cfg = QcodeConfig.load(path)

        registry = cls()

        for prov_id, prov_data in cfg.providers.items():
            # Support both dict and ProviderConfig objects
            if isinstance(prov_data, dict):
                protocol = prov_data.get("protocol", "openai")
                api_key = prov_data.get("api_key", "")
                base_url = prov_data.get("base_url", "")
                model = prov_data.get("model", "")
                name = prov_data.get("name", prov_id)
            else:
                # ProviderConfig dataclass
                protocol = getattr(prov_data, "protocol", "openai")
                api_key = getattr(prov_data, "api_key", "")
                base_url = getattr(prov_data, "base_url", "")
                model = getattr(prov_data, "model", "")
                name = prov_id

            # Try env var fallback for api_key
            if not api_key:
                preset = PRESETS.get(prov_id, {})
                env_key = preset.get("env", "")
                if env_key:
                    api_key = os.environ.get(env_key, "")

            if not api_key:
                continue

            registry.add(ProviderEntry(
                id=prov_id,
                protocol=protocol,
                api_key=api_key,
                base_url=base_url,
                model=model,
                name=name,
            ))

        if cfg.provider:
            registry.set_active(cfg.provider)

        return registry
