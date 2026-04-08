"""FastAPI application factory for Qcode Web UI."""

import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import starlette.status as status

from qcode.app import (
    build_background_manager,
    build_goal_store,
    build_message_bus,
    build_team_protocol_manager,
    build_task_graph_manager,
    build_teammate_manager,
    build_verification_loop_manager,
)
from qcode.config import AppConfig
from qcode.prompts import (
    build_subagent_system_prompt,
    build_system_prompt,
)
from qcode.providers.factory import build_chat_provider
from qcode.runtime.background import BackgroundManager
from qcode.runtime.engine import AgentEngine
from qcode.runtime.goal_store import GoalStore
from qcode.runtime.task_graph import TaskGraphManager
from qcode.runtime.team import MessageBus, TeammateManager
from qcode.runtime.team_protocols import TeamProtocolManager
from qcode.runtime.verification_loops import VerificationLoopManager
from qcode.telemetry.events import CallbackEventSink, EventSink
from qcode.tools.builtin_tools import build_builtin_tool_registry
from qcode.tools.registry import ToolRegistry
from qcode.tools.task_graph_tools import build_task_graph_tool_definitions
from qcode.tools.task_tool import build_task_tool_definition
from qcode.tools.team_tools import build_lead_team_tool_definitions
from qcode.tools.verification_tools import build_verification_tool_definitions
from qcode.runtime.subagent import SubagentRunner
from qcode.runtime.goal_middleware import GoalMiddleware
from qcode.runtime.middleware import MiddlewarePipeline
from qcode.runtime.todo_middleware import TodoReminderMiddleware
from qcode.runtime.team_middleware import TeamInboxMiddleware
from qcode.team_defaults import DEFAULT_LEAD_NAME


logger = logging.getLogger(__name__)

# Global runtime state
_runtime_state: dict = {
    "app": None,
    "config": None,
    "engine": None,
    "task_graph": None,
    "team_manager": None,
    "message_bus": None,
    "protocol_manager": None,
    "verification_manager": None,
    "background_manager": None,
    "goal_store": None,
    "event_sink": None,
    "websocket_clients": set(),
    "subagent_runner": None,
}


# Pydantic models for API
class ChatRequest(BaseModel):
    message: str
    role: Optional[str] = "user"


class ProtocolApproveRequest(BaseModel):
    request_id: str
    approve: bool
    reason: Optional[str] = ""


class ShutdownRespondRequest(BaseModel):
    request_id: str
    approve: bool
    reason: Optional[str] = ""


class TaskClaimRequest(BaseModel):
    task_id: int


