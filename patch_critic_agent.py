import re
from src.agents.critic_agent import SeniorEngineeringCriticAgent
from src.core.domain import CandidateSubmission, ScenarioSpec, VerificationReport, EvidenceCitation, FindingSeverity, RecommendationType, SeniorVettingDossier
import json
from typing import Any

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
        f"Architecture: {spec.architecture_type.value}\n"
        f"Known Architectural Flaw: {spec.ground_truth_flaw}\n"
        f"Expected Optimal Fix: {spec.expected_optimal_solution}\n\n"
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
    
    res = await self.llm_client.acomplete(
        messages=messages,
        model=self.model,
        temperature=0.2,
        tools=tools
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

SeniorEngineeringCriticAgent.build_initial_messages = build_initial_messages
SeniorEngineeringCriticAgent.step_evaluation = step_evaluation
SeniorEngineeringCriticAgent.parse_dossier = parse_dossier

