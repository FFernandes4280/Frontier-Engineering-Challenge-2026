"""State definitions and models for the Agent FSM."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Possible states for the Agent Finite State Machine."""
    INITIALIZING = "INITIALIZING"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    EXECUTING_TOOLS = "EXECUTING_TOOLS"
    VERIFYING = "VERIFYING"
    REFLECTING = "REFLECTING"
    HUMAN_CHECKPOINT = "HUMAN_CHECKPOINT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StateTransition(BaseModel):
    """Record of a state transition inside the FSM."""
    from_state: AgentStatus
    to_state: AgentStatus
    trigger: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: dict[str, Any] | None = None


class AgentContext(BaseModel):
    """Persistent context passed between states in the FSM."""
    task_id: str
    task_input: str
    current_state: AgentStatus = AgentStatus.INITIALIZING
    state_history: list[StateTransition] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    verification_attempts: int = 0
    max_verification_attempts: int = 3
    final_output: str | None = None
    error_message: str | None = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    def transition_to(self, new_state: AgentStatus, trigger: str, details: dict[str, Any] | None = None) -> None:
        """Record and transition the agent to a new state."""
        transition = StateTransition(
            from_state=self.current_state,
            to_state=new_state,
            trigger=trigger,
            details=details or {}
        )
        self.state_history.append(transition)
        self.current_state = new_state
