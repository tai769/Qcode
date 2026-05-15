"""Tool interface with metadata — inspired by Claude Code's Tool type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class Tool:
    """A tool exposed to the LLM with metadata for intelligent dispatch."""

    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., str]

    # ── Metadata (fail-closed defaults) ──────────────────────────
    is_read_only: bool = False
    is_concurrency_safe: bool = False
    is_destructive: bool = False
    max_result_size: int = 50_000

    def to_openai_tool(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def build_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    handler: Callable[..., str],
    *,
    is_read_only: bool = False,
    is_concurrency_safe: bool = False,
    is_destructive: bool = False,
    max_result_size: int = 50_000,
) -> Tool:
    """Build a Tool with safe defaults (fail-closed)."""
    return Tool(
        name=name,
        description=description,
        parameters=parameters,
        handler=handler,
        is_read_only=is_read_only,
        is_concurrency_safe=is_concurrency_safe,
        is_destructive=is_destructive,
        max_result_size=max_result_size,
    )
