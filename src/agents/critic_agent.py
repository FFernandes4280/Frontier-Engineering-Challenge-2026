"""Agent 4: Senior Engineering Alignment Critic."""

import os
import json
from typing import Dict, Any, List
from src.core.domain import (
    ScenarioSpec,
    CandidateSubmission,
    VerificationReport,
    SeniorVettingDossier,
    RecommendationType,
    FindingSeverity,
    EvidenceCitation
)
from src.core.llm import LLMClient


CRITIC_SYSTEM_PROMPT = """You are a Principal Software Architect and Senior Vetting Evaluator for micro1.
Your role is to produce a rigorous, grounded, and evidence-backed technical dossier evaluating a senior software engineer's code submission.

Rules for your evaluation:
- Cite specific architectural flaws, concurrency bottlenecks, deadlocks, and codebase redundancy.
- Return your executive summary in 3-4 sentences highlighting the primary technical decision and recommendation.
"""


class SeniorEngineeringCriticAgent:
    """Synthesizes all multi-agent observations into a Senior Vetting Dossier."""

    def __init__(self, name: str = "SeniorEngineeringCriticAgent", model: str = None):
        self.name = name
        self.model = model or os.getenv("ADVANCED_MODEL", os.getenv("DEFAULT_MODEL", "gemini/gemini-1.5-flash"))
        self.llm_client = LLMClient(default_model=self.model)

    async def generate_dossier(
        self,
        submission: CandidateSubmission,
        spec: ScenarioSpec,
        alignment_data: Dict[str, Any],
        verification_report: VerificationReport
    ) -> SeniorVettingDossier:
        """Produces the final holistic vetting dossier with real LLM synthesis."""
        
        blast_score = alignment_data.get("blast_radius", {}).get("blast_radius_score", 1.0)
        context_score = alignment_data.get("context_alignment", {}).get("alignment_score", 1.0)
        api_contract_preserved = alignment_data.get("context_alignment", {}).get("api_contract_preserved", True)

        load = verification_report.load_metrics
        load_sla_met = load.sla_met
        deadlock = load.distributed_deadlock_detected
        security_clean = verification_report.static_analysis_clean

        # Score formulation
        if deadlock:
            arch_score = 30.0
            scalability_score = 25.0
        elif not security_clean:
            arch_score = 20.0
            scalability_score = 40.0
        elif not api_contract_preserved:
            arch_score = 45.0
            scalability_score = 60.0
        elif load.error_rate_pct > 10.0:
            arch_score = 40.0
            scalability_score = 35.0
        elif not load_sla_met:
            if load.memory_peak_mb > spec.requirements.max_memory_mb:
                arch_score = 50.0
                scalability_score = 45.0
            else:
                arch_score = 75.0
                scalability_score = 72.0
        else:
            arch_score = 95.0
            scalability_score = 92.0

        code_quality_score = round(((blast_score + context_score) / 2.0) * 100.0, 1)
        overall_score = round((arch_score * 0.40) + (scalability_score * 0.40) + (code_quality_score * 0.20), 1)
        overall_score = max(0.0, min(100.0, overall_score))

        if overall_score >= 85.0:
            recommendation = RecommendationType.STRONG_HIRE
        elif overall_score >= 65.0:
            recommendation = RecommendationType.HIRE
        elif overall_score >= 50.0:
            recommendation = RecommendationType.LEAN_NO
        else:
            recommendation = RecommendationType.REJECT

        citations: List[EvidenceCitation] = []
        flaws: List[str] = []

        if not load_sla_met or deadlock or load.error_rate_pct > 0.0:
            flaws.append(load.details)
            citations.append(
                EvidenceCitation(
                    file_path=submission.file_changes[0].path if submission.file_changes else "src/service.py",
                    severity=FindingSeverity.CRITICAL_FLAW if (deadlock or not security_clean) else FindingSeverity.MAJOR_DEBT,
                    title="Concurrency / Load SLA Finding",
                    explanation=load.details
                )
            )

        if not security_clean:
            for vuln in verification_report.security_vulnerabilities_found:
                flaws.append(vuln)
                citations.append(
                    EvidenceCitation(
                        file_path="src/services",
                        severity=FindingSeverity.CRITICAL_FLAW,
                        title="Security Vulnerability",
                        explanation=vuln
                    )
                )

        if not api_contract_preserved:
            flaws.append("Breaking contract change: Deleted response field in public API without deprecation cycle.")
            citations.append(
                EvidenceCitation(
                    file_path="src/api",
                    severity=FindingSeverity.MAJOR_DEBT,
                    title="Breaking Public API Contract",
                    explanation="Direct deletion of legacy fields breaks downstream client backwards compatibility."
                )
            )

        for finding in alignment_data.get("findings", []):
            flaws.append(finding)
            citations.append(
                EvidenceCitation(
                    file_path="src/repository",
                    severity=FindingSeverity.MINOR_CONCERN,
                    title="Codebase Alignment Finding",
                    explanation=finding
                )
            )

        # Execute real LLM call for Senior Engineering Critique
        user_msg = (
            f"Candidate: {submission.candidate_id}\n"
            f"Scenario: {spec.title} ({spec.github_repo})\n"
            f"Ground Truth Flaw in Repo: {spec.ground_truth_flaw}\n"
            f"Diff:\n{submission.full_diff}\n"
            f"Load Test Metrics: {load.model_dump_json()}\n"
            f"Calculated Score: {overall_score}/100 ({recommendation.value})\n"
            f"Findings: {json.dumps(flaws)}\n"
            f"Summarize the technical decision and final recommendation."
        )

        llm_res = await self.llm_client.acomplete(
            messages=[
                {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            model=self.model,
            temperature=0.2
        )

        executive_summary = llm_res.content.strip() if llm_res.content else (
            f"Candidate scored {overall_score}/100 in Scenario {spec.scenario_id}. "
            f"Architecture: {arch_score}%, Scalability: {scalability_score}%, Code Quality: {code_quality_score}%. "
            f"Recommendation: {recommendation.value}."
        )

        trade_off_analysis = (
            f"The submission was evaluated for horizontal consistency, memory footprint, and concurrency safety. "
            f"{'Met all target SLAs and distributed contracts.' if (load_sla_met and api_contract_preserved) else f'Failed distributed contracts/SLAs: {load.details}'}"
        )

        return SeniorVettingDossier(
            candidate_id=submission.candidate_id,
            scenario_id=spec.scenario_id,
            overall_vetting_score=overall_score,
            recommendation=recommendation,
            architecture_score=arch_score,
            concurrency_scalability_score=scalability_score,
            code_quality_reusability_score=code_quality_score,
            executive_summary=executive_summary,
            trade_off_analysis=trade_off_analysis,
            evidence_citations=citations,
            primary_flaws_flagged=flaws,
            human_in_the_loop_approval_needed=(50.0 <= overall_score < 65.0)
        )