class TaskUpdateRequest(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None


class SendMessageRequest(BaseModel):
    to: str
    content: str
    msg_type: Optional[str] = "message"


def get_app(
    workdir: Optional[Path] = None,
    profile: Optional[str] = None,
) -> FastAPI:
    """Create and configure FastAPI application."""
    if _runtime_state["app"] is not None:
        return _runtime_state["app"]

    # Load configuration
    config = AppConfig.from_env(workdir=workdir, overrides=None, profile=profile)
    config.validate()

    # Build event sink
    event_sink = CallbackEventSink()

    # Build core components
    background_manager = build_background_manager(config, event_sink)
    task_graph = build_task_graph_manager(config, event_sink)
    message_bus = build_message_bus(config, event_sink)
    protocol_manager = build_team_protocol_manager(config, event_sink)
    verification_manager = build_verification_loop_manager(
        config, task_graph, event_sink
    )
    goal_store = build_goal_store(config)

    # Build subagent runner
    def build_child_engine() -> AgentEngine:
        system_prompt = build_subagent_system_prompt(config.workdir)
        provider = build_chat_provider(config, system_prompt)
        tool_registry = _build_shared_tool_registry(
            config, background_manager, task_graph
        )
        return AgentEngine(
            provider,
            tool_registry,
            event_sink=event_sink,
            middleware=_build_runtime_middleware(
                config, system_prompt, goal_store, background_manager, event_sink
            ),
        )

    subagent_runner = SubagentRunner(
        build_child_engine,
        max_iterations=config.subagent_max_iterations,
        event_sink=event_sink,
    )

    # Build team manager
    team_manager = build_teammate_manager(
        config,
        task_graph,
        message_bus,
        protocol_manager,
        verification_manager,
        background_manager,
        event_sink,
        goal_store,
    )

    # Build lead engine
    system_prompt = build_system_prompt(config.workdir)
    provider = build_chat_provider(config, system_prompt)
    base_tool_registry = _build_shared_tool_registry(
        config, background_manager, task_graph
    )
    tool_registry = ToolRegistry(
        [
            *base_tool_registry.tool_definitions(),
            build_task_tool_definition(subagent_runner),
            *build_lead_team_tool_definitions(
                team_manager,
                protocol_manager,
                goal_store,
                lead_name=team_manager.lead_name,
            ),
            *build_verification_tool_definitions(verification_manager, team_manager.lead_name),
        ]
    )

    engine = AgentEngine(
        provider,
        tool_registry,
        event_sink=event_sink,
        middleware=_build_runtime_middleware(
            config,
            system_prompt,
            goal_store,
            background_manager,
            event_sink,
            prefix_middlewares=[TeamInboxMiddleware(message_bus, team_manager.lead_name)],
        ),
    )

    # Store runtime state
    _runtime_state["config"] = config
    _runtime_state["engine"] = engine
    _runtime_state["task_graph"] = task_graph
    _runtime_state["team_manager"] = team_manager
    _runtime_state["message_bus"] = message_bus
    _runtime_state["protocol_manager"] = protocol_manager
    _runtime_state["verification_manager"] = verification_manager
    _runtime_state["background_manager"] = background_manager
    _runtime_state["goal_store"] = goal_store
    _runtime_state["event_sink"] = event_sink
    _runtime_state["subagent_runner"] = subagent_runner

    # Setup WebSocket notification callback
    event_sink.set_callback(_on_runtime_event)

    # Create FastAPI app
    app = FastAPI(
        title="Qcode Web API",
        description="Backend API for Qcode Web UI",
        version="0.1.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    _register_routes(app)

    _runtime_state["app"] = app

    logger.info("FastAPI application initialized")
    return app


def _build_shared_tool_registry(
    config: AppConfig,
    background_manager: BackgroundManager,
    task_graph: TaskGraphManager,
) -> ToolRegistry:
    base_tool_registry = build_builtin_tool_registry(
        config.workdir,
        shell_timeout=config.shell_timeout,
        background_manager=background_manager,
    )
    return ToolRegistry(
        [
            *base_tool_registry.tool_definitions(),
            *build_task_graph_tool_definitions(task_graph),
        ]
    )


def _build_runtime_middleware(
    config: AppConfig,
    system_prompt: str,
    goal_store: GoalStore,
    background_manager: BackgroundManager,
    event_sink: EventSink,
    prefix_middlewares: Optional[list] = None,
) -> MiddlewarePipeline:
    from qcode.runtime.background_middleware import BackgroundNotificationMiddleware

    middlewares = list(prefix_middlewares or [])

    if background_manager is not None:
        middlewares.append(BackgroundNotificationMiddleware(background_manager))

    middlewares.extend(
        [
            GoalMiddleware(goal_store),
            TodoReminderMiddleware(config.todo_reminder_interval),
        ]
    )
    return MiddlewarePipeline(middlewares)


def _register_routes(app: FastAPI) -> None:
    """Register all API routes."""

    @app.get("/api/health")
    async def health_check() -> dict:
        return {"status": "ok", "service": "qcode-web-api"}

    @app.get("/api/team")
    async def get_team_status() -> dict:
        team_manager = _runtime_state["team_manager"]
        if not team_manager:
            raise HTTPException(status_code=503, detail="Team manager not initialized")

        teammates = team_manager.list_all()
        return {
            "lead_name": team_manager.lead_name,
            "teammates": teammates,
        }

    @app.get("/api/tasks")
    async def get_task_graph() -> dict:
        task_graph = _runtime_state["task_graph"]
        if not task_graph:
            raise HTTPException(status_code=503, detail="Task graph not initialized")

        try:
            snapshot = task_graph.snapshot()
            return snapshot
        except Exception as e:
            logger.exception("Error listing tasks")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/chat/stream")
    async def chat_stream_get(prompt: str) -> StreamingResponse:
        """SSE streaming endpoint for chat (GET version with query param)."""
        engine = _runtime_state["engine"]
        if not engine:
            raise HTTPException(status_code=503, detail="Engine not initialized")

        async def generate() -> AsyncIterator[str]:
            try:
                # Send initial message event
                data = json.dumps({"type": "message", "content": f"User: {prompt}"})
                yield f"data: {data}\n\n"

                # Run the engine
                response = await _run_engine_async(engine, prompt)

                # Stream tokens
                for char in response:
                    data = json.dumps({"type": "token", "content": char})
                    yield f"data: {data}\n\n"

                # Done
                data = json.dumps({"type": "done"})
                yield f"data: {data}\n\n"

            except Exception as e:
                logger.exception("Error during chat stream")
                data = json.dumps({"type": "error", "message": str(e)})
                yield f"data: {data}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    @app.post("/api/chat")
    async def chat_stream_post(request: ChatRequest) -> StreamingResponse:
        """SSE streaming endpoint for chat (POST version)."""
        return await chat_stream_get(request.message)

    @app.post("/api/plans/approve")
    async def approve_plan(request: ProtocolApproveRequest) -> dict:
        protocol_manager = _runtime_state["protocol_manager"]
        team_manager = _runtime_state["team_manager"]

        if not protocol_manager or not team_manager:
            raise HTTPException(status_code=503, detail="Protocol manager not initialized")

        try:
            record = protocol_manager.respond(
                request_id=request.request_id,
                responder=team_manager.lead_name,
                approve=request.approve,
                content=request.reason,
            )
            return {"status": "ok", "record": record}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/api/shutdown/respond")
    async def respond_shutdown(request: ShutdownRespondRequest) -> dict:
        protocol_manager = _runtime_state["protocol_manager"]
        team_manager = _runtime_state["team_manager"]

        if not protocol_manager or not team_manager:
            raise HTTPException(status_code=503, detail="Protocol manager not initialized")

        try:
            record = protocol_manager.respond(
                request_id=request.request_id,
                responder=team_manager.lead_name,
                approve=request.approve,
                content=request.reason,
            )
            return {"status": "ok", "record": record}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/api/tasks/claim")
    async def claim_task(request: TaskClaimRequest) -> dict:
        task_graph = _runtime_state["task_graph"]
        team_manager = _runtime_state["team_manager"]

        if not task_graph or not team_manager:
            raise HTTPException(status_code=503, detail="Service not initialized")

        try:
            task = task_graph.get(request.task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            updated_task = task_graph.update(
                task_id=request.task_id,
                owner=team_manager.lead_name,
                status="in_progress"
            )
            return {"status": "ok", "task": updated_task}
        except Exception as e:
            logger.exception("Error claiming task")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/messages")
    async def send_message(request: SendMessageRequest) -> dict:
        message_bus = _runtime_state["message_bus"]
        team_manager = _runtime_state["team_manager"]

        if not message_bus or not team_manager:
            raise HTTPException(status_code=503, detail="Service not initialized")

        try:
            message_bus.send(
                sender=team_manager.lead_name,
                recipient=request.to,
                content=request.content,
                msg_type=request.msg_type
            )
            return {"status": "ok", "message": "Message sent"}
        except Exception as e:
            logger.exception("Error sending message")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/protocols")
    async def list_protocols() -> dict:
        protocol_manager = _runtime_state["protocol_manager"]

        if not protocol_manager:
            raise HTTPException(status_code=503, detail="Protocol manager not initialized")

        try:
            # Get all protocol requests and group by status
            all_requests = protocol_manager.list_requests()
            result = {
                "pending": [],
                "approved": [],
                "rejected": [],
            }
            for req in all_requests:
                status = req.get("status", "pending")
                if status in result:
                    result[status].append(req)
                else:
                    result["pending"].append(req)
            return result
        except Exception as e:
            logger.exception("Error listing protocols")
            raise HTTPException(status_code=500, detail=str(e))

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        _runtime_state["websocket_clients"].add(websocket)

        try:
            while True:
                # Keep connection alive and handle any incoming messages
                data = await websocket.receive_text()
                # Echo back or handle as needed
                await websocket.send_json({"type": "echo", "data": data})
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
            _runtime_state["websocket_clients"].discard(websocket)


def _on_runtime_event(event_type: str, payload: dict) -> None:
    """Handle runtime events and broadcast to WebSocket clients."""
    if not _runtime_state["websocket_clients"]:
        return

    message_type = None
    if event_type.startswith("team."):
        message_type = "team_update"
    elif event_type.startswith("task."):
        message_type = "task_update"
    elif event_type.startswith("protocol."):
        message_type = "protocol_update"

    if message_type:
        message = {"type": message_type, "event_type": event_type, "payload": payload}

        # Broadcast to all connected clients
        disconnected = set()
        for ws in _runtime_state["websocket_clients"]:
            try:
                async def send():
                    await ws.send_json(message)
                asyncio.create_task(send())
            except Exception:
                disconnected.add(ws)

        # Remove disconnected clients
        for ws in disconnected:
            _runtime_state["websocket_clients"].discard(ws)


async def _run_engine_async(engine: AgentEngine, message: str) -> str:
    """Run the engine asynchronously (simplified wrapper)."""
    import concurrent.futures

    def run():
        # Process the message through the engine
        # For now, return a simple echo response
        # Actual implementation would call engine.process() or similar
        return f"Processed: {message}"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run)


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    workdir: Optional[Path] = None,
    profile: Optional[str] = None,
) -> None:
    """Run the development server."""
    import uvicorn

    app = get_app(workdir=workdir, profile=profile)
    uvicorn.run(app, host=host, port=port, log_level="info")


# Create default app instance
app = get_app()
