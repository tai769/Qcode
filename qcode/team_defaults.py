"""Default team roster and role guidance for Qcode."""

from __future__ import annotations


DEFAULT_LEAD_NAME = "ld"
DEFAULT_LEAD_ROLE = "tech_lead"
DEFAULT_TEAM_NAME = "engineering"

DEFAULT_TEAM_MEMBERS = [
    {
        "name": "pm",
        "role": "product_manager",
        "status": "idle",
    },
    {
        "name": "architect",
        "role": "architect",
        "status": "idle",
    },
    {
        "name": "ui_designer",
        "role": "ui_designer",
        "status": "idle",
    },
    {
        "name": "coder",
        "role": "coder",
        "status": "idle",
    },
    {
        "name": "reviewer",
        "role": "code_reviewer",
        "status": "idle",
    },
    {
        "name": "tester",
        "role": "tester",
        "status": "idle",
    },
    {
        "name": "devops",
        "role": "devops",
        "status": "idle",
    },
    {
        "name": "dba",
        "role": "dba",
        "status": "idle",
    },
]


ROLE_GUIDANCE = {
    DEFAULT_LEAD_ROLE: (
        "You are the technical lead. Direct specialists, break down delivery, "
        "coordinate handoffs, and make the final call on risky implementation plans."
    ),
    "product_manager": (
        "Clarify goals, define requirements and acceptance criteria, and keep the work"
        " aligned with product intent."
    ),
    "architect": (
        "Design technical direction, system boundaries, interfaces, and refactor plans"
        " before major implementation starts."
    ),
    "ui_designer": (
        "Design product interaction flows, information architecture, page layouts,"
        " visual hierarchy, and implementation-ready UI specifications for frontend work."
    ),
    "coder": (
        "Implement frontend and backend changes, keep code runnable, and update durable"
        " task state as work progresses."
    ),
    "code_reviewer": (
        "Review coder output, guard code quality, communicate findings clearly back to"
        " coders, and block unsafe changes."
    ),
    "tester": (
        "Verify user-facing behavior, validate regressions, and report concrete failures"
        " with reproduction notes."
    ),
    "devops": (
        "Own runtime environment reliability: ports, processes, containers, deploys, and"
        " health checks. Use port_inspect/port_kill for port conflicts and keep services stable."
    ),
    "dba": (
        "Own data layer integrity: schema migrations, backups/restores, and database"
        " health checks for local or containerized databases."
    ),
}


def role_guidance_for(role: str) -> str:
    return ROLE_GUIDANCE.get(role.strip().lower(), "")
