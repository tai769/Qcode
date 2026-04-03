"""Provider factory for selecting the wire API implementation."""

from qcode.config import AppConfig
from qcode.providers.base import ChatProvider
from qcode.providers.openai_compatible import OpenAICompatibleProvider
from qcode.providers.responses_compatible import ResponsesCompatibleProvider


def build_chat_provider(config: AppConfig, system_prompt: str) -> ChatProvider:
    wire_api = config.api_wire_api.strip().lower()
    if wire_api == "responses":
        return ResponsesCompatibleProvider(config, system_prompt)
    return OpenAICompatibleProvider(config, system_prompt)
