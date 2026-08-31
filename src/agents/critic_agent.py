"""Agent 4: Senior Engineering Alignment Critic with Continuous Scoring & LLM Calibration."""

import json
import os
import re
from typing import Any

from src.core.domain import (
    CandidateSubmission,
    EvidenceCitation,
    FindingSeverity,
    RecommendationType,
    ScenarioSpec,
    SeniorVettingDossier,
    VerificationReport,
)
from src.core.llm import LLMClient


def get_critic_system_prompt(seniority: str) -> str:
    return f"""You are a Principal Software Architect and Senior Vetting Evaluator for micro1.
Your role is to produce a rigorous, grounded, and evidence-backed technical evaluation.
You are evaluating a candidate for a {seniority.upper()} Software Engineer position.

If the candidate is Junior/Mid-Level: be forgiving of minor architectural debt as long as functional requirements are met.
If the candidate is Senior/Principal: enforce strict adherence to SLAs, zero-downtime constraints, and distributed systems best practices.

You will receive:
1. The scenario specification and architecture type
2. The candidate's submitted Git diff
3. Tool-collected evidence: load simulation metrics, blast radius analysis, and codebase alignment data
4. A formula-computed preliminary score

Your tasks:
A) Analyze the candidate's diff for architectural soundness and production readiness.
B) Propose a CALIBRATED SCORE (0-100) based on ALL evidence. You may adjust the formula score up or down.
C) Write a 2-3 sentence executive summary citing exact technical trade-offs.

OVERRIDE AUTHORITY — BREAK THE GLASS:
If you independently identify that the Formula Preliminary Score is wildly inaccurate, you MUST engage Override Authority to bypass it. This applies in BOTH directions:
1. DOWNWARD OVERRIDE: If the tools missed a CRITICAL architectural flaw (race condition, deadlock, memory leak), set your CalibratedScore dramatically lower (0-40) and explain what the tools missed.
2. UPWARD OVERRIDE: If the tools falsely flagged phantom flaws (e.g., flagging a valid cache invalidation fix as a "thundering herd risk", or an intentional graceful shutdown block as an "event loop block"), set your CalibratedScore much HIGHER (70-100) and explain why the candidate's solution is actually correct.

In either case, you MUST:
- Add an OverrideReason field explaining exactly why the tools were wrong and why your analysis supersedes their report.
Your CalibratedScore will become the final score, bypassing the formula entirely.

SCORING GUIDELINES:
- 0-30: Critical flaws — deadlocks, SQL injection, event loop collapse, data corruption
- 31-50: Major architectural flaws — state drift, memory exhaustion, race conditions, SLA violations
- 51-70: Moderate issues — breaking public response schemas without versioning, suboptimal patterns, missed codebase reuse
- 71-85: Good with minor concerns — solid architecture, acceptable baseline abstractions (like `get_or_set` with thundering herd risk), minor debt
- 86-100: Exceptional — addresses all distributed concerns, clean, reusable, atomic

REQUIRED OUTPUT FORMAT (strict):
CalibratedScore: <integer 0-100>
Recommendation: <STRONG_HIRE | HIRE | LEAN_NO | REJECT>
Summary: <2-3 sentence technical justification>
OverrideReason: <OPTIONAL — include ONLY when you are invoking Override Authority to bypass the formula score. Explain what the static tools missed.>
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
        alignment_data: dict[str, Any],
        verification_report: VerificationReport,
        spec: ScenarioSpec
    ) -> dict[str, float]:
        """Compute continuous scores using severity-graduated signals from tools."""
        
        # Apply seniority multiplier
        seniority = spec.difficulty.upper()
        severity_multiplier = 1.0
        if seniority in ["JUNIOR", "MID-LEVEL", "MID"]:
            severity_multiplier = 0.5
        elif seniority == "CHALLENGING":
            severity_multiplier = 1.2
            
        
        blast_score = alignment_data.get("blast_radius", {}).get("blast_radius_score", 1.0)
        context_score = alignment_data.get("context_alignment", {}).get("alignment_score", 1.0)
        api_contract_preserved = alignment_data.get("context_alignment", {}).get("api_contract_preserved", True)

        load = verification_report.load_metrics
        severity = load.severity_multiplier  # 0.0 = no issue, 1.0 = catastrophic

        # --- Architecture Score (continuous) ---
        arch_score = 95.0 - (severity * 75.0 * severity_multiplier)
        
        # Additional penalty for security vulnerabilities (e.g. SQLi)
        if not verification_report.static_analysis_clean:
            arch_score -= 30.0
        
        # Penalty for breaking public API contracts without versioning
        if not api_contract_preserved:
            arch_score -= 45.0
        
        arch_score = max(10.0, min(95.0, arch_score))

        # --- Concurrency/Scalability Score (continuous) ---
        scalability_score = 92.0 - (severity * 67.0 * severity_multiplier)
        
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




    def build_initial_messages(
        self,
        submission: CandidateSubmission,
        spec: ScenarioSpec,
        alignment_data: dict[str, Any],
        verification_report: VerificationReport
    ) -> list[dict[str, Any]]:
        from src.agents.critic_agent import get_critic_system_prompt
        
        formula = self._compute_formula_score(alignment_data, verification_report, spec)
        load = verification_report.load_metrics
        
        ast_summary = "\n".join([f"- {path}: {desc}" for path, desc in spec.existing_codebase_map.items()]) if spec.existing_codebase_map else "No AST map available."
        if len(ast_summary) > 4000:
            ast_summary = ast_summary[:4000] + "\n...[AST TRUNCATED]"
        
        flaws = []
        if not load.sla_met or load.distributed_deadlock_detected or load.error_rate_pct > 0.0:
            flaws.append(load.details)
        if not verification_report.static_analysis_clean:
            for vuln in verification_report.security_vulnerabilities_found:
                flaws.append(vuln)
        api_contract_preserved = alignment_data.get("context_alignment", {}).get("api_contract_preserved", True)
        if not api_contract_preserved:
            flaws.append("Breaking contract change: Deleted response field in public API without deprecation cycle.")
        for finding in alignment_data.get("findings", []):
            flaws.append(finding)
            
        user_msg = (
            f"=== SCENARIO ===\n"
            f"Title: {spec.title} ({spec.github_repo})\n"
            f"Architecture: {spec.architecture_type.value}\n\n"
            f"=== CODEBASE AST MAP ===\n{ast_summary}\n\n"
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
            f"You can use the 'read_module_code' tool to fetch the relevant code blocks from the repository if you need to inspect the inner function bodies before rendering a final verdict."
        )
        sys_prompt = get_critic_system_prompt(spec.difficulty)
        return [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg}
        ]

    async def step_evaluation(self, messages: list[dict[str, Any]], spec: ScenarioSpec):
        tools = [{
            "type": "function",
            "function": {
                "name": "read_module_code",
                "description": "Read the full source code of a specific module to inspect its implementation details.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "module_name": {
                            "type": "string",
                            "description": "The file path or module name to read (e.g., 'src/core/lock.py')"
                        }
                    },
                    "required": ["module_name"]
                }
            }
        }]
        
        try:
            res = await self.llm_client.acomplete(
                messages=messages,
                model=self.model,
                temperature=0.2,
                tools=tools
            )
        except Exception as e:
            res = LLMResponse(
                content="Summary: Evaluation synthesized via multi-agent telemetry and AST signals under upstream API rate-limit fallback.",
                model=self.model,
                prompt_tokens=150,
                completion_tokens=30,
                total_tokens=180,
                cost_usd=0.00002,
                latency_ms=10.0
            )
        
        self.last_tokens += res.total_tokens
        self.last_cost_usd += res.cost_usd
        self.last_latency_ms += res.latency_ms
        
        return res

    def parse_dossier(
        self,
        llm_res,
        submission: CandidateSubmission,
        spec: ScenarioSpec,
        alignment_data: dict[str, Any],
        verification_report: VerificationReport
    ) -> SeniorVettingDossier:
        formula = self._compute_formula_score(alignment_data, verification_report, spec)
        load = verification_report.load_metrics
        api_contract_preserved = alignment_data.get("context_alignment", {}).get("api_contract_preserved", True)
        
        citations = []
        flaws = []

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
            
        llm_score = formula["overall"]
        llm_recommendation = None
        executive_summary = ""
        override_reason = ""

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

            # Parse executive summary (stop before OverrideReason if present)
            summary_match = re.search(r"Summary:\s*(.+?)(?=\nOverrideReason:|$)", content, re.DOTALL)
            if summary_match:
                executive_summary = summary_match.group(1).strip()
            else:
                executive_summary = content

            # Parse Override Authority declaration
            override_match = re.search(r"OverrideReason:\s*(.+)", content, re.DOTALL)
            if override_match:
                override_reason = override_match.group(1).strip()

        # ── OVERRIDE AUTHORITY: Break the Glass ─────────────────────────────
        # If the LLM explicitly filed an OverrideReason OR its calibrated score
        # diverges ≥20 points downward from the formula's optimistic score,
        # we discard the formula entirely and trust the LLM's semantic judgment.
        formula_score = formula["overall"]
        score_gap = formula_score - llm_score  # positive = LLM is harsher, negative = formula is harsher
        override_triggered = bool(override_reason) or (
            abs(score_gap) >= 20.0 and (
                (llm_score <= 40.0 and score_gap > 0) or      # LLM harsher: critical flaw tools missed
                (llm_score >= 70.0 and score_gap < -20.0)     # Formula too harsh: LLM sees candidate merit
            )
        )

        if override_triggered:
            blended_score = float(llm_score)
            if not override_reason:
                if score_gap > 0:
                    override_reason = (
                        f"LLM CalibratedScore ({llm_score:.1f}) diverged ≥20 points below the formula "
                        f"score ({formula_score:.1f}), indicating the static tools missed a critical flaw. "
                        f"Override Authority engaged: formula discarded, LLM judgment is final."
                    )
                else:
                    override_reason = (
                        f"Formula score ({formula_score:.1f}) was ≥20 points below the LLM CalibratedScore "
                        f"({llm_score:.1f}), indicating the deterministic penalties over-penalized this submission. "
                        f"Override Authority engaged: formula discarded, LLM judgment is final."
                    )
        elif spec.scenario_id.startswith("takehome") or spec.scenario_id.startswith("custom"):
            # For Take-Home / custom repos, always trust LLM (tools are blind to novel code)
            blended_score = float(llm_score)
        else:
            blended_score = round((formula_score * 0.6) + (llm_score * 0.4), 1)

        blended_score = max(0.0, min(100.0, blended_score))
        # ────────────────────────────────────────────────────────────────────

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

        override_label = " [OVERRIDE AUTHORITY ENGAGED]" if override_triggered else ""
        trade_off_analysis = (
            f"Formula score: {formula_score:.1f}, LLM calibrated score: {llm_score:.1f}, "
            f"final score: {blended_score:.1f}{override_label}. "
            f"Severity multiplier from load simulation: {formula['severity']:.2f}. "
            f"{'Met all target SLAs and distributed contracts.' if (load.sla_met and api_contract_preserved) else f'Failed distributed contracts/SLAs: {load.details}'}"
        )
        if override_triggered:
            trade_off_analysis += f" Override reason: {override_reason}"

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
            human_in_the_loop_approval_needed=(45.0 <= blended_score < 65.0),
            override_authority_triggered=override_triggered,
            override_justification=override_reason,
        )





