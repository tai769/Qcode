"""Tool definitions and dispatch."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

from qcode.runtime.context import ToolExecutionContext


ToolHandler = Callable[..., str]


@dataclass(frozen=True)
class ToolDefinition:
    """A local tool exposed to the LLM."""

    name: str
    description: str
    parameters: Dict[str, Any]
    handler: ToolHandler

    def to_openai_tool(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Keeps tool metadata and routes tool calls."""

    def __init__(self, tools: Iterable[ToolDefinition]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def definitions(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_tool() for tool in self._tools.values()]

    def tool_definitions(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

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
            return tool.handler(context=context, **arguments)
        except TypeError as exc:
            return f"Error: Invalid arguments for {name}: {exc}"
        except Exception as exc:
            return f"Error: {exc}"
