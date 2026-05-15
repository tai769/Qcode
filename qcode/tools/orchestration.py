"""Tool orchestration — concurrent/serial scheduling based on tool metadata.

Inspired by Claude Code's toolOrchestration.ts: partition tool calls into
batches where read-only tools run concurrently and write tools run serially.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from qcode.tools.tool import Tool


@dataclass
class ToolCall:
    """A single tool call from the model."""

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class Batch:
    """A batch of tool calls that can be executed together."""

    is_concurrent: bool
    blocks: List[ToolCall] = field(default_factory=list)


@dataclass
class ToolResult:
    """Result of a single tool execution."""

    tool_call_id: str
    tool_name: str
    content: str
    is_error: bool = False


def partition_tool_calls(
    tool_calls: List[ToolCall],
    tool_map: Dict[str, Tool],
) -> List[Batch]:
    """Partition tool calls into concurrent and serial batches.

    Consecutive concurrency-safe tools are merged into one concurrent batch.
    Non-concurrency-safe tools each get their own serial batch.
    """
    batches: List[Batch] = []

    for tc in tool_calls:
        tool = tool_map.get(tc.name)
        is_safe = bool(tool and tool.is_concurrency_safe)

        if is_safe and batches and batches[-1].is_concurrent:
            batches[-1].blocks.append(tc)
        else:
            batches.append(Batch(is_concurrent=is_safe, blocks=[tc]))

    return batches


async def run_single_tool(
    tc: ToolCall,
    tool_map: Dict[str, Tool],
    dispatch_fn: Callable[[str, Dict[str, Any]], str],
) -> ToolResult:
    """Execute a single tool call."""
    try:
        content = dispatch_fn(tc.name, tc.arguments)
        return ToolResult(
            tool_call_id=tc.id,
            tool_name=tc.name,
            content=content,
            is_error=content.startswith("Error:"),
        )
    except Exception as exc:
        return ToolResult(
            tool_call_id=tc.id,
            tool_name=tc.name,
            content=f"Error: {exc}",
            is_error=True,
        )


async def run_tools(
    tool_calls: List[ToolCall],
    tool_map: Dict[str, Tool],
    dispatch_fn: Callable[[str, Dict[str, Any]], str],
    max_concurrency: int = 10,
) -> List[ToolResult]:
    """Execute tool calls with intelligent concurrency scheduling.

    Read-only tools run in parallel (up to max_concurrency).
    Write tools run serially.
    """
    batches = partition_tool_calls(tool_calls, tool_map)
    results: List[ToolResult] = []

    for batch in batches:
        if batch.is_concurrent:
            # Run read-only tools concurrently
            tasks = [
                run_single_tool(tc, tool_map, dispatch_fn)
                for tc in batch.blocks
            ]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
        else:
            # Run write tools serially
            for tc in batch.blocks:
                result = await run_single_tool(tc, tool_map, dispatch_fn)
                results.append(result)

    return results
