"""Shared runtime type aliases."""

from typing import Any, Dict, List


JsonDict = Dict[str, Any]
Message = Dict[str, Any]
Messages = List[Message]
ToolCall = Dict[str, Any]
ToolSpec = Dict[str, Any]
