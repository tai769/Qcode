"""Runtime middleware hooks."""

from typing import Iterable, Protocol

from qcode.runtime.context import AgentRunContext


class SessionMiddleware(Protocol):
    """Hook point for mutating or validating a session before model calls."""

    def before_model_call(self, run_context: AgentRunContext) -> None:
        ...


class MiddlewarePipeline:
    """Sequentially applies runtime middleware."""

    def __init__(self, middlewares: Iterable[SessionMiddleware] = ()) -> None:
        self._middlewares = list(middlewares)

    def before_model_call(self, run_context: AgentRunContext) -> None:
        for middleware in self._middlewares:
            middleware.before_model_call(run_context)
