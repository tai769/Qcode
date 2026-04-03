"""Tooling for coder/tester verification loops."""

from __future__ import annotations

import json
from typing import Optional

from qcode.runtime.context import ToolExecutionContext
from qcode.runtime.verification_loops import VerificationLoopManager
from qcode.tools.registry import ToolDefinition


def build_verification_tool_definitions(
    verification_manager: VerificationLoopManager,
    sender: str,
) -> list[ToolDefinition]:
    def request_verification(
        subject: str = "",
        details: str = "",
        tester: str = "tester",
        task_id: Optional[int] = None,
        loop_id: str = "",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        try:
            record = verification_manager.request_verification(
                owner=sender,
                subject=subject,
                details=details,
                tester=tester,
                task_id=task_id,
                loop_id=loop_id,
            )
        except ValueError as exc:
            return f"Error: {exc}"
        return json.dumps(record, indent=2, ensure_ascii=False)

    def report_verification_result(
        loop_id: str,
        passed: bool,
        summary: str,
        details: str = "",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        try:
            record = verification_manager.report_result(
                loop_id=loop_id,
                tester=sender,
                passed=passed,
                summary=summary,
                details=details,
            )
        except ValueError as exc:
            return f"Error: {exc}"
        return json.dumps(record, indent=2, ensure_ascii=False)

    def get_verification_loop(
        loop_id: str,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        try:
            record = verification_manager.get(loop_id)
        except ValueError as exc:
            return f"Error: {exc}"
        return json.dumps(record, indent=2, ensure_ascii=False)

    def list_verification_loops(
        status: str = "",
        owner: str = "",
        tester: str = "",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        records = verification_manager.list_loops(
            status=status,
            owner=owner,
            tester=tester,
        )
        return json.dumps(records, indent=2, ensure_ascii=False)

    return [
        ToolDefinition(
            name="request_verification",
            description=(
                "Submit work to a tester and create or continue a durable verification loop. "
                "Use this after coder changes are ready for smoke/acceptance testing."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Feature or change being verified"},
                    "details": {"type": "string", "description": "What changed and what should be tested"},
                    "tester": {"type": "string", "description": "Tester teammate name"},
                    "task_id": {"type": "integer", "description": "Optional linked task id"},
                    "loop_id": {"type": "string", "description": "Existing loop id when resubmitting after fixes"},
                },
            },
            handler=request_verification,
        ),
        ToolDefinition(
            name="report_verification_result",
            description=(
                "Report a tester result for a verification loop. On failure it notifies coder; "
                "on pass it notifies coder and lead."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "loop_id": {"type": "string", "description": "Verification loop id"},
                    "passed": {"type": "boolean", "description": "Whether verification passed"},
                    "summary": {"type": "string", "description": "Short test outcome summary"},
                    "details": {"type": "string", "description": "Concrete findings or smoke notes"},
                },
                "required": ["loop_id", "passed", "summary"],
            },
            handler=report_verification_result,
        ),
        ToolDefinition(
            name="get_verification_loop",
            description="Read one verification loop record by id.",
            parameters={
                "type": "object",
                "properties": {
                    "loop_id": {"type": "string", "description": "Verification loop id"},
                },
                "required": ["loop_id"],
            },
            handler=get_verification_loop,
        ),
        ToolDefinition(
            name="list_verification_loops",
            description="List verification loops, optionally filtered by status, owner, or tester.",
            parameters={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Optional status filter"},
                    "owner": {"type": "string", "description": "Optional owner filter"},
                    "tester": {"type": "string", "description": "Optional tester filter"},
                },
            },
            handler=list_verification_loops,
        ),
    ]
