"""Finite State Machine execution engine for autonomous agents."""

from collections.abc import Callable, Coroutine
from typing import Any

from src.core.state import AgentContext, AgentStatus

StateHandler = Callable[[AgentContext], Coroutine[Any, Any, AgentStatus]]


class StateMachineAgent:
    """Finite State Machine Runner for Goal-Oriented Agents."""

    def __init__(self, context: AgentContext):
        self.context = context
        self.handlers: dict[AgentStatus, StateHandler] = {}

    def register_handler(self, state: AgentStatus, handler: StateHandler) -> None:
        """Register an async handler function for a specific state."""
        self.handlers[state] = handler

    async def run(self) -> AgentContext:
        """Execute the FSM until a terminal state (COMPLETED or FAILED) is reached."""
        while self.context.current_state not in [AgentStatus.COMPLETED, AgentStatus.FAILED]:
            current_state = self.context.current_state
            handler = self.handlers.get(current_state)

            if not handler:
                self.context.transition_to(
                    AgentStatus.FAILED,
                    trigger="missing_handler",
                    details={"error": f"No handler registered for state {current_state}"}
                )
                self.context.error_message = f"Missing handler for state: {current_state}"
                break

            try:
                next_state = await handler(self.context)
                self.context.transition_to(
                    next_state,
                    trigger=f"handler_{current_state.value.lower()}_completed"
                )
            except Exception as e:
                self.context.transition_to(
                    AgentStatus.FAILED,
                    trigger="exception_in_handler",
                    details={"error": str(e), "state": current_state.value}
                )
                self.context.error_message = f"Unhandled exception in state {current_state}: {e!s}"
                break

        return self.context
