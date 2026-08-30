"""Agent 4: Senior Engineering Alignment Critic with Continuous Scoring & LLM Calibration."""

import os
import re
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
Your role is to produce a rigorous, grounded, and evidence-backed technical evaluation.

You will receive:
1. The scenario specification and the KNOWN architectural flaw in the repository
2. The candidate's submitted Git diff
3. Tool-collected evidence: load simulation metrics, blast radius analysis, and codebase alignment data
4. A formula-computed preliminary score

Your tasks:
A) Analyze whether the candidate's diff addresses or worsens the known architectural flaw.
B) Propose a CALIBRATED SCORE (0-100) based on ALL evidence. You may adjust the formula score up or down.
C) Write a 2-3 sentence executive summary citing exact technical trade-offs.

SCORING GUIDELINES:
- 0-30: Critical flaws — deadlocks, SQL injection, event loop collapse, data corruption
- 31-50: Major architectural flaws — state drift, memory exhaustion, race conditions, SLA violations
- 51-70: Moderate issues — breaking public response schemas without versioning, suboptimal patterns, missed codebase reuse
- 71-85: Good with minor concerns — solid architecture, minor debt, thundering herd risk
- 86-100: Exceptional — addresses all distributed concerns, clean, reusable, atomic

REQUIRED OUTPUT FORMAT (strict):
CalibratedScore: <integer 0-100>
Recommendation: <STRONG_HIRE | HIRE | LEAN_NO | REJECT>
Summary: <2-3 sentence technical justification>
"""


class SeniorEngineeringCriticAgent:
    """Synthesizes all multi-agent observations into a Senior Vetting Dossier.
    
    Uses a continuous penalty formula based on severity signals from tools,
    then calibrates the score via LLM reasoning to capture nuance that
    pure formulas miss.
    """

    def __init__(self, name: str = "SeniorEngineeringCriticAgent", model: str = None):
        self.name = name
        self.model = model or os.getenv("ADVANCED_MODEL", os.getenv("DEFAULT_MODEL", "groq/openai/gpt-oss-20b"))
        self.llm_client = LLMClient(default_model=self.model)
        self.last_tokens: int = 0
        self.last_cost_usd: float = 0.0
        self.last_latency_ms: float = 0.0

    def _compute_formula_score(
        self,
        alignment_data: Dict[str, Any],
        verification_report: VerificationReport,
        spec: ScenarioSpec
    ) -> Dict[str, float]:
        """Compute continuous scores using severity-graduated signals from tools."""
        
        blast_score = alignment_data.get("blast_radius", {}).get("blast_radius_score", 1.0)
        context_score = alignment_data.get("context_alignment", {}).get("alignment_score", 1.0)
        api_contract_preserved = alignment_data.get("context_alignment", {}).get("api_contract_preserved", True)

        load = verification_report.load_metrics
        severity = load.severity_multiplier  # 0.0 = no issue, 1.0 = catastrophic

        # --- Architecture Score (continuous) ---
        arch_score = 95.0 - (severity * 75.0)
        
        # Additional penalty for security vulnerabilities (e.g. SQLi)
        if not verification_report.static_analysis_clean:
            arch_score -= 30.0
        
        # Penalty for breaking public API contracts without versioning
        if not api_contract_preserved:
            arch_score -= 45.0
        
        arch_score = max(10.0, min(95.0, arch_score))

        # --- Concurrency/Scalability Score (continuous) ---
        scalability_score = 92.0 - (severity * 67.0)
        
        # Penalty for broken API contracts on downstream clients
        if not api_contract_preserved:
            scalability_score -= 35.0
            
        # Extra penalty based on error rate magnitude
        if load.error_rate_pct > 0:
            error_penalty = min(20.0, load.error_rate_pct * 0.5)
            scalability_score -= error_penalty
        
        scalability_score = max(10.0, min(92.0, scalability_score))

        # --- Code Quality Score (from tool signals) ---
        code_quality_score = round(((blast_score + context_score) / 2.0) * 100.0, 1)
        code_quality_score = max(10.0, min(100.0, code_quality_score))

        # --- Weighted Overall ---
        overall = round(
            (arch_score * 0.40) + (scalability_score * 0.40) + (code_quality_score * 0.20),
            1
        )
        overall = max(0.0, min(100.0, overall))

        return {
            "arch_score": round(arch_score, 1),
            "scalability_score": round(scalability_score, 1),
            "code_quality_score": round(code_quality_score, 1),
            "overall": round(overall, 1),
            "severity": severity
        }

    async def generate_dossier(
        self,
        submission: CandidateSubmission,
        spec: ScenarioSpec,
        alignment_data: Dict[str, Any],
        verification_report: VerificationReport
    ) -> SeniorVettingDossier:
        """Produces the final holistic vetting dossier with formula + LLM calibration."""
        
        # Step 1: Compute formula-based scores
        formula = self._compute_formula_score(alignment_data, verification_report, spec)
        
        load = verification_report.load_metrics
        api_contract_preserved = alignment_data.get("context_alignment", {}).get("api_contract_preserved", True)

        # Step 2: Collect evidence citations and flaws
        citations: List[EvidenceCitation] = []
        flaws: List[str] = []

        if not load.sla_met or load.distributed_deadlock_detected or load.error_rate_pct > 0.0:
            flaws.append(load.details)
            citations.append(
                EvidenceCitation(
                    file_path=submission.file_changes[0].path if submission.file_changes else "src/service.py",
                    severity=FindingSeverity.CRITICAL_FLAW if (load.distributed_deadlock_detected or not verification_report.static_analysis_clean) else FindingSeverity.MAJOR_DEBT,
                    title="Concurrency / Load SLA Finding",
                    explanation=load.details
                )
            )

        if not verification_report.static_analysis_clean:
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

        # Step 3: LLM Calibration — ask the model to propose a calibrated score
        user_msg = (
            f"=== SCENARIO ===\n"
            f"Title: {spec.title} ({spec.github_repo})\n"
            f"Architecture: {spec.architecture_type.value}\n"
            f"Known Architectural Flaw: {spec.ground_truth_flaw}\n"
            f"Expected Optimal Fix: {spec.expected_optimal_solution}\n\n"
            f"=== CANDIDATE DIFF ===\n{submission.full_diff}\n\n"
            f"=== TOOL EVIDENCE ===\n"
            f"Load Simulation: severity={formula['severity']:.2f}, "
            f"p95={load.p95_latency_ms}ms (SLA={spec.requirements.latency_p95_sla_ms}ms), "
            f"error_rate={load.error_rate_pct}%, "
            f"memory_peak={load.memory_peak_mb}MB (max={spec.requirements.max_memory_mb}MB), "
            f"deadlock={load.distributed_deadlock_detected}\n"
            f"Codebase Alignment: {json.dumps(alignment_data.get('findings', []))}\n"
            f"Security Issues: {json.dumps(verification_report.security_vulnerabilities_found)}\n\n"
            f"=== FORMULA PRELIMINARY SCORE ===\n"
            f"Architecture: {formula['arch_score']}/100, Scalability: {formula['scalability_score']}/100, "
            f"Code Quality: {formula['code_quality_score']}/100 → Overall: {formula['overall']}/100\n"
            f"Detected Flaws: {json.dumps(flaws)}\n\n"
            f"Based on ALL evidence above, provide your CalibratedScore, Recommendation, and Summary."
        )

        llm_res = await self.llm_client.acomplete(
            messages=[
                {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            model=self.model,
            temperature=0.2
        )

        # Track LLM telemetry metrics
        self.last_tokens = llm_res.total_tokens
        self.last_cost_usd = llm_res.cost_usd
        self.last_latency_ms = llm_res.latency_ms

        # Step 4: Parse LLM response and blend scores
        llm_score = formula["overall"]  # Fallback
        llm_recommendation = None
        executive_summary = ""

        if llm_res.content:
            content = llm_res.content.strip()
            
            score_match = re.search(r"CalibratedScore:\s*(\d+(?:\.\d+)?)", content)
            if score_match:
                llm_score = float(score_match.group(1))
                llm_score = max(0.0, min(100.0, llm_score))
            else:
                score_match = re.search(r"Score:\s*(\d+(?:\.\d+)?)", content)
                if score_match:
                    llm_score = float(score_match.group(1))
                    llm_score = max(0.0, min(100.0, llm_score))
            
            if "STRONG_HIRE" in content:
                llm_recommendation = RecommendationType.STRONG_HIRE
            elif "LEAN_NO" in content:
                llm_recommendation = RecommendationType.LEAN_NO
            elif "REJECT" in content:
                llm_recommendation = RecommendationType.REJECT
            elif "HIRE" in content:
                llm_recommendation = RecommendationType.HIRE
            
            summary_match = re.search(r"Summary:\s*(.+)", content, re.DOTALL)
            if summary_match:
                executive_summary = summary_match.group(1).strip()
            else:
                executive_summary = content

        # Step 5: Blend formula and LLM scores (60% formula, 40% LLM)
        blended_score = round((formula["overall"] * 0.6) + (llm_score * 0.4), 1)
        blended_score = max(0.0, min(100.0, blended_score))

        if llm_recommendation:
            recommendation = llm_recommendation
        else:
            if blended_score >= 85.0:
                recommendation = RecommendationType.STRONG_HIRE
            elif blended_score >= 65.0:
                recommendation = RecommendationType.HIRE
            elif blended_score >= 50.0:
                recommendation = RecommendationType.LEAN_NO
            else:
                recommendation = RecommendationType.REJECT

        if not executive_summary:
            executive_summary = (
                f"Candidate scored {blended_score}/100 in Scenario {spec.scenario_id}. "
                f"Architecture: {formula['arch_score']}%, Scalability: {formula['scalability_score']}%, "
                f"Code Quality: {formula['code_quality_score']}%. "
                f"Recommendation: {recommendation.value}."
            )

        trade_off_analysis = (
            f"Formula score: {formula['overall']:.1f}, LLM calibrated score: {llm_score:.1f}, "
            f"blended (60/40): {blended_score:.1f}. "
            f"Severity multiplier from load simulation: {formula['severity']:.2f}. "
            f"{'Met all target SLAs and distributed contracts.' if (load.sla_met and api_contract_preserved) else f'Failed distributed contracts/SLAs: {load.details}'}"
        )

        return SeniorVettingDossier(
            candidate_id=submission.candidate_id,
            scenario_id=spec.scenario_id,
            overall_vetting_score=blended_score,
            recommendation=recommendation,
            architecture_score=formula["arch_score"],
            concurrency_scalability_score=formula["scalability_score"],
            code_quality_reusability_score=formula["code_quality_score"],
            executive_summary=executive_summary,
            trade_off_analysis=trade_off_analysis,
            evidence_citations=citations,
            primary_flaws_flagged=flaws,
            human_in_the_loop_approval_needed=(45.0 <= blended_score < 65.0)
        )
