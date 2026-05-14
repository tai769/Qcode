"""Provider factory for selecting the wire API implementation."""

from qcode.config import AppConfig
from qcode.providers.base import ChatProvider


def build_chat_provider(config: AppConfig, system_prompt: str) -> ChatProvider:
    wire_api = config.api_wire_api.strip().lower()

    if wire_api in ("anthropic", "messages"):
        from qcode.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(config, system_prompt)

    if wire_api == "responses":
        from qcode.providers.responses_compatible import ResponsesCompatibleProvider
        return ResponsesCompatibleProvider(config, system_prompt)

    # Default: OpenAI-compatible chat/completions
    from qcode.providers.openai_compatible import OpenAICompatibleProvider
    return OpenAICompatibleProvider(config, system_prompt)
