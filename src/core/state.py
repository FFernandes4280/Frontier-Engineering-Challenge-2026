"""State definitions and models for the Agent FSM."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


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
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    details: Optional[Dict[str, Any]] = None


class AgentContext(BaseModel):
    """Persistent context passed between states in the FSM."""
    task_id: str
    task_input: str
    current_state: AgentStatus = AgentStatus.INITIALIZING
    state_history: List[StateTransition] = Field(default_factory=list)
    memory: Dict[str, Any] = Field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    verification_attempts: int = 0
    max_verification_attempts: int = 3
    final_output: Optional[str] = None
    error_message: Optional[str] = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    def transition_to(self, new_state: AgentStatus, trigger: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Record and transition the agent to a new state."""
        transition = StateTransition(
            from_state=self.current_state,
            to_state=new_state,
            trigger=trigger,
            details=details or {}
        )
        self.state_history.append(transition)
        self.current_state = new_state
