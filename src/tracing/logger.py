"""Dual Tracing Engine: Structured JSONL streaming + Formatted JSON + Markdown."""

import json
import os
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TraceStep(BaseModel):
    """Single step / event in an agent execution trajectory."""
    step_id: int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    event_type: str  # SYSTEM_PROMPT, USER_INPUT, LLM_CALL, TOOL_CALL, TOOL_RESPONSE, STATE_CHANGE, VERIFICATION
    agent_name: str
    state: str | None = None
    input_data: Any | None = None
    output_data: Any | None = None
    tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrajectoryLog(BaseModel):
    """Complete trajectory for an execution run."""
    run_id: str
    runner_type: str  # baseline or advanced
    task_id: str
    start_time: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: str | None = None
    success: bool = False
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_duration_ms: float = 0.0
    steps: list[TraceStep] = Field(default_factory=list)


class TraceLogger:
    """Manages appending trace steps and exporting human-friendly views."""

    def __init__(self, run_id: str, runner_type: str, task_id: str, trace_dir: str = "./trajectories"):
        self.trace_dir = trace_dir
        os.makedirs(trace_dir, exist_ok=True)
        self.trajectory = TrajectoryLog(
            run_id=run_id,
            runner_type=runner_type,
            task_id=task_id
        )
        self._step_counter = 0
        self.jsonl_path = os.path.join(trace_dir, f"{runner_type}_{task_id}_{run_id}.jsonl")
        self.json_path = os.path.join(trace_dir, f"{runner_type}_{task_id}_{run_id}.json")
        self.md_path = os.path.join(trace_dir, f"{runner_type}_{task_id}_{run_id}.md")

    def log_step(
        self,
        event_type: str,
        agent_name: str,
        state: str | None = None,
        input_data: Any | None = None,
        output_data: Any | None = None,
        tokens: int = 0,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        metadata: dict[str, Any] | None = None
    ) -> TraceStep:
        """Log a single step immediately to JSONL and internal trajectory."""
        self._step_counter += 1
        step = TraceStep(
            step_id=self._step_counter,
            event_type=event_type,
            agent_name=agent_name,
            state=state,
            input_data=input_data,
            output_data=output_data,
            tokens=tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            metadata=metadata or {}
        )
        self.trajectory.steps.append(step)
        self.trajectory.total_tokens += tokens
        self.trajectory.total_cost_usd += cost_usd
        self.trajectory.total_duration_ms += latency_ms

        # Append to JSONL for crash safety
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(step.model_dump_json() + "\n")

        return step

    def finalize(self, success: bool) -> None:
        """Finalize the run, write full JSON and generate Markdown summary."""
        self.trajectory.end_time = datetime.utcnow().isoformat()
        self.trajectory.success = success

        # Write formatted JSON
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.trajectory.model_dump(), f, indent=2, ensure_ascii=False)

        # Write Human-Readable Markdown
        self._generate_markdown()

    def _generate_markdown(self) -> None:
        """Create a beautifully formatted Markdown report for human evaluation."""
        traj = self.trajectory
        status_emoji = "✅ Success" if traj.success else "❌ Failed"
        lines = [
            f"# Agent Trajectory Report: `{traj.task_id}`",
            "",
            f"- **Runner Type:** `{traj.runner_type}`",
            f"- **Status:** {status_emoji}",
            f"- **Total Duration:** {traj.total_duration_ms:.1f} ms",
            f"- **Total Tokens:** {traj.total_tokens}",
            f"- **Estimated Cost:** ${traj.total_cost_usd:.5f} USD",
            "",
            "## ⏱️ Execution Timeline",
            "",
            "| Step | Event Type | State / Agent | Details / Tool | Tokens | Cost | Latency |",
            "| :---: | :--- | :--- | :--- | :---: | :---: | :---: |"
        ]

        for s in traj.steps:
            detail = ""
            if s.event_type == "TOOL_CALL":
                tool_name = s.metadata.get("tool_name", "tool")
                detail = f"`{tool_name}`"
            elif s.event_type == "STATE_CHANGE":
                detail = f"{s.metadata.get('from_state')} ➔ {s.metadata.get('to_state')}"
            elif s.event_type == "VERIFICATION":
                detail = "Verification Check"
            else:
                detail = s.event_type.lower()

            lines.append(
                f"| {s.step_id} | `{s.event_type}` | `{s.agent_name}` ({s.state or '-'}) | {detail} | {s.tokens} | ${s.cost_usd:.4f} | {s.latency_ms:.1f}ms |"
            )

        lines.extend([
            "",
            "## 🔍 Detailed Step Logs",
            ""
        ])

        for s in traj.steps:
            lines.append(f"### Step {s.step_id}: {s.event_type} ({s.agent_name})")
            if s.input_data:
                lines.append(f"**Input:**\n```json\n{json.dumps(s.input_data, indent=2) if isinstance(s.input_data, (dict, list)) else str(s.input_data)}\n```")
            if s.output_data:
                lines.append(f"**Output:**\n```json\n{json.dumps(s.output_data, indent=2) if isinstance(s.output_data, (dict, list)) else str(s.output_data)}\n```")
            lines.append("")

        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
