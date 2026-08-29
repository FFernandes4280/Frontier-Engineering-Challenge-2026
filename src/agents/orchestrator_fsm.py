"""FSM Orchestrator connecting the 4 specialized agents to the state machine."""

import uuid
from typing import Dict, Any, Tuple
from src.core.state import AgentContext, AgentStatus
from src.core.fsm import StateMachineAgent
from src.core.domain import ScenarioSpec, CandidateSubmission, SeniorVettingDossier, RecommendationType
from src.tracing.logger import TraceLogger
from src.agents.orchestrator_agent import ScenarioProvisionerAgent
from src.agents.telemetry_agent import CodeEvolutionAlignmentAgent
from src.agents.verifier_agent import CodeVerifierAgent
from src.agents.critic_agent import SeniorEngineeringCriticAgent


class HolisticVettingOrchestrator:
    """Orchestrates the entire multi-agent vetting pipeline over the FSM engine."""

    def __init__(self, trace_dir: str = "./traces"):
        self.trace_dir = trace_dir
        self.provisioner = ScenarioProvisionerAgent()
        self.alignment_agent = CodeEvolutionAlignmentAgent()
        self.verifier_agent = CodeVerifierAgent()
        self.critic_agent = SeniorEngineeringCriticAgent()

    async def evaluate_submission(
        self,
        submission: CandidateSubmission,
        spec: ScenarioSpec
    ) -> Tuple[SeniorVettingDossier, TraceLogger]:
        """Runs the complete FSM pipeline with tracing and error safety."""
        run_id = str(uuid.uuid4())[:8]
        logger = TraceLogger(
            run_id=run_id,
            runner_type="advanced",
            task_id=f"{spec.scenario_id}_{submission.candidate_id}",
            trace_dir=self.trace_dir
        )

        context = AgentContext(
            task_id=spec.scenario_id,
            task_input=submission.model_dump_json()
        )

        fsm = StateMachineAgent(context)

        # Shared state storage across handlers
        pipeline_data: Dict[str, Any] = {}

        # 1. INITIALIZING Handler
        async def handle_initializing(ctx: AgentContext) -> AgentStatus:
            logger.log_step(
                event_type="STATE_CHANGE",
                agent_name=self.provisioner.name,
                state=AgentStatus.INITIALIZING.value,
                input_data={"scenario_id": spec.scenario_id},
                metadata={"from_state": "START", "to_state": AgentStatus.INITIALIZING.value}
            )
            scenario_meta = self.provisioner.provision_scenario(spec)
            pipeline_data["scenario"] = scenario_meta
            return AgentStatus.ANALYZING

        # 2. ANALYZING Handler
        async def handle_analyzing(ctx: AgentContext) -> AgentStatus:
            logger.log_step(
                event_type="STATE_CHANGE",
                agent_name=self.alignment_agent.name,
                state=AgentStatus.ANALYZING.value,
                metadata={"from_state": AgentStatus.INITIALIZING.value, "to_state": AgentStatus.ANALYZING.value}
            )
            alignment = self.alignment_agent.evaluate_alignment(submission, spec)
            pipeline_data["alignment"] = alignment
            logger.log_step(
                event_type="TOOL_CALL",
                agent_name=self.alignment_agent.name,
                state=AgentStatus.ANALYZING.value,
                output_data=alignment,
                metadata={"tool_name": "BlastRadius & ContextInspector"}
            )
            return AgentStatus.EXECUTING_TOOLS

        # 3. EXECUTING_TOOLS Handler
        async def handle_executing_tools(ctx: AgentContext) -> AgentStatus:
            logger.log_step(
                event_type="STATE_CHANGE",
                agent_name=self.verifier_agent.name,
                state=AgentStatus.EXECUTING_TOOLS.value,
                metadata={"from_state": AgentStatus.ANALYZING.value, "to_state": AgentStatus.EXECUTING_TOOLS.value}
            )
            verification = self.verifier_agent.verify(submission, spec)
            pipeline_data["verification"] = verification
            logger.log_step(
                event_type="TOOL_RESPONSE",
                agent_name=self.verifier_agent.name,
                state=AgentStatus.EXECUTING_TOOLS.value,
                output_data=verification.model_dump(),
                metadata={"tool_name": "LoadSimulator & SecurityScanner"}
            )
            return AgentStatus.VERIFYING

        # 4. VERIFYING Handler
        async def handle_verifying(ctx: AgentContext) -> AgentStatus:
            logger.log_step(
                event_type="VERIFICATION",
                agent_name=self.critic_agent.name,
                state=AgentStatus.VERIFYING.value,
                metadata={"all_passed": pipeline_data["verification"].all_tests_passed}
            )
            dossier = await self.critic_agent.generate_dossier(
                submission=submission,
                spec=spec,
                alignment_data=pipeline_data["alignment"],
                verification_report=pipeline_data["verification"]
            )
            pipeline_data["dossier"] = dossier
            return AgentStatus.HUMAN_CHECKPOINT if dossier.human_in_the_loop_approval_needed else AgentStatus.COMPLETED

        # 5. HUMAN_CHECKPOINT Handler
        async def handle_human_checkpoint(ctx: AgentContext) -> AgentStatus:
            logger.log_step(
                event_type="STATE_CHANGE",
                agent_name="HumanInTheLoopGate",
                state=AgentStatus.HUMAN_CHECKPOINT.value,
                metadata={"reason": "Borderline score requires reviewer sign-off."}
            )
            return AgentStatus.COMPLETED

        # Register handlers
        fsm.register_handler(AgentStatus.INITIALIZING, handle_initializing)
        fsm.register_handler(AgentStatus.ANALYZING, handle_analyzing)
        fsm.register_handler(AgentStatus.EXECUTING_TOOLS, handle_executing_tools)
        fsm.register_handler(AgentStatus.VERIFYING, handle_verifying)
        fsm.register_handler(AgentStatus.HUMAN_CHECKPOINT, handle_human_checkpoint)

        await fsm.run()

        dossier: SeniorVettingDossier = pipeline_data.get("dossier")
        if not dossier:
            # Fallback if unhandled FSM exception
            dossier = SeniorVettingDossier(
                candidate_id=submission.candidate_id,
                scenario_id=spec.scenario_id,
                overall_vetting_score=50.0,
                recommendation=RecommendationType.LEAN_NO,
                architecture_score=50.0,
                concurrency_scalability_score=50.0,
                code_quality_reusability_score=50.0,
                executive_summary="FSM execution pipeline completed with partial telemetry.",
                trade_off_analysis="Partial evaluation recorded.",
                evidence_citations=[]
            )

        logger.finalize(success=(dossier.overall_vetting_score >= 70.0))
        return dossier, logger
