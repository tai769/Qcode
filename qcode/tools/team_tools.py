"""Tool definitions for lead/team mailbox coordination."""

import json
from typing import Optional

from qcode.runtime.context import ToolExecutionContext
from qcode.runtime.goal_store import GoalStore
from qcode.runtime.task_graph import TaskGraphManager
from qcode.runtime.team_protocols import TeamProtocolManager
from qcode.runtime.team import TeammateManager, VALID_TEAM_MESSAGE_TYPES
from qcode.team_defaults import DEFAULT_LEAD_NAME
from qcode.tools.registry import ToolDefinition


def build_lead_team_tool_definitions(
    team_manager: TeammateManager,
    protocol_manager: TeamProtocolManager,
    goal_store: GoalStore,
    lead_name: str = DEFAULT_LEAD_NAME,
) -> list[ToolDefinition]:
    resolved_lead_name = lead_name or team_manager.lead_name

    def spawn_teammate(
        name: str,
        role: str,
        prompt: str,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return team_manager.spawn(name, role, prompt)

    def list_teammates(
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return team_manager.list_all()

    def send_message(
        to: str,
        content: str,
        msg_type: str = "message",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return team_manager.send_message(resolved_lead_name, to, content, msg_type)

    def read_inbox(
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        inbox = team_manager.read_inbox(resolved_lead_name)
        return json.dumps(inbox, indent=2, ensure_ascii=False)

    def broadcast(
        content: str,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return team_manager.broadcast(resolved_lead_name, content)

    def shutdown_request(
        teammate: str,
        reason: str = "Please shut down gracefully.",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        member = team_manager.get_member(teammate)
        if member is None:
            return f"Error: Unknown teammate '{teammate}'"

        record = protocol_manager.create_request(
            kind="shutdown",
            requester=resolved_lead_name,
            target=teammate,
            content=reason,
        )
        send_result = team_manager.send_message(
            resolved_lead_name,
            teammate,
            reason,
            msg_type="shutdown_request",
            extra={"request_id": record["request_id"]},
        )
        if send_result.startswith("Error:"):
            return send_result
        return (
            f"Shutdown request {record['request_id']} sent to '{teammate}' "
            f"(status: pending)"
        )

    def check_protocol_request(
        request_id: str,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        try:
            record = protocol_manager.get(request_id)
        except ValueError as exc:
            return f"Error: {exc}"
        return json.dumps(record, indent=2, ensure_ascii=False)

    def list_protocol_requests(
        kind: str = "",
        status: str = "",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        records = protocol_manager.list_requests(kind=kind or None, status=status or None)
        return json.dumps(records, indent=2, ensure_ascii=False)

    def review_plan(
        request_id: str,
        approve: bool,
        feedback: str = "",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        try:
            record = protocol_manager.get(request_id)
        except ValueError as exc:
            return f"Error: {exc}"
        if record["kind"] != "plan_approval":
            return f"Error: Request {request_id} is not a plan approval request"

        try:
            updated = protocol_manager.respond(
                request_id=request_id,
                responder=resolved_lead_name,
                approve=approve,
                content=feedback,
            )
        except ValueError as exc:
            return f"Error: {exc}"
        send_result = team_manager.send_message(
            resolved_lead_name,
            updated["requester"],
            feedback,
            msg_type="plan_approval_response",
            extra={
                "request_id": request_id,
                "approve": approve,
                "feedback": feedback,
            },
        )
        if send_result.startswith("Error:"):
            return send_result
        return (
            f"Plan request {request_id} {updated['status']} for "
            f"'{updated['requester']}'"
        )

    def set_goal(
        goal: str,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        try:
            saved_goal = goal_store.set(goal)
        except ValueError as exc:
            return f"Error: {exc}"
        return f"Active goal set:\n{saved_goal}"

    def get_goal(
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        goal = goal_store.get()
        return goal or "(no active goal)"

    def clear_goal(
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        goal_store.clear()
        return "Active goal cleared."

    return [
        ToolDefinition(
            name="spawn_teammate",
            description="Spawn or wake a persistent teammate that works in its own thread.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Teammate name"},
                    "role": {"type": "string", "description": "Teammate role"},
                    "prompt": {
                        "type": "string",
                        "description": "Initial task or assignment for the teammate",
                    },
                },
                "required": ["name", "role", "prompt"],
            },
            handler=spawn_teammate,
        ),
        ToolDefinition(
            name="list_teammates",
            description="List all teammates with name, role, and lifecycle status.",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=list_teammates,
        ),
        ToolDefinition(
            name="send_message",
            description="Send a message to a teammate or the lead inbox.",
            parameters={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient name"},
                    "content": {"type": "string", "description": "Message body"},
                    "msg_type": {
                        "type": "string",
                        "enum": sorted(VALID_TEAM_MESSAGE_TYPES),
                    },
                },
                "required": ["to", "content"],
            },
            handler=send_message,
        ),
        ToolDefinition(
            name="read_inbox",
            description="Read and drain the lead inbox immediately.",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=read_inbox,
        ),
        ToolDefinition(
            name="broadcast",
            description="Send a broadcast message to all teammates.",
            parameters={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Broadcast body",
                    }
                },
                "required": ["content"],
            },
            handler=broadcast,
        ),
        ToolDefinition(
            name="shutdown_request",
            description="Request a teammate to shut down gracefully. Returns a request id.",
            parameters={
                "type": "object",
                "properties": {
                    "teammate": {"type": "string", "description": "Teammate name"},
                    "reason": {
                        "type": "string",
                        "description": "Optional shutdown reason or instructions",
                    },
                },
                "required": ["teammate"],
            },
            handler=shutdown_request,
        ),
        ToolDefinition(
            name="check_protocol_request",
            description="Inspect one shutdown or plan-approval request by request id.",
            parameters={
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "Protocol request id",
                    }
                },
                "required": ["request_id"],
            },
            handler=check_protocol_request,
        ),
        ToolDefinition(
            name="list_protocol_requests",
            description="List tracked protocol requests, optionally filtered by kind or status.",
            parameters={
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "description": "Optional kind filter, e.g. shutdown or plan_approval",
                    },
                    "status": {
                        "type": "string",
                        "description": "Optional status filter, e.g. pending, approved, rejected",
                    },
                },
            },
            handler=list_protocol_requests,
        ),
        ToolDefinition(
            name="review_plan",
            description="Approve or reject a teammate's submitted plan by request id.",
            parameters={
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "Plan approval request id",
                    },
                    "approve": {"type": "boolean"},
                    "feedback": {
                        "type": "string",
                        "description": "Optional feedback to send back to the teammate",
                    },
                },
                "required": ["request_id", "approve"],
            },
            handler=review_plan,
        ),
        ToolDefinition(
            name="set_goal",
            description="Persist the active mission so the lead and teammates stay aligned.",
            parameters={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Current mission, success criteria, and constraints.",
                    }
                },
                "required": ["goal"],
            },
            handler=set_goal,
        ),
        ToolDefinition(
            name="get_goal",
            description="Read the currently pinned mission/goal.",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=get_goal,
        ),
        ToolDefinition(
            name="clear_goal",
            description="Clear the currently pinned mission/goal.",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=clear_goal,
        ),
    ]


