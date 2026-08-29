"""Evaluation metrics calculation: Primary Outcome, Human Time and Cost."""

from typing import List, Dict, Any
from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    """Result for a single evaluation case."""
    case_id: str
    runner_type: str
    passed: bool
    score: float = Field(default=0.0)  # 0.0 to 1.0
    latency_ms: float = 0.0
    tokens: int = 0
    cost_usd: float = 0.0
    human_time_estimated_sec: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)


class BenchmarkSummary(BaseModel):
    """Consolidated summary comparing Baseline vs Advanced."""
    runner_type: str
    total_cases: int
    passed_cases: int
    success_rate_pct: float
    average_score: float
    total_cost_usd: float
    avg_cost_per_task_usd: float
    total_latency_sec: float
    avg_latency_per_task_sec: float
    total_human_time_saved_sec: float


def compute_benchmark_summary(results: List[EvaluationResult]) -> BenchmarkSummary:
    """Compute aggregated benchmark metrics from case results."""
    total = len(results)
    if total == 0:
        return BenchmarkSummary(
            runner_type="unknown",
            total_cases=0,
            passed_cases=0,
            success_rate_pct=0.0,
            average_score=0.0,
            total_cost_usd=0.0,
            avg_cost_per_task_usd=0.0,
            total_latency_sec=0.0,
            avg_latency_per_task_sec=0.0,
            total_human_time_saved_sec=0.0
        )

    passed = sum(1 for r in results if r.passed)
    runner_type = results[0].runner_type
    total_cost = sum(r.cost_usd for r in results)
    total_tokens = sum(r.tokens for r in results)
    total_latency = sum(r.latency_ms for r in results) / 1000.0
    avg_score = sum(r.score for r in results) / total
    human_time_saved = sum(r.human_time_estimated_sec for r in results)

    return BenchmarkSummary(
        runner_type=runner_type,
        total_cases=total,
        passed_cases=passed,
        success_rate_pct=(passed / total) * 100.0,
        average_score=avg_score,
        total_cost_usd=total_cost,
        avg_cost_per_task_usd=total_cost / total,
        total_latency_sec=total_latency,
        avg_latency_per_task_sec=total_latency / total,
        total_human_time_saved_sec=human_time_saved
    )
