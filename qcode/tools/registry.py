"""Tool definitions and dispatch — with schema-based argument validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

from qcode.runtime.context import ToolExecutionContext
from qcode.tools.tool import Tool, build_tool

# Re-export for backward compatibility
ToolDefinition = Tool
ToolHandler = Callable[..., str]


class ToolRegistry:
    """Keeps tool metadata and routes tool calls."""

    def __init__(self, tools: Iterable[Tool]) -> None:
        self._tools: Dict[str, Tool] = {tool.name: tool for tool in tools}

    def definitions(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_tool() for tool in self._tools.values()]

    def tool_definitions(self) -> List[Tool]:
        return list(self._tools.values())

    def get_definition(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def tool_map(self) -> Dict[str, Tool]:
        """Return name→Tool map for orchestration."""
        return dict(self._tools)

    def __len__(self) -> int:
        return len(self._tools)

    def dispatch(
        self,
        name: str,
        arguments: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Unknown tool: {name}"

        try:
            # Validate and filter arguments against handler signature
            import inspect

            sig = inspect.signature(tool.handler)
            valid_params = {
                p.name
                for p in sig.parameters.values()
                if p.kind
                in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
            }

            # Filter out unknown arguments (model hallucination tolerance)
            filtered = {k: v for k, v in arguments.items() if k in valid_params}

            # Check required parameters
            for p in sig.parameters.values():
                if (
                    p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
                    and p.default is inspect.Parameter.empty
                    and p.name not in filtered
                    and p.name != "context"
                ):
                    return f"Error: Missing required argument '{p.name}' for tool '{name}'"

            return tool.handler(context=context, **filtered)
        except TypeError as exc:
            return f"Error: Invalid arguments for {name}: {exc}"
        except Exception as exc:
            return f"Error: {exc}"