def build_teammate_tool_definitions(
    team_manager: TeammateManager,
    task_graph: TaskGraphManager,
    protocol_manager: TeamProtocolManager,
    goal_store: GoalStore,
    sender: str,
) -> list[ToolDefinition]:
    def send_message(
        to: str,
        content: str,
        msg_type: str = "message",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        return team_manager.send_message(sender, to, content, msg_type)

    def read_inbox(
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        inbox = team_manager.read_inbox(sender)
        return json.dumps(inbox, indent=2, ensure_ascii=False)

    def shutdown_response(
        request_id: str,
        approve: bool,
        reason: str = "",
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        try:
            record = protocol_manager.get(request_id)
        except ValueError as exc:
            return f"Error: {exc}"

        if record["kind"] != "shutdown":
            return f"Error: Request {request_id} is not a shutdown request"
        if record["target"] != sender:
            return f"Error: Request {request_id} is not targeted to '{sender}'"

        try:
            updated = protocol_manager.respond(
                request_id=request_id,
                responder=sender,
                approve=approve,
                content=reason,
            )
        except ValueError as exc:
            return f"Error: {exc}"
        send_result = team_manager.send_message(
            sender,
            team_manager.lead_name,
            reason,
            msg_type="shutdown_response",
            extra={
                "request_id": request_id,
                "approve": approve,
                "reason": reason,
            },
        )
        if send_result.startswith("Error:"):
            return send_result

        if approve:
            team_manager.mark_shutdown(sender)
            if context is not None:
                context.session.request_run_stop("shutdown approved")
        return f"Shutdown request {request_id} {updated['status']}"

    def request_plan_approval(
        plan: str,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        record = protocol_manager.create_request(
            kind="plan_approval",
            requester=sender,
            target=team_manager.lead_name,
            content=plan,
            payload={"plan": plan},
        )
        send_result = team_manager.send_message(
            sender,
            team_manager.lead_name,
            plan,
            msg_type="plan_approval_request",
            extra={
                "request_id": record["request_id"],
                "plan": plan,
            },
        )
        if send_result.startswith("Error:"):
            return send_result

        if context is not None:
            context.session.request_idle_poll("approval_wait")
            context.session.request_run_stop("waiting for plan approval")
        return (
            f"Plan submitted for approval (request_id={record['request_id']}). "
            "Waiting for lead response."
        )

    def idle(
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        if context is not None:
            context.session.request_idle_poll("autonomous")
            context.session.request_run_stop("idle requested")
        return "Entering idle phase. Will poll inbox and unclaimed tasks."

    def claim_task(
        task_id: int,
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        member = team_manager.get_member(sender)
        if member is None:
            return f"Error: Unknown teammate '{sender}'"
        role = str(member.get("role", ""))
        return task_graph.claim(task_id, sender, owner_role=role)

    def get_goal(
        context: Optional[ToolExecutionContext] = None,
    ) -> str:
        goal = goal_store.get()
        return goal or "(no active goal)"

    return [
        ToolDefinition(
            name="send_message",
            description="Send a message to the lead or another teammate.",
            parameters={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient name"},
                    "content": {"type": "string", "description": "Message body"},
                    "msg_type": {
                        "type": "string",
                        "enum": sorted(VALID_TEAM_MESSAGE_TYPES),
                    },
                },
                "required": ["to", "content"],
            },
            handler=send_message,
        ),
        ToolDefinition(
            name="read_inbox",
            description="Read and drain your own inbox immediately.",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=read_inbox,
        ),
        ToolDefinition(
            name="shutdown_response",
            description="Approve or reject a shutdown request by request id.",
            parameters={
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "Shutdown request id",
                    },
                    "approve": {"type": "boolean"},
                    "reason": {
                        "type": "string",
                        "description": "Optional explanation or shutdown note",
                    },
                },
                "required": ["request_id", "approve"],
            },
            handler=shutdown_response,
        ),
        ToolDefinition(
            name="request_plan_approval",
            description="Submit a major-work plan for lead approval, then pause for a response.",
            parameters={
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "string",
                        "description": "Plan text that the lead should review",
                    }
                },
                "required": ["plan"],
            },
            handler=request_plan_approval,
        ),
        ToolDefinition(
            name="idle",
            description="Declare that you have no immediate work and enter autonomous idle polling.",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=idle,
        ),
        ToolDefinition(
            name="claim_task",
            description="Claim a ready unowned task for yourself by task id.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "Task id to claim",
                    }
                },
                "required": ["task_id"],
            },
            handler=claim_task,
        ),
        ToolDefinition(
            name="get_goal",
            description="Read the currently pinned mission/goal so you stay aligned with the lead.",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=get_goal,
        ),
    ]
