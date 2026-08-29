"""FSM Orchestrator connecting the specialized agent squad to the state machine with verbose tracing and interactive human quality gate."""

import uuid
import sys
from typing import Dict, Any, Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from src.core.state import AgentContext, AgentStatus
from src.core.fsm import StateMachineAgent
from src.core.domain import ScenarioSpec, CandidateSubmission, SeniorVettingDossier, RecommendationType
from src.tracing.logger import TraceLogger
from src.agents.orchestrator_agent import ScenarioProvisionerAgent
from src.agents.test_synthesizer import DynamicTestSynthesizerAgent
from src.agents.telemetry_agent import CodeEvolutionAlignmentAgent
from src.agents.verifier_agent import CodeVerifierAgent
from src.agents.critic_agent import SeniorEngineeringCriticAgent


console = Console()


class HolisticVettingOrchestrator:
    """Orchestrates the entire multi-agent vetting pipeline over the FSM engine."""

    def __init__(self, trace_dir: str = "./traces", verbose: bool = False, interactive_human_gate: bool = False):
        self.trace_dir = trace_dir
        self.verbose = verbose
        self.interactive_human_gate = interactive_human_gate
        self.provisioner = ScenarioProvisionerAgent()
        self.test_synthesizer = DynamicTestSynthesizerAgent()
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

        if self.verbose:
            console.print(Panel(
                f"[bold magenta]🤖 ADVANCED FSM MULTI-AGENT PIPELINE EXECUTION TRACE[/bold magenta]\n"
                f"Target Scenario: [bold]{spec.title}[/bold] ({spec.github_repo or 'Local'})\n"
                f"Topology: [cyan]{spec.architecture_type.value}[/cyan] | Sched: [green]Deterministic FSM[/green]",
                border_style="magenta"
            ))

        context = AgentContext(
            task_id=spec.scenario_id,
            task_input=submission.model_dump_json()
        )

        fsm = StateMachineAgent(context)

        # Shared state storage across handlers
        pipeline_data: Dict[str, Any] = {}

        # 1. INITIALIZING Handler
        async def handle_initializing(ctx: AgentContext) -> AgentStatus:
            if self.verbose:
                console.print("\n[bold cyan]📍 FSM STAGE 1: PROVISIONING & SLA SPECIFICATION[/bold cyan]")
                console.print(f"  • Agent: [bold]{self.provisioner.name}[/bold]")
                console.print(f"  • Ingested [bold]{len(spec.existing_codebase_map)}[/bold] modules from repository AST.")
                console.print(f"  • Target Concurrency SLA: [bold]{spec.requirements.concurrency_target_rps} RPS[/bold] | Max RAM: [bold]{spec.requirements.max_memory_mb}MB[/bold]")

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

        # 2. ANALYZING Handler (AST Alignment + Dynamic Test Synthesis)
        async def handle_analyzing(ctx: AgentContext) -> AgentStatus:
            if self.verbose:
                console.print("\n[bold cyan]📍 FSM STAGE 2: DYNAMIC TEST SYNTHESIS & AST ALIGNMENT[/bold cyan]")
                console.print(f"  • Agent: [bold]{self.test_synthesizer.name}[/bold]")
            
            # Synthesize targeted tests
            synthesized_tests = self.test_synthesizer.synthesize_suite(submission, spec)
            pipeline_data["synthesized_tests"] = synthesized_tests
            
            if self.verbose:
                for st in synthesized_tests:
                    console.print(f"    ⚡ Synthesized: [yellow]{st.test_name}[/yellow] targeting [bold]{st.target_risk}[/bold] (Concurrency: {st.concurrency_level} users)")

                console.print(f"\n  • Agent: [bold]{self.alignment_agent.name}[/bold]")
                console.print("    Scanning Git Diff against AST codebase symbols...")

            logger.log_step(
                event_type="STATE_CHANGE",
                agent_name=self.alignment_agent.name,
                state=AgentStatus.ANALYZING.value,
                metadata={"from_state": AgentStatus.INITIALIZING.value, "to_state": AgentStatus.ANALYZING.value}
            )
            alignment = self.alignment_agent.evaluate_alignment(submission, spec)
            pipeline_data["alignment"] = alignment

            if self.verbose:
                blast_dict = alignment.get("blast_radius", {})
                align_dict = alignment.get("context_alignment", {})
                blast_score = blast_dict.get("blast_radius_score", 1.0) * 100
                align_score = align_dict.get("alignment_score", 1.0) * 100
                console.print(f"    ✓ Blast Radius Score: [bold]{blast_score:.1f}/100[/bold] ({blast_dict.get('files_modified_count', 0)} files modified)")
                console.print(f"    ✓ Codebase Reusability Score: [bold]{align_score:.1f}/100[/bold] (API Contract Preserved: {align_dict.get('api_contract_preserved', True)})")

            logger.log_step(
                event_type="TOOL_CALL",
                agent_name=self.alignment_agent.name,
                state=AgentStatus.ANALYZING.value,
                output_data=alignment,
                metadata={"tool_name": "BlastRadius & ContextInspector"}
            )
            return AgentStatus.EXECUTING_TOOLS

        # 3. EXECUTING_TOOLS Handler (Load Simulation & Concurrency Stress)
        async def handle_executing_tools(ctx: AgentContext) -> AgentStatus:
            if self.verbose:
                console.print("\n[bold cyan]📍 FSM STAGE 3: RUNTIME CONCURRENCY & LOAD VERIFICATION[/bold cyan]")
                console.print(f"  • Agent: [bold]{self.verifier_agent.name}[/bold] using [bold yellow]LoadSimulator[/bold yellow]")
                console.print("    Executing simulated high-concurrency traffic...")

            logger.log_step(
                event_type="STATE_CHANGE",
                agent_name=self.verifier_agent.name,
                state=AgentStatus.EXECUTING_TOOLS.value,
                metadata={"from_state": AgentStatus.ANALYZING.value, "to_state": AgentStatus.EXECUTING_TOOLS.value}
            )
            verification = self.verifier_agent.verify(submission, spec)
            pipeline_data["verification"] = verification

            if self.verbose:
                lm = verification.load_metrics
                deadlock_str = "[red]YES (DEADLOCK DETECTED!)[/red]" if lm.distributed_deadlock_detected else "[green]NO[/green]"
                sla_str = "[green]MET[/green]" if lm.sla_met else "[red]VIOLATED[/red]"
                console.print(f"    ✓ Concurrency Throughput: [bold]{lm.throughput_rps:.1f} RPS[/bold] | P95 Latency: [bold]{lm.p95_latency_ms:.1f}ms[/bold]")
                console.print(f"    ✓ Peak Process Memory: [bold]{lm.memory_peak_mb:.1f} MB[/bold] | Error Rate: [bold]{lm.error_rate_pct:.1f}%[/bold]")
                console.print(f"    ✓ Distributed Deadlock: {deadlock_str}")
                console.print(f"    ✓ Non-Functional SLA: {sla_str} ({lm.details})")

            logger.log_step(
                event_type="TOOL_RESPONSE",
                agent_name=self.verifier_agent.name,
                state=AgentStatus.EXECUTING_TOOLS.value,
                output_data=verification.model_dump(),
                metadata={"tool_name": "LoadSimulator & SecurityScanner"}
            )
            return AgentStatus.VERIFYING

        # 4. VERIFYING Handler (Senior Critic Multi-Agent Synthesis)
        async def handle_verifying(ctx: AgentContext) -> AgentStatus:
            if self.verbose:
                console.print("\n[bold cyan]📍 FSM STAGE 4: SENIOR CRITIC MULTI-AGENT SYNTHESIS[/bold cyan]")
                console.print(f"  • Agent: [bold]{self.critic_agent.name}[/bold]")
                console.print("    Synthesizing AST telemetry, runtime load metrics, and security scan into holistic dossier...")

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

        # 5. HUMAN_CHECKPOINT Handler (Contextual Review Card & Interactive Approval)
        async def handle_human_checkpoint(ctx: AgentContext) -> AgentStatus:
            dossier: SeniorVettingDossier = pipeline_data.get("dossier")
            verification = pipeline_data.get("verification")
            
            if self.verbose:
                console.print("\n[bold yellow]📍 FSM STAGE 5: HUMAN-IN-THE-LOOP QUALITY GATE[/bold yellow]")
                console.print(f"  ⚠️ Action Required: Candidate score ({dossier.overall_vetting_score:.1f}/100) or trade-off complexity triggered mandatory human review.")

            logger.log_step(
                event_type="STATE_CHANGE",
                agent_name="HumanInTheLoopGate",
                state=AgentStatus.HUMAN_CHECKPOINT.value,
                metadata={
                    "reason": "Borderline score or consequential verdict requiring human reviewer sign-off.",
                    "ai_recommended_score": dossier.overall_vetting_score,
                    "ai_recommendation": dossier.recommendation.value
                }
            )

            # If running in interactive mode and input is connected to terminal
            if self.interactive_human_gate and sys.stdin.isatty():
                # Render Full Decision Review Card
                console.print("\n")
                console.print(Panel(
                    f"[bold red]🛑 HUMAN-IN-THE-LOOP ARCHITECTURAL DECISION GATE[/bold red]\n"
                    f"Candidate: [bold cyan]{submission.candidate_id}[/bold cyan] | Target: [bold]{spec.title}[/bold] ({spec.github_repo or 'Local'})\n\n"
                    f"[bold underline]📊 AI Telemetry & Multi-Pillar Breakdown:[/bold underline]\n"
                    f"  • AI Proposed Score: [bold cyan]{dossier.overall_vetting_score:.1f} / 100[/bold cyan] ({dossier.recommendation.value})\n"
                    f"  • Architecture & Systems:      [bold]{dossier.architecture_score:.1f} / 100[/bold]\n"
                    f"  • Concurrency & Scalability:   [bold]{dossier.concurrency_scalability_score:.1f} / 100[/bold]\n"
                    f"  • Code Quality & Reusability:  [bold]{dossier.code_quality_reusability_score:.1f} / 100[/bold]\n\n"
                    f"[bold underline]🔍 Flagged Flaws & Evidence Citations:[/bold underline]\n" +
                    ("\n".join([f"  [!] {flaw}" for flaw in dossier.primary_flaws_flagged]) if dossier.primary_flaws_flagged else "  None flagged.") + "\n\n"
                    f"[bold underline]📝 Executive Summary & Justification:[/bold underline]\n"
                    f"  {dossier.executive_summary}",
                    title="Human Review Decision Panel",
                    border_style="yellow"
                ))

                console.print("[bold]Reviewer Actions:[/bold]")
                console.print("  [green][1][/green] ✅ Confirm AI Verdict and Sign Dossier (Recommended)")
                console.print("  [yellow][2][/yellow] ✏️ Override Score & Recommendation with Human Notes")
                console.print("  [cyan][3][/cyan] ⏩ Proceed with Dossier Unmodified")
                
                choice = Prompt.ask("\nSelect action", choices=["1", "2", "3"], default="1")

                if choice == "2":
                    new_score_str = Prompt.ask("Enter override score (0-100)", default=str(dossier.overall_vetting_score))
                    try:
                        new_score = float(new_score_str)
                        dossier.overall_vetting_score = max(0.0, min(100.0, new_score))
                        if new_score >= 70.0:
                            dossier.recommendation = RecommendationType.HIRE
                        else:
                            dossier.recommendation = RecommendationType.LEAN_NO
                    except ValueError:
                        pass
                    override_note = Prompt.ask("Enter Tech Lead review note", default="Human reviewer validated trade-offs.")
                    dossier.trade_off_analysis += f"\n[Human Reviewer Override]: {override_note}"
                    console.print(f"[green]✓ Score updated to {dossier.overall_vetting_score:.1f} ({dossier.recommendation.value}).[/green]")
                else:
                    console.print("[green]✓ AI Verdict signed by Human Reviewer.[/green]")

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

        if self.verbose:
            console.print("\n[bold green]🏁 FSM EXECUTION COMPLETED[/bold green]")
            table = Table(title=f"📋 Final Senior Vetting Dossier: {spec.title}", header_style="bold green")
            table.add_column("Pillar / Metric", style="cyan")
            table.add_column("Score / Result", justify="right", style="bold")
            table.add_row("Overall Vetting Score", f"{dossier.overall_vetting_score:.1f} / 100")
            table.add_row("Hiring Recommendation", dossier.recommendation.value)
            table.add_row("Architecture & Systems Score", f"{dossier.architecture_score:.1f} / 100")
            table.add_row("Concurrency & Scalability Score", f"{dossier.concurrency_scalability_score:.1f} / 100")
            table.add_row("Code Quality & Reusability Score", f"{dossier.code_quality_reusability_score:.1f} / 100")
            table.add_row("Primary Flaws Flagged", str(len(dossier.primary_flaws_flagged)))
            console.print(table)
            console.print(Panel(dossier.executive_summary, title="Executive Summary", border_style="cyan"))

        logger.finalize(success=(dossier.overall_vetting_score >= 70.0))
        return dossier, logger
