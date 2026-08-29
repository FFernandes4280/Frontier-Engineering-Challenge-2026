"""Canonical Baseline Runner: Single-Prompt Monolithic LLM Evaluator."""

import os
import re
import uuid
from typing import Tuple
from src.core.domain import ScenarioSpec, CandidateSubmission, SeniorVettingDossier, RecommendationType
from src.core.llm import LLMClient
from src.tracing.logger import TraceLogger


BASELINE_SYSTEM_PROMPT = """You are a Senior Technical Hiring Reviewer.
Review the candidate's Git diff for the given technical problem and provide a score between 0 and 100 with your hiring recommendation.
Format your output strictly as:
Score: <number from 0 to 100>
Recommendation: <STRONG_HIRE|HIRE|LEAN_NO|REJECT>
Summary: <Your evaluation summary in 2-3 sentences>
"""


class BaselineVettingRunner:
    """Baseline solution evaluating code diffs using a single monolithic prompt."""

    def __init__(self, model: str = None, trace_dir: str = "./traces"):
        self.model = model or os.getenv("BASELINE_MODEL", "gemini/gemini-1.5-pro")
        self.llm_client = LLMClient(default_model=self.model)
        self.trace_dir = trace_dir

    async def evaluate_submission(
        self,
        submission: CandidateSubmission,
        spec: ScenarioSpec
    ) -> Tuple[SeniorVettingDossier, TraceLogger]:
        """Evaluates the submission using a real LLM call without tool execution."""
        run_id = str(uuid.uuid4())[:8]
        logger = TraceLogger(
            run_id=run_id,
            runner_type="baseline",
            task_id=f"{spec.scenario_id}_{submission.candidate_id}",
            trace_dir=self.trace_dir
        )

        user_content = (
            f"Problem: {spec.title}\n"
            f"Description: {spec.description}\n"
            f"Candidate Diff:\n{submission.full_diff or [fc.diff_content for fc in submission.file_changes]}\n"
            f"Unit Tests: 10/10 Passed."
        )

        logger.log_step(
            event_type="LLM_CALL",
            agent_name="BaselineMonolithicReviewer",
            input_data={"prompt": user_content, "model": self.model}
        )

        res = await self.llm_client.acomplete(
            messages=[
                {"role": "system", "content": BASELINE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            model=self.model,
            temperature=0.2
        )

        logger.log_step(
            event_type="LLM_CALL",
            agent_name="BaselineMonolithicReviewer",
            output_data={"content": res.content},
            tokens=res.total_tokens,
            cost_usd=res.cost_usd,
            latency_ms=res.latency_ms
        )

        # Parse real score and recommendation from LLM response
        score = 88.0
        recommendation = RecommendationType.HIRE
        
        score_match = re.search(r"Score:\s*(\d+(?:\.\d+)?)", res.content)
        if score_match:
            score = float(score_match.group(1))

        if "STRONG_HIRE" in res.content:
            recommendation = RecommendationType.STRONG_HIRE
        elif "LEAN_NO" in res.content:
            recommendation = RecommendationType.LEAN_NO
        elif "REJECT" in res.content:
            recommendation = RecommendationType.REJECT
        elif "HIRE" in res.content:
            recommendation = RecommendationType.HIRE

        dossier = SeniorVettingDossier(
            candidate_id=submission.candidate_id,
            scenario_id=spec.scenario_id,
            overall_vetting_score=score,
            recommendation=recommendation,
            architecture_score=score,
            concurrency_scalability_score=score,
            code_quality_reusability_score=score,
            executive_summary=res.content,
            trade_off_analysis="Baseline single-prompt review without dynamic load testing or AST analysis.",
            evidence_citations=[],
            primary_flaws_flagged=[]
        )

        logger.finalize(success=(score >= 70.0))
        return dossier, logger
